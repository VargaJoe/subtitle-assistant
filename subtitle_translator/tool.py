"""Machine-readable, model-independent CLI: python -m subtitle_translator.tool."""

import argparse
import json
from pathlib import Path
import sys
import uuid

from .project.errors import ProjectError
from .project.service import API_VERSION, ProjectService


class ToolParser(argparse.ArgumentParser):
    def error(self, message):
        raise ProjectError("invalid_arguments", message)


def _common(parser, root=False):
    default = str(Path.cwd() / ".local" / "subtitle-assistant") if root else argparse.SUPPRESS
    parser.add_argument("--workspace", default=default, help="Workspace directory; default: .local/subtitle-assistant in current directory")
    parser.add_argument("--json", dest="json_output", action="store_true",
                        default=False if root else argparse.SUPPRESS, help="One JSON result on stdout")


def build_parser():
    parser = ToolParser(description="Subtitle Assistant external-agent subtitle tool")
    _common(parser, root=True)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("capabilities", "doctor"):
        _common(commands.add_parser(name))
    project = commands.add_parser("project")
    actions = project.add_subparsers(dest="action", required=True)
    imp = actions.add_parser("import", help="Import a complete, valid SRT into a persistent project")
    imp.add_argument("--input", required=True)
    imp.add_argument("--source", default="en")
    imp.add_argument("--target", default="hu")
    imp.add_argument("--name")
    imp.add_argument("--encoding")
    imp.add_argument("--request-id")
    _common(imp)
    inspect = actions.add_parser("inspect", help="Inspect a source file or stored project")
    choice = inspect.add_mutually_exclusive_group(required=True)
    choice.add_argument("--input")
    choice.add_argument("--project")
    inspect.add_argument("--encoding")
    _common(inspect)
    for name in ("status", "validate"):
        leaf = actions.add_parser(name)
        leaf.add_argument("--project", required=True)
        _common(leaf)
    listing = actions.add_parser("list")
    listing.add_argument("--limit", type=int, default=50)
    listing.add_argument("--cursor")
    _common(listing)
    export = actions.add_parser("export")
    export.add_argument("--project", required=True)
    export.add_argument("--output", required=True)
    export.add_argument("--variant", choices=("source", "original", "target", "draft"), default="source")
    export.add_argument("--expected-revision", type=int)
    export.add_argument("--request-id")
    _common(export)
    entries = commands.add_parser("entry")
    entry_actions = entries.add_subparsers(dest="action", required=True)
    listing = entry_actions.add_parser("list")
    listing.add_argument("--project", required=True)
    listing.add_argument("--limit", type=int, default=50)
    listing.add_argument("--cursor")
    _common(listing)
    for name in ("edit", "restore"):
        leaf = entry_actions.add_parser(name)
        leaf.add_argument("--request", required=True, help="JSON request file, or - for stdin")
        _common(leaf)
    history = entry_actions.add_parser("history")
    history.add_argument("--project", required=True)
    history.add_argument("--entry", required=True)
    _common(history)
    batch = commands.add_parser("batch")
    batch_actions = batch.add_subparsers(dest="action", required=True)
    for name in ("prepare", "submit"):
        leaf = batch_actions.add_parser(name)
        leaf.add_argument("--request", required=True)
        _common(leaf)
    get = batch_actions.add_parser("get")
    get.add_argument("--batch", required=True)
    _common(get)
    job = commands.add_parser("job")
    job_actions = job.add_subparsers(dest="action", required=True)
    for name in ("activity", "control"):
        leaf = job_actions.add_parser(name)
        leaf.add_argument("--request", required=True)
        _common(leaf)
    status = job_actions.add_parser("status")
    status.add_argument("--project", required=True)
    _common(status)
    issues = commands.add_parser("issue").add_subparsers(dest="action", required=True)
    listing = issues.add_parser("list")
    listing.add_argument("--project", required=True)
    listing.add_argument("--limit", type=int, default=50)
    listing.add_argument("--cursor")
    _common(listing)
    workspace = commands.add_parser("workspace").add_subparsers(dest="action", required=True)
    migrate = workspace.add_parser("migrate")
    migrate.add_argument("--expected-version", type=int, default=1)
    _common(migrate)
    api = commands.add_parser("api").add_subparsers(dest="action", required=True)
    serve = api.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=0)
    serve.add_argument("--allowed-root")
    _common(serve)
    call = api.add_parser("call")
    call.add_argument("--request", required=True)
    _common(call)
    _common(api.add_parser("stop"))
    gui = commands.add_parser("gui", help="Launch the local supervised subtitle editor")
    gui.add_argument("--host", default="127.0.0.1")
    gui.add_argument("--port", type=int, default=0)
    gui.add_argument("--allowed-root")
    gui.add_argument("--no-browser", action="store_true")
    _common(gui)
    request = commands.add_parser("request")
    request_actions = request.add_subparsers(dest="action", required=True)
    receipt = request_actions.add_parser("receipt")
    receipt.add_argument("--request-id", required=True)
    _common(receipt)
    return parser


