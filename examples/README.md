# Training Data Examples

This directory contains example files for training custom MarianMT models.

## Files

### training_data_example.json

Sample JSON file showing the format for training data. Contains 20 famous movie quotes translated from English to Hungarian, with genre labels.

**Format:**
```json
[
  {
    "source": "English text",
    "target": "Hungarian translation",
    "genre": "genre_label"
  }
]
```

**Usage:**
```bash
python train_marian.py train-json \
  --source en \
  --target hu \
  --json-file examples/training_data_example.json
```

## Creating Your Own Training Data

### From SRT Files

The best approach is to use aligned subtitle files:

1. **Gather SRT pairs**: Find movies/shows with subtitles in both languages
2. **Verify alignment**: Ensure subtitle entries match (same count, same timing)
3. **Organize files**: Keep source and target files paired

Example structure:
```
my_training_data/
├── movie1.en.srt
├── movie1.hu.srt
├── movie2.en.srt
├── movie2.hu.srt
└── ...
```

Train with:
```bash
python train_marian.py train-srt \
  --source en \
  --target hu \
  --genre drama \
  --source-files my_training_data/*.en.srt \
  --target-files my_training_data/*.hu.srt
```

### From JSON Data

For custom datasets or when SRT files aren't available:

1. **Create JSON file**: Follow the format in `training_data_example.json`
2. **Include genres**: Label each pair with appropriate genre
3. **Quality matters**: Use high-quality translations

**Minimum dataset sizes:**
- Testing/experimentation: 100+ pairs
- Small model: 1,000+ pairs
- Production model: 3,000+ pairs
- High-quality model: 10,000+ pairs

### Data Quality Tips

✅ **DO:**
- Use professional translations
- Include variety within genre
- Maintain consistent style
- Keep subtitle-style text (short, natural)
- Include multi-line dialogue examples

❌ **DON'T:**
- Mix formal and informal without clear separation
- Include machine-translated data
- Use book/article translations for subtitle training
- Include spelling errors or typos

## Genre Labels

Supported genres:
- `general` - General purpose / mixed content
- `drama` - Dramatic content
- `comedy` - Comedy and humor
- `action` - Action movies
- `scifi` - Science fiction
- `documentary` - Documentaries
- `romance` - Romance
- `thriller` - Thrillers
- `horror` - Horror

Choose the genre that best matches your content for optimal results.
