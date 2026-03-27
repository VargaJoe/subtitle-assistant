# Implementation Tasks

---

## In-Progress Stories

### Gemini Provider + Multiline Stretching Fix (CURRENT SESSION)
- [x] **Critical Bug Fix: Cross-Entry Timestamp Misalignment** - COMPLETED ✓
  - [x] Investigated user reports of text appearing at wrong timestamps
  - [x] Found Bug #1: Integer truncation in proportional splitting causing rounding accumulation
  - [x] Found Bug #2: Silent entry loss when zip() receives mismatched counts
  - [x] Found Bug #3: No validation of split_translations count matching group_entries
  - [x] Fixed: Implemented cumulative allocation algorithm with proper rounding
  - [x] Fixed: Added entry count safety checks and empty string padding
  - [x] Fixed: Added validation before zip() to prevent silent entry loss
  - [x] Created test_cross_entry_splitting.py demonstrating bug and validating fix
  - [x] Test results: Improved from 11:1:2 (78.6%:7.1%:14.3%) to 12:1:1 (85.7%:7.1%:7.1%) distribution

- [x] **Multiline Translation Stretching Fix** - COMPLETED ✓
  - [x] Understanding clarified: Two separate aspects covered
  - [x] Cross-entry preservation: Already working via Story 09C implementation (now bug-fixed)
  - [x] Within-entry line preservation: Fixed with original_line_count tracking
  - [x] Both aspects now properly implemented and tested
  
- [x] **Gemini Translation Slippage Fix** - COMPLETED ✓
  - [x] Root cause identified: Gemini merges cross-entry sentence continuations into a
        single output key, shifting all subsequent entry translations by 1+ positions
  - [x] Example: entries 85 ("You've been ducking me") + 86 ("since I got back from Sweden.")
        were merged into key "85", making every entry after that one position off
  - [x] Fix: pre-merge cross-entry sentence groups before the API call in
        `_translate_entries_api_batch()`, reusing `_detect_cross_entry_groups()`
  - [x] After translation, merged results are split back proportionally per entry
        using existing `_split_translation_to_entries()` logic
  - [x] 5 new unit tests added in `tests/unit/test_api_batch_cross_entry.py` — all passing

- [ ] **Gemini Provider Integration** - IN PROGRESS
  - [x] Created GeminiProvider class (200 lines) following plugin architecture
  - [x] Implements BaseTranslationProvider interface with @translation_provider("gemini") decorator
  - [x] Add google-generativeai to requirements.txt ✓
  - [x] Add Gemini configuration to config.yaml (api_key, model selection) ✓
  - [x] **HTML-safe Gemini API-batch formatting fix** - COMPLETED ✓
    - [x] Strip HTML tags before Gemini sees API-batch texts
    - [x] Restore tags after translation and keep each output line self-contained
    - [x] Add regression coverage for API-batch HTML preservation and line-safe splitting
  - [ ] Test Gemini provider integration end-to-end
  - [ ] Add Gemini API key setup guide to documentation
  - [ ] Optional: Add quality diagnostics for comparing providers

---

## Recently Completed Stories

## Planned Stories

### Story 14 - Automatic Language Detection
- [ ] **Phase 1: Filename-Based Detection**
  - [ ] Implement language code extraction from filenames (.eng, .en, _eng, etc.)
  - [ ] Support both 2-letter (ISO 639-1) and 3-letter (ISO 639-2/3) codes
  - [ ] Handle various separator patterns (`.`, `_`, `-`)
  - [ ] Integrate with Config system (auto_detect_source_language setting)
  - [ ] Add CLI flags: `--auto-detect-language` and `--no-auto-detect`
  - [ ] Update batch processing script with auto-detection
- [ ] **Phase 2: Content-Based Detection**
  - [ ] Research and select detection library (langdetect, langid, fasttext)
  - [ ] Implement content-based detection with confidence threshold
  - [ ] Add hybrid detection (filename + content validation)
  - [ ] Optimize performance with intelligent sampling
  - [ ] Cache detection results in progress files
- [ ] **Phase 3: User Experience**
  - [ ] Add informative logging for detected languages
  - [ ] Create Auto-Detection User Guide
  - [ ] Comprehensive test coverage
  - [ ] Validation and fallback behavior
- [ ] See details: [story14-auto-language-detection.md](stories/story14-auto-language-detection.md)

### Story 15 - Simple PowerShell GUI
- [ ] **Phase 1: Basic GUI Framework**
  - [ ] Create gui_translate.ps1 using Windows Forms/WPF
  - [ ] Implement operation selection (Translate All, Translate Selected, Reformat)
  - [ ] Add settings configuration UI (folders, languages, options)
  - [ ] Settings persistence between sessions
