#!/usr/bin/env python3
import json
import os

# Load the log or create a test to see what the AI is returning
# First, let's create a quick test to see the actual AI response format

from subtitle_translator.multi_model import MultiModelOrchestrator
from subtitle_translator.config import Config
from subtitle_translator.srt_parser import SubtitleEntry
import datetime

# Load config
config = Config("config.yaml")

# Create translator
translator = MultiModelOrchestrator(config)

# Create a small test batch
test_entries = [
    SubtitleEntry(1, datetime.timedelta(seconds=1), datetime.timedelta(seconds=3), "Hello world."),
    SubtitleEntry(2, datetime.timedelta(seconds=4), datetime.timedelta(seconds=6), "Get out."),
    SubtitleEntry(3, datetime.timedelta(seconds=7), datetime.timedelta(seconds=9), "Come on.")
]

# Create batch prompt
batch_lines = []
for entry in test_entries:
    batch_lines.append(f"[{entry.index}] {entry.text}")

batch_text = "\n".join(batch_lines)

prompt = f"""<INSTRUCTION>
You are a professional translator. Your task is to translate subtitle lines from English to Hungarian.

CRITICAL: Only translate the content between <SUBTITLE_LINES> tags. Do NOT translate these instructions.
</INSTRUCTION>

<SUBTITLE_LINES>
{batch_text}
</SUBTITLE_LINES>

<OUTPUT_FORMAT>
Provide ONLY the Hungarian translations using this exact format:
[1] Hungarian translation of first line
[2] Hungarian translation of second line
[3] Hungarian translation of third line
(continue for all lines)

Rules:
- Keep the [number] markers exactly as shown
- Translate to natural, fluent Hungarian
- Preserve the meaning and tone of each subtitle
- Do NOT include any other text in your response
</OUTPUT_FORMAT>"""

print("=== SENDING PROMPT ===")
print(prompt)
print("\n=== AI RESPONSE ===")

# Get response from AI
response = translator.translation_client.translate_with_retry(prompt, "")
print(response)

print("\n=== PARSED RESULT ===")
translations = translator._parse_batch_response(response, test_entries)
for i, (entry, translation) in enumerate(zip(test_entries, translations)):
    print(f"Entry {entry.index}: '{entry.text}' -> '{translation}'")
