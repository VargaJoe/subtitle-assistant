"""
Subtitle Translator Assistant Package
"""

__version__ = "0.1.0"
__author__ = "VargaJoe"
__description__ = "AI-powered subtitle translation tool for hearing-impaired users"

from importlib import import_module

# Keep the historical public imports without loading model SDKs for parser/tool use.
_EXPORTS = {
    "SubtitleTranslator": ".translator",
    "Config": ".config",
    "SRTParser": ".srt_parser",
    "SubtitleEntry": ".srt_parser",
    "OllamaClient": ".ollama_client",
    "MarianClient": ".marian_client",
}
__all__ = list(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(_EXPORTS[name], __name__), name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(_EXPORTS))