- [ ] **Phase 2: File Selection and Browsing**
  - [ ] Implement folder browser dialogs
  - [ ] Add drag-and-drop support for folders and files
  - [ ] File selection for single-file mode with multi-select
  - [ ] Recent folders list and file preview
- [ ] **Phase 3: Translation Process Management**
  - [ ] Real-time progress tracking with progress bar
  - [ ] Live log viewer with colorized output
  - [ ] Process control (Start, Stop, Pause, Resume)
  - [ ] Integration with batch script and progress files
- [ ] **Phase 4: Results and Error Handling**
  - [ ] Results summary dialog with statistics
  - [ ] User-friendly error messages and troubleshooting
  - [ ] "Open Output Folder" and "View Error Log" buttons
  - [ ] Help documentation and tooltips
- [ ] **Phase 5: Polish and Distribution**
  - [ ] UI/UX improvements and theming
  - [ ] Advanced features (remember position, keyboard shortcuts)
  - [ ] Create standalone executable with ps2exe
  - [ ] Testing on Windows 10/11, user manual with screenshots
- [ ] See details: [story15-simple-gui.md](stories/story15-simple-gui.md)

### Story 16 - Folder-Specific Configuration Overrides
- [ ] **Phase 1: Configuration Discovery**
  - [ ] Create ConfigResolver class for config file discovery
  - [ ] Walk directory tree to find .subtitle-config.yaml files
  - [ ] Implement config hierarchy and caching
  - [ ] Support multiple naming conventions
- [ ] **Phase 2: Configuration Merging**
  - [ ] Implement deep merge algorithm for nested configs
  - [ ] Define override precedence (CLI > Folder > Parent > Root)
  - [ ] Optimize config loading with caching
  - [ ] Handle null values and list merging strategies
- [ ] **Phase 3: Integration with Translator**
  - [ ] Update SubtitleTranslator to use ConfigResolver
  - [ ] Integrate with batch processing
  - [ ] Update CLI with --show-config and --ignore-folder-configs flags
  - [ ] Update PowerShell scripts with config preview
- [ ] **Phase 4: Configuration Validation**
  - [ ] Implement validation rules for overrides
  - [ ] Create config linting tool (lint_config.py)
  - [ ] Add migration utilities for config updates
  - [ ] Backup and restore functionality
- [ ] **Phase 5: Documentation and Testing**
  - [ ] Create "Folder Configuration Guide"
  - [ ] Update existing documentation
  - [ ] Comprehensive test coverage for precedence and merging
  - [ ] Performance tests for large directory trees
- [ ] See details: [story16-folder-config-overrides.md](stories/story16-folder-config-overrides.md)

### Story 10 - MarianMT Hybrid Multi-Model Architecture
- [ ] Integrate MarianMT as Translation Model within multi-model pipeline
- [ ] Create Context Enhancer step for LLM refinement of MarianMT output
- [ ] Implement hybrid mode: `--backend hybrid`
- [ ] Combine 40x speed improvement with context awareness and validation
- [ ] Expected: 10-20x faster than current multi-model with superior quality
- [ ] See details: [story10-marianmt-hybrid-architecture.md](stories/story10-marianmt-hybrid-architecture.md)

### Story 11 - Pure MarianMT Production Pipeline
- [ ] Optimize MarianMT for large-scale production subtitle translation
- [ ] Implement directory batch processing and multi-file operations
- [ ] Add production-grade quality enhancements and post-processing
- [ ] Build automated workflow for processing entire seasons
- [ ] Expected: Process full seasons in minutes with 90%+ quality
- [ ] See details: [story11-pure-marianmt-production.md](stories/story11-pure-marianmt-production.md)

### Story 03 - Speech-to-Text Extraction
- [ ] Hungarian Whisper integration
- [ ] Audio file processing pipeline
- [ ] SRT generation from audio
- [ ] Quality validation for generated subtitles

### Story 08 - Accessibility Features
- [ ] Sound effect descriptions
- [ ] Speaker identification tags
- [ ] Enhanced formatting for hearing-impaired
- [ ] Audio cue translations

### Story 04 - Multi-Language Support
- [ ] Language detection system (see Story 14)
- [ ] Multiple source/target language pairs
- [ ] Model routing for different languages
- [ ] CLI enhancements for language selection

### Story 05 - GUI Application (SUPERSEDED by Story 15)
- [ ] ~~PyQt6 graphical interface~~ (replaced with PowerShell GUI)
- [ ] ~~Drag-and-drop file handling~~ (included in Story 15)
- [ ] ~~Real-time translation preview~~ (included in Story 15)
- [ ] ~~Settings management UI~~ (included in Story 15)

