# Filename Language Indicator Cleanup

## Overview
The Subtitle Assistant automatically removes language indicators from source filenames when generating output files, preventing unwanted language code duplication in translated subtitle names.

## Problem
When translating subtitle files that contain source language indicators in their filenames, the output would include both the source and target language codes:

**Before (❌ Incorrect):**
- `moviename.eng.srt` → `moviename.eng.hun.srt`
- `tvshow.s01e01.en.srt` → `tvshow.s01e01.en.hun.srt`
- `movie_track4_eng_1.srt` → `movie_track4_eng_1.hun.srt`

**After (✅ Correct):**
- `moviename.eng.srt` → `moviename.hun.srt`
- `tvshow.s01e01.en.srt` → `tvshow.s01e01.hun.srt`
- `movie_track4_eng_1.srt` → `movie_track4_1.hun.srt`

## Features

### Automatic Detection
The system automatically detects and removes language indicators in various formats:
- **2-letter codes**: en, hu, de, fr, es, it, pt, ru, ja, ko, zh, ar, pl, nl, sv, no, da, fi, cs, tr
- **3-letter codes**: eng, hun, deu, fra, spa, ita, por, rus, jpn, kor, chi, ara, pol, nld, swe, nor, dan, fin, ces, tur

### Flexible Separators
Supports multiple separator formats:
- Dot separator: `moviename.eng.srt`
- Underscore separator: `moviename_eng.srt`
- Dash separator: `moviename-eng.srt`
- Mixed separators: `movie.name_eng-2023.srt`

### Intelligent Cleanup
- Removes multiple language indicators: `test.eng.eng.srt` → `test.hun.srt`
- Handles multiple different languages: `test_en_track2_de.srt` → `test_track2.hun.srt`
- Preserves other identifiers: `movie.2023.eng.1080p.srt` → `movie.2023.1080p.hun.srt`
- Cleans up double separators: `movie..eng.srt` → `movie.hun.srt`
- Removes trailing separators: `movie.eng_.srt` → `movie.hun.srt`

## How It Works

The cleanup process happens automatically when generating output filenames:

1. **Extract base name**: Remove the `.srt` extension
2. **Detect language indicators**: Use regex pattern matching to find language codes
3. **Remove indicators**: Strip matched language codes from filename
4. **Clean up separators**: Remove duplicate or trailing separators
5. **Add target language**: Append target language code (e.g., `.hu`)
6. **Add extension**: Append `.srt` extension

## Examples

### Common Patterns
```
Input:                              Output:
─────────────────────────────────── ───────────────────────────
moviename.eng.srt                   moviename.hun.srt
tvshow.s01e01.eng.srt              tvshow.s01e01.hun.srt
tvshow.s01e03.de.srt               tvshow.s01e03.hun.srt
series.s01e01.en.720p.srt          series.s01e01.720p.hun.srt
show.s02e01.en.srt                 show.s02e01.hun.srt
movie_track4_eng_1.srt             movie_track4_1.hun.srt
subtitle-eng-final.srt             subtitle-final.hun.srt
show_s01e01_eng_final.srt          show_s01e01_final.hun.srt
```

### Edge Cases
```
Input:                              Output:
─────────────────────────────────── ───────────────────────────
test.eng.eng.srt                    test.hun.srt
test_en_track2_de.srt              test_track2.hun.srt
normal_filename.srt                 normal_filename.hun.srt
movie.2023.eng.1080p.srt           movie.2023.1080p.hun.srt
```

## Configuration

No configuration needed! The feature works automatically for all translation operations.

### Customization (Future)
If you need to customize the behavior, you can modify the language codes list in `subtitle_translator/config.py`:

```python
# In Config._remove_language_indicators() method
language_codes = [
    'eng', 'en', 'hun', 'hu', 'deu', 'de', 'fra', 'fr', 'spa', 'es',
    'ita', 'it', 'por', 'pt', 'rus', 'ru', 'jpn', 'ja', 'kor', 'ko',
    # Add more language codes here...
]
```

## Testing

Run the test suite to verify the filename cleanup:

```powershell
python test_filename_cleanup.py
```

Expected output:
```
Testing filename language indicator removal:
======================================================================
✅ PASS: 'moviename.eng' -> 'moviename'
✅ PASS: 'moviename.en' -> 'moviename'
...
======================================================================
✅ All tests passed!

Testing complete output filename generation:
======================================================================
✅ PASS: 'subtitles/moviename.eng.srt' -> 'moviename.hu.srt'
...
======================================================================
✅ All output filename tests passed!

🎉 All tests passed successfully!
```

## Technical Details

### Implementation
The cleanup logic is implemented in the `Config` class:
- Method: `_remove_language_indicators(filename: str) -> str`
- Location: `subtitle_translator/config.py`
- Called by: `get_output_filename(input_path: Path) -> Path`

### Regex Pattern
```python
pattern = r'[._-](' + '|'.join(language_codes) + r')(?=[._-]|\d|$)'
```

This pattern matches:
- Separator before language code: `[._-]`
- Language code: captured from list
- Lookahead for separator, digit, or end of string: `(?=[._-]|\d|$)`

### Performance
- **Time complexity**: O(n) where n is the filename length
- **Overhead**: < 1ms per filename
- **Caching**: Not needed due to minimal overhead

## Troubleshooting

### Issue: Language code not removed
**Cause**: Language code not in the supported list or unusual separator  
**Solution**: Add the language code to the list in `config.py` or use standard separators

### Issue: Part of filename incorrectly removed
**Cause**: Filename contains word matching a language code (e.g., "engine.srt" contains "en")  
**Solution**: The regex requires separators, so this shouldn't happen. If it does, please report as a bug.

### Issue: Need to keep source language in filename
**Cause**: You want both source and target language indicators  
**Solution**: Currently not configurable. Feature request can be submitted.

## Related Features

- **Story 14**: Automatic Language Detection - Detect source language from filename
- **Story 16**: Folder-Specific Configuration - Override settings per folder

## Changelog

### Version 1.0 (October 2025)
- ✅ Initial implementation of language indicator removal
- ✅ Support for 40+ language codes (2-letter and 3-letter)
- ✅ Support for multiple separator formats
- ✅ Comprehensive test coverage
- ✅ Automatic cleanup of double separators
- ✅ Documentation and examples

## Future Enhancements
- Configuration option to disable cleanup
- Custom language code list via config file
- Option to preserve source language indicator
- Support for custom separator patterns
- Configurable cleanup strategy (remove all, remove first, remove last, etc.)
