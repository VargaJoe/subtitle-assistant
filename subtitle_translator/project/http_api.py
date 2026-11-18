"""Private, model-free loopback transport for :class:`ProjectService`.

The connection file is a local credential: clients discover it from the workspace,
and no token appears in readiness output or HTTP logs. Actor labels remain data.
"""

from contextlib import contextmanager
import hmac
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import inspect
import ipaddress
import json
import os
from pathlib import Path
import secrets
import socket
import threading
import urllib.error
import urllib.parse
import urllib.request
import unicodedata
import uuid

from .common import API_VERSION, _request_id
from .errors import ProjectError
from .service import ProjectService
from .gui_host import BrowserFiles, BrowserSessions, MAX_UPLOAD_BYTES, SESSION_TTL


APPLICATION = "subtitle-assistant"
CONNECTION_FILE = "api-connection.json"
MAX_BODY = 1024 * 1024
MAX_RESPONSE = 16 * MAX_BODY

# Both the method and invocation style are fixed here. No client value is ever
# used as an attribute name. Request-object methods own their field validation.
OPERATIONS = {
    "capabilities": (ProjectService.capabilities, False),
    "doctor": (ProjectService.doctor, False),
    "project.import": (ProjectService.import_project, False),
    "project.inspect": (ProjectService.inspect_source, False),
    "project.status": (ProjectService.status, False),
    "project.list": (ProjectService.list_projects, False),
    "entry.list": (ProjectService.list_entries, False),
    "project.validate": (ProjectService.validate, False),
    "project.export": (ProjectService.export_project, False),
    "request.receipt": (ProjectService.receipt, False),
    "workspace.migrate": (ProjectService.migrate_workspace, False),
    "batch.prepare": (ProjectService.prepare_batch, True),
    "batch.get": (ProjectService.get_batch, False),
    "batch.submit": (ProjectService.submit_batch, True),
    "entry.edit": (ProjectService.edit_entry, True),
    "entry.history": (ProjectService.entry_history, False),
    "job.activity": (ProjectService.job_activity, True),
    "job.status": (ProjectService.job_status, False),
    "job.control": (ProjectService.control_job, True),
    "issue.list": (ProjectService.translation_issues, False),
}
OPERATIONS["entry.restore"] = (ProjectService.restore_entry, True)

MUTATIONS = {"project.import", "project.export", "batch.prepare", "batch.submit",
             "entry.edit", "entry.restore", "job.activity", "job.control"}


def _success(data, request_id=None):
    data = dict(data)
    return {"ok": True, "api_version": API_VERSION,
            "request_id": data.pop("request_id", request_id),
            "warnings": data.pop("warnings", []), "data": data}


def _failure(code, message, details=None, request_id=None):
    return {"ok": False, "api_version": API_VERSION, "request_id": request_id,
            "error": {"code": code, "message": message, "details": details or {}},
            "warnings": []}


def _status(response):
    if response["ok"]:
        return 200
    code = response["error"]["code"]
    if code == "workspace_busy":
        return 503
    if code in ("internal_error", "workspace_error", "io_error") or "integrity_error" in code:
        return 500
    if code.endswith("_not_found"):
        return 404
    if ("conflict" in code or "stale" in code or "protected" in code
            or code in ("job_paused", "job_cancelled", "output_exists", "export_output_changed",
                        "job_not_running", "workspace_migration_required", "migration_backup_exists", "translation_incomplete")):
        return 409
    if code in ("invalid_translation", "timing_anchor_changed", "invalid_mapping", "invalid_translation_formatting",
                "formatting_scope_changed", "speaker_markers_changed", "accessibility_markers_changed",
                "batch_incomplete", "duplicate_translation", "unexpected_entry", "review_required"):
        return 422
    return 400


def _json_loads(raw):
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate field")
            result[key] = value
        return result

    def constant(value):
        raise ValueError("non-finite number")

    return json.loads(raw, object_pairs_hook=object_pairs, parse_constant=constant)


