"""Display wrapping preserves markup meaning and the caller's cue anchors."""

from contextlib import redirect_stdout
from datetime import timedelta
from html.parser import HTMLParser
import io
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import reformat_srt
from subtitle_translator.formatting import format_subtitle_texts, split_subtitle_text
from subtitle_translator.srt_parser import SRTParser, SubtitleEntry
from subtitle_translator.srt_parser import split_subtitle_text as legacy_split


ROOT = Path(__file__).resolve().parents[2]


class StyledCharacters(HTMLParser):
    """Compare visible characters and their actual inline scope after reflow."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.scope = []
        self.characters = []

    def handle_starttag(self, tag, attrs):
        self.scope.append((tag, tuple(attrs)))

    def handle_endtag(self, tag):
        if not self.scope or self.scope[-1][0] != tag:
            raise AssertionError(f"Unbalanced tag: {tag}")
        self.scope.pop()

    def handle_data(self, data):
        self.characters.extend((character, tuple(self.scope)) for character in data if not character.isspace())


def styled(text):
    parser = StyledCharacters()
    parser.feed(text)
    parser.close()
    return parser


class SharedFormattingTests(unittest.TestCase):
    def test_legacy_and_standalone_use_the_shared_function(self):
        self.assertIs(legacy_split, split_subtitle_text)
        self.assertIs(reformat_srt.split_subtitle_text, split_subtitle_text)

    def test_inline_and_nested_scope_is_preserved_for_all_methods(self):
        text = 'plain <b>bold <i>two words</i> bold</b> <font title="a>b" color="red">red &amp; warm</font> plain'
        expected = styled(text).characters
        for method in ("word", "even", "char"):
            with self.subTest(method=method):
                output = split_subtitle_text(text, 12, method)
                self.assertEqual(styled(output).characters, expected)
                for line in output.split("\n"):
                    self.assertEqual(styled(line).scope, [])
                    parser = HTMLParser(convert_charrefs=True)
                    visible = []
                    parser.handle_data = visible.append
                    parser.feed(line)
                    self.assertLessEqual(len("".join(visible)), 12)

    def test_tags_dont_make_a_short_visible_line_wrap(self):
        text = '<font color="a very long attribute">small</font>'
        self.assertEqual(split_subtitle_text(text, 5), text)

    def test_entities_are_atomic_and_count_by_rendered_width(self):
        self.assertEqual(split_subtitle_text("a &amp; b", 3, "word"), "a &amp;\nb")
        self.assertEqual(split_subtitle_text("a&amp;b", 1, "char"), "a\n&amp;\nb")
        self.assertEqual(split_subtitle_text("one&nbsp;two", 3, "word"), "one&nbsp;two")

    def test_existing_speaker_lines_and_paragraphs_are_hard_boundaries(self):
        text = "- First speaker.\n- Second speaker.\n\nA new paragraph."
        self.assertEqual(split_subtitle_text(text, 100, target_line_count=2), text)
        output = split_subtitle_text(text, 10)
        self.assertIn("speaker.\n- Second", output)
        self.assertIn("\n\n", output)
        self.assertEqual(re.sub(r"\s+", " ", output), re.sub(r"\s+", " ", text))

    def test_styles_cross_existing_rows_and_cues_without_moving_text(self):
        source = ["plain <i>one two\nthree", "four <b>five six</b></i> plain", "normal"]
        output = format_subtitle_texts(iter(source), 8)
        self.assertEqual(len(output), len(source))
        self.assertEqual(styled("\n".join(output)).characters, styled("\n".join(source)).characters)
        for original, formatted in zip(source, output):
            self.assertEqual(
                re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", original)),
                re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", formatted)),
            )
            for line in formatted.split("\n"):
                self.assertEqual(styled(line).scope, [])
        self.assertEqual(output[-1], "normal")

    def test_unmatched_tags_are_retained_without_invented_openings(self):
        self.assertEqual(split_subtitle_text("plain</i> tail", 100), "plain</i> tail")
        self.assertEqual(format_subtitle_texts(["<i>open", "continues"], 100), ["<i>open</i>", "<i>continues</i>"])
        self.assertIn("</b>", split_subtitle_text("<b><i>bad</b> close</i>", 100))

    def test_legacy_target_line_count_is_optional_and_soft(self):
        text = "This translated sentence has enough words to require several display rows under the ordinary narrow width."
        self.assertEqual(len(split_subtitle_text(text, 20, target_line_count=2).splitlines()), 2)
        self.assertGreater(len(split_subtitle_text(text, 20).splitlines()), 2)
        self.assertEqual(split_subtitle_text("Short enough", 42, target_line_count=2), "Short enough")
        self.assertEqual(split_subtitle_text("unbreakable", 3, "word"), "unbreakable")

    def test_document_row_count_hints_are_per_cue_and_cannot_truncate(self):
        text = "A sentence that requires many narrow display rows to fit all these words."
        output = format_subtitle_texts([text, text], 15, target_line_counts=[2, 3])
        self.assertEqual([len(cue.splitlines()) for cue in output], [2, 3])
        for hints in ([2], [2, 3, 4]):
            with self.subTest(hints=hints), self.assertRaises(ValueError):
                format_subtitle_texts([text, text], target_line_counts=hints)

    def test_entry_wrapping_keeps_index_and_timestamps(self):
        entry = SubtitleEntry(71, timedelta(milliseconds=1234), timedelta(milliseconds=5678), "Some words to wrap here")
        before = (entry.index, entry.start_time, entry.end_time)
        output = entry.to_srt_format(max_row_length=7)
        self.assertEqual(output.splitlines()[:2], ["71", "00:00:01,234 --> 00:00:05,678"])
        self.assertEqual((entry.index, entry.start_time, entry.end_time), before)

    def test_lightweight_import_needs_no_yaml_or_model_packages(self):
        result = subprocess.run(
            [sys.executable, "-S", "-c", "import reformat_srt, subtitle_translator.srt_parser, sys; "
             "assert not {'yaml', 'torch', 'transformers', 'ollama', 'google'}.intersection(sys.modules)"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class StandaloneFormattingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "synthetic-copy.srt"

    def reformat(self, **kwargs):
        with redirect_stdout(io.StringIO()):
            return reformat_srt.parse_srt_file(self.path, **kwargs)

    def test_preserves_raw_anchors_bom_newlines_and_cross_cue_scope(self):
        raw = ("\ufeff0007\r\n00:00:01,000  -->  00:00:03,000\r\nplain <i>one two three\r\n\r\n"
               "0099\r\n00:00:04,000 --> 00:00:06,000\r\nfour five</i> plain\r\n").encode("utf-8")
        self.path.write_bytes(raw)
        self.assertTrue(self.reformat(max_row_length=10))
        output = self.path.read_bytes()
        self.assertTrue(output.startswith(b"\xef\xbb\xbf0007\r\n00:00:01,000  -->  00:00:03,000\r\n"))
        self.assertIn(b"\r\n\r\n0099\r\n00:00:04,000 --> 00:00:06,000\r\n", output)
        self.assertNotIn(b"\n", output.replace(b"\r\n", b""))
        blocks = output.decode("utf-8-sig").replace("\r\n", "\n").strip().split("\n\n")
        self.assertEqual(len(blocks), 2)
        text = "\n".join("\n".join(block.splitlines()[2:]) for block in blocks)
        self.assertEqual(styled(text).characters, styled("plain <i>one two three four five</i> plain").characters)

    def test_legacy_document_export_preserves_cross_cue_inline_scope_and_hints(self):
        entries = [
            SubtitleEntry(7, timedelta(seconds=1), timedelta(seconds=3),
                          "plain <i>one two three four", original_line_count=2),
            SubtitleEntry(99, timedelta(seconds=4), timedelta(seconds=6),
                          "five <b>six seven</b> eight</i> plain", original_line_count=3),
        ]
        original_texts = [entry.text for entry in entries]
        SRTParser().write_file(entries, self.path, max_row_length=8)
        blocks = self.path.read_text(encoding="utf-8").strip().split("\n\n")
        self.assertEqual([block.splitlines()[:2] for block in blocks], [
            ["7", "00:00:01,000 --> 00:00:03,000"],
            ["99", "00:00:04,000 --> 00:00:06,000"],
        ])
        output_texts = ["\n".join(block.splitlines()[2:]) for block in blocks]
        self.assertEqual([len(text.splitlines()) for text in output_texts], [2, 3])
        expected = styled("\n".join(original_texts)).characters
        self.assertEqual(styled("\n".join(output_texts)).characters, expected)
        for original, output in zip(original_texts, output_texts):
            self.assertEqual(
                re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", original)),
                re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", output)),
            )
            for row in output.splitlines():
                self.assertEqual(styled(row).scope, [])
        self.assertEqual([entry.text for entry in entries], original_texts)

    def test_any_malformed_block_leaves_entire_input_unchanged(self):
        valid = b"1\n00:00:00,000 --> 00:00:01,000\nSome words here\n\n"
        for invalid in (b"broken\n", b"2\nnot a timestamp\ntext\n", b"2\n00:80:00,000 --> 00:81:00,000\ntext\n"):
            with self.subTest(invalid=invalid):
                original = valid + invalid
                self.path.write_bytes(original)
                self.assertFalse(self.reformat(max_row_length=5))
                self.assertEqual(self.path.read_bytes(), original)

    def test_missing_separator_and_decode_failure_leave_input_unchanged(self):
        for original in (
            b"1\n00:00:00,000 --> 00:00:01,000\none\n2\n00:00:02,000 --> 00:00:03,000\ntwo\n",
            b"1\n00:00:00,000 --> 00:00:01,000\n\xff\n",
        ):
            self.path.write_bytes(original)
            self.assertFalse(self.reformat())
            self.assertEqual(self.path.read_bytes(), original)

    def test_failed_replace_preserves_input_and_removes_temporary_output(self):
        original = b"1\n00:00:00,000 --> 00:00:01,000\nSome words here\n"
        self.path.write_bytes(original)
        with patch("reformat_srt.os.replace", side_effect=PermissionError("synthetic blocked replace")):
            self.assertFalse(self.reformat(max_row_length=5))
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])


if __name__ == "__main__":
    unittest.main()
