"""Model-free browser launch and generated upload/download storage.

The long-lived API credential never reaches the page. Browser authentication is
an in-memory, expiring session obtained using a one-use launch ticket.
"""

import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import uuid
import webbrowser

from .common import API_VERSION, _atomic_create, _request_id
from .errors import ProjectError
from .srt import parse_source


MAX_UPLOAD_BYTES = 700 * 1024
LAUNCH_FILE = "gui-launch.json"
TICKET_TTL = 90
SESSION_TTL = 12 * 60 * 60


class BrowserSessions:
    def __init__(self):
        self.lock = threading.Lock()
        self.tickets = {}
        self.sessions = {}

    def _prune(self):
        now = time.monotonic()
        self.tickets = {key: end for key, end in self.tickets.items() if end > now}
        self.sessions = {key: end for key, end in self.sessions.items() if end > now}

    def ticket(self):
        import secrets
        with self.lock:
            self._prune()
            if len(self.tickets) >= 128:
                raise ProjectError("ui_launch_busy", "Too many outstanding browser launches")
            ticket = secrets.token_urlsafe(32)
            self.tickets[ticket] = time.monotonic() + TICKET_TTL
            return ticket

    def exchange(self, ticket):
        import secrets
        with self.lock:
            self._prune()
            if not isinstance(ticket, str) or self.tickets.pop(ticket, None) is None:
                raise ProjectError("invalid_ui_ticket", "Browser launch ticket is invalid or expired")
            session = secrets.token_urlsafe(32)
            self.sessions[session] = time.monotonic() + SESSION_TTL
            return session

    def valid(self, session):
        with self.lock:
            self._prune()
            return isinstance(session, str) and session in self.sessions


def _fields(body, required, optional=()):
    if not isinstance(body, dict) or not set(required) <= set(body) or set(body) - set(required) - set(optional):
        raise ProjectError("invalid_request", "Request contains missing or unsupported fields")


def _generated_path(root, *parts):
    path = root.joinpath(*parts)
    # Owner-created links must never turn generated storage into arbitrary files.
    if path.resolve() != path.absolute():
        raise ProjectError("invalid_storage_path", "Generated workspace storage contains a link")
    return path


