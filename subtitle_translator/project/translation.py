"""External-agent translation operations, with immutable timing anchors."""

import json
import sqlite3
import time
import uuid

from .common import _hash, _json, _now, _page, _project, _receipt, _request_id
from .errors import ProjectError
from .grouping import profiles, translation_units, validate_mapping
from .srt import MAX_INTEGER, parse_source, render_source
from .store import SCHEMA_VERSION, TRANSLATION_SCHEMA

FINAL = {"translated", "intentionally_preserved"}
REVIEWED = {"agent_reviewed", "human_reviewed"}


def _require(request, required, optional=()):
    if not isinstance(request, dict) or set(request) - set(required) - set(optional) or set(required) - set(request):
        raise ProjectError("invalid_request", "Request contains missing or unsupported fields", {"required": list(required)})


def _revision(project, value):
    if isinstance(value, bool) or not isinstance(value, int) or value != project["revision"]:
        raise ProjectError("revision_conflict", "Project revision does not match", {"current_revision": project["revision"]})


def _actor(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 80:
        raise ProjectError("invalid_request", "actor must be a non-empty label (max 80 characters)")
    return value


def _entries(connection, project_id):
    return [dict(row) for row in connection.execute(
        """SELECT e.*, t.text AS target_text, t.state AS translation_state,
           t.review_state, t.protected, t.source_revision AS translated_source_revision,
           t.timing_revision AS translated_timing_revision, t.context_revision AS translated_context_revision
           FROM entries e LEFT JOIN translations t ON t.entry_id=e.entry_id
           WHERE e.project_id=? ORDER BY e.ordinal""", (project_id,),
    )]


def _final(entry, context_revision):
    return (entry.get("translation_state") in FINAL and entry.get("review_state") in REVIEWED
            and entry.get("translated_source_revision") == entry["source_revision"]
            and entry.get("translated_timing_revision") == entry["timing_revision"]
            and entry.get("translated_context_revision") == context_revision)


def _public_entry(entry):
    return {key: entry.get(key) for key in (
        "entry_id", "ordinal", "source_index", "source_text", "start_ms", "end_ms",
        "source_revision", "timing_revision", "target_text", "translation_state", "review_state", "protected",
    )}


def _advance(connection, project_id):
    connection.execute("UPDATE projects SET revision=revision+1 WHERE project_id=?", (project_id,))
    connection.execute("UPDATE batches SET state='stale' WHERE project_id=? AND state='prepared'", (project_id,))
    connection.execute("UPDATE jobs SET batch_id=NULL WHERE project_id=?", (project_id,))
    return _project(connection, project_id)["revision"]


def _put_translation(connection, entry, text, state, review, actor, protected, context_revision):
    connection.execute(
        """INSERT INTO translations VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
           ON CONFLICT(entry_id) DO UPDATE SET text=excluded.text, state=excluded.state,
           review_state=excluded.review_state, actor=excluded.actor, protected=excluded.protected,
           revision=translations.revision+1, source_revision=excluded.source_revision,
           timing_revision=excluded.timing_revision, context_revision=excluded.context_revision,
           updated_at=excluded.updated_at""",
        (entry["entry_id"], text, state, review, actor, int(protected), entry["source_revision"],
         entry["timing_revision"], context_revision, _now()),
    )


def _safe_text(entry, text):
    if not isinstance(text, str) or not text.strip():
        raise ProjectError("invalid_translation", "Subtitle text must not be empty")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    probe = parse_source(render_source([{**entry, "source_text": text}]))
    if probe.errors or len(probe.entries) != 1 or probe.entries[0].text != text:
        raise ProjectError("invalid_translation", "Text would alter SRT block structure")
    return text


class TranslationOperations:
    def _target_bytes(self, connection, project):
        from ..formatting import format_subtitle_texts
        if connection.execute("PRAGMA user_version").fetchone()[0] < 2:
            raise ProjectError("workspace_migration_required", "Target export needs schema 2")
        entries = _entries(connection, project["project_id"])
        remaining = [e["entry_id"] for e in entries if not _final(e, project["context_revision"])]
        if remaining:
            raise ProjectError("translation_incomplete", "Target export requires reviewed translations for every timed entry", {"remaining": len(remaining), "entry_ids": remaining[:20]})
        for unit in translation_units(project["project_id"], [_public_entry(e) for e in entries]):
            validate_mapping(unit, [{"entry_id": e["entry_id"], "text": e["target_text"]} for e in unit["source_entries"]])
        texts = format_subtitle_texts([e["target_text"] for e in entries])
        return self._render_target(entries, texts)

    def _draft_bytes(self, connection, project):
        """Export partial work without changing its review state or timing anchors."""
        from ..formatting import format_subtitle_texts
        if connection.execute("PRAGMA user_version").fetchone()[0] < 2:
            raise ProjectError("workspace_migration_required", "Draft export needs schema 2")
        entries = _entries(connection, project["project_id"])
        pending, texts, mapping_issues, mapping_ids = [], [], [], set()
        for unit in translation_units(project["project_id"], [_public_entry(e) for e in entries]):
            if all(e["target_text"] for e in unit["source_entries"]):
                try:
                    validate_mapping(unit, [{"entry_id": e["entry_id"], "text": e["target_text"]}
                                            for e in unit["source_entries"]])
                except ProjectError as exc:
                    ids = [e["entry_id"] for e in unit["source_entries"]]
                    mapping_issues.append({"unit_id": unit["unit_id"], "entry_ids": ids,
                                           "code": exc.code, "message": str(exc)})
                    mapping_ids.update(ids)
        for entry in entries:
            text = entry["target_text"]
            missing = not text or not text.strip()
            if missing or not _final(entry, project["context_revision"]) or entry["entry_id"] in mapping_ids:
                stale = not missing and (
                    entry["translated_source_revision"] != entry["source_revision"]
                    or entry["translated_timing_revision"] != entry["timing_revision"]
                    or entry["translated_context_revision"] != project["context_revision"])
                reason = ("missing_translation" if missing else "stale_translation" if stale
                          else "formatting_review" if entry["entry_id"] in mapping_ids else "review_required")
                marker = {"missing_translation": "[NINCS FORDÍTÁS]",
                          "stale_translation": "[ELAVULT FORDÍTÁS]",
                          "review_required": "[ELLENŐRIZENDŐ]",
                          "formatting_review": "[ELLENŐRIZENDŐ]"}[reason]
                pending.append({key: entry[key] for key in (
                    "entry_id", "ordinal", "source_index", "start_ms", "end_ms",
                    "translation_state", "review_state")})
                pending[-1].update(reason=reason, marker=marker,
                                   text_origin="source" if missing else "target")
                text = marker + "\n" + (entry["source_text"] if missing else text)
            texts.append(text)
        report = {"format": "subtitle-assistant-draft-v1", "project_id": project["project_id"],
                  "revision": project["revision"], "entry_count": len(entries),
                  "pending_count": len(pending),
                  "missing_count": sum(e["reason"] == "missing_translation" for e in pending),
                  "entries": pending, "formatting_issues": mapping_issues}
        # Unfinished wording/tag/speaker mappings are allowed in a draft. SRT block
        # structure and exact source index/start/end anchors are still mandatory.
        raw = self._render_target(entries, format_subtitle_texts(texts))
        return raw, report

    @staticmethod
    def _render_target(entries, texts):
        target = [{**entry, "source_text": text} for entry, text in zip(entries, texts)]
        raw = render_source(target)
        parsed = parse_source(raw)
        if parsed.errors or len(parsed.entries) != len(entries):
            raise ProjectError("invalid_translation", "Formatted target cannot be safely exported")
        for source, result in zip(entries, parsed.entries):
            if (source["source_index"], source["start_ms"], source["end_ms"]) != (result.source_index, result.start_ms, result.end_ms):
                raise ProjectError("timing_anchor_changed", "Target formatting changed a timing anchor")
        return raw

    def _mutate(self, operation, request, action):
        if not isinstance(request, dict):
            raise ProjectError("invalid_request", "A JSON object is required")
        request = dict(request)
        request_id = _request_id(request.get("request_id"))
        request["request_id"] = request_id
        fingerprint = _hash(_json(request).encode("utf-8"))
        with self.store.connect(require_version=2) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            prior = _receipt(connection, request_id, operation, fingerprint)
            if prior:
                return {**json.loads(prior["result_json"]), "request_id": request_id, "replayed": True}
            result = action(connection, request)
            connection.execute("INSERT INTO requests VALUES (?, ?, ?, 'completed', ?, ?)",
                               (request_id, operation, fingerprint, _json(result), _now()))
        return {**result, "request_id": request_id, "replayed": False}

    def migrate_workspace(self, expected_version=1):
        if type(expected_version) is not int or expected_version != 1:
            raise ProjectError("invalid_request", "The supported migration is schema 1 to 2")
        with self.store.connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version == SCHEMA_VERSION:
                return {"schema_version": version, "migrated": False}
            if version != expected_version:
                raise ProjectError("revision_conflict", "Workspace schema changed")
            backup = self.store.root / "before-schema-v1.sqlite3"
            if backup.exists():
                raise ProjectError("migration_backup_exists", "Existing backup will not be overwritten", {"path": str(backup)})
            # backup() includes any WAL content. Exclusive creation protects an owner file.
            with backup.open("xb"):
                pass
            destination = sqlite3.connect(backup)
            try:
                connection.backup(destination)
            finally:
                destination.close()
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                if connection.execute("PRAGMA user_version").fetchone()[0] != expected_version:
                    raise ProjectError("revision_conflict", "Workspace schema changed during backup")
                for statement in TRANSLATION_SCHEMA:
                    connection.execute(statement)
                connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        return {"schema_version": SCHEMA_VERSION, "migrated": True, "backup": str(backup)}

    def prepare_batch(self, request):
        def action(connection, req):
            _require(req, ("request_id", "project_id", "expected_project_revision"),
                     ("max_chars", "context_before", "context_after", "actor"))
            project = _project(connection, req["project_id"])
            _revision(project, req["expected_project_revision"])
            actor = _actor(req.get("actor", "agent"))
            budget = req.get("max_chars", 6000)
            before, after = req.get("context_before", 2), req.get("context_after", 2)
            if isinstance(budget, bool) or not isinstance(budget, int) or not 100 <= budget <= 50000:
                raise ProjectError("invalid_request", "max_chars must be between 100 and 50000")
            if any(isinstance(n, bool) or not isinstance(n, int) or not 0 <= n <= 10 for n in (before, after)):
                raise ProjectError("invalid_request", "Context entry counts must be between 0 and 10")
            job = connection.execute("SELECT * FROM jobs WHERE project_id=?", (project["project_id"],)).fetchone()
            if job and job["state"] in ("pause_requested", "paused", "cancelled"):
                raise ProjectError("job_not_running", "Resume the project job before requesting a new batch", {"state": job["state"]})
            if job and job["batch_id"]:
                raise ProjectError("batch_already_prepared", "Fetch or cancel the active batch first", {"batch_id": job["batch_id"]})
            entries = _entries(connection, project["project_id"])
            units = translation_units(project["project_id"], [_public_entry(e) for e in entries])
            selected, used = [], 0
            lookup = {entry["entry_id"]: entry for entry in entries}
            for unit in units:
                pending = [lookup[entry_id] for entry_id in unit["entry_ids"]
                           if not _final(lookup[entry_id], project["context_revision"])
                           and not lookup[entry_id].get("protected")]
                if not pending:
                    continue
                errors = [error for profile in unit["formatting"] for error in profile["errors"]]
                if errors:
                    raise ProjectError("source_formatting_requires_review", "Source markup needs review before translation", {"issues": errors, "unit_id": unit["unit_id"]})
                size = sum(len(e["source_text"]) for e in unit["source_entries"])
                if not selected and size > budget:
                    raise ProjectError("unit_too_large", "Increase the budget; a translation unit will not be cut", {"unit_id": unit["unit_id"], "source_chars": size})
                if used + size > budget:
                    break
                unit["writable_entry_ids"] = [e["entry_id"] for e in unit["source_entries"] if not lookup[e["entry_id"]].get("protected")]
                unit_first = unit["source_entries"][0]["ordinal"] - 1
                unit_last = unit["source_entries"][-1]["ordinal"]
                unit["context_before"] = [_public_entry(e) for e in entries[max(0, unit_first-before):unit_first]]
                unit["context_after"] = [_public_entry(e) for e in entries[unit_last:unit_last+after]]
                selected.append(unit)
                used += size
            if not selected:
                return {"batch": None, "complete": all(_final(e, project["context_revision"]) for e in entries),
                        "remaining": sum(not _final(e, project["context_revision"]) for e in entries)}
            batch_id = "batch_" + uuid.uuid4().hex
            first = selected[0]["source_entries"][0]["ordinal"] - 1
            last = selected[-1]["source_entries"][-1]["ordinal"]
            payload = {"batch_id": batch_id, "project_id": project["project_id"],
                       "expected_project_revision": project["revision"], "context_revision": project["context_revision"],
                       "source_sha256": project["source_sha256"], "units": selected,
                       "context_before": [_public_entry(e) for e in entries[max(0, first-before):first]],
                       "context_after": [_public_entry(e) for e in entries[last:last+after]],
                       "state": "prepared", "source_chars": used}
            connection.execute("INSERT INTO batches VALUES (?, ?, ?, ?, ?, 'prepared', ?)",
                               (batch_id, project["project_id"], project["revision"], project["context_revision"], _json(payload), _now()))
            connection.execute(
                """INSERT INTO jobs VALUES (?, 'running', ?, 'translating', ?, ?, 120, 1)
                   ON CONFLICT(project_id) DO UPDATE SET state='running', agent_label=excluded.agent_label,
                   phase='translating', batch_id=excluded.batch_id, last_seen=excluded.last_seen,
                   activity_revision=jobs.activity_revision+1""",
                (project["project_id"], actor, batch_id, time.time()),
            )
            return {"batch": payload}
        return self._mutate("batch.prepare", request, action)

    def get_batch(self, batch_id):
        with self.store.connect(require_version=2) as connection:
            row = connection.execute("SELECT * FROM batches WHERE batch_id=?", (batch_id,)).fetchone()
            if row is None:
                raise ProjectError("batch_not_found", "Batch does not exist")
            payload = json.loads(row["payload_json"])
            payload["state"] = row["state"]
            return {"batch": payload}

    def submit_batch(self, request):
        def action(connection, req):
            _require(req, ("request_id", "batch_id", "expected_project_revision", "source_sha256", "context_revision", "translations"), ("actor",))
            row = connection.execute("SELECT * FROM batches WHERE batch_id=?", (req["batch_id"],)).fetchone()
            if row is None:
                raise ProjectError("batch_not_found", "Batch does not exist")
            project = _project(connection, row["project_id"])
            _revision(project, req["expected_project_revision"])
            if row["state"] != "prepared" or row["project_revision"] != project["revision"]:
                raise ProjectError("batch_stale", "Batch must be prepared again")
            if req["source_sha256"] != project["source_sha256"] or req["context_revision"] != project["context_revision"]:
                raise ProjectError("batch_stale", "Source or context version does not match")
            job = connection.execute("SELECT * FROM jobs WHERE project_id=?", (project["project_id"],)).fetchone()
            if job and job["state"] in ("paused", "cancelled"):
                raise ProjectError("job_not_running", "The job no longer accepts this submission")
            actor = _actor(req.get("actor", "agent"))
            payload = json.loads(row["payload_json"])
            submitted = req["translations"]
            if not isinstance(submitted, list) or len(submitted) != len(payload["units"]):
                raise ProjectError("batch_incomplete", "Every translation unit must be returned exactly once")
            by_unit = {}
            for item in submitted:
                _require(item, ("unit_id", "entries"))
                if not isinstance(item["unit_id"], str):
                    raise ProjectError("invalid_request", "unit_id must be a string")
                if item["unit_id"] in by_unit:
                    raise ProjectError("duplicate_translation", "Duplicate unit_id")
                by_unit[item["unit_id"]] = item["entries"]
            if set(by_unit) != {u["unit_id"] for u in payload["units"]}:
                raise ProjectError("batch_incomplete", "Unknown or missing translation unit")
            all_entries = {e["entry_id"]: e for e in _entries(connection, project["project_id"])}
            changes, warnings = [], []
            for unit in payload["units"]:
                mapped = by_unit[unit["unit_id"]]
                if not isinstance(mapped, list):
                    raise ProjectError("invalid_request", "Unit entries must be an array")
                seen = set()
                for item in mapped:
                    _require(item, ("entry_id", "text", "state", "review_state"))
                    entry_id = item["entry_id"]
                    if not isinstance(entry_id, str):
                        raise ProjectError("invalid_request", "entry_id must be a string")
                    if entry_id in seen:
                        raise ProjectError("duplicate_translation", "Duplicate entry_id")
                    seen.add(entry_id)
                    if entry_id not in unit["writable_entry_ids"]:
                        raise ProjectError("unexpected_entry", "Entry is not writable in this unit")
                    if item["state"] not in ("translated", "draft", "intentionally_preserved", "needs_review") or item["review_state"] not in ("unchecked", "agent_reviewed", "human_reviewed"):
                        raise ProjectError("invalid_request", "Unsupported translation/review state")
                    entry = all_entries[entry_id]
                    if entry.get("protected"):
                        raise ProjectError("manual_edit_protected", "A manual target edit cannot be overwritten")
                    item = {**item, "text": _safe_text(entry, item["text"])}
                    if item["state"] in FINAL and item["review_state"] not in REVIEWED:
                        raise ProjectError("review_required", "Final translation needs an explicit review state")
                    if item["state"] == "intentionally_preserved" and profiles([item["text"]])[0]["plain"] != profiles([entry["source_text"]])[0]["plain"]:
                        raise ProjectError("invalid_translation", "Intentionally preserved text must match the source")
                    changes.append((entry, item))
                if seen != set(unit["writable_entry_ids"]):
                    raise ProjectError("batch_incomplete", "Missing timed entries; no padding or positional shift is allowed")
                warnings.extend(validate_mapping(unit, mapped))
            for entry, item in changes:
                _put_translation(connection, entry, item["text"], item["state"], item["review_state"], actor, False, project["context_revision"])
            updated_entries = {e["entry_id"]: e for e in _entries(connection, project["project_id"])}
            for entry, item in changes:
                connection.execute("INSERT INTO changes VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ("change_" + uuid.uuid4().hex, project["project_id"], entry["entry_id"], actor,
                     _json(entry), _json(updated_entries[entry["entry_id"]]), _now()))
            connection.execute("UPDATE batches SET state='submitted' WHERE batch_id=?", (row["batch_id"],))
            revision = _advance(connection, project["project_id"])
            remaining = sum(not _final(e, project["context_revision"]) for e in _entries(connection, project["project_id"]))
            state = "paused" if job and job["state"] == "pause_requested" else "pending" if remaining else "completed"
            connection.execute("UPDATE jobs SET state=?, phase=?, last_seen=? WHERE project_id=?",
                               (state, "finished" if not remaining else "waiting", time.time(), project["project_id"]))
            # These are application review warnings, not source-parser Diagnostic objects.
            return {"project_id": project["project_id"], "revision": revision, "submitted_entries": len(changes),
                    "remaining": remaining, "review_notes": warnings}
        return self._mutate("batch.submit", request, action)

    def _edit_action(self, connection, req):
        _require(req, ("request_id", "project_id", "entry_id", "expected_project_revision", "changes"), ("actor",))
        project = _project(connection, req["project_id"])
        _revision(project, req["expected_project_revision"])
        actor = _actor(req.get("actor", "human"))
        entries = _entries(connection, project["project_id"])
        entry = next((e for e in entries if e["entry_id"] == req["entry_id"]), None)
        if entry is None:
            raise ProjectError("entry_not_found", "Entry does not belong to this project")
        changes = req["changes"]
        allowed = {"source_text", "start_ms", "end_ms", "target_text", "protected", "review_state", "clear_target"}
        if not isinstance(changes, dict) or not changes or set(changes) - allowed:
            raise ProjectError("invalid_request", "Unsupported or empty entry changes")
        if "review_state" in changes and "target_text" not in changes:
            raise ProjectError("invalid_request", "Review change must include the target text being reviewed")
        if "clear_target" in changes and (changes["clear_target"] is not True or any(k in changes for k in ("target_text", "protected", "review_state"))):
            raise ProjectError("invalid_request", "clear_target must be true and cannot accompany target fields")
        before = dict(entry)
        working = {**entry, **{key: value for key, value in changes.items() if key in ("source_text", "start_ms", "end_ms")}}
        if any(isinstance(working[k], bool) or not isinstance(working[k], int) or not 0 <= working[k] <= MAX_INTEGER for k in ("start_ms", "end_ms")) or working["end_ms"] <= working["start_ms"]:
            raise ProjectError("invalid_timestamp", "Working timing must have 0 <= start < end in the supported range")
        working["source_text"] = _safe_text(working, working["source_text"])
        source_changed = working["source_text"] != entry["source_text"]
        timing_changed = (working["start_ms"], working["end_ms"]) != (entry["start_ms"], entry["end_ms"])
        working["source_revision"] += int(source_changed)
        working["timing_revision"] += int(timing_changed)
        connection.execute("UPDATE entries SET source_text=?, start_ms=?, end_ms=?, source_revision=?, timing_revision=? WHERE entry_id=?",
                           (working["source_text"], working["start_ms"], working["end_ms"], working["source_revision"], working["timing_revision"], entry["entry_id"]))
        if (source_changed or timing_changed) and entry.get("target_text") is not None:
            connection.execute("UPDATE translations SET state='needs_review', revision=revision+1 WHERE entry_id=?", (entry["entry_id"],))
        if changes.get("clear_target"):
            connection.execute("DELETE FROM translations WHERE entry_id=?", (entry["entry_id"],))
        elif "target_text" in changes:
            text = _safe_text(working, changes["target_text"])
            review = changes.get("review_state", "unchecked")
            if review not in ("unchecked", "agent_reviewed", "human_reviewed"):
                raise ProjectError("invalid_request", "Unknown review state")
            protect = changes.get("protected", True)
            if not isinstance(protect, bool):
                raise ProjectError("invalid_request", "protected must be boolean")
            _put_translation(connection, working, text, "translated" if review in REVIEWED else "draft", review, actor, protect, project["context_revision"])
        elif "protected" in changes:
            if not isinstance(changes["protected"], bool) or entry.get("target_text") is None:
                raise ProjectError("invalid_request", "Protection change needs an existing target and a boolean")
            connection.execute("UPDATE translations SET protected=?, revision=revision+1 WHERE entry_id=?", (int(changes["protected"]), entry["entry_id"]))
        elif "review_state" in changes:
            raise ProjectError("invalid_request", "Review change must include the target text being reviewed")
        revision = _advance(connection, project["project_id"])
        updated = next(e for e in _entries(connection, project["project_id"]) if e["entry_id"] == entry["entry_id"])
        change_id = "change_" + uuid.uuid4().hex
        connection.execute("INSERT INTO changes VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (change_id, project["project_id"], entry["entry_id"], actor, _json(before), _json(updated), _now()))
        return {"project_id": project["project_id"], "revision": revision, "change_id": change_id,
                "entry": _public_entry(updated)}

    def edit_entry(self, request):
        return self._mutate("entry.edit", request, self._edit_action)

    def restore_entry(self, request):
        def action(connection, req):
            _require(req, ("request_id", "project_id", "change_id", "expected_project_revision"), ("actor",))
            project = _project(connection, req["project_id"])
            _revision(project, req["expected_project_revision"])
            change = connection.execute("SELECT * FROM changes WHERE change_id=? AND project_id=?", (req["change_id"], req["project_id"])).fetchone()
            if change is None:
                raise ProjectError("change_not_found", "Change does not belong to this project")
            before = json.loads(change["before_json"])
            changes = {key: before[key] for key in ("source_text", "start_ms", "end_ms")}
            if before.get("target_text") is None:
                changes["clear_target"] = True
            else:
                changes.update(target_text=before["target_text"], protected=bool(before["protected"]), review_state=before["review_state"])
            result = self._edit_action(connection, {"request_id": req["request_id"], "project_id": req["project_id"],
                                      "expected_project_revision": req["expected_project_revision"],
                                      "entry_id": before["entry_id"], "actor": req.get("actor", "human"), "changes": changes})
            # Restoring an already stale/draft translation is not a fresh review.
            if before.get("target_text") is not None and not _final(before, project["context_revision"]):
                connection.execute("UPDATE translations SET state='needs_review', review_state='unchecked' WHERE entry_id=?", (before["entry_id"],))
                restored = next(e for e in _entries(connection, req["project_id"]) if e["entry_id"] == before["entry_id"])
                connection.execute("UPDATE changes SET after_json=? WHERE change_id=?", (_json(restored), result["change_id"]))
                result["entry"] = _public_entry(restored)
            result["restored_change_id"] = req["change_id"]
            return result
        return self._mutate("entry.restore", request, action)

    def entry_history(self, project_id, entry_id):
        with self.store.connect(require_version=2) as connection:
            _project(connection, project_id)
            rows = connection.execute("SELECT change_id, actor, before_json, after_json, created_at FROM changes WHERE project_id=? AND entry_id=? ORDER BY rowid", (project_id, entry_id))
            return {"items": [{"change_id": r["change_id"], "actor": r["actor"], "before": json.loads(r["before_json"]), "after": json.loads(r["after_json"]), "created_at": r["created_at"]} for r in rows]}

    def job_activity(self, request):
        def action(connection, req):
            _require(req, ("request_id", "project_id", "agent_label", "phase"), ("batch_id", "ttl_seconds"))
            _project(connection, req["project_id"])
            actor = _actor(req["agent_label"])
            phase = req["phase"]
            if phase not in ("starting", "analyzing", "translating", "validating", "waiting", "paused", "finished", "failed"):
                raise ProjectError("invalid_request", "Unknown activity phase")
            ttl = req.get("ttl_seconds", 120)
            if isinstance(ttl, bool) or not isinstance(ttl, int) or not 10 <= ttl <= 600:
                raise ProjectError("invalid_request", "ttl_seconds must be between 10 and 600")
            job = connection.execute("SELECT * FROM jobs WHERE project_id=?", (req["project_id"],)).fetchone()
            if job and job["state"] == "cancelled":
                raise ProjectError("job_not_running", "Cancelled jobs need an explicit resume")
            state = job["state"] if job else "running"
            if req.get("batch_id") is not None:
                batch = connection.execute("SELECT project_id, state FROM batches WHERE batch_id=?", (req["batch_id"],)).fetchone()
                if not batch or batch["project_id"] != req["project_id"] or batch["state"] != "prepared":
                    raise ProjectError("batch_stale", "Activity references no active project batch")
            if phase in ("starting", "analyzing", "translating", "validating") and state not in ("pause_requested", "paused"):
                state = "running"
            if phase == "paused":
                state = "paused"
            elif phase == "failed" and state not in ("pause_requested", "paused"):
                state = "failed"
            elif phase == "finished" and state not in ("pause_requested", "paused"):
                project = _project(connection, req["project_id"])
                state = "completed" if all(_final(e, project["context_revision"]) for e in _entries(connection, req["project_id"])) else "pending"
            connection.execute(
                """INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                   ON CONFLICT(project_id) DO UPDATE SET state=excluded.state, agent_label=excluded.agent_label,
                   phase=excluded.phase, batch_id=COALESCE(excluded.batch_id, jobs.batch_id),
                   last_seen=excluded.last_seen, ttl_seconds=excluded.ttl_seconds,
                   activity_revision=jobs.activity_revision+1""",
                (req["project_id"], state, actor, phase, req.get("batch_id"), time.time(), ttl),
            )
            return {"project_id": req["project_id"], "state": state, "phase": phase}
        return self._mutate("job.activity", request, action)

    def control_job(self, request):
        def action(connection, req):
            _require(req, ("request_id", "project_id", "action"))
            _project(connection, req["project_id"])
            if req["action"] not in ("pause", "resume", "cancel"):
                raise ProjectError("invalid_request", "action must be pause, resume or cancel")
            job = connection.execute("SELECT * FROM jobs WHERE project_id=?", (req["project_id"],)).fetchone()
            if not job:
                connection.execute("INSERT INTO jobs VALUES (?, 'pending', '', 'waiting', NULL, NULL, 120, 0)", (req["project_id"],))
            state = {"pause": "pause_requested", "resume": "pending", "cancel": "cancelled"}[req["action"]]
            connection.execute("UPDATE jobs SET state=?, phase=CASE WHEN ?='resume' THEN 'waiting' ELSE phase END WHERE project_id=?", (state, req["action"], req["project_id"]))
            if req["action"] == "cancel":
                connection.execute("UPDATE batches SET state='cancelled' WHERE project_id=? AND state='prepared'", (req["project_id"],))
                connection.execute("UPDATE jobs SET batch_id=NULL WHERE project_id=?", (req["project_id"],))
            return {"project_id": req["project_id"], "state": state}
        return self._mutate("job.control", request, action)

    def job_status(self, project_id):
        with self.store.connect(require_version=2) as connection:
            project = _project(connection, project_id)
            row = connection.execute("SELECT * FROM jobs WHERE project_id=?", (project_id,)).fetchone()
            result = dict(row) if row else {"project_id": project_id, "state": "pending", "agent_label": "", "phase": "waiting", "batch_id": None, "last_seen": None, "ttl_seconds": 120, "activity_revision": 0}
            result["freshness"] = "unknown" if result["last_seen"] is None else "fresh" if time.time() - result["last_seen"] <= result["ttl_seconds"] else "stale"
            entries = _entries(connection, project_id)
            result["completed_entries"] = sum(_final(e, project["context_revision"]) for e in entries)
            result["total_entries"] = len(entries)
            result["project_revision"] = project["revision"]
            return result

    def translation_issues(self, project_id, limit=50, cursor=None):
        offset = _page(limit, cursor)
        with self.store.connect(require_version=2) as connection:
            project = _project(connection, project_id)
            issues = []
            for entry in _entries(connection, project_id):
                if not _final(entry, project["context_revision"]):
                    issues.append({"entry_id": entry["entry_id"], "code": "untranslated" if entry["target_text"] is None else "translation_needs_review",
                                   "protected": bool(entry["protected"]), "state": entry["translation_state"]})
            return {"items": issues[offset:offset+limit], "total": len(issues),
                    "next_cursor": str(offset+limit) if offset+limit < len(issues) else None}
