# MarianMT Translation Backend - User Guide

MarianMT is the best local/offline backend for Subtitle Assistant. It is a strong fit when you need fast processing without internet access, but if you have reliable internet and want the strongest translation quality, the Gemini backend is usually the better choice.

## Performance Modes

```powershell
# Line-by-line mode (safest, resumable)
python main.py "subtitles/sample.srt" --backend marian --mode line-by-line

# Batch mode (faster processing)
python main.py "subtitles/sample.srt" --backend marian --mode batch

# Whole-file mode (fastest for small files)
python main.py "subtitles/sample.srt" --backend marian --mode whole-file
```

## Multi-Line Subtitle Handling

MarianMT supports intelligent handling of multi-line subtitles with configurable strategies:

```powershell
# Smart detection (default) - automatically detects single sentences vs dialogue
python main.py "subtitles/sample.srt" --backend marian --multiline-strategy smart

# Preserve line breaks - always keep original line structure
python main.py "subtitles/sample.srt" --backend marian --multiline-strategy preserve_lines

# Join all lines - always combine into single sentence
python main.py "subtitles/sample.srt" --backend marian --multiline-strategy join_all
```

**Strategy Examples:**

**Smart Strategy (Recommended):**
```
Input:  "A loud enough fight\nthat your neighbors called 911."
Output: "Egy elég hangos harc, amit a szomszédok hívtak a 911-nek."  ✅ Single sentence

Input:  "- Have you seen my daughter?\n- No, lo siento."
Output: "- Nem láttad a lányomat?\n- Nem, lo siento."  ✅ Dialogue preserved
```

**Preserve Lines Strategy:**
```
Input:  "A loud enough fight\nthat your neighbors called 911."
Output: "Hangos, elég harc.\nhogy a szomszédja hívta a 911-et."  ❌ Broken grammar
```

**Join All Strategy:**
```
Input:  "- Have you seen my daughter?\n- No, lo siento."
Output: "- Nem láttad a lányomat?"  ❌ Dialogue lost
```

### Cross-Entry Sentence Detection (NEW!)

MarianMT now includes advanced cross-entry sentence detection that identifies sentences spanning multiple subtitle timestamps and translates them as cohesive units while maintaining original timing.

```powershell
# Enable cross-entry detection (default when using smart strategy)
python main.py "subtitles/sample.srt" --backend marian --multiline-strategy smart --cross-entry-detection

# Disable cross-entry detection if needed
python main.py "subtitles/sample.srt" --backend marian --multiline-strategy smart --no-cross-entry-detection
```

**Cross-Entry Detection Examples:**

**Cross-Entry Sentence (3 timestamps):**
```
Input:  Entry 1: "This is now"
        Entry 2: "an NYPD homicide investigation,"  
        Entry 3: "so if we collar Hughes, we'll let you know."

Groups:  [1,2,3] detected as single sentence spanning multiple entries

Translation: "Ez most egy rendőrségi gyilkossági nyomozás, szóval ha elkapjuk Hughest, szólunk."

Output: Entry 1: "Ez"
        Entry 2: "most egy rendőrségi gyilkossági"
        Entry 3: "nyomozás, szóval ha elkapjuk Hughest, szólunk."
```

**Dialogue Detection (preserved separately):**
```
Input:  Entry 4: "- Have you seen my daughter?"
        Entry 5: "- No, lo siento."

Groups:  [4] and [5] detected as separate dialogue lines

Output: Entry 4: "- Nem láttad a lányomat?"
        Entry 5: "- Nem, lo siento."
```

**Benefits:**
- ✅ **Better Context**: Translates complete sentences instead of fragments
- ✅ **Timing Preserved**: Proportionally distributes translation across original entries
- ✅ **Smart Detection**: Distinguishes between cross-entry sentences and dialogue
- ✅ **Automatic**: Works seamlessly with smart multiline strategy Overview

MarianMT is a high-performance neural machine translation backend for the Subtitle Assistant project. It provides **40x faster** translation speeds compared to Ollama while maintaining good subtitle translation quality for local/offline workflows.

## Key Benefits

- ⚡ **Ultra-Fast Performance**: 0.14 seconds per subtitle entry (vs 5-6 seconds with Ollama)
- 🎯 **Good Local Quality**: Natural Hungarian translations using Helsinki-NLP models, suitable for offline use
- 🖥️ **Local Processing**: No internet required, works completely offline
- 💾 **Automatic Model Management**: Downloads and caches models automatically
- 🔄 **GPU Acceleration**: Supports CUDA when available, falls back to CPU

## Quick Start

### 1. Installation

Install required dependencies:
```powershell
pip install torch transformers sentencepiece
```

### 2. Basic Usage

Use MarianMT backend with any translation command:
```powershell
# Single file translation
python main.py "subtitles/sample.srt" --backend marian

# With verbose output
python main.py "subtitles/sample.srt" --backend marian --verbose

# Line-by-line mode (default)
python main.py "subtitles/sample.srt" --backend marian --mode line-by-line
```

### 3. Performance Modes

```powershell
# Line-by-line mode (safest, resumable)
python main.py "subtitles/sample.srt" --backend marian --mode line-by-line

# Batch mode (faster processing)
python main.py "subtitles/sample.srt" --backend marian --mode batch

# Whole-file mode (fastest for small files)
python main.py "subtitles/sample.srt" --backend marian --mode whole-file
```

## Configuration

### Backend Selection

Set MarianMT as default backend in `config.yaml`:
```yaml
backend: "marian"  # Options: "ollama", "marian"
```

Or use CLI parameter to override:
```powershell
python main.py "file.srt" --backend marian
```

### MarianMT Specific Settings

