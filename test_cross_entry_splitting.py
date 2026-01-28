#!/usr/bin/env python3
"""
Test to verify cross-entry splitting preserves entry count and doesn't lose text.
"""

from subtitle_translator.srt_parser import SubtitleEntry
from datetime import timedelta


def test_split_translation_proportional():
    """Test the FIXED proportional splitting logic for cross-entry groups."""
    
    # NEW FIXED implementation using cumulative approach
    def fixed_split(translated_text: str, original_entries):
        if len(original_entries) == 1:
            return [translated_text]
        
        original_lengths = [len(entry.text.strip()) for entry in original_entries]
        total_original_length = sum(original_lengths)
        
        if total_original_length == 0:
            words = translated_text.split()
            words_per_entry = len(words) // len(original_entries)
            remainder = len(words) % len(original_entries)
            
            result = []
            start_idx = 0
            for i in range(len(original_entries)):
                end_idx = start_idx + words_per_entry + (1 if i < remainder else 0)
                result.append(' '.join(words[start_idx:end_idx]))
                start_idx = end_idx
            return result
        
        translated_words = translated_text.split()
        total_words = len(translated_words)
        
        if total_words == 0:
            return [''] * len(original_entries)
        
        result = []
        words_used = 0
        
        for i, original_entry in enumerate(original_entries):
            if i == len(original_entries) - 1:
                portion_words = translated_words[words_used:]
            else:
                # FIXED: Use cumulative approach
                proportion_so_far = sum(original_lengths[:i+1]) / total_original_length
                target_words_cumulative = int(total_words * proportion_so_far + 0.5)
                
                words_for_this_entry = max(1, target_words_cumulative - words_used)
                portion_words = translated_words[words_used:words_used + words_for_this_entry]
                words_used += len(portion_words)
            
            result.append(' '.join(portion_words) if portion_words else '')
        
        # Safety check
        if len(result) != len(original_entries):
            while len(result) < len(original_entries):
                result.append('')
            result = result[:len(original_entries)]
        
        return result
    
    print("=" * 60)
    print("Testing Cross-Entry Splitting Logic")
    print("=" * 60 + "\n")
    
    # Test case 1: Equal length entries
    print("Test 1: Equal length entries (should split evenly)")
    entries = [
        SubtitleEntry(1, timedelta(0), timedelta(2), "First entry", original_line_count=1),
        SubtitleEntry(2, timedelta(2), timedelta(4), "Second one", original_line_count=1),
        SubtitleEntry(3, timedelta(4), timedelta(6), "Third text", original_line_count=1),
    ]
    translated = "Ez az első bejegyzés második harmadik szöveg"
    result = fixed_split(translated, entries)
    
    print(f"  Original lengths: {[len(e.text) for e in entries]}")
    print(f"  Translated: {translated}")
    print(f"  Split result ({len(result)} parts):")
    for i, part in enumerate(result):
        print(f"    Entry {i+1}: '{part}' ({len(part.split())} words)")
    
    total_words_in = len(translated.split())
    total_words_out = sum(len(part.split()) for part in result)
    print(f"  Words IN: {total_words_in}, Words OUT: {total_words_out}")
    
    if total_words_in != total_words_out:
        print(f"  ❌ WORD LOSS DETECTED: {total_words_in - total_words_out} words lost!")
    else:
        print(f"  ✓ All words preserved")
    
    if len(result) != len(entries):
        print(f"  ❌ ENTRY COUNT MISMATCH: Expected {len(entries)}, got {len(result)}")
    else:
        print(f"  ✓ Entry count preserved")
    print()
    
    # Test case 2: Unequal length entries
    print("Test 2: Unequal length entries (15, 5, 5 chars)")
    entries = [
        SubtitleEntry(1, timedelta(0), timedelta(2), "Very long entry", original_line_count=1),  # 15 chars
        SubtitleEntry(2, timedelta(2), timedelta(4), "Short", original_line_count=1),            # 5 chars
        SubtitleEntry(3, timedelta(4), timedelta(6), "Tiny!", original_line_count=1),            # 5 chars
    ]
    translated = "Nagyon hosszú bejegyzés rövid apró szöveg három négy öt hat hét nyolc"
    result = fixed_split(translated, entries)
    
    print(f"  Original lengths: {[len(e.text) for e in entries]}")
    print(f"  Translated: {translated}")
    print(f"  Split result ({len(result)} parts):")
    for i, part in enumerate(result):
        print(f"    Entry {i+1}: '{part}' ({len(part.split())} words)")
    
    total_words_in = len(translated.split())
    total_words_out = sum(len(part.split()) for part in result)
    print(f"  Words IN: {total_words_in}, Words OUT: {total_words_out}")
    
    if total_words_in != total_words_out:
        print(f"  ❌ WORD LOSS DETECTED: {total_words_in - total_words_out} words lost!")
    else:
        print(f"  ✓ All words preserved")
    
    if len(result) != len(entries):
        print(f"  ❌ ENTRY COUNT MISMATCH: Expected {len(entries)}, got {len(result)}")
    else:
        print(f"  ✓ Entry count preserved")
    print()
    
    # Test case 3: Very unequal (stress test)
    print("Test 3: Very unequal entries (30, 3, 2 chars)")
    entries = [
        SubtitleEntry(1, timedelta(0), timedelta(3), "This is a very long sentence", original_line_count=1),  # 30 chars
        SubtitleEntry(2, timedelta(3), timedelta(4), "Hi!", original_line_count=1),                          # 3 chars
        SubtitleEntry(3, timedelta(4), timedelta(5), "Ok", original_line_count=1),                           # 2 chars
    ]
    translated = "Ez egy nagyon hosszú mondat szia oké plusz még pár szó ami nem fér"
    result = fixed_split(translated, entries)
    
    print(f"  Original lengths: {[len(e.text) for e in entries]}")
    print(f"  Translated: {translated}")
    print(f"  Split result ({len(result)} parts):")
    for i, part in enumerate(result):
        print(f"    Entry {i+1}: '{part}' ({len(part.split())} words)")
    
    total_words_in = len(translated.split())
    total_words_out = sum(len(part.split()) for part in result)
    print(f"  Words IN: {total_words_in}, Words OUT: {total_words_out}")
    
    if total_words_in != total_words_out:
        print(f"  ❌ WORD LOSS DETECTED: {total_words_in - total_words_out} words lost!")
    else:
        print(f"  ✓ All words preserved")
    
    if len(result) != len(entries):
        print(f"  ❌ ENTRY COUNT MISMATCH: Expected {len(entries)}, got {len(result)}")
    else:
        print(f"  ✓ Entry count preserved")
    print()
    
    print("=" * 60)
    print("Test Complete - Check for issues above")
    print("=" * 60)


if __name__ == "__main__":
    test_split_translation_proportional()
