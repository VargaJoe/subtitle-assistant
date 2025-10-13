# MarianMT Model Training Guide

This guide explains how to train custom MarianMT translation models optimized for subtitle-style text.

## Overview

The subtitle assistant now supports training custom MarianMT models that can be fine-tuned for:
- **Specific genres** (drama, comedy, action, sci-fi, etc.)
- **Subtitle-specific language** (short, natural, spoken dialogue)
- **Domain-specific terminology** (technical terms, slang, idioms)
- **Character voice consistency** (maintaining speaking patterns)

## Why Train Custom Models?

While pre-trained MarianMT models work well for general translation, custom training can improve:
- **Translation quality** for specific content types
- **Consistency** in character voices and terminology
- **Natural dialogue** that matches subtitle constraints
- **Genre-appropriate language** (formal vs. informal, technical vs. casual)

## Training Methods

### Method 1: PowerShell GUI (Easiest)

The PowerShell GUI provides a user-friendly interface for training models.

#### Launch the GUI
```powershell
.\train_marian_gui.ps1
```

#### Features
- **Train Model Tab**: Configure and start training
  - Choose between SRT file pairs or JSON data
  - Set language pair (source → target)
  - Select genre (drama, comedy, action, etc.)
  - Configure training parameters
  - Monitor training progress in real-time

- **Manage Models Tab**: View and manage trained models
  - List all trained models
  - View model details and metadata
  - Delete models you no longer need

### Method 2: Command Line (Advanced)

For automation or more control, use the CLI tool.

#### List Trained Models
```bash
python train_marian.py list
```

#### Get Model Information
```bash
python train_marian.py info marian-subtitle-en-hu-drama
```

#### Train from SRT File Pairs
```bash
python train_marian.py train-srt \
  --source en \
  --target hu \
  --genre drama \
  --source-files movie1.en.srt movie2.en.srt movie3.en.srt \
  --target-files movie1.hu.srt movie2.hu.srt movie3.hu.srt \
  --epochs 3 \
  --batch-size 8 \
  --learning-rate 0.00005
```

#### Train from JSON Data
```bash
python train_marian.py train-json \
  --source en \
  --target hu \
  --json-file training_data.json \
  --epochs 3
```

JSON format:
```json
[
  {
    "source": "Hello, how are you?",
    "target": "Szia, hogy vagy?",
    "genre": "general"
  },
  {
    "source": "I'll be back.",
    "target": "Visszajövök.",
    "genre": "action"
  }
]
```

#### Delete a Model
```bash
python train_marian.py delete marian-subtitle-en-hu-drama --yes
```

## Preparing Training Data

### SRT File Pairs

The best way to train is using aligned SRT files (source and target language subtitles for the same content).

**Requirements:**
- Source and target SRT files must have the **same number of entries**
- Entries should be **aligned** (same timestamps and corresponding content)
- Files should be provided in **matching pairs** (source1 → target1, source2 → target2, etc.)

**Example Structure:**
```
training_data/
├── movie1.en.srt    → movie1.hu.srt  (must have same entry count)
├── movie2.en.srt    → movie2.hu.srt  (must have same entry count)
├── tvshow.s01e01.en.srt → tvshow.s01e01.hu.srt
└── ...
```

**Common Issues:**

❌ **Entry Count Mismatch:**
```
Source file: movie.en.srt (950 entries)
Target file: movie.hu.srt (780 entries)
Result: Training fails with "Mismatch in entry count" error
```

✅ **Solution:** Ensure SRT files are properly aligned:
- Use subtitles from the same video source
- Verify both files have identical timestamps
- Check that no subtitle entries are missing or extra

❌ **Wrong File Order:**
```
--source-files movie1.en.srt movie2.en.srt
--target-files movie2.hu.srt movie1.hu.srt  ← Wrong order!
```

✅ **Solution:** Match source and target files by position:
```
--source-files movie1.en.srt movie2.en.srt
--target-files movie1.hu.srt movie2.hu.srt  ← Correct order
```

**Tips:**
- Use at least 3-5 movies/episodes (3,000-5,000+ subtitle pairs)
- More data = better results
- Include variety within the genre
- Ensure high-quality existing translations

### JSON Training Data

For more flexibility, use JSON format:

