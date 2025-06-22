"""
Ollama client for AI translation services.
"""

import json
import logging
from typing import Dict, List, Optional
import requests
from requests.exceptions import RequestException, ConnectionError, Timeout

from .config import Config


class OllamaClient:
    """Client for interacting with Ollama AI service."""
    
    def __init__(self, config: Config):
        """Initialize Ollama client with configuration."""
        self.config = config
        self.base_url = config.ollama_url
        self.logger = logging.getLogger(__name__)
        
    def is_available(self) -> bool:
        """Check if Ollama service is available."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except (ConnectionError, Timeout, RequestException):
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available models from Ollama."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except (ConnectionError, Timeout, RequestException) as e:
            self.logger.error(f"Failed to get models: {e}")
            return []
    
    def translate_text(self, text: str, context: Optional[str] = None) -> str:
        """
        Translate text using Ollama.
        
        Args:
            text: Text to translate
            context: Optional context for better translation
            
        Returns:
            Translated text
            
        Raises:
            ConnectionError: If Ollama service is not available
            ValueError: If translation fails
        """
        if not self.is_available():
            raise ConnectionError("Ollama service is not available")
          # Build translation prompt
        prompt = self._build_translation_prompt(text, context)
        
        # Make API request
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "top_p": 0.9,
                "num_predict": 200
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.config.ollama_timeout
            )
            response.raise_for_status()
            
            result = response.json()
            translated_text = result.get("response", "").strip()
            
            if not translated_text:
                raise ValueError("Empty translation response")
            
            # Clean up the response (remove any extra formatting)
            translated_text = self._clean_translation(translated_text)
            
            if self.config.verbose:
                self.logger.info(f"Translated: '{text}' -> '{translated_text}'")
            
            return translated_text
            
        except RequestException as e:
            self.logger.error(f"Translation request failed: {e}")
            raise ValueError(f"Translation failed: {e}")
    def _build_translation_prompt(self, text: str, context: Optional[str] = None) -> str:
        """Build translation prompt with context and style instructions."""
        source_lang = self.config.get_language_name(self.config.source_lang)
        target_lang = self.config.get_language_name(self.config.target_lang)
        
        prompt = f"""You are a professional subtitle translator specializing in {source_lang} to {target_lang} translation for hearing-impaired users.

TRANSLATION GUIDELINES:
1. Maintain the original meaning and emotional tone
2. Keep translations natural and fluent in {target_lang}
3. Preserve any formatting (like *italics*)
4. Keep translations concise to fit subtitle timing constraints
5. {self.config.get_formality_instruction()}
6. Use natural, conversational {target_lang} - avoid overly formal or awkward phrasing

HUNGARIAN-SPECIFIC RULES:
- For casual conversations, use informal "te" forms (e.g., "Hogy vagy?" not "Hogy van?")
- For formal situations, use polite "maga/Ön" forms
- Keep English proper names unchanged
- Handle contractions naturally (e.g., "I'm" → "Én" or context-appropriate form)
- Aim for natural Hungarian expressions rather than literal translations

SUBTITLE CONTEXT:
These are dialogue subtitles, so prioritize natural speech patterns over formal written language.
"""
        
        if context:
            prompt += f"\nSURROUNDING DIALOGUE CONTEXT:\n{context}\n"
        
        prompt += f"""
TRANSLATE THIS {source_lang.upper()} SUBTITLE TO {target_lang.upper()}:
"{text}"

Important: Respond with ONLY the translated text, no explanations or quotes."""
        
        return prompt
    
    def _clean_translation(self, text: str) -> str:
        """Clean up translation response."""
        # Remove common AI response artifacts
        text = text.strip()
        
        # Remove quotes if the entire text is wrapped in them
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        elif text.startswith("'") and text.endswith("'"):
            text = text[1:-1]
        
        # Remove "Translation:" prefix if present
        if text.lower().startswith("translation:"):
            text = text[12:].strip()
        
        return text
    
    def translate_with_retry(self, text: str, context: Optional[str] = None) -> str:
        """
        Translate text with retry logic.
        
        Args:
            text: Text to translate
            context: Optional context
            
        Returns:
            Translated text
            
        Raises:
            ValueError: If all retries fail
        """
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                return self.translate_text(text, context)
            except (ConnectionError, ValueError) as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    self.logger.warning(f"Translation attempt {attempt + 1} failed: {e}")
                    continue
                break
        
        raise ValueError(f"Translation failed after {self.config.max_retries} attempts: {last_error}")
    
    def translate_with_fallback(self, text: str, context: Optional[str] = None) -> str:
        """
        Translate text with fallback to alternative models if the primary fails.
        
        Args:
            text: Text to translate
            context: Optional context
            
        Returns:
            Translated text
            
        Raises:
            ValueError: If all models fail
        """
        models_to_try = [self.config.model] + self.config.fallback_models
        last_error = None
        
        for model in models_to_try:
            if model not in self.get_available_models():
                self.logger.warning(f"Model '{model}' not available, skipping")
                continue
                
            # Temporarily change model
            original_model = self.config.model
            self.config.model = model
            
            try:
                self.logger.info(f"Trying translation with model: {model}")
                result = self.translate_with_retry(text, context)
                
                # Restore original model
                self.config.model = original_model
                return result
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"Model '{model}' failed: {e}")
                # Restore original model before trying next
                self.config.model = original_model
                continue
        
        raise ValueError(f"All models failed. Last error: {last_error}")