def _loopback_host(host):
    if host == "localhost":
        return "127.0.0.1"
    try:
        address = ipaddress.ip_address(host)
    except (TypeError, ValueError) as exc:
        raise ProjectError("invalid_host", "The API host must be a loopback IP address") from exc
    if not address.is_loopback:
        raise ProjectError("invalid_host", "The API host must be a loopback IP address")
    return str(address)


def _contained_path(value, allowed_root):
    if not isinstance(value, str) or not value.strip():
        raise ProjectError("invalid_path", "A non-empty path string is required")
    try:
        path = Path(value).expanduser()
        path = (path if path.is_absolute() else allowed_root / path).resolve()
        path.relative_to(allowed_root)
    except ValueError as exc:
        raise ProjectError("path_outside_allowed_root", "The requested path is outside the API allowed root") from exc
    except (OSError, TypeError) as exc:
        raise ProjectError("invalid_path", "Path cannot be resolved") from exc
    return str(path)


def _dispatch(service, operation, arguments, allowed_root):
    request_id = None
    try:
        if not isinstance(operation, str) or operation not in OPERATIONS:
            raise ProjectError("unknown_operation", "Unknown API operation")
        if not isinstance(arguments, dict):
            raise ProjectError("invalid_request", "arguments must be a JSON object")
        arguments = dict(arguments)
        if operation in MUTATIONS:
            request_id = _request_id(arguments.get("request_id"))
            arguments["request_id"] = request_id
        for field in ("project_id", "entry_id", "batch_id", "change_id"):
            if field in arguments and (not isinstance(arguments[field], str) or not arguments[field]):
                raise ProjectError("invalid_request", field + " must be a non-empty string")
        if "cursor" in arguments and arguments["cursor"] is not None and not isinstance(arguments["cursor"], str):
            raise ProjectError("invalid_request", "cursor must be a string or null")
        if "encoding" in arguments and arguments["encoding"] is not None and not isinstance(arguments["encoding"], str):
            raise ProjectError("invalid_request", "encoding must be a string or null")
        if operation in ("project.import", "project.inspect") and "input_path" in arguments:
            arguments["input_path"] = _contained_path(arguments["input_path"], allowed_root)
        if operation == "project.export" and "output_path" in arguments:
            arguments["output_path"] = _contained_path(arguments["output_path"], allowed_root)
        method, request_object = OPERATIONS[operation]
        if request_object:
            result = method(service, arguments)
        else:
            try:
                inspect.signature(method).bind(service, **arguments)
            except TypeError as exc:
                raise ProjectError("invalid_request", "Operation contains missing or unsupported arguments") from exc
            result = method(service, **arguments)
        return _success(result, request_id)
    except ProjectError as exc:
        return _failure(exc.code, str(exc), exc.details, request_id)
    except OSError:
        return _failure("io_error", "Cannot access the requested local file", request_id=request_id)
    except Exception:
        # An HTTP response must never echo payloads, credentials or tracebacks.
        return _failure("internal_error", "The operation could not be completed", request_id=request_id)


def _read_registration(workspace):
    try:
        with (Path(workspace).expanduser().resolve() / CONNECTION_FILE).open("rb") as handle:
            raw = handle.read(MAX_BODY + 1)
        if len(raw) > MAX_BODY:
            raise ValueError("oversized registration")
        registration = _json_loads(raw)
        if (not isinstance(registration, dict) or registration.get("application") != APPLICATION
                or registration.get("registration_version") != 1
                or not isinstance(registration.get("token"), str)
                or len(registration["token"]) < 32
                or not isinstance(registration.get("instance_id"), str)):
            raise ValueError("invalid registration")
        url = urllib.parse.urlsplit(registration["endpoint"])
        if (url.scheme != "http" or url.username or url.password or url.path or url.query
                or url.fragment or not url.port or _loopback_host(url.hostname) != url.hostname):
            raise ValueError("invalid endpoint")
        return registration
    except FileNotFoundError as exc:
        raise ProjectError("api_not_running", "No local API connection was found for this workspace") from exc
    except (OSError, ValueError, TypeError, KeyError, ProjectError) as exc:
        raise ProjectError("invalid_api_connection", "The workspace API connection is invalid") from exc


