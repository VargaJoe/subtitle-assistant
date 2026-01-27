"""
Core Plugin System Module

Provides the plugin architecture foundation with abstract interfaces,
provider registry, and auto-discovery system.
"""

from .plugin_system import (
    BaseTranslationProvider,
    ProviderCapabilities,
    TranslationProviderRegistry,
    registry,
    translation_provider
)
from .plugin_loader import discover_plugins, load_user_plugins, load_all_plugins

__all__ = [
    # Interfaces
    'BaseTranslationProvider',
    'ProviderCapabilities',

    # Registry
    'TranslationProviderRegistry',
    'registry',

    # Decorators
    'translation_provider',

    # Plugin Loader
    'discover_plugins',
    'load_user_plugins',
    'load_all_plugins',
]