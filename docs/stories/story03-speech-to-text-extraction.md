# Story 03 - Speech-to-Text Subtitle Extraction with Progress

## Story Title
**Progressive Audio-to-Subtitle Extraction with Resume Capability**

## User Story
As a content creator or subtitle translator, I want to extract subtitles directly from video/audio files using speech recognition with the ability to save progress and resume extraction, so that I can efficiently create subtitle files from raw video content without losing work if the process is interrupted.

## Background
This feature bridges the gap between raw video content and the translation pipeline by automatically extracting spoken content into subtitle format, which can then be translated using the existing translation system.

## Core Functionality

### 🎯 **Speech-to-Text Extraction**
- Extract audio from video files (MKV, MP4, AVI, etc.)
- Convert speech to text using specialized models
- Generate timestamped SRT files with proper formatting
- Support for multiple languages (Hungarian focus initially)

### 💾 **Progress Persistence**
- Save extraction progress during processing
- Resume from interruption point without reprocessing
- Chunk-based processing for memory efficiency
- Progress tracking with time estimates

### 🔄 **Integration with Translation Pipeline**
- Generated SRT files compatible with existing translation system
- Seamless workflow: Video → SRT → Translated SRT
- Quality validation before translation handoff

## Acceptance Criteria

### Must Have - Core Extraction
- [ ] Extract audio from common video formats (MP4, MKV, AVI)
- [ ] Speech-to-text conversion with Hungarian language support
- [ ] Generate properly formatted SRT files with accurate timestamps
- [ ] Progress persistence and resume functionality
- [ ] Error handling and recovery mechanisms

### Should Have - Quality & Performance
- [ ] Multiple speech recognition model options (quality vs speed)
- [ ] GPU acceleration support for faster processing
- [ ] Quality metrics and confidence scoring
- [ ] Chunk-based processing for long videos (>1 hour)
- [ ] Progress visualization and time estimation

### Could Have - Advanced Features
- [ ] Speaker identification and labeling
- [ ] Automatic silence detection and trimming
- [ ] Multiple audio track support
- [ ] Batch processing of multiple videos
- [ ] Integration with existing CLI interface

## Technical Approach

### **Models & Technologies**
- **Primary**: Hungarian-fine-tuned Whisper models (sarpba/whisper-base-hungarian_v1)
- **Fallback**: Standard OpenAI Whisper models
- **Audio Processing**: ffmpeg for audio extraction
- **Progress Storage**: JSON-based progress files (similar to translation progress)

### **Architecture Integration**
- **Module**: `subtitle_translator/speech_extractor.py`
- **Progress**: Extend existing progress system for extraction
- **CLI**: Add `extract` command to main CLI interface
- **Config**: Add extraction settings to configuration system

## Example Usage

```bash
# Extract subtitles from video
python main.py extract video.mkv --output subtitles.srt

# Resume interrupted extraction
python main.py extract video.mkv --resume

# Extract with specific model quality
python main.py extract video.mkv --model-quality best --gpu

# Extract then translate in one command
python main.py extract-translate video.mkv --target hu --output final.hu.srt
```

## Expected Benefits
- **Workflow Efficiency**: Direct video-to-translated-subtitles pipeline
- **Time Savings**: No manual transcription needed
- **Quality**: Specialized Hungarian models for better accuracy
- **Reliability**: Progress saving prevents lost work on long videos
- **Integration**: Seamless connection with existing translation features

## Dependencies
- Speech recognition models (Whisper variants)
- ffmpeg for audio processing
- Existing progress management system
- GPU support (optional but recommended)

## Risks & Mitigations
- **Speech Recognition Accuracy**: Use multiple model options, quality validation
- **Processing Time**: GPU acceleration, chunk processing, progress saving
- **Audio Quality**: Preprocessing and noise reduction options
- **Language Support**: Focus on Hungarian initially, expand later

## Priority
**Medium-High** - Valuable feature that completes the content creation pipeline

## Estimated Effort
**Medium** - 5-8 days development time
- 2 days: Core extraction functionality
- 2 days: Progress persistence integration
- 2 days: Quality optimization and model integration
- 1-2 days: CLI integration and testing

## Story Dependencies
- Story 1.5 - Resume and Progress Management (✅ COMPLETED)
- Configuration system expansion
- Optional: Story 02 for quality validation integration

## Implementation Phases

### Phase 1: Basic Extraction (Demo Level)
- Core speech-to-text with simple progress saving
- Single model support
- Basic SRT generation

### Phase 2: Production Ready
- Multiple model options
- Full progress persistence
- Error handling and recovery

### Phase 3: Advanced Features
- Quality validation
- Batch processing
- CLI integration with main system

---

**Status**: Planning Phase  
**Created**: 2025-06-26  
**Next Action**: Implement Phase 1 demo functionality in current branch
