# Story 1.5 - Resume and Progress Management

## Story Title
**Resume Interrupted Translations and Progress Tracking**

## User Story
As a user translating large subtitle files or batch processing multiple episodes, I want the ability to resume interrupted translations and track progress, so that I don't lose hours of work when the process is stopped or fails.

## Acceptance Criteria

### Must Have
- [ ] **Progress State Persistence**: Save translation progress to disk during processing
- [ ] **Resume Functionality**: Detect and resume interrupted translations automatically
- [ ] **Batch Resume**: Resume batch processing from the last completed file
- [ ] **Entry-Level Resume**: Resume individual files from the last completed subtitle entry
- [ ] **Progress File Management**: Clean up completed progress files automatically

### Should Have
- [ ] **Progress Indicators**: Show detailed progress with estimated time remaining
- [ ] **Safe Interruption**: Handle Ctrl+C gracefully with state saving
- [ ] **Corruption Recovery**: Validate and recover from corrupted progress files
- [ ] **Multi-File Progress**: Track progress across entire batch operations

### Could Have
- [ ] **Progress Dashboard**: Visual progress display for long operations
- [ ] **Resume Confirmation**: Ask user before resuming vs starting fresh
- [ ] **Progress History**: Keep history of completed translations
- [ ] **Selective Resume**: Choose which files to resume vs restart

## Technical Requirements

### Progress File Format
```json
{
  "source_file": "path/to/input.srt",
  "target_file": "path/to/output.srt", 
  "total_entries": 433,
  "completed_entries": 156,
  "last_completed_index": 156,
  "start_time": "2025-06-22T20:59:29",
  "last_update": "2025-06-22T21:15:30",
  "config_hash": "md5_of_translation_config",
  "translated_entries": [
    {
      "index": 1,
      "original": "Hello, world",
      "translated": "Helló, világ",
      "timestamp": "2025-06-22T20:59:45"
    }
  ]
}
```

### Batch Progress Format
```json
{
  "batch_id": "magnum_s02_20250622",
  "input_pattern": "subtitles/Magnum.P.I.S02.*.srt",
  "output_dir": "output/",
  "total_files": 21,
  "completed_files": 3,
  "current_file": "Magnum.P.I.S02E04.srt",
  "failed_files": [],
  "start_time": "2025-06-22T20:59:29"
}
```

### Implementation Areas
- [ ] **Progress Manager Module**: Handle progress file creation and management
- [ ] **Resume Detection**: Check for existing progress files on startup
- [ ] **State Serialization**: Save/load translation state efficiently
- [ ] **CLI Resume Options**: `--resume`, `--restart`, `--continue-batch`
- [ ] **Error Handling**: Graceful handling of corrupted progress files

## Priority
**High** - Critical for production use with large files

## Estimated Effort
**Medium** - 2-3 days development time

## Definition of Done
- [ ] Can resume any interrupted single file translation
- [ ] Can resume batch processing from any point
- [ ] Progress files are cleaned up after successful completion
- [ ] CLI commands support resume operations
- [ ] Tested with large files and interruption scenarios
- [ ] Documentation includes resume usage examples

## User Experience Examples

### Resume Single File
```bash
# Start translation
python main.py large_movie.srt --verbose

# Process interrupted at entry 234/800
# Later...

# Resume automatically detected
python main.py large_movie.srt --verbose
> ✅ Found existing progress (234/800 completed)
> ❓ Resume from entry 235? [Y/n]: y
> 🔄 Resuming translation...
```

### Resume Batch Processing  
```bash
# Start batch
python main.py "season2/*.srt" --batch

# Interrupted after completing 3/21 files
# Later...

# Resume batch
python main.py "season2/*.srt" --batch --resume
> ✅ Found batch progress (3/21 files completed)
> 📁 Resuming from: Magnum.P.I.S02E04.srt
```

## Implementation Notes
- Progress files stored in `.subtitle-progress/` directory
- Use file locks to prevent concurrent access
- Validate config compatibility before resuming
- Option to force restart with `--restart` flag
- Clean up progress files older than 7 days automatically
