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
                timeout=30
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
        """Build translation prompt with context."""
        source_lang = self.config.get_language_name(self.config.source_lang)
        target_lang = self.config.get_language_name(self.config.target_lang)
        
        prompt = f"""You are a professional subtitle translator specializing in {source_lang} to {target_lang} translation for hearing-impaired users.

Your task is to translate subtitle text while:
1. Maintaining the original meaning and tone
2. Keeping translations natural and fluent in {target_lang}
3. Preserving any formatting (like *italics*)
4. Keeping translations concise to fit subtitle timing
5. Considering the context of surrounding dialogue

"""
        
        if context:
            prompt += f"Context from surrounding subtitles:\n{context}\n\n"
        
        prompt += f"""Translate this {source_lang} subtitle to {target_lang}:
"{text}"

Translation:"""
        
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
