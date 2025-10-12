# Story 14 - Automatic Language Detection

## Overview
Implement automatic detection of source language from subtitle filenames and content, enabling fully automated translation workflows without manual language specification.

## Business Value
- Reduces manual configuration for batch translation
- Enables "drag and drop" style workflows
- Improves user experience for processing large subtitle collections
- Minimizes errors from incorrect language specification

## User Stories

### US-14.1: Detect Source Language from Filename
**As a** subtitle translator user  
**I want** the application to automatically detect the source language from the filename  
**So that** I don't need to manually specify it when the filename already indicates the language

**Acceptance Criteria:**
- Application recognizes common language indicators in filenames (e.g., `.eng`, `.en`, `_eng`, `-en`)
- Supports both 2-letter (ISO 639-1) and 3-letter (ISO 639-2/3) language codes
- Handles various separator formats (`.`, `_`, `-`)
- Falls back to configured default if no language indicator found
- Works with complex filename patterns (e.g., `show.s01e01.eng.1080p.srt`)

**Examples:**
- `moviename.eng.srt` → Auto-detects English as source
- `series.s01e01.en.720p.srt` → Auto-detects English as source
- `subtitle_track4_hun_1.srt` → Auto-detects Hungarian as source
- `tvshow.s01e03.de.srt` → Auto-detects German as source

### US-14.2: Configure Auto-Detection Behavior
**As a** power user  
**I want** to configure when auto-detection should be used  
**So that** I can control the behavior for different workflows

**Acceptance Criteria:**
- Configuration option: `auto_detect_source_language` (default: `false`)
- Configuration option: `auto_detect_mode` with values: `filename`, `content`, `both`
- CLI flag: `--auto-detect-language` to enable for specific runs
- CLI flag: `--no-auto-detect` to disable when enabled in config
- Explicit `--source` flag always overrides auto-detection
- Clear logging when auto-detection is used and what language was detected

### US-14.3: Validate Detected Language
**As a** user  
**I want** the application to validate detected languages  
**So that** I'm notified if an unsupported language is detected

**Acceptance Criteria:**
- Validates detected language codes against supported languages
- Warns if detected language is not supported by the current backend
- Falls back to configured default if validation fails
- Logs warning with detected vs. fallback language
- Provides list of supported languages in error message

## Technical Implementation

### Phase 1: Filename-Based Detection
**Task 14.1.1:** Implement language code extraction from filenames
- Create `LanguageDetector` class in `subtitle_translator/language_detector.py`
- Implement `detect_from_filename()` method
- Support both 2-letter and 3-letter ISO codes
- Handle various separator patterns
- Add comprehensive test coverage

**Task 14.1.2:** Integrate with Config system
- Add `auto_detect_source_language` boolean to config
- Add `auto_detect_mode` enum to config
- Update `Config` class to use detection when enabled
- Add validation for detected languages

**Task 14.1.3:** Update CLI interface
- Add `--auto-detect-language` flag
- Add `--no-auto-detect` flag
- Ensure explicit `--source` overrides auto-detection
- Update help text and examples

**Task 14.1.4:** Update batch processing
- Integrate auto-detection in `translate_all_srt.ps1`
- Add `-AutoDetectLanguage` switch parameter
- Log detected languages for each file
- Handle mixed-language batches gracefully

### Phase 2: Content-Based Detection
**Task 14.2.1:** Research and select detection library
- Evaluate libraries: `langdetect`, `langid`, `fasttext`
- Consider accuracy, performance, and dependencies
- Document selection rationale
- Create proof-of-concept

**Task 14.2.2:** Implement content-based detection
- Add chosen library to `requirements.txt`
- Implement `detect_from_content()` method in `LanguageDetector`
- Sample representative text from subtitle (first N entries)
- Cache detection results to avoid repeated analysis
- Add confidence threshold configuration

**Task 14.2.3:** Implement hybrid detection strategy
- Combine filename and content detection
- Prioritize filename detection (faster)
- Use content detection as fallback or validation
- Add `both` mode that validates filename detection with content
- Configure confidence threshold for content detection

**Task 14.2.4:** Optimize detection performance
- Implement intelligent sampling for large files
- Cache detection results in progress files
- Add option to skip detection for resume operations
- Benchmark detection overhead

### Phase 3: User Experience
**Task 14.3.1:** Add informative logging
- Log when auto-detection is triggered
- Display detected language clearly
- Show confidence scores for content-based detection
- Warn when falling back to defaults

**Task 14.3.2:** Update documentation
- Add Auto-Detection User Guide
- Document supported language codes
- Provide configuration examples
- Add troubleshooting section

**Task 14.3.3:** Create unit tests
- Test filename patterns with various separators
- Test content detection with sample texts
- Test hybrid detection scenarios
- Test validation and fallback behavior

## Configuration Example

```yaml
translation:
  source_language: "en"  # Default fallback
  target_language: "hu"
  auto_detect_source_language: true  # Enable auto-detection
  auto_detect_mode: "both"  # filename, content, or both
  
language_detection:
  content_detection:
    enabled: true
    confidence_threshold: 0.8  # Minimum confidence for content-based detection
    sample_entries: 10  # Number of subtitle entries to sample
    cache_results: true  # Cache detection in progress files
  
  supported_languages:
    - en
    - hu
    - de
    - fr
    - es
    - it
    # ... more languages
  
  fallback_behavior: "use_default"  # use_default, prompt_user, or fail
```

## Dependencies
- Language detection library (e.g., `langdetect>=1.0.9`)
- Updated `Config` class with new fields
- Extended CLI argument parsing

## Testing Strategy
1. **Unit Tests**: Test `LanguageDetector` class with various inputs
2. **Integration Tests**: Test end-to-end with real subtitle files
3. **Regression Tests**: Ensure existing behavior not affected when disabled
4. **Performance Tests**: Measure overhead of detection on large batches

## Success Metrics
- 95%+ accuracy for filename-based detection on common patterns
- 90%+ accuracy for content-based detection on clear text samples
- < 100ms overhead for filename detection per file
- < 500ms overhead for content detection per file

## Future Enhancements
- Machine learning model for improved content detection
- Support for detecting multiple languages in bilingual subtitles
- Integration with filename normalization utilities
- Auto-detect target language from directory structure
