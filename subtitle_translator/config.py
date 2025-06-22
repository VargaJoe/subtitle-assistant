"""
Configuration module for subtitle translator.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Configuration settings for the subtitle translator."""
    
    source_lang: str = "en"
    target_lang: str = "hu"
    model: str = "llama3.2"
    verbose: bool = False
    context_window: int = 3  # Number of previous/next subtitles for context
    max_retries: int = 3
    temperature: float = 0.3  # Lower temperature for more consistent translations
    
    # Ollama connection settings
    ollama_host: str = "localhost"
    ollama_port: int = 11434
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.context_window < 0:
            raise ValueError("Context window must be non-negative")
        if self.max_retries < 1:
            raise ValueError("Max retries must be at least 1")
        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError("Temperature must be between 0.0 and 2.0")
    
    @property
    def ollama_url(self) -> str:
        """Get the full Ollama API URL."""
        return f"http://{self.ollama_host}:{self.ollama_port}"
    
    def get_language_name(self, code: str) -> str:
        """Get human-readable language name from code."""
        languages = {
            "en": "English",
            "hu": "Hungarian",
            "de": "German",
            "fr": "French",
            "es": "Spanish",
            "it": "Italian"
        }
        return languages.get(code.lower(), code.upper())