Current optimized configuration in `config.yaml`:
```yaml
marian:
  model: "Helsinki-NLP/opus-mt-en-hu"
  max_new_tokens: 128
  repetition_penalty: 1.2
  no_repeat_ngram_size: 3
  device: "auto"  # "auto", "cuda", "cpu"
```

## Performance Comparison

| Backend | Speed (per entry) | Quality | GPU Required | Internet Required |
|---------|------------------|---------|--------------|-------------------|
| Ollama  | 5-6 seconds      | ⭐⭐⭐⭐ | Optional     | No                |
| MarianMT| 0.14 seconds     | ⭐⭐⭐⭐ | Optional     | No (after model download) |

## When to Use Gemini Instead

If you have internet access and want the best overall translation quality, use the Gemini backend instead of MarianMT. Gemini generally produces more natural and higher-quality translations, especially for cloud-based workflows.

## Production Usage Examples

### Process Individual Episodes
```powershell
# Single file processing
python main.py "./subtitles/season01/episode_01.srt" --backend marian --verbose
python main.py "./subtitles/season01/episode_02.srt" --backend marian --verbose

# Different series structure
python main.py "./subtitles/series_a/s01e01.srt" --backend marian --verbose
python main.py "./subtitles/series_a/s01e02.srt" --backend marian --verbose
```

### Batch Processing Entire Seasons
```powershell
# Process entire season directory
Get-ChildItem ".\subtitles\season01\*.srt" | ForEach-Object {
    Write-Host "Processing: $($_.Name)"
    python main.py $_.FullName --backend marian --verbose
}

# Process multiple series
Get-ChildItem ".\subtitles\series_a\*.srt" | ForEach-Object {
    Write-Host "Processing: $($_.Name)"
    python main.py $_.FullName --backend marian --verbose
}
```

## Model Information

### Helsinki-NLP/opus-mt-en-hu
- **Size**: ~484MB download (cached locally)
- **Language Pair**: English → Hungarian
- **Quality**: Excellent for subtitle translation
- **Speed**: Optimized for subtitle-length segments

### First-Time Model Download
```
Downloading (…)pytorch_model.bin: 100%|████████| 301M/301M
Downloading (…)generation_config.json: 100%|████████| 293/293
Downloading (…)okenizer_config.json: 100%|████████| 42.0/42.0
Downloading (…)cial_tokens_map.json: 100%|████████| 2.54k/2.54k
Downloading (…)source.spm: 100%|████████| 802k/802k
Downloading (…)target.spm: 100%|████████| 826k/826k
Downloading (…)vocab.json: 100%|████████| 1.59M/1.59M
```

## Translation Quality Examples

### Input (English)
```
"Hello, how are you?"
"I need to find my keys."
"What's your name?"
```

### Output (Hungarian - MarianMT)
```
"Helló, hogy vagy?"
"Meg kell találnom a kulcsaimat."
"Mi a neved?"
```

## Troubleshooting

### Common Issues

#### Model Download Fails
```powershell
# Clear cache and retry
Remove-Item -Recurse -Force "$env:USERPROFILE\.cache\huggingface"
python main.py "file.srt" --backend marian
```

#### CUDA Out of Memory
```powershell
# Force CPU usage
python main.py "file.srt" --backend marian --device cpu
```

#### Poor Translation Quality
Check model configuration:
```yaml
marian:
  model: "Helsinki-NLP/opus-mt-en-hu"  # Use this model, NOT NYTK
  max_new_tokens: 128                  # Prevent truncation
  repetition_penalty: 1.2              # Prevent repetition
  no_repeat_ngram_size: 3              # Quality control
```

### Performance Tips

1. **GPU Acceleration**: Install CUDA-compatible PyTorch for 2-3x speed improvement
2. **Batch Processing**: Use batch mode for faster processing of large files
3. **Model Caching**: Models are cached after first download - no re-download needed
4. **Memory Management**: MarianMT uses ~2GB RAM for optimal performance

## File Organization

### Input Files
```
subtitles/
  ├── season01/
  │   ├── episode_01.srt
  │   └── episode_02.srt
  └── series_a/
      ├── s01e01.srt
      └── s01e02.srt
```

### Output Files
```
subtitles/
  ├── season01/
  │   ├── episode_01.hu.srt          # Translated
  │   └── episode_01.hu.progress     # Progress file
  └── series_a/
      ├── s01e01.hu.srt             # Translated
      └── s01e01.hu.progress        # Progress file
```

## Advanced Usage

### Resume Interrupted Translations
```powershell
# Resume from where it left off
python main.py "large-file.srt" --backend marian --resume

# Restart completely
python main.py "large-file.srt" --backend marian --restart
```

### Verbose Monitoring
```powershell
# See detailed progress
python main.py "file.srt" --backend marian --verbose
```

Output includes:
- Translation speed (entries/second)
- Model loading time
- Progress percentage
- Estimated completion time

## Integration with Multi-Model Architecture

MarianMT can be combined with the multi-model architecture for enhanced quality:

```powershell
# Use MarianMT for base translation, Ollama for quality enhancement
python main.py "file.srt" --backend marian --mode multi-model
```

This approach:
1. Uses MarianMT for fast initial translation
2. Uses Ollama models for context analysis and validation
3. Combines speed of MarianMT with quality of multi-model workflow

## Best Practices

1. **Production Environment**: Always use `--verbose` for monitoring
2. **Large Files**: Use `--mode line-by-line` for resumable processing
3. **Quality Focus**: Consider multi-model mode for highest quality
4. **Speed Focus**: Use pure MarianMT backend for maximum speed
5. **Backup**: Progress files enable safe interruption and resume

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review configuration in `config.yaml`
3. Test with sample files first
4. Use `--verbose` flag for debugging information
