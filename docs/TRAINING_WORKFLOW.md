# MarianMT Training Workflow

This document illustrates the complete training workflow for custom subtitle translation models.

## Training Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      TRAINING WORKFLOW                           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐
│  USER INTERFACE │
└────────┬────────┘
         │
    ┌────┴────────────────┐
    │                     │
┌───▼──────┐      ┌───────▼────┐
│   GUI    │      │    CLI     │
│  (PS1)   │      │  (Python)  │
└───┬──────┘      └───────┬────┘
    │                     │
    └──────────┬──────────┘
               │
┌──────────────▼──────────────┐
│   TRAINING DATA SOURCES     │
├─────────────────────────────┤
│  • SRT File Pairs           │
│    ├─ movie1.en.srt ←→ .hu  │
│    ├─ movie2.en.srt ←→ .hu  │
│    └─ movie3.en.srt ←→ .hu  │
│                             │
│  • JSON Data                │
│    └─ training_data.json    │
│       [{"source": "...",    │
│         "target": "...",    │
│         "genre": "..."}]    │
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│   DATA PREPARATION          │
├─────────────────────────────┤
│  • Parse SRT/JSON files     │
│  • Create TrainingDataPair  │
│  • Split train/validation   │
│  • Tokenize sequences       │
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│   BASE MODEL LOADING        │
├─────────────────────────────┤
│  • Load MarianMT model      │
│    (Helsinki-NLP/opus-mt-)  │
│  • Load tokenizer           │
│  • Move to GPU/CPU          │
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│   TRAINING LOOP             │
├─────────────────────────────┤
│  For each epoch:            │
│    For each batch:          │
│      • Forward pass         │
│      • Calculate loss       │
│      • Backward pass        │
│      • Update weights       │
│    Validate on val set      │
│    Save checkpoint          │
│    Log metrics              │
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│   MODEL SAVING              │
├─────────────────────────────┤
│  • Save model weights       │
│  • Save tokenizer           │
│  • Save config              │
│  • Save metadata JSON       │
│    ├─ source/target lang    │
│    ├─ genre                 │
│    ├─ training samples      │
│    └─ hyperparameters       │
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│   OUTPUT                    │
├─────────────────────────────┤
│  ./trained_models/          │
│    └─ model-name/           │
│       ├─ config.json        │
│       ├─ pytorch_model.bin  │
│       ├─ tokenizer files    │
│       ├─ metadata.json      │
│       └─ logs/              │
└─────────────────────────────┘
```

## Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Source    │────▶│  Tokenizer  │────▶│   Model     │
│   Text      │     │             │     │   Input     │
│  "Hello"    │     │  [101,...]  │     │  Tensors    │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
┌─────────────┐     ┌─────────────┐            │
│   Target    │────▶│  Tokenizer  │            │
│   Text      │     │             │            │
│   "Szia"    │     │  [102,...]  │            │
└─────────────┘     └──────┬──────┘            │
                           │                   │
                           │  ┌────────────────▼────┐
                           │  │   Training Step     │
                           │  ├─────────────────────┤
                           └─▶│  • Forward pass     │
                              │  • Calculate loss   │
                              │  • Backpropagation  │
                              │  • Update weights   │
                              └─────────────────────┘
```

## Model Usage Flow

```
┌─────────────────────────────────────────────────────────┐
│                    USING TRAINED MODEL                   │
└─────────────────────────────────────────────────────────┘

1. Configure (config.yaml)
   ┌────────────────────────────────┐
   │ marian:                        │
   │   model: "./trained_models/    │
   │           my-drama-model"      │
   └────────────────────────────────┘

2. Translate subtitle
   ┌────────────────────────────────┐
   │ python main.py movie.srt       │
   │   --backend marian             │
   └────────────────────────────────┘

3. Translation process
   ┌─────────────┐
   │ Load Model  │
   │   (custom)  │
   └──────┬──────┘
          │
   ┌──────▼──────┐
   │  Translate  │
   │  Subtitles  │
   └──────┬──────┘
          │
   ┌──────▼──────┐
   │   Output    │
   │  movie.hu.  │
   │    srt      │
   └─────────────┘
```

