# Story 15 - Simple PowerShell GUI

## Overview
Create a simple, fast, and easy-to-use PowerShell-based GUI for the Subtitle Assistant, wrapping the existing batch processing functionality with an intuitive interface.

## Business Value
- Lowers barrier to entry for non-technical users
- Provides visual feedback during translation
- Enables easy control (stop/pause/resume) without command line knowledge
- Maintains the power of batch processing with a friendlier interface

## User Stories

### US-15.1: Launch GUI for Batch Translation
**As a** casual user  
**I want** a simple GUI to translate all subtitles in a folder  
**So that** I don't need to remember command-line options

**Acceptance Criteria:**
- Double-click PowerShell script launches GUI window
- GUI shows clear title and branding
- Window size is appropriate and resizable
- GUI loads quickly (< 1 second)
- No external dependencies required (pure PowerShell)

### US-15.2: Select Translation Operation
**As a** user  
**I want** to choose between translate-all, translate-selected, or reformat  
**So that** I can perform different operations from the same interface

**Acceptance Criteria:**
- Radio buttons or dropdown for operation selection:
  - "Translate All Subtitles"
  - "Translate Selected File(s)"
  - "Reformat Existing Translations"
- Operation selection is clear and self-explanatory
- Selected operation updates relevant UI elements
- Default selection is "Translate All Subtitles"

### US-15.3: Configure Translation Settings
**As a** user  
**I want** to configure basic translation settings in the GUI  
**So that** I can customize translations without editing config files

**Acceptance Criteria:**
- Input field or folder browser for subtitles folder path
- Input field or folder browser for output folder path
- Dropdown for source language (default: English)
- Dropdown for target language (default: Hungarian)
- Checkbox for verbose output
- "Use Config File Settings" button to load from config.yaml
- Settings persist between GUI sessions (saved to user preferences)

### US-15.4: Browse and Select Files/Folders
**As a** user  
**I want** folder browser dialogs for selecting paths  
**So that** I don't need to type or remember file paths

**Acceptance Criteria:**
- "Browse" button next to folder path fields
- Standard Windows folder picker dialog
- Recent folders list for quick access
- Drag-and-drop support for folders and files
- Selected paths display with full path tooltip

### US-15.5: Monitor Translation Progress
**As a** user  
**I want** to see real-time progress of translation  
**So that** I know how long to wait and what's happening

**Acceptance Criteria:**
- Progress bar showing overall completion percentage
- Current file being processed displayed
- File counter (e.g., "5/20 files")
- Estimated time remaining
- Live log output window (scrollable, auto-scroll to bottom)
- Success/failure count updates in real-time

### US-15.6: Control Translation Process
**As a** user  
**I want** to stop, pause, or resume translation  
**So that** I can control the process without closing the application

**Acceptance Criteria:**
- "Start Translation" button (changes to "Stop" when running)
- "Pause/Resume" toggle button (enabled during translation)
- "Stop" button gracefully terminates current file and saves progress
- Resume functionality works across GUI sessions
- Confirmation dialog before stopping
- Visual indication of current state (translating, paused, stopped)

### US-15.7: Review Translation Results
**As a** user  
**I want** to see a summary of translation results  
**So that** I know what succeeded and what failed

**Acceptance Criteria:**
- Final summary dialog with:
  - Total files processed
  - Successful translations count
  - Failed translations count
  - Total time elapsed
  - Option to view error log
- Summary remains visible after completion
- "Open Output Folder" button
- "View Error Log" button (if errors occurred)
- "Close" button to exit GUI

### US-15.8: Handle Errors Gracefully
**As a** user  
**I want** clear error messages when something goes wrong  
**So that** I can fix issues and retry

**Acceptance Criteria:**
- User-friendly error messages (not technical stack traces)
- Specific error context (which file, what operation)
- Suggestions for fixing common errors
- Option to retry failed translations
- Error log saved to file for troubleshooting
- Visual indication of errors (red text, warning icons)

## Technical Implementation

### Phase 1: Basic GUI Framework
**Task 15.1.1:** Create PowerShell GUI script
- Create `gui_translate.ps1` in project root
- Use Windows Forms (System.Windows.Forms)
- Design main window layout with WPF or WinForms
- Implement basic window controls (buttons, labels, textboxes)
- Add error handling and logging

**Task 15.1.2:** Implement operation selection
- Add radio buttons for operation types
- Wire up event handlers for selection changes
- Update UI elements based on selected operation
- Set appropriate defaults

**Task 15.1.3:** Add settings configuration UI
- Create input fields for folder paths
- Add language dropdown lists
- Implement settings persistence (registry or JSON file)
- Add "Load from Config" functionality
- Validate input before starting translation

### Phase 2: File Selection and Browsing
**Task 15.2.1:** Implement folder browser
- Add FolderBrowserDialog for folder selection
- Implement "Browse" button event handlers
- Add drag-and-drop support for folders
- Store recent folders in settings
- Validate selected paths

**Task 15.2.2:** Implement file selection for single-file mode
- Add OpenFileDialog for file selection
- Support multi-file selection
- Show selected files in list view
- Add "Remove" button for selected files
- Validate file types (.srt only)

**Task 15.2.3:** Add file preview
- Show list of files to be processed
- Display file count and total size
- Preview first file's content in read-only textbox
- Add "Refresh" button to rescan folder

