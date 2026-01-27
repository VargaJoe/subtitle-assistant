#!/usr/bin/env python3
import json
import os

# Load the results file
results_path = 'output/multi_model_results/blue_bloods_test50_results.json'
if os.path.exists(results_path):
    with open(results_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("=== Debugging Batch Translation Results ===")
    print(f"Total entries processed: {len(data['entries'])}")
    print()
    
    # Check first few entries
    for i in range(1, 11):  # Check first 10 entries
        key = f'entry_{i:04d}'
        if key in data['entries']:
            entry = data['entries'][key]
            print(f"Entry {i} ({key}):")
            print(f"  Original: {entry['original_text']}")
            print(f"  Translation: {entry['step2_translation']['text']}")
            if entry['original_text'] == entry['step2_translation']['text']:
                print("  *** SAME AS ORIGINAL (parsing issue?) ***")
            print()
    
    # Count successful vs failed translations
    total = 0
    translated = 0
    for key, entry in data['entries'].items():
        total += 1
        if entry['original_text'] != entry['step2_translation']['text']:
            translated += 1
    
    print(f"Summary: {translated}/{total} entries successfully translated ({translated/total*100:.1f}%)")
else:
    print(f"Results file not found: {results_path}")
