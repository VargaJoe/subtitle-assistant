"""
Multi-Model Orchestrator for Enhanced Translation Quality.

This module implements the revolutionary multi-model architecture that uses
specialized AI models for different aspects of translation:
- Context Model: Story understanding and character analysis
- Translation Model: Context-aware primary translation
- Technical Validator: Quality scoring and validation
- Dialogue Specialist: Character voice consistency
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from dataclasses import dataclass
from pathlib import Path

from .config import Config, MultiModelSettings
from .srt_parser import SubtitleEntry
from .ollama_client import OllamaClient
from .progress import TranslationProgress


@dataclass
class StoryContext:
    """Story context analysis results from the Context Model."""
    characters: Dict[str, Dict[str, Any]]  # Character profiles and patterns
    formality_patterns: Dict[str, str]  # Formality patterns by scene/character
    technical_terms: List[str]  # Important technical terminology
    emotional_arcs: Dict[str, str]  # Emotional progression patterns
    story_summary: str  # Brief story summary for context


@dataclass
class TranslationResult:
    """Result from translation with quality metrics."""
    text: str
    confidence_score: float
    quality_metrics: Dict[str, float]
    model_consensus: Dict[str, str]  # Results from different models


class MultiModelOrchestrator:
    """
    Orchestrates multiple AI models for enhanced translation quality.
    
    This class implements the revolutionary multi-model architecture that
    significantly improves translation quality through specialized models.
    """
    
    def __init__(self, config: Config):
        """Initialize the multi-model orchestrator."""
        self.config = config
        self.multi_config = config.multi_model
        self.logger = logging.getLogger(__name__)
        
        # Initialize Ollama clients for each model
        self.context_client = self._create_ollama_client(self.multi_config.context_model.model)
        self.translation_client = self._create_ollama_client(self.multi_config.translation_model.model)
        self.validator_client = self._create_ollama_client(self.multi_config.technical_validator.model)
        self.dialogue_client = self._create_ollama_client(self.multi_config.dialogue_specialist.model)
        
        # Story context cache
        self.story_context: Optional[StoryContext] = None
        
    def _create_ollama_client(self, model: str) -> OllamaClient:
        """Create an Ollama client for a specific model."""
        # Create a temporary config with the specific model
        temp_config = Config(
            model=model,
            ollama_host=self.config.ollama_host,
            ollama_port=self.config.ollama_port,
            ollama_timeout=self.config.ollama_timeout,
            source_lang=self.config.source_lang,
            target_lang=self.config.target_lang,
            max_retries=self.config.max_retries
        )
        return OllamaClient(temp_config)
    
    def is_enabled(self) -> bool:
        """Check if multi-model architecture is enabled."""
        return self.multi_config.enabled
    
    def analyze_story_context(self, entries: List[SubtitleEntry]) -> StoryContext:
        """
        Analyze the complete story using the Context Model.
        
        Args:
            entries: Complete list of subtitle entries
            
        Returns:
            StoryContext with character profiles and story analysis
        """
        if not self.multi_config.context_model.analyze_full_story:
            # Return minimal context if full analysis is disabled
            return StoryContext(
                characters={},
                formality_patterns={},
                technical_terms=[],
                emotional_arcs={},
                story_summary=""
            )
        
        self.logger.info("🧠 Analyzing story context with Context Model...")
        
        # Prepare story text for analysis
        story_text = self._prepare_story_text(entries)
        
        # Create context analysis prompt
        prompt = self._create_context_analysis_prompt(story_text)
        
        try:
            # Use Context Model for analysis
            response = self.context_client.translate_with_retry(
                prompt, 
                ""  # No additional context needed
            )
            
            # Parse the context analysis response
            context = self._parse_context_analysis(response)
            self.story_context = context
            
            self.logger.info(f"✅ Story context analyzed: {len(context.characters)} characters identified")
            return context
            
        except Exception as e:
            self.logger.error(f"❌ Context analysis failed: {e}")
            # Return minimal context on failure
            return StoryContext(
                characters={},
                formality_patterns={},
                technical_terms=[],
                emotional_arcs={},
                story_summary=""
            )
    
    def translate_with_multimodel(
        self, 
        entries: List[SubtitleEntry], 
        progress: TranslationProgress
    ) -> List[SubtitleEntry]:
        """
        Translate entries using the multi-model architecture.
        
        Args:
            entries: Subtitle entries to translate
            progress: Progress manager
            
        Returns:
            Translated subtitle entries with enhanced quality
        """
        if not self.is_enabled():
            self.logger.warning("Multi-model architecture disabled, falling back to single model")
            # TODO: Fallback to single model translation
            return entries
        
        self.logger.info("🚀 Starting multi-model translation pipeline...")
        
        # Phase 1: Analyze story context (if not already done)
        if self.story_context is None:
            self.story_context = self.analyze_story_context(entries)
        
        translated_entries = []
        
        for entry in entries:
            # Phase 2: Primary translation with context
            translation_result = self._translate_with_context(entry, self.story_context)
            
            # Phase 3: Technical validation
            validated_result = self._validate_translation(entry, translation_result)
            
            # Phase 4: Dialogue specialist refinement
            final_result = self._refine_dialogue(entry, validated_result, self.story_context)
            
            # Create final subtitle entry
            translated_entry = SubtitleEntry(
                index=entry.index,
                start_time=entry.start_time,
                end_time=entry.end_time,
                text=final_result.text,
                original_text=entry.text
            )
            
            translated_entries.append(translated_entry)
            progress.add_translated_entry(translated_entry)
            
            self.logger.debug(f"Multi-model translation completed for entry {entry.index}")
        
        self.logger.info("✅ Multi-model translation pipeline completed")
        return translated_entries
    
    def _prepare_story_text(self, entries: List[SubtitleEntry]) -> str:
        """Prepare story text for context analysis."""
        # Combine subtitle texts with timing context
        lines = []
        for entry in entries[:50]:  # Analyze first 50 entries for context
            lines.append(f"[{entry.index}] {entry.text}")
        return "\n".join(lines)
    
    def _create_context_analysis_prompt(self, story_text: str) -> str:
        """Create prompt for story context analysis."""
        return f"""Analyze this subtitle text and provide a structured analysis:

