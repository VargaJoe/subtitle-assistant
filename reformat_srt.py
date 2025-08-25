#!/usr/bin/env python3
"""
Lightweight SRT reformatter - splits subtitle lines without loading AI models.
"""

import argparse
import sys
from pathlib import Path
import yaml
import re
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


def parse_srt_file(file_path: Path, max_row_length: int = 42, row_split_method: str = "even"):
    """Parse and reformat SRT file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        except UnicodeDecodeError:
            print(f"❌ Cannot decode file {file_path}")
            return False

    # Remove BOM if present
    if content.startswith('\ufeff'):
        content = content[1:]

    # Split content into blocks (separated by double newlines)
    blocks = re.split(r'\n\s*\n', content.strip())
    
    reformatted_blocks = []
    
    for block in blocks:
        if not block.strip():
            continue
            
        lines = block.strip().split('\n')
        
        if len(lines) < 3:
            # Invalid block, skip
            continue
            
        # Keep index and timestamp lines, reformat text lines
        index_line = lines[0]
        timestamp_line = lines[1]
        text_lines = lines[2:]
        
        # Join all text lines and reformat
        text = '\n'.join(text_lines)
        reformatted_text = split_subtitle_text(text, max_row_length, row_split_method)
        
        # Rebuild the block
        reformatted_block = f"{index_line}\n{timestamp_line}\n{reformatted_text}"
        reformatted_blocks.append(reformatted_block)
    
    # Write back to file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(reformatted_blocks) + '\n')
        return True
    except IOError as e:
        print(f"❌ Failed to write file {file_path}: {e}")
        return False


def load_config():
    """Load configuration from config.yaml."""
    config_path = Path("config.yaml")
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            output_config = config.get('output', {})
            return {
                'max_row_length': output_config.get('max_row_length', 42),
                'row_split_method': output_config.get('row_split_method', 'even')
            }
        except Exception as e:
            print(f"⚠️ Failed to load config.yaml: {e}")
    
    # Default values
    return {
        'max_row_length': 42,
        'row_split_method': 'even'
    }


def main():
    parser = argparse.ArgumentParser(description="Fast SRT reformatter - splits subtitle lines")
    parser.add_argument("files", nargs="+", help="SRT files to reformat")
    parser.add_argument("--max-length", type=int, help="Maximum line length (overrides config)")
    parser.add_argument("--method", choices=["even", "word", "char"], help="Split method (overrides config)")
    
    args = parser.parse_args()
    
    # Load config
    config = load_config()
    max_length = args.max_length or config['max_row_length']
    method = args.method or config['row_split_method']
    
    print(f"🔧 SRT Reformatter - Max length: {max_length}, Method: {method}")
    
    success_count = 0
    error_count = 0
    
    for file_arg in args.files:
        file_path = Path(file_arg)
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            error_count += 1
            continue
            
        print(f"🔧 Reformatting: {file_path.name}")
        if parse_srt_file(file_path, max_length, method):
            print(f"✅ Success: {file_path.name}")
            success_count += 1
        else:
            error_count += 1
    
    print(f"\n📊 Results: ✅ {success_count} success, ❌ {error_count} failed")
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
