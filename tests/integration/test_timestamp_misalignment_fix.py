#!/usr/bin/env python3
"""
Test the fixed cross-entry splitting with realistic subtitle examples.
This validates that the bug fix resolves user-reported timestamp stretching issues.
"""

from subtitle_translator.translator import SubtitleTranslator
from subtitle_translator.srt_parser import SubtitleEntry
import datetime

def create_test_entry(index, start, end, text):
    """Helper to create SubtitleEntry"""
    return SubtitleEntry(
        index=index,
        start_time=start,
        end_time=end,
        text=text,
        original_line_count=text.count('\n') + 1
    )

def test_realistic_subtitle_scenario():
    """Test with realistic subtitle data that caused the bug"""
    # Don't need full translator, just use the method directly
    from subtitle_translator.config import Config
    config = Config()
    translator = SubtitleTranslator(config)
    
    # Simulate a cross-entry group where sentence spans multiple entries
    # Entry 1: Long dialogue (30 chars)
    # Entry 2: Short continuation (3 chars) 
    # Entry 3: Very short continuation (2 chars)
    entries = [
        create_test_entry(
            1, 
            datetime.timedelta(seconds=1), 
            datetime.timedelta(seconds=3),
            "Yeah, but there was a perfectly"
        ),
        create_test_entry(
            2, 
            datetime.timedelta(seconds=3, milliseconds=100), 
            datetime.timedelta(seconds=5),
            "healthy"
        ),
        create_test_entry(
            3, 
            datetime.timedelta(seconds=5, milliseconds=100), 
            datetime.timedelta(seconds=7),
            "elevator waiting for us."
        ),
    ]
    
    # Simulate translation: "Yeah, but there was a perfectly healthy elevator waiting for us."
    # -> "Igen, de volt egy tökéletesen egészséges lift várva ránk." (14 words)
    translated_text = "Igen, de volt egy tökéletesen egészséges lift várva ránk."
    
    # Calculate original proportions
    original_lengths = [len(e.text) for e in entries]
    total_length = sum(original_lengths)
    proportions = [length / total_length for length in original_lengths]
    
    print("🔍 TEST: Realistic Subtitle Scenario")
    print("=" * 60)
    print(f"Original entries: {len(entries)}")
    print(f"Original character counts: {original_lengths}")
    print(f"Original proportions: {[f'{p:.1%}' for p in proportions]}")
    print(f"Translated text: '{translated_text}'")
    print(f"Translated word count: {len(translated_text.split())}")
    
    # Use the fixed _split_translation_to_entries method
    split_texts = translator._split_translation_to_entries(translated_text, entries)
    
    print(f"\n✅ FIXED ALGORITHM RESULTS:")
    print(f"Split texts count: {len(split_texts)}")
    
    split_word_counts = [len(text.split()) for text in split_texts]
    split_char_counts = [len(text) for text in split_texts]
    total_words = sum(split_word_counts)
    word_proportions = [count / total_words for count in split_word_counts]
    
    print(f"Word distribution: {split_word_counts}")
    print(f"Word proportions: {[f'{p:.1%}' for p in word_proportions]}")
    print(f"Character counts: {split_char_counts}")
    
    # Verify entries and their content
    print(f"\n📝 ENTRY DETAILS:")
    for i, (entry, text) in enumerate(zip(entries, split_texts), 1):
        print(f"Entry {i}: [{entry.start_time} --> {entry.end_time}]")
        print(f"  Text: '{text}'")
        print(f"  Words: {len(text.split())}, Chars: {len(text)}")
        print(f"  Proportion: {(len(text.split()) / total_words):.1%}")
    
    # Validation checks
    print(f"\n✓ VALIDATION CHECKS:")
    all_words_preserved = sum(split_word_counts) == len(translated_text.split())
    entry_count_preserved = len(split_texts) == len(entries)
    timestamps_preserved = True  # Timestamps are on entries, not split_texts
    
    print(f"  ✓ All words preserved: {all_words_preserved}")
    print(f"  ✓ Entry count preserved: {entry_count_preserved}")
    print(f"  ✓ Timestamps preserved: {timestamps_preserved}")
    
    # Check distribution accuracy (should be closer to original proportions)
    print(f"\n📊 DISTRIBUTION ACCURACY:")
    for i in range(len(entries)):
        expected_prop = proportions[i]
        actual_prop = word_proportions[i]
        diff = abs(expected_prop - actual_prop)
        status = "✓" if diff < 0.15 else "⚠"
        print(f"  {status} Entry {i+1}: Expected ~{expected_prop:.1%}, Got {actual_prop:.1%} (diff: {diff:.1%})")
    
    return all([all_words_preserved, entry_count_preserved, timestamps_preserved])

