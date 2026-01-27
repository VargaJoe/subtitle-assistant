"""
Ollama Translation Provider

Plugin-based wrapper for OllamaClient that implements the BaseTranslationProvider interface.
"""

from typing import Dict, Any, List, Optional
import logging

from ..core.plugin_system import BaseTranslationProvider, ProviderCapabilities, translation_provider
from ..ollama_client import OllamaClient
from ..config import Config


@translation_provider("ollama")
class OllamaProvider(BaseTranslationProvider):
    """Ollama-based translation provider."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Convert dict config to Config object for OllamaClient
        self._config_obj = Config()
        # Set basic properties
        if "ollama_host" in config:
            self._config_obj.ollama_host = config["ollama_host"]
        if "ollama_port" in config:
            self._config_obj.ollama_port = config["ollama_port"]
        if "ollama_timeout" in config:
            self._config_obj.ollama_timeout = config["ollama_timeout"]
        if "model" in config:
            self._config_obj.model = config["model"]
        if "temperature" in config:
            self._config_obj.temperature = config["temperature"]
        if "source_lang" in config:
            self._config_obj.source_lang = config["source_lang"]
        if "target_lang" in config:
            self._config_obj.target_lang = config["target_lang"]
        if "fallback_models" in config:
            self._config_obj.fallback_models = config["fallback_models"]
        if "max_retries" in config:
            self._config_obj.max_retries = config["max_retries"]
        if "verbose" in config:
            self._config_obj.verbose = config["verbose"]

        self._client = OllamaClient(self._config_obj)

    def get_capabilities(self) -> ProviderCapabilities:
        """Return provider capabilities."""
        return ProviderCapabilities(
            name="Ollama AI Service",
            version="1.0.0",
            description="Local AI models via Ollama service with multi-model support",
            supported_languages=["en", "hu", "de", "fr", "es", "it", "pt", "ru", "ja", "ko", "zh"],
            requires_gpu=False,  # Can run on CPU, but GPU preferred
            batch_processing=True,
            context_window_support=True,
            multi_model_support=True
        )

    def is_available(self) -> bool:
        """Check if Ollama service is available."""
        return self._client.is_available()

    def get_available_models(self) -> List[str]:
        """Return list of available models."""
        return self._client.get_available_models()

    def translate_with_retry(self, text: str, context: Optional[str] = None) -> str:
        """Translate text with retry logic."""
        return self._client.translate_with_retry(text, context)

    def translate_with_fallback(self, text: str, context: Optional[str] = None) -> str:
        """Translate text with fallback models if primary fails."""
        return self._client.translate_with_fallback(text, context)

    def translate_batch(self, texts: List[str], context: Optional[str] = None) -> List[str]:
        """Translate multiple texts in batch."""
        return self._client.translate_batch(texts, context)

    def translate_whole_file(self, content: str) -> str:
        """Translate entire file content."""
        return self._client.translate_whole_file(content)

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate Ollama configuration."""
        required_keys = ["ollama_host", "ollama_port", "model"]
        for key in required_keys:
            if key not in config:
                self.logger.error(f"Missing required config key: {key}")
                return False
        return True