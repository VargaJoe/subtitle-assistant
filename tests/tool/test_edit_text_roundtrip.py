"""Manual edits must remain exportable after Windows newline normalization."""

from pathlib import Path
import tempfile
import unittest
import uuid

from subtitle_translator.project.errors import ProjectError
from subtitle_translator.project.grouping import profiles
from subtitle_translator.project.service import ProjectService
from subtitle_translator.project.srt import parse_source


ROOT = Path(__file__).resolve().parents[2]
SOURCE = b"1\n00:00:01,000 --> 00:00:02,000\nHello.\n"


class EditTextRoundtripTests(unittest.TestCase):
    def setUp(self):
        location = ROOT / "temp" / "m2-edit-text-roundtrip-tests"
        location.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=location)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.source = self.directory / "source.srt"
        self.source.write_bytes(SOURCE)
        self.service = ProjectService(self.directory / "workspace")
        self.project_id = self.service.import_project(self.source)["project"]["project_id"]
        self.entry_id = self.entries()[0]["entry_id"]

    def entries(self):
        return self.service.list_entries(self.project_id)["items"]

    def revision(self):
        return self.service.status(self.project_id)["project"]["revision"]

    def edit_request(self, changes):
        return {"request_id": str(uuid.uuid4()), "project_id": self.project_id,
                "entry_id": self.entry_id, "expected_project_revision": self.revision(),
                "changes": changes}

    def assert_error(self, code, operation, *args, **kwargs):
        with self.assertRaises(ProjectError) as caught:
            operation(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def check_source_newline_normalization(self, newline):
        result = self.service.edit_entry(self.edit_request({"source_text": f"First{newline}second."}))
        self.assertEqual(result["entry"]["source_text"], "First\nsecond.")
        self.assertEqual(self.entries()[0]["source_text"], "First\nsecond.")
        self.assertTrue(self.service.validate(self.project_id)["valid"])
        working, original = self.directory / "working.srt", self.directory / "original.srt"
        self.service.export_project(self.project_id, working, variant="source")
        self.service.export_project(self.project_id, original, variant="original")
        parsed = parse_source(working.read_bytes())
        self.assertEqual(parsed.errors, [])
        self.assertEqual(parsed.entries[0].text, "First\nsecond.")
        self.assertEqual((parsed.entries[0].start_ms, parsed.entries[0].end_ms), (1000, 2000))
        self.assertEqual(original.read_bytes(), SOURCE)
        self.assertEqual(self.source.read_bytes(), SOURCE)

    def test_source_crlf_edit_is_normalized_and_both_exports_remain_available(self):
        self.check_source_newline_normalization("\r\n")

    def test_source_cr_edit_is_normalized_and_both_exports_remain_available(self):
        self.check_source_newline_normalization("\r")

    def test_target_newlines_are_normalized_in_storage_history_and_export(self):
        for index, newline in enumerate(("\r\n", "\r")):
            with self.subTest(newline=repr(newline)):
                result = self.service.edit_entry(self.edit_request({
                    "target_text": f"First{newline}second.", "review_state": "human_reviewed",
                }))
                self.assertEqual(result["entry"]["target_text"], "First\nsecond.")
                self.assertEqual(self.entries()[0]["target"]["text"], "First\nsecond.")
                history = self.service.entry_history(self.project_id, self.entry_id)["items"]
                self.assertEqual(history[-1]["after"]["target_text"], "First\nsecond.")
                output = self.directory / f"target-{index}.srt"
                self.service.export_project(self.project_id, output, variant="target")
                self.assertEqual(parse_source(output.read_bytes()).entries[0].text, "First\nsecond.")

    def test_blank_text_boundaries_are_rejected_without_changes_or_receipts(self):
        self.service.edit_entry(self.edit_request({
            "target_text": "Reviewed target.", "review_state": "human_reviewed",
        }))
        for field in ("source_text", "target_text"):
            for text in ("\nText.", "Text.\n", "\r\nText.", "Text.\r", " \nText.", "Text.\n "):
                with self.subTest(field=field, text=repr(text)):
                    before, revision = self.entries(), self.revision()
                    changes = {field: text}
                    if field == "target_text":
                        # A late target validation failure must roll back source SQL too.
                        changes["source_text"] = "Temporary source change."
                    request = self.edit_request(changes)
                    self.assert_error("invalid_translation", self.service.edit_entry, request)
                    self.assertEqual(self.entries(), before)
                    self.assertEqual(self.revision(), revision)
                    self.assert_error("request_not_found", self.service.receipt, request["request_id"])

    def test_bare_ampersand_text_stays_attached_to_its_own_cue(self):
        plain = profiles(["AT&T", "R&D"])
        self.assertEqual([item["plain"] for item in plain], ["AT&T", "R&D"])
        styled = profiles(["<i>AT&T", "R&D</i>"])
        self.assertEqual([item["plain"] for item in styled], ["AT&T", "R&D"])
        self.assertTrue(styled[0]["open_after"])
        self.assertFalse(styled[1]["open_after"])
        self.assertEqual([item["errors"] for item in styled], [[], []])

    def test_intentionally_preserved_requires_matching_bare_ampersand_text(self):
        self.service.edit_entry(self.edit_request({"source_text": "AT&T"}))
        batch = self.service.prepare_batch({
            "request_id": str(uuid.uuid4()), "project_id": self.project_id,
            "expected_project_revision": self.revision(),
        })["batch"]
        self.assertEqual(batch["units"][0]["source_text"], "AT&T")
        item = {"entry_id": self.entry_id, "text": "R&D", "state": "intentionally_preserved",
                "review_state": "agent_reviewed"}
        request = {
            "request_id": str(uuid.uuid4()), "batch_id": batch["batch_id"],
            "expected_project_revision": batch["expected_project_revision"],
            "source_sha256": batch["source_sha256"], "context_revision": batch["context_revision"],
            "translations": [{"unit_id": batch["units"][0]["unit_id"], "entries": [item]}],
        }
        revision = self.revision()
        self.assert_error("invalid_translation", self.service.submit_batch, request)
        self.assertEqual(self.revision(), revision)
        self.assertIsNone(self.entries()[0]["target"])
        self.assert_error("request_not_found", self.service.receipt, request["request_id"])
        request["request_id"] = str(uuid.uuid4())
        item["text"] = "AT&T"
        self.assertEqual(self.service.submit_batch(request)["remaining"], 0)
        output = self.directory / "preserved-target.srt"
        self.service.export_project(self.project_id, output, variant="target")
        self.assertEqual(parse_source(output.read_bytes()).entries[0].text, "AT&T")


if __name__ == "__main__":
    unittest.main()