def _opener():
    # Local credentials must never be sent to environment-configured proxies or
    # followed to a redirected origin.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, message, headers, newurl):
            return None
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())


def _request(registration, path, payload=None, timeout=10, authenticated=True):
    headers = {"Accept": "application/json"}
    if authenticated:
        headers["Authorization"] = "Bearer " + registration["token"]
    raw = None
    if payload is not None:
        raw = json.dumps(payload, ensure_ascii=True, allow_nan=False).encode("utf-8")
        if len(raw) > MAX_BODY:
            raise ProjectError("request_too_large", "API request exceeds the one MiB limit")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(registration["endpoint"] + path, data=raw, headers=headers)
    try:
        response = _opener().open(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        body = response.read(MAX_RESPONSE + 1)
    if len(body) > MAX_RESPONSE:
        raise ProjectError("invalid_api_response", "API response exceeds the size limit")
    try:
        result = _json_loads(body)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ProjectError("invalid_api_response", "The local API returned invalid JSON") from exc
    if not isinstance(result, dict) or not isinstance(result.get("ok"), bool):
        raise ProjectError("invalid_api_response", "The local API returned an invalid envelope")
    return result


def _client_call(workspace, path, payload=None, timeout=10):
    try:
        return _request(_read_registration(workspace), path, payload, timeout)
    except ProjectError as exc:
        return _failure(exc.code, str(exc), exc.details)
    except (OSError, urllib.error.URLError):
        return _failure("api_unavailable", "The workspace local API is unavailable")
    except (ValueError, TypeError, RecursionError):
        return _failure("invalid_request", "The request cannot be encoded as JSON")


def api_request(workspace, operation, arguments, timeout=10):
    """Call the workspace's saved local endpoint without exposing its token."""
    request_id = None
    if isinstance(operation, str) and operation in MUTATIONS and isinstance(arguments, dict):
        arguments = dict(arguments)
        try:
            request_id = _request_id(arguments.get("request_id"))
        except ProjectError as exc:
            return _failure(exc.code, str(exc), exc.details)
        arguments["request_id"] = request_id
    response = _client_call(workspace, "/api/v1/operations",
                            {"operation": operation, "arguments": arguments}, timeout)
    if response.get("request_id") is None:
        response["request_id"] = request_id
    return response


def stop_api(workspace):
    """Ask the registered server to stop and return its application envelope."""
    return _client_call(workspace, "/api/v1/shutdown", {})


@contextmanager
def _workspace_lock(root):
    """Hold an OS lock through cleanup; the stable lock inode is never removed."""
    root.mkdir(parents=True, exist_ok=True)
    handle = (root / "api-server.lock").open("a+b")
    locked = False
    try:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise ProjectError("api_already_running", "An API server already owns this workspace") from exc
            if os.fstat(handle.fileno()).st_size == 0:
                handle.write(b"\0")
                handle.flush()
        else:
            import fcntl
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ProjectError("api_already_running", "An API server already owns this workspace") from exc
        locked = True
        yield
    finally:
        if locked:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _check_previous(root):
    if not (root / CONNECTION_FILE).exists():
        return
    previous = _read_registration(root)
    try:
        _request(previous, "/api/v1/health", timeout=1, authenticated=False)
    except urllib.error.URLError as exc:
        # Windows may time out even on an unbound loopback port. An exclusive
        # bind independently proves there is no listener; a timeout alone never
        # authorizes replacing the saved registration. The workspace lock keeps
        # another instance from starting between this check and publication.
        url = urllib.parse.urlsplit(previous["endpoint"])
        family = socket.AF_INET6 if ":" in url.hostname else socket.AF_INET
        try:
            with socket.socket(family) as probe:
                if os.name == "nt":
                    probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                probe.bind((url.hostname, url.port))
            return
        except OSError:
            pass
        raise ProjectError("api_registration_unconfirmed", "Cannot confirm that the previous API registration is stale") from exc
    except (OSError, ProjectError) as exc:
        raise ProjectError("api_registration_unconfirmed", "Cannot confirm that the previous API registration is stale") from exc
    raise ProjectError("api_already_running", "The workspace API registration is still live")


def _write_registration(root, registration):
    temporary = root / (".api-connection-" + registration["instance_id"] + ".tmp")
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(registration, handle, ensure_ascii=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, root / CONNECTION_FILE)
    finally:
        temporary.unlink(missing_ok=True)


def _handler(service, token, allowed_root, instance_id):
    sessions = BrowserSessions()
    files = BrowserFiles(service)
    cookie_name = "subtitle_ui_" + instance_id
    assets = {"/ui/": ("index.html", "text/html; charset=utf-8"),
              "/ui/app.js": ("app.js", "text/javascript; charset=utf-8"),
              "/ui/state.mjs": ("state.mjs", "text/javascript; charset=utf-8"),
              "/ui/app.css": ("app.css", "text/css; charset=utf-8")}

    class Handler(BaseHTTPRequestHandler):
        server_version = "SubtitleAssistant"
        sys_version = ""

        def log_message(self, format, *args):
            pass

        def send_error(self, code, message=None, explain=None):
            self._reply(code, _failure("unsupported_http_request", "Unsupported HTTP request"))

        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def _reply(self, status, response, extra_headers=None):
            # Windows closes sockets with unread POST bytes using RST, which can
            # discard even a complete error response. Drain a bounded small body
            # before closing; never allocate according to an untrusted length.
            length = self.headers.get_all("Content-Length", [])
            if (not getattr(self, "_body_consumed", False) and len(length) == 1
                    and len(length[0]) <= 7 and length[0].isascii() and length[0].isdecimal()):
                remaining = int(length[0])
                if remaining <= 2 * MAX_BODY:
                    try:
                        self.connection.settimeout(1)
                        while remaining:
                            chunk = self.rfile.read(min(65536, remaining))
                            if not chunk:
                                break
                            remaining -= len(chunk)
                    except OSError:
                        pass
                self._body_consumed = True
            body = json.dumps(response, ensure_ascii=True, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            for name, value in (extra_headers or {}).items():
                self.send_header(name, value)
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
            self.close_connection = True

        def _origin(self):
            host, port = self.server.server_address[:2]
            authority = ("[" + host + "]" if ":" in host else host) + ":" + str(port)
            return "http://" + authority

        def _same_origin(self, mutation=False):
            expected = self._origin()
            hosts = self.headers.get_all("Host", [])
            origins = self.headers.get_all("Origin", [])
            if hosts != [urllib.parse.urlsplit(expected).netloc]:
                return False
            if mutation:
                return origins == [expected] and self.headers.get_all("X-Subtitle-UI", []) == ["1"]
            return not origins or origins == [expected]

        def _cookie_session(self):
            try:
                cookies = SimpleCookie()
                cookies.load(self.headers.get("Cookie", ""))
                return sessions.valid(cookies[cookie_name].value) if cookie_name in cookies else False
            except CookieError:
                return False

        def _authenticated(self, bearer_only=False):
            supplied = self.headers.get("Authorization", "")
            if hmac.compare_digest(supplied.encode("utf-8"), ("Bearer " + token).encode("ascii")):
                return True
            if not bearer_only and self._cookie_session():
                if not self._same_origin(mutation=self.command == "POST"):
                    self._reply(403, _failure("ui_origin_rejected", "A same-origin browser request is required"))
                    return False
                return True
            self._reply(401, _failure("unauthorized", "A valid workspace API credential or browser session is required"))
            return False

        def _file(self, raw, content_type, filename=None):
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
            if filename:
                fallback = unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode("ascii")
                fallback = "".join(character if character.isalnum() or character in "._ -" else "_" for character in fallback).strip(" .") or "subtitle.srt"
                disposition = 'attachment; filename="' + fallback + '"'
                if filename != fallback:
                    disposition += "; filename*=UTF-8''" + urllib.parse.quote(filename, safe="")
                self.send_header("Content-Disposition", disposition)
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(raw)
            self.close_connection = True

        def do_GET(self):
            if self.path in assets:
                filename, mime = assets[self.path]
                try:
                    self._file((Path(__file__).resolve().parents[1] / "web" / filename).read_bytes(), mime)
                except OSError:
                    self._reply(404, _failure("asset_not_found", "Browser asset is unavailable"))
                return
            if self.path == "/api/v1/health":
                self._reply(200, _success({"application": APPLICATION, "api_version": API_VERSION,
                                          "instance_id": instance_id}))
                return
            if not self._authenticated():
                return
            if self.path == "/ui/config":
                self._reply(200, _success({"workspace": str(service.store.root),
                                          "allowed_root": str(allowed_root),
                                          "max_upload_bytes": MAX_UPLOAD_BYTES,
                                          "api_version": API_VERSION}))
            elif self.path.startswith("/ui/download/"):
                try:
                    download_id = self.path[len("/ui/download/"):]
                    review = download_id.endswith("/review")
                    filename, raw = files.download(download_id[:-7] if review else download_id, review=review)
                    self._file(raw, "text/plain; charset=utf-8" if review else "application/x-subrip", filename)
                except ProjectError as exc:
                    response = _failure(exc.code, str(exc), exc.details)
                    self._reply(_status(response), response)
                except OSError:
                    self._reply(500, _failure("io_error", "Cannot read the generated export"))
            elif self.path == "/api/v1/capabilities":
                response = _dispatch(service, "capabilities", {}, allowed_root)
                self._reply(_status(response), response)
            elif self.path == "/api/v1/schema":
                self._reply(200, _success({"operations": sorted(OPERATIONS),
                                          "request": {"operation": "string", "arguments": "object"},
                                          "max_request_bytes": MAX_BODY}))
            else:
                self._reply(404, _failure("endpoint_not_found", "Unknown API endpoint"))

        def _body(self):
            if self.headers.get("Transfer-Encoding"):
                raise ProjectError("invalid_request", "Transfer encoding is unsupported")
            length = self.headers.get_all("Content-Length", [])
            if len(length) != 1 or not length[0].isascii() or not length[0].isdecimal():
                raise ProjectError("invalid_request", "One Content-Length header is required")
            if len(length[0]) > 7:
                raise ProjectError("request_too_large", "API request exceeds the one MiB limit")
            count = int(length[0])
            if count > MAX_BODY:
                raise ProjectError("request_too_large", "API request exceeds the one MiB limit")
            if self.headers.get_content_type() != "application/json":
                raise ProjectError("invalid_request", "Content-Type must be application/json")
            raw = self.rfile.read(count)
            self._body_consumed = True
            try:
                if len(raw) != count:
                    raise ValueError("incomplete body")
                return _json_loads(raw)
            except (ValueError, UnicodeError, RecursionError) as exc:
                raise ProjectError("invalid_json", "Request body must contain valid JSON") from exc

        def do_POST(self):
            if self.path == "/ui/session":
                if not self._same_origin(mutation=True):
                    self._reply(403, _failure("ui_origin_rejected", "A same-origin browser request is required"))
                    return
            elif not self._authenticated(bearer_only=self.path == "/api/v1/ui-launch"):
                return
            try:
                body = self._body()
                if self.path == "/ui/session":
                    if not isinstance(body, dict) or set(body) != {"ticket"}:
                        raise ProjectError("invalid_request", "Session exchange requires a browser ticket")
                    session = sessions.exchange(body["ticket"])
                    self._reply(200, _success({"state": "ready"}), {"Set-Cookie": cookie_name + "=" + session + "; HttpOnly; SameSite=Strict; Path=/; Max-Age=" + str(SESSION_TTL)})
                elif self.path == "/api/v1/ui-launch":
                    if body != {}:
                        raise ProjectError("invalid_request", "Browser launch accepts an empty JSON object")
                    self._reply(200, _success({"launch_url": self._origin() + "/ui/#ticket=" + sessions.ticket()}))
                elif self.path in ("/ui/import", "/ui/export"):
                    request_id = _request_id(body.get("request_id")) if isinstance(body, dict) else None
                    try:
                        result = files.import_upload(body) if self.path == "/ui/import" else files.export_download(body)
                        response = _success(result, request_id)
                    except ProjectError as exc:
                        response = _failure(exc.code, str(exc), exc.details, request_id)
                    except OSError:
                        response = _failure("io_error", "Cannot access generated workspace storage", request_id=request_id)
                    self._reply(413 if not response["ok"] and response["error"]["code"] == "request_too_large" else _status(response), response)
                elif self.path == "/api/v1/shutdown":
                    if body != {}:
                        raise ProjectError("invalid_request", "Shutdown accepts an empty JSON object")
                    self._reply(200, _success({"state": "stopping"}))
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                elif self.path == "/api/v1/operations":
                    if not isinstance(body, dict) or set(body) != {"operation", "arguments"}:
                        raise ProjectError("invalid_request", "A request requires operation and arguments fields")
                    response = _dispatch(service, body["operation"], body["arguments"], allowed_root)
                    self._reply(_status(response), response)
                else:
                    self._reply(404, _failure("endpoint_not_found", "Unknown API endpoint"))
            except ProjectError as exc:
                self._reply(413 if exc.code == "request_too_large" else 401 if exc.code == "invalid_ui_ticket" else 400,
                            _failure(exc.code, str(exc), exc.details))
            except (OSError, TimeoutError):
                self.close_connection = True

    return Handler


def serve_api(workspace, host="127.0.0.1", port=0, allowed_root=None):
    """Serve until authenticated shutdown; print one token-free ready envelope."""
    host = _loopback_host(host)
    if type(port) is not int or not 0 <= port <= 65535:
        raise ProjectError("invalid_port", "port must be an integer between 0 and 65535")
    root = Path(workspace).expanduser().resolve()
    allowed_root = Path(allowed_root if allowed_root is not None else Path.cwd()).expanduser().resolve()
    if not allowed_root.is_dir():
        raise ProjectError("invalid_path", "The API allowed root must be an existing directory")
    instance_id = uuid.uuid4().hex
    token = secrets.token_urlsafe(32)
    service = ProjectService(root)

    class Server(ThreadingHTTPServer):
        address_family = socket.AF_INET6 if ":" in host else socket.AF_INET
        daemon_threads = False

        def handle_error(self, request, client_address):
            # BaseServer otherwise prints exception tracebacks to stderr.
            pass

    with _workspace_lock(root):
        _check_previous(root)
        with Server((host, port), _handler(service, token, allowed_root, instance_id)) as server:
            bound_port = server.server_address[1]
            address = "[" + host + "]" if ":" in host else host
            endpoint = "http://" + address + ":" + str(bound_port)
            registration = {"application": APPLICATION, "registration_version": 1,
                            "instance_id": instance_id, "endpoint": endpoint,
                            "token": token, "pid": os.getpid()}
            _write_registration(root, registration)
            try:
                print(json.dumps(_success({"state": "ready", "endpoint": endpoint,
                                          "connection_file": str(root / CONNECTION_FILE),
                                          "allowed_root": str(allowed_root)}), ensure_ascii=True), flush=True)
                server.serve_forever(poll_interval=0.05)
            finally:
                try:
                    saved = _read_registration(root)
                    if saved["instance_id"] == instance_id and hmac.compare_digest(saved["token"], token):
                        (root / CONNECTION_FILE).unlink()
                except ProjectError:
                    pass
    return 0
