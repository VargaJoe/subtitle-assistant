"""Persistence and CLI tests that run with Python's standard library only."""

import hashlib
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest import mock

from subtitle_translator.project.errors import ProjectError
from subtitle_translator.project.service import ProjectService
from subtitle_translator.project.srt import parse_source


SOURCE = ("\ufeff7\r\n00:00:01,001 --> 00:00:03,777\r\n"
          "<i> Köszönöm. </i>\r\n- Second line.\r\n\r\n"
          "7\r\n00:00:04,008 --> 00:00:05,999\r\n[DOOR CLOSES]\r\n\r\n"
          "9\r\n00:00:06,000 --> 00:00:08,002\r\nThird entry.\r\n").encode("utf-8")
ROOT = Path(__file__).resolve().parents[2]


def temporary_workspace():
    location = ROOT / "temp" / "m1-tests"
    location.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=location)


class ProjectServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = temporary_workspace()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.source = self.directory / "episode.eng.srt"
        self.source.write_bytes(SOURCE)
        self.workspace = self.directory / "workspace"
        self.service = ProjectService(self.workspace)

    def import_source(self, **kwargs):
        return self.service.import_project(self.source, **kwargs)

    def assert_error(self, code, call, *args, **kwargs):
        with self.assertRaises(ProjectError) as raised:
            call(*args, **kwargs)
        self.assertEqual(raised.exception.code, code)
        return raised.exception

    def test_persists_identity_source_and_diagnostics_across_reopen(self):
        result = self.import_source()
        project = result["project"]
        self.assertEqual(project["entry_count"], 3)
        self.assertEqual(project["revision"], 1)
        self.assertEqual(project["source_sha256"], hashlib.sha256(SOURCE).hexdigest())
        reopened = ProjectService(self.workspace)
        self.assertEqual(reopened.status(project["project_id"])["project"], project)
        first = reopened.list_entries(project["project_id"], limit=2)
        second = reopened.list_entries(project["project_id"], limit=2, cursor=first["next_cursor"])
        self.assertEqual([item["source_index"] for item in first["items"] + second["items"]], [7, 7, 9])
        self.assertEqual(len({item["entry_id"] for item in first["items"] + second["items"]}), 3)
        self.assertIsNone(second["next_cursor"])
        self.assertEqual(result["warnings"][0]["code"], "duplicate_index")
        self.assertTrue(reopened.validate(project["project_id"])["valid"])

    def test_bad_source_is_diagnosed_and_not_partially_imported(self):
        self.source.write_bytes(SOURCE + b"\n10\nnot a timestamp\nBad block\n")
        inspection = self.service.inspect_source(self.source)["inspection"]
        self.assertEqual(inspection["entry_count"], 3)
        self.assertEqual(inspection["error_count"], 1)
        self.assert_error("invalid_subtitle", self.import_source)
        self.assertFalse(self.workspace.exists())

    def test_missing_separator_with_valid_or_malformed_time_is_rejected(self):
        for time in ("00:00:03,003 --> 00:00:04,004", "00:00:03.003 --> 00:00:04.004"):
            with self.subTest(time=time):
                self.source.write_text("1\n00:00:01,001 --> 00:00:02,002\nHello.\n2\n" + time + "\nWorld.\n", encoding="utf-8")
                error = self.assert_error("invalid_subtitle", self.import_source)
                self.assertIn("missing_separator", [d["code"] for d in error.details["inspection"]["diagnostics"]])
                self.assertFalse(self.workspace.exists())

    def test_import_receipt_is_idempotent_but_rejects_changed_payload(self):
        request_id = str(uuid.uuid4())
        first = self.import_source(request_id=request_id)
        replay = ProjectService(self.workspace).import_project(self.source, request_id=request_id)
        self.assertTrue(replay["replayed"])
        self.assertEqual(first["project"], replay["project"])
        self.assertEqual(self.service.list_projects()["total"], 1)
        self.assertEqual(self.service.receipt(request_id)["state"], "completed")
        self.assert_error("request_id_conflict", self.import_source, request_id=request_id, name="Different")

    def test_different_imports_have_distinct_project_and_entry_ids(self):
        one, two = self.import_source(), self.import_source()
        self.assertNotEqual(one["project"]["project_id"], two["project"]["project_id"])
        one_id = self.service.list_entries(one["project"]["project_id"])["items"][0]["entry_id"]
        two_id = self.service.list_entries(two["project"]["project_id"])["items"][0]["entry_id"]
        self.assertNotEqual(one_id, two_id)

    def test_original_and_canonical_exports_preserve_source_after_source_disappears(self):
        project_id = self.import_source()["project"]["project_id"]
        self.source.unlink()
        original, canonical = self.directory / "original.srt", self.directory / "source.srt"
        self.service.export_project(project_id, original, variant="original")
        exported = self.service.export_project(project_id, canonical, expected_revision=1)
        self.assertEqual(original.read_bytes(), SOURCE)
        expected, actual = parse_source(SOURCE), parse_source(canonical.read_bytes())
        self.assertEqual(expected.entries, actual.entries)
        self.assertEqual(exported["sha256"], hashlib.sha256(canonical.read_bytes()).hexdigest())
        self.assertNotIn(b"\r", canonical.read_bytes())
        self.assertFalse(canonical.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_export_never_overwrites_source_or_existing_output(self):
        project_id = self.import_source()["project"]["project_id"]
        self.assert_error("source_overwrite_refused", self.service.export_project, project_id, self.source)
        output = self.directory / "existing.srt"
        output.write_bytes(b"owner data")
        self.assert_error("output_exists", self.service.export_project, project_id, output)
        self.assertEqual(output.read_bytes(), b"owner data")
        self.assertEqual(self.source.read_bytes(), SOURCE)

    def test_export_replay_and_pending_receipt_reconciliation(self):
        project_id = self.import_source()["project"]["project_id"]
        output, request_id = self.directory / "result.srt", str(uuid.uuid4())
        first = self.service.export_project(project_id, output, request_id=request_id)
        self.assertFalse(first["replayed"])
        replay = self.service.export_project(project_id, output, request_id=request_id)
        self.assertTrue(replay["replayed"])
        with closing(sqlite3.connect(self.service.store.database)) as connection, connection:
            connection.execute("UPDATE requests SET state='pending' WHERE request_id=?", (request_id,))
        recovered = self.service.export_project(project_id, output, request_id=request_id)
        self.assertTrue(recovered["replayed"])
        self.assertEqual(self.service.receipt(request_id)["state"], "completed")
        self.assertEqual(output.read_bytes(), parse_source(SOURCE).raw.decode("utf-8-sig").replace("\r\n", "\n").encode("utf-8"))

    def test_interruption_after_publication_is_reconciled_with_same_request(self):
        from subtitle_translator.project.service import _atomic_create
        project_id = self.import_source()["project"]["project_id"]
        request_id, output = str(uuid.uuid4()), self.directory / "interrupted.srt"

        def interrupted(path, raw):
            _atomic_create(path, raw)
            raise KeyboardInterrupt()

        with mock.patch("subtitle_translator.project.service._atomic_create", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.service.export_project(project_id, output, request_id=request_id)
        self.assertTrue(output.exists())
        self.assertEqual(self.service.receipt(request_id)["state"], "pending")
        self.assertTrue(self.service.export_project(project_id, output, request_id=request_id)["replayed"])
        self.assertEqual(self.service.receipt(request_id)["state"], "completed")

    def interrupt_export_after_publication(self, project_id, output, **options):
        from subtitle_translator.project.service import _atomic_create

        def interrupted(path, raw):
            _atomic_create(path, raw)
            raise KeyboardInterrupt()

        with mock.patch("subtitle_translator.project.service._atomic_create", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.service.export_project(project_id, output, **options)
        receipt = self.service.receipt(options["request_id"])
        self.assertEqual(receipt["state"], "pending")
        self.assertTrue(output.is_file())
        return receipt["result"]

    def test_pending_draft_publication_reconciles_saved_snapshot_after_manual_edits(self):
        for changes in ({"target_text": "A manual draft."}, {"source_text": "A changed source."},
                        {"start_ms": 6100, "end_ms": 8100}):
            for expected_revision in (1, None):
                with self.subTest(changes=changes, expected_revision=expected_revision):
                    project_id = self.import_source()["project"]["project_id"]
                    request_id = str(uuid.uuid4())
                    output = self.directory / (request_id + ".draft.srt")
                    options = {"variant": "draft", "expected_revision": expected_revision, "request_id": request_id}
                    saved = self.interrupt_export_after_publication(project_id, output, **options)
                    published = output.read_bytes()
                    entry_id = self.service.list_entries(project_id)["items"][-1]["entry_id"]
                    self.service.edit_entry({"project_id": project_id, "entry_id": entry_id,
                                             "expected_project_revision": 1, "changes": changes})
                    before = self.service.list_entries(project_id)
                    self.assert_error("request_id_conflict", self.service.export_project,
                                      project_id, output, **{**options, "variant": "source"})
                    recovered = ProjectService(self.workspace).export_project(project_id, output, **options)
                    self.assertEqual(recovered, {**saved, "request_id": request_id, "replayed": True})
                    receipt = self.service.receipt(request_id)
                    self.assertEqual(receipt["state"], "completed")
                    self.assertEqual(receipt["result"], saved)
                    self.assertEqual(receipt["result"]["draft"]["revision"], 1)
                    self.assertEqual(output.read_bytes(), published)
                    self.assertEqual(self.service.list_entries(project_id), before)
                    self.assertEqual(before["revision"], 2)
                    self.assertEqual(self.source.read_bytes(), SOURCE)

    def test_pending_draft_missing_or_changed_output_after_edit_stays_pending(self):
        for output_state in ("missing", "changed"):
            for expected_revision in (1, None):
                with self.subTest(output_state=output_state, expected_revision=expected_revision):
                    project_id = self.import_source()["project"]["project_id"]
                    request_id = str(uuid.uuid4())
                    output = self.directory / (request_id + ".draft.srt")
                    options = {"variant": "draft", "expected_revision": expected_revision, "request_id": request_id}
                    saved = self.interrupt_export_after_publication(project_id, output, **options)
                    if output_state == "missing":
                        output.unlink()
                    else:
                        output.write_bytes(b"owner changes")
                    entry_id = self.service.list_entries(project_id)["items"][-1]["entry_id"]
                    self.service.edit_entry({"project_id": project_id, "entry_id": entry_id,
                                             "expected_project_revision": 1,
                                             "changes": {"target_text": "A manual draft."}})
                    self.assert_error("revision_conflict", self.service.export_project,
                                      project_id, output, **options)
                    self.assertEqual(self.service.receipt(request_id)["state"], "pending")
                    self.assertEqual(self.service.receipt(request_id)["result"], saved)
                    if output_state == "missing":
                        self.assertFalse(output.exists())
                    else:
                        self.assertEqual(output.read_bytes(), b"owner changes")

    def test_pending_export_unchanged_snapshot_recovers_missing_but_not_changed_output(self):
        project_id = self.import_source()["project"]["project_id"]
        for output_state in ("missing", "changed"):
            with self.subTest(output_state=output_state):
                request_id = str(uuid.uuid4())
                output = self.directory / (request_id + ".srt")
                options = {"expected_revision": 1, "request_id": request_id}
                saved = self.interrupt_export_after_publication(project_id, output, **options)
                published = output.read_bytes()
                if output_state == "missing":
                    output.unlink()
                    recovered = self.service.export_project(project_id, output, **options)
                    self.assertEqual(recovered, {**saved, "request_id": request_id, "replayed": True})
                    self.assertEqual(output.read_bytes(), published)
                    self.assertEqual(self.service.receipt(request_id)["state"], "completed")
                else:
                    output.write_bytes(b"owner changes")
                    self.assert_error("output_exists", self.service.export_project,
                                      project_id, output, **options)
                    self.assertEqual(output.read_bytes(), b"owner changes")
                    self.assertEqual(self.service.receipt(request_id)["state"], "pending")

    def test_failed_import_rolls_back_project_entries_and_receipt(self):
        self.import_source()
        with closing(sqlite3.connect(self.service.store.database)) as connection, connection:
            connection.execute("CREATE TRIGGER fail_entry BEFORE INSERT ON entries BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        self.assert_error("workspace_error", self.import_source)
        with closing(sqlite3.connect(self.service.store.database)) as connection:
            counts = [connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in ("projects", "entries", "requests")]
        self.assertEqual(counts, [1, 3, 1])

    def test_changed_completed_export_is_not_silently_recreated(self):
        project_id = self.import_source()["project"]["project_id"]
        output, request_id = self.directory / "result.srt", str(uuid.uuid4())
        self.service.export_project(project_id, output, request_id=request_id)
        output.write_bytes(b"manually changed")
        self.assert_error("export_output_changed", self.service.export_project, project_id, output, request_id=request_id)
        self.assertEqual(output.read_bytes(), b"manually changed")

    def test_export_stale_revision_and_target_variant_rejected(self):
        project_id = self.import_source()["project"]["project_id"]
        output = self.directory / "out.srt"
        self.assert_error("revision_conflict", self.service.export_project, project_id, output, expected_revision=2)
        self.assert_error("translation_incomplete", self.service.export_project, project_id, output, variant="target")
        self.assert_error("unsupported_export_variant", self.service.export_project, project_id, output, variant="unsupported")
        self.assertFalse(output.exists())

    def test_read_commands_do_not_create_workspace(self):
        self.assertEqual(self.service.list_projects()["items"], [])
        self.assertTrue(self.service.doctor()["ready"])
        self.assertFalse(self.service.doctor()["workspace_exists"])
        self.assert_error("workspace_not_found", self.service.status, "missing")
        self.assertFalse(self.workspace.exists())

    def test_future_or_unrelated_schema_is_not_mutated(self):
        self.import_source()
        with closing(sqlite3.connect(self.service.store.database)) as connection, connection:
            connection.execute("PRAGMA user_version = 999")
        self.assert_error("workspace_version_unsupported", self.service.doctor)
        with closing(sqlite3.connect(self.service.store.database)) as connection, connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 999)
        other = self.directory / "other"
        other.mkdir()
        with closing(sqlite3.connect(other / "workspace.sqlite3")) as connection, connection:
            connection.execute("CREATE TABLE owner_data (value TEXT)")
            connection.execute("INSERT INTO owner_data VALUES ('keep')")
        self.assert_error("invalid_workspace", ProjectService(other).import_project, self.source)
        with closing(sqlite3.connect(other / "workspace.sqlite3")) as connection, connection:
            self.assertEqual(connection.execute("SELECT value FROM owner_data").fetchone()[0], "keep")
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 0)

    def test_archive_tampering_is_detected_before_export(self):
        project_id = self.import_source()["project"]["project_id"]
        with closing(sqlite3.connect(self.service.store.database)) as connection, connection:
            connection.execute("UPDATE projects SET original_source = ?", (b"tampered",))
        self.assert_error("source_integrity_error", self.service.validate, project_id)
        output = self.directory / "out.srt"
        self.assert_error("source_integrity_error", self.service.export_project, project_id, output)
        self.assertFalse(output.exists())

    def test_invalid_page_and_request_id_errors(self):
        project_id = self.import_source()["project"]["project_id"]
        for limit in (0, 501, True):
            self.assert_error("invalid_page", self.service.list_entries, project_id, limit=limit)
        for cursor in ("-1", "not-a-cursor", "1.5", str(2 ** 63), "9" * 4301):
            self.assert_error("invalid_cursor", self.service.list_entries, project_id, cursor=cursor)
        self.assert_error("invalid_request_id", self.import_source, request_id="bad")
        self.assert_error("project_not_found", self.service.status, "not-a-project")


class ToolCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = temporary_workspace()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.source = self.directory / "episode.srt"
        self.source.write_bytes(SOURCE)
        self.workspace = self.directory / "workspace"

    def run_tool(self, *args, success=True, ascii_output=False):
        environment = os.environ.copy()
        if ascii_output:
            environment["PYTHONIOENCODING"] = "ascii"
        result = subprocess.run(
            [sys.executable, "-S", "-m", "subtitle_translator.tool", "--workspace", str(self.workspace), *args, "--json"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=environment,
        )
        self.assertEqual(result.returncode, 0 if success else 1, result.stderr or result.stdout)
        self.assertEqual(result.stderr, "", result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), 1)
        response = json.loads(result.stdout)
        self.assertEqual(response["ok"], success)
        self.assertTrue(response["api_version"].startswith("1."))
        return response

    def test_separate_process_import_inspect_entries_validate_and_export(self):
        cap = self.run_tool("capabilities")
        self.assertFalse(cap["data"]["model_required"])
        self.assertEqual(cap["data"]["features"]["translation"], "external_agent")
        imported = self.run_tool("project", "import", "--input", str(self.source))
        project_id = imported["data"]["project"]["project_id"]
        self.assertEqual(self.run_tool("project", "status", "--project", project_id)["data"]["project"]["entry_count"], 3)
        self.assertEqual(len(self.run_tool("entry", "list", "--project", project_id, "--limit", "2")["data"]["items"]), 2)
        self.assertTrue(self.run_tool("project", "validate", "--project", project_id)["data"]["valid"])
        output = self.directory / "original.srt"
        self.run_tool("project", "export", "--project", project_id, "--output", str(output), "--variant", "original")
        self.assertEqual(output.read_bytes(), SOURCE)
        receipt = self.run_tool("request", "receipt", "--request-id", imported["request_id"])
        self.assertEqual(receipt["data"]["state"], "completed")

    def test_failures_are_one_json_value_and_nonzero_exit(self):
        response = self.run_tool("project", "status", "--project", "missing", success=False)
        self.assertEqual(response["error"]["code"], "workspace_not_found")
        response = self.run_tool("project", "import", success=False)
        self.assertEqual(response["error"]["code"], "invalid_arguments")
        self.assertFalse(self.workspace.exists())

    def test_failed_mutation_still_returns_its_request_id(self):
        response = self.run_tool("project", "import", "--input", str(self.directory / "missing.srt"), success=False)
        self.assertEqual(response["error"]["code"], "source_not_found")
        self.assertEqual(str(uuid.UUID(response["request_id"])), response["request_id"])
        invalid = self.run_tool("project", "import", "--input", str(self.source), "--request-id", "bad", success=False)
        self.assertEqual(invalid["error"]["code"], "invalid_request_id")
        self.assertIsNone(invalid["request_id"])

    def test_workspace_and_json_flags_may_follow_leaf_command(self):
        result = subprocess.run(
            [sys.executable, "-S", "-m", "subtitle_translator.tool", "doctor", "--workspace", str(self.workspace), "--json"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["data"]["workspace"], str(self.workspace.resolve()))

    def test_json_transports_unicode_even_with_ascii_stdout(self):
        imported = self.run_tool("project", "import", "--input", str(self.source), ascii_output=True)
        project_id = imported["data"]["project"]["project_id"]
        entries = self.run_tool("entry", "list", "--project", project_id, ascii_output=True)
        self.assertIn("Köszönöm", entries["data"]["items"][0]["source_text"])


if __name__ == "__main__":
    unittest.main()