### Story 06 - Advanced Subtitle Formats
- [ ] WebVTT format support
- [ ] ASS format support
- [ ] Format conversion utilities
- [ ] Formatting preservation

### Story 07 - Audio-Based Enhancements
- [ ] Audio timing analysis
- [ ] Speaker detection
- [ ] Speech rate optimization
- [ ] Audio-subtitle synchronization

---

## Completed Stories 

### Story 01 - SRT Translation
- [x] SRT parser with timecode preservation
- [x] Ollama AI integration for Hungarian translation
- [x] Context-aware translation pipeline
- [x] YAML configuration with CLI overrides
- [x] Batch processing and directory recursion
- [x] Error handling and retry logic
- [x] Production validation (21 episodes)

### Story 1.5 - Resume and Progress Management
- [x] Progress persistence with .progress files
- [x] Resume/restart CLI options
- [x] Ctrl+C interruption handling
- [x] Multiple translation modes (line/batch/whole-file)
- [x] Entry-level resume capability
- [x] Batch mode performance optimization (35% faster)
- [x] Atomic operations and error recovery

### Story 02A - Overlap Enhancement
- [x] Configurable overlap between batches
- [x] Overlap reassessment feature
- [x] CLI integration (--overlap-size, --no-overlap-reassess)
- [x] Context continuity across boundaries
- [x] Quality improvement validation

### Story 02 - Multi-Model Architecture
- [x] Context Model (story analysis and character profiling)
- [x] Translation Model (context-aware primary translation)
- [x] Technical Validator (quality scoring and validation)
- [x] Dialogue Specialist (character voice consistency)
- [x] Single result file workflow
- [x] Step selection system (--only-translation, --steps)
- [x] gemma3n model integration
- [x] Performance optimization (5x faster with step selection)
- [x] JSON tracking of pipeline steps
- [x] Comprehensive documentation (README + Multi-Model Guide)
- [x] Configuration presets and troubleshooting guides
- [x] Performance matrices and best practices documentation

### Story 09 - MarianMT Alternative Translation Backend 
- [x] **Core Implementation**:
  - [x] MarianMT backend integration (Helsinki-NLP/opus-mt-en-hu model)
  - [x] Backend selection system (`--backend marian` vs `--backend ollama`)
  - [x] GPU acceleration with CPU fallback
  - [x] Automatic model download and caching
  - [x] Error handling and retry logic
  - [x] **Language Pair Support**: Helsinki-NLP/opus-mt-zh-en and opus-mt-en-zh models added for Chinese support. Cache directory changed to project-relative trained_models/cache/marianmt instead of system home directory. Only pre-trained model pairs supported (zh-hu not available, use Ollama)
- [x] **Advanced Multi-line Processing**:
  - [x] Smart multiline strategy with intelligent sentence detection
  - [x] Three configurable strategies: `smart`, `preserve_lines`, `join_all`
  - [x] CLI options: `--multiline-strategy` and `--cross-entry-detection`
- [x] **Cross-Entry Sentence Detection** (NEW BREAKTHROUGH FEATURE):
  - [x] Detects sentences spanning multiple subtitle timestamps
  - [x] Translates cross-entry sentences as cohesive units
  - [x] Maintains original timing with proportional text distribution
  - [x] Intelligent distinction between cross-entry sentences and dialogue
  - [x] Advanced algorithms: `_detect_cross_entry_groups()`, `_entry_completes_sentence()`, `_entry_continues_sentence()`
  - [x] Proportional text splitting: `_split_translation_to_entries()`
- [x] **HTML Formatting Preservation**:
  - [x] Fixed HTML tag corruption issues (e.g., `<i>Previously...</i>`)
  - [x] Proper extraction and restoration of HTML tags
  - [x] Methods: `_extract_html_tags()`, `_restore_html_tags()`
- [x] **Performance & Quality**:
  - [x] 40x speed improvement (0.14s vs 5-6s per entry)
  - [x] Best available translation quality vs Ollama (80-90% satisfactory)
  - [x] **Known limitations**: Occasional issues with specialized argot, formal/informal consistency, rare unclear output
  - [x] Local processing (no internet required after model download)
  - [x] Memory efficient processing
- [x] **Documentation & Testing**:
  - [x] Comprehensive MarianMT User Guide with production examples
  - [x] Neutral Batch Processing Guide
  - [x] Unit and integration tests
  - [x] Cross-entry detection test scripts
  - [x] HTML formatting test scripts
- [x] **Production Features**:
  - [x] PowerShell batch processing script (`translate_all_srt.ps1`)
  - [x] Updated .gitignore patterns for output management
  - [x] Complete README repositioning MarianMT as primary backend
  - [x] Model license documentation and attribution

