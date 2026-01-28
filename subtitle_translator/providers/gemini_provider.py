"""
Google Gemini Translation Provider

Simple provider implementation for Google Gemini API.
Follows the same plugin architecture as MarianMT and Ollama providers.
"""

import logging
import os
from typing import Dict, Any, List, Optional

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

from ..core.plugin_system import BaseTranslationProvider, ProviderCapabilities, translation_provider
from ..core.rate_limiter import APIRateLimiter, RateLimitConfig


@translation_provider("gemini")
class GeminiProvider(BaseTranslationProvider):
    """Google Gemini API translation provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        if not GEMINI_AVAILABLE:
            raise ImportError(
                "google-generativeai library not available. "
                "Install with: pip install google-generativeai"
            )
        
        # Get API key
        api_key = config.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "Gemini API key required. Set GEMINI_API_KEY environment variable "
                "or gemini_api_key in config."
            )
        
        genai.configure(api_key=api_key)
        
        # Configuration
        self.model_name = config.get("gemini_model", "gemini-2.0-flash")
        self.temperature = config.get("temperature", 0.3)
        self.max_output_tokens = config.get("max_output_tokens", 512)
        
        # Initialize rate limiter with Gemini-specific limits (from AI Studio)
        # Free tier limits by model:
        # - gemini-2.5-flash: 5 RPM, 250K TPM, 20 RPD (requests/day!)
        # - gemini-3-flash: 5 RPM, 250K TPM, 20 RPD
        # - gemini-2.5-flash-lite: 10 RPM, 250K TPM, 20 RPD
        
        # Determine rate limits based on selected model
        requests_per_minute = 5  # Default for most models
        if "flash-lite" in self.model_name:
            requests_per_minute = 10  # flash-lite allows 10 RPM
        
        rate_limit_config = RateLimitConfig(
            requests_per_minute=requests_per_minute,
            requests_per_hour=50,  # Calculated from 20 RPD limit
            requests_per_day=20,   # CRITICAL: Only 20 requests per DAY on free tier!
            tokens_per_minute=250000  # Actual limit: 250K TPM
        )
        self.rate_limiter = APIRateLimiter(
            provider_name="gemini",
            config=rate_limit_config
        )
        
        # Language settings
        self.source_lang = config.get("source_lang", "English")
        self.target_lang = config.get("target_lang", "Hungarian")
        
        # System prompt
        self.system_prompt = (
            f"You are a professional subtitle translator. "
            f"Translate from {self.source_lang} to {self.target_lang}. "
            f"Keep translations concise for subtitles. "
            f"Preserve names and technical terms. "
            f"Maintain tone and formality of original."
        )
    
    def get_capabilities(self) -> ProviderCapabilities:
        """Return provider capabilities."""
        return ProviderCapabilities(
            name="Google Gemini API",
            version="1.0.0",
            description=f"Cloud-based translation using Google Gemini API",
            supported_languages=["en", "hu", "de", "fr", "es", "it", "pt", "ru", "ja", "ko", "zh"],
            requires_gpu=False,
            batch_processing=True,
            context_window_support=True,
            multi_model_support=False
        )
    
    def is_available(self) -> bool:
        """Check if Gemini API is accessible."""
        if not GEMINI_AVAILABLE:
            return False
        try:
            genai.list_models()
            return True
        except Exception as e:
            self.logger.error(f"Gemini API unavailable: {e}")
            return False
    
    def get_available_models(self) -> List[str]:
        """Return available models."""
        return [self.model_name]
    
    def translate_with_retry(self, text: str, context: Optional[str] = None) -> str:
        """Translate text with retry logic and rate limiting."""
        # Estimate tokens (rough: ~4 chars per token)
        estimated_tokens = len(text) // 4 + 100  # Add buffer for output
        
        for attempt in range(3):
            try:
                # Check rate limits and wait if needed
                is_allowed, error_msg = self.rate_limiter.check_rate_limit(estimated_tokens)
                if not is_allowed:
                    # Try waiting once
                    if attempt < 2:
                        waited = self.rate_limiter.wait_if_needed(estimated_tokens, max_wait=60)
                        if not waited:
                            raise RuntimeError(f"Rate limit exceeded: {error_msg}")
                    else:
                        raise RuntimeError(f"Rate limit exceeded: {error_msg}")
                
                # Perform translation
                result = self._translate(text, context)
                
                # Record successful usage
                self.rate_limiter.record_usage(requests=1, tokens=estimated_tokens)
                
                return result
                
            except Exception as e:
                if attempt == 2:
                    raise
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying...")
    
    def translate_with_fallback(self, text: str, context: Optional[str] = None) -> str:
        """Translate with fallback (same as retry for Gemini)."""
        return self.translate_with_retry(text, context)
    
    def translate_batch(self, texts: List[str], context: Optional[str] = None) -> List[str]:
        """Translate batch of texts."""
        if not texts:
            return []
        
        # For batch: translate each individually to maintain quality
        # (Could batch multiple entries per API call if needed for cost optimization)
        results = []
        for text in texts:
            try:
                results.append(self.translate_with_retry(text, context))
            except Exception as e:
                self.logger.error(f"Failed to translate: {e}")
                results.append(text)  # Return original on failure
        
        return results
    
    def translate_whole_file(self, content: str) -> str:
        """Translate entire file content."""
        lines = content.split('\n')
        translated_lines = []
        
        for line in lines:
            if line.strip():
                try:
                    translated_lines.append(self.translate_with_retry(line.strip()))
                except Exception as e:
                    self.logger.error(f"Failed to translate line: {e}")
                    translated_lines.append(line)
            else:
                translated_lines.append(line)
        
        return '\n'.join(translated_lines)
    
    def _translate(self, text: str, context: Optional[str] = None) -> str:
        """Internal translation method."""
        if not text.strip():
            return text
        
        prompt = f"Translate: {text}"
        if context:
            prompt = f"{context}\n\n{prompt}"
        
        try:
            model = genai.GenerativeModel(
                self.model_name,
                system_instruction=self.system_prompt
            )
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_output_tokens,
                )
            )
            
            result = response.text.strip()
            return result if result else text
            
        except Exception as e:
            self.logger.error(f"Gemini translation error: {e}")
            raise
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration."""
        if not config.get("gemini_api_key") and not os.environ.get("GEMINI_API_KEY"):
            self.logger.error("Missing GEMINI_API_KEY")
            return False
        return True
