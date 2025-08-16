# Subtitle Assistant

A Python-based AI-powered subtitle translation tool designed to help hearing-impaired users enjoy movies and TV shows with accurate, context-aware translations.

## 🎯 Project Mission

This project aims to bridge communication gaps for hearing-impaired users by providing high-quality subtitle translations and, in the future, comprehensive accessibility features for multimedia content.

## 🚀 Features

### ✅ **Implemented (Story 01)**
- **SRT Parser** - Robust parsing with timing preservation
- **AI Translation** - Context-aware translation using Ollama
- **YAML Configuration** - Flexible configuration system
- **CLI Interface** - Complete command-line interface
- **Multiple Models** - Support for various Ollama models
- **Formality Control** - Auto-detect, formal, or informal translation styles
- **Error Handling** - Retry logic and fallback models
- **Real-time Progress** - Translation progress indicators

### 🚧 **Planned Features**
- **Enhanced Translation Quality** - Advanced context handling and consistency
- **Batch Processing** - Automated directory processing
- **Multi-Language Support** - Support for multiple language pairs
- **GUI Application** - User-friendly drag-and-drop interface
- **Accessibility Features** - Sound effects, music descriptions, speaker identification
- **Audio Processing** - Auto-subtitle generation from video/audio files

## 🛠️ Technology Stack

- **Python 3.8+** - Core language
- **Ollama** - Local AI translation engine
- **PyYAML** - Configuration management
- **Requests** - HTTP client for Ollama API

## 📦 Installation

### Prerequisites
1. **Python 3.8+** installed
2. **Ollama** running locally with a translation model

### Setup
```bash
# Clone the repository
git clone https://github.com/VargaJoe/subtitle-assistant.git
cd subtitle-assistant

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Install Ollama model (recommended for Hungarian)
ollama pull jobautomation/OpenEuroLLM-Hungarian:latest
```

## 🚀 Usage

### Quick Start Examples

```bash
# Translate a single SRT file
python main.py "subtitles\show_s01e01.srt"

# Translate with specific output location
python main.py "subtitles\episode.srt" -o "output\episode_hungarian.srt"

# Use pattern matching for files
python main.py "subtitles\show*s01e01*.srt"
```

### Translation Modes

#### 1. **Multi-Model Mode** (Recommended - Best Quality)
```bash
# 4-stage AI pipeline for highest quality
python main.py "subtitles\episode.srt" --mode multi-model

# Run only translation step (5x faster)
python main.py "subtitles\episode.srt" --mode multi-model --only-translation

# Select specific steps
python main.py input.srt --mode multi-model --steps context translation validation
```

#### 2. **Line-by-Line Mode** (Default - Reliable)
```bash
# Process entry by entry with resume capability
python main.py "subtitles\episode.srt" --mode line-by-line

# Resume from interruption
python main.py "subtitles\episode.srt" --resume
```

#### 3. **Batch Mode** (Fast - 35% Performance Boost)
```bash
# Process multiple entries together
python main.py "subtitles\episode.srt" --mode batch --batch-size 10

# With overlap for better context
python main.py input.srt --mode batch --batch-size 5 --overlap-size 2
```

#### 4. **Whole-File Mode** (Experimental)
```bash
# Process entire file at once (for small files)
python main.py test_sample.srt --mode whole-file
```

### Real-World Examples

#### Single Episode Translation
```bash
# Translate a TV show episode with highest quality
python main.py "subtitles\show_s01e01.srt" --mode multi-model --verbose

# Output: show_s01e01.hu.srt (same directory)
```

#### Batch Processing Multiple Episodes
```bash
# Translate all episodes in a season
python main.py "subtitles\season01\*.srt" --batch --mode multi-model

# Process first 5 episodes only
python main.py "subtitles\season01\*s01e0[1-5]*.srt" --batch --mode multi-model
```

#### Advanced Options
```bash
# High-quality translation with specific model
python main.py "subtitles\episode.srt" \
  --mode multi-model \
  --model "gemma3:latest" \
  --formality auto \
  --verbose

# Fast translation for preview
python main.py "subtitles\episode.srt" \
  --mode multi-model \
  --only-translation \
  --batch-size 20
```

### Resume and Progress Management

```bash
# Safe interruption with Ctrl+C - automatically resumes next time
python main.py "subtitles\episode.srt" --mode multi-model

# Force restart (ignore existing progress)
python main.py "subtitles\episode.srt" --restart

# Explicitly resume from last position
python main.py "subtitles\episode.srt" --resume
```

### Configuration

Create or edit `config.yaml` for persistent settings:

```yaml
translation:
  source_language: en
  target_language: hu
  model: "jobautomation/OpenEuroLLM-Hungarian:latest"
  context_window: 3
  tone:
    formality: auto  # formal, informal, auto
    style: natural   # natural, literal, creative

ollama:
  host: localhost
  port: 11434
  timeout: 300

output:
  suffix: "{target_lang}"
  encoding: utf-8
```

### Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--mode` | Translation mode | `--mode multi-model` |
| `--only-translation` | Fast mode (translation step only) | `--only-translation` |
| `--steps` | Select specific pipeline steps | `--steps context translation` |
| `--batch-size` | Entries per batch | `--batch-size 10` |
| `--overlap-size` | Context overlap between batches | `--overlap-size 2` |
| `--resume` | Resume from interruption | `--resume` |
| `--restart` | Force restart ignoring progress | `--restart` |
| `--config`, `-c` | Configuration file | `--config my-config.yaml` |
| `--model` | Ollama model name | `--model gemma3:latest` |
| `--source` | Source language | `--source en` |
| `--target` | Target language | `--target hu` |
| `--formality` | Translation style | `--formality auto` |
| `--verbose`, `-v` | Detailed output | `--verbose` |
| `--validate` | Validate setup only | `--validate` |

