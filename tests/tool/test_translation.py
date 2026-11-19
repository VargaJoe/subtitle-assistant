"""Independent, model-free regression checks for external-agent translation.

The bilingual fixture has a deliberately known cue mapping. Its duplicate source
index, cross-cue italic scope, partial bold emphasis, speaker changes, and changed
physical row count exercise information that positional translation would lose.
"""

from contextlib import closing
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import uuid
from unittest import mock

from subtitle_translator.project.errors import ProjectError
from subtitle_translator.project.service import ProjectService
from subtitle_translator.project.srt import parse_source


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (
    "\ufeff7\r\n00:00:01,001 --> 00:00:02,777\r\n<i>If you trust\r\n\r\n"
    "7\r\n00:00:03,008 --> 00:00:04,999\r\nme, take the <b>red</b> key.</i>\r\n\r\n"
    "9\r\n00:00:06,000 --> 00:00:08,002\r\n- No.\r\n- Why?\r\n\r\n"
    "12\r\n00:00:08,100 --> 00:00:09,000\r\n[DOOR CLOSES]\r\n\r\n"
    "13\r\n00:00:10,000 --> 00:00:11,999\r\nWait for me.\r\n\r\n"
    "14\r\n00:00:12,000 --> 00:00:13,900\r\nI will bring\r\n\r\n"
    "15\r\n00:00:14,000 --> 00:00:16,000\r\nthe car.\r\n"
).encode("utf-8")
ANCHORS = [
    (7, 1001, 2777), (7, 3008, 4999), (9, 6000, 8002),
    (12, 8100, 9000), (13, 10000, 11999), (14, 12000, 13900),
    (15, 14000, 16000),
]
SOURCE_TEXTS = [
    "<i>If you trust", "me, take the <b>red</b> key.</i>",
    "- No.\n- Why?", "[DOOR CLOSES]", "Wait for me.",
    "I will bring", "the car.",
]
TARGET_TEXTS = [
    "<i>Ha bízol\nbennem,", "vedd a <b>piros</b> kulcsot.</i>",
    "- Nem.\n- Miért?", "[AZ AJTÓ BECSUKÓDIK]", "Várj meg!",
    "Elhozom", "az autót.",
]
EXPORTED_TARGET_TEXTS = [
    "<i>Ha bízol</i>\n<i>bennem,</i>", "<i>vedd a <b>piros</b> kulcsot.</i>",
    "- Nem.\n- Miért?", "[AZ AJTÓ BECSUKÓDIK]", "Várj meg!",
    "Elhozom", "az autót.",
]


def request_id():
    return str(uuid.uuid4())


