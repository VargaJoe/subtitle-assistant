#!/usr/bin/env python3
"""
Test script for filename language indicator removal.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from subtitle_translator.config import Config


def test_filename_cleanup():
    """Test the filename language indicator removal."""
    config = Config()
    
    test_cases = [
        # (input_filename, expected_output)
        ("moviename.eng", "moviename"),
        ("moviename.en", "moviename"),
        ("moviename_track4_eng_1", "moviename_track4_1"),
        ("Blue.Bloods.s14e01.eng", "Blue.Bloods.s14e01"),
        ("Blue.Bloods.14x03.de", "Blue.Bloods.14x03"),
        ("series.s01e01.en.720p", "series.s01e01.720p"),
        ("subtitle_track4_hun_1", "subtitle_track4_1"),
        ("movie-name-eng-2023", "movie-name-2023"),
        ("NCIS.Hawaii.S02E01.en", "NCIS.Hawaii.S02E01"),
        ("test.eng.eng", "test"),  # Multiple indicators
        ("test_en_track2_de", "test_track2"),  # Multiple different languages
        ("normal_filename", "normal_filename"),  # No language indicator
        ("movie.2023.eng.1080p", "movie.2023.1080p"),
        ("show_s01e01_eng_final", "show_s01e01_final"),
    ]
    
    print("Testing filename language indicator removal:")
    print("=" * 70)
    
    all_passed = True
    for input_name, expected in test_cases:
        result = config._remove_language_indicators(input_name)
        passed = result == expected
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: '{input_name}' -> '{result}'", end="")
        
        if not passed:
            print(f" (expected: '{expected}')")
            all_passed = False
        else:
            print()
    
    print("=" * 70)
    
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    return all_passed


def test_output_filename_generation():
    """Test complete output filename generation."""
    config = Config()
    config.target_lang = "hu"
    
    test_cases = [
        # (input_path, expected_output_name)
        ("subtitles/moviename.eng.srt", "moviename.hu.srt"),
        ("subtitles/Blue.Bloods.14x01.en.srt", "Blue.Bloods.14x01.hu.srt"),
        ("path/to/movie_track4_eng_1.srt", "movie_track4_1.hu.srt"),
        ("test.srt", "test.hu.srt"),
    ]
    
    print("\nTesting complete output filename generation:")
    print("=" * 70)
    
    all_passed = True
    for input_path, expected_name in test_cases:
        input_path_obj = Path(input_path)
        result_path = config.get_output_filename(input_path_obj)
        result_name = result_path.name
        
        passed = result_name == expected_name
        status = "✅ PASS" if passed else "❌ FAIL"
        
        print(f"{status}: '{input_path}' -> '{result_name}'", end="")
        
        if not passed:
            print(f" (expected: '{expected_name}')")
            all_passed = False
        else:
            print()
    
    print("=" * 70)
    
    if all_passed:
        print("✅ All output filename tests passed!")
    else:
        print("❌ Some output filename tests failed!")
    
    return all_passed


if __name__ == "__main__":
    test1_passed = test_filename_cleanup()
    test2_passed = test_output_filename_generation()
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

