#!/usr/bin/env python3
"""
Test HTML-aware cross-entry detection functionality.
"""

import sys
sys.path.append('.')

from subtitle_translator.srt_parser import SubtitleEntry
from subtitle_translator.translator import SubtitleTranslator
from subtitle_translator.config import Config
import yaml
from datetime import timedelta

def test_html_cross_entry_detection():
    """Test that HTML formatting is preserved during cross-entry translation."""
    
    # Create test config
    config_data = {
        'translation': {
            'backend': 'marian',
            'source_language': 'en',
            'target_language': 'hu'
        },
        'marian': {
            'model': 'Helsinki-NLP/opus-mt-en-hu',
            'multiline_strategy': 'smart',
            'cross_entry_detection': True
        },
        'output': {
            'preserve_formatting': True
        }
    }
    config = Config.from_dict(config_data)
    
    # Create test entries with HTML formatting (based on your example)
    test_entries = [
        SubtitleEntry(
            index=17,
            start_time=timedelta(seconds=268, milliseconds=989),
            end_time=timedelta(seconds=270, milliseconds=752),
            text="<i>Dreams are</i>\n<i>supposed to represent</i>"
        ),
        SubtitleEntry(
            index=18,
            start_time=timedelta(seconds=270, milliseconds=777),
            end_time=timedelta(seconds=273, milliseconds=337),
            text="<i>your subconscious</i>\n<i>wishes and conflicts.</i>"
        ),
        SubtitleEntry(
            index=19,
            start_time=timedelta(seconds=273, milliseconds=362),
            end_time=timedelta(seconds=276, milliseconds=798),
            text="<i>Sort of a private movie</i>\n<i>you write, produce and direct.</i>"
        ),
        SubtitleEntry(
            index=20,
            start_time=timedelta(seconds=277, milliseconds=403),
            end_time=timedelta(seconds=280, milliseconds=167),
            text="<i>Only you can't hide your eyes</i>\n<i>in your dreams.</i>"
        ),
        SubtitleEntry(
            index=21,
            start_time=timedelta(seconds=280, milliseconds=192),
            end_time=timedelta(seconds=282, milliseconds=888),
            text="<i>Even when they're</i>\n<i>scaring you to death.</i>"
        )
    ]
    
    print("Original entries:")
    for entry in test_entries:
        print(f"Entry {entry.index}: {repr(entry.text)}")
    print()
    
    # Test HTML detection
    translator = SubtitleTranslator(config)
    
    # Test individual HTML detection
    print("HTML detection test:")
    for entry in test_entries:
        has_html = translator._contains_html_tags(entry.text)
        print(f"Entry {entry.index} has HTML: {has_html}")
    print()
    
    # Test HTML combination
    print("HTML combination test:")
    combined_text, entry_html_info = translator._combine_entries_with_html(test_entries)
    print(f"Combined clean text: {repr(combined_text)}")
    print()
    print("HTML info per entry:")
    for i, info in enumerate(entry_html_info):
        print(f"Entry {i}: {info}")
    print()
    
    # Test splitting and restoration (simulate translated text)
    simulated_translation = "Az álmok a tudatalatti vágyaidat és konfliktusaidat képviselik, egyfajta privát film, amit írsz, előállítasz és irányítasz, de nem rejtheted el a szemed az álmaidban, még akkor sem, ha halálra rémítenek."
    
    print("Splitting and HTML restoration test:")
    restored_translations = translator._split_translation_with_html(
        simulated_translation, test_entries, entry_html_info
    )
    
    print("Restored translations:")
    for i, translation in enumerate(restored_translations):
        print(f"Entry {test_entries[i].index}: {repr(translation)}")
    print()
    
    # Verify that HTML tags are preserved
    print("HTML preservation verification:")
    for i, translation in enumerate(restored_translations):
        has_original_html = translator._contains_html_tags(test_entries[i].text)
        has_restored_html = translator._contains_html_tags(translation)
        print(f"Entry {test_entries[i].index}: Original HTML: {has_original_html}, Restored HTML: {has_restored_html}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_html_cross_entry_detection()
