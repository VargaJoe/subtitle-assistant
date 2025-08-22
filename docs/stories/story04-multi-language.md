# Story 04 - Multi-Language Support

## Story Title
**Expand Translation Support Beyond English-to-Hungarian**

## User Story
As a subtitle translator working with international content, I want to translate subtitles between multiple language pairs (not just English-to-Hungarian), so that I can serve diverse audiences and expand the utility of the translation system.

## Acceptance Criteria

### Must Have
- [ ] Support multiple source languages (English, German, French, Spanish)
- [ ] Support multiple target languages (Hungarian, German, French, Spanish)
- [ ] Automatic source language detection
- [ ] Configurable language pair selection via CLI and config

### Should Have
- [ ] Language-specific AI model selection and optimization
- [ ] Cultural adaptation rules per language pair
- [ ] Formality pattern detection for each language
- [ ] Language-specific context window optimization

### Could Have
- [ ] Language quality scoring and validation
- [ ] Mixed-language subtitle handling
- [ ] Language-specific character encoding support
- [ ] Regional dialect and variant support

### Won't Have (This Release)
- [ ] Real-time language switching
- [ ] Automatic dialect detection
- [ ] Custom language model training

## Technical Requirements

### Configuration Changes
```yaml
translation:
  source_language: "auto"  # auto-detect or specify
  target_language: "hu"    # Hungarian default
  language_pairs:
    - source: "en"
      target: "hu" 
      model: "jobautomation/OpenEuroLLM-Hungarian:latest"
    - source: "de"
      target: "hu"
      model: "jobautomation/OpenEuroLLM-Hungarian:latest"
```

### CLI Enhancements
```bash
python main.py input.srt --source en --target hu
python main.py input.srt --source auto --target de
python main.py input.srt --detect-language  # auto-detect and suggest
```

### Model Integration
- Language detection using lightweight models
- Model routing based on language pair
- Fallback models for unsupported pairs
- Quality validation per language

## Implementation Tasks
- [ ] Add language detection capability
- [ ] Extend configuration system for language pairs
- [ ] Update CLI interface with language options
- [ ] Implement model routing logic
- [ ] Add language-specific validation
- [ ] Test with multilingual content
- [ ] Update documentation for new features

## Priority
**Low** - Expands utility but current Hungarian focus meets primary needs
