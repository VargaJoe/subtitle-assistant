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
        Only performs context analysis, never translation.
        """
        if not self.multi_config.context_model.analyze_full_story:
            return StoryContext(
                characters={},
                formality_patterns={},
                technical_terms=[],
                emotional_arcs={},
                story_summary=""
            )
        self.logger.info("🧠 [CONTEXT MODEL] Analyzing story context with Context Model (no translation)...")
        story_text = self._prepare_story_text(entries)
        prompt = self._create_context_analysis_prompt(story_text)
        self.logger.debug(f"[CONTEXT MODEL] Prompt sent to model:\n{prompt}")
        try:
            response = self.context_client.query_model(
                prompt,
                temperature=self.multi_config.context_model.temperature
            )
            self._save_raw_model_response(response, stage="context_analysis")
            self.logger.debug(f"[CONTEXT MODEL] Raw response from model:\n{response}")
            context = self._parse_context_analysis(response)
            self.story_context = context
            self.logger.info(f"✅ [CONTEXT MODEL] Story context analyzed: {len(context.characters)} characters identified")
            return context
        except Exception as e:
            self.logger.error(f"❌ [CONTEXT MODEL] Context analysis failed: {e}")
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
        
        Each step updates the same result files incrementally:
        Step 1: Context Analysis -> result.json (context)
        Step 2: Translation -> result.json (context + translation)  
        Step 3: Validation -> result.json (context + translation + validation)
        Step 4: Dialogue -> result.json (context + translation + validation + dialogue)
        
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
        
        # Create results directory for intermediate files
        results_dir = Path("output/multi_model_results")
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # Create single result file for the entire SRT file
        input_filename = progress.input_file.stem  # Get filename without extension
        result_file = results_dir / f"{input_filename}_results.json"
        
        # Initialize the main result structure
        srt_results = {
            "file_info": {
                "input_file": str(progress.input_file),
                "output_file": str(progress.output_file),
                "total_entries": len(entries),
                "processing_start": self._get_timestamp()
            },
            "entries": {}
        }
        
        # Phase 1: Analyze story context (if enabled and not already done)
        if self.multi_config.pipeline.run_context_analysis and self.story_context is None:
            self.logger.info("📊 Step 1: Story Context Analysis")
            self.story_context = self.analyze_story_context(entries)
            
            # Add context analysis to main result file
            srt_results["step1_context_analysis"] = {
                "timestamp": self._get_timestamp(),
                "context": self.story_context.__dict__
            }
            self._save_step_result(result_file, srt_results)
        elif not self.multi_config.pipeline.run_context_analysis:
            self.logger.info("⏭️  Step 1: Context Analysis SKIPPED")
            # Use empty context if step is disabled
            if self.story_context is None:
                self.story_context = StoryContext(
                    characters={},
                    formality_patterns={},
                    technical_terms=[],
                    emotional_arcs={},
                    story_summary=""
                )
        
        translated_entries = []
        
        # Process each entry through the 4-stage pipeline
        for entry in entries:
            self.logger.info(f"🔄 Processing entry {entry.index}/{len(entries)}: Multi-model pipeline")
            
            # Initialize entry results in the main structure
            entry_key = f"entry_{entry.index:04d}"
            srt_results["entries"][entry_key] = {
                "index": entry.index,
                "original_text": entry.text,
                "start_time": str(entry.start_time),
                "end_time": str(entry.end_time)
            }
            
            # Ensure we have a valid story context (empty if disabled)
            current_context = self.story_context or StoryContext(
                characters={},
                formality_patterns={},
                technical_terms=[],
                emotional_arcs={},
                story_summary=""
            )
            
            # Add step 1 context information to each entry
            if self.multi_config.pipeline.run_context_analysis:
                srt_results["entries"][entry_key]["step1_context"] = {
                    "analyzed": True,
                    "timestamp": self._get_timestamp(),
                    "characters_found": len(current_context.characters) if current_context else 0,
                    "technical_terms": len(current_context.technical_terms) if current_context else 0
                }
            else:
                srt_results["entries"][entry_key]["step1_context"] = {
                    "skipped": True,
                    "reason": "disabled"
                }
            
            # Phase 2: Primary translation with context (if enabled)
            if self.multi_config.pipeline.run_translation:
                self.logger.debug(f"Step 2: Translation (entry {entry.index})")
                translation_result = self._translate_with_context(entry, current_context)
                srt_results["entries"][entry_key]["step2_translation"] = {
                    "text": translation_result.text,
                    "confidence": translation_result.confidence_score,
                    "timestamp": self._get_timestamp()
                }
            else:
                self.logger.debug(f"⏭️  Step 2: Translation SKIPPED (entry {entry.index})")
                # Use original text if translation is skipped
                translation_result = TranslationResult(
                    text=entry.text,
                    confidence_score=0.5,
                    quality_metrics={"grammar": 0.5, "naturalness": 0.5},
                    model_consensus={"translation": entry.text}
                )
                srt_results["entries"][entry_key]["step2_translation"] = {"skipped": True}
            self._save_step_result(result_file, srt_results)
            
            # Phase 3: Technical validation (if enabled and conditional)
            if not self.multi_config.pipeline.run_validation:
                validated_result = translation_result
                self.logger.debug(f"⏭️  Step 3: Validation SKIPPED (entry {entry.index})")
                srt_results["entries"][entry_key]["step3_validation"] = {"skipped": True, "reason": "disabled"}
            elif (self.multi_config.pipeline.skip_validation_for_high_confidence and 
                translation_result.confidence_score > 0.8):
                # Skip validation for high-confidence translations
                validated_result = translation_result
                self.logger.debug(f"⏭️  Skipping validation for high-confidence entry {entry.index}")
                srt_results["entries"][entry_key]["step3_validation"] = {"skipped": True, "reason": "high_confidence"}
            else:
                self.logger.debug(f"Step 3: Validation (entry {entry.index})")
                validated_result = self._validate_translation(entry, translation_result)
                srt_results["entries"][entry_key]["step3_validation"] = {
                    "text": validated_result.text,
                    "confidence": validated_result.confidence_score,
                    "quality_metrics": validated_result.quality_metrics,
                    "timestamp": self._get_timestamp()
                }
            self._save_step_result(result_file, srt_results)
            
            # Phase 4: Dialogue specialist refinement (if enabled and conditional)
            if not self.multi_config.pipeline.run_dialogue_refinement:
                final_result = validated_result
                self.logger.debug(f"⏭️  Step 4: Dialogue Refinement SKIPPED (entry {entry.index})")
                srt_results["entries"][entry_key]["step4_dialogue"] = {"skipped": True, "reason": "disabled"}
            else:
                self.logger.debug(f"Step 4: Dialogue Refinement (entry {entry.index})")
                final_result = self._refine_dialogue(entry, validated_result, current_context)
                srt_results["entries"][entry_key]["step4_dialogue"] = {
                    "text": final_result.text,
                    "confidence": final_result.confidence_score,
                    "timestamp": self._get_timestamp()
                }
            
            # Save final step results for this entry
            srt_results["entries"][entry_key]["final_result"] = {
                "text": final_result.text,
                "confidence": final_result.confidence_score,
                "pipeline_complete": True
            }
            self._save_step_result(result_file, srt_results)
            
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
        
        # Mark processing as complete in the result file
        srt_results["file_info"]["processing_end"] = self._get_timestamp()
        srt_results["file_info"]["processing_complete"] = True
        self._save_step_result(result_file, srt_results)
        
        self.logger.info(f"💾 Complete multi-model results saved to: {result_file}")
        
        self.logger.info("✅ Multi-model translation pipeline completed")
        return translated_entries
    
    def _prepare_story_text(self, entries: List[SubtitleEntry]) -> str:
        """Prepare story text for context analysis."""
        # Get context window size from config, default to 15 if not specified
        context_window = getattr(self.multi_config.context_model, 'context_window', 15)
        
        # Combine subtitle texts with timing context - limit based on context_window
        lines = []
        for entry in entries[:context_window]:
            lines.append(f"[{entry.index}] {entry.text}")
        
        self.logger.info(f"📋 Preparing story context from first {len(lines)} entries")
        return "\n".join(lines)
    
    def _create_context_analysis_prompt(self, story_text: str) -> str:
        """Create prompt for story context analysis."""
        # Use custom prompt template if available, otherwise use default
        if self.multi_config.context_model.prompt_template.strip():
            return self.multi_config.context_model.prompt_template.format(
                story_text=story_text
            )
        
        # Default prompt template
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
        # Use custom prompt template if available
        if self.multi_config.translation_model.prompt_template.strip():
            prompt = self.multi_config.translation_model.prompt_template.format(
                entry_text=entry.text,
                characters=', '.join(context.characters.keys()) if context.characters else 'N/A',
                formality_patterns=context.formality_patterns,
                technical_terms=', '.join(context.technical_terms) if context.technical_terms else 'N/A',
                emotional_arcs=context.emotional_arcs,
                story_summary=context.story_summary
            )
        else:
            # Default prompt template
            prompt = f"""