```json
[
  {
    "source": "English subtitle text",
    "target": "Hungarian subtitle text",
    "genre": "drama"
  },
  {
    "source": "Another line of dialogue",
    "target": "Another translated line",
    "genre": "drama"
  }
]
```

## Training Parameters

### Essential Parameters

- **Source Language** (`--source`): Source language code (e.g., `en`)
- **Target Language** (`--target`): Target language code (e.g., `hu`)
- **Genre** (`--genre`): Content genre for specialized training
  - `general`: General purpose
  - `drama`: Dramatic content
  - `comedy`: Comedy and humor
  - `action`: Action movies
  - `scifi`: Science fiction
  - `documentary`: Documentaries
  - `romance`: Romance
  - `thriller`: Thrillers
  - `horror`: Horror

### Training Hyperparameters

- **Epochs** (`--epochs`): Number of training passes (default: 3)
  - Fewer epochs: Faster training, less overfitting
  - More epochs: Better results, risk of overfitting
  - Recommended: 3-5 epochs

- **Batch Size** (`--batch-size`): Number of samples per batch (default: 8)
  - Smaller: Less memory, slower training
  - Larger: More memory, faster training
  - Adjust based on GPU memory

- **Learning Rate** (`--learning-rate`): Step size for optimization (default: 5e-5)
  - Too high: Unstable training
  - Too low: Slow convergence
  - Recommended: 3e-5 to 5e-5

### Advanced Parameters

Available via configuration file (`config.yaml`):

```yaml
marian_training:
  base_model: "Helsinki-NLP/opus-mt-en-hu"
  learning_rate: 0.00005
  batch_size: 8
  num_epochs: 3
  warmup_steps: 500
  weight_decay: 0.01
  max_grad_norm: 1.0
  
  max_source_length: 128
  max_target_length: 128
  validation_split: 0.1
  
  output_dir: "./trained_models"
  save_steps: 500
  eval_steps: 500
  logging_steps: 100
  
  genre: "general"
  
  use_8bit: false
  gradient_checkpointing: true
  fp16: true
```

## Using Trained Models

### Update Configuration

After training, update your `config.yaml`:

```yaml
marian:
  model: "./trained_models/marian-subtitle-en-hu-drama"
  # ... other settings
```

### Use with CLI

```bash
python main.py movie.srt --backend marian
```

The trained model will be used automatically.

### Switch Between Models

You can maintain multiple trained models for different genres:

```yaml
# config-drama.yaml
marian:
  model: "./trained_models/marian-subtitle-en-hu-drama"

# config-comedy.yaml  
marian:
  model: "./trained_models/marian-subtitle-en-hu-comedy"
```

Use different configs:
```bash
python main.py drama-movie.srt --config config-drama.yaml
python main.py comedy-show.srt --config config-comedy.yaml
```

## Training Tips

### Data Quality
- **Quality over quantity**: High-quality translations are crucial
- **Consistency**: Ensure consistent style across training data
- **Genre matching**: Train on content similar to what you'll translate
- **Balance**: Include variety within the genre

### Training Process
- **Start small**: Test with 1-2 epochs on small dataset first
- **Monitor loss**: Check training logs for decreasing loss
- **Validation**: Use validation split to detect overfitting
- **GPU recommended**: Training on CPU is very slow

### Hardware Requirements

**Minimum:**
- 8GB RAM
- CPU training (slow but works)
- 5-10GB disk space per model

**Recommended:**
- 16GB+ RAM
- NVIDIA GPU with 6GB+ VRAM
- CUDA support
- 10-20GB disk space per model

**Training Time Estimates:**
- CPU: 4-12 hours (depending on data size)
- GPU (RTX 3060): 1-3 hours
- GPU (RTX 4090): 30-60 minutes

## Troubleshooting

### GUI Issues

**❌ "Nothing happens when I click Start Training"**
- **Cause:** SRT files have mismatched entry counts
- **Solution:** Use the GUI's new validation - it will check files before training starts
- **Check:** Look for "Entry count mismatch" messages in the log

**❌ "Training button stays disabled"**
- **Cause:** Previous training session didn't complete properly
- **Solution:** Close and restart the GUI, or check Task Manager for stuck Python processes

**❌ "No progress shown during training"**
- **Cause:** GUI redirects output to log files for stability
- **Solution:** Monitor `training.log` file in real-time, or check Task Manager for Python CPU usage
- **Note:** Training can take 1-12 hours depending on hardware and data size

