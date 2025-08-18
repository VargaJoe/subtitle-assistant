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
class MarianSettings:
    """MarianMT-specific translation settings."""
    model: str = "Helsinki-NLP/opus-mt-en-hu"
    max_new_tokens: int = 128
    repetition_penalty: float = 1.2
    no_repeat_ngram_size: int = 3
    device: str = "auto"  # "auto", "cuda", "cpu"
    
    # Multi-line handling strategy
    multiline_strategy: str = "smart"  # "smart", "preserve_lines", "join_all"
    # smart: Intelligently detect single sentences vs dialogue
    # preserve_lines: Always keep line breaks (previous behavior)
    # join_all: Always join all lines into single sentence
    
    # Cross-entry sentence detection
    cross_entry_detection: bool = True  # Detect sentences spanning multiple subtitle entries
    # Only active when multiline_strategy is "smart"


@dataclass
class ModelSettings:
    """Settings for individual models in multi-model architecture."""
    model: str = "gemma3:latest"
    temperature: float = 0.3
    
    
@dataclass
class ContextModelSettings(ModelSettings):
    """Settings for the Context Model."""
    temperature: float = 0.2
    analyze_full_story: bool = True
    character_profiling: bool = True
    formality_detection: bool = True
    context_window: int = 15  # Number of entries to analyze for context
    prompt_template: str = ""  # Custom prompt template for context analysis
    

@dataclass
class TranslationModelSettings(ModelSettings):
    """Settings for the Translation Model."""
    temperature: float = 0.3
    use_context_analysis: bool = True
    cultural_adaptation: bool = True
    prompt_template: str = ""  # Custom prompt template for translation
    

@dataclass
class TechnicalValidatorSettings(ModelSettings):
    """Settings for the Technical Validator."""
    temperature: float = 0.1
    grammar_check: bool = True
    naturalness_score: bool = True
    quality_threshold: float = 0.7
    prompt_template: str = ""  # Custom prompt template for validation
    

@dataclass
class DialogueSpecialistSettings(ModelSettings):
    """Settings for the Dialogue Specialist."""
    temperature: float = 0.25
    voice_consistency: bool = True
    emotional_tone: bool = True
    formality_adjustment: bool = True
    prompt_template: str = ""  # Custom prompt template for dialogue refinement
    

@dataclass
class MultiModelPipelineSettings:
    """Settings for the multi-model pipeline."""
    parallel_processing: bool = False
    quality_consensus: bool = True
    fallback_to_single: bool = True
    skip_validation_for_high_confidence: bool = False
    skip_dialogue_refinement: bool = False
    
    # Step selection - which steps to run
    run_context_analysis: bool = True     # Step 01: Story understanding
    run_translation: bool = True          # Step 02: Primary translation  
    run_validation: bool = True           # Step 03: Quality validation
    run_dialogue_refinement: bool = True  # Step 04: Dialogue polishing
    

@dataclass
class MultiModelSettings:
    """Multi-model architecture settings."""
    enabled: bool = False
    context_model: ContextModelSettings = field(default_factory=ContextModelSettings)
    translation_model: TranslationModelSettings = field(default_factory=TranslationModelSettings)
    technical_validator: TechnicalValidatorSettings = field(default_factory=TechnicalValidatorSettings)
    dialogue_specialist: DialogueSpecialistSettings = field(default_factory=DialogueSpecialistSettings)
    pipeline: MultiModelPipelineSettings = field(default_factory=MultiModelPipelineSettings)
    