Translate the following subtitle into Hungarian, considering the context below.

SUBTITLE:
{entry.text}

CONTEXT:
- Characters: {', '.join(context.characters.keys()) if context.characters else 'N/A'}
- Formality Patterns: {context.formality_patterns}
- Technical Terms: {', '.join(context.technical_terms) if context.technical_terms else 'N/A'}
- Emotional Arcs: {context.emotional_arcs}
- Story Summary: {context.story_summary}

Requirements:
- Use appropriate formality and character voice.
- Preserve technical terms and emotional tone.
- Output only the translated Hungarian subtitle.
"""
        try:
            response = self.translation_client.translate_with_retry(prompt, "")
            self._save_raw_model_response(response, stage="translation", entry_index=entry.index)
            translated_text = response.strip()
            # Basic confidence/quality metrics (can be improved later)
            confidence = 0.9 if translated_text and translated_text != entry.text else 0.5
            quality_metrics = {"grammar": 0.8, "naturalness": 0.8} if confidence > 0.7 else {"grammar": 0.5, "naturalness": 0.5}
            return TranslationResult(
                text=translated_text,
                confidence_score=confidence,
                quality_metrics=quality_metrics,
                model_consensus={"translation": translated_text}
            )
        except Exception as e:
            self.logger.error(f"❌ Translation failed for entry {entry.index}: {e}")
            # Fallback: return original text with low confidence
            return TranslationResult(
                text=entry.text,
                confidence_score=0.2,
                quality_metrics={"grammar": 0.2, "naturalness": 0.2},
                model_consensus={"translation": entry.text}
            )
    
    def _validate_translation(self, original: SubtitleEntry, translation: TranslationResult) -> TranslationResult:
        """Validate translation using the Technical Validator."""
        # Use custom prompt template if available
        if self.multi_config.technical_validator.prompt_template.strip():
            prompt = self.multi_config.technical_validator.prompt_template.format(
                original_text=original.text,
                translated_text=translation.text
            )
        else:
            # Default prompt template
            prompt = f"""
