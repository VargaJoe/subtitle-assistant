# Story 16 - Folder-Specific Configuration Overrides

## Overview
Enable folder-specific configuration overrides to allow different translation settings for different subtitle collections within the same directory structure.

## Business Value
- Process mixed-language subtitle collections in a single batch
- Apply different translation strategies per TV show/movie
- Reduce manual configuration changes when processing diverse content
- Enable per-project or per-season translation customization

## User Stories

### US-16.1: Create Folder-Specific Config Files
**As a** power user  
**I want** to place config files in subtitle folders  
**So that** each folder can have its own translation settings

**Acceptance Criteria:**
- Support `.subtitle-config.yaml` in any folder
- Config file is optional (falls back to parent/root config)
- Nested folders inherit parent folder configs
- Child folder configs can override specific parent settings
- Config file format matches main `config.yaml` structure

### US-16.2: Override Source/Target Languages
**As a** user processing multilingual content  
**I want** to override source and target languages per folder  
**So that** I can translate different language subtitles without manual intervention

**Acceptance Criteria:**
- Folder config can override `source_language`
- Folder config can override `target_language`
- Language overrides apply to all files in that folder and subfolders
- Clear logging shows which config is being used
- Validation ensures language overrides are valid

**Example Structure:**
```
subtitles/
├── config.yaml (en->hu)
├── English-Shows/
│   └── .subtitle-config.yaml (en->hu, specific model)
├── German-Shows/
│   └── .subtitle-config.yaml (de->hu, different model)
└── French-Movies/
    └── .subtitle-config.yaml (fr->hu, different backend)
```

### US-16.3: Override Translation Backend and Model
**As a** user  
**I want** to use different backends or models per folder  
**So that** I can optimize translation quality for different content types

**Acceptance Criteria:**
- Folder config can override `translation_backend` (ollama/marian)
- Folder config can override `model` selection
- Folder config can override `fallback_models`
- Backend switching validated before translation starts
- Model availability checked for each override

### US-16.4: Override Processing Settings
**As a** user  
**I want** to configure batch size and processing mode per folder  
**So that** I can optimize performance for different file sizes

**Acceptance Criteria:**
- Folder config can override `translation_mode`
- Folder config can override `batch_size`
- Folder config can override `overlap_size`
- Folder config can override `context_window`
- Folder config can override `verbose` setting

### US-16.5: Override Output Settings
**As a** user  
**I want** to control output format per folder  
**So that** different subtitle collections have appropriate formatting

**Acceptance Criteria:**
- Folder config can override `max_row_length`
- Folder config can override `row_split_method`
- Folder config can override `output_suffix`
- Folder config can override `preserve_formatting`
- Output settings validated before translation

### US-16.6: Visualize Active Configuration
**As a** user  
**I want** to see which configuration is active for each file  
**So that** I can verify the correct settings are being used

**Acceptance Criteria:**
- Verbose mode shows config hierarchy
- Log message shows which config file is active
- Display effective settings (after overrides applied)
- Show config file path being used
- CLI option to preview effective config per folder without translating

### US-16.7: Inherit and Merge Configurations
**As a** user with nested folder structures  
**I want** configurations to merge intelligently  
**So that** I can set defaults at the top level and override only what's needed

**Acceptance Criteria:**
- Child configs inherit all settings from parent
- Child configs can override individual settings
- Deep merge of nested config sections
- Clear precedence rules documented
- No breaking of existing single-config behavior

## Technical Implementation

### Phase 1: Configuration Discovery
**Task 16.1.1:** Implement config file discovery
- Create `ConfigResolver` class in `subtitle_translator/config_resolver.py`
- Implement `find_config_for_path()` method
- Walk directory tree from file location to project root
- Cache discovered configs for performance
- Handle config file errors gracefully

**Task 16.1.2:** Add config file naming conventions
- Support `.subtitle-config.yaml` (hidden file)
- Support `subtitle-config.yaml` (visible file)
- Support `.srt-config.yaml` (alternative)
- Document naming conventions
- Priority order if multiple configs exist

**Task 16.1.3:** Implement config hierarchy
- Build config chain from root to file location
- Implement inheritance logic
- Create merged config object
- Handle circular inheritance (if symlinks)
- Add debug mode to show config chain

### Phase 2: Configuration Merging
**Task 16.2.1:** Implement deep merge algorithm
- Merge nested dictionary structures
- Handle list merging (replace vs. extend)
- Handle null values (unset vs. remove)
- Support merge strategies per field type
- Add comprehensive test coverage

**Task 16.2.2:** Define override precedence
- Document precedence: CLI > Folder > Parent > Root
- Implement precedence rules
- Handle conflicting overrides
- Validate merged configuration
- Add precedence visualization tool

**Task 16.2.3:** Optimize config loading
- Cache loaded configs in memory
- Invalidate cache on file modification
- Share configs between parallel processes
- Minimize file system access
- Benchmark performance impact

### Phase 3: Integration with Translator
**Task 16.3.1:** Update SubtitleTranslator class
- Accept config resolver instance
- Resolve config per file during batch processing
- Log active config for each file
- Handle config changes mid-batch
- Support config reload without restart

