# MarianMT Training Feature - Implementation Summary

## Overview

This document summarizes the implementation of the custom MarianMT model training feature for the Subtitle Assistant project.

## Problem Statement

Users requested the ability to train custom MarianMT-based translation models specifically optimized for subtitle-style text, with support for:
- Different genres (drama, comedy, action, etc.)
- Easy-to-understand and easy-to-use interface
- GUI option (PowerShell)
- Model management capabilities

## Solution

We implemented a comprehensive training system with multiple interfaces and extensive documentation.

## Components Implemented

### 1. Core Training Module (`subtitle_translator/marian_trainer.py`)

**Classes:**
- `TrainingDataPair`: Data structure for training pairs
- `SubtitleDataset`: PyTorch dataset for subtitle data
- `MarianTrainer`: Main training class with methods for:
  - Loading data from SRT file pairs
  - Loading data from JSON files
  - Training models with configurable parameters
  - Saving models with metadata
- `ModelManager`: Model management class for:
  - Listing trained models
  - Getting model information
  - Deleting models

**Key Features:**
- Fine-tuning from base MarianMT models
- Support for multiple data sources
- GPU/CPU support
- Training progress logging
- Validation split
- Checkpoint support
- Metadata tracking

### 2. Configuration (`subtitle_translator/config.py`)

Added `MarianTrainingSettings` dataclass with parameters:
- `base_model`: Model to fine-tune from
- `learning_rate`: Training learning rate
- `batch_size`: Batch size for training
- `num_epochs`: Number of training epochs
- `genre`: Genre label for the model
- Advanced settings (warmup, weight decay, etc.)

### 3. Command-Line Interface (`train_marian.py`)

**Commands:**
- `list`: List all trained models
- `info <model>`: Show detailed model information
- `delete <model>`: Delete a trained model
- `train-srt`: Train from SRT file pairs
- `train-json`: Train from JSON data

**Features:**
- Comprehensive argument parsing
- Progress logging
- Model metadata tracking
- Resume from checkpoint support
- Flexible parameter configuration

### 4. PowerShell GUI (`train_marian_gui.ps1`)

**Two-Tab Interface:**

**Tab 1 - Train Model:**
- Data source selection (SRT pairs or JSON)
- Language configuration
- Genre selection dropdown
- File selection (source/target SRT or JSON)
- Training parameter controls:
  - Epochs (numeric up/down)
  - Batch size (numeric up/down)
  - Learning rate (text input)
  - Custom model name (optional)
- Real-time training log
- Start/stop training controls

**Tab 2 - Manage Models:**
- List of trained models
- Refresh button
- Detailed model information display
- Delete model functionality

**Features:**
- User-friendly Windows Forms interface
- Asynchronous training execution
- Real-time log updates
- Error handling and validation
- Progress indicators

### 5. Documentation

**Files Created:**

1. **`docs/MARIANMT_TRAINING_GUIDE.md`** (10KB)
   - Complete training guide
   - Data preparation instructions
   - Parameter explanations
   - Best practices
   - Troubleshooting section
   - Advanced topics

2. **`docs/TRAINING_QUICK_START.md`** (4KB)
   - Quick start guide
   - Step-by-step instructions
   - Common use cases
   - Quick reference

3. **`examples/README.md`** (2KB)
   - Example data format
   - Data creation guidelines
   - Quality tips

### 6. Example Data

**`examples/training_data_example.json`:**
- 20 famous movie quotes
- English → Hungarian translations
- Multiple genres demonstrated
- Proper JSON format example

### 7. README Updates

Updated main README with:
- Training feature overview
- Quick start instructions
- Links to documentation
- GUI and CLI usage examples

## Usage Examples

### GUI Usage
```powershell
.\train_marian_gui.ps1
```

### CLI Usage

**Train from SRT:**
```bash
python train_marian.py train-srt \
  --source en --target hu \
  --genre drama \
  --source-files movie1.en.srt movie2.en.srt \
  --target-files movie1.hu.srt movie2.hu.srt
```

**Train from JSON:**
```bash
python train_marian.py train-json \
  --source en --target hu \
  --json-file training_data.json
```

**List models:**
```bash
python train_marian.py list
```

**Use trained model:**
```yaml
# config.yaml
marian:
  model: "./trained_models/marian-subtitle-en-hu-drama"
```

```bash
python main.py movie.srt --backend marian
```

## Technical Details

### Dependencies
- PyTorch: Deep learning framework
- Transformers: Hugging Face library for MarianMT
- SentencePiece: Tokenization library

### Training Process
1. Load base MarianMT model and tokenizer
2. Prepare dataset from SRT or JSON
3. Split into training and validation sets
4. Configure training arguments
5. Train with Hugging Face Trainer
6. Save model and metadata
7. Enable resume from checkpoints

### Model Output
Trained models are saved to `./trained_models/` with:
- Model weights and configuration
- Tokenizer files
- Training metadata (JSON)
- Training logs (TensorBoard compatible)

## Benefits

### For Users
- **Easy to use**: GUI requires no coding
- **Flexible**: CLI for automation and advanced users
- **Genre-specific**: Optimize for content type
- **Quality**: Better translations for specific domains
- **Offline**: All training happens locally

### For Developers
- **Modular**: Clean separation of concerns
- **Extensible**: Easy to add new features
- **Well-documented**: Comprehensive guides
- **Maintainable**: Clear code structure

## Testing

Created `test_training_feature.py` for basic validation:
- Config loading with training settings
- Training module structure
- CLI/GUI script presence
- Documentation existence
- Example files

Note: Full training tests require PyTorch installation.

## Future Enhancements

Potential improvements:
- [ ] Distributed training support
- [ ] Multi-GPU training
- [ ] Hyperparameter tuning automation
- [ ] Training metrics visualization in GUI
- [ ] Model comparison tools
- [ ] Export models to ONNX format
- [ ] Quantization for smaller models
- [ ] Pre-built genre-specific models

## Files Changed/Added

### New Files (9 total)
1. `subtitle_translator/marian_trainer.py` - Core training module
2. `train_marian.py` - CLI interface
3. `train_marian_gui.ps1` - PowerShell GUI
4. `docs/MARIANMT_TRAINING_GUIDE.md` - Full documentation
5. `docs/TRAINING_QUICK_START.md` - Quick start guide
6. `examples/training_data_example.json` - Example data
7. `examples/README.md` - Examples documentation
8. `test_training_feature.py` - Basic tests
9. `TRAINING_FEATURE_SUMMARY.md` - This file

### Modified Files (2 total)
1. `subtitle_translator/config.py` - Added MarianTrainingSettings
2. `README.md` - Added training feature section

## Conclusion

The training feature provides a complete solution for users to train custom MarianMT models optimized for subtitle translation. It combines ease of use (GUI), power (CLI), and comprehensive documentation to make model training accessible to all users.

The implementation follows the project's principles:
- **Accessibility**: Easy-to-use GUI for non-technical users
- **Flexibility**: CLI for advanced users and automation
- **Quality**: Comprehensive documentation and examples
- **Completeness**: Full feature set from data preparation to model usage