### SRT File Issues

**❌ "Mismatch in entry count" error**
- **Cause:** Source and target SRT files have different numbers of subtitle entries
- **Solution:** 
  - Ensure SRT files are from the same video
  - Check for missing or extra subtitle entries
  - Use subtitle editing software to align entries

**❌ "No training data prepared"**
- **Cause:** All SRT file pairs were rejected due to mismatches
- **Solution:** Verify all source/target file pairs have matching entry counts

### Training Issues

**❌ "Out of Memory" errors**
- **Cause:** Insufficient RAM/VRAM for training parameters
- **Solutions:**
  - Reduce batch size: `--batch-size 4`
  - Enable 8-bit training in config: `use_8bit: true`
  - Use CPU training (slower but uses less memory)

**❌ Poor translation quality**
- **Common causes:**
  - Insufficient training data (need 3,000+ pairs)
  - Too few epochs (try 3-5)
  - Mismatched genres
  - Poor quality source translations
- **Solutions:**
  - Add more training data
  - Increase epochs to 5
  - Train on genre-specific data
  - Verify source translations are high quality

**❌ Training too slow**
- **Solutions:**
  - Use GPU instead of CPU
  - Increase batch size (if memory allows)
  - Reduce validation frequency (`eval_steps`)
  - Use fewer epochs initially

**❌ Model not improving**
- **Check:**
  - Training loss should decrease over time
  - Validation loss should decrease (but not diverge too much from training loss)
- **Try:**
  - Different learning rates (3e-5, 5e-5, 7e-5)
  - More training data
  - Different batch sizes

## Example Workflow

### 1. Gather Training Data
```bash
# Organize your SRT pairs
mkdir -p training_data/drama
cp movie1.en.srt movie1.hu.srt training_data/drama/
cp movie2.en.srt movie2.hu.srt training_data/drama/
# ... add more
```

### 2. Train the Model
```bash
python train_marian.py train-srt \
  --source en \
  --target hu \
  --genre drama \
  --source-files training_data/drama/*.en.srt \
  --target-files training_data/drama/*.hu.srt \
  --epochs 3 \
  --model-name my-drama-model
```

### 3. Verify Training
```bash
python train_marian.py info my-drama-model
```

### 4. Test the Model
```bash
# Update config.yaml
# marian:
#   model: "./trained_models/my-drama-model"

python main.py test-movie.srt --backend marian
```

### 5. Compare Results
Compare translations with the base model to see improvements.

## Best Practices

1. **Start with base model**: Always fine-tune from a pre-trained model
2. **Genre-specific training**: Train separate models for different genres
3. **Regular evaluation**: Test on held-out data to check quality
4. **Version control**: Keep track of training data and parameters
5. **Backup models**: Save successful models before experimenting
6. **Document metadata**: Record what data was used for each model

## Advanced Topics

### Multi-Genre Models

Train on mixed genres for general-purpose models:
```bash
python train_marian.py train-srt \
  --source en \
  --target hu \
  --genre general \
  --source-files drama/*.en.srt comedy/*.en.srt action/*.en.srt \
  --target-files drama/*.hu.srt comedy/*.hu.srt action/*.hu.srt
```

### Continuous Training

Resume training from a checkpoint:
```bash
python train_marian.py train-srt \
  ... \
  --resume-from ./trained_models/my-model/checkpoint-1000
```

### Transfer Learning

Fine-tune a trained model on new data:
```bash
# First training
python train_marian.py train-srt --genre drama ...

# Then update config to use trained model as base
# config.yaml:
# marian_training:
#   base_model: "./trained_models/marian-subtitle-en-hu-drama"

# Train on new genre
python train_marian.py train-srt --genre comedy ...
```

## Support

For issues or questions:
1. Check this guide and troubleshooting section
2. Review training logs in `training.log`
3. Try with smaller dataset first
4. Open an issue on GitHub with details

## References

- [MarianMT Documentation](https://huggingface.co/docs/transformers/model_doc/marian)
- [Hugging Face Trainer](https://huggingface.co/docs/transformers/main_classes/trainer)
- [Fine-tuning Translation Models](https://huggingface.co/docs/transformers/tasks/translation)