### Story 09B - HTML Formatting Preservation
- [x] Identified HTML corruption issue: `<i>Previously...</i>` → malformed outputs
- [x] Implemented HTML tag extraction before translation
- [x] Added HTML tag restoration after translation
- [x] Created test scripts for HTML formatting validation
- [x] Verified fix with user-reported examples

### Story 09C - Cross-Entry Sentence Optimization
- [x] Analyzed subtitle timing patterns and sentence boundaries
- [x] Developed cross-entry sentence detection algorithms
- [x] Implemented intelligent grouping vs dialogue distinction
- [x] Created proportional text distribution system
- [x] Added comprehensive test coverage for edge cases

### Story 09D - Backend Architecture Refactoring
- [x] Refactored translator.py for backend abstraction
- [x] Created unified translation client interface
- [x] Implemented backend-specific feature detection
- [x] Added comprehensive backend switching tests
- [x] Updated configuration system for backend selection

### Story 09E - Production Documentation Overhaul
- [x] Complete README.md rewrite positioning MarianMT as primary backend
- [x] Created detailed MarianMT User Guide with production examples
- [x] Developed neutral Batch Processing Guide
- [x] Added model licensing and attribution documentation
- [x] Created PowerShell automation scripts for batch processing

### Story 09F - Plugin System Architecture
- [x] **Core Plugin Infrastructure**:
  - [x] Abstract BaseTranslationProvider class with standardized interface
  - [x] ProviderCapabilities dataclass for feature metadata
  - [x] TranslationProviderRegistry singleton with factory pattern
  - [x] @translation_provider decorator for automatic registration
  - [x] Auto-discovery system loading providers from providers/ directory
- [x] **Provider Migration**:
  - [x] MarianProvider class implementing BaseTranslationProvider interface
  - [x] OllamaProvider class implementing BaseTranslationProvider interface
  - [x] Full backward compatibility with existing MarianClient and OllamaClient
  - [x] Registry-based provider instantiation replacing hardcoded if-elif selection
- [x] **System Integration**:
  - [x] Updated SubtitleTranslator to use registry.get_provider() for backend selection
  - [x] Modified main.py argument parsing to support dynamic provider selection
  - [x] Added --list-providers command for provider discovery and status checking
  - [x] Updated config.py default backend to "marian" for production performance
- [x] **Batch Processing Enhancement**:
  - [x] Enhanced translate_all_srt.ps1 with dynamic -Backend parameter support
  - [x] Added -ListProviders switch for provider enumeration
  - [x] Removed hardcoded backend restrictions allowing any registered provider
  - [x] Improved configuration display showing backend-specific capabilities
- [x] **Extensibility Features**:
  - [x] User plugin directory support (~/.subtitle_translator/plugins/)
  - [x] Plugin loading with error handling and validation
  - [x] Provider capability reporting (batch support, whole-file support, languages)
  - [x] Zero-code-change provider addition through decorator pattern

### Story 12 - Subtitle Row Splitting
- [x] **Configuration System**:
  - [x] Added max_row_length (default: 42) and row_split_method (default: 'even') to config.yaml
  - [x] Enhanced Config dataclass with output section for subtitle formatting
  - [x] Three splitting methods: 'even' (balanced), 'word' (word boundaries), 'char' (character-level)
- [x] **Core Implementation**:
  - [x] Enhanced split_subtitle_text() function in srt_parser.py
  - [x] Improved 'even' algorithm to evaluate all word boundary splits for optimal balance
  - [x] Integration into SubtitleEntry.to_srt_format() for automatic output formatting
- [x] **CLI Integration**:
  - [x] Added --reformat-only option to main.py for reformatting without retranslation
  - [x] Enhanced translate_all_srt.ps1 with -ReformatOnly switch for batch operations
- [x] **Lightweight Reformatter**:
  - [x] Created standalone reformat_srt.py to avoid AI model loading overhead
  - [x] Fast text-only processing for existing translated files
  - [x] Same splitting algorithms as main translator for consistency
- [x] **Quality Optimization**:
  - [x] Algorithm improvement: Fixed splitting from (23,34) chars imbalance to (30,27) chars near-perfect balance
  - [x] Best word boundary selection to minimize line length differences
  - [x] Maintains readability while ensuring compatibility with non-wrapping subtitle viewers

### Story 17 - MarianMT Model Training Feature
- [x] MarianMT model training implementation with GUI and CLI
- [x] Subtitle-optimized translation training pipeline
- [x] Training data preparation and management
- [x] GUI interface for training configuration
- [x] CLI integration for automated training workflows
- [x] Model evaluation and validation
- [x] Integration with existing MarianMT backend
- [x] Documentation and user guides for training feature