### Translation Modes Comparison

| Mode | Speed | Quality | Resume | Best For |
|------|-------|---------|--------|----------|
| `multi-model` | Slow | ⭐⭐⭐⭐⭐ | ✅ | Production, highest quality |
| `multi-model --only-translation` | Fast | ⭐⭐⭐⭐ | ✅ | Good quality, faster processing |
| `line-by-line` | Medium | ⭐⭐⭐ | ✅ | Reliable, interruptible |
| `batch` | Fast | ⭐⭐⭐ | ✅ | Good balance of speed/quality |
| `whole-file` | Very Fast | ⭐⭐ | ❌ | Small files, quick preview |

## 📁 Output Structure

### Single File Translation
```
# Input
subtitles\show_s01e01.eng.srt

# Output (same directory with .hu suffix)
subtitles\show_s01e01.eng.hu.srt
```

### Custom Output Location
```bash
python main.py "subtitles\episode.srt" -o "output\episode_hungarian.srt"
```

### Batch Translation
```
subtitles\season01\
  ├── show_s01e01.eng.srt
  ├── show_s01e02.eng.srt
  └── show_s01e03.eng.srt

# After translation
subtitles\season01\
  ├── show_s01e01.eng.srt
  ├── show_s01e01.eng.hu.srt    ← New
  ├── show_s01e02.eng.srt
  ├── show_s01e02.eng.hu.srt    ← New
  ├── show_s01e03.eng.srt
  └── show_s01e03.eng.hu.srt    ← New
```

### Multi-Model Output (Advanced)
```
# Besides the .hu.srt file, multi-model mode creates detailed JSON results:
show_s01e01.eng_results.json    ← AI pipeline details
```

## 🏗️ Project Structure

```
subtitle-assistant/
├── main.py                    # CLI entry point
├── config.yaml               # Configuration file
├── requirements.txt           # Python dependencies
├── subtitle_translator/       # Core modules
│   ├── config.py             # Configuration management
│   ├── srt_parser.py         # SRT file handling
│   ├── ollama_client.py      # AI translation client
│   └── translator.py         # Main translation logic
├── docs/                     # Documentation
│   ├── stories/             # User stories
│   └── implementation-tasks.md
├── subtitles/               # Sample subtitle files
└── output/                  # Translated files (created)
```
- ⏳ Core translation functionality

See [Implementation Tasks](docs/implementation-tasks.md) for detailed progress tracking.

## 🧪 Testing

### Validate Setup
```bash
# Check if everything is configured correctly
python main.py --validate
```

### Test with Sample Files
```bash
# Quick test with small sample
python main.py test_sample.srt --verbose

# Test multi-model pipeline
python main.py test_sample.srt --mode multi-model --verbose

# Test with a real episode (first few entries)
python main.py "subtitles\episode.srt" --mode multi-model --batch-size 5
```

### Performance Testing
```bash
# Compare translation modes
python main.py test_sample.srt --mode line-by-line --verbose
python main.py test_sample.srt --mode batch --verbose  
python main.py test_sample.srt --mode multi-model --only-translation --verbose
```

## ⚡ Performance

- **Multi-Model Mode**: ~45-60 seconds per entry (4-stage AI pipeline)
- **Multi-Model Translation-Only**: ~12-15 seconds per entry (5x faster)
- **Batch Mode**: ~10-13 seconds per entry (35% faster than line-by-line)
- **Line-by-Line**: ~13-18 seconds per entry (reliable baseline)
- **Context Awareness**: Uses surrounding subtitles for better translation
- **Memory Efficient**: Processes entries sequentially with resume capability
- **Error Recovery**: Automatic retry and fallback to alternative models

### Real-World Performance Examples
```bash
# Typical TV episode (~400 entries)
Multi-Model (full):     ~6.5 hours  (highest quality)
Multi-Model (fast):     ~1.5 hours  (excellent quality)
Batch Mode:             ~1.2 hours  (good quality)
Line-by-Line:           ~1.8 hours  (reliable)
```

## 🎨 Translation Quality

### Hungarian-Specific Features
- **Formality Detection**: Automatically detects formal vs informal context
- **Natural Expressions**: Prioritizes natural Hungarian over literal translation
- **Proper Names**: Preserves English character names
- **Contractions**: Handles English contractions naturally

### Example Translations
```
English: "Hello, how are you today?"
Hungarian (informal): "Szia, hogy vagy ma?"
Hungarian (formal): "Jó napot kívánok, hogy érzi magát?"

English: "Excuse me, buddy. You speak English?"
Hungarian: "Bocs, fiú. Beszél angolul?"
```

## 🔧 Troubleshooting

### Common Issues

**Ollama Connection Failed**
```bash
# Start Ollama service
ollama serve

# Check if model is available
ollama list
```

**Translation Timeouts**
```bash
# Increase timeout for large models
python main.py input.srt --timeout 600
```

**Memory Issues with Large Files**
- Process files in smaller batches
- Reduce context window in config
- Use faster models for initial processing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai/) - Local AI model execution
- [OpenEuroLLM](https://huggingface.co/jobautomation/OpenEuroLLM-Hungarian) - Hungarian language model
- Hearing-impaired community feedback and testing

## 📬 Contact

- **Project Repository**: [GitHub](https://github.com/VargaJoe/subtitle-assistant)
- **Issues & Bug Reports**: [GitHub Issues](https://github.com/VargaJoe/subtitle-assistant/issues)

---

*Built with ❤️ for the hearing-impaired community*
