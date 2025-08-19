#!/usr/bin/env python3
"""
Test script to verify the cross-entry sentence detection fix.
"""

import sys
from pathlib import Path
from datetime import timedelta
from subtitle_translator.srt_parser import SubtitleEntry, SRTParser
from subtitle_translator.translator import SubtitleTranslator
from subtitle_translator.config import Config

def parse_timestamp(timestamp_str: str) -> timedelta:
    """Parse SRT timestamp string to timedelta."""
    # Parse "00:00:57,819" format
    time_part, ms_part = timestamp_str.split(',')
    hours, minutes, seconds = map(int, time_part.split(':'))
    milliseconds = int(ms_part)
    
    return timedelta(
        hours=hours,
        minutes=minutes,
        seconds=seconds,
        milliseconds=milliseconds
    )

def test_problematic_case():
    """Test the specific problematic case reported by the user."""
    
    # Create test entries that match the user's problem
    entries = [
        SubtitleEntry(
            index=21,
            start_time=parse_timestamp("00:00:57,819"),
            end_time=parse_timestamp("00:00:59,795"),
            text="(INDISTINCT RADIO CHATTER)"
        ),
        SubtitleEntry(
            index=22,
            start_time=parse_timestamp("00:00:59,819"), 
            end_time=parse_timestamp("00:01:01,825"),
            text="- What do we got?\n- Vic is Nia Fox."
        )
    ]
    
    # Create a minimal config for testing
    config = Config()
    config.translation_backend = "marian"  # We're testing the logic, not actual translation
    
    # Create translator instance (we'll just test the grouping logic)
    translator = SubtitleTranslator(config)
    
    # Test the cross-entry group detection
    groups = translator._detect_cross_entry_groups(entries)
    
    print("Test Case: Problematic cross-entry detection")
    print("=" * 50)
    print("Original entries:")
    for entry in entries:
        print(f"  {entry.index}: {repr(entry.text)}")
    
    print(f"\nDetected groups: {groups}")
    
    # Expected: [[0], [1]] (two separate groups)
    # Problematic: [[0, 1]] (incorrectly joined)
    
    if len(groups) == 2 and groups == [[0], [1]]:
        print("✅ PASS: Entries correctly detected as separate")
        return True
    else:
        print("❌ FAIL: Entries incorrectly grouped together")
        return False

def test_sentence_completion():
    """Test the _entry_completes_sentence function with various cases."""
    
    config = Config()
    config.translation_backend = "marian"
    translator = SubtitleTranslator(config)
    
    test_cases = [
        # (text, expected_result, description)
        ("(INDISTINCT RADIO CHATTER)", True, "Parenthetical sound effect"),
        ("[DOOR SLAMS]", True, "Bracketed sound effect"),
        ("PHONE RINGING", True, "All-caps sound effect"),
        ("MUSIC PLAYING", True, "All-caps music description"),
        ("- What do we got?", True, "Dialogue with dash"),
        ("Hello there.", True, "Complete sentence with period"),
        ("Are you sure?", True, "Question with question mark"),
        ("Wait!", True, "Exclamation"),
        ("I think that", False, "Incomplete sentence"),
        ("He said", False, "Incomplete with conjunction"),
        ("OK", False, "Short caps word (not sound effect)"),
        ("STOP", False, "Short caps word (not sound effect)"),
    ]
    
    print("\nTest Case: Sentence completion detection")
    print("=" * 50)
    
    all_passed = True
    for text, expected, description in test_cases:
        entry = SubtitleEntry(1, parse_timestamp("00:00:01,000"), parse_timestamp("00:00:02,000"), text)
        result = translator._entry_completes_sentence(entry)
        
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"{status}: {description}")
        print(f"         Text: {repr(text)}")
        print(f"         Expected: {expected}, Got: {result}")
        
        if result != expected:
            all_passed = False
        print()
    
    return all_passed

def test_entry_continuation():
    """Test the _entry_continues_sentence function."""
    
    config = Config()
    config.translation_backend = "marian"
    translator = SubtitleTranslator(config)
    
    test_cases = [
        # (current_text, next_text, expected_result, description)
        ("(INDISTINCT RADIO CHATTER)", "- What do we got?", False, "Sound effect should not continue to dialogue"),
        ("I think that", "we should go.", True, "Incomplete sentence continues"),
        ("Hello.", "How are you?", False, "Complete sentence doesn't continue"),
        ("He said", "- I'm fine.", False, "Incomplete doesn't continue to dialogue"),
        ("The car", "(ENGINE STARTS)", False, "Incomplete doesn't continue to sound effect"),
        ("I want to", "tell you something.", True, "Natural continuation"),
        ("- Are you", "coming with us?", True, "Dialogue continuation with lowercase"),
    ]
    
    print("Test Case: Entry continuation detection")
    print("=" * 50)
    
    all_passed = True
    for current_text, next_text, expected, description in test_cases:
        current_entry = SubtitleEntry(1, parse_timestamp("00:00:01,000"), parse_timestamp("00:00:02,000"), current_text)
        next_entry = SubtitleEntry(2, parse_timestamp("00:00:02,000"), parse_timestamp("00:00:03,000"), next_text)
        result = translator._entry_continues_sentence(current_entry, next_entry)
        
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"{status}: {description}")
        print(f"         Current: {repr(current_text)}")
        print(f"         Next: {repr(next_text)}")
        print(f"         Expected: {expected}, Got: {result}")
        
        if result != expected:
            all_passed = False
        print()
    
    return all_passed

def main():
    """Run all tests."""
    print("Testing Cross-Entry Sentence Detection Fix")
    print("=" * 60)
    
    test1_passed = test_problematic_case()
    test2_passed = test_sentence_completion()
    test3_passed = test_entry_continuation()
    
    print("\nOVERALL RESULTS")
    print("=" * 60)
    
    if test1_passed and test2_passed and test3_passed:
        print("🎉 ALL TESTS PASSED! The fix is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please review the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