SUBTITLE TEXT:
{story_text}

Please analyze and provide:
1. CHARACTER PROFILES: Identify main characters and their speaking patterns
2. FORMALITY PATTERNS: Detect formal/informal speech patterns
3. TECHNICAL TERMS: List important technical or specialized terms
4. EMOTIONAL ARCS: Identify emotional themes and progressions
5. STORY SUMMARY: Brief summary of the content

Respond in a structured format that can be parsed."""
    
    def _parse_context_analysis(self, response: str) -> StoryContext:
        """Parse the context analysis response into structured data."""
        # TODO: Implement proper parsing of context analysis
        # For now, return basic structure
        return StoryContext(
            characters={"main": {"formality": "auto", "traits": []}},
            formality_patterns={"default": "auto"},
            technical_terms=[],
            emotional_arcs={"default": "neutral"},
            story_summary=response[:200] if response else ""
        )
    
    def _translate_with_context(self, entry: SubtitleEntry, context: StoryContext) -> TranslationResult:
        """Translate using the Translation Model with story context."""
        # TODO: Implement context-aware translation
        return TranslationResult(
            text=entry.text,  # Placeholder
            confidence_score=0.5,
            quality_metrics={"grammar": 0.5, "naturalness": 0.5},
            model_consensus={"translation": entry.text}
        )
    
    def _validate_translation(self, original: SubtitleEntry, translation: TranslationResult) -> TranslationResult:
        """Validate translation using the Technical Validator."""
        # TODO: Implement technical validation
        return translation
    
    def _refine_dialogue(self, original: SubtitleEntry, translation: TranslationResult, context: StoryContext) -> TranslationResult:
        """Refine dialogue using the Dialogue Specialist."""
        # TODO: Implement dialogue refinement
        return translation