## Genre-Specific Training

```
┌──────────────────────────────────────────────────────────┐
│            TRAINING MULTIPLE GENRE MODELS                 │
└──────────────────────────────────────────────────────────┘

        Base Model (Helsinki-NLP/opus-mt-en-hu)
                        │
        ┌───────────────┼───────────────┐
        │               │               │
    ┌───▼───┐       ┌───▼───┐      ┌───▼───┐
    │ Drama │       │Comedy │      │Action │
    │ Data  │       │ Data  │      │ Data  │
    └───┬───┘       └───┬───┘      └───┬───┘
        │               │               │
    ┌───▼───┐       ┌───▼───┐      ┌───▼───┐
    │ Train │       │ Train │      │ Train │
    │ Model │       │ Model │      │ Model │
    └───┬───┘       └───┬───┘      └───┬───┘
        │               │               │
    ┌───▼──────┐    ┌───▼──────┐   ┌───▼──────┐
    │  Drama   │    │  Comedy  │   │  Action  │
    │  Model   │    │  Model   │   │  Model   │
    └──────────┘    └──────────┘   └──────────┘
         │               │               │
         └───────────────┴───────────────┘
                         │
         Use appropriate model for content type
```

## Training Parameter Impact

```
┌──────────────────────────────────────────────────────────┐
│               HYPERPARAMETER EFFECTS                      │
└──────────────────────────────────────────────────────────┘

Epochs
  Low (1-2)  ──▶ Fast training, may underfit
  Medium (3-5)  ──▶ Good balance (recommended)
  High (>5)  ──▶ Better results, risk overfitting

Batch Size
  Small (2-4)  ──▶ Less memory, slower, noisy updates
  Medium (8)  ──▶ Good balance (recommended)
  Large (16+)  ──▶ More memory, faster, stable updates

Learning Rate
  Low (1e-6)  ──▶ Slow convergence
  Medium (5e-5)  ──▶ Good balance (recommended)
  High (1e-4)  ──▶ Fast learning, may be unstable

Training Data Size
  Small (<1K)  ──▶ Quick test, poor quality
  Medium (1-5K)  ──▶ Good for testing
  Large (>5K)  ──▶ Production quality
```

## Quality Progression

```
Training Progress Over Time

Quality
   ▲
   │                            ┌─────────┐
   │                        ┌───┤ Plateau │
   │                    ┌───┘   └─────────┘
   │                ┌───┘
   │            ┌───┘
   │        ┌───┘  Learning Phase
   │    ┌───┘
   │────┘
   └────────────────────────────────────────▶ Epochs
   0    1    2    3    4    5    6    7    8

Best Practice: Stop at plateau (typically 3-5 epochs)
```

## Integration with Main App

```
┌─────────────────────────────────────────────────────────┐
│              SUBTITLE ASSISTANT ECOSYSTEM                │
└─────────────────────────────────────────────────────────┘

┌─────────────────┐
│  Train Models   │
│  train_marian   │
└────────┬────────┘
         │
         │ creates
         ▼
┌─────────────────┐
│ Custom Models   │
│ ./trained_models│
└────────┬────────┘
         │
         │ used by
         ▼
┌─────────────────┐
│  Main App       │
│  main.py        │
└────────┬────────┘
         │
         │ produces
         ▼
┌─────────────────┐
│  Translations   │
│  *.hu.srt       │
└─────────────────┘
```

## Summary

This workflow ensures:
- **Flexibility**: Multiple data sources and interfaces
- **Quality**: Proper training with validation
- **Usability**: Easy to use for all skill levels
- **Integration**: Seamless integration with main app
- **Reproducibility**: Metadata tracking and checkpoints

For detailed instructions, see:
- [Quick Start Guide](TRAINING_QUICK_START.md)
- [Full Training Guide](MARIANMT_TRAINING_GUIDE.md)
