"""
SRT (SubRip) subtitle file parser and handler.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Iterator
from datetime import timedelta

def split_subtitle_text(text: str, max_length: int = 42, method: str = "even") -> str:
    """
    Split subtitle text into rows according to max_length and method.
    Methods:
        - even: Split as evenly as possible, may break words if needed.
        - word: Split at word boundaries, never break words.
        - char: Split at exact character count, may break words.
    """
    if not text or max_length < 1:
        return text

    lines = []
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    paragraphs = text.split('\n')
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if method == "char":
            # Split at exact character count
            for i in range(0, len(paragraph), max_length):
                lines.append(paragraph[i:i+max_length])
        elif method == "word":
            # Split at word boundaries
            words = paragraph.split()
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + (1 if current_line else 0) > max_length:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
                else:
                    current_line = (current_line + " " + word) if current_line else word
            if current_line:
                lines.append(current_line)
        else:  # even
            # Split as evenly as possible, trying different split points
            if len(paragraph) <= max_length:
                lines.append(paragraph)
            else:
                words = paragraph.split()
                best_split = None
                min_difference = float('inf')
                
                # Try splitting at different word positions
                for i in range(1, len(words)):
                    first_part = " ".join(words[:i])
                    second_part = " ".join(words[i:])
                    
                    # Both parts must fit within max_length
                    if len(first_part) <= max_length and len(second_part) <= max_length:
                        # Calculate how even the split is
                        difference = abs(len(first_part) - len(second_part))
                        
                        # Prefer this split if it's more even
                        if difference < min_difference:
                            min_difference = difference
                            best_split = (first_part, second_part)
                
                if best_split:
                    # Found a good 2-line split
                    lines.append(best_split[0])
                    lines.append(best_split[1])
                else:
                    # No good 2-line split possible, fall back to word-boundary splitting
                    current_line = ""
                    for word in words:
                        test_line = (current_line + " " + word) if current_line else word
                        
                        if len(test_line) > max_length:
                            if current_line:
                                lines.append(current_line)
                                current_line = word
                            else:
                                lines.append(word)
                                current_line = ""
                        else:
                            current_line = test_line
                    
                    if current_line:
                        lines.append(current_line)
    return '\n'.join(lines)


@dataclass
class SubtitleEntry:
    """Represents a single subtitle entry."""
    
    index: int
    start_time: timedelta
    end_time: timedelta
    text: str
    original_text: Optional[str] = None
    
    def __post_init__(self):
        """Clean and validate subtitle entry after creation."""
        self.text = self._clean_text(self.text)
        if self.original_text:
            self.original_text = self._clean_text(self.original_text)
    
    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean subtitle text while preserving formatting."""
        if not text:
            return ""
        
        # Normalize line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove extra whitespace but preserve intentional spacing
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(line for line in lines if line)
        
        return text
    
    @property
    def duration(self) -> timedelta:
        """Get duration of the subtitle."""
        return self.end_time - self.start_time
    
    def format_time(self, time: timedelta) -> str:
        """Format timedelta to SRT timestamp format."""
        total_seconds = int(time.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        milliseconds = int(time.microseconds / 1000)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    def to_srt_format(self, use_original: bool = False, max_row_length: int = 42, row_split_method: str = "even") -> str:
        """Convert entry back to SRT format, applying row splitting."""
        text_to_use = self.original_text if use_original and self.original_text else self.text
        # Apply row splitting
        text_to_use = split_subtitle_text(text_to_use, max_row_length, row_split_method)
        start_time_str = self.format_time(self.start_time)
        end_time_str = self.format_time(self.end_time)
        return f"{self.index}\n{start_time_str} --> {end_time_str}\n{text_to_use}\n"


class SRTParser:
    """Parser for SRT subtitle files."""
    
    def __init__(self):
        """Initialize SRT parser."""
        self.logger = logging.getLogger(__name__)
        
        # Regex pattern for SRT timestamp
        self.time_pattern = re.compile(
            r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})'
        )
    
    def parse_file(self, file_path: Path) -> List[SubtitleEntry]:
        """
        Parse SRT file and return list of subtitle entries.
        
        Args:
            file_path: Path to SRT file
            
        Returns:
            List of SubtitleEntry objects
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        if not file_path.exists():
            raise FileNotFoundError(f"SRT file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                self.logger.warning(f"Used latin-1 encoding for {file_path}")
            except UnicodeDecodeError as e:
                raise ValueError(f"Cannot decode file {file_path}: {e}")
        
        return self.parse_content(content)
    
    def parse_content(self, content: str) -> List[SubtitleEntry]:
        """
        Parse SRT content string.
        
        Args:
            content: SRT file content as string
            
        Returns:
            List of SubtitleEntry objects
        """
        entries = []
        
        # Remove BOM if present
        if content.startswith('\ufeff'):
            content = content[1:]
            self.logger.info("Removed BOM from SRT content")
        
        # Split content into blocks (separated by double newlines)
        blocks = re.split(r'\n\s*\n', content.strip())
        
        for block in blocks:
            if not block.strip():
                continue
                
            try:
                entry = self._parse_block(block)
                if entry:
                    entries.append(entry)
            except ValueError as e:
                self.logger.warning(f"Skipping invalid subtitle block: {e}")
                continue
        
        if not entries:
            raise ValueError("No valid subtitle entries found")
        
        return entries
    
    def _parse_block(self, block: str) -> Optional[SubtitleEntry]:
        """Parse a single subtitle block."""
        lines = block.strip().split('\n')
        
        if len(lines) < 3:
            raise ValueError(f"Block has insufficient lines: {len(lines)}")
        
        # Parse index
        try:
            index_str = lines[0].strip()
            # Remove BOM if present on first line
            if index_str.startswith('\ufeff'):
                index_str = index_str[1:]
                self.logger.info(f"Removed BOM from subtitle index at line: {lines[0]}")
            index = int(index_str)
        except ValueError:
            raise ValueError(f"Invalid subtitle index: {lines[0]} (check for BOM or invalid characters)")
        
        # Parse timestamp
        time_match = self.time_pattern.match(lines[1].strip())
        if not time_match:
            raise ValueError(f"Invalid timestamp format: {lines[1]}")
        
        start_time = self._parse_timestamp(*time_match.groups()[:4])
        end_time = self._parse_timestamp(*time_match.groups()[4:])
        
        # Parse subtitle text (can be multiple lines)
        text = '\n'.join(lines[2:]).strip()
        
        if not text:
            self.logger.warning(f"Empty subtitle text at index {index}")
            return None
        
        return SubtitleEntry(
            index=index,
            start_time=start_time,
            end_time=end_time,
            text=text
        )
    
    def _parse_timestamp(self, hours: str, minutes: str, seconds: str, milliseconds: str) -> timedelta:
        """Parse timestamp components into timedelta."""
        return timedelta(
            hours=int(hours),
            minutes=int(minutes),
            seconds=int(seconds),
            milliseconds=int(milliseconds)
        )
    
    def write_file(self, entries: List[SubtitleEntry], file_path: Path, max_row_length: int = 42, row_split_method: str = "even") -> None:
        """
        Write subtitle entries to SRT file.
        
        Args:
            entries: List of SubtitleEntry objects
            file_path: Output file path
        """
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for i, entry in enumerate(entries):
                    f.write(entry.to_srt_format(max_row_length=max_row_length, row_split_method=row_split_method))
                    # Add separator between entries (except for last one)
                    if i < len(entries) - 1:
                        f.write('\n')
            self.logger.info(f"Written {len(entries)} subtitle entries to {file_path}")
        except IOError as e:
            raise ValueError(f"Failed to write SRT file {file_path}: {e}")
    
    def get_context_window(self, entries: List[SubtitleEntry], current_index: int, window_size: int = 3) -> str:
        """
        Get context text from surrounding subtitle entries.
        
        Args:
            entries: List of all subtitle entries
            current_index: Index of current entry (0-based)
            window_size: Number of entries before/after to include
            
        Returns:
            Context string with surrounding subtitles
        """
        if not entries or current_index < 0 or current_index >= len(entries):
            return ""
        
        context_parts = []
        
        # Add previous entries
        start_idx = max(0, current_index - window_size)
        for i in range(start_idx, current_index):
            context_parts.append(f"Previous: {entries[i].text}")
        
        # Add current entry
        context_parts.append(f"Current: {entries[current_index].text}")
        
        # Add next entries
        end_idx = min(len(entries), current_index + window_size + 1)
        for i in range(current_index + 1, end_idx):
            context_parts.append(f"Next: {entries[i].text}")
        
        return "\n".join(context_parts)
