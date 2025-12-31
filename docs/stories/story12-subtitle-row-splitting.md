# Story 12: Subtitle Row Splitting

## Goal
Implement automatic subtitle row splitting to ensure subtitle lines fit within standard display limits (typically 42 characters per line) while maintaining readability and optimal balance between lines.

## Tasks

### 1. Configuration System
- [x] Add max_row_length (default: 42) and row_split_method (default: 'even') to config.yaml
- [x] Enhance Config dataclass with output section for subtitle formatting
- [x] Support three splitting methods: 'even' (balanced), 'word' (word boundaries), 'char' (character-level)

### 2. Core Implementation
- [x] Enhance split_subtitle_text() function in srt_parser.py
- [x] Implement 'even' algorithm to evaluate all word boundary splits for optimal balance
- [x] Integrate splitting into SubtitleEntry.to_srt_format() for automatic output formatting

### 3. CLI Integration
- [x] Add --reformat-only option to main.py for reformatting without retranslation
- [x] Enhance translate_all_srt.ps1 with -ReformatOnly switch for batch operations

### 4. Lightweight Reformatter
- [x] Create standalone reformat_srt.py to avoid AI model loading overhead
- [x] Enable fast text-only processing for existing translated files
- [x] Ensure same splitting algorithms as main translator for consistency

### 5. Quality Optimization
- [x] Improve 'even' algorithm: Fixed splitting from (23,34) chars imbalance to (30,27) chars near-perfect balance
- [x] Implement best word boundary selection to minimize line length differences
- [x] Maintain readability while ensuring compatibility with non-wrapping subtitle viewers

## Acceptance Criteria
- Subtitle lines are automatically split to fit within max_row_length
- Three splitting methods work correctly with optimal balance
- CLI --reformat-only option works for existing files
- Standalone reformatter provides fast processing without AI overhead
- Output maintains subtitle timing and formatting