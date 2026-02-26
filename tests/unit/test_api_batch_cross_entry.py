"""
Tests for cross-entry pre-merge in _translate_entries_api_batch().

The key bug being tested: Gemini (and other smart API batch providers) would
"helpfully" combine cross-entry sentence continuations into a single output key,
shifting every subsequent translation by one position.

The fix: pre-merge continuation groups before the API call; split results back
proportionally after.
"""

import unittest
from datetime import timedelta
from unittest import mock

from subtitle_translator.srt_parser import SubtitleEntry
from subtitle_translator.config import Config
from subtitle_translator.translator import SubtitleTranslator


def _entry(index: int, text: str, start_sec: float = 0.0, end_sec: float = 1.0) -> SubtitleEntry:
    return SubtitleEntry(
        index=index,
        start_time=timedelta(seconds=start_sec),
        end_time=timedelta(seconds=end_sec),
        text=text,
        original_line_count=text.count('\n') + 1,
    )


def _make_translator(translate_fn=None) -> SubtitleTranslator:
    """Build a SubtitleTranslator with a mock provider that supports api_batch."""
    config = Config()
    config.verbose = False

    translator = SubtitleTranslator.__new__(SubtitleTranslator)
    translator.config = config
    translator.logger = mock.MagicMock()
    translator.parser = mock.MagicMock()
    translator.multi_model_orchestrator = None

    mock_provider = mock.MagicMock()
    mock_provider.supports_api_batch = True
    if translate_fn:
        mock_provider.translate_api_batch.side_effect = translate_fn

    translator.translation_client = mock_provider
    return translator


class TestApiBatchCrossEntryPreMerge(unittest.TestCase):
    """Test that continuation entries are pre-merged before the API call."""

    def test_continuation_entries_are_merged_in_api_call(self):
        """Entries forming a cross-sentence should be sent as a single API text."""
        entries = [
            _entry(84, "Hey, I need to talk to you.", 210.0, 211.5),
            _entry(85, "Finally. You've been ducking me", 211.6, 213.0),  # no ending punctuation
            _entry(86, "since I got back from Sweden.", 213.0, 214.2),    # lowercase start → continuation
            _entry(87, "We agreed to be discreet, remember?", 214.3, 215.8),
            _entry(88, "Mmm.", 215.9, 216.5),
        ]

        captured_texts: list = []

        def fake_batch(texts):
            captured_texts.extend(texts)
            # Return one translation per collapsed text
            return [f"HU({t})" for t in texts]

        translator = _make_translator(fake_batch)
        progress = mock.MagicMock()
        progress.total_entries = len(entries)
        progress.add_translated_entry = mock.MagicMock()

        translator._translate_entries_api_batch(entries, progress, start_offset=0)

        # Entries 85+86 are a cross-entry sentence, so they should be collapsed
        # into a SINGLE text in the API call, reducing 5 entries to 4 calls.
        self.assertEqual(len(captured_texts), 4,
                         f"Expected 4 collapsed texts, got {len(captured_texts)}: {captured_texts}")

        # The merged text should combine both lines
        self.assertIn("ducking me", captured_texts[1])  # second group = merged 85+86
        self.assertIn("Sweden", captured_texts[1])

    def test_non_continuation_entries_are_not_merged(self):
        """Entries with proper sentence endings must NOT be merged."""
        entries = [
            _entry(1, "First complete sentence.", 0.0, 1.0),
            _entry(2, "Second complete sentence.", 1.0, 2.0),
            _entry(3, "Third complete sentence.", 2.0, 3.0),
        ]

        captured_texts: list = []

        def fake_batch(texts):
            captured_texts.extend(texts)
            return [f"HU({t})" for t in texts]

        translator = _make_translator(fake_batch)
        progress = mock.MagicMock()
        progress.total_entries = len(entries)
        progress.add_translated_entry = mock.MagicMock()

        translator._translate_entries_api_batch(entries, progress)

        # Each entry is a complete sentence — no merging should happen
        self.assertEqual(len(captured_texts), 3)

    def test_output_entry_count_preserved_after_merge_split(self):
        """Even when entries are pre-merged, the output must have the original entry count."""
        entries = [
            _entry(85, "Finally. You've been ducking me", 211.6, 213.0),
            _entry(86, "since I got back from Sweden.", 213.0, 214.2),
            _entry(87, "We agreed to be discreet, remember?", 214.3, 215.8),
        ]

        def fake_batch(texts):
            # Simulate returning one translation per collapsed text
            return [f"HU:{t}" for t in texts]

        translator = _make_translator(fake_batch)
        progress = mock.MagicMock()
        progress.total_entries = len(entries)

        added: list = []
        progress.add_translated_entry.side_effect = added.append

        translator._translate_entries_api_batch(entries, progress)

        # Must have 3 output entries even though the API received fewer texts
        self.assertEqual(len(added), 3,
                         f"Expected 3 output entries, got {len(added)}")

    def test_entry_indices_and_timestamps_preserved(self):
        """After expand, each output entry keeps its original index and timestamps."""
        entries = [
            _entry(85, "You've been ducking me", 211.6, 213.0),
            _entry(86, "since I got back from Sweden.", 213.0, 214.2),
        ]

        def fake_batch(texts):
            return ["Kerültél engem mióta visszajöttem Svédországból."]

        translator = _make_translator(fake_batch)
        progress = mock.MagicMock()
        progress.total_entries = len(entries)

        added: list = []
        progress.add_translated_entry.side_effect = added.append

        translator._translate_entries_api_batch(entries, progress)

        self.assertEqual(len(added), 2)
        self.assertEqual(added[0].index, 85)
        self.assertEqual(added[1].index, 86)
        self.assertEqual(added[0].start_time, timedelta(seconds=211.6))
        self.assertEqual(added[1].end_time, timedelta(seconds=214.2))

    def test_all_translated_text_is_present_in_output(self):
        """No translated words should be silently lost during the split."""
        entries = [
            _entry(85, "ducking me", 211.6, 213.0),
            _entry(86, "since Sweden.", 213.0, 214.2),
        ]

        def fake_batch(texts):
            return ["Került engem mióta Svédország."]

        translator = _make_translator(fake_batch)
        progress = mock.MagicMock()
        progress.total_entries = len(entries)

        added: list = []
        progress.add_translated_entry.side_effect = added.append

        translator._translate_entries_api_batch(entries, progress)

        combined_output = " ".join(e.text for e in added)
        # All words from the translation should appear somewhere in the outputs
        for word in ["Került", "engem", "mióta", "Svédország."]:
            self.assertIn(word, combined_output,
                          f"Word '{word}' missing from output: {combined_output!r}")


if __name__ == "__main__":
    unittest.main()
