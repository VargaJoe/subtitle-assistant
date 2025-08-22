#!/usr/bin/env python3

from subtitle_translator.srt_parser import SubtitleEntry

# Test the text cleaning
test_text = "..."
cleaned = SubtitleEntry._clean_text(test_text)
print(f'Original text: "{test_text}"')
print(f'Cleaned text: "{cleaned}"')
print(f'Is empty: {not cleaned}')
print(f'Length: {len(cleaned)}')

# Test with actual problematic entry
test_block = """1
00:00:05,230 --> 00:00:07,470
..."""

from subtitle_translator.srt_parser import SRTParser
parser = SRTParser()

try:
    entry = parser._parse_block(test_block)
    print(f'Entry created: {entry}')
except Exception as e:
    print(f'Error: {e}')