class BrowserFiles:
    def __init__(self, service):
        self.service = service
        self.root = service.store.root
        self.lock = threading.Lock()

    def import_upload(self, body):
        _fields(body, ("request_id", "file_name", "content_base64", "source_language", "target_language"), ("name", "encoding"))
        if not isinstance(body["request_id"], str):
            raise ProjectError("invalid_request_id", "request_id must be a UUID")
        request_id = _request_id(body["request_id"])
        if not isinstance(body["file_name"], str) or len(body["file_name"]) > 1024:
            raise ProjectError("invalid_file_name", "A subtitle file name is required")
        # Both Windows and POSIX path components supplied by a picker are ignored.
        name = re.split(r"[/\\]", body["file_name"])[-1]
        name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
        if not name or name in (".", "..") or not name.lower().endswith(".srt"):
            raise ProjectError("invalid_file_name", "Upload must have an SRT file name")
        if len(name) > 120:
            name = name[:116] + ".srt"
        if name.split(".")[0].rstrip(" ").upper() in {"CON", "PRN", "AUX", "NUL", *["COM" + str(i) for i in range(1, 10)], *["LPT" + str(i) for i in range(1, 10)]}:
            name = "subtitle-" + name
        encoded = body["content_base64"]
        if not isinstance(encoded, str):
            raise ProjectError("invalid_upload", "Subtitle content must be strict base64")
        if len(encoded) > 4 * ((MAX_UPLOAD_BYTES + 2) // 3):
            raise ProjectError("request_too_large", "Subtitle upload exceeds the upload limit")
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ProjectError("invalid_upload", "Subtitle content must be strict base64") from exc
        if len(raw) > MAX_UPLOAD_BYTES:
            raise ProjectError("request_too_large", "Subtitle upload exceeds the upload limit")
        for field in ("source_language", "target_language"):
            value = body[field]
            if not isinstance(value, str) or not value.strip() or len(value) > 32:
                raise ProjectError("invalid_language", "Language must be a non-empty code or name (max 32 characters)")
        if body.get("name") is not None and not isinstance(body["name"], str):
            raise ProjectError("invalid_request", "name must be a string")
        if body.get("encoding") is not None and not isinstance(body["encoding"], str):
            raise ProjectError("invalid_request", "encoding must be a string")
        manifest = {"file_name": name, "sha256": hashlib.sha256(raw).hexdigest(),
                    "source_language": body["source_language"], "target_language": body["target_language"],
                    "name": body.get("name"), "encoding": body.get("encoding")}
        with self.lock:
            source = _generated_path(self.root, "imports", request_id, name)
            record = _generated_path(self.root, "imports", request_id, "request.json")
            if self.service.store.database.exists():
                try:
                    receipt = self.service.receipt(request_id)
                except ProjectError as exc:
                    if exc.code != "request_not_found":
                        raise
                else:
                    if (receipt["operation"] != "project.import"
                            or receipt["result"].get("project", {}).get("source_path") != str(source)):
                        raise ProjectError("request_id_conflict", "request_id was already used with different input")
            if record.exists():
                try:
                    previous = json.loads(record.read_text(encoding="utf-8"))
                except (UnicodeError, ValueError) as exc:
                    raise ProjectError("upload_integrity_error", "Staged subtitle request record has changed") from exc
                if previous != manifest:
                    raise ProjectError("request_id_conflict", "request_id was already used with different input")
            parsed = parse_source(raw, body.get("encoding"))
            if parsed.errors:
                raise ProjectError("invalid_subtitle", "Import refused: malformed blocks would cause source loss", {"inspection": parsed.report()})
            if not record.exists():
                # Record publication is immutable. Reconciliation can finish a
                # crash between this record and source publication safely.
                _atomic_create(record, json.dumps(manifest, sort_keys=True).encode("utf-8"))
            if source.exists():
                if source.read_bytes() != raw:
                    raise ProjectError("request_id_conflict", "Staged subtitle content has changed")
            else:
                _atomic_create(source, raw)
            return self.service.import_project(str(source), body["source_language"], body["target_language"],
                                               body.get("name"), body.get("encoding"), request_id=request_id)

    def export_download(self, body):
        _fields(body, ("request_id", "project_id", "variant", "expected_revision"))
        if not isinstance(body["request_id"], str):
            raise ProjectError("invalid_request_id", "request_id must be a UUID")
        request_id = _request_id(body["request_id"])
        variant = body["variant"]
        if variant not in ("source", "target", "original", "draft"):
            raise ProjectError("unsupported_export_variant", "Unknown export variant")
        output = _generated_path(self.root, "exports", request_id + "." + variant + ".srt")
        result = self.service.export_project(body["project_id"], str(output), variant,
                                             body["expected_revision"], request_id)
        links = {"download_url": "/ui/download/" + request_id}
        if variant == "draft":
            links["review_download_url"] = "/ui/download/" + request_id + "/review"
        return {**result, **links}

    def download(self, request_id, review=False):
        canonical = _request_id(request_id)
        if canonical != request_id:
            raise ProjectError("download_not_found", "Unknown generated download")
        receipt = self.service.receipt(request_id)
        result = receipt["result"]
        variant = result.get("variant")
        if receipt["operation"] != "project.export" or receipt["state"] != "completed" or variant not in ("source", "target", "original", "draft"):
            raise ProjectError("download_not_found", "No completed generated export exists")
        output = _generated_path(self.root, "exports", request_id + "." + variant + ".srt")
        if result.get("path") != str(output) or not output.is_file():
            raise ProjectError("download_not_found", "No completed generated export exists")
        raw = output.read_bytes()
        if hashlib.sha256(raw).hexdigest() != result.get("sha256"):
            raise ProjectError("export_output_changed", "Completed export is missing or has changed")
        project = self.service.status(result["project_id"])["project"]
        # Keep generated paths opaque and stable, but give browser downloads a
        # useful project/language name. Never carry path or control characters
        # from project labels into an attachment header or suggested file name.
        def label(value, fallback, maximum):
            value = re.sub(r'[\x00-\x1f\x7f<>:"/\\|?*]', "_", value).strip(" .")
            return value[:maximum].rstrip(" .") or fallback
        name = label(project["name"], "subtitle", 100)
        language = label(project["target_language"] if variant in ("target", "draft") else project["source_language"], "und", 32)
        if review:
            if variant != "draft" or not isinstance(result.get("draft"), dict):
                raise ProjectError("download_not_found", "No draft review report exists")
            from ..srt_format import format_timestamp
            report = result["draft"]
            lines = ["Subtitle Assistant — munkaváltozat ellenőrzési lista", name,
                     f"Mentett változat: {result['revision']}",
                     f"Ellenőrizendő: {report['pending_count']} / {report['entry_count']}; hiányzó fordítás: {report['missing_count']}",
                     "A munkaváltozat nem végleges. A hiányzó cél helyén jelölt forrásszöveg látható.", ""]
            reasons = {"missing_translation": "Hiányzó fordítás; a forrásszöveg látható.",
                       "stale_translation": "A fordítás alapjául szolgáló szöveg vagy időzítés megváltozott.",
                       "review_required": "A szöveg még nincs átnézve.",
                       "formatting_review": "A csoport formázását vagy beszélőjelölését ellenőrizni kell."}
            ordinals = {entry["entry_id"]: entry["ordinal"] for entry in report["entries"]}
            for entry in report["entries"]:
                lines.append(f"#{entry['ordinal']} (SRT {entry['source_index']}) "
                             f"{format_timestamp(entry['start_ms'])} --> {format_timestamp(entry['end_ms'])} "
                             f"{entry['marker']} · {reasons.get(entry['reason'], 'Ellenőrzés szükséges.')}")
            for issue in report.get("formatting_issues", []):
                affected = ", ".join(f"#{ordinals[entry_id]}" for entry_id in issue["entry_ids"] if entry_id in ordinals)
                lines.append(f"Csoportos formázási vagy beszélőjelölési ellenőrzés szükséges: {affected}")
            return name + "." + language + ".draft.review.txt", ("\n".join(lines) + "\n").encode("utf-8")
        return name + "." + language + "." + variant + ".srt", raw


def _private_launch_file(root, payload):
    temporary = root / (".gui-launch-" + uuid.uuid4().hex + ".tmp")
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, root / LAUNCH_FILE)
    finally:
        temporary.unlink(missing_ok=True)