**Task 16.3.2:** Update batch processing
- Integrate config resolver in `batch_translate()`
- Group files by effective config (optimization)
- Update progress tracking for config changes
- Handle backend switches gracefully
- Log config summary before batch starts

**Task 16.3.3:** Update CLI interface
- Add `--show-config` flag to preview effective config
- Add `--config-path` to override discovery
- Add `--ignore-folder-configs` to disable overrides
- Update help text with examples
- Add verbose logging for config discovery

**Task 16.3.4:** Update PowerShell scripts
- Integrate config resolution in `translate_all_srt.ps1`
- Display folder-specific configs in summary
- Add `-ShowConfigs` switch to preview
- Handle config errors gracefully
- Update documentation

### Phase 4: Configuration Validation
**Task 16.4.1:** Implement validation rules
- Validate each override independently
- Check backend availability before translation
- Verify model exists for Ollama
- Validate language codes
- Check file path permissions

**Task 16.4.2:** Add config linting tool
- Create `lint_config.py` utility
- Check all folder configs in tree
- Report validation errors
- Suggest fixes for common issues
- Support CI/CD integration

**Task 16.4.3:** Add migration utilities
- Tool to generate folder configs from main config
- Tool to consolidate common overrides
- Tool to update all configs when schema changes
- Backup and restore functionality
- Dry-run mode for testing

### Phase 5: Documentation and Testing
**Task 16.5.1:** Create user documentation
- Write "Folder Configuration Guide"
- Document use cases and examples
- Provide templates for common scenarios
- Add troubleshooting section
- Create video tutorial

**Task 16.5.2:** Update existing documentation
- Update README with folder config info
- Update batch processing guide
- Add folder config to quick start
- Update all examples to mention overrides
- Add FAQ section

**Task 16.5.3:** Create comprehensive tests
- Unit tests for ConfigResolver
- Integration tests with real folder structures
- Test precedence rules
- Test validation and error handling
- Performance tests for large trees

## Configuration Example

### Root Config: `config.yaml`
```yaml
translation:
  backend: "marian"
  source_language: "en"
  target_language: "hu"
  model: "Helsinki-NLP/opus-mt-en-hu"

processing:
  translation_mode: "line-by-line"
  batch_size: 10
  verbose: false

output:
  max_row_length: 42
  row_split_method: "even"
```

### Folder Override: `subtitles/German-Shows/.subtitle-config.yaml`
```yaml
# Override only what's different
translation:
  source_language: "de"  # Override: German source
  model: "Helsinki-NLP/opus-mt-de-hu"  # German->Hungarian model

processing:
  verbose: true  # More logging for this folder
```

### Subfolder Override: `subtitles/German-Shows/ShowName/.subtitle-config.yaml`
```yaml
# Further override for specific show
processing:
  batch_size: 20  # Larger batches for this show
  
output:
  max_row_length: 50  # Longer lines for this show
```

## Effective Configuration Logic

For file: `subtitles/German-Shows/ShowName/episode.srt`

1. Load root: `config.yaml`
2. Merge: `subtitles/.subtitle-config.yaml` (if exists)
3. Merge: `subtitles/German-Shows/.subtitle-config.yaml`
4. Merge: `subtitles/German-Shows/ShowName/.subtitle-config.yaml`
5. Apply CLI overrides
6. Validate final config

Result:
```yaml
translation:
  backend: "marian"  # from root
  source_language: "de"  # from German-Shows
  target_language: "hu"  # from root
  model: "Helsinki-NLP/opus-mt-de-hu"  # from German-Shows

processing:
  translation_mode: "line-by-line"  # from root
  batch_size: 20  # from ShowName
  verbose: true  # from German-Shows

output:
  max_row_length: 50  # from ShowName
  row_split_method: "even"  # from root
```

## CLI Examples

```bash
# Preview effective config for a folder
python main.py --show-config subtitles/German-Shows/

# Translate with folder configs
python main.py subtitles/**/*.srt --batch

# Ignore folder configs (use root config only)
python main.py subtitles/**/*.srt --batch --ignore-folder-configs

# Override even folder configs with CLI
python main.py input.srt --source fr --target en
# CLI always wins
```

## Dependencies
- Enhanced `Config` class with merge support
- New `ConfigResolver` class
- YAML parsing library (already have PyYAML)
- Path traversal utilities (pathlib)

## Testing Strategy
1. **Unit Tests**: Test config merging logic
2. **Integration Tests**: Test with real folder structures
3. **Precedence Tests**: Verify override precedence rules
4. **Performance Tests**: Ensure minimal overhead
5. **Error Tests**: Validate error handling for invalid configs

## Success Metrics
- Config resolution < 10ms per file
- Support arbitrary nesting depth
- 100% backward compatibility with single config
- Zero errors for valid config hierarchies
- Clear error messages for invalid configs

## Future Enhancements
- Web UI for managing folder configs
- Auto-generate configs based on filename patterns
- Config templates for popular subtitle sources
- Sync folder configs with cloud storage
- A/B testing different configs on same content
