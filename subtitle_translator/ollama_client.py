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
    
    def translate_batch(self, texts: List[str], context: Optional[str] = None) -> List[str]:
        """
        Translate multiple texts in a single API call for better performance.
        
        Args:
            texts: List of texts to translate
            context: Optional context for better translation
            
        Returns:
            List of translated texts
        """
        if not texts:
            return []
        
        # Prepare batch text with numbering
        batch_text = "\n".join([f"[{i+1}] {text}" for i, text in enumerate(texts)])
        
        # Build batch translation prompt
        prompt = self._build_batch_translation_prompt(batch_text, context)
        
        try:
            # Make API call
            response = self._make_request(prompt)
            translated_content = response.get("response", "")
            
            # Parse response back to individual translations
            translated_texts = self._parse_batch_translation(translated_content, len(texts))
            
            # Clean each translation
            return [self._clean_translation(text) for text in translated_texts]
            
        except Exception as e:
            self.logger.error(f"Batch translation failed: {e}")
            raise
    
    def translate_whole_file(self, file_content: str) -> str:
        """
        Translate entire file content in a single API call.
        
        Args:
            file_content: Complete file content to translate
            
        Returns:
            Translated file content
        """
        # Build whole-file translation prompt
        prompt = self._build_whole_file_translation_prompt(file_content)
        
        try:
            # Make API call with extended timeout for large files
            response = self._make_request(prompt, timeout=self.config.ollama_timeout * 3)
            translated_content = response.get("response", "")
            
            return self._clean_translation(translated_content)
            
        except Exception as e:
            self.logger.error(f"Whole-file translation failed: {e}")
            raise

    def _build_batch_translation_prompt(self, batch_text: str, context: Optional[str] = None) -> str:
        """Build prompt for batch translation."""
        formality = self.config.get_formality_instruction()
        
        prompt = f"""You are a professional subtitle translator. Translate the following numbered subtitle entries from {self.config.get_language_name(self.config.source_lang)} to {self.config.get_language_name(self.config.target_lang)}.

Requirements:
- {formality}
- Maintain natural dialogue flow
- Preserve subtitle timing and structure
- Keep the same numbering format [1], [2], etc.
- Translate each entry on a separate line

"""
        
        if context:
            prompt += f"Context from surrounding subtitles:\n{context}\n\n"
        
        prompt += f"Subtitle entries to translate:\n{batch_text}\n\nTranslated entries:"
        
        return prompt
    
    def _build_whole_file_translation_prompt(self, file_content: str) -> str:
        """Build prompt for whole-file translation."""
        formality = self.config.get_formality_instruction()
        
        prompt = f"""You are a professional subtitle translator. Translate the complete subtitle file from {self.config.get_language_name(self.config.source_lang)} to {self.config.get_language_name(self.config.target_lang)}.

Requirements:
- {formality}
- Maintain natural dialogue flow and character consistency
- Preserve subtitle timing and structure
- Keep the same numbering format [1], [2], etc.
- Translate each entry on a separate line
- Maintain overall story coherence

Complete subtitle file to translate:
{file_content}

Translated subtitle file:"""
        
        return prompt
    
    def _parse_batch_translation(self, translated_content: str, expected_count: int) -> List[str]:
        """Parse batch translation response back to individual texts."""
        lines = translated_content.strip().split('\n')
        translated_texts = []
        
        for i in range(expected_count):
            if i < len(lines):
                line = lines[i].strip()
                # Remove numbering if present: [1] text -> text
                if line.startswith(f"[{i+1}]"):
                    line = line[len(f"[{i+1}]"):].strip()
                translated_texts.append(line)
            else:
                # Not enough lines in response, use empty string
                self.logger.warning(f"Missing translation for batch item {i+1}")
                translated_texts.append("")
        
        return translated_texts

    def _make_request(self, prompt: str, timeout: Optional[int] = None) -> dict:
        """
        Make a request to the Ollama API.
        
        Args:
            prompt: The prompt to send
            timeout: Optional timeout for the request
            
        Returns:
            Parsed JSON response
            
        Raises:
            RequestException: If the request fails
        """
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
                timeout=timeout or self.config.ollama_timeout
            )
            response.raise_for_status()
            
            return response.json()
            
        except RequestException as e:
            self.logger.error(f"Request to Ollama API failed: {e}")
            raise
    
    def query_model(self, prompt: str, temperature: float = 0.3) -> str:
        """
        Send a general query to the model (not specifically for translation).
        
        Args:
            prompt: The prompt to send to the model
            temperature: Temperature for the model response
            
        Returns:
            Model response text
            
        Raises:
            ConnectionError: If Ollama service is not available
            ValueError: If query fails
        """
        if not self.is_available():
            raise ConnectionError("Ollama service is not available")
        
        # Make API request
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": 0.9,
                "num_predict": 500  # Allow more tokens for context analysis
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
            response_text = result.get("response", "").strip()
            
            if not response_text:
                raise ValueError("Empty response from model")
            
            if self.config.verbose:
                self.logger.info(f"Model query completed: {len(response_text)} characters")
            
            return response_text
            
        except RequestException as e:
            self.logger.error(f"Model query failed: {e}")
            raise ValueError(f"Query failed: {e}")
