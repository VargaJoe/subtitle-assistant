# MarianMT Training - Quick Start Guide

Get started training your own subtitle translation models in minutes!

## Prerequisites

Before training, ensure you have:
```bash
pip install torch transformers sentencepiece
```

## Option 1: Use the GUI (Easiest!)

### Step 1: Launch the GUI
```powershell
.\train_marian_gui.ps1
```

### Step 2: Configure Training
1. Select **"Train Model"** tab
2. Choose data source: **SRT File Pairs** or **JSON File**
3. Set language pair (e.g., en → hu)
4. Select genre (drama, comedy, action, etc.)
5. Add your training files
6. Click **"Start Training"**

### Step 3: Monitor Progress
Watch the training log for real-time updates!

## Option 2: Use the CLI

### Quick Training Command
```bash
python train_marian.py train-srt \
  --source en \
  --target hu \
  --genre drama \
  --source-files movie1.en.srt movie2.en.srt \
  --target-files movie1.hu.srt movie2.hu.srt
```

### Using JSON Data
```bash
python train_marian.py train-json \
  --source en \
  --target hu \
  --json-file examples/training_data_example.json
```

## Training Data

### Minimum Requirements
- **Small test**: 100+ subtitle pairs
- **Production use**: 3,000+ pairs (recommended)
- **High quality**: 10,000+ pairs

### Where to Get Training Data?

1. **Your own subtitles**: If you have SRT files in both languages
2. **Public databases**: OpenSubtitles, etc. (check licenses!)
3. **Create your own**: Use the example JSON format

### Data Format

**SRT Pairs:**
```
movie1.en.srt  ←→  movie1.hu.srt
movie2.en.srt  ←→  movie2.hu.srt
```

**JSON Format:**
```json
[
  {
    "source": "English text",
    "target": "Hungarian translation",
    "genre": "drama"
  }
]
```

## After Training

### List Your Models
```bash
python train_marian.py list
```

### Get Model Info
```bash
python train_marian.py info your-model-name
```

### Use Your Model

Update `config.yaml`:
```yaml
marian:
  model: "./trained_models/your-model-name"
```

Then translate:
```bash
python main.py movie.srt --backend marian
```

## Training Tips

### For Best Results:
- ✅ Use 3-5 epochs (default is good)
- ✅ Keep batch size at 8 (or reduce if out of memory)
- ✅ Use GPU if available (40x faster!)
- ✅ Include variety in your training data
- ✅ Match genre to your use case

### Avoid:
- ❌ Too few training samples (< 1,000)
- ❌ Mixing different genres without labels
- ❌ Poor quality translations as training data
- ❌ Too many epochs (can overfit)

## Common Issues

### "Out of Memory"
**Solution**: Reduce batch size
```bash
python train_marian.py train-srt ... --batch-size 4
```

### "Training is slow"
**Solution**: 
- Use GPU instead of CPU
- Reduce training data size for testing

### "Model not improving"
**Solution**:
- Increase training data
- Try different learning rate
- Increase epochs to 5

## Example Workflow

```bash
# 1. Organize your data
mkdir -p training_data/drama
cp *.en.srt *.hu.srt training_data/drama/

# 2. Train the model
python train_marian.py train-srt \
  --source en --target hu \
  --genre drama \
  --source-files training_data/drama/*.en.srt \
  --target-files training_data/drama/*.hu.srt \
  --model-name my-drama-model

# 3. Test your model
# Update config.yaml: marian.model = "./trained_models/my-drama-model"
python main.py test-movie.srt --backend marian

# 4. Compare with base model to see improvement!
```

## Next Steps

- 📖 Read the [Full Training Guide](MARIANMT_TRAINING_GUIDE.md) for advanced features
- 🎯 Train models for different genres
- 🔧 Experiment with hyperparameters
- 📊 Monitor training metrics

## Need Help?

- Check the [Full Guide](MARIANMT_TRAINING_GUIDE.md) for troubleshooting
- Review the [examples](../examples/) folder
- Open an issue on GitHub

Happy training! 🚀
