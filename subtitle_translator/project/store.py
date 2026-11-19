"""SQLite workspace, schema ownership and transaction boundaries."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3

from .errors import ProjectError

SCHEMA_VERSION = 2
APPLICATION_ID = 0x53554241

SCHEMA = (
    """CREATE TABLE projects (
        project_id TEXT PRIMARY KEY, name TEXT NOT NULL, revision INTEGER NOT NULL,
        context_revision INTEGER NOT NULL, source_language TEXT NOT NULL,
        target_language TEXT NOT NULL, source_path TEXT NOT NULL,
        source_sha256 TEXT NOT NULL, source_encoding TEXT NOT NULL,
        source_newline TEXT NOT NULL, original_source BLOB NOT NULL,
        created_at TEXT NOT NULL)""",
    """CREATE TABLE entries (
        entry_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(project_id),
        ordinal INTEGER NOT NULL, source_index INTEGER NOT NULL,
        source_line INTEGER NOT NULL, original_text TEXT NOT NULL,
        original_start_ms INTEGER NOT NULL, original_end_ms INTEGER NOT NULL,
        source_text TEXT NOT NULL, start_ms INTEGER NOT NULL, end_ms INTEGER NOT NULL,
        source_revision INTEGER NOT NULL, timing_revision INTEGER NOT NULL,
        UNIQUE(project_id, ordinal), CHECK(start_ms >= 0 AND end_ms > start_ms))""",
    """CREATE TABLE diagnostics (
        project_id TEXT NOT NULL REFERENCES projects(project_id),
        code TEXT NOT NULL, severity TEXT NOT NULL, block INTEGER NOT NULL,
        line INTEGER NOT NULL, message TEXT NOT NULL)""",
    """CREATE TABLE requests (
        request_id TEXT PRIMARY KEY, operation TEXT NOT NULL, payload_hash TEXT NOT NULL,
        state TEXT NOT NULL CHECK(state IN ('pending', 'completed')),
        result_json TEXT NOT NULL, created_at TEXT NOT NULL)""",
)

TRANSLATION_SCHEMA = (
    """CREATE TABLE translations (
        entry_id TEXT PRIMARY KEY REFERENCES entries(entry_id), text TEXT NOT NULL,
        state TEXT NOT NULL, review_state TEXT NOT NULL, actor TEXT NOT NULL,
        protected INTEGER NOT NULL DEFAULT 0, revision INTEGER NOT NULL,
        source_revision INTEGER NOT NULL, timing_revision INTEGER NOT NULL,
        context_revision INTEGER NOT NULL, updated_at TEXT NOT NULL)""",
    """CREATE TABLE batches (
        batch_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(project_id),
        project_revision INTEGER NOT NULL, context_revision INTEGER NOT NULL,
        payload_json TEXT NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL)""",
    """CREATE TABLE changes (
        change_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(project_id),
        entry_id TEXT NOT NULL REFERENCES entries(entry_id), actor TEXT NOT NULL,
        before_json TEXT NOT NULL, after_json TEXT NOT NULL, created_at TEXT NOT NULL)""",
    """CREATE TABLE jobs (
        project_id TEXT PRIMARY KEY REFERENCES projects(project_id), state TEXT NOT NULL,
        agent_label TEXT NOT NULL, phase TEXT NOT NULL, batch_id TEXT,
        last_seen REAL, ttl_seconds INTEGER NOT NULL DEFAULT 120,
        activity_revision INTEGER NOT NULL DEFAULT 0)""",
)


class WorkspaceStore:
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()
        self.database = self.root / "workspace.sqlite3"

    @contextmanager
    def connect(self, create=False, require_version=1):
        if not self.database.exists() and not create:
            raise ProjectError("workspace_not_found", "Workspace has not been created", {"workspace": str(self.root)})
        connection = None
        try:
            if create:
                self.root.mkdir(parents=True, exist_ok=True)
            # mode=rw prevents a read operation racing deletion from creating an empty DB.
            uri = self.database.as_uri() + ("?mode=rwc" if create else "?mode=rw")
            connection = sqlite3.connect(uri, uri=True, timeout=5)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            app_id = connection.execute("PRAGMA application_id").fetchone()[0]
            if version == 0 and app_id == 0 and create:
                connection.execute("BEGIN IMMEDIATE")
                # Another process may have initialized it while we waited for the lock.
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                app_id = connection.execute("PRAGMA application_id").fetchone()[0]
                if version == 0 and app_id == 0:
                    tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                    if tables:
                        raise ProjectError("invalid_workspace", "Refusing to initialize a database containing unrelated tables")
                    for statement in SCHEMA:
                        connection.execute(statement)
                    for statement in TRANSLATION_SCHEMA:
                        connection.execute(statement)
                    connection.execute(f"PRAGMA application_id = {APPLICATION_ID}")
                    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                    version, app_id = SCHEMA_VERSION, APPLICATION_ID
                connection.commit()
            if app_id != APPLICATION_ID:
                raise ProjectError("invalid_workspace", "Database is not a Subtitle Assistant workspace")
            if version not in (1, SCHEMA_VERSION):
                raise ProjectError("workspace_version_unsupported", "Workspace schema needs a supported migration", {
                    "found_version": version, "supported_version": SCHEMA_VERSION,
                })
            if version < require_version or (create and version < SCHEMA_VERSION):
                raise ProjectError("workspace_migration_required", "Explicit workspace migration is required", {
                    "found_version": version, "target_version": SCHEMA_VERSION,
                })
            if create:
                connection.execute("PRAGMA journal_mode = WAL")
            yield connection
        except sqlite3.Error as exc:
            code = "workspace_busy" if "locked" in str(exc).lower() else "workspace_error"
            raise ProjectError(code, "Cannot access the workspace database", {"workspace": str(self.root)}) from exc
        except OSError as exc:
            raise ProjectError("workspace_error", "Cannot access the workspace directory", {"workspace": str(self.root)}) from exc
        finally:
            if connection is not None:
                connection.close()
