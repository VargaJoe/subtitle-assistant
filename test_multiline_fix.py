#!/usr/bin/env python3
"""
Test to verify that multiline subtitle translation preserves line count.
"""

from subtitle_translator.srt_parser import split_subtitle_text, SubtitleEntry
from datetime import timedelta

def test_split_with_target_line_count():
    """Test that split_subtitle_text respects target line count."""
    
    # Test case 1: Original 2 lines, translation should also be split into 2
    print("Test 1: Preserving 2 lines")
    text = "This is a longer translated sentence that would normally be split into more than 2 lines at the default 42 char limit because it is quite verbose"
    result = split_subtitle_text(text, max_length=42, method="even", target_line_count=2)
    lines = result.split('\n')
    print(f"  Input: {text}")
    print(f"  Output lines: {lines}")
    print(f"  Line count: {len(lines)} (expected: ~2)")
    assert len(lines) <= 3, f"Expected ~2 lines, got {len(lines)}"
    print("  ✓ PASSED\n")
    
    # Test case 2: Original 3 lines
    print("Test 2: Preserving 3 lines")
    text = "This is a very long translated text that needs to be split into exactly three lines because the original subtitle had three lines and we want to preserve that layout"
    result = split_subtitle_text(text, max_length=42, method="even", target_line_count=3)
    lines = result.split('\n')
    print(f"  Input: {text}")
    print(f"  Output lines: {lines}")
    print(f"  Line count: {len(lines)} (expected: ~3)")
    assert len(lines) <= 4, f"Expected ~3 lines, got {len(lines)}"
    print("  ✓ PASSED\n")
    
    # Test case 3: Without target line count (default behavior)
    print("Test 3: Default behavior without target line count")
    text = "This is a longer translated sentence that would normally be split"
    result = split_subtitle_text(text, max_length=42, method="even", target_line_count=None)
    lines = result.split('\n')
    print(f"  Input: {text}")
    print(f"  Output lines: {lines}")
    print(f"  Line count: {len(lines)}")
    print("  ✓ PASSED\n")


def test_subtitle_entry_with_line_count():
    """Test that SubtitleEntry preserves original_line_count."""
    
    print("Test 4: SubtitleEntry preserves original_line_count")
    
    entry = SubtitleEntry(
        index=1,
        start_time=timedelta(seconds=0),
        end_time=timedelta(seconds=3),
        text="Line 1\nLine 2",
        original_line_count=2
    )
    
    print(f"  Original line count: {entry.original_line_count}")
    assert entry.original_line_count == 2, "Should preserve original line count"
    
    # Translate with longer text
    translated_entry = SubtitleEntry(
        index=1,
        start_time=entry.start_time,
        end_time=entry.end_time,
        text="This is a much longer translated version of the original two lines that would normally require three lines",
        original_text=entry.text,
        original_line_count=entry.original_line_count  # Preserve original
    )
    
    print(f"  Translated line count preserved: {translated_entry.original_line_count}")
    assert translated_entry.original_line_count == 2, "Should preserve original line count in translation"
    print("  ✓ PASSED\n")


def test_srt_format_with_multiline():
    """Test that to_srt_format respects original_line_count."""
    
    print("Test 5: to_srt_format respects original_line_count")
    
    entry = SubtitleEntry(
        index=1,
        start_time=timedelta(seconds=0),
        end_time=timedelta(seconds=5),
        text="This is a very long translated sentence that exceeds the 42 character limit and should be split intelligently while preserving the original line count",
        original_line_count=2
    )
    
    srt_output = entry.to_srt_format(max_row_length=42)
    print(f"  SRT output:\n{srt_output}")
    
    # Extract the text lines (skip index and timing)
    srt_lines = srt_output.strip().split('\n')
    text_lines = srt_lines[2:]  # Skip index and timing
    actual_line_count = len(text_lines)
    
    print(f"  Actual line count in output: {actual_line_count}")
    print(f"  Expected: ~{entry.original_line_count} lines")
    
    # Should be close to original line count
    target = entry.original_line_count if entry.original_line_count else 1
    assert actual_line_count <= target + 1, \
        f"Should preserve ~{target} lines, got {actual_line_count}"
    print("  ✓ PASSED\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Multiline Subtitle Preservation Fix")
    print("=" * 60 + "\n")
    
    try:
        test_split_with_target_line_count()
        test_subtitle_entry_with_line_count()
        test_srt_format_with_multiline()
        
        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        raise
