# Multi-Model Architecture Guide

This guide provides comprehensive documentation for the 4-phase multi-model translation pipeline.

## 🎯 Overview

The multi-model architecture uses specialized AI models for different aspects of translation:

```
Phase 1: Context Analysis    → Story understanding, character identification
Phase 2: Translation         → Context-aware Hungarian translation  
Phase 3: Technical Validation → Grammar checking, quality scoring
Phase 4: Dialogue Refinement → Character voice consistency
```

## 🚀 Quick Start

### CLI Usage
```bash
# Full pipeline (all 4 phases)
python main.py episode.srt --mode multi-model

# Fast mode (translation only)
python main.py episode.srt --mode multi-model --only-translation

# Custom phases
python main.py episode.srt --mode multi-model --steps context translation validation
```

### Available Steps
| CLI Parameter | Phase | Purpose | Time Impact |
|---------------|-------|---------|-------------|
| `context` | Phase 1 | Story analysis, character profiles | +20-30 seconds |
| `translation` | Phase 2 | Primary Hungarian translation | Base time |
| `validation` | Phase 3 | Grammar and quality checking | +50% time |
| `dialogue` | Phase 4 | Character voice refinement | +30% time |

## ⚙️ Configuration

### Step Selection in config.yaml

```yaml
multi_model:
  pipeline:
    run_context_analysis: true     # Phase 1: Story understanding
    run_translation: true          # Phase 2: Primary translation  
    run_validation: true           # Phase 3: Quality validation
    run_dialogue_refinement: true  # Phase 4: Dialogue polishing
```

### Model Configuration

Each phase can use different models:

```yaml
multi_model:
  context_model:
    model: "llama3.2:latest"       # Smaller model for context
    temperature: 0.2               # Consistent analysis
    
  translation_model:
    model: "gemma3:latest"         # Balanced translation
    temperature: 0.3               # Natural translations
    
  technical_validator:
    model: "gemma3:12b"            # Larger model for quality
    temperature: 0.1               # Strict validation
    
  dialogue_specialist:
    model: "gemma3:latest"         # Character consistency
    temperature: 0.25              # Stable voice patterns
```

### Custom Prompts

Customize AI instructions for each phase:

```yaml
multi_model:
  translation_model:
    prompt_template: |
      Translate to casual Hungarian that sounds natural:
      
      "{entry_text}"
      
      Context: {story_summary}
      Characters: {characters}
      
      Make it sound like real Hungarian conversation!
```

## 📊 Performance Profiles

### Quality vs Speed Matrix

| Configuration | Time per Entry | Quality Score | Best For |
|---------------|----------------|---------------|----------|
| `--only-translation` | ~12 seconds | ⭐⭐⭐ | Quick preview |
| `--steps translation validation` | ~18 seconds | ⭐⭐⭐⭐ | Production balance |
| Full 4-phase pipeline | ~45-60 seconds | ⭐⭐⭐⭐⭐ | Maximum quality |

### Real-World Performance

```bash
# TV Episode (~400 entries)
--only-translation:     ~1.3 hours
--steps trans valid:    ~2.0 hours  
Full pipeline:          ~6.7 hours
```

## 🔧 Optimization Strategies

### Same Model Optimization
When all phases use the same model (e.g., `gemma3:latest`):

```yaml
# Enable batch processing for efficiency
multi_model:
  pipeline:
    batch_validation: true         # Validate multiple entries together
    skip_validation_for_high_confidence: true  # Skip validation for confident translations
```

### Different Models Strategy
When using specialized models:

```yaml
# Optimize for model switching
multi_model:
  pipeline:
    parallel_processing: false     # Sequential to avoid model conflicts
    fallback_to_single: true       # Fallback if model unavailable
```

## 🎛️ Advanced Configuration

### Context Analysis Settings

```yaml
context_model:
  analyze_full_story: true         # Analyze complete subtitle file
  character_profiling: true       # Extract character patterns
  formality_detection: true       # Detect formal/informal speech
  context_window: 15              # Number of entries to analyze
```

### Validation Thresholds

```yaml
technical_validator:
  quality_threshold: 0.7          # Minimum quality score (0.0-1.0)
  grammar_check: true             # Enable grammar validation
  naturalness_score: true         # Score translation naturalness
```

### Dialogue Refinement

```yaml
dialogue_specialist:
  voice_consistency: true         # Enforce character voice consistency
  emotional_tone: true            # Preserve emotional tone
  formality_adjustment: true      # Adjust formality per character
```

## 📁 Output Structure

Multi-model mode creates detailed result files:

```
output/
├── episode.hu.srt                    # Final translated subtitles
├── episode.hu.progress               # Resume information  
└── multi_model_results/
    └── episode_results.json          # Detailed pipeline results
```

### Result File Structure

```json
{
  "file_info": {
    "input_file": "episode.srt",
    "total_entries": 400,
    "processing_start": "2025-08-17 10:00:00"
  },
  "step1_context_analysis": {
    "context": {
      "characters": {"Thomas": {"formality": "informal"}},
      "story_summary": "Detective story with casual dialogue"
    }
  },
  "entries": {
    "entry_0001": {
      "original_text": "Hello there!",
      "step2_translation": {
        "text": "Szia!",
        "confidence": 0.9
      },
      "step3_validation": {
        "grammar": 0.95,
        "naturalness": 0.88,
        "suggestion": null
      },
      "step4_dialogue": {
        "text": "Szia!",
        "improved": false
      },
      "final_result": {
        "text": "Szia!",
        "confidence": 0.9
      }
    }
  }
}
```

## 🐛 Troubleshooting

### Common Issues

**Context Analysis Takes Too Long:**
```yaml
context_model:
  context_window: 5               # Reduce from default 15
  analyze_full_story: false       # Disable for speed
```

**Quality Too Strict:**
```yaml
technical_validator:
  quality_threshold: 0.5          # Lower from default 0.7
  skip_validation_for_high_confidence: true
```

**Model Loading Issues:**
```yaml
multi_model:
  pipeline:
    fallback_to_single: true       # Enable fallback
    parallel_processing: false     # Sequential processing
```

### Debug Mode

Enable verbose logging to diagnose issues:

```bash
python main.py episode.srt --mode multi-model --verbose --steps context
```

## 💡 Best Practices

1. **Start Small**: Test with `test_sample.srt` before processing large files
2. **Incremental Steps**: Test each phase individually first
3. **Model Selection**: Use consistent models across phases for efficiency
4. **Quality Tuning**: Adjust temperature and thresholds based on content type
5. **Performance Monitoring**: Check result files to validate quality improvements

## 📚 See Also

- [README.md](../README.md) - Basic usage and installation
- [Implementation Tasks](implementation-tasks.md) - Project roadmap
- [config.yaml](../config.yaml) - Configuration reference
