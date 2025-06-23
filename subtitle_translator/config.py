"""
Configuration module for subtitle translator.
"""

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any


@dataclass
class ToneSettings:
    """Settings for translation tone and style."""
    formality: str = "auto"  # "formal", "informal", "auto"
    style: str = "natural"   # "natural", "literal", "creative"
    preserve_timing: bool = True
    
    
@dataclass
class HungarianSettings:
    """Hungarian-specific translation settings."""
    use_informal_when_appropriate: bool = True
    preserve_english_names: bool = True
    handle_contractions: bool = True


@dataclass
class Config:
    """Configuration settings for the subtitle translator."""
    
    # Basic translation settings
    source_lang: str = "en"
    target_lang: str = "hu"
    model: str = "jobautomation/OpenEuroLLM-Hungarian:latest"
    fallback_models: List[str] = field(default_factory=lambda: ["llama3.2", "llama3.1", "mistral"])
    verbose: bool = False
    
    # Translation quality settings
    context_window: int = 3
    max_retries: int = 3
    temperature: float = 0.3
    
    # Ollama connection settings
    ollama_host: str = "localhost"
    ollama_port: int = 11434
    ollama_timeout: int = 30
    
    # Tone and style settings
    tone: ToneSettings = field(default_factory=ToneSettings)
    hungarian: HungarianSettings = field(default_factory=HungarianSettings)
      # Processing settings
    translation_mode: str = "line-by-line"  # "line-by-line", "batch", "whole-file"
    batch_size: int = 10
    progress_display: bool = True
    backup_original: bool = True
    resume_enabled: bool = True
    
    # Output settings
    output_suffix: str = "{target_lang}"
    output_encoding: str = "utf-8"
    preserve_formatting: bool = True    def __post_init__(self):
        """Validate configuration after initialization."""
        # Ensure nested objects are properly initialized
        if not isinstance(self.tone, ToneSettings):
            self.tone = ToneSettings()
        if not isinstance(self.hungarian, HungarianSettings):
            self.hungarian = HungarianSettings()
            
        if self.context_window < 0:
            raise ValueError("Context window must be non-negative")
        if self.max_retries < 1:
            raise ValueError("Max retries must be at least 1")
        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError("Temperature must be between 0.0 and 2.0")
        if self.tone.formality not in ["formal", "informal", "auto"]:
            raise ValueError("Formality must be 'formal', 'informal', or 'auto'")
        if self.tone.style not in ["natural", "literal", "creative"]:
            raise ValueError("Style must be 'natural', 'literal', or 'creative'")
        if self.translation_mode not in ["line-by-line", "batch", "whole-file"]:
            raise ValueError("Translation mode must be 'line-by-line', 'batch', or 'whole-file'")
        if self.batch_size < 1:
            raise ValueError("Batch size must be at least 1")
    
    @classmethod
    def from_yaml(cls, config_path: Path) -> 'Config':
        """Load configuration from YAML file."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create Config from dictionary."""
        # Extract nested settings
        translation = data.get('translation', {})
        ollama = data.get('ollama', {})
        processing = data.get('processing', {})
        output = data.get('output', {})
        tone_data = translation.get('tone', {})
        hungarian_data = translation.get('hungarian', {})
        
        # Create tone and Hungarian settings
        tone = ToneSettings(
            formality=tone_data.get('formality', 'auto'),
            style=tone_data.get('style', 'natural'),
            preserve_timing=tone_data.get('preserve_timing', True)
        )
        
        hungarian = HungarianSettings(
            use_informal_when_appropriate=hungarian_data.get('use_informal_when_appropriate', True),
            preserve_english_names=hungarian_data.get('preserve_english_names', True),
            handle_contractions=hungarian_data.get('handle_contractions', True)
        )
          return cls(
            source_lang=translation.get('source_language', 'en'),
            target_lang=translation.get('target_language', 'hu'),
            model=translation.get('model', 'jobautomation/OpenEuroLLM-Hungarian:latest'),
            fallback_models=translation.get('fallback_models', ['llama3.2', 'llama3.1', 'mistral']),
            context_window=translation.get('context_window', 3),
            max_retries=translation.get('max_retries', 3),
            temperature=translation.get('temperature', 0.3),
            ollama_host=ollama.get('host', 'localhost'),
            ollama_port=ollama.get('port', 11434),
            ollama_timeout=ollama.get('timeout', 30),
            tone=tone,
            hungarian=hungarian,
            translation_mode=processing.get('translation_mode', 'line-by-line'),
            batch_size=processing.get('batch_size', 10),
            progress_display=processing.get('progress_display', True),
            backup_original=processing.get('backup_original', True),
            resume_enabled=processing.get('resume_enabled', True),
            output_suffix=output.get('suffix', '{target_lang}'),
            output_encoding=output.get('encoding', 'utf-8'),
            preserve_formatting=output.get('preserve_formatting', True)
        )
    
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
    
    def get_output_filename(self, input_path: Path) -> Path:
        """Generate output filename based on configuration."""
        suffix = self.output_suffix.format(target_lang=self.target_lang)
        return input_path.with_suffix(f".{suffix}.srt")
    
    def get_formality_instruction(self) -> str:
        """Get formality instruction for translation prompts."""
        if self.tone.formality == "formal":
            return "Use formal language (magázó forms in Hungarian)"
        elif self.tone.formality == "informal":
            return "Use informal, casual language (tegező forms in Hungarian)"
        else:  # auto
            return "Detect the appropriate formality level from context and use it consistently"
