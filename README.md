# Subtitle Assistant

🎬 **AI-powered subtitle translation tool** primarily designed for **hearing-impaired users** and others who **need** subtitles to access multimedia content.

## 🎯 Project Mission

**Primary Goal**: This project serves people who **cannot** watch or understand movies and TV shows without subtitles - primarily the hearing-impaired community who depend on subtitles for accessibility.

**Secondary Goals**: Support those who don't understand the original language and language learners.

While mainstream perception often views subtitles as some kind of luxury or convenience tool, **my priority is accessibility for those who have no alternative**. To bridge communication gaps by providing high-quality subtitle translations that make entertainment truly accessible to everyone.

## ⚡ **Recommended: MarianMT Backend (Production Ready)**

**MarianMT** is our **primary recommendation** for production subtitle translation, offering the best balance of speed, quality, and reliability.

### 🚀 Quick Start with MarianMT

```bash
# Single file translation
python main.py "movie.srt" --backend marian

# With cross-entry sentence detection (recommended)
python main.py "movie.srt" --backend marian --multiline-strategy smart

# Batch processing multiple files
python main.py "subtitles/*.srt" --backend marian --verbose

# Different multiline strategies
python main.py "movie.srt" --backend marian --multiline-strategy smart      # Intelligent detection
python main.py "movie.srt" --backend marian --multiline-strategy preserve_lines  # Keep line breaks
python main.py "movie.srt" --backend marian --multiline-strategy join_all  # Join as sentences
```

### 🎯 MarianMT Key Features

- ⚡ **Ultra-Fast**: 40x faster than Ollama (0.14s vs 5-6s per entry)
- 🧠 **Intelligent Processing**: Cross-entry sentence detection spanning multiple timestamps
- 🎭 **Smart Detection**: Automatically distinguishes dialogue from cross-entry sentences  
- ⏱️ **Timing Preserved**: Maintains original subtitle timing with proportional text distribution
- 🖥️ **Local Processing**: No internet required, works completely offline
- 💾 **Auto-Model Management**: Downloads and caches models automatically
- 🔄 **GPU Acceleration**: CUDA support with CPU fallback

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- For MarianMT: PyTorch and Transformers

### Setup for MarianMT (Recommended)
```bash
# Clone repository
git clone https://github.com/VargaJoe/subtitle-assistant.git
cd subtitle-assistant

# Install dependencies (including MarianMT)
pip install -r requirements.txt

# Test installation
python main.py --help
```

### Alternative: Ollama Backend (Advanced Users for experimental use)
```bash
# Install Ollama (see ollama.ai)
# Pull a translation model
ollama pull gemma3:latest

# Configure for Ollama backend in config.yaml
translation:
  backend: "ollama"
```

## 📖 Usage Examples

### Basic Translation
```bash
# Simple translation (EN → HU)
python main.py "episode.srt"

# Specify output file
python main.py "episode.srt" --output "episode.hu.srt"

# Verbose output
python main.py "episode.srt" --verbose
```

### Advanced MarianMT Features
```bash
# Smart multiline with cross-entry detection (recommended)
python main.py "episode.srt" --backend marian --multiline-strategy smart --cross-entry-detection

# Disable cross-entry detection if needed  
python main.py "episode.srt" --backend marian --no-cross-entry-detection

# Different translation modes
python main.py "episode.srt" --backend marian --mode line-by-line  # Safest, resumable
python main.py "episode.srt" --backend marian --mode batch         # Faster processing  
python main.py "episode.srt" --backend marian --mode whole-file    # Fastest for small files
```

### Batch Processing
```bash
# Process all SRT files in a directory
python main.py "season1/*.srt" --backend marian --verbose

# Process with custom output pattern
python main.py "season1/*.srt" --backend marian --output "translated/{name}.hu.srt"
```

## 🏗️ Translation Backends

### 🔥 MarianMT Backend (Recommended & Production-Ready)
- **Best Available Solution:** MarianMT provides the most reliable translation quality among tested backends, achieving 80-90% satisfactory results for subtitle translation needs.
- **Known Limitations:** May occasionally struggle with specialized slang/argot, inconsistent formal/informal speech patterns, and rare instances of unclear output.
- **Best for:** Production use, fast processing, reliable baseline quality
- **Pros:** Ultra-fast (40x speedup), cross-entry detection, offline, consistent results
- **Cons:** Limited to translation only (no multi-model pipeline), occasional quality variations
- **Languages:** EN↔HU (Helsinki-NLP), EN↔DE/FR/ES (Helsinki-NLP)
- **Model:** Helsinki-NLP/opus-mt-en-hu (484MB, auto-downloaded)

