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
  python main.py input.srt --config custom_config.yaml
        """
    )
    
    parser.add_argument(
        "input",
        nargs="?",
        help="Input SRT file(s) to translate"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: adds language suffix)"
    )
    
    parser.add_argument(
        "--config", "-c",
        help="Configuration YAML file (default: config.yaml)"
    )
    
    parser.add_argument(
        "--source",
        help="Source language code (overrides config)"
    )
    
    parser.add_argument(
        "--target", 
        help="Target language code (overrides config)"
    )
    
    parser.add_argument(
        "--model",
        help="Ollama model to use (overrides config)"
    )
    
    parser.add_argument(
        "--formality",
        choices=["formal", "informal", "auto"],
        help="Translation formality level (overrides config)"
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
    
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate setup and exit"
    )
    
    parser.add_argument(
        "--mode",
        choices=["line-by-line", "batch", "whole-file", "multi-model"],
        help="Translation mode: line-by-line (default), batch (faster), whole-file (experimental), or multi-model (4-stage AI pipeline)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        help="Number of entries per batch (for batch mode, overrides config)"
    )
    
    parser.add_argument(
        "--overlap-size",
        type=int,
        help="Number of entries to overlap between batches (overrides config)"
    )
    
    parser.add_argument(
        "--no-overlap-reassess",
        action="store_true",
        help="Disable reassessment of overlapping entries"
    )
    
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing progress (default: auto-detect)"
    )
    
    parser.add_argument(
        "--restart", 
        action="store_true",
        help="Force restart, ignoring existing progress"
    )

    args = parser.parse_args()
    
    # Load configuration
    config_path = Path(args.config or "config.yaml")
    
    try:
        if config_path.exists():
            config = Config.from_yaml(config_path)
            print(f"✅ Loaded configuration from {config_path}")
        else:
            config = Config()
            print("⚠️  Using default configuration (config.yaml not found)")
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return 1
    
    # Override config with CLI arguments
    if args.source:
        config.source_lang = args.source
    if args.target:
        config.target_lang = args.target
    if args.model:
        config.model = args.model
    if args.formality:
        config.tone.formality = args.formality
    if args.mode:
        config.translation_mode = args.mode
    if args.batch_size:
        config.batch_size = args.batch_size
    if args.overlap_size is not None:
        config.overlap_size = args.overlap_size
    if args.no_overlap_reassess:
        config.reassess_overlaps = False
    if args.verbose:
        config.verbose = True
    
    # Initialize translator
    try:
        translator = SubtitleTranslator(config)
    except Exception as e:
        print(f"❌ Failed to initialize translator: {e}")
        return 1
    
    # Validate setup if requested
    if args.validate:
        if translator.validate_setup():
            print("🎉 Translator setup is valid!")
            return 0
        else:
            print("❌ Translator setup has issues.")
            return 1

    # Check if input is provided when not validating
    if not args.input:
        parser.error("Input file is required unless using --validate")

    # Determine resume behavior
    resume_enabled = True  # Default to auto-detect
    if args.restart:
        resume_enabled = False
        print("🔄 Forcing restart, ignoring existing progress")
    elif args.resume:
        resume_enabled = True
        print("▶️  Resume mode enabled")
    
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
                output_path = args.output or config.get_output_filename(file)
                translator.translate_file(file, output_path, resume=resume_enabled)
        else:
            # Single file processing
            output_path = args.output or config.get_output_filename(input_path)
            translator.translate_file(input_path, output_path, resume=resume_enabled)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