### Phase 3: Translation Process Management
**Task 15.3.1:** Implement progress tracking
- Add progress bar control
- Add status label for current file
- Add file counter label
- Implement time estimation algorithm
- Update progress in real-time

**Task 15.3.2:** Integrate with batch script
- Call `translate_all_srt.ps1` or `main.py` from GUI
- Capture output and parse progress
- Update GUI based on script output
- Handle script errors gracefully
- Support background execution

**Task 15.3.3:** Add process control
- Implement "Start" button functionality
- Implement "Stop" button with graceful shutdown
- Add "Pause/Resume" toggle
- Handle Ctrl+C interruption
- Save progress state on stop

**Task 15.3.4:** Create live log viewer
- Add RichTextBox for log output
- Colorize log messages (info, warning, error)
- Auto-scroll to bottom
- Add "Clear Log" button
- Implement log filtering (show only errors, etc.)

### Phase 4: Results and Error Handling
**Task 15.4.1:** Implement results summary
- Create summary dialog window
- Display statistics (success/fail counts, time)
- Add "Open Output Folder" button
- Add "View Error Log" button
- Save summary to file

**Task 15.4.2:** Add error handling and reporting
- Catch and display user-friendly errors
- Create error log file with detailed info
- Implement retry mechanism for failed files
- Add "Report Issue" button (opens browser to GitHub issues)
- Show troubleshooting tips for common errors

**Task 15.4.3:** Add help and documentation
- Create "Help" button with user guide
- Add tooltips for all controls
- Create "About" dialog with version info
- Link to online documentation
- Add keyboard shortcuts

### Phase 5: Polish and Distribution
**Task 15.5.1:** Improve UI/UX
- Add application icon
- Implement consistent styling
- Add status bar with helpful information
- Improve spacing and alignment
- Test on different Windows versions

**Task 15.5.2:** Add advanced features
- Remember window size and position
- Add "Settings" menu for advanced config
- Implement theme support (light/dark)
- Add keyboard shortcuts
- Support command-line arguments for automation

**Task 15.5.3:** Create installer/launcher
- Create standalone executable (with ps2exe or similar)
- Add desktop shortcut creation option
- Create "Quick Start" guide
- Add uninstaller
- Include in project documentation

**Task 15.5.4:** Testing and documentation
- Test on different Windows versions (10, 11)
- Test with various screen resolutions
- Create user manual with screenshots
- Add troubleshooting section
- Create video tutorial

## GUI Mockup (Text-Based)

```
┌─────────────────────────────────────────────────────────────────┐
│ Subtitle Assistant - Translation GUI                      [_][□][X] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Operation:                                                     │
│  ○ Translate All Subtitles                                     │
│  ○ Translate Selected File(s)                                  │
│  ○ Reformat Existing Translations                              │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Settings                                                │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ Subtitles Folder: [C:\subtitles           ] [Browse...] │   │
│  │ Output Folder:    [C:\output              ] [Browse...] │   │
│  │ Source Language:  [English ▼]                           │   │
│  │ Target Language:  [Hungarian ▼]                         │   │
│  │ ☑ Verbose Output  ☐ Auto-detect Language               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Progress                                                │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ Status: Ready                                           │   │
│  │ Files: 0/15                                             │   │
│  │ [█████████░░░░░░░░░░░░░░] 45% - ETA: 2m 30s            │   │
│  │ Current: tvshow.s01e03.srt                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Log Output                                    [Clear]   │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ [INFO] Starting translation...                          │   │
│  │ [INFO] Processing tvshow.s01e01.srt                     │   │
│  │ [SUCCESS] Translation complete (23.5s)                  │   │
│  │ [INFO] Processing tvshow.s01e02.srt                     │   │
│  │ ...                                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [  Start Translation  ] [  Stop  ] [ Pause ]  [ Help ]        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Configuration Example

No additional configuration file needed. Settings stored in:
- Windows Registry: `HKCU:\Software\SubtitleAssistant\GUI`
- Or JSON file: `%APPDATA%\SubtitleAssistant\gui_settings.json`

```json
{
  "last_subtitles_folder": "C:\\subtitles",
  "last_output_folder": "C:\\output",
  "source_language": "en",
  "target_language": "hu",
  "verbose": false,
  "auto_detect": false,
  "window_position": { "x": 100, "y": 100 },
  "window_size": { "width": 800, "height": 600 },
  "theme": "light"
}
```

## Dependencies
- PowerShell 5.1+ (included with Windows 10/11)
- .NET Framework 4.5+ (for Windows Forms)
- Optional: ps2exe for creating standalone .exe

## Testing Strategy
1. **Manual Testing**: Test on Windows 10 and 11
2. **UI Testing**: Verify all controls work as expected
3. **Integration Testing**: Test with real translation workflows
4. **Error Testing**: Verify error handling for various failure scenarios
5. **Performance Testing**: Ensure GUI remains responsive during translation

## Success Metrics
- GUI launches in < 1 second
- Translation starts within 2 seconds of clicking "Start"
- Progress updates every second
- No GUI freezing during translation
- Clear error messages for 100% of error scenarios

## Future Enhancements
- WPF version with modern UI
- Dark mode support
- Queue multiple translation jobs
- Schedule translations
- Integration with drag-and-drop from Windows Explorer
- System tray icon for background operation
- Cloud backup of translations
- Real-time preview of translations
