# Traditional Translation Guide

This guide covers the simple, reliable traditional translation modes that focus on **Phase 2 only** (translation).

## 🎯 Overview

Traditional translation modes provide straightforward, fast, and reliable subtitle translation:

```
Traditional Modes: Phase 2 Only → Direct AI translation
- line-by-line: Process one entry at a time (most reliable)
- batch: Process multiple entries together (faster)
- whole-file: Process entire file at once (fastest, experimental)
```

**Key Benefits:**
- ✅ **Simple and reliable** - Just translation, no complex pipeline
- ✅ **Fast processing** - No context analysis or validation overhead
- ✅ **Easy to understand** - Straightforward input → translation → output
- ✅ **Perfect for batch processing** - Great for processing many files
- ✅ **Resume support** - Can be interrupted and resumed safely

## 🚀 Quick Start

### CLI Usage
```bash
# Line-by-line (default, most reliable)
python main.py episode.srt --mode line-by-line

# Batch processing (faster)
python main.py episode.srt --mode batch --batch-size 10

# Whole file (fastest, for small files)
python main.py episode.srt --mode whole-file
```

### When to Use Traditional Modes

**✅ Perfect for:**
- Quick subtitle previews
- Batch processing many files
- Testing and development
- Simple translation needs
- When you want fast, consistent results

**⚠️ Consider Multi-Model Instead When:**
- You need highest quality translations
- Character consistency is important
- You're processing important content for production

## ⚙️ Traditional Translation Modes

### 1. Line-by-Line Mode (Default)

**How it works:** Processes one subtitle entry at a time with context from surrounding entries.

```bash
# Basic usage
python main.py episode.srt --mode line-by-line

# With custom context window
python main.py episode.srt --mode line-by-line --config custom-config.yaml

# Resume interrupted translation
python main.py episode.srt --mode line-by-line --resume
```

**Configuration:**
```yaml
translation:
  context_window: 3  # Number of surrounding entries for context
  temperature: 0.3   # AI creativity (0.0 = consistent, 1.0 = creative)
  
processing:
  translation_mode: "line-by-line"
```

**Performance:**
- **Speed:** ~13-18 seconds per entry
- **Memory:** Low (processes one entry at a time)
- **Reliability:** Highest (individual retry per entry)
- **Resume:** ✅ Entry-level resume capability

**Best for:**
- Reliable, interruptible processing
- Large files where you might need to stop/start
- When consistency is more important than speed

### 2. Batch Mode (Recommended for Speed)

**How it works:** Groups multiple subtitle entries together and translates them as a batch for better efficiency.

```bash
# Basic batch processing
python main.py episode.srt --mode batch --batch-size 10

# With overlap for context continuity
python main.py episode.srt --mode batch --batch-size 5 --overlap-size 2

# Custom batch settings
python main.py episode.srt --mode batch --batch-size 15 --no-overlap-reassess
```

**Configuration:**
```yaml
processing:
  translation_mode: "batch"
  batch_size: 10        # Entries per batch
  overlap_size: 2       # Context overlap between batches
  reassess_overlaps: true  # Re-evaluate overlapped entries
```

**Performance:**
- **Speed:** ~10-13 seconds per entry (35% faster than line-by-line)
- **Memory:** Medium (holds batch in memory)
- **Reliability:** High (batch-level retry)
- **Resume:** ✅ Batch-level resume capability

**Best for:**
- Good balance of speed and reliability
- Processing medium to large files efficiently
- When you want faster results but still need resume capability

**Batch Size Guidelines:**
- **Small batches (5-8):** Better context, more reliable
- **Medium batches (10-15):** Good balance of speed and quality
- **Large batches (20+):** Fastest but may lose context quality

### 3. Whole-File Mode (Experimental)

**How it works:** Sends the entire subtitle file to the AI at once for translation.

```bash
# Whole file translation (best for small files)
python main.py small-episode.srt --mode whole-file

# Not recommended for large files
python main.py large-episode.srt --mode whole-file  # May timeout or run out of memory
```

**Configuration:**
```yaml
processing:
  translation_mode: "whole-file"

ollama:
  timeout: 600  # Increase timeout for large files
```