Evaluate the following Hungarian subtitle translation for grammar, naturalness, and accuracy. Provide a confidence score (0-1), and suggest improvements if needed.

ORIGINAL ENGLISH:
{original.text}

TRANSLATED HUNGARIAN:
{translation.text}

Requirements:
- Rate grammar and naturalness (0-1 scale)
- Suggest improvements if translation is awkward or inaccurate
- Output: JSON with keys: confidence, grammar, naturalness, suggestion (if any)
"""
        try:
            response = self.validator_client.query_model(
                prompt, 
                temperature=self.multi_config.technical_validator.temperature
            )
            self._save_raw_model_response(response, stage="validation", entry_index=original.index)
            # Attempt to parse JSON-like response (robust fallback)
            import json
            try:
                result = json.loads(response)
                confidence = float(result.get("confidence", 0.5))
                grammar = float(result.get("grammar", 0.5))
                naturalness = float(result.get("naturalness", 0.5))
                suggestion = result.get("suggestion", None)
            except Exception:
                confidence = 0.5
                grammar = 0.5
                naturalness = 0.5
                suggestion = None
            # If suggestion is provided and confidence is low, use it
            final_text = suggestion if suggestion and confidence < 0.7 else translation.text
            return TranslationResult(
                text=final_text,
                confidence_score=confidence,
                quality_metrics={"grammar": grammar, "naturalness": naturalness},
                model_consensus={"translation": final_text}
            )
        except Exception as e:
            self.logger.error(f"❌ Validation failed for entry {original.index}: {e}")
            return translation
    
    def _refine_dialogue(self, original: SubtitleEntry, translation: TranslationResult, context: StoryContext) -> TranslationResult:
        """Refine dialogue using the Dialogue Specialist."""
        # Use custom prompt template if available
        if self.multi_config.dialogue_specialist.prompt_template.strip():
            prompt = self.multi_config.dialogue_specialist.prompt_template.format(
                translated_text=translation.text,
                characters=', '.join(context.characters.keys()) if context.characters else 'N/A',
                emotional_arcs=context.emotional_arcs,
                story_summary=context.story_summary
            )
        else:
            # Default prompt template
            prompt = f"""
Polish the following Hungarian subtitle for natural conversational flow and character voice, considering the context below. Only output the improved Hungarian subtitle, or the original if no improvement is needed.

SUBTITLE:
{translation.text}

CONTEXT:
- Characters: {', '.join(context.characters.keys()) if context.characters else 'N/A'}
- Emotional Arcs: {context.emotional_arcs}
- Story Summary: {context.story_summary}
"""
        try:
            response = self.dialogue_client.translate_with_retry(prompt, "")
            self._save_raw_model_response(response, stage="dialogue", entry_index=original.index)
            improved_text = response.strip()
            # Use improved text if it differs and is not empty
            if improved_text and improved_text != translation.text:
                return TranslationResult(
                    text=improved_text,
                    confidence_score=translation.confidence_score,
                    quality_metrics=translation.quality_metrics,
                    model_consensus={"translation": improved_text}
                )
            else:
                return translation
        except Exception as e:
            self.logger.error(f"❌ Dialogue refinement failed for entry {original.index}: {e}")
            return translation
    
    def _save_raw_model_response(self, response: str, stage: str, entry_index: Optional[int] = None):
        """Save raw model response to a .txt file for debugging."""
        from datetime import datetime
        import os
        base_dir = Path("output/raw_model_responses")
        base_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if entry_index is not None:
            filename = f"{stage}_entry{entry_index}_{timestamp}.txt"
        else:
            filename = f"{stage}_{timestamp}.txt"
        file_path = base_dir / filename
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(response)
        except Exception as e:
            self.logger.error(f"Failed to save raw model response: {e}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp as string."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _save_step_result(self, file_path: Path, result_data: Dict[str, Any]):
        """Save step result to JSON file."""
        import json
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save step result to {file_path}: {e}")
