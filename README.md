# Subtitle Assistant

🎬 **AI-powered subtitle translation tool** primarily designed for **hearing-impaired users** and others who **need** subtitles to access multimedia content.

## 🎯 Project Mission

**Primary Goal**: This project serves people who **cannot** watch or understand movies and TV shows without subtitles - primarily the hearing-impaired community who depend on subtitles for accessibility.

**Secondary Goals**: Support those who don't understand the original language and language learners.

While mainstream perception often views subtitles as some kind of luxury or convenience tool, **my priority is accessibility for those who have no alternative**. To bridge communication gaps by providing high-quality subtitle translations that make entertainment truly accessible to everyone.

## ⚡ Recommended: MarianMT Backend

**MarianMT** is our **primary recommendation** for production subtitle translation, offering the best balance of speed, quality, and reliability.

### Key Features
- ⚡ **Ultra-Fast**: 40x faster than Ollama (0.14s vs 5-6s per entry)
- 🧠 **Intelligent Processing**: Cross-entry sentence detection spanning multiple timestamps
- 🎭 **Smart Detection**: Automatically distinguishes dialogue from cross-entry sentences
- ⏱️ **Timing Preserved**: Maintains original subtitle timing with proportional text distribution
- 🖥️ **Local Processing**: No internet required, works completely offline
- 💾 **Auto-Model Management**: Downloads and caches models automatically
- 🔄 **GPU Acceleration**: CUDA support with CPU fallback

### Quick Start
```bash
# Single file translation
python main.py "movie.srt" --backend marian

# Batch processing multiple files
python main.py "subtitles/*.srt" --backend marian --verbose

# Smart multiline with cross-entry detection
python main.py "movie.srt" --backend marian --multiline-strategy smart
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- For MarianMT: PyTorch and Transformers

### Setup
```bash
# Clone repository
git clone https://github.com/VargaJoe/subtitle-assistant.git
cd subtitle-assistant

# Install dependencies
pip install -r requirements.txt

# Test installation
python main.py --help
```

## 🏗️ Translation Backends

### MarianMT Backend (Recommended)
- **Best Available Solution:** Reliable translation quality (~80-90% satisfactory results).
- **Known Limitations:** May struggle with slang, formal/informal consistency, and rare unclear outputs.
- **Languages:** EN↔HU (Helsinki-NLP).
- **Model:** Helsinki-NLP/opus-mt-en-hu (484MB, auto-downloaded).

### Ollama Backend (Experimental)
- **Warning:** Extensive testing showed poor translation quality, not suitable for production.
- **Best for:** Experimental research, custom AI model exploration.
- **Cons:** Slower, requires installation, experimental status.

## 📚 Advanced Features

### Cross-Entry Sentence Detection
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
- Cross-entry sentence detection is a unique MarianMT feature providing superior translation quality.
- All processing is done locally - no data sent to external services.
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