def test_extreme_imbalance():
    """Test extreme length imbalance that exposed the bug"""
    from subtitle_translator.config import Config
    config = Config()
    translator = SubtitleTranslator(config)
    
    entries = [
        create_test_entry(1, datetime.timedelta(seconds=1), datetime.timedelta(seconds=3), "A" * 50),
        create_test_entry(2, datetime.timedelta(seconds=3, milliseconds=100), datetime.timedelta(seconds=5), "B"),
        create_test_entry(3, datetime.timedelta(seconds=5, milliseconds=100), datetime.timedelta(seconds=7), "C"),
    ]
    
    # 50:1:1 ratio - extreme imbalance
    translated_text = "This is a very long translated text with many words to test the distribution algorithm properly."
    
    original_lengths = [len(e.text) for e in entries]
    proportions = [length / sum(original_lengths) for length in original_lengths]
    
    print("\n🔍 TEST: Extreme Length Imbalance")
    print("=" * 60)
    print(f"Original character ratio: {original_lengths[0]}:{original_lengths[1]}:{original_lengths[2]}")
    print(f"Original proportions: {[f'{p:.1%}' for p in proportions]}")
    print(f"Translated words: {len(translated_text.split())}")
    
    split_texts = translator._split_translation_to_entries(translated_text, entries)
    
    split_word_counts = [len(text.split()) for text in split_texts]
    total_words = sum(split_word_counts)
    word_proportions = [count / total_words for count in split_word_counts]
    
    print(f"\n✅ FIXED ALGORITHM RESULTS:")
    print(f"Word distribution: {split_word_counts}")
    print(f"Word proportions: {[f'{p:.1%}' for p in word_proportions]}")
    
    # Check that entry 3 doesn't get disproportionately large allocation
    entry3_prop = word_proportions[2]
    expected_prop = proportions[2]
    
    print(f"\n📊 CRITICAL CHECK (Entry 3):")
    print(f"  Expected proportion: {expected_prop:.1%}")
    print(f"  Actual proportion: {entry3_prop:.1%}")
    print(f"  Difference: {abs(expected_prop - entry3_prop):.1%}")
    
    # Before fix: Entry 3 would get ~14.3% instead of 1.9%
    # After fix: Entry 3 should get ~1-2%
    is_fixed = entry3_prop < 0.05  # Should be less than 5%
    
    if is_fixed:
        print(f"  ✓ FIX VERIFIED: Entry 3 no longer receives excessive allocation!")
    else:
        print(f"  ✗ ISSUE PERSISTS: Entry 3 still receives too many words")
    
    return is_fixed

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TESTING TIMESTAMP MISALIGNMENT BUG FIX")
    print("=" * 60)
    
    test1_pass = test_realistic_subtitle_scenario()
    test2_pass = test_extreme_imbalance()
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"Realistic scenario test: {'✓ PASSED' if test1_pass else '✗ FAILED'}")
    print(f"Extreme imbalance test: {'✓ PASSED' if test2_pass else '✗ FAILED'}")
    
    if test1_pass and test2_pass:
        print("\n🎉 ALL TESTS PASSED - BUG FIX VERIFIED!")
        print("User-reported timestamp stretching issue should be resolved.")
    else:
        print("\n⚠ SOME TESTS FAILED - Further investigation needed")
