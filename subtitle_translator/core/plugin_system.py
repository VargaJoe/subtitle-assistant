"""
Plugin System for Translation Providers

Inspired by comic-bridge's modular plugin architecture, this system provides
extensible translation provider support with auto-discovery and factory patterns.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProviderCapabilities:
    """Capabilities and metadata for a translation provider."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    supported_languages: Optional[List[str]] = None
    requires_gpu: bool = False
    batch_processing: bool = True
    context_window_support: bool = True
    multi_model_support: bool = False

    def __post_init__(self):
        if self.supported_languages is None:
            self.supported_languages = ["en", "hu"]  # Default English-Hungarian


class BaseTranslationProvider(ABC):
    """Abstract base class for all translation providers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        """Return provider capabilities and metadata."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and properly configured."""
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Return list of available models for this provider."""
        pass

    @abstractmethod
    def translate_with_retry(self, text: str, context: Optional[str] = None) -> str:
        """Translate text with retry logic."""
        pass

    @abstractmethod
    def translate_with_fallback(self, text: str, context: Optional[str] = None) -> str:
        """Translate text with fallback models if primary fails."""
        pass

    @abstractmethod
    def translate_batch(self, texts: List[str], context: Optional[str] = None) -> List[str]:
        """Translate multiple texts in batch."""
        pass

    @abstractmethod
    def translate_whole_file(self, content: str) -> str:
        """Translate entire file content."""
        pass

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate provider configuration. Override in subclasses."""
        return True


class TranslationProviderRegistry:
    """Singleton registry for translation providers."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._providers = {}
        return cls._instance

    def register_provider(self, name: str, provider_class: Type[BaseTranslationProvider]):
        """Register a translation provider."""
        self._providers[name] = provider_class
        logger.debug(f"Registered translation provider: {name}")

    def get_provider(self, name: str, config: Dict[str, Any]) -> BaseTranslationProvider:
        """Get a provider instance by name."""
        if name not in self._providers:
            available = list(self._providers.keys())
            raise ValueError(f"Unknown translation provider '{name}'. Available: {available}")

        provider_class = self._providers[name]
        return provider_class(config)

    def list_providers(self) -> List[str]:
        """List all registered provider names."""
        return list(self._providers.keys())

    def get_provider_class(self, name: str) -> Type[BaseTranslationProvider]:
        """Get provider class by name."""
        return self._providers[name]


# Global registry instance
registry = TranslationProviderRegistry()


def translation_provider(name: str):
    """Decorator to register a translation provider."""
    def decorator(cls: Type[BaseTranslationProvider]):
        registry.register_provider(name, cls)
        return cls
    return decorator