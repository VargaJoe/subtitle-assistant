"""
Subtitle Translator Assistant Package
"""

__version__ = "0.1.0"
__author__ = "VargaJoe"
__description__ = "AI-powered subtitle translation tool for hearing-impaired users"

# Load all plugins when the package is imported
try:
    from .core.plugin_loader import load_all_plugins
    load_all_plugins()
except ImportError:
    # Plugins not available yet during early development
    pass

# Import main classes for easy access
from .translator import SubtitleTranslator
from .config import Config
from .srt_parser import SRTParser, SubtitleEntry
from .ollama_client import OllamaClient

# Conditionally import MarianClient if dependencies are available
try:
    from .marian_client import MarianClient
    __all__ = ['SubtitleTranslator', 'Config', 'SRTParser', 'SubtitleEntry', 'OllamaClient', 'MarianClient']
except ImportError:
    __all__ = ['SubtitleTranslator', 'Config', 'SRTParser', 'SubtitleEntry', 'OllamaClient']
