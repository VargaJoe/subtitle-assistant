#!/usr/bin/env python3
"""
Subtitle Translator Assistant
A Python application for translating SRT subtitle files using Ollama AI.

Main entry point for the CLI application.
"""

import argparse
import sys
from pathlib import Path

from subtitle_translator.translator import SubtitleTranslator
from subtitle_translator.config import Config


def main():
    """Main entry point for the subtitle translator CLI."""
    parser = argparse.ArgumentParser(
        description="Translate SRT subtitle files using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py input.srt -o output.srt
  python main.py input.srt --source en --target hu
  python main.py *.srt --batch
        """
    )
    
    parser.add_argument(
        "input",
        help="Input SRT file(s) to translate"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: adds language suffix)"
    )
    
    parser.add_argument(
        "--source",
        default="en",
        help="Source language code (default: en)"
    )
    
    parser.add_argument(
        "--target", 
        default="hu",
        help="Target language code (default: hu)"
    )
    
    parser.add_argument(
        "--model",
        default="llama3.2",
        help="Ollama model to use (default: llama3.2)"
    )
    
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process multiple files in batch mode"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Create config from arguments
    config = Config(
        source_lang=args.source,
        target_lang=args.target,
        model=args.model,
        verbose=args.verbose
    )
    
    # Initialize translator
    translator = SubtitleTranslator(config)
    
    try:
        # Handle single file or batch processing
        input_path = Path(args.input)
        
        if args.batch or "*" in args.input:
            # Batch processing
            if "*" in args.input:
                files = list(Path().glob(args.input))
            else:
                files = [input_path] if input_path.is_file() else list(input_path.glob("*.srt"))
            
            print(f"Processing {len(files)} files...")
            for file in files:
                output_path = args.output or file.with_suffix(f".{args.target}.srt")
                translator.translate_file(file, output_path)
        else:
            # Single file processing
            output_path = args.output or input_path.with_suffix(f".{args.target}.srt")
            translator.translate_file(input_path, output_path)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
