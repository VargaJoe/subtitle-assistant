# Story 01 - SRT Translation

## Story Title
**Basic SRT Subtitle Translation with AI Context-Awareness**

## User Story
As a hearing-impaired user, I want to translate existing English SRT subtitle files to Hungarian while preserving the original timing and structure, so that I can enjoy movies and TV shows in my native language with accurate, context-aware translations.

## Acceptance Criteria

### Must Have
- [ ] Parse existing SRT files maintaining original timecode structure
- [ ] Translate subtitle text from English to Hungarian using Ollama AI
- [ ] Preserve original SRT format and timing information
- [ ] Handle multiple subtitle entries in sequence
- [ ] Output translated SRT file with same filename + language suffix (e.g., `movie.srt` → `movie.hun.srt`)

### Should Have
- [ ] Context-aware translation that considers previous and next subtitles for better accuracy
- [ ] Handle special formatting (italics, bold) in subtitle text
- [ ] Support batch processing of multiple SRT files
- [ ] Progress indication for long translation processes

### Could Have
- [ ] Configuration for translation parameters (temperature, model selection)
- [ ] Backup original files before translation
- [ ] Validation of translated content length vs. original
- [ ] Simple logging of translation process

### Won't Have (This Release)
- [ ] Real-time translation
- [ ] GUI interface
- [ ] Support for other subtitle formats (VTT, ASS, etc.)
- [ ] Automatic language detection

## Technical Requirements

### Dependencies
- Python 3.8+
- Ollama running locally
- Required Python packages:
  - `pysrt` for SRT parsing
  - `ollama` for AI translation
  - `argparse` for CLI interface
  - `pathlib` for file handling

### Input/Output
- **Input**: SRT file(s) in English
- **Output**: Translated SRT file(s) in Hungarian
- **Configuration**: CLI arguments for source/target languages, model selection

### Performance Criteria
- Process standard TV episode subtitles (500-800 entries) within 5-10 minutes
- Maintain translation context across subtitle boundaries
- Handle files up to 1000 subtitle entries without memory issues

## Definition of Done
- [ ] CLI application can successfully translate SRT files
- [ ] Original timing and structure preserved
- [ ] Context-aware translation produces coherent Hungarian text
- [ ] Unit tests cover core functionality
- [ ] Documentation includes usage examples
- [ ] Tested with provided Magnum P.I. subtitle files

## Priority
**High** - This is the core functionality of the application

## Estimated Effort
**Medium** - 3-5 days development time

## Notes
- Start with simple sentence-by-sentence translation, then enhance with context awareness
- Use Ollama's chat completion API for better context handling
- Consider subtitle text length constraints to avoid display issues
- Test thoroughly with real subtitle files from the project