**Performance:**
- **Speed:** Very fast for small files (~5-8 seconds per entry)
- **Memory:** High (entire file in memory)
- **Reliability:** Lower (single point of failure)
- **Resume:** ❌ No resume capability

**Best for:**
- Small test files (< 50 entries)
- Quick previews
- Testing translation quality

**Limitations:**
- No resume capability
- May timeout on large files
- Can run out of memory
- Single point of failure

## 📊 Performance Comparison

### Speed Comparison (400-entry TV episode)
| Mode | Time per Entry | Total Time | Reliability | Resume |
|------|----------------|------------|-------------|--------|
| line-by-line | 13-18 seconds | ~1.8 hours | ⭐⭐⭐⭐⭐ | ✅ Entry-level |
| batch (size 10) | 10-13 seconds | ~1.2 hours | ⭐⭐⭐⭐ | ✅ Batch-level |
| batch (size 20) | 8-12 seconds | ~1.0 hours | ⭐⭐⭐ | ✅ Batch-level |
| whole-file | 5-8 seconds | ~0.7 hours | ⭐⭐ | ❌ None |

### Memory Usage
| Mode | RAM Usage | Disk I/O | Network |
|------|-----------|----------|---------|
| line-by-line | ~50MB | Low | Frequent small requests |
| batch | ~100-200MB | Medium | Medium-sized requests |
| whole-file | ~500MB+ | High | One large request |

## ⚙️ Configuration

### Basic Configuration (config.yaml)

```yaml
# Traditional translation settings
translation:
  source_language: "en"
  target_language: "hu"
  model: "gemma3:latest"
  temperature: 0.3
  context_window: 3
  max_retries: 3

# Processing mode selection
processing:
  translation_mode: "batch"  # or "line-by-line", "whole-file"
  batch_size: 10
  overlap_size: 2
  reassess_overlaps: true
  progress_display: true
  backup_original: true
  resume_enabled: true

# Ollama connection
ollama:
  host: "localhost"
  port: 11434
  timeout: 300  # Increase for large files or slow models
```

### Advanced Configuration Examples

#### Fast Processing (Maximum Speed)
```yaml
processing:
  translation_mode: "batch"
  batch_size: 20  # Larger batches
  overlap_size: 1  # Minimal overlap
  reassess_overlaps: false  # Skip reassessment

translation:
  context_window: 1  # Minimal context
  temperature: 0.2   # More consistent/faster
```

#### Reliable Processing (Maximum Reliability)
```yaml
processing:
  translation_mode: "line-by-line"
  
translation:
  context_window: 5  # More context
  max_retries: 5     # More retry attempts
  temperature: 0.3   # Balanced creativity
```

#### Quality Processing (Best Traditional Quality)
```yaml
processing:
  translation_mode: "batch"
  batch_size: 8      # Smaller batches for better context
  overlap_size: 3    # More overlap
  reassess_overlaps: true

translation:
  context_window: 5  # More context
  temperature: 0.3   # Balanced creativity
```

## 🔧 CLI Reference

### Common Commands

```bash
# Basic translation
python main.py episode.srt

# Specify mode explicitly
python main.py episode.srt --mode batch

# Custom batch size
python main.py episode.srt --mode batch --batch-size 15

# With overlap settings
python main.py episode.srt --mode batch --batch-size 10 --overlap-size 3

# Disable overlap reassessment (faster)
python main.py episode.srt --mode batch --no-overlap-reassess

# Resume interrupted translation
python main.py episode.srt --resume

# Force restart (ignore existing progress)
python main.py episode.srt --restart

# Verbose output for debugging
python main.py episode.srt --mode batch --verbose

# Custom configuration
python main.py episode.srt --config my-config.yaml

# Multiple files
python main.py "subtitles/*.srt" --batch --mode batch
```

### CLI Options for Traditional Modes

| Option | Description | Example |
|--------|-------------|---------|
| `--mode` | Translation mode | `--mode batch` |
| `--batch-size` | Entries per batch | `--batch-size 10` |
| `--overlap-size` | Context overlap | `--overlap-size 2` |
| `--no-overlap-reassess` | Skip overlap reassessment | `--no-overlap-reassess` |
| `--resume` | Resume from interruption | `--resume` |
| `--restart` | Force restart | `--restart` |
| `--verbose` | Detailed output | `--verbose` |
| `--config` | Configuration file | `--config custom.yaml` |

