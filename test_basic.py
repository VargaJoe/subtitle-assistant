#!/usr/bin/env python3
"""
Test script to verify subtitle translator functionality.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from subtitle_translator.config import Config
from subtitle_translator.srt_parser import SRTParser
from subtitle_translator.ollama_client import OllamaClient


def test_srt_parsing():
    """Test SRT file parsing."""
    print("Testing SRT parsing...")
    
    parser = SRTParser()
    srt_file = project_root / "subtitles" / "Magnum.P.I.S02.REMASTERED.BDRip.x264-DEUTERiUM" / "Magnum.P.I.S02E01.srt"
    
    try:
        entries = parser.parse_file(srt_file)
        print(f"✅ Successfully parsed {len(entries)} subtitle entries")
        
        # Show first few entries
        print("\nFirst 3 entries:")
        for i, entry in enumerate(entries[:3]):
            print(f"  {entry.index}: {entry.start_time} -> {entry.end_time}")
            print(f"    Text: {entry.text}")
            print()
        
        return True
    except Exception as e:
        print(f"❌ SRT parsing failed: {e}")
        return False


def test_ollama_connection():
    """Test Ollama connection."""
    print("Testing Ollama connection...")
    
    config = Config()
    client = OllamaClient(config)
    
    try:
        if client.is_available():
            print("✅ Ollama service is available")
            
            models = client.get_available_models()
            print(f"✅ Available models: {models}")
            
            return True
        else:
            print("❌ Ollama service is not available")
            print("Please ensure Ollama is running with: ollama serve")
            return False
            
    except Exception as e:
        print(f"❌ Ollama connection test failed: {e}")
        return False


def test_basic_translation():
    """Test basic translation functionality."""
    print("Testing basic translation...")
    
    config = Config(verbose=True)
    client = OllamaClient(config)
    
    if not client.is_available():
        print("❌ Skipping translation test - Ollama not available")
        return False
    
    try:
        test_text = "Hello, how are you?"
        translated = client.translate_text(test_text)
        
        print(f"✅ Translation successful:")
        print(f"  Original: {test_text}")
        print(f"  Translated: {translated}")
        
        return True
        
    except Exception as e:
        print(f"❌ Translation test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Subtitle Translator - Basic Functionality Test")
    print("=" * 50)
    
    tests = [
        test_srt_parsing,
        test_ollama_connection,
        test_basic_translation
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! The subtitle translator is ready to use.")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
