"""Model-free application operations used by the CLI and future API/GUI."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid

from .errors import ProjectError
from .srt import MAX_INTEGER

API_VERSION = "1.1"


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _request_id(value):
    if value is None:
        return str(uuid.uuid4())
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError) as exc:
        raise ProjectError("invalid_request_id", "request_id must be a UUID") from exc


def _page(limit, cursor):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
        raise ProjectError("invalid_page", "limit must be an integer between 1 and 500")
    try:
        offset = int(cursor or 0)
    except (TypeError, ValueError) as exc:
        raise ProjectError("invalid_cursor", "cursor must be a non-negative integer") from exc
    if offset < 0 or offset > MAX_INTEGER or str(offset) != str(cursor or 0):
        raise ProjectError("invalid_cursor", "cursor must be a non-negative integer")
    return offset


def _path(value):
    try:
        return Path(value).expanduser().resolve()
    except (OSError, ValueError, TypeError) as exc:
        raise ProjectError("invalid_path", "Path cannot be resolved") from exc


def _read_source(path):
    try:
        return path.read_bytes()
    except FileNotFoundError as exc:
        raise ProjectError("source_not_found", "Subtitle file does not exist", {"path": str(path)}) from exc
    except OSError as exc:
        raise ProjectError("source_read_error", "Cannot read the subtitle file", {"path": str(path)}) from exc


def _receipt(connection, request_id, operation, payload_hash):
    row = connection.execute("SELECT * FROM requests WHERE request_id = ?", (request_id,)).fetchone()
    if row and (row["operation"] != operation or row["payload_hash"] != payload_hash):
        raise ProjectError("request_id_conflict", "request_id was already used with different input")
    return row


def _project(connection, project_id):
    if not isinstance(project_id, str) or not project_id:
        raise ProjectError("invalid_request", "project_id must be a non-empty string")
    row = connection.execute(
        """SELECT project_id, name, revision, context_revision, source_language,
           target_language, source_path, source_sha256, source_encoding, source_newline,
           created_at, length(original_source) AS source_byte_count,
           (SELECT count(*) FROM entries e WHERE e.project_id = projects.project_id) AS entry_count
           FROM projects WHERE project_id = ?""", (project_id,),
    ).fetchone()
    if row is None:
        raise ProjectError("project_not_found", "Project does not exist", {"project_id": project_id})
    return dict(row)


def _diagnostics(connection, project_id):
    rows = connection.execute(
        "SELECT code, severity, block, line, message FROM diagnostics WHERE project_id = ? ORDER BY rowid",
        (project_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _atomic_create(path, raw):
    """Publish a complete new file without overwriting an existing destination."""
    staging = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix=".sa-export-", suffix=".tmp", dir=path.parent, delete=False) as handle:
            staging = Path(handle.name)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        # Windows rename is atomic and refuses an existing destination. Hard links
        # are prohibited in some Windows sandboxes. POSIX rename would overwrite,
        # so there we use same-filesystem, atomic, no-clobber hard-link publication.
        if os.name == "nt":
            os.rename(staging, path)
        else:
            os.link(staging, path)
    except FileExistsError as exc:
        raise ProjectError("output_exists", "Output already exists; choose a new path", {"path": str(path)}) from exc
    except OSError as exc:
        raise ProjectError("export_write_error", "Cannot atomically create the output file", {"path": str(path)}) from exc
    finally:
        if staging is not None:
            staging.unlink(missing_ok=True)