### 🧪 Ollama Backend (Experimental & Not Recommended)
- **Warning:** Despite extensive testing and prompt engineering, Ollama models (both translation-only and multi-model pipeline) did NOT produce satisfactory translations. Quality was consistently poor and not suitable for production use.
- **Best for:** Experimental research, custom AI model exploration
- **Cons:** Much slower, requires Ollama installation, experimental status, poor translation quality in all tested modes
- **Features:** Multi-model architecture 4-phase pipeline: context → translation → validation → dialogue (but results not satisfactory)

## 🎛️ Configuration

Configuration is handled via `config.yaml` with CLI overrides:

```yaml
# MarianMT Configuration (Recommended)
translation:
  backend: "marian"
  source_language: "en"
  target_language: "hu"

marian:
  multiline_strategy: "smart"      # Intelligent detection
  cross_entry_detection: true     # Enable cross-entry sentences
  max_new_tokens: 128
  device: "auto"                   # "auto", "cuda", "cpu"

processing:
  translation_mode: "line-by-line"
  resume_enabled: true
  verbose: true
```

## 📚 Advanced Features

### Cross-Entry Sentence Detection (MarianMT)
Automatically detects sentences spanning multiple subtitle timestamps:

```
Input:  Entry 1: "This is now"
        Entry 2: "an NYPD homicide investigation,"  
        Entry 3: "so if we collar Hughes, we'll let you know."

Result: Translates as unified sentence while preserving original timing
        Entry 1: "Ez"
        Entry 2: "most egy rendőrségi gyilkossági"
        Entry 3: "nyomozás, szóval ha elkapjuk Hughest, szólunk."
```

### Multi-Model Pipeline (Ollama)
Advanced 4-phase translation workflow:
1. **Context Analysis** - Story understanding and character profiling
2. **Translation** - Context-aware primary translation
3. **Technical Validation** - Grammar and quality scoring  
4. **Dialogue Specialist** - Character voice consistency

## 🔍 Performance Comparison

| Backend    | Speed per Entry | Features                                 | Quality         | Recommended Use         |
|------------|----------------|------------------------------------------|-----------------|------------------------|
| **MarianMT** | **0.14s** ⚡⚡⚡⚡⚡ | Cross-entry detection, Smart multiline   | **Good (80-90%)** ⭐⭐⭐⭐ | **Production**         |
| Ollama     | 5-6s ⚡         | Multi-model pipeline, Context analysis   | **Unsatisfactory** | Experimental/Not Recommended |

## 📋 Supported Language Pairs

### MarianMT (Helsinki-NLP Models)
- **Primary**: English ↔ Hungarian ✅ (Fully tested)

### Ollama
- Any language pair supported by the selected model

## 📖 Documentation

- **[MarianMT User Guide](docs/MARIANMT_USER_GUIDE.md)** - Complete MarianMT setup and usage ⭐ **Recommended**
- **[Multi-Model Architecture Guide](docs/multi-model-guide.md)** - Advanced Ollama pipeline documentation
- **[Implementation Tasks](docs/implementation-tasks.md)** - Development progress tracking
- **[Traditional Translation Guide](docs/traditional-translation-guide.md)** - Basic translation modes

## 🧪 Testing

```bash
# Run cross-entry detection tests
python tests/test_cross_entry_detection.py

# Test translation with sample file
python main.py "test_sample.srt" --backend marian --verbose
```

## ⚠️ Important Notes

- **MarianMT provides the best available translation quality** achieving 80-90% satisfactory results for subtitle needs, though it may occasionally struggle with specialized argot, formal/informal consistency, and rare unclear outputs.
- Ollama backend (translation-only and multi-model) did NOT yield acceptable results, even after extensive prompt engineering and testing.
- Cross-entry sentence detection is a unique MarianMT feature providing superior translation quality.
- All processing is done locally - no data sent to external services
- **This tool prioritizes accessibility for hearing-impaired users** who depend on subtitles, not convenience features for casual users.

## 📜 Model License & Attribution

This project uses the Helsinki-NLP/opus-mt-en-hu model for English↔Hungarian translation via MarianMT.

- **Model:** [Helsinki-NLP/opus-mt-en-hu on Hugging Face](https://huggingface.co/Helsinki-NLP/opus-mt-en-hu)
- **License:** MIT License (see [model card](https://huggingface.co/Helsinki-NLP/opus-mt-en-hu))
- **Attribution:** © Tiedemann, Jörg, OPUS-MT, University of Helsinki

Please review the model's license and terms before using in commercial or public projects.

## 🤝 Contributing

We welcome contributions! Please see our development documentation for implementation guidelines.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**🎬 Enjoy your translated subtitles with MarianMT's lightning-fast processing and intelligent cross-entry detection!**
