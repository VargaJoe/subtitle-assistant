"""Real loopback HTTP checks; no translation provider or optional dependencies."""

import json
from pathlib import Path
import queue
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import uuid

from subtitle_translator.project.errors import ProjectError
from subtitle_translator.project.http_api import (
    APPLICATION, CONNECTION_FILE, MAX_BODY, api_request, serve_api, stop_api,
)


ROOT = Path(__file__).resolve().parents[2]
SRT = b"1\n00:00:01,000 --> 00:00:02,000\nHello.\n\n2\n00:00:03,000 --> 00:00:04,000\nWorld!\n"
SERVER_SCRIPT = (
    "import sys; from subtitle_translator.project.http_api import serve_api; "
    "raise SystemExit(serve_api(sys.argv[1],allowed_root=sys.argv[2]))"
)


class HttpApiTests(unittest.TestCase):
    def setUp(self):
        location = ROOT / "temp" / "m2-http-tests"
        location.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=location)
        self.root = Path(self.temporary.name)
        self.allowed = self.root / "allowed"
        self.allowed.mkdir()
        self.workspace = self.root / "workspace"
        self.source = self.allowed / "source.srt"
        self.source.write_bytes(SRT)
        self.process = None
        self.start_server()

    def start_server(self):
        self.process = subprocess.Popen(
            [sys.executable, "-S", "-u", "-c", SERVER_SCRIPT, str(self.workspace), str(self.allowed)],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        lines = queue.Queue()
        threading.Thread(target=lambda: lines.put(self.process.stdout.readline()), daemon=True).start()
        try:
            self.ready_line = lines.get(timeout=8)
        except queue.Empty:
            self.process.kill()
            stdout, stderr = self.process.communicate(timeout=3)
            self.fail("Server did not become ready: " + stderr)
        if not self.ready_line:
            stdout, stderr = self.process.communicate(timeout=3)
            self.fail("Server startup failed: " + stderr)
        self.ready = json.loads(self.ready_line)
        self.registration = json.loads((self.workspace / CONNECTION_FILE).read_text(encoding="utf-8"))

    def tearDown(self):
        if self.process and self.process.poll() is None:
            stop_api(self.workspace)
            try:
                self.process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.communicate(timeout=3)
        elif self.process:
            self.process.communicate(timeout=3)
        self.temporary.cleanup()

    def http(self, path, payload=None, authenticated=True, raw=None, headers=None):
        request_headers = dict(headers or {})
        if authenticated:
            request_headers["Authorization"] = "Bearer " + self.registration["token"]
        if payload is not None:
            raw = json.dumps(payload).encode("utf-8")
        if raw is not None:
            request_headers.setdefault("Content-Type", "application/json")
        request = urllib.request.Request(self.registration["endpoint"] + path,
                                         data=raw, headers=request_headers)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            response = opener.open(request, timeout=3)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            return response.status, json.load(response), dict(response.headers)

    def import_project(self):
        result = api_request(self.workspace, "project.import", {"input_path": "source.srt"})
        self.assertTrue(result["ok"], result)
        return result

    def test_readiness_health_and_authenticated_discovery(self):
        self.assertTrue(self.ready["ok"])
        self.assertEqual(self.ready["data"]["state"], "ready")
        self.assertNotIn(self.registration["token"], self.ready_line)
        self.assertNotIn("token", self.ready_line)
        status, health, headers = self.http("/api/v1/health", authenticated=False)
        self.assertEqual(status, 200)
        self.assertEqual(health["data"]["application"], APPLICATION)
        self.assertNotIn(self.registration["token"], json.dumps(health))
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        for path in ("/api/v1/capabilities", "/api/v1/schema"):
            status, result, _ = self.http(path)
            self.assertEqual(status, 200)
            self.assertIn("batch.prepare", result["data"]["operations"])
            self.assertIn("entry.restore", result["data"]["operations"])

    def test_authentication_rejects_reads_writes_and_shutdown(self):
        for path, payload in (("/api/v1/capabilities", None),
                              ("/api/v1/operations", {"operation": "project.list", "arguments": {}}),
                              ("/api/v1/shutdown", {})):
            status, result, _ = self.http(path, payload, authenticated=False)
            self.assertEqual(status, 401)
            self.assertEqual(result["error"]["code"], "unauthorized")
        self.assertTrue(api_request(self.workspace, "project.list", {})["ok"])

    def test_shared_service_import_export_and_receipt_roundtrip(self):
        imported = self.import_project()
        project_id = imported["data"]["project"]["project_id"]
        self.assertIsNotNone(imported["request_id"])
        for operation in ("project.status", "project.validate", "entry.list", "job.status", "issue.list"):
            result = api_request(self.workspace, operation, {"project_id": project_id})
            self.assertTrue(result["ok"], result)
        receipt = api_request(self.workspace, "request.receipt", {"request_id": imported["request_id"]})
        self.assertTrue(receipt["ok"], receipt)
        result = api_request(self.workspace, "project.export", {
            "project_id": project_id, "output_path": "original.srt", "variant": "original",
        })
        self.assertTrue(result["ok"], result)
        self.assertEqual((self.allowed / "original.srt").read_bytes(), SRT)
        self.assertEqual(self.source.read_bytes(), SRT)

    def test_translation_edit_history_restore_and_job_roundtrip(self):
        project = self.import_project()["data"]["project"]
        project_id = project["project_id"]
        prepared = api_request(self.workspace, "batch.prepare", {
            "project_id": project_id, "expected_project_revision": project["revision"],
        })
        self.assertTrue(prepared["ok"], prepared)
        batch = prepared["data"]["batch"]
        self.assertTrue(api_request(self.workspace, "batch.get", {"batch_id": batch["batch_id"]})["ok"])
        activity = api_request(self.workspace, "job.activity", {
            "project_id": project_id, "agent_label": "Transport test agent", "phase": "translating",
            "batch_id": batch["batch_id"],
        })
        self.assertTrue(activity["ok"], activity)
        job = api_request(self.workspace, "job.status", {"project_id": project_id})
        self.assertEqual(job["data"]["freshness"], "fresh")
        targets = {"Hello.": "Helló.", "World!": "Világ!"}
        translations = [{"unit_id": unit["unit_id"], "entries": [
            {"entry_id": entry["entry_id"], "text": targets[entry["source_text"]],
             "state": "translated", "review_state": "agent_reviewed"}
            for entry in unit["source_entries"] if entry["entry_id"] in unit["writable_entry_ids"]
        ]} for unit in batch["units"]]
        submitted = api_request(self.workspace, "batch.submit", {
            "batch_id": batch["batch_id"], "expected_project_revision": batch["expected_project_revision"],
            "source_sha256": batch["source_sha256"], "context_revision": batch["context_revision"],
            "translations": translations,
        })
        self.assertTrue(submitted["ok"], submitted)
        self.assertEqual(submitted["data"]["remaining"], 0)
        exported = api_request(self.workspace, "project.export", {
            "project_id": project_id, "output_path": "target.srt", "variant": "target",
        })
        self.assertTrue(exported["ok"], exported)
        target = (self.allowed / "target.srt").read_text(encoding="utf-8")
        self.assertIn("Helló.", target)
        self.assertIn("00:00:03,000 --> 00:00:04,000", target)
        entries = api_request(self.workspace, "entry.list", {"project_id": project_id})["data"]["items"]
        edited = api_request(self.workspace, "entry.edit", {
            "project_id": project_id, "entry_id": entries[0]["entry_id"],
            "expected_project_revision": submitted["data"]["revision"],
            "changes": {"target_text": "Szia.", "review_state": "human_reviewed"}, "actor": "Human test label",
        })
        self.assertTrue(edited["ok"], edited)
        history = api_request(self.workspace, "entry.history", {
            "project_id": project_id, "entry_id": entries[0]["entry_id"],
        })
        self.assertEqual(len(history["data"]["items"]), 2)
        self.assertEqual(history["data"]["items"][-1]["change_id"], edited["data"]["change_id"])
        restored = api_request(self.workspace, "entry.restore", {
            "project_id": project_id, "change_id": edited["data"]["change_id"],
            "expected_project_revision": edited["data"]["revision"],
        })
        self.assertTrue(restored["ok"], restored)
        self.assertEqual(restored["data"]["entry"]["target_text"], "Helló.")
        controlled = api_request(self.workspace, "job.control", {"project_id": project_id, "action": "pause"})
        self.assertTrue(controlled["ok"], controlled)
        self.assertEqual(controlled["data"]["state"], "pause_requested")
        self.assertEqual(self.source.read_bytes(), SRT)

    def test_invalid_json_types_and_closed_dispatch_have_stable_errors(self):
        for raw, code in ((b"{", "invalid_json"), (b"[]", "invalid_request"),
                          (b'{"operation":"doctor","arguments":{},"arguments":{}}', "invalid_json"),
                          (b'{"operation":"doctor","arguments":{"x":NaN}}', "invalid_json")):
            status, result, _ = self.http("/api/v1/operations", raw=raw)
            self.assertEqual(status, 400)
            self.assertEqual(result["error"]["code"], code)
        for operation, arguments, code in (("__dict__", {}, "unknown_operation"),
                                           ("doctor", [], "invalid_request"),
                                           ("doctor", {"surprise": True}, "invalid_request"),
                                           ("project.import", {}, "invalid_request"),
                                           ("project.inspect", {"input_path": []}, "invalid_path"),
                                           ("project.status", {"project_id": []}, "invalid_request")):
            status, result, _ = self.http("/api/v1/operations", {"operation": operation, "arguments": arguments})
            self.assertEqual(status, 400, result)
            self.assertEqual(result["error"]["code"], code)
        status, result, _ = self.http("/api/v1/operations", raw=b"x" * (MAX_BODY + 1))
        self.assertEqual(status, 413)
        self.assertEqual(result["error"]["code"], "request_too_large")

    def test_import_inspect_export_paths_are_contained(self):
        outside = self.root / "outside.srt"
        outside.write_bytes(SRT)
        for operation in ("project.import", "project.inspect"):
            for path in (str(outside), "../outside.srt"):
                result = api_request(self.workspace, operation, {"input_path": path})
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"]["code"], "path_outside_allowed_root")
        imported = self.import_project()
        result = api_request(self.workspace, "project.export", {
            "project_id": imported["data"]["project"]["project_id"],
            "output_path": str(self.root / "forbidden.srt"),
        })
        self.assertEqual(result["error"]["code"], "path_outside_allowed_root")
        self.assertFalse((self.root / "forbidden.srt").exists())

    def test_meaningful_http_failure_status_and_client_envelope(self):
        imported = self.import_project()
        project_id = imported["data"]["project"]["project_id"]
        status, result, _ = self.http("/api/v1/operations", {
            "operation": "project.status", "arguments": {"project_id": "missing"},
        })
        self.assertEqual(status, 404)
        self.assertEqual(result["error"]["code"], "project_not_found")
        status, result, _ = self.http("/api/v1/operations", {
            "operation": "project.export", "arguments": {
                "project_id": project_id, "output_path": "conflict.srt", "expected_revision": 900,
            },
        })
        self.assertEqual(status, 409)
        self.assertEqual(result["error"]["code"], "revision_conflict")
        self.assertIsNotNone(result["request_id"])
        client_result = api_request(self.workspace, "project.status", {"project_id": "missing"})
        self.assertEqual(client_result["error"]["code"], "project_not_found")

    def test_live_registration_is_not_overwritten_and_shutdown_cleans_own_file(self):
        before = (self.workspace / CONNECTION_FILE).read_bytes()
        with self.assertRaises(ProjectError) as caught:
            serve_api(self.workspace, allowed_root=self.allowed)
        self.assertEqual(caught.exception.code, "api_already_running")
        self.assertEqual((self.workspace / CONNECTION_FILE).read_bytes(), before)
        result = stop_api(self.workspace)
        self.assertTrue(result["ok"], result)
        stdout, stderr = self.process.communicate(timeout=5)
        self.assertEqual(self.process.returncode, 0, stderr)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "")
        self.assertFalse((self.workspace / CONNECTION_FILE).exists())
        self.assertEqual(api_request(self.workspace, "doctor", {})["error"]["code"], "api_not_running")

    def test_cleanup_preserves_replaced_registration(self):
        replacement = {**self.registration, "instance_id": uuid.uuid4().hex}
        connection = self.workspace / CONNECTION_FILE
        connection.write_text(json.dumps(replacement), encoding="utf-8")
        self.assertTrue(stop_api(self.workspace)["ok"])
        self.process.communicate(timeout=5)
        self.assertEqual(json.loads(connection.read_text(encoding="utf-8")), replacement)

    def test_confirmed_stale_registration_is_replaced(self):
        self.assertTrue(stop_api(self.workspace)["ok"])
        self.process.communicate(timeout=5)
        old = dict(self.registration)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            unused_port = listener.getsockname()[1]
        old["endpoint"] = "http://127.0.0.1:" + str(unused_port)
        (self.workspace / CONNECTION_FILE).write_text(json.dumps(old), encoding="utf-8")
        self.start_server()
        self.assertNotEqual(self.registration["instance_id"], old["instance_id"])
        self.assertTrue(api_request(self.workspace, "doctor", {})["ok"])

    def test_non_loopback_host_and_remote_discovery_are_refused(self):
        with self.assertRaises(ProjectError) as caught:
            serve_api(self.root / "other", host="0.0.0.0", allowed_root=self.allowed)
        self.assertEqual(caught.exception.code, "invalid_host")
        other = self.root / "remote"
        other.mkdir()
        registration = {**self.registration, "endpoint": "http://192.0.2.1:80"}
        (other / CONNECTION_FILE).write_text(json.dumps(registration), encoding="utf-8")
        result = api_request(other, "doctor", {})
        self.assertEqual(result["error"]["code"], "invalid_api_connection")

    def test_client_retains_mutation_request_id_when_server_is_unavailable(self):
        request_id = str(uuid.uuid4())
        result = api_request(self.root / "missing-workspace", "project.import", {
            "input_path": str(self.source), "request_id": request_id,
        })
        self.assertEqual(result["error"]["code"], "api_not_running")
        self.assertEqual(result["request_id"], request_id)
        generated = api_request(self.root / "missing-workspace", "project.import", {"input_path": str(self.source)})
        self.assertEqual(str(uuid.UUID(generated["request_id"])), generated["request_id"])


if __name__ == "__main__":
    unittest.main()
