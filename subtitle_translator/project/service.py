"""Model-free application operations used by the CLI and API/GUI."""

import json
import uuid
from .errors import ProjectError
from .srt import parse_source, render_source
from .store import SCHEMA_VERSION, WorkspaceStore
from .common import (API_VERSION, _now, _json, _hash, _request_id, _page, _path,
                     _read_source, _receipt, _project, _diagnostics, _atomic_create)
from .translation import TranslationOperations


class ProjectService(TranslationOperations):
    def __init__(self, workspace):
        self.store = WorkspaceStore(workspace)

    def capabilities(self):
        return {
            "api_version": API_VERSION,
            "schema_version": SCHEMA_VERSION,
            "workspace": str(self.store.root),
            "model_required": False,
            "operations": ["capabilities", "doctor", "project.import", "project.inspect",
                           "project.status", "project.list", "entry.list", "project.validate",
                           "project.export", "request.receipt", "workspace.migrate", "batch.prepare",
                           "batch.get", "batch.submit", "entry.edit", "entry.history", "job.activity",
                           "entry.restore", "job.status", "job.control", "issue.list"],
            "export_variants": ["source", "original", "target", "draft"],
            "features": {"http_api": True, "translation": "external_agent", "editing": True,
                         "oauth": False, "gui": True},
        }

    def doctor(self):
        exists = self.store.database.exists()
        version = None
        if exists:
            with self.store.connect() as connection:
                version = connection.execute("PRAGMA user_version").fetchone()[0]
        return {"workspace": str(self.store.root), "workspace_exists": exists,
                "schema_version": version, "latest_schema_version": SCHEMA_VERSION,
                "migration_required": exists and version < SCHEMA_VERSION,
                "model_required": False, "ready": True}

    def inspect_source(self, input_path, encoding=None):
        path = _path(input_path)
        parsed = parse_source(_read_source(path), encoding)
        return {"path": str(path), "inspection": parsed.report()}

    def import_project(self, input_path, source_language="en", target_language="hu",
                       name=None, encoding=None, request_id=None):
        if name is not None and not isinstance(name, str):
            raise ProjectError("invalid_request", "name must be a string")
        if encoding is not None and not isinstance(encoding, str):
            raise ProjectError("invalid_request", "encoding must be a string")
        for value in (source_language, target_language):
            if not isinstance(value, str) or not value.strip() or len(value) > 32:
                raise ProjectError("invalid_language", "Language must be a non-empty code or name (max 32 characters)")
        path = _path(input_path)
        parsed = parse_source(_read_source(path), encoding)
        if parsed.errors:
            raise ProjectError("invalid_subtitle", "Import refused: malformed blocks would cause source loss", {
                "inspection": parsed.report(),
            })
        request_id = _request_id(request_id)
        payload = {"input_path": str(path), "source_sha256": parsed.sha256, "name": name,
                   "source_language": source_language, "target_language": target_language,
                   "encoding": encoding}
        payload_hash = _hash(_json(payload).encode("utf-8"))
        with self.store.connect(create=True) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            previous = _receipt(connection, request_id, "project.import", payload_hash)
            if previous:
                return {**json.loads(previous["result_json"]), "request_id": request_id, "replayed": True}
            project_id = "prj_" + uuid.uuid4().hex
            connection.execute(
                "INSERT INTO projects VALUES (?, ?, 1, 0, ?, ?, ?, ?, ?, ?, ?, ?)",
                (project_id, name if name is not None else path.stem, source_language,
                 target_language, str(path), parsed.sha256, parsed.encoding, parsed.newline,
                 parsed.raw, _now()),
            )
            connection.executemany(
                "INSERT INTO entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1)",
                [(f"{project_id}:entry:{entry.ordinal:06d}", project_id, entry.ordinal,
                  entry.source_index, entry.source_line, entry.text, entry.start_ms,
                  entry.end_ms, entry.text, entry.start_ms, entry.end_ms)
                 for entry in parsed.entries],
            )
            connection.executemany("INSERT INTO diagnostics VALUES (?, ?, ?, ?, ?, ?)", [
                (project_id, d.code, d.severity, d.block, d.line, d.message) for d in parsed.diagnostics
            ])
            result = {"project": _project(connection, project_id), "inspection": parsed.report(),
                      "warnings": [d.to_dict() for d in parsed.diagnostics[:100]]}
            connection.execute("INSERT INTO requests VALUES (?, ?, ?, 'completed', ?, ?)",
                               (request_id, "project.import", payload_hash, _json(result), _now()))
        return {**result, "request_id": request_id, "replayed": False}

    def status(self, project_id):
        with self.store.connect() as connection:
            project = _project(connection, project_id)
            diagnostics = _diagnostics(connection, project_id)
            counts = {"untranslated": project["entry_count"]}
            if connection.execute("PRAGMA user_version").fetchone()[0] >= 2:
                from .translation import _entries, _final
                counts = {}
                for entry in _entries(connection, project_id):
                    state = entry["translation_state"] or "untranslated"
                    if entry["target_text"] is not None and not _final(entry, project["context_revision"]):
                        state = "needs_review"
                    counts[state] = counts.get(state, 0) + 1
            return {"project": project, "diagnostics": diagnostics[:100],
                    "diagnostics_truncated": len(diagnostics) > 100,
                    "translation_counts": counts}

    def list_projects(self, limit=50, cursor=None):
        offset = _page(limit, cursor)
        if not self.store.database.exists():
            return {"items": [], "next_cursor": None, "total": 0}
        with self.store.connect() as connection:
            total = connection.execute("SELECT count(*) FROM projects").fetchone()[0]
            ids = connection.execute("SELECT project_id FROM projects ORDER BY created_at, project_id LIMIT ? OFFSET ?",
                                     (limit, offset)).fetchall()
            return {"items": [_project(connection, row[0]) for row in ids], "total": total,
                    "next_cursor": str(offset + len(ids)) if offset + len(ids) < total else None}

    def list_entries(self, project_id, limit=50, cursor=None):
        offset = _page(limit, cursor)
        with self.store.connect() as connection:
            project = _project(connection, project_id)
            rows = connection.execute(
                """SELECT entry_id, ordinal, source_index, source_line, source_text,
                   start_ms, end_ms, source_revision, timing_revision
                   FROM entries WHERE project_id = ? AND ordinal > ? ORDER BY ordinal LIMIT ?""",
                (project_id, offset, limit + 1),
            ).fetchall()
            items = [dict(row) for row in rows[:limit]]
            if connection.execute("PRAGMA user_version").fetchone()[0] >= 2:
                for item in items:
                    target = connection.execute("SELECT text, state, review_state, protected FROM translations WHERE entry_id=?", (item["entry_id"],)).fetchone()
                    item["target"] = dict(target) if target else None
            return {"project_id": project_id, "revision": project["revision"],
                    "items": items, "total": project["entry_count"],
                    "next_cursor": str(items[-1]["ordinal"]) if len(rows) > limit else None}

    def _source_data(self, connection, project_id):
        project = _project(connection, project_id)
        raw = connection.execute("SELECT original_source FROM projects WHERE project_id = ?", (project_id,)).fetchone()[0]
        entries = [dict(row) for row in connection.execute(
            "SELECT * FROM entries WHERE project_id = ? ORDER BY ordinal", (project_id,),
        )]
        if _hash(raw) != project["source_sha256"]:
            raise ProjectError("source_integrity_error", "Archived source hash does not match the imported source")
        parsed = parse_source(raw, project["source_encoding"])
        if parsed.errors or len(parsed.entries) != len(entries):
            raise ProjectError("project_integrity_error", "Stored entries do not match the archived source")
        for stored, original in zip(entries, parsed.entries):
            fields = ("ordinal", "source_index", "source_line")
            if (any(stored[key] != getattr(original, key) for key in fields)
                    or stored["original_text"] != original.text
                    or stored["original_start_ms"] != original.start_ms
                    or stored["original_end_ms"] != original.end_ms):
                raise ProjectError("project_integrity_error", "Original entry identity or content has changed")
        return project, raw, entries

    def validate(self, project_id):
        with self.store.connect() as connection:
            project, raw, entries = self._source_data(connection, project_id)
            exported = parse_source(render_source(entries))
            if exported.errors or len(exported.entries) != len(entries):
                raise ProjectError("project_integrity_error", "Working source cannot be safely exported")
            for stored, rendered in zip(entries, exported.entries):
                if (stored["source_index"], stored["start_ms"], stored["end_ms"], stored["source_text"]) != (
                        rendered.source_index, rendered.start_ms, rendered.end_ms, rendered.text):
                    raise ProjectError("project_integrity_error", "Source export would alter entry content or times")
            result = {"project_id": project_id, "revision": project["revision"], "valid": True,
                    "entry_count": len(entries), "source_sha256": _hash(raw),
                    "checks": ["archived_bytes", "original_entries", "source_export_mapping"],
                    "warnings": _diagnostics(connection, project_id)[:100]}
            if connection.execute("PRAGMA user_version").fetchone()[0] >= 2:
                try:
                    self._target_bytes(connection, project)
                    result["target_ready"] = True
                    result["checks"].append("target_export_mapping")
                except ProjectError as exc:
                    result["target_ready"] = False
                    result["target_issue"] = exc.to_dict()
            return result

    def export_project(self, project_id, output_path, variant="source", expected_revision=None, request_id=None):
        if variant not in ("source", "original", "target", "draft"):
            raise ProjectError("unsupported_export_variant", "Unknown export variant")
        output = _path(output_path)
        request_id = _request_id(request_id)
        payload = {"project_id": project_id, "output_path": str(output), "variant": variant,
                   "expected_revision": expected_revision}
        payload_hash = _hash(_json(payload).encode("utf-8"))
        with self.store.connect() as connection:
            # Reserve the exact operation before touching the filesystem. A pending
            # operation can be reconciled after publication but before receipt commit.
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                previous = _receipt(connection, request_id, "project.export", payload_hash)
                if previous and previous["state"] == "completed":
                    result = json.loads(previous["result_json"])
                    if not output.is_file() or _hash(output.read_bytes()) != result["sha256"]:
                        raise ProjectError("export_output_changed", "Completed export is missing or has changed; choose a new request and output")
                    return {**result, "request_id": request_id, "replayed": True}
                if previous and output.is_file():
                    result = json.loads(previous["result_json"])
                    if _hash(output.read_bytes()) == result["sha256"]:
                        # Publication already succeeded for this exact request.
                        # Reconcile its saved snapshot even if editing continued.
                        connection.execute("UPDATE requests SET state='completed' WHERE request_id = ?", (request_id,))
                        return {**result, "request_id": request_id, "replayed": True}
                project, original, entries = self._source_data(connection, project_id)
                if expected_revision is not None and (isinstance(expected_revision, bool)
                        or not isinstance(expected_revision, int) or expected_revision != project["revision"]):
                    raise ProjectError("revision_conflict", "Project revision does not match", {"current_revision": project["revision"]})
                if output == _path(project["source_path"]):
                    raise ProjectError("source_overwrite_refused", "Cannot export over the imported source path")
                # Validate canonical export before reserving or publishing it.
                self.validate(project_id)
                draft = None
                if variant == "draft":
                    raw, draft = self._draft_bytes(connection, project)
                else:
                    raw = (original if variant == "original" else self._target_bytes(connection, project)
                           if variant == "target" else render_source(entries))
                result = {"project_id": project_id, "revision": project["revision"], "variant": variant,
                          "path": str(output), "sha256": _hash(raw), "byte_count": len(raw),
                          "entry_count": len(entries)}
                if draft is not None:
                    result["draft"] = draft
                if previous:
                    if json.loads(previous["result_json"]) != result:
                        raise ProjectError("revision_conflict", "Pending export no longer matches the current project")
                else:
                    if output.exists():
                        raise ProjectError("output_exists", "Output already exists; choose a new path", {"path": str(output)})
                    connection.execute("INSERT INTO requests VALUES (?, ?, ?, 'pending', ?, ?)",
                                       (request_id, "project.export", payload_hash, _json(result), _now()))
            if previous and output.is_file():
                if _hash(output.read_bytes()) != result["sha256"]:
                    raise ProjectError("output_exists", "Pending export destination has different content")
            else:
                _atomic_create(output, raw)
            with connection:
                connection.execute("UPDATE requests SET state='completed' WHERE request_id = ?", (request_id,))
            return {**result, "request_id": request_id, "replayed": previous is not None}

    def receipt(self, request_id):
        request_id = _request_id(request_id)
        with self.store.connect() as connection:
            row = connection.execute("SELECT * FROM requests WHERE request_id = ?", (request_id,)).fetchone()
            if row is None:
                raise ProjectError("request_not_found", "No receipt exists for this request")
            return {"request_id": request_id, "operation": row["operation"], "state": row["state"],
                    "result": json.loads(row["result_json"])}
