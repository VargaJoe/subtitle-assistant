"""
MarianMT Translation Provider

Plugin-based wrapper for MarianClient that implements the BaseTranslationProvider interface.
"""

from typing import Dict, Any, List, Optional
import logging

from ..core.plugin_system import BaseTranslationProvider, ProviderCapabilities, translation_provider
from ..marian_client import MarianClient
from ..config import Config


@translation_provider("marian")
class MarianProvider(BaseTranslationProvider):
    """MarianMT-based translation provider."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Convert dict config to Config object for MarianClient
        self._config_obj = Config()
        # Set basic properties
        if "source_lang" in config:
            self._config_obj.source_lang = config["source_lang"]
        if "target_lang" in config:
            self._config_obj.target_lang = config["target_lang"]
        if "model" in config:
            self._config_obj.marian.model = config["model"]
        if "max_new_tokens" in config:
            self._config_obj.marian.max_new_tokens = config["max_new_tokens"]
        if "repetition_penalty" in config:
            self._config_obj.marian.repetition_penalty = config["repetition_penalty"]
        if "no_repeat_ngram_size" in config:
            self._config_obj.marian.no_repeat_ngram_size = config["no_repeat_ngram_size"]
        if "device" in config:
            self._config_obj.marian.device = config["device"]
        if "multiline_strategy" in config:
            self._config_obj.marian.multiline_strategy = config["multiline_strategy"]
        if "cross_entry_detection" in config:
            self._config_obj.marian.cross_entry_detection = config["cross_entry_detection"]
        if "max_retries" in config:
            self._config_obj.max_retries = config["max_retries"]
        if "verbose" in config:
            self._config_obj.verbose = config["verbose"]

        self._client = MarianClient(self._config_obj)

    def get_capabilities(self) -> ProviderCapabilities:
        """Return provider capabilities."""
        return ProviderCapabilities(
            name="MarianMT Neural Machine Translation",
            version="1.0.0",
            description="Fast offline translation using Helsinki-NLP MarianMT models",
            supported_languages=["en", "hu", "de", "fr", "es", "it", "pt", "ru", "zh"],
            requires_gpu=True,  # GPU highly recommended for performance
            batch_processing=True,
            context_window_support=False,  # MarianMT doesn't use context windows
            multi_model_support=False  # Single model architecture
        )

    def is_available(self) -> bool:
        """Check if MarianMT dependencies are available."""
        return self._client.is_available()

    def get_available_models(self) -> List[str]:
        """Return list of available models."""
        return self._client.get_available_models()

    def translate_with_retry(self, text: str, context: Optional[str] = None) -> str:
        """Translate text with retry logic."""
        # MarianMT doesn't use context, so ignore it
        return self._client.translate_with_retry(text)

    def translate_batch(self, texts: List[str], context: Optional[str] = None) -> List[str]:
        """Translate multiple texts in batch."""
        # MarianMT doesn't use context, so ignore it
        return self._client.translate_batch(texts)

    def translate_with_fallback(self, text: str, context: Optional[str] = None) -> str:
        """Translate text with fallback models if primary fails."""
        # MarianMT doesn't have fallback models, so just use retry
        return self._client.translate_with_retry(text)

    def translate_whole_file(self, content: str) -> str:
        """Translate entire file content."""
        # For MarianMT, whole file translation is the same as single text translation
        return self._client.translate_with_retry(content)

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate MarianMT configuration."""
        required_keys = ["source_lang", "target_lang"]
        for key in required_keys:
            if key not in config:
                self.logger.error(f"Missing required config key: {key}")
                return False
        return True