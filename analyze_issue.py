#!/usr/bin/env python3
"""
Test the exact batch scenario that's causing issues
"""
import json
import os

# Load the results to see what entries failed
results_path = 'output/multi_model_results/blue_bloods_test50_results.json'
if os.path.exists(results_path):
    with open(results_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Find the problematic first entry
    entry1 = data['entries']['entry_0001']
    print("Problematic entry:")
    print(f"Original: {entry1['original_text']}")
    print(f"Translation: {entry1['step2_translation']['text']}")
    print()
    
    # The problem is that the first entry in a batch sometimes gets the instructions translated
    # This means the AI is treating the prompt instructions as content to translate
    
    print("Analysis:")
    print("The AI translated the instruction 'You are a translator. Translate specifically the following lines from English to Hungarian.'")
    print("This suggests the prompt format might be confusing the AI.")
    print()
    print("Potential solutions:")
    print("1. Use clearer separators between instructions and content")
    print("2. Use XML tags or other markup to clearly delineate")  
    print("3. Restructure the prompt to be more explicit")
    print("4. Use a different approach like numbered lists with clear headers")
    
else:
    print(f"Results file not found: {results_path}")
