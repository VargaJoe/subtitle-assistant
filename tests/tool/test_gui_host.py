"""Real HTTP browser sessions, immutable files and launcher lifecycle checks."""

import base64
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import urllib.error
import urllib.parse
import urllib.request
import uuid

from subtitle_translator.project.errors import ProjectError
from subtitle_translator.project.gui_host import BrowserSessions, LAUNCH_FILE, MAX_UPLOAD_BYTES, launch_gui
from subtitle_translator.project.http_api import CONNECTION_FILE, api_request, stop_api


ROOT = Path(__file__).resolve().parents[2]
SRT = b"1\n00:00:01,000 --> 00:00:02,000\nHello.\n\n2\n00:00:03,000 --> 00:00:04,000\nWorld!\n"


class GuiHostTests(unittest.TestCase):
    def setUp(self):
        location = ROOT / "temp" / "m7a-gui-tests"
        location.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=location)
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "workspace"
        self.allowed = self.root / "allowed"
        self.allowed.mkdir()
        self.ready = launch_gui(self.workspace, allowed_root=self.allowed, no_browser=True)
        self.registration = json.loads((self.workspace / CONNECTION_FILE).read_text(encoding="utf-8"))
        self.origin = self.registration["endpoint"]
        self.launch = json.loads((self.workspace / LAUNCH_FILE).read_text(encoding="utf-8"))
        self.cookie = None

    def tearDown(self):
        stop_api(self.workspace)
        deadline = time.monotonic() + 5
        while (self.workspace / CONNECTION_FILE).exists() and time.monotonic() < deadline:
            time.sleep(.02)
        # Registration cleanup precedes interpreter exit by a small interval;
        # Windows retains log handles until the detached process finishes.
        deadline = time.monotonic() + 5
        while True:
            try:
                self.temporary.cleanup()
                break
            except PermissionError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(.02)

    def http(self, path, payload=None, bearer=False, cookie=True, origin=True, ui_header=True, headers=None):
        values = dict(headers or {})
        if bearer:
            values["Authorization"] = "Bearer " + self.registration["token"]
        if cookie and self.cookie:
            values["Cookie"] = self.cookie
        if origin:
            values.setdefault("Origin", self.origin)
        if ui_header:
            values.setdefault("X-Subtitle-UI", "1")
        raw = None
        if payload is not None:
            raw = json.dumps(payload).encode("utf-8")
            values["Content-Type"] = "application/json"
        request = urllib.request.Request(self.origin + path, data=raw, headers=values)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            response = opener.open(request, timeout=4)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            result = response.read()
            if response.headers.get_content_type() == "application/json":
                result = json.loads(result)
            return response.status, result, response.headers

    def exchange(self):
        ticket = urllib.parse.parse_qs(urllib.parse.urlsplit(self.launch["launch_url"]).fragment)["ticket"][0]
        status, result, headers = self.http("/ui/session", {"ticket": ticket}, cookie=False)
        self.assertEqual(status, 200, result)
        self.cookie = headers["Set-Cookie"].split(";", 1)[0]
        return ticket, headers

    def upload(self, **changes):
        body = {"request_id": str(uuid.uuid4()), "file_name": "subtitle.srt",
                "content_base64": base64.b64encode(SRT).decode("ascii"),
                "source_language": "en", "target_language": "hu"}
        body.update(changes)
        return body

    def import_project(self):
        body = self.upload()
        status, result, _ = self.http("/ui/import", body)
        self.assertEqual(status, 200, result)
        return body, result

    def test_launch_readiness_is_private_and_attaches_without_replacement(self):
        self.assertTrue(self.ready["server_started"])
        self.assertEqual(self.ready["ui_url"], self.origin + "/ui/")
        self.assertFalse(self.registration["token"] in json.dumps(self.ready))
        self.assertNotIn("ticket", json.dumps(self.ready))
        before = (self.workspace / CONNECTION_FILE).read_bytes()
        captured = io.StringIO()
        with redirect_stdout(captured), patch("subtitle_translator.project.gui_host.webbrowser.open", return_value=True) as opener:
            attached = launch_gui(self.workspace, allowed_root=self.allowed)
        self.assertFalse(attached["server_started"])
        self.assertTrue((self.workspace / CONNECTION_FILE).read_bytes() == before, "Live registration was replaced")
        self.assertEqual(captured.getvalue(), "")
        self.assertEqual(opener.call_count, 1)
        self.assertTrue(opener.call_args.args[0].startswith(self.origin + "/ui/#ticket="))
        self.assertFalse(self.registration["token"] in (self.workspace / LAUNCH_FILE).read_text())
        for name in ("gui-api.stdout.log", "gui-api.stderr.log"):
            self.assertFalse(self.registration["token"] in (self.workspace / name).read_text())

    def test_real_cli_parent_exit_keeps_server_alive_and_is_token_free(self):
        workspace = self.root / "cli-workspace"
        result = subprocess.run([sys.executable, "-S", "-m", "subtitle_translator.tool", "gui",
                                 "--workspace", str(workspace), "--allowed-root", str(self.allowed),
                                 "--no-browser", "--json"], cwd=ROOT, capture_output=True, text=True, timeout=15)
        try:
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            output = json.loads(result.stdout)
            self.assertTrue(output["data"]["server_started"])
            self.assertTrue(api_request(workspace, "project.list", {})["ok"])
            registration = json.loads((workspace / CONNECTION_FILE).read_text())
            self.assertFalse(registration["token"] in result.stdout + result.stderr)
            self.assertNotIn("#ticket", result.stdout)
            attached = subprocess.run([sys.executable, "-S", "-m", "subtitle_translator.tool", "gui",
                                      "--workspace", str(workspace), "--no-browser", "--json"],
                                     cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertEqual(attached.returncode, 0, attached.stdout + attached.stderr)
            self.assertFalse(json.loads(attached.stdout)["data"]["server_started"])
        finally:
            stop_api(workspace)
            deadline = time.monotonic() + 5
            while (workspace / CONNECTION_FILE).exists() and time.monotonic() < deadline:
                time.sleep(.02)

    def test_single_use_ticket_strict_cookie_and_session_authentication(self):
        status, result, _ = self.http("/ui/config", cookie=False)
        self.assertEqual(status, 401)
        self.assertEqual(result["error"]["code"], "unauthorized")
        ticket, headers = self.exchange()
        cookie = headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)
        self.assertNotIn("Domain=", cookie)
        status, result, _ = self.http("/ui/session", {"ticket": ticket})
        self.assertEqual(status, 401)
        self.assertEqual(result["error"]["code"], "invalid_ui_ticket")
        status, result, _ = self.http("/ui/config")
        self.assertEqual(status, 200)
        self.assertEqual(result["data"]["workspace"], str(self.workspace))
        self.assertEqual(result["data"]["allowed_root"], str(self.allowed))
        self.assertEqual(result["data"]["max_upload_bytes"], MAX_UPLOAD_BYTES)
        self.assertFalse(self.registration["token"] in json.dumps(result))
        for path in ("/api/v1/schema", "/api/v1/capabilities"):
            self.assertEqual(self.http(path)[0], 200)
        self.assertEqual(self.http("/api/v1/ui-launch", {})[0], 401)
        status, result, _ = self.http("/api/v1/operations", {"operation": "project.list", "arguments": {}})
        self.assertEqual(status, 200, result)

    def test_isolated_launcher_uses_same_interpreter_without_site_dependencies(self):
        workspace = self.root / "isolated-workspace"
        script = ("import sys; sys.path.insert(0, sys.argv.pop(1)); "
                  "from subtitle_translator.tool import main; raise SystemExit(main())")
        result = subprocess.run([sys.executable, "-I", "-S", "-c", script, str(ROOT), "gui",
                                 "--workspace", str(workspace), "--allowed-root", str(self.allowed),
                                 "--no-browser", "--json"], cwd=ROOT, capture_output=True, text=True, timeout=15)
        try:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(json.loads(result.stdout)["data"]["server_started"])
            self.assertTrue(api_request(workspace, "project.list", {})["ok"])
        finally:
            stop_api(workspace)
            deadline = time.monotonic() + 5
            while (workspace / CONNECTION_FILE).exists() and time.monotonic() < deadline:
                time.sleep(.02)

    def test_foreign_origins_missing_headers_and_rebinding_are_rejected(self):
        ticket = urllib.parse.parse_qs(urllib.parse.urlsplit(self.launch["launch_url"]).fragment)["ticket"][0]
        for kwargs in ({"origin": False}, {"headers": {"Origin": "http://evil.invalid"}},
                       {"ui_header": False}, {"headers": {"Host": "evil.invalid"}}):
            status, result, _ = self.http("/ui/session", {"ticket": ticket}, **kwargs)
            self.assertEqual(status, 403, result)
        self.exchange()
        body = {"operation": "project.list", "arguments": {}}
        for kwargs in ({"origin": False}, {"ui_header": False},
                       {"headers": {"Origin": "null"}}, {"headers": {"Host": "evil.invalid"}}):
            status, result, _ = self.http("/api/v1/operations", body, **kwargs)
            self.assertEqual(status, 403, result)
        self.assertEqual(self.http("/ui/config", headers={"Origin": "http://evil.invalid"})[0], 403)
        # Existing automation remains bearer-authenticated without UI headers.
        self.assertEqual(self.http("/api/v1/operations", body, bearer=True, cookie=False,
                                   origin=False, ui_header=False)[0], 200)

    def test_upload_staging_replays_and_rejects_changed_uuid_payload(self):
        self.exchange()
        body = self.upload(file_name=r"C:\fakepath\../../My subtitle.srt")
        status, result, _ = self.http("/ui/import", body)
        self.assertEqual(status, 200, result)
        project = result["data"]["project"]
        source = Path(project["source_path"])
        self.assertEqual(source, self.workspace / "imports" / body["request_id"] / "My subtitle.srt")
        self.assertEqual(source.read_bytes(), SRT)
        status, replay, _ = self.http("/ui/import", body)
        self.assertEqual(status, 200, replay)
        self.assertTrue(replay["data"]["replayed"])
        self.assertEqual(replay["data"]["project"]["project_id"], project["project_id"])
        for change in ({"content_base64": base64.b64encode(SRT.replace(b"Hello.", b"Changed.")).decode()},
                       {"content_base64": base64.b64encode(b"malformed subtitle").decode()},
                       {"name": "different"}, {"file_name": "different.srt"}, {"target_language": "de"}):
            status, conflict, _ = self.http("/ui/import", {**body, **change})
            self.assertEqual(status, 409, conflict)
            self.assertEqual(conflict["error"]["code"], "request_id_conflict")
        self.assertEqual(source.read_bytes(), SRT)
        receipt = api_request(self.workspace, "request.receipt", {"request_id": body["request_id"]})
        self.assertEqual(receipt["data"]["operation"], "project.import")

    def test_invalid_uploads_do_not_create_partial_projects_or_staged_sources(self):
        self.exchange()
        changes = [("invalid_upload", {"content_base64": "@@@="}),
                   ("invalid_upload", {"content_base64": "á"}),
                   ("invalid_subtitle", {"content_base64": base64.b64encode(b"bad subtitle").decode()}),
                   ("invalid_file_name", {"file_name": "../"}),
                   ("invalid_language", {"source_language": []}),
                   ("invalid_request_id", {"request_id": None}),
                   ("request_too_large", {"content_base64": base64.b64encode(b"x" * (MAX_UPLOAD_BYTES + 1)).decode()})]
        for code, change in changes:
            body = self.upload(**change)
            status, result, _ = self.http("/ui/import", body)
            self.assertIn(status, (400, 413), result)
            self.assertEqual(result["error"]["code"], code)
        self.assertEqual(api_request(self.workspace, "project.list", {})["data"]["total"], 0)
        self.assertFalse((self.workspace / "imports").exists())

    def test_upload_explicit_encoding_uses_shared_parser(self):
        self.exchange()
        raw = SRT.replace(b"Hello.", "Árvíztűrő.".encode("cp1250"))
        body = self.upload(content_base64=base64.b64encode(raw).decode(), encoding="cp1250")
        status, result, _ = self.http("/ui/import", body)
        self.assertEqual(status, 200, result)
        project_id = result["data"]["project"]["project_id"]
        entries = api_request(self.workspace, "entry.list", {"project_id": project_id})
        self.assertEqual(entries["data"]["items"][0]["source_text"], "Árvíztűrő.")

    def test_export_download_reconciles_receipt_replay_and_refuses_tampering(self):
        self.exchange()
        imported, project = self.import_project()
        project = project["data"]["project"]
        body = {"request_id": str(uuid.uuid4()), "project_id": project["project_id"],
                "variant": "original", "expected_revision": project["revision"]}
        status, result, _ = self.http("/ui/export", body)
        self.assertEqual(status, 200, result)
        url = result["data"]["download_url"]
        self.assertEqual(url, "/ui/download/" + body["request_id"])
        status, raw, headers = self.http(url)
        self.assertEqual(status, 200)
        self.assertEqual(raw, SRT)
        self.assertIn("attachment", headers["Content-Disposition"])
        self.assertIn('filename="subtitle.en.original.srt"', headers["Content-Disposition"])
        self.assertEqual(self.http(url, cookie=False)[0], 401)
        status, replay, _ = self.http("/ui/export", body)
        self.assertEqual(status, 200, replay)
        self.assertTrue(replay["data"]["replayed"])
        status, conflict, _ = self.http("/ui/export", {**body, "variant": "source"})
        self.assertEqual(status, 409, conflict)
        self.assertEqual(conflict["error"]["code"], "request_id_conflict")
        output = Path(result["data"]["path"])
        output.write_bytes(b"changed")
        self.assertEqual(self.http(url)[1]["error"]["code"], "export_output_changed")
        self.assertEqual(self.http("/ui/export", body)[1]["error"]["code"], "export_output_changed")
        self.assertEqual(Path(project["source_path"]).read_bytes(), SRT)

    def test_download_header_uses_project_language_name_and_blocks_header_injection(self):
        self.exchange()
        body = self.upload(name="Árvíz\r\nX-Injected: yes", source_language="en\r\nBad: bad")
        status, imported, _ = self.http("/ui/import", body)
        self.assertEqual(status, 200, imported)
        status, exported, _ = self.http("/ui/export", {
            "request_id": str(uuid.uuid4()), "project_id": imported["data"]["project"]["project_id"],
            "variant": "original", "expected_revision": 1,
        })
        self.assertEqual(status, 200, exported)
        status, raw, headers = self.http(exported["data"]["download_url"])
        self.assertEqual(status, 200)
        self.assertEqual(raw, SRT)
        disposition = headers["Content-Disposition"]
        self.assertIn('filename="Arviz__X-Injected_ yes.en__Bad_ bad.original.srt"', disposition)
        self.assertIn("filename*=UTF-8''%C3%81rv%C3%ADz", disposition)
        self.assertNotIn("\r", disposition)
        self.assertNotIn("\n", disposition)
        self.assertNotIn("X-Injected", headers)
        self.assertNotIn("Bad", headers)
        self.assertEqual(Path(exported["data"]["path"]).name,
                         exported["request_id"] + ".original.srt")

    def test_download_never_exposes_arbitrary_export_or_receipt_paths(self):
        self.exchange()
        _, imported = self.import_project()
        request_id = str(uuid.uuid4())
        outside = self.allowed / "owner-export.srt"
        result = api_request(self.workspace, "project.export", {
            "project_id": imported["data"]["project"]["project_id"], "request_id": request_id,
            "variant": "original", "output_path": str(outside),
        })
        self.assertTrue(result["ok"], result)
        status, result, _ = self.http("/ui/download/" + request_id)
        self.assertEqual(status, 404, result)
        self.assertEqual(outside.read_bytes(), SRT)
        self.assertNotEqual(self.http("/ui/download/../../api-connection.json")[0], 200)
        self.assertNotEqual(self.http("/ui/../api-connection.json", bearer=True)[0], 200)

    def test_draft_download_includes_partial_work_markers_report_and_exact_replay(self):
        self.exchange()
        _, imported = self.import_project()
        project_id = imported["data"]["project"]["project_id"]
        entries = api_request(self.workspace, "entry.list", {"project_id": project_id})["data"]["items"]
        changed = api_request(self.workspace, "entry.edit", {
            "request_id": str(uuid.uuid4()), "project_id": project_id,
            "entry_id": entries[0]["entry_id"], "expected_project_revision": 1,
            "changes": {"target_text": "Szia, még félkész"}})
        self.assertTrue(changed["ok"], changed)
        body = {"request_id": str(uuid.uuid4()), "project_id": project_id,
                "variant": "draft", "expected_revision": 2}
        status, exported, _ = self.http("/ui/export", body)
        self.assertEqual(status, 200, exported)
        self.assertEqual(exported["data"]["draft"]["pending_count"], 2)
        self.assertEqual(exported["data"]["draft"]["missing_count"], 1)
        status, raw, headers = self.http(exported["data"]["download_url"])
        self.assertEqual(status, 200)
        self.assertIn("[ELLENŐRIZENDŐ]\nSzia, még félkész", raw.decode("utf-8"))
        self.assertIn("[NINCS FORDÍTÁS]\nWorld!", raw.decode("utf-8"))
        self.assertIn(".hu.draft.srt", headers["Content-Disposition"])
        url = exported["data"]["review_download_url"]
        status, raw, headers = self.http(url)
        self.assertEqual(status, 200)
        self.assertIn("text/plain", headers["Content-Type"])
        self.assertIn(".hu.draft.review.txt", headers["Content-Disposition"])
        self.assertIn("#2 (SRT 2) 00:00:03,000 --> 00:00:04,000", raw.decode("utf-8"))
        self.assertIn("Hiányzó fordítás; a forrásszöveg látható.", raw.decode("utf-8"))
        self.assertEqual(self.http(url, cookie=False)[0], 401)
        status, replay, _ = self.http("/ui/export", body)
        self.assertEqual(status, 200, replay)
        self.assertTrue(replay["data"]["replayed"])
        self.assertEqual(replay["data"]["review_download_url"], url)
        status, final, _ = self.http("/ui/export", {**body, "request_id": str(uuid.uuid4()), "variant": "target"})
        self.assertEqual((status, final["error"]["code"]), (409, "translation_incomplete"))
        self.assertEqual(self.http("/ui/download/" + body["request_id"] + "/review/extra")[0], 400)
        self.assertEqual(api_request(self.workspace, "project.status", {"project_id": project_id})["data"]["project"]["revision"], 2)
        Path(exported["data"]["path"]).write_bytes(b"changed")
        self.assertEqual(self.http(url)[1]["error"]["code"], "export_output_changed")

    def test_source_export_no_clobber_target_incomplete_and_shutdown_session(self):
        self.exchange()
        _, imported = self.import_project()
        body = {"request_id": str(uuid.uuid4()), "project_id": imported["data"]["project"]["project_id"],
                "variant": "target", "expected_revision": 1}
        status, result, _ = self.http("/ui/export", body)
        self.assertEqual(status, 409, result)
        self.assertEqual(result["error"]["code"], "translation_incomplete")
        body.update(request_id=str(uuid.uuid4()), variant="source")
        output = self.workspace / "exports" / (body["request_id"] + ".source.srt")
        output.parent.mkdir(exist_ok=True)
        output.write_bytes(b"owner data")
        status, result, _ = self.http("/ui/export", body)
        self.assertEqual(status, 409, result)
        self.assertEqual(output.read_bytes(), b"owner data")
        self.assertEqual(self.http("/api/v1/shutdown", {})[0], 200)

    def test_fixed_assets_are_public_and_hardened_without_credentials(self):
        for path, content_type in (("/ui/", "text/html"), ("/ui/app.js", "text/javascript"),
                                   ("/ui/state.mjs", "text/javascript"), ("/ui/app.css", "text/css")):
            status, raw, headers = self.http(path, cookie=False, origin=False)
            self.assertEqual(status, 200, raw)
            self.assertEqual(headers.get_content_type(), content_type)
            self.assertEqual(headers["Cache-Control"], "no-store")
            self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
            self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
            self.assertFalse(self.registration["token"].encode() in raw)

    def test_launcher_preserves_unconfirmed_live_registration_and_replaces_confirmed_stale(self):
        # An occupied endpoint with a foreign/invalid response cannot authorize
        # replacing its registration, even if the intended API is unavailable.
        other = self.root / "unconfirmed"
        other.mkdir()
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            saved = {**self.registration, "endpoint": "http://127.0.0.1:" + str(listener.getsockname()[1])}
            connection = other / CONNECTION_FILE
            connection.write_text(json.dumps(saved))
            before = connection.read_bytes()
            with self.assertRaises(ProjectError) as caught:
                launch_gui(other, allowed_root=self.allowed, no_browser=True)
            self.assertEqual(caught.exception.code, "api_registration_unconfirmed")
            self.assertTrue(connection.read_bytes() == before, "Unconfirmed registration was replaced")
        # The now-unbound endpoint is independently proved stale by the API.
        try:
            ready = launch_gui(other, allowed_root=self.allowed, no_browser=True)
            self.assertTrue(ready["server_started"])
            self.assertTrue(api_request(other, "project.list", {})["ok"])
        finally:
            stop_api(other)
            deadline = time.monotonic() + 5
            while (other / CONNECTION_FILE).exists() and time.monotonic() < deadline:
                time.sleep(.02)


class BrowserSessionExpiryTests(unittest.TestCase):
    def test_tickets_and_sessions_expire_per_server(self):
        with patch("subtitle_translator.project.gui_host.time.monotonic", return_value=0):
            sessions = BrowserSessions()
            ticket = sessions.ticket()
            another = BrowserSessions()
            with self.assertRaises(ProjectError):
                another.exchange(ticket)
            session = sessions.exchange(ticket)
            self.assertTrue(sessions.valid(session))
            second = sessions.ticket()
        with patch("subtitle_translator.project.gui_host.time.monotonic", return_value=91):
            with self.assertRaises(ProjectError):
                sessions.exchange(second)
        with patch("subtitle_translator.project.gui_host.time.monotonic", return_value=12 * 3600 + 1):
            self.assertFalse(sessions.valid(session))


if __name__ == "__main__":
    unittest.main()
