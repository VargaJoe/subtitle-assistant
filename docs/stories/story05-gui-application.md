# Story 05 - GUI Application

## Story Title
**User-Friendly Graphical Interface for Subtitle Translation**

## User Story
As a non-technical user, I want a simple drag-and-drop graphical interface for translating subtitle files, so that I can use the translation system without needing to use command-line tools or understand technical configurations.

## Acceptance Criteria

### Must Have
- [ ] Simple drag-and-drop interface for SRT files
- [ ] Progress visualization with estimated time remaining
- [ ] Basic settings management (source/target language, model selection)
- [ ] File browser for input/output selection
- [ ] Start/stop/pause translation controls

### Should Have
- [ ] Real-time translation preview as processing occurs
- [ ] Settings import/export from YAML configuration
- [ ] Batch processing queue management
- [ ] Translation history and recent files
- [ ] Error handling with user-friendly messages

### Could Have
- [ ] Side-by-side original/translated preview
- [ ] Manual translation editing and correction
- [ ] Multi-model pipeline controls in GUI
- [ ] Advanced settings panel for power users
- [ ] Themes and customizable interface

### Won't Have (This Release)
- [ ] Real-time subtitle editing during video playback
- [ ] Video player integration
- [ ] Cloud translation services
- [ ] Collaborative editing features

## Technical Requirements

### Framework Selection
- **Recommended**: PyQt6 or PySide6 for native desktop experience
- **Alternative**: Tkinter for lightweight solution
- **Web-based**: Flask/FastAPI + HTML/CSS/JS for browser interface

### Core Components
- **File Handler**: Drag-and-drop support, file validation
- **Progress Manager**: Real-time progress updates, cancellation support
- **Settings Panel**: Configuration management, model selection
- **Preview Pane**: Translation preview, side-by-side comparison

### Integration Points
```python
# GUI calls existing translation system
from subtitle_translator import SubtitleTranslator, Config

translator = SubtitleTranslator(config)
translator.translate_file(input_file, output_file, progress_callback=update_gui)
```

## Implementation Tasks
- [ ] Choose GUI framework (PyQt6 recommended)
- [ ] Design interface mockups and user flows
- [ ] Implement main window with drag-and-drop
- [ ] Add progress visualization and controls
- [ ] Create settings management interface
- [ ] Integrate with existing translation pipeline
- [ ] Add error handling and user notifications
- [ ] Implement batch processing queue
- [ ] Create installer/packaging for distribution
- [ ] Write user documentation and tutorials

## User Interface Mockup
```
┌─────────────────────────────────────────────────────────┐
│ Subtitle Assistant                                   [_][□][×] │
├─────────────────────────────────────────────────────────┤
│ File  Settings  Help                                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│    📁 Drag SRT files here or click to browse           │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Source: English        Target: Hungarian           │ │
│ │ Model: gemma3n:latest  Mode: Multi-model           │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Progress: ████████████████░░░░ 75%                      │
│ Processing: entry 150/200 (Est: 2:30 remaining)        │
│                                                         │
│ [📁 Browse] [⚙️ Settings] [▶️ Start] [⏸️ Pause] [⏹️ Stop] │
└─────────────────────────────────────────────────────────┘
```

## Priority
**Low** - Nice-to-have for user experience but CLI interface meets current needs
