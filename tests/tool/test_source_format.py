"""Model-free source parsing/export regression tests; all text is synthetic."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest

from subtitle_translator.project.errors import ProjectError
from subtitle_translator.project.srt import parse_source, render_source
from subtitle_translator.srt_format import format_timestamp


REPOSITORY = Path(__file__).resolve().parents[2]
VALID_BLOCK = "7\n00:00:01,001 --> 00:00:02,009\nA valid line."


class ParseSourceTests(unittest.TestCase):
    def test_preserves_text_tags_spacing_indices_and_milliseconds(self):
        raw = (
            "42\n00:00:01,001 --> 00:01:02,987\n"
            '  <i>[DOOR OPENS]</i>  \n- <font color="yellow">Ő itt van.</font>\t\n'
            "\n9\n100:02:03,004 --> 100:02:03,005\n♪ Hello & goodbye ♪"
        ).encode("utf-8")

        parsed = parse_source(raw)

        self.assertIs(parsed.raw, raw)
        self.assertEqual(parsed.errors, [])
        self.assertEqual(parsed.diagnostics, [])
        self.assertEqual(parsed.block_count, 2)
        first, second = parsed.entries
        self.assertEqual(
            (first.ordinal, first.source_index, first.start_ms, first.end_ms, first.source_line),
            (1, 42, 1001, 62987, 1),
        )
        self.assertEqual(
            first.text,
            '  <i>[DOOR OPENS]</i>  \n- <font color="yellow">Ő itt van.</font>\t',
        )
        self.assertEqual(
            (second.ordinal, second.source_index, second.start_ms, second.end_ms, second.source_line),
            (2, 9, 360123004, 360123005, 6),
        )
        self.assertEqual(second.text, "♪ Hello & goodbye ♪")

    def test_bom_crlf_and_original_byte_metadata(self):
        raw = b"\xef\xbb\xbf" + VALID_BLOCK.replace("\n", "\r\n").encode("utf-8") + b"\r\n"

        parsed = parse_source(raw)

        self.assertEqual(parsed.encoding, "utf-8-sig")
        self.assertEqual(parsed.newline, "CRLF")
        self.assertEqual(parsed.entries[0].text, "A valid line.")
        self.assertEqual(parsed.raw, raw)
        self.assertEqual(parsed.sha256, hashlib.sha256(raw).hexdigest())
        self.assertEqual(
            parsed.report(),
            {
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "byte_count": len(raw),
                "encoding": "utf-8-sig",
                "newline": "CRLF",
                "block_count": 1,
                "entry_count": 1,
                "error_count": 0,
                "warning_count": 0,
                "diagnostics": [],
                "diagnostics_truncated": False,
            },
        )
        # A report is a JSON payload, with no dataclass/bytes objects leaking out.
        self.assertEqual(json.loads(json.dumps(parsed.report())), parsed.report())

    def test_newline_styles_normalize_only_text_line_endings(self):
        text = "7\n00:00:01,001 --> 00:00:02,009\n  First.  \n\tSecond.\t\n"
        for separator, expected in (("\n", "LF"), ("\r\n", "CRLF"), ("\r", "CR")):
            with self.subTest(newline=expected):
                parsed = parse_source(text.replace("\n", separator).encode("utf-8"))
                self.assertEqual(parsed.newline, expected)
                self.assertEqual(parsed.entries[0].text, "  First.  \n\tSecond.\t")
                self.assertEqual(parsed.errors, [])

    def test_mixed_newlines_are_reported(self):
        raw = b"7\r\n00:00:01,001 --> 00:00:02,009\rFirst.\nSecond.\r\n"
        parsed = parse_source(raw)
        self.assertEqual(parsed.newline, "mixed")
        self.assertEqual(parsed.entries[0].text, "First.\nSecond.")

    def test_explicit_legacy_encoding_is_lossless(self):
        text = "Árvíztűrő tükörfúrógép – ő, ű."
        raw = VALID_BLOCK.replace("A valid line.", text).encode("cp1250")
        parsed = parse_source(raw, encoding="cp1250")
        self.assertEqual(parsed.encoding, "cp1250")
        self.assertEqual(parsed.entries[0].text, text)
        self.assertEqual(parsed.raw, raw)
        self.assertEqual(parsed.errors, [])

    def test_explicit_unicode_encoding_consumes_bom(self):
        parsed = parse_source(VALID_BLOCK.encode("utf-16"), encoding="utf-16")
        self.assertEqual(parsed.entries[0].source_index, 7)
        self.assertEqual(parsed.entries[0].text, "A valid line.")
        self.assertEqual(parsed.errors, [])

    def test_invalid_encoding_and_undecodable_bytes_have_stable_errors(self):
        for raw, encoding, expected_encoding in (
            (b"\xff", None, "utf-8"),
            (VALID_BLOCK.encode(), "no-such-codec", "no-such-codec"),
            (VALID_BLOCK.encode() + b"\xff", "utf-8", "utf-8"),
        ):
            with self.subTest(encoding=encoding, raw=raw[-5:]):
                with self.assertRaises(ProjectError) as error:
                    parse_source(raw, encoding=encoding)
                self.assertEqual(error.exception.code, "source_encoding_error")
                self.assertEqual(error.exception.details, {"encoding": expected_encoding})

    def test_invalid_block_is_reported_and_next_block_keeps_source_position(self):
        raw = ("\n\n1\n00:00:00,000 --> 00:00:01,000\n\n" + VALID_BLOCK).encode()
        parsed = parse_source(raw)
        self.assertEqual(parsed.block_count, 2)
        self.assertEqual(len(parsed.entries), 1)
        self.assertEqual(parsed.entries[0].ordinal, 2)
        self.assertEqual(parsed.entries[0].source_line, 6)
        self.assertEqual(
            [(d.code, d.severity, d.block, d.line) for d in parsed.diagnostics],
            [("invalid_block", "error", 1, 3)],
        )
        self.assertEqual(parsed.errors, parsed.diagnostics)

    def test_missing_separator_cannot_silently_merge_two_cues(self):
        raw = (
            b"1\n00:00:01,001 --> 00:00:02,002\nHello.\n"
            b"2\n00:00:03,003 --> 00:00:04,004\nWorld.\n"
        )
        parsed = parse_source(raw)
        self.assertEqual(parsed.entries, [])
        self.assertEqual(
            [(d.code, d.severity, d.block, d.line) for d in parsed.errors],
            [("missing_separator", "error", 1, 4), ("no_entries", "error", 0, 1)],
        )
        self.assertEqual(parsed.raw, raw)

    def test_invalid_indices_are_not_silently_renumbered(self):
        for index in ("words", "0", "-1", "1.0"):
            with self.subTest(index=index):
                bad = VALID_BLOCK.replace("7\n", index + "\n", 1)
                parsed = parse_source((bad + "\n\n" + VALID_BLOCK).encode())
                self.assertEqual([d.code for d in parsed.errors], ["invalid_index"])
                self.assertEqual((parsed.errors[0].block, parsed.errors[0].line), (1, 1))
                self.assertEqual([entry.source_index for entry in parsed.entries], [7])
                self.assertEqual(parsed.entries[0].ordinal, 2)

    def test_indices_beyond_storage_range_are_diagnostics(self):
        for index in ("9223372036854775808", "9" * 4301):
            with self.subTest(index_digits=len(index)):
                bad = VALID_BLOCK.replace("7\n", index + "\n", 1)
                parsed = parse_source((bad + "\n\n" + VALID_BLOCK).encode())
                self.assertEqual(
                    [(d.code, d.block, d.line) for d in parsed.errors],
                    [("index_out_of_range", 1, 1)],
                )
                self.assertEqual([entry.source_index for entry in parsed.entries], [7])

    def test_timestamps_beyond_storage_range_are_diagnostics(self):
        timings = (
            "3000000000000:00:00,001 --> 3000000000000:00:01,002",
            "2562047788015:12:55,806 --> 2562047788015:12:55,808",
            f"{'9' * 4301}:00:00,001 --> {'9' * 4301}:00:01,002",
        )
        for timing in timings:
            with self.subTest(timing_length=len(timing)):
                raw = ("1\n" + timing + "\nToo large.\n\n" + VALID_BLOCK).encode()
                parsed = parse_source(raw)
                self.assertEqual(
                    [(d.code, d.block, d.line) for d in parsed.errors],
                    [("timestamp_out_of_range", 1, 2)],
                )
                self.assertEqual([entry.source_index for entry in parsed.entries], [7])

    def test_largest_supported_values_and_long_zero_padding_remain_valid(self):
        raw = (
            "9223372036854775807\n"
            "2562047788015:12:55,806 --> 2562047788015:12:55,807\n"
            "At the supported boundary.\n"
        ).encode()
        parsed = parse_source(raw)
        self.assertEqual(parsed.errors, [])
        entry = parsed.entries[0]
        self.assertEqual(entry.source_index, 9223372036854775807)
        self.assertEqual((entry.start_ms, entry.end_ms), (9223372036854775806, 9223372036854775807))

        padded = (
            f"{'0' * 4301}7\n"
            f"{'0' * 4301}00:00:01,001 --> {'0' * 4301}00:00:02,009\n"
            "Padding is not an oversized value.\n"
        ).encode()
        parsed = parse_source(padded)
        self.assertEqual(parsed.errors, [])
        self.assertEqual(parsed.entries[0].source_index, 7)
        self.assertEqual((parsed.entries[0].start_ms, parsed.entries[0].end_ms), (1001, 2009))

    def test_invalid_timestamp_syntax_or_ranges_is_diagnosed(self):
        timings = (
            "00:00:01.001 --> 00:00:02.009",
            "0:00:01,001 --> 00:00:02,009",
            "00:00:01,01 --> 00:00:02,009",
            "00:60:01,001 --> 01:00:02,009",
            "00:00:60,001 --> 00:01:02,009",
            "00:00:01,001 --> 00:60:02,009",
            "00:00:01,001 --> 00:01:60,009",
            "00:00:01,001 -> 00:00:02,009",
            "00:00:01,001 --> 00:00:02,009 trailing garbage",
        )
        for timing in timings:
            with self.subTest(timing=timing):
                raw = ("1\n" + timing + "\nInvalid timing.\n\n" + VALID_BLOCK).encode()
                parsed = parse_source(raw)
                self.assertEqual(
                    [(d.code, d.block, d.line) for d in parsed.errors],
                    [("invalid_timestamp", 1, 2)],
                )
                self.assertEqual(len(parsed.entries), 1)

    def test_zero_and_negative_duration_are_errors(self):
        for end in ("00:00:01,001", "00:00:01,000"):
            with self.subTest(end=end):
                raw = (f"1\n00:00:01,001 --> {end}\nInvalid duration.\n\n" + VALID_BLOCK).encode()
                parsed = parse_source(raw)
                self.assertEqual(
                    [(d.code, d.block, d.line) for d in parsed.errors],
                    [("invalid_duration", 1, 2)],
                )
                self.assertEqual(len(parsed.entries), 1)

    def test_duplicate_index_and_decreasing_time_are_retained_with_warnings(self):
        raw = (
            "8\n00:00:02,001 --> 00:00:03,001\nFirst.\n\n"
            "8\n00:00:01,001 --> 00:00:01,999\nSecond.\n"
        ).encode()
        parsed = parse_source(raw)
        self.assertEqual(parsed.errors, [])
        self.assertEqual([entry.source_index for entry in parsed.entries], [8, 8])
        self.assertEqual([entry.text for entry in parsed.entries], ["First.", "Second."])
        self.assertEqual([entry.ordinal for entry in parsed.entries], [1, 2])
        self.assertEqual(
            [(d.code, d.severity, d.block, d.line) for d in parsed.diagnostics],
            [("duplicate_index", "warning", 2, 5), ("out_of_order_time", "warning", 2, 6)],
        )
        report = parsed.report()
        self.assertEqual((report["error_count"], report["warning_count"]), (0, 2))
        self.assertEqual(report["diagnostics"][0]["code"], "duplicate_index")
        self.assertEqual(report["diagnostics"][0]["block"], 2)

    def test_empty_or_all_invalid_source_is_explicitly_rejected(self):
        for raw, expected_codes in (
            (b"", ["no_entries"]),
            (b" \r\n\t\r\n", ["no_entries"]),
            (b"not an SRT block", ["invalid_block", "no_entries"]),
        ):
            with self.subTest(raw=raw):
                parsed = parse_source(raw)
                self.assertEqual(parsed.entries, [])
                self.assertEqual([d.code for d in parsed.errors], expected_codes)
                self.assertEqual(parsed.errors[-1].line, 1)

    def test_report_truncates_details_without_losing_total_error_count(self):
        bad = "bad-index\n00:00:00,000 --> 00:00:01,000\nInvalid index."
        raw = ("\n\n".join([bad] * 101 + [VALID_BLOCK])).encode()
        parsed = parse_source(raw)
        report = parsed.report()
        self.assertEqual(len(parsed.errors), 101)
        self.assertEqual(report["block_count"], 102)
        self.assertEqual(report["entry_count"], 1)
        self.assertEqual(report["error_count"], 101)
        self.assertEqual(report["warning_count"], 0)
        self.assertTrue(report["diagnostics_truncated"])
        self.assertEqual(len(report["diagnostics"]), 100)
        self.assertEqual(report["diagnostics"][99]["block"], 100)


class RenderSourceTests(unittest.TestCase):
    def test_mapping_export_matches_golden_bytes_without_reflow(self):
        entries = [
            {
                "source_index": 42,
                "start_ms": 1001,
                "end_ms": 62987,
                "source_text": "  <i>[DOOR OPENS]</i>  \n- Ő itt van.\t",
            },
            {
                "source_index": 9,
                "start_ms": 360123004,
                "end_ms": 360123005,
                "source_text": "♪ Hello & goodbye ♪",
            },
        ]
        exported = render_source(entries)
        self.assertEqual(
            exported,
            (
                "42\n00:00:01,001 --> 00:01:02,987\n"
                "  <i>[DOOR OPENS]</i>  \n- Ő itt van.\t\n\n"
                "9\n100:02:03,004 --> 100:02:03,005\n♪ Hello & goodbye ♪\n"
            ).encode("utf-8"),
        )
        self.assertNotIn(b"\r", exported)
        self.assertFalse(exported.startswith(b"\xef\xbb\xbf"))
        parsed = parse_source(exported)
        self.assertEqual(parsed.errors, [])
        self.assertEqual(
            [(e.source_index, e.start_ms, e.end_ms, e.text) for e in parsed.entries],
            [
                (42, 1001, 62987, "  <i>[DOOR OPENS]</i>  \n- Ő itt van.\t"),
                (9, 360123004, 360123005, "♪ Hello & goodbye ♪"),
            ],
        )

    def test_timestamp_format_retains_milliseconds_at_boundaries(self):
        for milliseconds, expected in (
            (0, "00:00:00,000"),
            (1, "00:00:00,001"),
            (59999, "00:00:59,999"),
            (60000, "00:01:00,000"),
            (3599999, "00:59:59,999"),
            (3600000, "01:00:00,000"),
            (360123004, "100:02:03,004"),
        ):
            with self.subTest(milliseconds=milliseconds):
                self.assertEqual(format_timestamp(milliseconds), expected)

    def test_timestamp_format_rejects_lossy_or_invalid_values(self):
        for value in (-1, 1.5, "1000", True, None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    format_timestamp(value)


class ModelFreeImportTests(unittest.TestCase):
    def test_package_parser_and_project_import_without_site_packages_or_models(self):
        script = textwrap.dedent(
            """
            import json
            import sys

            forbidden = (
                "subtitle_translator.config", "subtitle_translator.translator",
                "subtitle_translator.providers", "subtitle_translator.core.plugin_loader",
                "subtitle_translator.marian_client", "subtitle_translator.ollama_client",
                "torch", "transformers", "ollama", "google", "requests", "dotenv",
            )

            class RejectModelImports:
                def find_spec(self, fullname, path=None, target=None):
                    if any(fullname == name or fullname.startswith(name + ".") for name in forbidden):
                        raise AssertionError("Model/config import attempted: " + fullname)

            sys.meta_path.insert(0, RejectModelImports())
            import subtitle_translator
            from subtitle_translator import SRTParser, SubtitleEntry
            from subtitle_translator.project import ProjectService
            from subtitle_translator.project.srt import parse_source
            from subtitle_translator.srt_format import format_timestamp

            assert subtitle_translator.__version__
            assert "Config" in dir(subtitle_translator)
            assert SRTParser is not None and SubtitleEntry is not None and ProjectService is not None
            assert format_timestamp(1001) == "00:00:01,001"
            assert parse_source(b"1\\n00:00:01,001 --> 00:00:02,002\\nHello.").entries[0].text == "Hello."
            assert not any(
                loaded == name or loaded.startswith(name + ".")
                for loaded in sys.modules for name in forbidden
            )
            print(json.dumps({"ok": True, "site_loaded": "site" in sys.modules}))
            """
        )
        completed = subprocess.run(
            [sys.executable, "-S", "-c", script],
            cwd=REPOSITORY,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(json.loads(completed.stdout), {"ok": True, "site_loaded": False})


if __name__ == "__main__":
    unittest.main()
