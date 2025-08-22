#!/usr/bin/env python3
"""
Test script for cross-entry sentence detection functionality.
"""

import sys
from pathlib import Path

# Add the project root to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from subtitle_translator.config import Config
from subtitle_translator.translator import SubtitleTranslator
from subtitle_translator.srt_parser import SubtitleEntry
from datetime import timedelta

def create_test_entries():
    """Create test subtitle entries to test cross-entry detection."""
    return [
        # Case 1: Cross-entry sentence (should be grouped)
        SubtitleEntry(1, timedelta(seconds=1), timedelta(seconds=3), "This is now"),
        SubtitleEntry(2, timedelta(seconds=3), timedelta(seconds=5), "an NYPD homicide investigation,"),
        SubtitleEntry(3, timedelta(seconds=5), timedelta(seconds=7), "so if we collar Hughes, we'll let you know."),
        
        # Case 2: Dialogue (should be separate)
        SubtitleEntry(4, timedelta(seconds=8), timedelta(seconds=10), "- Have you seen my daughter?"),
        SubtitleEntry(5, timedelta(seconds=10), timedelta(seconds=12), "- No, lo siento."),
        
        # Case 3: Single complete sentence
        SubtitleEntry(6, timedelta(seconds=13), timedelta(seconds=15), "I understand completely."),
        
        # Case 4: Another cross-entry sentence
        SubtitleEntry(7, timedelta(seconds=16), timedelta(seconds=18), "We need to find"),
        SubtitleEntry(8, timedelta(seconds=18), timedelta(seconds=20), "the missing evidence quickly."),
    ]

def test_cross_entry_detection():
    """Test the cross-entry sentence detection algorithm."""
    print("Testing Cross-Entry Sentence Detection")
    print("=" * 50)
    
    # Create config with cross-entry detection enabled
    config = Config()
    config.translation_backend = "marian"
    config.marian.multiline_strategy = "smart"
    config.marian.cross_entry_detection = True
    config.verbose = True
    
    # Create translator
    translator = SubtitleTranslator(config)
    
    # Create test entries
    entries = create_test_entries()
    
    print("Original entries:")
    for entry in entries:
        print(f"  [{entry.index}] {entry.text}")
    
    print("\nDetecting cross-entry groups...")
    
    # Test the detection algorithm
    groups = translator._detect_cross_entry_groups(entries)
    
    print(f"\nDetected {len(groups)} groups:")
    for i, group in enumerate(groups):
        print(f"  Group {i+1}: Entries {group}")
        for idx in group:
            print(f"    [{entries[idx].index}] {entries[idx].text}")
        print()
    
    # Test individual detection methods
    print("Individual sentence completion analysis:")
    for entry in entries:
        completes = translator._entry_completes_sentence(entry)
        print(f"  [{entry.index}] '{entry.text}' -> Completes sentence: {completes}")
    
    print("\nContinuation analysis:")
    for i in range(len(entries) - 1):
        current = entries[i]
        next_entry = entries[i + 1]
        continues = translator._entry_continues_sentence(current, next_entry)
        print(f"  [{current.index}] -> [{next_entry.index}]: Continues sentence: {continues}")

if __name__ == "__main__":
    test_cross_entry_detection()
