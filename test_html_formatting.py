#!/usr/bin/env python3
"""
Test script for HTML formatting preservation in MarianMT translation.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from subtitle_translator.config import Config
from subtitle_translator.marian_client import MarianClient


def test_html_formatting():
    """Test HTML formatting preservation during translation."""
    
    print("Testing HTML formatting preservation in MarianMT translation...")
    
    # Load configuration
    config = Config.from_yaml(project_root / "config.yaml")
    
    # Ensure we're using MarianMT backend
    config.translation_backend = "marian"
    config.preserve_formatting = True
    
    try:
        # Initialize MarianMT client
        print("Initializing MarianMT client...")
        client = MarianClient(config)
        
        # Test cases with HTML formatting
        test_cases = [
            "<i>Previously...</i>",
            "<i>The Raven and his followers</i>",
            "<i>went to great lengths\nto poison half the city.</i>",
            "<i>And now, it appears\nhe blames you</i>",
            "for stopping the attack.",
        ]
        
        print(f"\nTesting {len(test_cases)} subtitle entries with HTML formatting:")
        print("=" * 60)
        
        for i, original_text in enumerate(test_cases, 1):
            print(f"\nTest {i}:")
            print(f"Original:   {repr(original_text)}")
            
            try:
                translated = client.translate_text(original_text)
                print(f"Translated: {repr(translated)}")
                
                # Check if HTML tags are preserved
                has_original_tags = '<i>' in original_text or '</i>' in original_text
                has_translated_tags = '<i>' in translated or '</i>' in translated
                
                if has_original_tags:
                    if has_translated_tags:
                        print("✅ HTML tags preserved")
                    else:
                        print("❌ HTML tags lost during translation")
                else:
                    print("ℹ️  No HTML tags in original")
                
            except Exception as e:
                print(f"❌ Translation failed: {e}")
        
        print("\n" + "=" * 60)
        print("HTML formatting test completed!")
        
        # Test the specific issue from user's example
        print("\nTesting specific user issue:")
        user_test = "<i>Previously...</i>"
        print(f"Input:  {repr(user_test)}")
        
        result = client.translate_text(user_test)
        print(f"Output: {repr(result)}")
        
        if '<i>' in result and '</i>' in result and not result.endswith(' <i'):
            print("✅ User issue FIXED - HTML tags properly preserved")
        else:
            print("❌ User issue PERSISTS - HTML tags still corrupted")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = test_html_formatting()
    sys.exit(0 if success else 1)
