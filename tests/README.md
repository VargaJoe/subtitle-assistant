# Test Structure

This directory contains all tests and test-related files organized by purpose and scope.

## Directory Structure

### `unit/`
Unit tests that test individual components in isolation.
- `test_filename_cleanup.py` - Tests filename language indicator removal
- `test_training_feature.py` - Tests MarianMT training functionality

### `integration/`
Integration tests that test component interactions and end-to-end functionality.
- `test_cross_entry_fix.py` - Tests cross-entry sentence detection fixes
- `test_html_cross_entry.py` - Tests HTML formatting with cross-entry detection
- `test_html_formatting.py` - Tests HTML tag preservation in translations
- `test_user_examples.py` - Tests specific user-reported issues

### `data/`
Test data files used by various tests.
- `.srt` files - Sample subtitle files for testing
- `.progress` files - Sample progress files for resume testing

### `debug/`
Debug and analysis scripts for troubleshooting specific issues.
- `debug_*.py` - Scripts for debugging batch processing, SRT parsing, etc.
- `analyze_issue.py` - General issue analysis script

### Root Level
- `test_backend_switching.py` - Tests for backend switching functionality
- `test_cross_entry_detection.py` - Tests for cross-entry detection algorithms
- `test_marian_client.py` - Tests for MarianMT client functionality

## Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Backend switching tests
pytest tests/test_backend_switching.py
```

### Run Individual Test Scripts
```bash
# These are standalone scripts, not pytest tests
python tests/integration/test_html_formatting.py
python tests/integration/test_user_examples.py
```

## Test Compatibility

All tests have been updated to work with the plugin system:
- ✅ Integration tests use `SubtitleTranslator` (plugin-compatible)
- ✅ Unit tests don't depend on translation backends
- ✅ Updated scripts that used direct clients now use plugin system
- ✅ All tests maintain their original functionality

## Adding New Tests

- **Unit tests**: Add to `tests/unit/`
- **Integration tests**: Add to `tests/integration/`
- **Test data**: Add to `tests/data/`
- **Debug scripts**: Add to `tests/debug/`
- **Backend-specific tests**: Add to root `tests/` directory