class TranslationServiceTests(unittest.TestCase):
    def setUp(self):
        location = ROOT / "temp" / "m2-translation-tests"
        location.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=location)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.source = self.directory / "episode.eng.srt"
        self.source.write_bytes(SOURCE)
        self.service = ProjectService(self.directory / "workspace")
        self.project = self.service.import_project(self.source)["project"]
        self.project_id = self.project["project_id"]
        self.original_entries = self.entries()
        self.ids = [entry["entry_id"] for entry in self.original_entries]
        self.targets = dict(zip(self.ids, TARGET_TEXTS))

    def entries(self):
        return self.service.list_entries(self.project_id)["items"]

    def revision(self):
        return self.service.status(self.project_id)["project"]["revision"]

    def assert_error(self, code, call, *args, **kwargs):
        with self.assertRaises(ProjectError) as raised:
            call(*args, **kwargs)
        self.assertEqual(raised.exception.code, code)
        return raised.exception

    def prepare_request(self, **options):
        return {"request_id": request_id(), "project_id": self.project_id,
                "expected_project_revision": self.revision(), **options}

    def prepare(self, **options):
        return self.service.prepare_batch(self.prepare_request(**options))["batch"]

    def submission(self, batch):
        return {
            "request_id": request_id(), "batch_id": batch["batch_id"],
            "expected_project_revision": batch["expected_project_revision"],
            "source_sha256": batch["source_sha256"],
            "context_revision": batch["context_revision"],
            "translations": [
                {"unit_id": unit["unit_id"], "entries": [
                    {"entry_id": entry_id, "text": self.targets[entry_id],
                     "state": "translated", "review_state": "agent_reviewed"}
                    for entry_id in unit["writable_entry_ids"]
                ]} for unit in batch["units"]
            ],
        }

    def edit(self, ordinal, changes, **options):
        return self.service.edit_entry({
            "request_id": request_id(), "project_id": self.project_id,
            "entry_id": self.ids[ordinal - 1], "expected_project_revision": self.revision(),
            "changes": changes, **options,
        })

    def control(self, action):
        return self.service.control_job({"request_id": request_id(),
                                         "project_id": self.project_id, "action": action})

    def complete(self):
        batch = self.prepare()
        return self.service.submit_batch(self.submission(batch))

    def test_units_follow_semantic_and_markup_boundaries_without_losing_identity(self):
        batch = self.prepare(context_before=1, context_after=1)
        self.assertEqual([unit["entry_ids"] for unit in batch["units"]],
                         [self.ids[:2], self.ids[2:3], self.ids[3:4],
                          self.ids[4:5], self.ids[5:7]])
        self.assertEqual(batch["units"][0]["group_reasons"], ["formatting_scope"])
        self.assertEqual(batch["units"][-1]["group_reasons"], ["sentence_continuation"])
        flattened = [entry for unit in batch["units"] for entry in unit["source_entries"]]
        self.assertEqual([entry["entry_id"] for entry in flattened], self.ids)
        self.assertEqual([(entry["source_index"], entry["start_ms"], entry["end_ms"])
                          for entry in flattened], ANCHORS)
        self.assertEqual([entry["source_text"] for entry in flattened], SOURCE_TEXTS)
        self.assertEqual(batch["units"][1]["context_before"][0]["entry_id"], self.ids[1])
        self.assertEqual(batch["units"][1]["context_after"][0]["entry_id"], self.ids[3])
        reopened = ProjectService(self.service.store.root).get_batch(batch["batch_id"])["batch"]
        self.assertEqual(reopened, json.loads(json.dumps(batch)))
        self.assertEqual(self.revision(), 1)

    def test_sentence_join_stops_at_speaker_and_long_time_gap(self):
        self.edit(5, {"source_text": "Wait for me"})
        self.edit(6, {"source_text": "- I will bring"})
        self.edit(7, {"start_ms": 20000, "end_ms": 22000})
        batch = self.prepare()
        self.assertEqual([unit["entry_ids"] for unit in batch["units"]],
                         [self.ids[:2], self.ids[2:3], self.ids[3:4],
                          self.ids[4:5], self.ids[5:6], self.ids[6:7]])

    def test_budget_never_splits_an_indivisible_multicue_unit(self):
        self.edit(1, {"source_text": "<i>" + "A quiet thought " * 5})
        self.edit(2, {"source_text": "ends with a <b>red</b> key.</i>"})
        failed_request = self.prepare_request(max_chars=100)
        error = self.assert_error("unit_too_large", self.service.prepare_batch, failed_request)
        self.assertGreater(error.details["source_chars"], 100)
        self.assert_error("request_not_found", self.service.receipt, failed_request["request_id"])
        batch = self.prepare(max_chars=error.details["source_chars"])
        self.assertEqual([unit["entry_ids"] for unit in batch["units"]], [self.ids[:2]])
        self.assertEqual(batch["source_chars"], error.details["source_chars"])

    def test_reverse_unit_and_entry_order_is_mapped_by_ids_not_position(self):
        batch = self.prepare()
        payload = self.submission(batch)
        payload["translations"].reverse()
        for unit in payload["translations"]:
            unit["entries"].reverse()
        result = self.service.submit_batch(payload)
        self.assertEqual((result["revision"], result["submitted_entries"], result["remaining"]), (2, 7, 0))
        self.assertEqual([entry["target"]["text"] for entry in self.entries()], TARGET_TEXTS)
        self.assertEqual([entry["entry_id"] for entry in self.entries()], self.ids)
        self.assertEqual(self.service.job_status(self.project_id)["state"], "completed")
        notes = result["review_notes"]
        self.assertIn({"code": "partial_formatting_review", "entry_id": self.ids[1]}, notes)

    def test_missing_duplicate_and_extra_ids_reject_the_entire_submission(self):
        batch = self.prepare()
        valid = self.submission(batch)

        def missing_unit(payload):
            payload["translations"].pop()

        def duplicate_unit(payload):
            payload["translations"][-1] = deepcopy(payload["translations"][0])

        def unknown_unit(payload):
            payload["translations"][-1]["unit_id"] = "unit_unknown"

        def extra_unit(payload):
            payload["translations"].append({"unit_id": "unit_extra", "entries": []})

        def missing_entry(payload):
            payload["translations"][0]["entries"].pop()

        def duplicate_entry(payload):
            payload["translations"][0]["entries"][1] = deepcopy(payload["translations"][0]["entries"][0])

        def unknown_entry(payload):
            payload["translations"][-1]["entries"][-1]["entry_id"] = "entry_unknown"

        def wrong_unit_entry(payload):
            payload["translations"][0]["entries"][1]["entry_id"] = self.ids[-1]

        def extra_entry(payload):
            payload["translations"][-1]["entries"].append({
                "entry_id": "entry_extra", "text": "Extra.", "state": "translated",
                "review_state": "agent_reviewed",
            })

        for mutate, code in (
            (missing_unit, "batch_incomplete"), (duplicate_unit, "duplicate_translation"),
            (unknown_unit, "batch_incomplete"), (extra_unit, "batch_incomplete"),
            (missing_entry, "batch_incomplete"), (duplicate_entry, "duplicate_translation"),
            (unknown_entry, "unexpected_entry"), (wrong_unit_entry, "unexpected_entry"),
            (extra_entry, "unexpected_entry"),
        ):
            with self.subTest(case=mutate.__name__):
                payload = deepcopy(valid)
                payload["request_id"] = request_id()
                mutate(payload)
                self.assert_error(code, self.service.submit_batch, payload)
                self.assertEqual(self.entries(), self.original_entries)
                self.assertEqual(self.revision(), 1)
                self.assertEqual(self.service.get_batch(batch["batch_id"])["batch"]["state"], "prepared")
                self.assert_error("request_not_found", self.service.receipt, payload["request_id"])
        self.assertEqual(self.service.submit_batch(valid)["submitted_entries"], 7)

    def test_late_invalid_translation_does_not_commit_earlier_valid_entries(self):
        batch = self.prepare()
        payload = self.submission(batch)
        payload["translations"][-1]["entries"][-1]["text"] = ""
        self.assert_error("invalid_translation", self.service.submit_batch, payload)
        self.assertEqual(self.entries(), self.original_entries)
        self.assertEqual(self.revision(), 1)

    def test_batch_version_guards_reject_changed_hash_context_and_boolean_revision(self):
        batch = self.prepare()
        valid = self.submission(batch)
        for key, value, code in (("source_sha256", "0" * 64, "batch_stale"),
                                 ("context_revision", 1, "batch_stale"),
                                 ("expected_project_revision", True, "revision_conflict")):
            with self.subTest(field=key):
                payload = deepcopy(valid)
                payload["request_id"] = request_id()
                payload[key] = value
                self.assert_error(code, self.service.submit_batch, payload)
                self.assertEqual(self.entries(), self.original_entries)
                self.assertEqual(self.revision(), 1)
        self.assertEqual(self.service.submit_batch(valid)["remaining"], 0)

    def test_database_failure_rolls_back_all_translation_and_receipt_changes(self):
        batch = self.prepare()
        payload = self.submission(batch)
        with closing(sqlite3.connect(self.service.store.database)) as connection, connection:
            connection.execute("""CREATE TRIGGER reject_last_target BEFORE INSERT ON translations
                WHEN NEW.entry_id LIKE '%000007' BEGIN SELECT RAISE(ABORT, 'injected failure'); END""")
        self.assert_error("workspace_error", self.service.submit_batch, payload)
        self.assertEqual(self.entries(), self.original_entries)
        self.assertEqual(self.revision(), 1)
        self.assert_error("request_not_found", self.service.receipt, payload["request_id"])
        self.assertEqual(self.service.get_batch(batch["batch_id"])["batch"]["state"], "prepared")

    def test_formatting_speaker_and_accessibility_scope_changes_are_rejected(self):
        batch = self.prepare()
        valid = self.submission(batch)
        cases = [
            (0, 1, "vedd a piros kulcsot.</i>", "formatting_scope_changed"),
            (0, 1, "<b>vedd a piros kulcsot.</b></i>", "formatting_scope_changed"),
            (1, 0, "Nem.\nMiért?", "speaker_markers_changed"),
            (2, 0, "Az ajtó becsukódik.", "accessibility_markers_changed"),
            (0, 1, "vedd a <b>piros</b> kulcsot.", "invalid_translation_formatting"),
        ]
        for unit_index, entry_index, text, code in cases:
            with self.subTest(text=text):
                payload = deepcopy(valid)
                payload["request_id"] = request_id()
                payload["translations"][unit_index]["entries"][entry_index]["text"] = text
                self.assert_error(code, self.service.submit_batch, payload)
                self.assertEqual(self.entries(), self.original_entries)

    def test_final_translation_requires_review_and_preserved_text_must_match(self):
        batch = self.prepare()
        payload = self.submission(batch)
        item = payload["translations"][-1]["entries"][-1]
        item["review_state"] = "unchecked"
        self.assert_error("review_required", self.service.submit_batch, payload)
        item["review_state"] = "agent_reviewed"
        item["state"] = "intentionally_preserved"
        self.assert_error("invalid_translation", self.service.submit_batch, payload)
        item["text"] = "the car."
        result = self.service.submit_batch(payload)
        self.assertEqual(result["remaining"], 0)
        self.assertEqual(self.entries()[-1]["target"]["state"], "intentionally_preserved")

    def test_prepare_and_submit_uuid_replay_preserves_batch_and_revision(self):
        prepare_request = self.prepare_request()
        first = self.service.prepare_batch(prepare_request)
        replay = self.service.prepare_batch(prepare_request)
        self.assertFalse(first["replayed"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["batch"], json.loads(json.dumps(first["batch"])))
        payload = self.submission(first["batch"])
        submitted = self.service.submit_batch(payload)
        repeated = ProjectService(self.service.store.root).submit_batch(payload)
        self.assertTrue(repeated["replayed"])
        self.assertEqual(repeated["revision"], submitted["revision"])
        self.assertEqual(self.revision(), 2)
        self.assertEqual(self.service.receipt(payload["request_id"])["operation"], "batch.submit")
        changed = deepcopy(payload)
        changed["translations"][-1]["entries"][-1]["text"] = "Másik autó."
        self.assert_error("request_id_conflict", self.service.submit_batch, changed)

    def test_batch_submission_has_per_entry_history_and_can_be_restored(self):
        payload = self.submission(self.prepare())
        payload["actor"] = "fixture-translator"
        self.service.submit_batch(payload)
        for entry_id, expected_text in zip(self.ids, TARGET_TEXTS):
            history = self.service.entry_history(self.project_id, entry_id)["items"]
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["actor"], "fixture-translator")
            self.assertIsNone(history[0]["before"]["target_text"])
            self.assertEqual(history[0]["after"]["target_text"], expected_text)
            self.assertEqual(history[0]["after"]["entry_id"], entry_id)
        change = self.service.entry_history(self.project_id, self.ids[4])["items"][0]
        self.service.restore_entry({"request_id": request_id(), "project_id": self.project_id,
                                    "change_id": change["change_id"], "expected_project_revision": self.revision()})
        self.assertIsNone(self.entries()[4]["target"])
        self.assertEqual(self.entries()[4]["source_text"], "Wait for me.")
        self.assertEqual(self.service.translation_issues(self.project_id)["total"], 1)

    def test_protected_manual_target_stays_in_unit_as_fixed_context(self):
        manual = self.edit(1, {"target_text": TARGET_TEXTS[0], "review_state": "human_reviewed"})
        self.assertTrue(manual["entry"]["protected"])
        batch = self.prepare()
        self.assertEqual(batch["units"][0]["entry_ids"], self.ids[:2])
        self.assertEqual(batch["units"][0]["writable_entry_ids"], self.ids[1:2])
        payload = self.submission(batch)
        invalid = deepcopy(payload)
        invalid["request_id"] = request_id()
        invalid["translations"][0]["entries"].append({
            "entry_id": self.ids[0], "text": "<i>Felülírva,", "state": "translated",
            "review_state": "agent_reviewed",
        })
        self.assert_error("unexpected_entry", self.service.submit_batch, invalid)
        self.service.submit_batch(payload)
        target = self.entries()[0]["target"]
        self.assertEqual(target["text"], TARGET_TEXTS[0])
        self.assertEqual(target["review_state"], "human_reviewed")
        self.assertTrue(target["protected"])

    def test_source_timing_and_manual_target_edits_stale_prepared_batches(self):
        for changes in ({"source_text": "Wait for us."}, {"start_ms": 10100},
                        {"target_text": "Kézi javítás.", "review_state": "human_reviewed"}):
            with self.subTest(changes=changes):
                batch = self.prepare()
                payload = self.submission(batch)
                self.edit(5, changes)
                self.assertEqual(self.service.get_batch(batch["batch_id"])["batch"]["state"], "stale")
                self.assert_error("revision_conflict", self.service.submit_batch, payload)
                payload["expected_project_revision"] = self.revision()
                self.assert_error("batch_stale", self.service.submit_batch, payload)
                self.assertEqual(self.entries()[0]["target"], None)

    def test_source_and_timing_revisions_keep_entry_id_and_invalidate_review(self):
        self.complete()
        before = self.entries()[4]
        changed = self.edit(5, {"source_text": "Wait for us.", "start_ms": 10100,
                                "end_ms": 12100})["entry"]
        self.assertEqual(changed["entry_id"], self.ids[4])
        self.assertEqual((changed["source_revision"], changed["timing_revision"]), (2, 2))
        after = self.entries()[4]
        self.assertEqual(after["target"]["text"], before["target"]["text"])
        self.assertEqual(after["target"]["state"], "needs_review")
        self.assertEqual(self.service.translation_issues(self.project_id)["items"][0]["entry_id"], self.ids[4])
        output = self.directory / "stale-target.srt"
        self.assert_error("translation_incomplete", self.service.export_project,
                          self.project_id, output, variant="target")
        self.assertFalse(output.exists())

    def test_only_edited_unit_identity_changes_when_source_or_timing_revision_changes(self):
        before = self.prepare()
        self.edit(5, {"source_text": "Wait for us.", "start_ms": 10100})
        after = self.prepare()
        self.assertEqual([unit["entry_ids"] for unit in before["units"]],
                         [unit["entry_ids"] for unit in after["units"]])
        self.assertEqual([unit["unit_id"] for unit in before["units"][:3]],
                         [unit["unit_id"] for unit in after["units"][:3]])
        self.assertNotEqual(before["units"][3]["unit_id"], after["units"][3]["unit_id"])
        self.assertEqual(before["units"][4]["unit_id"], after["units"][4]["unit_id"])

    def test_target_export_requires_complete_reviewed_mapping_then_keeps_known_anchors(self):
        output = self.directory / "target.srt"
        self.assert_error("translation_incomplete", self.service.export_project,
                          self.project_id, output, variant="target")
        self.assertFalse(output.exists())
        self.complete()
        result = self.service.export_project(self.project_id, output, variant="target", expected_revision=2)
        parsed = parse_source(output.read_bytes())
        self.assertEqual(parsed.errors, [])
        self.assertEqual([(entry.source_index, entry.start_ms, entry.end_ms) for entry in parsed.entries], ANCHORS)
        self.assertEqual([entry.text for entry in parsed.entries], EXPORTED_TARGET_TEXTS)
        self.assertEqual(result["entry_count"], 7)
        self.assertEqual(result["sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
        self.assertEqual(len(SOURCE_TEXTS[0].splitlines()), 1)
        self.assertEqual(len(parsed.entries[0].text.splitlines()), 2)

    def test_partial_draft_persists_exports_marked_fallbacks_and_keeps_review_states(self):
        self.complete()
        self.edit(5, {"source_text": "Wait for us."})
        self.edit(6, {"clear_target": True})
        self.edit(7, {"target_text": "az autó"})
        # Reopen from disk: unfinished manual wording is durable without review.
        self.service = ProjectService(self.directory / "workspace")
        before = self.entries()
        self.assertEqual(before[6]["target"]["state"], "draft")
        self.assertEqual(before[6]["target"]["text"], "az autó")
        output = self.directory / "episode.hu.draft.srt"
        request = request_id()
        revision = self.revision()
        result = self.service.export_project(self.project_id, output, variant="draft",
                                             expected_revision=revision, request_id=request)
        report = result["draft"]
        self.assertEqual((report["pending_count"], report["missing_count"]), (3, 1))
        self.assertEqual({e["ordinal"]: e["reason"] for e in report["entries"]},
                         {5: "stale_translation", 6: "missing_translation", 7: "review_required"})
        parsed = parse_source(output.read_bytes())
        self.assertEqual(parsed.errors, [])
        self.assertEqual([(e.source_index, e.start_ms, e.end_ms) for e in parsed.entries], ANCHORS)
        self.assertIn("[ELAVULT FORDÍTÁS]", parsed.entries[4].text)
        self.assertIn("[NINCS FORDÍTÁS]\nI will bring", parsed.entries[5].text)
        self.assertIn("[ELLENŐRIZENDŐ]\naz autó", parsed.entries[6].text)
        self.assertEqual(self.entries(), before)
        self.assertEqual(self.revision(), revision)
        self.assertEqual(self.source.read_bytes(), SOURCE)
        self.assertFalse(self.service.validate(self.project_id)["target_ready"])
        self.assert_error("translation_incomplete", self.service.export_project,
                          self.project_id, self.directory / "final.srt", variant="target")
        self.assertEqual(self.service.receipt(request)["result"]["draft"], report)
        self.edit(7, {"target_text": "másik változat"})
        replay = self.service.export_project(self.project_id, output, variant="draft",
                                             expected_revision=revision, request_id=request)
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["draft"], report)
        self.assertNotIn("másik", output.read_text(encoding="utf-8"))

    def test_draft_records_formatting_review_but_refuses_broken_srt_structure(self):
        self.complete()
        self.edit(3, {"target_text": "Nem. Miért?", "review_state": "human_reviewed"})
        self.assertFalse(self.service.validate(self.project_id)["target_ready"])
        result = self.service.export_project(self.project_id, self.directory / "format.draft.srt", variant="draft")
        self.assertEqual(result["draft"]["entries"][0]["ordinal"], 3)
        self.assertEqual(result["draft"]["entries"][0]["reason"], "formatting_review")
        self.assertTrue(result["draft"]["formatting_issues"])
        with self.service.store.connect() as connection, connection:
            connection.execute("UPDATE translations SET text=? WHERE entry_id=?",
                               ("Bad\n\n99\n00:01:00,000 --> 00:01:01,000\nInjected", self.ids[2]))
        output = self.directory / "broken.draft.srt"
        self.assert_error("invalid_translation", self.service.export_project,
                          self.project_id, output, variant="draft")
        self.assertFalse(output.exists())

    def test_draft_targets_remain_incomplete_and_issues_have_stable_pagination(self):
        first = self.service.translation_issues(self.project_id, limit=3)
        second = self.service.translation_issues(self.project_id, limit=3, cursor=first["next_cursor"])
        third = self.service.translation_issues(self.project_id, limit=3, cursor=second["next_cursor"])
        self.assertEqual([issue["entry_id"] for issue in first["items"] + second["items"] + third["items"]], self.ids)
        self.assertIsNone(third["next_cursor"])
        payload = self.submission(self.prepare())
        item = payload["translations"][-1]["entries"][-1]
        item.update(state="draft", review_state="unchecked")
        result = self.service.submit_batch(payload)
        self.assertEqual(result["remaining"], 1)
        issue = self.service.translation_issues(self.project_id)
        self.assertEqual(issue["total"], 1)
        self.assertEqual(issue["items"][0]["entry_id"], self.ids[6])
        self.assertEqual(issue["items"][0]["code"], "translation_needs_review")
        self.assert_error("translation_incomplete", self.service.export_project,
                          self.project_id, self.directory / "draft.srt", variant="target")
        self.edit(7, {"clear_target": True})
        self.assertEqual(self.service.translation_issues(self.project_id)["items"][0]["code"], "untranslated")

    def test_translation_and_working_edits_preserve_original_source_bytes(self):
        self.complete()
        self.edit(5, {"source_text": "Wait for us.", "start_ms": 10100, "end_ms": 12100})
        original, source = self.directory / "original.srt", self.directory / "source.srt"
        self.service.export_project(self.project_id, original, variant="original")
        self.service.export_project(self.project_id, source, variant="source")
        self.assertEqual(self.source.read_bytes(), SOURCE)
        self.assertEqual(original.read_bytes(), SOURCE)
        working = parse_source(source.read_bytes())
        expected_anchors = ANCHORS[:]
        expected_anchors[4] = (13, 10100, 12100)
        expected_texts = SOURCE_TEXTS[:]
        expected_texts[4] = "Wait for us."
        self.assertEqual([(entry.source_index, entry.start_ms, entry.end_ms) for entry in working.entries], expected_anchors)
        self.assertEqual([entry.text for entry in working.entries], expected_texts)
        self.assertTrue(self.service.validate(self.project_id)["valid"])

    def test_restore_records_new_revision_and_removes_new_target_without_reusing_old_revisions(self):
        edited = self.edit(5, {"source_text": "Wait for us.", "start_ms": 10100,
                                "target_text": "Várjatok meg!", "review_state": "human_reviewed"})
        payload = {"request_id": request_id(), "project_id": self.project_id,
                   "change_id": edited["change_id"], "expected_project_revision": self.revision()}
        restored = self.service.restore_entry(payload)
        entry = self.entries()[4]
        self.assertEqual(restored["restored_change_id"], edited["change_id"])
        self.assertEqual(restored["revision"], 3)
        self.assertEqual((entry["entry_id"], entry["source_text"], entry["start_ms"], entry["end_ms"]),
                         (self.ids[4], "Wait for me.", 10000, 11999))
        self.assertEqual((entry["source_revision"], entry["timing_revision"]), (3, 3))
        self.assertIsNone(entry["target"])
        self.assertEqual(len(self.service.entry_history(self.project_id, self.ids[4])["items"]), 2)
        self.assertTrue(self.service.restore_entry(payload)["replayed"])
        self.assertEqual(self.revision(), 3)

    def test_restore_of_already_stale_snapshot_does_not_reapprove_old_target(self):
        self.complete()
        self.edit(5, {"source_text": "Wait for us."})
        second_edit = self.edit(5, {"source_text": "Wait here."})
        self.assertEqual(self.entries()[4]["target"]["state"], "needs_review")
        payload = {"request_id": request_id(), "project_id": self.project_id,
                   "change_id": second_edit["change_id"], "expected_project_revision": self.revision()}
        restored = self.service.restore_entry(payload)
        entry = self.entries()[4]
        self.assertEqual(entry["source_text"], "Wait for us.")
        self.assertEqual(entry["target"]["text"], "Várj meg!")
        self.assertEqual(entry["target"]["state"], "needs_review")
        self.assertEqual(self.service.translation_issues(self.project_id)["total"], 1)
        self.assert_error("translation_incomplete", self.service.export_project,
                          self.project_id, self.directory / "restored-stale.srt", variant="target")
        self.assertTrue(self.service.restore_entry(payload)["replayed"])
        self.assertEqual(self.revision(), restored["revision"])

    def test_clear_target_is_explicit_and_rejects_conflicting_target_fields(self):
        self.edit(5, {"target_text": "Várj meg!", "review_state": "human_reviewed"})
        for changes in ({"clear_target": False}, {"clear_target": True, "target_text": "Más."},
                        {"clear_target": True, "protected": False}):
            with self.subTest(changes=changes):
                before = self.entries()
                revision = self.revision()
                self.assert_error("invalid_request", self.edit, 5, changes)
                self.assertEqual(self.entries(), before)
                self.assertEqual(self.revision(), revision)
        self.edit(5, {"clear_target": True})
        self.assertIsNone(self.entries()[4]["target"])
        self.assertEqual(self.entries()[4]["source_text"], "Wait for me.")

    def test_pause_is_cooperative_current_batch_finishes_then_job_pauses(self):
        batch = self.prepare()
        self.assertEqual(self.control("pause")["state"], "pause_requested")
        self.assert_error("job_not_running", self.service.prepare_batch, self.prepare_request())
        self.service.submit_batch(self.submission(batch))
        self.assertEqual(self.service.job_status(self.project_id)["state"], "paused")
        self.assertEqual(self.control("resume")["state"], "pending")
        result = self.service.prepare_batch(self.prepare_request())
        self.assertIsNone(result["batch"])
        self.assertTrue(result["complete"])

    def test_cancel_invalidates_batch_and_needs_explicit_resume(self):
        batch = self.prepare()
        payload = self.submission(batch)
        self.assertEqual(self.control("cancel")["state"], "cancelled")
        self.assertEqual(self.service.get_batch(batch["batch_id"])["batch"]["state"], "cancelled")
        self.assert_error("batch_stale", self.service.submit_batch, payload)
        self.assert_error("job_not_running", self.service.prepare_batch, self.prepare_request())
        self.assert_error("job_not_running", self.service.job_activity,
                          {"request_id": request_id(), "project_id": self.project_id,
                           "agent_label": "fixture-agent", "phase": "translating"})
        self.control("resume")
        fresh = self.prepare()
        self.assertNotEqual(fresh["batch_id"], batch["batch_id"])
        self.assertEqual(self.entries(), self.original_entries)

    def test_activity_reports_cannot_resume_paused_or_pause_requested_jobs(self):
        self.prepare()
        for initially_paused in (False, True):
            for phase in ("starting", "analyzing", "translating", "validating", "waiting", "finished", "failed"):
                with self.subTest(initially_paused=initially_paused, phase=phase):
                    self.control("resume")
                    self.control("pause")
                    if initially_paused:
                        self.service.job_activity({"request_id": request_id(), "project_id": self.project_id,
                                                   "agent_label": "fixture-agent", "phase": "paused"})
                    expected = "paused" if initially_paused else "pause_requested"
                    self.service.job_activity({"request_id": request_id(), "project_id": self.project_id,
                                               "agent_label": "fixture-agent", "phase": phase})
                    self.assertEqual(self.service.job_status(self.project_id)["state"], expected)
                    self.assert_error("job_not_running", self.service.prepare_batch, self.prepare_request())

    def test_activity_freshness_and_replay_do_not_change_project_revision(self):
        payload = {"request_id": request_id(), "project_id": self.project_id,
                   "agent_label": "fixture-agent", "phase": "analyzing", "ttl_seconds": 10}
        with mock.patch("subtitle_translator.project.translation.time.time", return_value=1000):
            self.service.job_activity(payload)
            fresh = self.service.job_status(self.project_id)
        self.assertEqual((fresh["freshness"], fresh["state"], fresh["activity_revision"]), ("fresh", "running", 1))
        with mock.patch("subtitle_translator.project.translation.time.time", return_value=1011):
            self.assertTrue(self.service.job_activity(payload)["replayed"])
            stale = self.service.job_status(self.project_id)
        self.assertEqual(stale["freshness"], "stale")
        self.assertEqual(stale["last_seen"], 1000)
        self.assertEqual(stale["activity_revision"], 1)
        self.assertEqual(self.revision(), 1)

    def test_activity_cannot_claim_a_stale_batch(self):
        batch = self.prepare()
        self.edit(5, {"source_text": "Wait for us."})
        before = self.service.job_status(self.project_id)
        payload = {"request_id": request_id(), "project_id": self.project_id,
                   "agent_label": "old-agent", "phase": "translating", "batch_id": batch["batch_id"]}
        self.assert_error("batch_stale", self.service.job_activity, payload)
        after = self.service.job_status(self.project_id)
        self.assertEqual(after["activity_revision"], before["activity_revision"])
        self.assertEqual(after["agent_label"], before["agent_label"])
        self.assertIsNone(after["batch_id"])
        self.assert_error("request_not_found", self.service.receipt, payload["request_id"])

    def test_schema_v1_requires_explicit_migration_with_verified_original_backup(self):
        # Remove only schema-2 additions to produce an actual persisted v1 fixture.
        # All original project/entry/request rows are the pre-M2 storage shape.
        with closing(sqlite3.connect(self.service.store.database)) as connection, connection:
            for table in ("jobs", "changes", "batches", "translations"):
                connection.execute(f"DROP TABLE {table}")
            connection.execute("PRAGMA user_version=1")
        doctor = self.service.doctor()
        self.assertEqual(doctor["schema_version"], 1)
        self.assertTrue(doctor["migration_required"])
        self.assert_error("workspace_migration_required", self.service.prepare_batch, self.prepare_request())
        original = self.directory / "v1-original.srt"
        self.service.export_project(self.project_id, original, variant="original")
        self.assertEqual(original.read_bytes(), SOURCE)
        migrated = self.service.migrate_workspace(expected_version=1)
        self.assertTrue(migrated["migrated"])
        self.assertEqual(migrated["schema_version"], 2)
        with closing(sqlite3.connect(migrated["backup"])) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT original_source FROM projects").fetchone()[0], SOURCE)
            self.assertEqual(connection.execute("SELECT count(*) FROM entries").fetchone()[0], 7)
            self.assertIsNone(connection.execute("SELECT name FROM sqlite_master WHERE name='translations'").fetchone())
        self.assertEqual(self.entries(), self.original_entries)
        self.assertEqual(self.revision(), 1)
        self.assertEqual(self.service.migrate_workspace(), {"schema_version": 2, "migrated": False})
        self.assertEqual(self.prepare()["units"][0]["entry_ids"], self.ids[:2])


if __name__ == "__main__":
    unittest.main()
