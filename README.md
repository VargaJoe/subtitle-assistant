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

### Basic Translation

```bash
# Translate single file
python main.py input.srt

# Specify output file
python main.py input.srt -o output.srt

# Use specific model and formality
python main.py input.srt --model "jobautomation/OpenEuroLLM-Hungarian:latest" --formality informal

# Increase timeout for large models
python main.py input.srt --timeout 300 --verbose
```

### Batch Processing

```bash
# Translate all SRT files in a directory
python main.py "subtitles/*.srt" --batch

# Process directory with output to specific folder
python main.py subtitles/ --batch -o output/
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
| `--config`, `-c` | Configuration file | `--config my-config.yaml` |
| `--model` | Ollama model name | `--model llama3.2` |
| `--source` | Source language | `--source en` |
| `--target` | Target language | `--target hu` |
| `--formality` | Translation style | `--formality informal` |
| `--timeout` | Request timeout (seconds) | `--timeout 300` |
| `--verbose`, `-v` | Detailed output | `--verbose` |
| `--batch` | Batch processing mode | `--batch` |
| `--validate` | Validate setup only | `--validate` |

## 📁 Output Structure

### Single File Translation
```
input.srt → input.hu.srt  (same directory)
```

### Batch Translation
```
subtitles/
  ├── episode1.srt
  ├── episode2.srt
  └── episode3.srt

output/
  ├── episode1.hu.srt
  ├── episode2.hu.srt
  └── episode3.hu.srt
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

# Test with real Magnum P.I. dialogue
python main.py magnum_sample.srt --model "jobautomation/OpenEuroLLM-Hungarian:latest" --formality auto
```

## ⚡ Performance

- **Translation Speed**: ~13-18 seconds per subtitle entry (depends on model)
- **Context Awareness**: Uses surrounding subtitles for better translation
- **Memory Efficient**: Processes entries sequentially
- **Error Recovery**: Automatic retry and fallback to alternative models

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
