"""
Google Gemini Translation Provider

Batch-optimized provider that sends subtitle entries in JSON array chunks
(single API call per chunk) instead of one call per entry.
This matches the comic-bridge approach: minimal API calls, maximum efficiency.
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional

try:
    from google import genai
    from google.genai import types as genai_types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None
    genai_types = None

from ..core.plugin_system import BaseTranslationProvider, ProviderCapabilities, translation_provider
from ..core.rate_limiter import APIRateLimiter, RateLimitConfig


# Maximum source characters per API call chunk.
# Gemini output ~30% larger than input (EN->HU expansion).
# Keep well under the token limit to prevent JSON truncation.
MAX_CHARS_PER_CHUNK = 3000


@translation_provider("gemini")
class GeminiProvider(BaseTranslationProvider):
    """Google Gemini API translation provider with chunk-based batch calls."""

    # Signal to translator.py that this provider supports true API-level batching
    supports_api_batch = True

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        if not GEMINI_AVAILABLE:
            raise ImportError(
                "google-genai library not available. "
                "Install with: pip install google-genai"
            )

        # Get API key
        api_key = config.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "Gemini API key required. Set GEMINI_API_KEY environment variable "
                "or gemini_api_key in config."
            )

        self.client = genai.Client(api_key=api_key)

        # Configuration — also read from env vars (set in .env)
        self.model_name = config.get("gemini_model", os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"))
        self.temperature = float(config.get("temperature", os.environ.get("GEMINI_TEMPERATURE", 0.3)))
        self.max_output_tokens = int(config.get("max_output_tokens", os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", 8192)))

        # Rate limiter with actual free-tier limits (from Google AI Studio)
        # gemini-2.5-flash / gemini-3-flash : 5 RPM, 250K TPM, 20 RPD
        # gemini-2.5-flash-lite             : 10 RPM, 250K TPM, 20 RPD
        requests_per_minute = 10 if "flash-lite" in self.model_name else 5
        rate_limit_config = RateLimitConfig(
            requests_per_minute=requests_per_minute,
            requests_per_hour=50,
            requests_per_day=20,   # CRITICAL: only 20 req/day on free tier
            tokens_per_minute=250000
        )
        self.rate_limiter = APIRateLimiter(provider_name="gemini", config=rate_limit_config)

        # Language settings
        self.source_lang = config.get("source_lang", "English")
        self.target_lang = config.get("target_lang", "Hungarian")

        self.system_prompt = (
            f"You are a professional subtitle translator. "
            f"Translate from {self.source_lang} to {self.target_lang}. "
            f"Keep translations concise for subtitles. "
            f"Preserve names and technical terms. "
            f"Maintain tone and formality of original."
        )

    # ------------------------------------------------------------------
    # Provider interface
    # ------------------------------------------------------------------

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name="Google Gemini API",
            version="2.0.0",
            description="Cloud-based batch translation using Google Gemini API",
            supported_languages=["en", "hu", "de", "fr", "es", "it", "pt", "ru", "ja", "ko", "zh"],
            requires_gpu=False,
            batch_processing=True,
            context_window_support=False,
            multi_model_support=False
        )

    def is_available(self) -> bool:
        if not GEMINI_AVAILABLE:
            return False
        try:
            list(self.client.models.list())
            return True
        except Exception as e:
            self.logger.error(f"Gemini API unavailable: {e}")
            return False

    def get_available_models(self) -> List[str]:
        return [self.model_name]

    # ------------------------------------------------------------------
    # True batch API translation (main entry point from translator.py)
    # ------------------------------------------------------------------

    def translate_api_batch(self, texts: List[str]) -> List[str]:
        """
        Translate a list of texts using chunked JSON-array API calls.

        Splits texts into character-limited chunks and makes ONE Gemini API call
        per chunk. A full subtitle file (1500 entries) becomes ~5-15 calls
        instead of 1500, staying within the 20 req/day free-tier limit.

        Returns:
            List of translated strings in the same order as input.
        """
        if not texts:
            return []

        chunks = self._split_into_chunks(texts, MAX_CHARS_PER_CHUNK)
        self.logger.info(
            f"Batch translating {len(texts)} subtitle entries as "
            f"{len(chunks)} API chunk(s) (max {MAX_CHARS_PER_CHUNK} chars each)"
        )

        results: List[str] = []
        for idx, chunk in enumerate(chunks):
            self.logger.info(f"  Chunk {idx + 1}/{len(chunks)}: {len(chunk)} entries, "
                             f"{sum(len(t) for t in chunk)} chars")
            translated = self._translate_chunk(chunk)
            results.extend(translated)

        return results

    # ------------------------------------------------------------------
    # Single-entry interface (fallback / compatibility)
    # ------------------------------------------------------------------

    def translate_with_retry(self, text: str, context: Optional[str] = None) -> str:
        """Translate a single text (fallback — prefer translate_api_batch for bulk work)."""
        estimated_tokens = len(text) // 4 + 100
        for attempt in range(3):
            try:
                is_allowed, error_msg = self.rate_limiter.check_rate_limit(estimated_tokens)
                if not is_allowed:
                    if attempt < 2:
                        waited = self.rate_limiter.wait_if_needed(estimated_tokens, max_wait=60)
                        if not waited:
                            raise RuntimeError(f"Rate limit exceeded: {error_msg}")
                    else:
                        raise RuntimeError(f"Rate limit exceeded: {error_msg}")
                result = self._translate_single(text)
                self.rate_limiter.record_usage(requests=1, tokens=estimated_tokens)
                return result
            except Exception as e:
                if attempt == 2:
                    raise
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying...")

    def translate_with_fallback(self, text: str, context: Optional[str] = None) -> str:
        return self.translate_with_retry(text, context)

    def translate_batch(self, texts: List[str], context: Optional[str] = None) -> List[str]:
        """Translate a list — routes to true API batch."""
        return self.translate_api_batch(texts)

    def translate_whole_file(self, content: str) -> str:
        lines = content.split('\n')
        non_empty = [(i, ln) for i, ln in enumerate(lines) if ln.strip()]
        if not non_empty:
            return content
        translated = self.translate_api_batch([ln for _, ln in non_empty])
        for (i, _), t in zip(non_empty, translated):
            lines[i] = t
        return '\n'.join(lines)

    def validate_config(self, config: Dict[str, Any]) -> bool:
        return bool(config.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY"))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _split_into_chunks(self, texts: List[str], max_chars: int) -> List[List[str]]:
        """Split texts into character-limited chunks for safe API calls."""
        chunks: List[List[str]] = []
        current_chunk: List[str] = []
        current_chars = 0

        for text in texts:
            text_len = len(text)
            if current_chunk and current_chars + text_len > max_chars:
                chunks.append(current_chunk)
                current_chunk = []
                current_chars = 0
            current_chunk.append(text)
            current_chars += text_len

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _translate_chunk(self, texts: List[str]) -> List[str]:
        """
        Send a single JSON-array batch request and parse the response.

        Prompt format:
            TRANSLATE TO HUNGARIAN. RESPOND ONLY WITH VALID JSON ARRAY. NO OTHER TEXT.
            INPUT (N English subtitle texts):
            ["text1", "text2", ...]
            OUTPUT JSON ARRAY:
        """
        estimated_tokens = sum(len(t) for t in texts) // 4 + 200

        # Rate-limit check / wait
        is_allowed, error_msg = self.rate_limiter.check_rate_limit(estimated_tokens)
        if not is_allowed:
            waited = self.rate_limiter.wait_if_needed(estimated_tokens, max_wait=3600)
            if not waited:
                raise RuntimeError(f"Gemini rate limit exceeded: {error_msg}")

        target_lang_upper = self.target_lang.upper()
        source_lang_upper = self.source_lang.upper()
        input_json = json.dumps(texts, ensure_ascii=False)

        prompt = (
            f"TRANSLATE TO {target_lang_upper}. RESPOND ONLY WITH VALID JSON ARRAY. NO OTHER TEXT.\n\n"
            f"INPUT ({len(texts)} {source_lang_upper} subtitle texts):\n"
            f"{input_json}\n\n"
            f"OUTPUT JSON ARRAY:"
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
                    temperature=self.temperature,
                    max_output_tokens=self.max_output_tokens,
                )
            )

            raw = response.text.strip() if response and response.text else ""
            if not raw:
                raise ValueError("Gemini returned empty response for chunk")

            self.rate_limiter.record_usage(requests=1, tokens=estimated_tokens)
            return self._parse_batch_response(raw, len(texts))

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Gemini chunk API error: {e}")
            raise

    def _parse_batch_response(self, response_text: str, expected_count: int) -> List[str]:
        """
        Parse JSON array response and validate item count.
        Raises ValueError on truncation or invalid JSON.
        """
        cleaned = response_text.strip()

        # Strip markdown code fences if present
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Gemini response is not valid JSON: {e}\n"
                f"Response (first 500 chars): {response_text[:500]}"
            )

        if not isinstance(parsed, list):
            raise ValueError(
                f"Gemini response is not a JSON array. Got: {type(parsed).__name__}"
            )

        if len(parsed) != expected_count:
            raise ValueError(
                f"Gemini response count mismatch: expected {expected_count}, "
                f"got {len(parsed)} — possible truncation. "
                f"Response length: {len(response_text)} chars."
            )

        return [str(item) for item in parsed]

    def _translate_single(self, text: str) -> str:
        """Single-entry translation for fallback use."""
        if not text.strip():
            return text
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=f"Translate: {text}",
                config=genai_types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
                    temperature=self.temperature,
                    max_output_tokens=self.max_output_tokens,
                )
            )
            result = response.text.strip() if response and response.text else text
            return result if result else text
        except Exception as e:
            self.logger.error(f"Gemini single translation error: {e}")
            raise
