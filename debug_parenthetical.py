#!/usr/bin/env python3
"""
Test script to debug why parenthetical content is not being translated.
"""

from subtitle_translator.marian_client import MarianClient
from subtitle_translator.config import Config

def test_parenthetical_translation():
    """Test various parenthetical content to see translation behavior."""
    
    config = Config()
    config.source_lang = "en"
    config.target_lang = "hu"
    config.translation_backend = "marian"
    
    marian_client = MarianClient(config)
    
    test_cases = [
        "(INDISTINCT RADIO CHATTER)",
        "(PHONE RINGING)",
        "(DOOR SLAMS)",
        "(He speaks quietly)",
        "(She laughs)",
        "(Background music)",
        "INDISTINCT RADIO CHATTER",  # Without parentheses
        "He speaks quietly",         # Without parentheses
        "(ÉRTHETETHEN RÁDIÓ BESZÉLGETÉS)",  # Hungarian test
    ]
    
    print("Testing parenthetical content translation with MarianMT")
    print("=" * 60)
    
    for text in test_cases:
        try:
            translated = marian_client._translate_single_line(text)
            print(f"Original:   {repr(text)}")
            print(f"Translated: {repr(translated)}")
            print(f"Changed:    {text != translated}")
            print()
        except Exception as e:
            print(f"Error translating {repr(text)}: {e}")
            print()

if __name__ == "__main__":
    test_parenthetical_translation()