@dataclass
class Config:
    """Configuration settings for the subtitle translator."""
    
    # Backend selection
    translation_backend: str = "ollama"  # "ollama" or "marian"
    
    # Basic translation settings
    source_lang: str = "en"
    target_lang: str = "hu"
    model: str = "cogito:14b" #"gemma3n:latest"
    fallback_models: List[str] = field(default_factory=lambda: ["gemma3:latest", "llama3.2", "llama3.1", "jobautomation/OpenEuroLLM-Hungarian:latest", "mistral"])
    verbose: bool = False
    
    # Translation quality settings
    context_window: int = 3
    max_retries: int = 3
    temperature: float = 0.3
    
    # Ollama connection settings
    ollama_host: str = "localhost"
    ollama_port: int = 11434
    ollama_timeout: int = 30
    
    # MarianMT settings
    marian: MarianSettings = field(default_factory=MarianSettings)
    
    # Tone and style settings
    tone: ToneSettings = field(default_factory=ToneSettings)
    hungarian: HungarianSettings = field(default_factory=HungarianSettings)
    multi_model: MultiModelSettings = field(default_factory=MultiModelSettings)
    
    # Processing settings
    translation_mode: str = "line-by-line"  # "line-by-line", "batch", "whole-file"
    batch_size: int = 10
    overlap_size: int = 2  # Number of entries to overlap between batches
    reassess_overlaps: bool = True  # Allow reassessment of previous translations
    progress_display: bool = True
    backup_original: bool = True
    resume_enabled: bool = True
    
    # Output settings
    output_suffix: str = "{target_lang}"
    output_encoding: str = "utf-8"
    preserve_formatting: bool = True
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        # Ensure nested objects are properly initialized
        if not isinstance(self.tone, ToneSettings):
            self.tone = ToneSettings()
        if not isinstance(self.hungarian, HungarianSettings):
            self.hungarian = HungarianSettings()
        if not isinstance(self.marian, MarianSettings):
            self.marian = MarianSettings()
        if not isinstance(self.multi_model, MultiModelSettings):
            self.multi_model = MultiModelSettings()
            
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
        if self.translation_mode not in ["line-by-line", "batch", "whole-file", "multi-model"]:
            raise ValueError("Translation mode must be 'line-by-line', 'batch', 'whole-file', or 'multi-model'")
        if self.translation_backend not in ["ollama", "marian"]:
            raise ValueError("Translation backend must be 'ollama' or 'marian'")
        if self.batch_size < 1:
            raise ValueError("Batch size must be at least 1")
        if self.overlap_size < 0:
            raise ValueError("Overlap size must be non-negative")
        if self.overlap_size >= self.batch_size:
            raise ValueError("Overlap size must be smaller than batch size")
        if self.marian.multiline_strategy not in ["smart", "preserve_lines", "join_all"]:
            raise ValueError("MarianMT multiline strategy must be 'smart', 'preserve_lines', or 'join_all'")
    
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
        multi_model_data = data.get('multi_model', {})  # Multi-model is at root level
        
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
        
        # Create MarianMT settings
        marian_data = data.get('marian', {})
        marian = MarianSettings(
            model=marian_data.get('model', 'Helsinki-NLP/opus-mt-en-hu'),
            max_new_tokens=marian_data.get('max_new_tokens', 128),
            repetition_penalty=marian_data.get('repetition_penalty', 1.2),
            no_repeat_ngram_size=marian_data.get('no_repeat_ngram_size', 3),
            device=marian_data.get('device', 'auto'),
            multiline_strategy=marian_data.get('multiline_strategy', 'smart'),
            cross_entry_detection=marian_data.get('cross_entry_detection', True)
        )
        
        multi_model = MultiModelSettings(
            enabled=multi_model_data.get('enabled', False),
            context_model=ContextModelSettings(
                model=multi_model_data.get('context_model', {}).get('model', 'llama3.2:latest'),
                temperature=multi_model_data.get('context_model', {}).get('temperature', 0.2),
                analyze_full_story=multi_model_data.get('context_model', {}).get('analyze_full_story', True),
                character_profiling=multi_model_data.get('context_model', {}).get('character_profiling', True),
                formality_detection=multi_model_data.get('context_model', {}).get('formality_detection', True),
                prompt_template=multi_model_data.get('context_model', {}).get('prompt_template', '')
            ),
            translation_model=TranslationModelSettings(
                model=multi_model_data.get('translation_model', {}).get('model', 'gemma3:latest'),
                temperature=multi_model_data.get('translation_model', {}).get('temperature', 0.3),
                use_context_analysis=multi_model_data.get('translation_model', {}).get('use_context_analysis', True),
                cultural_adaptation=multi_model_data.get('translation_model', {}).get('cultural_adaptation', True),
                prompt_template=multi_model_data.get('translation_model', {}).get('prompt_template', '')
            ),
            technical_validator=TechnicalValidatorSettings(
                model=multi_model_data.get('technical_validator', {}).get('model', 'gemma3:12b'),
                temperature=multi_model_data.get('technical_validator', {}).get('temperature', 0.1),
                grammar_check=multi_model_data.get('technical_validator', {}).get('grammar_check', True),
                naturalness_score=multi_model_data.get('technical_validator', {}).get('naturalness_score', True),
                quality_threshold=multi_model_data.get('technical_validator', {}).get('quality_threshold', 0.7),
                prompt_template=multi_model_data.get('technical_validator', {}).get('prompt_template', '')
            ),
            dialogue_specialist=DialogueSpecialistSettings(
                model=multi_model_data.get('dialogue_specialist', {}).get('model', 'llama3.2:latest'),
                temperature=multi_model_data.get('dialogue_specialist', {}).get('temperature', 0.25),
                voice_consistency=multi_model_data.get('dialogue_specialist', {}).get('voice_consistency', True),
                emotional_tone=multi_model_data.get('dialogue_specialist', {}).get('emotional_tone', True),
                formality_adjustment=multi_model_data.get('dialogue_specialist', {}).get('formality_adjustment', True),
                prompt_template=multi_model_data.get('dialogue_specialist', {}).get('prompt_template', '')
            ),
            pipeline=MultiModelPipelineSettings(
                parallel_processing=multi_model_data.get('pipeline', {}).get('parallel_processing', False),
                quality_consensus=multi_model_data.get('pipeline', {}).get('quality_consensus', True),
                fallback_to_single=multi_model_data.get('pipeline', {}).get('fallback_to_single', True),
                skip_validation_for_high_confidence=multi_model_data.get('pipeline', {}).get('skip_validation_for_high_confidence', False),
                skip_dialogue_refinement=multi_model_data.get('pipeline', {}).get('skip_dialogue_refinement', False)
            )
        )
        
        return cls(
            translation_backend=data.get('translation', {}).get('backend', 'ollama'),
            source_lang=translation.get('source_language', 'en'),
            target_lang=translation.get('target_language', 'hu'),
            model=translation.get('model', 'gemma3:12b'),
            fallback_models=translation.get('fallback_models', ['llama3.2', 'llama3.1', 'jobautomation/OpenEuroLLM-Hungarian:latest', 'mistral']),
            context_window=translation.get('context_window', 3),
            max_retries=translation.get('max_retries', 3),
            temperature=translation.get('temperature', 0.3),
            ollama_host=ollama.get('host', 'localhost'),
            ollama_port=ollama.get('port', 11434),
            ollama_timeout=ollama.get('timeout', 30),
            tone=tone,
            hungarian=hungarian,
            marian=marian,
            multi_model=multi_model,
            translation_mode=processing.get('translation_mode', 'line-by-line'),
            batch_size=processing.get('batch_size', 10),
            overlap_size=processing.get('overlap_size', 2),
            reassess_overlaps=processing.get('reassess_overlaps', True),
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
