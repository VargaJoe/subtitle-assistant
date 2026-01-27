#!/usr/bin/env python3
"""
Debug batch translation by examining the actual AI responses
"""
import sys
sys.path.append('.')

from subtitle_translator.multi_model import MultiModelOrchestrator
from subtitle_translator.config import Config
from subtitle_translator.srt_parser import SubtitleEntry, SRTParser
from pathlib import Path
import datetime

def debug_specific_batch():
    """Debug a specific batch that's having issues"""
    
    # Load config
    config = Config("config.yaml")
    
    # Create orchestrator
    orchestrator = MultiModelOrchestrator(config)
    
    # Load the problematic file
    parser = SRTParser()
    entries = parser.parse_file(Path("blue_bloods_test50.srt"))
    
    # Get the first small batch (entries 1-10) for simpler debugging
    batch_start = 0  # 0-based index
    batch_end = 10
    problem_batch = entries[batch_start:batch_end]
    
    print(f"=== Debugging batch with entries {batch_start+1}-{batch_end} ===")
    print(f"Batch size: {len(problem_batch)}")
    print()
    
    # Create the exact batch that would be sent
    batch_lines = []
    for entry in problem_batch:
        batch_lines.append(f"[{entry.index}] {entry.text}")
    
    batch_text = "\n".join(batch_lines)
    
    # Create the exact prompt that would be sent
    # Get the first and last entry numbers for the example
    first_num = problem_batch[0].index
    last_num = problem_batch[-1].index
    
    prompt = f"""<TASK>
Translate subtitle lines from English to Hungarian.
</TASK>

<CRITICAL_RULES>
1. ONLY translate the text content after each [number] marker
2. KEEP the exact same [number] markers in your response
3. Do NOT translate these instructions or any other text
4. Provide exactly one Hungarian translation for each numbered line
</CRITICAL_RULES>

<SUBTITLE_CONTENT>
{batch_text}
</SUBTITLE_CONTENT>

<EXPECTED_OUTPUT>
Your response must contain ONLY these translations with the EXACT same numbers:
[{first_num}] Hungarian translation of line {first_num}
[{first_num+1}] Hungarian translation of line {first_num+1}
...continue for all lines through...
[{last_num}] Hungarian translation of line {last_num}
</EXPECTED_OUTPUT>"""
    
    print("=== PROMPT TO AI ===")
    print(prompt)
    print("\n" + "="*50)
    
    # Get AI response
    print("\n=== AI RESPONSE ===")
    response = orchestrator.translation_client.translate_with_retry(prompt, "")
    print(response)
    print("\n" + "="*50)
    
    # Parse the response
    print("\n=== PARSING DEBUG ===")
    translations = orchestrator._parse_batch_response(response, problem_batch)
    
    print(f"\nResults ({len(translations)} translations for {len(problem_batch)} entries):")
    for i, (entry, translation) in enumerate(zip(problem_batch, translations)):
        status = "✅ TRANSLATED" if translation != entry.text else "❌ FALLBACK"
        print(f"{status} Entry {entry.index}: '{entry.text}' -> '{translation}'")

if __name__ == "__main__":
    debug_specific_batch()
