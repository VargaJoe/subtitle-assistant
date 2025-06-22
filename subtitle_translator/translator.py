"""
Main subtitle translator module.
"""

import logging
from pathlib import Path
from typing import List, Optional
import time

from .config import Config
from .srt_parser import SRTParser, SubtitleEntry
from .ollama_client import OllamaClient


class SubtitleTranslator:
    """Main translator class that orchestrates the translation process."""
    
    def __init__(self, config: Config):
        """Initialize translator with configuration."""
        self.config = config
        self.parser = SRTParser()
        self.ollama_client = OllamaClient(config)
        
        # Set up logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Verify Ollama connection
        if not self.ollama_client.is_available():
            raise ConnectionError(
                f"Cannot connect to Ollama at {config.ollama_url}. "
                "Please ensure Ollama is running."
            )
        
        # Verify model availability
        available_models = self.ollama_client.get_available_models()
        if config.model not in available_models:
            self.logger.warning(
                f"Model '{config.model}' not found. Available models: {available_models}"
            )
    
    def _setup_logging(self):
        """Set up logging configuration."""
        level = logging.INFO if self.config.verbose else logging.WARNING
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def translate_file(self, input_path: Path, output_path: Path) -> None:
        """
        Translate a single SRT file.
        
        Args:
            input_path: Path to input SRT file
            output_path: Path to output translated SRT file
        """
        start_time = time.time()
        
        self.logger.info(f"Starting translation: {input_path} -> {output_path}")
        self.logger.info(f"Languages: {self.config.source_lang} -> {self.config.target_lang}")
        
        try:
            # Parse input file
            entries = self.parser.parse_file(input_path)
            self.logger.info(f"Parsed {len(entries)} subtitle entries")
            
            # Translate entries
            translated_entries = self._translate_entries(entries)
            
            # Write output file
            self.parser.write_file(translated_entries, output_path)
            
            # Report completion
            elapsed_time = time.time() - start_time
            self.logger.info(
                f"Translation completed in {elapsed_time:.1f} seconds. "
                f"Output: {output_path}"
            )
            
            if self.config.verbose:
                self._print_translation_summary(entries, translated_entries, elapsed_time)
                
        except Exception as e:
            self.logger.error(f"Translation failed: {e}")
            raise
    
    def _translate_entries(self, entries: List[SubtitleEntry]) -> List[SubtitleEntry]:
        """
        Translate all subtitle entries with context awareness.
        
        Args:
            entries: List of original subtitle entries
            
        Returns:
            List of translated subtitle entries
        """
        translated_entries = []
        total_entries = len(entries)
        
        for i, entry in enumerate(entries):
            if self.config.verbose:
                progress = (i + 1) / total_entries * 100
                print(f"\rTranslating: {progress:.1f}% ({i + 1}/{total_entries})", end="", flush=True)
            
            # Get context for better translation
            context = self._get_translation_context(entries, i) if self.config.context_window > 0 else None
            
            # Translate the text
            try:
                translated_text = self.ollama_client.translate_with_retry(
                    entry.text, 
                    context
                )
                
                # Create translated entry
                translated_entry = SubtitleEntry(
                    index=entry.index,
                    start_time=entry.start_time,
                    end_time=entry.end_time,
                    text=translated_text,
                    original_text=entry.text
                )
                
                translated_entries.append(translated_entry)
                
            except Exception as e:
                self.logger.error(f"Failed to translate entry {entry.index}: {e}")
                # Keep original entry as fallback
                translated_entries.append(entry)
        
        if self.config.verbose:
            print()  # New line after progress indicator
        
        return translated_entries
    
    def _get_translation_context(self, entries: List[SubtitleEntry], current_index: int) -> Optional[str]:
        """
        Get context for translation from surrounding entries.
        
        Args:
            entries: All subtitle entries
            current_index: Index of current entry being translated
            
        Returns:
            Context string or None
        """
        if self.config.context_window <= 0:
            return None
        
        context_parts = []
        
        # Add previous entries for context
        start_idx = max(0, current_index - self.config.context_window)
        for i in range(start_idx, current_index):
            context_parts.append(f"Previous: {entries[i].text}")
        
        # Add next entries for context
        end_idx = min(len(entries), current_index + self.config.context_window + 1)
        for i in range(current_index + 1, end_idx):
            context_parts.append(f"Following: {entries[i].text}")
        
        return "\n".join(context_parts) if context_parts else None
    
    def _print_translation_summary(self, original: List[SubtitleEntry], translated: List[SubtitleEntry], elapsed_time: float):
        """Print summary of translation process."""
        print("\n" + "="*50)
        print("TRANSLATION SUMMARY")
        print("="*50)
        print(f"Entries processed: {len(original)}")
        print(f"Time elapsed: {elapsed_time:.1f} seconds")
        print(f"Average per entry: {elapsed_time/len(original):.2f} seconds")
        print(f"Source language: {self.config.get_language_name(self.config.source_lang)}")
        print(f"Target language: {self.config.get_language_name(self.config.target_lang)}")
        print(f"Model used: {self.config.model}")
        
        # Show some example translations
        print("\nEXAMPLE TRANSLATIONS:")
        print("-" * 50)
        for i in range(min(3, len(original))):
            print(f"Original:  {original[i].text}")
            print(f"Translated: {translated[i].text}")
            print()
    
    def batch_translate(self, input_dir: Path, output_dir: Path, pattern: str = "*.srt") -> None:
        """
        Translate multiple SRT files in a directory.
        
        Args:
            input_dir: Directory containing input SRT files
            output_dir: Directory for output files
            pattern: File pattern to match (default: *.srt)
        """
        input_files = list(input_dir.glob(pattern))
        
        if not input_files:
            self.logger.warning(f"No files matching '{pattern}' found in {input_dir}")
            return
        
        self.logger.info(f"Starting batch translation of {len(input_files)} files")
        
        for i, input_file in enumerate(input_files, 1):
            self.logger.info(f"Processing file {i}/{len(input_files)}: {input_file.name}")
            
            # Generate output filename
            output_file = output_dir / f"{input_file.stem}.{self.config.target_lang}.srt"
            
            try:
                self.translate_file(input_file, output_file)
            except Exception as e:
                self.logger.error(f"Failed to translate {input_file}: {e}")
                continue
        
        self.logger.info("Batch translation completed")
    
    def validate_setup(self) -> bool:
        """
        Validate that the translator is properly set up.
        
        Returns:
            True if setup is valid, False otherwise
        """
        try:
            # Check Ollama connection
            if not self.ollama_client.is_available():
                print("❌ Ollama service is not available")
                return False
            
            # Check if model is available
            available_models = self.ollama_client.get_available_models()
            if self.config.model not in available_models:
                print(f"❌ Model '{self.config.model}' is not available")
                print(f"Available models: {available_models}")
                return False
            
            print("✅ Ollama connection: OK")
            print(f"✅ Model '{self.config.model}': Available")
            print(f"✅ Translation: {self.config.source_lang} -> {self.config.target_lang}")
            
            return True
            
        except Exception as e:
            print(f"❌ Validation failed: {e}")
            return False