def _run(args):
    service = ProjectService(args.workspace)
    if args.command == "capabilities":
        return service.capabilities()
    if args.command == "doctor":
        return service.doctor()
    if args.command == "request":
        return service.receipt(args.request_id)
    if args.command == "workspace":
        return service.migrate_workspace(args.expected_version)
    if args.command == "entry":
        if args.action == "edit":
            return service.edit_entry(args.request_data)
        if args.action == "restore":
            return service.restore_entry(args.request_data)
        if args.action == "history":
            return service.entry_history(args.project, args.entry)
        return service.list_entries(args.project, args.limit, args.cursor)
    if args.command == "batch":
        if args.action == "get":
            return service.get_batch(args.batch)
        return service.prepare_batch(args.request_data) if args.action == "prepare" else service.submit_batch(args.request_data)
    if args.command == "job":
        if args.action == "status":
            return service.job_status(args.project)
        return service.job_activity(args.request_data) if args.action == "activity" else service.control_job(args.request_data)
    if args.command == "issue":
        return service.translation_issues(args.project, args.limit, args.cursor)
    if args.action == "import":
        return service.import_project(args.input, args.source, args.target, args.name, args.encoding, args.request_id)
    if args.action == "inspect":
        return service.inspect_source(args.input, args.encoding) if args.input else service.status(args.project)
    if args.action == "status":
        return service.status(args.project)
    if args.action == "validate":
        return service.validate(args.project)
    if args.action == "list":
        return service.list_projects(args.limit, args.cursor)
    return service.export_project(args.project, args.output, args.variant, args.expected_revision, args.request_id)


def _read_request(path):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate field")
            result[key] = value
        return result
    try:
        text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8-sig")
        result = json.loads(text, object_pairs_hook=unique_pairs,
                            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (UnicodeError, ValueError) as exc:
        raise ProjectError("invalid_request", "Request must contain a valid JSON object") from exc
    if not isinstance(result, dict):
        raise ProjectError("invalid_request", "Request must contain a JSON object")
    return result


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    json_output = "--json" in argv
    request_id = None
    try:
        args = build_parser().parse_args(argv)
        json_output = args.json_output
        if args.command == "gui":
            from .project.gui_host import launch_gui
            result = launch_gui(args.workspace, args.host, args.port, args.allowed_root, args.no_browser)
            response = {"ok": True, "api_version": API_VERSION, "request_id": None,
                        "data": result, "warnings": []}
            if json_output:
                print(json.dumps(response, ensure_ascii=True))
            else:
                print("Subtitle Assistant ready: " + result["ui_url"])
            return 0
        if args.command == "api":
            from .project.http_api import api_request, serve_api, stop_api
            if args.action == "serve":
                return serve_api(args.workspace, args.host, args.port, args.allowed_root)
            if args.action == "stop":
                response = stop_api(args.workspace)
            else:
                payload = _read_request(args.request)
                if set(payload) != {"operation", "arguments"}:
                    raise ProjectError("invalid_request", "API call needs operation and arguments")
                response = api_request(args.workspace, payload["operation"], payload["arguments"])
            print(json.dumps(response, ensure_ascii=True))
            return 0 if response["ok"] else 1
        if hasattr(args, "request"):
            args.request_data = _read_request(args.request)
            try:
                request_id = str(uuid.UUID(str(args.request_data.get("request_id")))) if args.request_data.get("request_id") else str(uuid.uuid4())
            except ValueError as exc:
                raise ProjectError("invalid_request_id", "request_id must be a UUID") from exc
            args.request_data["request_id"] = request_id
        if args.command == "project" and args.action in ("import", "export"):
            # Return the operation ID even if publication/receipt recording fails.
            # Clients can then query a pending receipt instead of inventing a retry.
            try:
                request_id = str(uuid.UUID(args.request_id)) if args.request_id else str(uuid.uuid4())
            except ValueError as exc:
                raise ProjectError("invalid_request_id", "request_id must be a UUID") from exc
            args.request_id = request_id
        result = _run(args)
        request_id = result.pop("request_id", None)
        warnings = result.pop("warnings", [])
        response = {"ok": True, "api_version": API_VERSION, "request_id": request_id,
                    "data": result, "warnings": warnings}
    except ProjectError as exc:
        response = {"ok": False, "api_version": API_VERSION, "request_id": request_id,
                    "error": exc.to_dict(), "warnings": []}
    except OSError:
        response = {"ok": False, "api_version": API_VERSION, "request_id": request_id,
                    "error": {"code": "io_error", "message": "Cannot access the requested local file", "details": {}},
                    "warnings": []}
    if json_output:
        # ASCII escapes keep machine JSON valid even on legacy Windows code pages.
        print(json.dumps(response, ensure_ascii=True))
    elif response["ok"]:
        print(json.dumps(response["data"], ensure_ascii=False, indent=2))
    else:
        print(f"{response['error']['code']}: {response['error']['message']}", file=sys.stderr)
    return 0 if response["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
