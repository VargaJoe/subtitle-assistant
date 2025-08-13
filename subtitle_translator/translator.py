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
from .progress import TranslationProgress, ProgressMode
from .multi_model import MultiModelOrchestrator


class SubtitleTranslator:
    """Main translator class that orchestrates the translation process."""
    
    def __init__(self, config: Config):
        """Initialize translator with configuration."""
        self.config = config
        self.parser = SRTParser()
        self.ollama_client = OllamaClient(config)
        self.multi_model_orchestrator = MultiModelOrchestrator(config)
        
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
    
    def translate_file(self, input_path: Path, output_path: Path, resume: bool = True) -> None:
        """
        Translate a single SRT file with resume support.
        
        Args:
            input_path: Path to input SRT file
            output_path: Path to output translated SRT file
            resume: Whether to resume from existing progress
        """
        # Ensure paths are Path objects
        input_path = Path(input_path)
        output_path = Path(output_path)
        start_time = time.time()
        
        self.logger.info(f"Starting translation: {input_path} -> {output_path}")
        self.logger.info(f"Languages: {self.config.source_lang} -> {self.config.target_lang}")
        self.logger.info(f"Mode: {self.config.translation_mode}")
        
        # Initialize progress manager
        progress = TranslationProgress(input_path, output_path)
        
        try:
            # Parse input file
            entries = self.parser.parse_file(input_path)
            total_entries = len(entries)
            
            # Check for existing progress
            start_index = 0
            if resume and self.config.resume_enabled and progress.has_existing_progress():
                if progress.load_progress():
                    self.logger.info(progress.get_resume_summary())
                    start_index = progress.current_index
                    
                    # Validate that we have the expected number of entries
                    if progress.total_entries != total_entries:
                        self.logger.warning(
                            f"Entry count mismatch: progress file has {progress.total_entries}, "
                            f"current file has {total_entries}. Starting fresh."
                        )
                        start_index = 0
                        progress.translated_entries = []
                        progress.current_index = 0
                else:
                    self.logger.warning("Failed to load progress, starting fresh")
            
            # Initialize or update progress
            progress.initialize_translation(total_entries)
            
            if start_index == 0:
                self.logger.info(f"Starting fresh translation of {total_entries} subtitle entries")
            else:
                remaining = total_entries - start_index
                self.logger.info(f"Resuming translation: {remaining} entries remaining")
            
            # Translate entries based on mode
            if self.multi_model_orchestrator.is_enabled():
                # Use multi-model pipeline for the whole file
                progress.translated_entries = self.multi_model_orchestrator.translate_with_multimodel(entries, progress)
                progress.current_index = len(progress.translated_entries)
            elif self.config.translation_mode == ProgressMode.BATCH:
                progress.translated_entries.extend(
                    self._translate_entries_batch(entries[start_index:], progress, start_index)
                )
            elif self.config.translation_mode == ProgressMode.WHOLE_FILE:
                if start_index > 0:
                    self.logger.warning("Whole-file mode doesn't support resume, starting fresh")
                    start_index = 0
                    progress.translated_entries = []
                    progress.current_index = 0
                progress.translated_entries = self._translate_entries_whole_file(entries)
                progress.current_index = total_entries
            else:  # line-by-line (default)
                progress.translated_entries.extend(
                    self._translate_entries_line_by_line(entries[start_index:], progress, start_index)
                )
            
            # Write output file
            all_entries = progress.translated_entries
            if start_index > 0:
                # We already have some entries, just add the new ones
                # Note: progress.translated_entries should already contain all entries
                pass
                
            self.parser.write_file(all_entries, output_path)
            
            # Clean up progress file on successful completion
            if progress.is_complete():
                progress.cleanup_progress_file()
            
            # Report completion
            elapsed_time = time.time() - start_time
            self.logger.info(
                f"Translation completed in {elapsed_time:.1f} seconds. "
                f"Output: {output_path}"
            )
            
            if self.config.verbose:
                self._print_translation_summary(entries, all_entries, elapsed_time)
                
        except Exception as e:
            self.logger.error(f"Translation failed: {e}")
            # Save progress even on failure
            try:
                progress.save_progress()
                self.logger.info("Progress saved before exit")
            except Exception as save_error:
                self.logger.error(f"Failed to save progress: {save_error}")
            raise
    
    def _translate_entries_line_by_line(self, entries: List[SubtitleEntry], progress: TranslationProgress, start_offset: int = 0) -> List[SubtitleEntry]:
        """
        Translate subtitle entries one by one with progress tracking.
        
        Args:
            entries: List of subtitle entries to translate
            progress: Progress manager for saving state
            start_offset: Starting index offset for progress display
            
        Returns:
            List of translated subtitle entries
        """
        if self.multi_model_orchestrator.is_enabled():
            # Use multi-model pipeline for line-by-line mode as well
            return self.multi_model_orchestrator.translate_with_multimodel(entries, progress)
        
        translated_entries = []
        total_entries = len(entries)
        
        for i, entry in enumerate(entries):
            current_index = start_offset + i + 1
            total_with_offset = progress.total_entries
            
            if self.config.verbose:
                progress_pct = (current_index / total_with_offset) * 100
                print(f"\rTranslating: {progress_pct:.1f}% ({current_index}/{total_with_offset})", end="", flush=True)
            
            # Get context for better translation
            context = self._get_translation_context(entries, i) if self.config.context_window > 0 else None
            
            # Translate the text
            try:
                # First try with retry on the primary model
                translated_text = self.ollama_client.translate_with_retry(
                    entry.text, 
                    context
                )
                
            except Exception as e:
                self.logger.warning(f"Primary translation failed for entry {entry.index}, trying fallback models: {e}")
                try:
                    # Try fallback models if primary fails
                    translated_text = self.ollama_client.translate_with_fallback(
                        entry.text,
                        context
                    )
                except Exception as fallback_error:
                    self.logger.error(f"All translation attempts failed for entry {entry.index}: {fallback_error}")
                    # Keep original entry as fallback
                    translated_entries.append(entry)
                    # Still update progress
                    progress.add_translated_entry(entry)
                    continue
            
            # Create translated entry
            translated_entry = SubtitleEntry(
                index=entry.index,
                start_time=entry.start_time,
                end_time=entry.end_time,
                text=translated_text,
                original_text=entry.text
            )
            
            translated_entries.append(translated_entry)
            
            # Update progress (this will auto-save periodically)
            progress.add_translated_entry(translated_entry)
        
        if self.config.verbose:
            print()  # New line after progress indicator
        
        return translated_entries
    
    def _translate_entries_batch(self, entries: List[SubtitleEntry], progress: TranslationProgress, start_offset: int = 0) -> List[SubtitleEntry]:
        """
        Translate subtitle entries in batches for better performance.
        
        Args:
            entries: List of subtitle entries to translate
            progress: Progress manager for saving state
            start_offset: Starting index offset for progress display
            
        Returns:
            List of translated subtitle entries
        """
        translated_entries = []
        batch_size = self.config.batch_size
        overlap_size = self.config.overlap_size
        total_entries = len(entries)
        
        # Track which entries we've processed to avoid duplication
        processed_indices = set()
        
        batch_start = 0
        while batch_start < total_entries:
            batch_end = min(batch_start + batch_size, total_entries)
            
            # Determine overlap range
            overlap_start = max(0, batch_start - overlap_size) if batch_start > 0 else batch_start
            overlap_end = batch_end
            
            # Get entries for this batch (including overlap)
            full_batch = entries[overlap_start:overlap_end]
            overlap_entries = entries[overlap_start:batch_start] if batch_start > 0 else []
            new_entries = entries[batch_start:batch_end]
            
            current_index = start_offset + batch_end
            total_with_offset = progress.total_entries
            
            if self.config.verbose:
                progress_pct = (current_index / total_with_offset) * 100
                overlap_info = f" (overlap: {len(overlap_entries)})" if overlap_entries else ""
                print(f"\rTranslating batch: {progress_pct:.1f}% ({current_index}/{total_with_offset}){overlap_info}", end="", flush=True)
            
            # Prepare batch text for translation
            batch_texts = [entry.text for entry in full_batch]
            batch_context = self._get_batch_context(entries, overlap_start, len(full_batch))
            
            try:
                # Translate entire batch (including overlap for context)
                translated_texts = self.ollama_client.translate_batch(batch_texts, batch_context)
                
                # Process results: handle overlap and new entries differently
                for i, (entry, translated_text) in enumerate(zip(full_batch, translated_texts)):
                    entry_index = overlap_start + i
                    
                    # Create translated entry
                    translated_entry = SubtitleEntry(
                        index=entry.index,
                        start_time=entry.start_time,
                        end_time=entry.end_time,
                        text=translated_text,
                        original_text=entry.text
                    )
                    
                    if entry_index < batch_start:
                        # This is an overlap entry - reassess if enabled
                        if self.config.reassess_overlaps and entry_index in processed_indices:
                            # Find existing translation by entry index and potentially update it
                            for existing_idx, existing_entry in enumerate(translated_entries):
                                if existing_entry.index == entry.index:
                                    old_translation = existing_entry.text
                                    if translated_text != old_translation:
                                        self.logger.info(f"Reassessing entry {entry.index}: '{old_translation}' → '{translated_text}'")
                                        translated_entries[existing_idx] = translated_entry
                                    break
                    else:
                        # This is a new entry
                        if entry_index not in processed_indices:
                            translated_entries.append(translated_entry)
                            processed_indices.add(entry_index)
                            
                            # Update progress for new entries only
                            progress.add_translated_entry(translated_entry)
                    
            except Exception as e:
                self.logger.warning(f"Batch translation failed, falling back to line-by-line: {e}")
                # Fall back to line-by-line for new entries only (not overlaps)
                for i, entry in enumerate(new_entries):
                    entry_index = batch_start + i  # Define entry_index first
                    try:
                        context = self._get_translation_context(entries, entry_index)
                        translated_text = self.ollama_client.translate_with_retry(entry.text, context)
                        
                        translated_entry = SubtitleEntry(
                            index=entry.index,
                            start_time=entry.start_time,
                            end_time=entry.end_time,
                            text=translated_text,
                            original_text=entry.text
                        )
                        
                        if entry_index not in processed_indices:
                            translated_entries.append(translated_entry)
                            processed_indices.add(entry_index)
                            progress.add_translated_entry(translated_entry)
                        
                    except Exception as entry_error:
                        self.logger.error(f"Failed to translate entry {entry.index}: {entry_error}")
                        # Keep original as fallback
                        if entry_index not in processed_indices:
                            translated_entries.append(entry)
                            processed_indices.add(entry_index)
                            progress.add_translated_entry(entry)
            
            # Move to next batch (accounting for overlap)
            batch_start = batch_end
        
        if self.config.verbose:
            print()  # New line after progress indicator
        
        return translated_entries
    
    def _translate_entries_whole_file(self, entries: List[SubtitleEntry]) -> List[SubtitleEntry]:
        """
        Translate entire file in a single API call (experimental).
        
        Args:
            entries: List of all subtitle entries
            
        Returns:
            List of translated subtitle entries
        """
        if len(entries) > 50:
            self.logger.warning(
                f"Large file ({len(entries)} entries) may exceed token limits in whole-file mode. "
                "Consider using line-by-line or batch mode instead."
            )
        
        # Prepare entire file content
        file_content = []
        for entry in entries:
            file_content.append(f"[{entry.index}] {entry.text}")
        
        full_text = "\n".join(file_content)
        
        try:
            # Translate entire file
            translated_content = self.ollama_client.translate_whole_file(full_text)
            
            # Parse translated content back into entries
            translated_entries = self._parse_whole_file_translation(entries, translated_content)
            
            return translated_entries
            
        except Exception as e:
            self.logger.error(f"Whole-file translation failed: {e}")
            raise
    
    def _get_batch_context(self, entries: List[SubtitleEntry], batch_start: int, batch_size: int) -> Optional[str]:
        """Get context for batch translation."""
        if self.config.context_window <= 0:
            return None
        
        context_parts = []
        
        # Add context before batch
        context_start = max(0, batch_start - self.config.context_window)
        for i in range(context_start, batch_start):
            context_parts.append(f"Previous: {entries[i].text}")
        
        # Add context after batch
        batch_end = min(len(entries), batch_start + batch_size)
        context_end = min(len(entries), batch_end + self.config.context_window)
        for i in range(batch_end, context_end):
            context_parts.append(f"Following: {entries[i].text}")
        
        return "\n".join(context_parts) if context_parts else None
    
    def _parse_whole_file_translation(self, original_entries: List[SubtitleEntry], translated_content: str) -> List[SubtitleEntry]:
        """Parse whole-file translation back into individual entries."""
        translated_entries = []
        translated_lines = translated_content.strip().split('\n')
        
        # Try to match translated lines to original entries
        for i, entry in enumerate(original_entries):
            if i < len(translated_lines):
                # Remove index prefix if present: [1] text -> text
                translated_text = translated_lines[i]
                if translated_text.startswith(f"[{entry.index}]"):
                    translated_text = translated_text[len(f"[{entry.index}]"):].strip()
                
                translated_entry = SubtitleEntry(
                    index=entry.index,
                    start_time=entry.start_time,
                    end_time=entry.end_time,
                    text=translated_text,
                    original_text=entry.text
                )
                translated_entries.append(translated_entry)
            else:
                # Not enough translated lines, keep original
                self.logger.warning(f"Missing translation for entry {entry.index}")
                translated_entries.append(entry)
        
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