def launch_gui(workspace, host="127.0.0.1", port=0, allowed_root=None, no_browser=False):
    """Attach or start a detached local API, then privately open a launch ticket."""
    from .http_api import (_check_previous, _loopback_host, _read_registration,
                           _request, _workspace_lock)
    host = _loopback_host(host)
    if type(port) is not int or not 0 <= port <= 65535:
        raise ProjectError("invalid_port", "port must be an integer between 0 and 65535")
    root = Path(workspace).expanduser().resolve()
    allowed = Path(allowed_root if allowed_root is not None else Path.cwd()).expanduser().resolve()
    if not allowed.is_dir():
        raise ProjectError("invalid_path", "The API allowed root must be an existing directory")
    root.mkdir(parents=True, exist_ok=True)
    started = False
    child = None
    # This separate launch lock serializes only launchers, leaving API ownership
    # and stale-registration proof to the established API workspace lock.
    with _workspace_lock(root / "gui-runtime"):
        try:
            registration = _read_registration(root)
            health = _request(registration, "/api/v1/health", timeout=1, authenticated=False)
            if (not health.get("ok") or not isinstance(health.get("data"), dict)
                    or health["data"].get("application") != "subtitle-assistant"
                    or health["data"].get("instance_id") != registration["instance_id"]):
                raise ProjectError("api_registration_unconfirmed", "Registered local API identity could not be confirmed")
        except ProjectError as exc:
            if exc.code != "api_not_running":
                raise
            registration = None
        except (OSError, urllib.error.URLError):
            # Do not weaken existing stale/occupied endpoint checks.
            with _workspace_lock(root):
                _check_previous(root)
            registration = None
        if registration is None:
            package_root = Path(__file__).resolve().parents[2]
            # A source checkout uses -S with its explicit cwd. Preserve isolated
            # launchers through -I and a trusted package path, still without site.
            command = [sys.executable, "-S", "-u", "-m", "subtitle_translator.tool", "api", "serve",
                       "--workspace", str(root), "--host", host, "--port", str(port),
                       "--allowed-root", str(allowed), "--json"]
            if sys.flags.isolated:
                command = [sys.executable, "-I", "-S", "-u", "-c",
                           "import sys; sys.path.insert(0, sys.argv.pop(1)); from subtitle_translator.tool import main; raise SystemExit(main())",
                           str(package_root), *command[5:]]
            with (root / "gui-api.stdout.log").open("ab") as stdout, (root / "gui-api.stderr.log").open("ab") as stderr:
                kwargs = {"cwd": str(package_root), "stdin": subprocess.DEVNULL, "stdout": stdout, "stderr": stderr}
                if os.name == "nt":
                    kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
                else:
                    kwargs["start_new_session"] = True
                child = subprocess.Popen(command, **kwargs)
            # Keep the Popen handle until exit and reap it while this launcher is
            # alive; a daemon waiter never holds the launcher process open.
            threading.Thread(target=child.wait, daemon=True).start()
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if child.poll() is not None:
                    raise ProjectError("gui_start_failed", "Local API failed to start; inspect workspace GUI API logs")
                try:
                    candidate = _read_registration(root)
                    health = _request(candidate, "/api/v1/health", timeout=.4, authenticated=False)
                    if (health.get("ok") and isinstance(health.get("data"), dict)
                            and health["data"].get("application") == "subtitle-assistant"
                            and health["data"].get("instance_id") == candidate["instance_id"]):
                        registration = candidate
                        break
                except (ProjectError, OSError, urllib.error.URLError):
                    pass
                time.sleep(.05)
            if registration is None:
                child.terminate()
                raise ProjectError("gui_start_timeout", "Local API did not become ready within ten seconds")
            started = True
        result = _request(registration, "/api/v1/ui-launch", {}, timeout=3)
        if not result.get("ok"):
            raise ProjectError("gui_unavailable", "Registered API does not support browser launch", {"code": result.get("error", {}).get("code")})
        url = result.get("data", {}).get("launch_url") if isinstance(result.get("data"), dict) else None
        expected = registration["endpoint"] + "/ui/#ticket="
        if not isinstance(url, str) or not url.startswith(expected) or not re.fullmatch(r"[A-Za-z0-9_-]{32,100}", url[len(expected):]):
            raise ProjectError("invalid_api_response", "Local API returned an invalid browser launch")
        _private_launch_file(root, {"launch_url": url, "instance_id": registration["instance_id"]})
        if not no_browser:
            webbrowser.open(url)
        return {"state": "ready", "ui_url": registration["endpoint"] + "/ui/",
                "launch_file": str(root / LAUNCH_FILE), "server_started": started,
                "workspace": str(root), "api_version": API_VERSION}
