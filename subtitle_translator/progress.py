"""
Progress persistence and resume functionality for subtitle translation.
"""

import json
import logging
import signal
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .srt_parser import SubtitleEntry


class TranslationProgress:
    """Manages translation progress persistence and resume functionality."""
    
    def __init__(self, input_file: Path, output_file: Path):
        """
        Initialize progress manager for a translation task.
        
        Args:
            input_file: Path to input SRT file
            output_file: Path to output SRT file
        """
        self.input_file = input_file
        self.output_file = output_file
        self.progress_file = self._get_progress_file_path()
        self.logger = logging.getLogger(__name__)
        
        # Progress state
        self.current_index = 0
        self.total_entries = 0
        self.translated_entries: List[SubtitleEntry] = []
        self.start_time = datetime.now()
        self.last_save_time = datetime.now()
        
        # Set up signal handlers for safe interruption
        self._setup_signal_handlers()
    
    def _get_progress_file_path(self) -> Path:
        """Generate progress file path based on input/output files."""
        # Create progress file in same directory as output
        progress_name = f"{self.input_file.stem}.{self.output_file.stem}.progress"
        return self.output_file.parent / progress_name
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful interruption."""
        def signal_handler(signum, frame):
            self.logger.info("Received interruption signal. Saving progress...")
            self.save_progress()
            self.logger.info(f"Progress saved to {self.progress_file}")
            sys.exit(0)
        
        # Handle Ctrl+C and other termination signals
        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)
    
    def has_existing_progress(self) -> bool:
        """Check if progress file exists for this translation."""
        return self.progress_file.exists()
    
    def load_progress(self) -> bool:
        """
        Load existing progress from file.
        
        Returns:
            True if progress was loaded successfully, False otherwise
        """
        if not self.has_existing_progress():
            return False
        
        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate progress file format
            required_fields = ['input_file', 'output_file', 'current_index', 
                             'total_entries', 'translated_entries', 'timestamp']
            if not all(field in data for field in required_fields):
                self.logger.warning("Invalid progress file format")
                return False
            
            # Verify file paths match
            if (data['input_file'] != str(self.input_file) or 
                data['output_file'] != str(self.output_file)):
                self.logger.warning("Progress file paths don't match current translation")
                return False
            
            # Load progress state
            self.current_index = data['current_index']
            self.total_entries = data['total_entries']
            
            # Reconstruct translated entries
            self.translated_entries = []
            for entry_data in data['translated_entries']:
                entry = SubtitleEntry(
                    index=entry_data['index'],
                    start_time=entry_data['start_time'],
                    end_time=entry_data['end_time'],
                    text=entry_data['text'],
                    original_text=entry_data.get('original_text', '')
                )
                self.translated_entries.append(entry)
            
            self.logger.info(
                f"Loaded progress: {self.current_index}/{self.total_entries} entries "
                f"({self.get_progress_percentage():.1f}%)"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load progress: {e}")
            return False
    
    def save_progress(self):
        """Save current progress to file."""
        try:
            # Prepare data for serialization
            progress_data = {
                'input_file': str(self.input_file),
                'output_file': str(self.output_file),
                'current_index': self.current_index,
                'total_entries': self.total_entries,
                'translated_entries': [
                    {
                        'index': entry.index,
                        'start_time': entry.start_time,
                        'end_time': entry.end_time,
                        'text': entry.text,
                        'original_text': getattr(entry, 'original_text', '')
                    }
                    for entry in self.translated_entries
                ],
                'timestamp': datetime.now().isoformat(),
                'start_time': self.start_time.isoformat()
            }
            
            # Ensure output directory exists
            self.progress_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write progress file atomically
            temp_file = self.progress_file.with_suffix('.progress.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2, ensure_ascii=False)
            
            # Atomic move
            temp_file.replace(self.progress_file)
            self.last_save_time = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Failed to save progress: {e}")
            raise
    
    def add_translated_entry(self, entry: SubtitleEntry):
        """
        Add a translated entry and save progress.
        
        Args:
            entry: Translated subtitle entry
        """
        self.translated_entries.append(entry)
        self.current_index += 1
        
        # Save progress periodically (every 5 entries) or if it's been a while
        time_since_save = (datetime.now() - self.last_save_time).total_seconds()
        if self.current_index % 5 == 0 or time_since_save > 30:
            self.save_progress()
    
    def initialize_translation(self, total_entries: int):
        """Initialize translation with total entry count."""
        self.total_entries = total_entries
        if not self.has_existing_progress():
            self.save_progress()  # Create initial progress file
    
    def get_progress_percentage(self) -> float:
        """Get current progress as percentage."""
        if self.total_entries == 0:
            return 0.0
        return (self.current_index / self.total_entries) * 100
    
    def get_remaining_entries(self) -> int:
        """Get number of remaining entries to translate."""
        return self.total_entries - self.current_index
    
    def is_complete(self) -> bool:
        """Check if translation is complete."""
        return self.current_index >= self.total_entries
    
    def cleanup_progress_file(self):
        """Remove progress file after successful completion."""
        try:
            if self.progress_file.exists():
                self.progress_file.unlink()
                self.logger.info("Progress file cleaned up")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup progress file: {e}")
    
    def get_resume_summary(self) -> str:
        """Get human-readable summary of resume state."""
        if not self.has_existing_progress():
            return "No existing progress found."
        
        percentage = self.get_progress_percentage()
        remaining = self.get_remaining_entries()
        
        return (
            f"Found existing progress: {self.current_index}/{self.total_entries} "
            f"entries completed ({percentage:.1f}%). "
            f"{remaining} entries remaining."
        )


class ProgressMode:
    """Translation mode configuration."""
    
    LINE_BY_LINE = "line-by-line"
    BATCH = "batch"
    WHOLE_FILE = "whole-file"
    
    @classmethod
    def get_all_modes(cls) -> List[str]:
        """Get all available translation modes."""
        return [cls.LINE_BY_LINE, cls.BATCH, cls.WHOLE_FILE]
    
    @classmethod
    def is_valid_mode(cls, mode: str) -> bool:
        """Check if mode is valid."""
        return mode in cls.get_all_modes()
