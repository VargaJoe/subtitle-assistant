"""
MarianMT client for neural translation services using Hugging Face transformers.
"""

import logging
import torch
from typing import List, Optional, Dict, Any
from pathlib import Path

try:
    from transformers import MarianMTModel, MarianTokenizer
    import torch
    try:
        from transformers.utils import is_torch_available
    except ImportError:
        # Fallback for older transformers versions
        def is_torch_available():
            return torch is not None
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    MarianMTModel = None
    MarianTokenizer = None
    torch = None
    def is_torch_available():
        return False

from .config import Config


class MarianClient:
    """Client for MarianMT neural translation using Hugging Face transformers."""
    
    def __init__(self, config: Config):
        """Initialize MarianMT client with configuration."""
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "Transformers library is not available. Install with: pip install transformers torch"
            )
        
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Device configuration (GPU if available, otherwise CPU)
        if torch is not None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            if self.device == "cuda":
                self.logger.info(f"Using GPU: {torch.cuda.get_device_name()}")
            else:
                self.logger.info("Using CPU for translation")
        else:
            self.device = "cpu"
            self.logger.info("PyTorch not available, using CPU")
        
        # Model configuration
        self.model_name = self._get_model_name()
        self.model = None
        self.tokenizer = None
        
        # Load model and tokenizer
        self._load_model()
    
    def _get_model_name(self) -> str:
        """Get the appropriate MarianMT model name based on language configuration."""
        source_lang = self.config.source_lang.lower()
        target_lang = self.config.target_lang.lower()
        
        # Mapping of language pairs to MarianMT model names
        model_mapping = {
            ("en", "hu"): "Helsinki-NLP/opus-mt-en-hu",  # Use Helsinki-NLP instead of NYTK
            ("hu", "en"): "Helsinki-NLP/opus-mt-hu-en", 
            ("en", "de"): "Helsinki-NLP/opus-mt-en-de",
            ("de", "en"): "Helsinki-NLP/opus-mt-de-en",
            ("en", "fr"): "Helsinki-NLP/opus-mt-en-fr",
            ("fr", "en"): "Helsinki-NLP/opus-mt-fr-en",
            ("en", "es"): "Helsinki-NLP/opus-mt-en-es",
            ("es", "en"): "Helsinki-NLP/opus-mt-es-en",
        }
        
        lang_pair = (source_lang, target_lang)
        if lang_pair in model_mapping:
            return model_mapping[lang_pair]
        else:
            # Default fallback for unsupported language pairs
            raise ValueError(
                f"Language pair {source_lang}->{target_lang} is not supported by MarianMT. "
                f"Supported pairs: {list(model_mapping.keys())}"
            )
    
    def _load_model(self):
        """Load the MarianMT model and tokenizer."""
        try:
            self.logger.info(f"Loading MarianMT model: {self.model_name}")
            
            # Load tokenizer
            self.tokenizer = MarianTokenizer.from_pretrained(
                self.model_name,
                cache_dir=self._get_cache_dir()
            )
            
            # Load model
            self.model = MarianMTModel.from_pretrained(
                self.model_name,
                cache_dir=self._get_cache_dir()
            )
            
            # Move model to device (GPU/CPU)
            self.model = self.model.to(self.device)
            
            # Set model to evaluation mode
            self.model.eval()
            
            self.logger.info(f"MarianMT model loaded successfully on {self.device}")
            
        except Exception as e:
            self.logger.error(f"Failed to load MarianMT model: {e}")
            raise ConnectionError(f"Cannot load MarianMT model '{self.model_name}': {e}")
    
    def _get_cache_dir(self) -> Path:
        """Get cache directory for model files."""
        cache_dir = Path.home() / ".cache" / "subtitle-translator" / "marianmt"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    
    def is_available(self) -> bool:
        """Check if MarianMT service is available."""
        try:
            return (
                TRANSFORMERS_AVAILABLE and 
                self.model is not None and 
                self.tokenizer is not None and
                is_torch_available()
            )
        except Exception:
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available MarianMT models."""
        # Return the current model if available
        if self.is_available():
            return [self.model_name]
        else:
            return []
    
    def translate_text(self, text: str, context: Optional[str] = None) -> str:
        """
        Translate text using MarianMT.
        
        Args:
            text: Text to translate
            context: Optional context (not used in MarianMT but kept for compatibility)
            
        Returns:
            Translated text
            
        Raises:
            ConnectionError: If MarianMT service is not available
            ValueError: If translation fails
        """
        if not self.is_available():
            raise ConnectionError("MarianMT service is not available")
        
        if not text.strip():
            return text
        
        try:
            # Handle multi-line text based on configuration strategy
            lines = text.split('\n')
            if len(lines) > 1:
                strategy = self.config.marian.multiline_strategy
                
                if strategy == "join_all":
                    # Always join all lines into single sentence
                    combined_text = ' '.join(line.strip() for line in lines if line.strip())
                    translated_text = self._translate_single_line(combined_text)
                    
                elif strategy == "preserve_lines":
                    # Always keep line breaks (previous behavior)
                    translated_lines = []
                    for line in lines:
                        line = line.strip()
                        if line:  # Only translate non-empty lines
                            translated_line = self._translate_single_line(line)
                            translated_lines.append(translated_line)
                        else:
                            translated_lines.append('')  # Preserve empty lines
                    translated_text = '\n'.join(translated_lines)
                    
                else:  # strategy == "smart"
                    # Intelligently detect single sentences vs dialogue/multiple sentences
                    if self._should_join_lines(lines):
                        # Single sentence split across lines - join and translate
                        combined_text = ' '.join(line.strip() for line in lines if line.strip())
                        translated_text = self._translate_single_line(combined_text)
                    else:
                        # Multiple sentences or dialogue - translate separately
                        translated_lines = []
                        for line in lines:
                            line = line.strip()
                            if line:  # Only translate non-empty lines
                                translated_line = self._translate_single_line(line)
                                translated_lines.append(translated_line)
                            else:
                                translated_lines.append('')  # Preserve empty lines
                        translated_text = '\n'.join(translated_lines)
            else:
                # Single line text: translate normally
                translated_text = self._translate_single_line(text.strip())
            
            if self.config.verbose:
                self.logger.info(f"MarianMT translated: '{text}' -> '{translated_text}'")
            
            return translated_text
            
        except Exception as e:
            self.logger.error(f"MarianMT translation failed: {e}")
            raise ValueError(f"Translation failed: {e}")
    
    def _should_join_lines(self, lines: List[str]) -> bool:
        """
        Determine if lines should be joined as a single sentence or kept separate.
        
        Args:
            lines: List of text lines
            
        Returns:
            True if lines should be joined (single sentence), False if kept separate (dialogue/multiple sentences)
        """
        # Remove empty lines for analysis
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        
        if len(non_empty_lines) <= 1:
            return True  # Single line or empty, no need to join
        
        # Check for dialogue indicators
        dialogue_indicators = ['-', '—', '–', '•']
        for line in non_empty_lines:
            if any(line.startswith(indicator) for indicator in dialogue_indicators):
                return False  # Dialogue detected, keep separate
        
        # Check for multiple sentences (ending with sentence terminators)
        sentence_endings = ['.', '!', '?', '…']
        sentences_found = 0
        
        for line in non_empty_lines[:-1]:  # Don't check the last line
            if any(line.rstrip().endswith(ending) for ending in sentence_endings):
                sentences_found += 1
        
        if sentences_found > 0:
            return False  # Multiple sentences detected, keep separate
        
        # Check for specific patterns that indicate continuation
        continuation_patterns = [
            # First line ends with conjunction, preposition, or incomplete phrase
            lambda line: line.rstrip().split()[-1].lower() in ['and', 'or', 'but', 'that', 'which', 'who', 'when', 'where', 'how', 'why', 'because', 'since', 'while', 'if', 'unless', 'although', 'though', 'whereas', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'from', 'of', 'about'],
            # First line doesn't end with punctuation (incomplete sentence)
            lambda line: not any(line.rstrip().endswith(ending) for ending in sentence_endings + [',', ';', ':']),
            # Second line starts with lowercase (likely continuation)
            lambda line: len(line) > 0 and line[0].islower()
        ]
        
        first_line = non_empty_lines[0]
        second_line = non_empty_lines[1] if len(non_empty_lines) > 1 else ""
        
        # Check first line patterns
        for pattern in continuation_patterns[:-1]:
            if pattern(first_line):
                return True  # Likely continuation, join lines
        
        # Check second line pattern
        if second_line and continuation_patterns[-1](second_line):
            return True  # Likely continuation, join lines
        
        # Additional check: if first line is very short and doesn't end with punctuation
        if len(first_line.strip()) < 30 and not any(first_line.rstrip().endswith(ending) for ending in sentence_endings):
            return True  # Likely incomplete, join lines
        
        # Default: treat as separate sentences/lines
        return False
    
    def _translate_single_line(self, text: str) -> str:
        """
        Translate a single line of text using MarianMT.
        
        Args:
            text: Single line of text to translate
            
        Returns:
            Translated text
        """
        if not text.strip():
            return text
        
        # Prepare input text with special tokens if needed
        input_text = self._prepare_input_text(text)
        
        # Tokenize input
        inputs = self.tokenizer(
            input_text, 
            return_tensors="pt", 
            padding=True, 
            truncation=True,
            max_length=512
        )
        
        # Move inputs to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Generate translation
        with torch.no_grad():
            translated_tokens = self.model.generate(
                **inputs,
                max_new_tokens=128,  # Limit new tokens instead of total length
                min_length=1,
                num_beams=2,  # Reduced beam size for faster, more focused translation
                length_penalty=1.0,  # Neutral length penalty
                no_repeat_ngram_size=3,  # Prevent repetition of 3-grams
                repetition_penalty=1.2,  # Penalize repetition
                early_stopping=True,
                pad_token_id=self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None else self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
        
        # Decode translation
        translated_text = self.tokenizer.decode(
            translated_tokens[0], 
            skip_special_tokens=True
        )
        
        # Clean up the translation
        translated_text = self._clean_translation(translated_text)
        
        return translated_text
    
    def _prepare_input_text(self, text: str) -> str:
        """Prepare input text for MarianMT (language-specific preprocessing)."""
        # For most MarianMT models, no special preprocessing is needed
        # But we can add language-specific handling here if needed
        return text.strip()
    
    def _clean_translation(self, text: str) -> str:
        """Clean up translation response."""
        text = text.strip()
        
        # Remove any artifacts that might be added by the model
        # MarianMT typically produces clean output, but we can add cleanup here if needed
        
        return text
    
    def translate_with_retry(self, text: str, context: Optional[str] = None) -> str:
        """
        Translate text with retry logic.
        
        Args:
            text: Text to translate
            context: Optional context
            
        Returns:
            Translated text
            
        Raises:
            ValueError: If all retries fail
        """
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                return self.translate_text(text, context)
            except (ConnectionError, ValueError) as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    self.logger.warning(f"MarianMT translation attempt {attempt + 1} failed: {e}")
                    continue
                break
        
        raise ValueError(f"MarianMT translation failed after {self.config.max_retries} attempts: {last_error}")
    
    def translate_with_fallback(self, text: str, context: Optional[str] = None) -> str:
        """
        Translate text with fallback (MarianMT doesn't have multiple models to fallback to).
        
        Args:
            text: Text to translate
            context: Optional context
            
        Returns:
            Translated text
            
        Raises:
            ValueError: If translation fails
        """
        # For MarianMT, we just use retry logic since there's typically only one model per language pair
        return self.translate_with_retry(text, context)
    
    def translate_batch(self, texts: List[str], context: Optional[str] = None) -> List[str]:
        """
        Translate multiple texts in batch for better performance.
        
        Args:
            texts: List of texts to translate
            context: Optional context (not used in MarianMT but kept for compatibility)
            
        Returns:
            List of translated texts
        """
        if not texts:
            return []
        
        if not self.is_available():
            raise ConnectionError("MarianMT service is not available")
        
        try:
            # Handle multi-line texts using the same strategy as translate_text
            result = []
            for text in texts:
                if not text.strip():
                    result.append(text)
                    continue
                
                # Use the same multi-line handling as translate_text
                lines = text.split('\n')
                if len(lines) > 1:
                    strategy = self.config.marian.multiline_strategy
                    
                    if strategy == "join_all":
                        # Always join all lines into single sentence
                        combined_text = ' '.join(line.strip() for line in lines if line.strip())
                        translated_text = self._translate_single_line(combined_text)
                        
                    elif strategy == "preserve_lines":
                        # Always keep line breaks
                        translated_lines = []
                        for line in lines:
                            line = line.strip()
                            if line:  # Only translate non-empty lines
                                translated_line = self._translate_single_line(line)
                                translated_lines.append(translated_line)
                            else:
                                translated_lines.append('')  # Preserve empty lines
                        translated_text = '\n'.join(translated_lines)
                        
                    else:  # strategy == "smart"
                        # Intelligently detect single sentences vs dialogue/multiple sentences
                        if self._should_join_lines(lines):
                            # Single sentence split across lines - join and translate
                            combined_text = ' '.join(line.strip() for line in lines if line.strip())
                            translated_text = self._translate_single_line(combined_text)
                        else:
                            # Multiple sentences or dialogue - translate separately
                            translated_lines = []
                            for line in lines:
                                line = line.strip()
                                if line:  # Only translate non-empty lines
                                    translated_line = self._translate_single_line(line)
                                    translated_lines.append(translated_line)
                                else:
                                    translated_lines.append('')  # Preserve empty lines
                            translated_text = '\n'.join(translated_lines)
                else:
                    # Single line text: translate normally
                    translated_text = self._translate_single_line(text.strip())
                
                result.append(translated_text)
            
            if self.config.verbose:
                self.logger.info(f"MarianMT batch translated {len([t for t in texts if t.strip()])} texts")
            
            return result
            
        except Exception as e:
            self.logger.error(f"MarianMT batch translation failed: {e}")
            raise ValueError(f"Batch translation failed: {e}")
    
    def translate_whole_file(self, file_content: str) -> str:
        """
        Translate entire file content (delegates to batch processing).
        
        Args:
            file_content: Complete file content to translate
            
        Returns:
            Translated file content
        """
        # Split file content into lines and process as batch
        lines = file_content.strip().split('\n')
        
        # Extract text from numbered format: [1] text -> text
        texts_to_translate = []
        for line in lines:
            line = line.strip()
            if line.startswith('[') and ']' in line:
                # Remove index: [1] text -> text
                bracket_end = line.find(']')
                if bracket_end != -1:
                    text = line[bracket_end + 1:].strip()
                    texts_to_translate.append(text)
                else:
                    texts_to_translate.append(line)
            else:
                texts_to_translate.append(line)
        
        # Translate all texts in batch
        translated_texts = self.translate_batch(texts_to_translate)
        
        # Rebuild file content with original numbering
        result_lines = []
        for i, (original_line, translated_text) in enumerate(zip(lines, translated_texts)):
            original_line = original_line.strip()
            if original_line.startswith('[') and ']' in original_line:
                # Keep original numbering: [1] translated_text
                bracket_end = original_line.find(']')
                if bracket_end != -1:
                    index_part = original_line[:bracket_end + 1]
                    result_lines.append(f"{index_part} {translated_text}")
                else:
                    result_lines.append(translated_text)
            else:
                result_lines.append(translated_text)
        
        return '\n'.join(result_lines)
    
    def query_model(self, prompt: str, temperature: float = 0.3) -> str:
        """
        MarianMT models are translation-specific and don't support general queries.
        This method is kept for compatibility but will raise NotImplementedError.
        
        Args:
            prompt: The prompt to send to the model
            temperature: Temperature for the model response (not used)
            
        Raises:
            NotImplementedError: MarianMT doesn't support general queries
        """
        raise NotImplementedError(
            "MarianMT models are specialized for translation and don't support general queries. "
            "Use Ollama backend for multi-model pipeline features."
        )