## 🎯 Best Practices

### File Size Guidelines

**Small Files (< 50 entries):**
- Use `whole-file` mode for fastest results
- Or `batch` with size 10-15

**Medium Files (50-500 entries):**
- Use `batch` mode with size 10-15
- Enable overlap for better context

**Large Files (500+ entries):**
- Use `line-by-line` for maximum reliability
- Or `batch` with smaller sizes (8-10) for better error recovery

### Error Handling

**Network Issues:**
```yaml
ollama:
  timeout: 600     # Increase timeout
  
translation:
  max_retries: 5   # More retry attempts
```

**Memory Issues:**
- Reduce batch size
- Use line-by-line mode
- Reduce context window

**Quality Issues:**
- Increase context window
- Use smaller batch sizes
- Enable overlap reassessment

### Performance Optimization

**For Speed:**
1. Use batch mode with larger batches (15-20)
2. Disable overlap reassessment
3. Reduce context window
4. Use faster AI models

**For Quality:**
1. Use smaller batch sizes (5-8)
2. Enable overlap reassessment
3. Increase context window
4. Use higher-quality AI models

**For Reliability:**
1. Use line-by-line mode
2. Increase retry attempts
3. Regular progress saves
4. Enable verbose logging

## 🔄 Migration from Multi-Model

If you're used to multi-model mode but want faster processing:

```bash
# Instead of multi-model translation-only
python main.py episode.srt --mode multi-model --only-translation

# Use traditional batch mode (similar speed, simpler)
python main.py episode.srt --mode batch --batch-size 10
```

### Feature Comparison

| Feature | Multi-Model --only-translation | Traditional Batch |
|---------|-------------------------------|------------------|
| Speed | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Simplicity | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Configuration | Complex | Simple |
| Overhead | Medium | Low |
| Resume | ✅ | ✅ |

## 🆚 vs Multi-Model Mode

### When to Use Traditional Instead of Multi-Model

**✅ Choose Traditional When:**
- You need fast, consistent results
- Processing many files in batch
- Testing or development work
- Simple translation requirements
- You want minimal configuration

**✅ Choose Multi-Model When:**
- Quality is more important than speed
- Character consistency matters
- Processing important/production content
- You need validation and refinement

### Performance vs Quality Trade-off

```
Traditional:    [⚡⚡⚡⚡⚡] Speed     [⭐⭐⭐] Quality
Multi-Model:    [⚡⚡] Speed         [⭐⭐⭐⭐⭐] Quality
```

## 🔍 Troubleshooting

### Common Issues

**Translation Timeouts:**
```bash
# Increase timeout
python main.py episode.srt --mode batch --batch-size 5
```

**Memory Errors:**
```bash
# Use smaller batches or line-by-line
python main.py episode.srt --mode line-by-line
```

**Quality Issues:**
```bash
# Increase context and enable overlap
python main.py episode.srt --mode batch --batch-size 8 --overlap-size 3
```

**Resume Not Working:**
```bash
# Check for .progress files and use --resume explicitly
python main.py episode.srt --mode batch --resume
```

### Debug Mode

```bash
# Enable verbose output for troubleshooting
python main.py episode.srt --mode batch --verbose

# This shows:
# - Batch processing details
# - AI model responses
# - Progress information
# - Error details
```

## 📈 Real-World Examples

### Processing a TV Season (24 episodes, ~400 entries each)

**Fast Processing:**
```bash
# Process all episodes with batch mode
for episode in subtitles/season01/*.srt; do
    python main.py "$episode" --mode batch --batch-size 15
done

# Expected time: ~20-24 hours total
```

**Reliable Processing:**
```bash
# Process with line-by-line for maximum reliability
for episode in subtitles/season01/*.srt; do
    python main.py "$episode" --mode line-by-line
done

# Expected time: ~30-36 hours total
```

### Quick Preview Translation

```bash
# Translate just first 50 entries for preview
head -n 200 episode.srt > preview.srt  # 50 entries × 4 lines
python main.py preview.srt --mode whole-file
```

---

*For advanced features and highest quality translations, see the [Multi-Model Architecture Guide](multi-model-guide.md)*
