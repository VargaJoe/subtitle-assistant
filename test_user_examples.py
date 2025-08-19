#!/usr/bin/env python3
"""
Test script for the exact user examples to verify HTML formatting fix.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from subtitle_translator.config import Config
from subtitle_translator.marian_client import MarianClient


def test_user_examples():
    """Test the exact user examples that were problematic."""
    
    print("Testing exact user examples with HTML formatting issues...")
    
    # Load configuration
    config = Config.from_yaml(project_root / "config.yaml")
    
    # Ensure we're using MarianMT backend
    config.translation_backend = "marian"
    config.preserve_formatting = True
    
    try:
        # Initialize MarianMT client
        print("Initializing MarianMT client...")
        client = MarianClient(config)
        
        # Exact user examples that were problematic
        user_examples = [
            "<i>Previously...</i>",
            "<i>The Raven and his followers</i>",
            "<i>went to great lengths\nto poison half the city.</i>",
            "<i>And now, it appears\nhe blames you</i>",
            "for stopping the attack."
        ]
        
        print(f"\nTesting {len(user_examples)} exact user examples:")
        print("=" * 80)
        
        for i, original_text in enumerate(user_examples, 1):
            print(f"\nExample {i}:")
            print(f"Original:   {repr(original_text)}")
            
            try:
                translated = client.translate_text(original_text)
                print(f"Translated: {repr(translated)}")
                
                # Check for the specific corruption patterns the user reported
                has_corruption = (
                    ' <i' in translated or  # Broken opening tag
                    '</i > <i' in translated or  # Broken/duplicated tags
                    '<ni>' in translated or  # Malformed tag
                    '>A Holló és követői </I>' in translated  # Wrong case closing tag
                )
                
                if has_corruption:
                    print("❌ Still has corruption issues")
                else:
                    # Check if HTML tags are properly preserved
                    has_original_tags = '<i>' in original_text or '</i>' in original_text
                    has_translated_tags = '<i>' in translated and '</i>' in translated
                    
                    if has_original_tags and has_translated_tags:
                        print("✅ HTML tags properly preserved - issue FIXED")
                    elif not has_original_tags:
                        print("✅ No HTML tags needed - translation OK")
                    else:
                        print("❌ HTML tags lost")
                
            except Exception as e:
                print(f"❌ Translation failed: {e}")
        
        print("\n" + "=" * 80)
        
        # Test a complete subtitle sequence like the user's problem
        print("\nTesting complete subtitle sequence (user's original issue):")
        complete_sequence = """<i>Previously...</i>

<i>The Raven and his followers</i>

<i>went to great lengths
to poison half the city.</i>

<i>And now, it appears
he blames you</i>

for stopping the attack."""
        
        print("Processing complete sequence...")
        lines = [line.strip() for line in complete_sequence.split('\n\n') if line.strip()]
        
        print("\nBefore vs After comparison:")
        print("-" * 40)
        
        for i, line in enumerate(lines, 1):
            if line:
                translated_line = client.translate_text(line)
                print(f"{i}. Original:   {repr(line)}")
                print(f"   Translated: {repr(translated_line)}")
                print()
        
        print("✅ Complete sequence test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = test_user_examples()
    sys.exit(0 if success else 1)
