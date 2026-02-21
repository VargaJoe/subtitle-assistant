"""
Google Gemini Translation Provider

Batch-optimized provider that sends subtitle entries in JSON array chunks
(single API call per chunk) instead of one call per entry.
This matches the comic-bridge approach: minimal API calls, maximum efficiency.
"""

import re
import json
import logging
import os
from datetime import datetime
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
#
# Sizing logic (we control INPUT, output limit is just a ceiling):
#   - BATCH_MAX_OUTPUT_TOKENS = 8192 tokens × 4 chars/token = ~32 768 chars output capacity
#   - EN→HU text expansion: ~30%  |  JSON quoting overhead: ~20%  →  combined ~1.5x
#   - 32 768 / 1.5 × 0.70 safety margin ≈ 15 000 chars max safe input
#   - Gemini free tier: 20 requests/day.  A 828-entry file ≈ 58 000 chars.
#     At 7 000 chars/chunk → ~9 API calls (well within daily limit).
#     At 1 500 chars/chunk → ~39 API calls (exceeds free tier!).
MAX_CHARS_PER_CHUNK = 7000

# Batch calls always use this output token limit, regardless of GEMINI_MAX_OUTPUT_TOKENS.
# We size INPUT (via MAX_CHARS_PER_CHUNK) so output always fits comfortably below this ceiling.
# NOTE: gemini-2.5-flash is a thinking model — thinking tokens COUNT against max_output_tokens
# unless thinking is explicitly disabled. Disable thinking for batch subtitle translation:
# subtitles are simple text, no reasoning needed, and thinking wastes the token budget.
BATCH_MAX_OUTPUT_TOKENS = 65536  # Large ceiling; actual output per chunk is ~3000-5000 tokens


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
        # NOTE: GEMINI_MAX_OUTPUT_TOKENS in .env is for single-entry use.
        # Batch chunk calls always use BATCH_MAX_OUTPUT_TOKENS (8192) instead.
        self.max_output_tokens = int(config.get("max_output_tokens", os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", 512)))

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
        Send a single JSON-object batch request and parse the response.

        Uses an INDEXED DICT (not a positional array) so that if the model
        accidentally merges two subtitle lines we know exactly which key is
        missing and can recover gracefully — instead of silently shifting
        every subsequent translation.

        Prompt format:
            TRANSLATE TO HUNGARIAN. Each entry has a numeric key.
            Respond ONLY with a JSON object with the same keys.
            {"1": "...", "2": "...", ...}
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

        # Build indexed dict: {"1": "text1", "2": "text2", ...}
        input_dict = {str(i + 1): t for i, t in enumerate(texts)}
        input_json = json.dumps(input_dict, ensure_ascii=False)

        prompt = (
            f"Translate each {source_lang_upper} subtitle entry to {target_lang_upper}.\n"
            f"Rules:\n"
            f"  - Keep EVERY numeric key. Return exactly {len(texts)} keys.\n"
            f"  - Do NOT merge or split entries — one input key = one output key.\n"
            f"  - Translate meaning faithfully; keep names and proper nouns.\n"
            f"  - Respond ONLY with a valid JSON object. No other text.\n\n"
            f"INPUT ({len(texts)} entries):\n"
            f"{input_json}\n\n"
            f"OUTPUT JSON OBJECT:"
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
                    temperature=self.temperature,
                    max_output_tokens=BATCH_MAX_OUTPUT_TOKENS,
                    # Disable thinking: subtitle translation needs no reasoning,
                    # and thinking tokens eat into max_output_tokens on gemini-2.5+
                    thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
                )
            )

            raw = response.text.strip() if response and response.text else ""
            if not raw:
                raise ValueError("Gemini returned empty response for chunk")

            self.rate_limiter.record_usage(requests=1, tokens=estimated_tokens)

            # Always save raw response for debugging
            self._save_debug_response(raw, len(texts))

            return self._parse_batch_response(raw, len(texts), original_texts=texts)

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Gemini chunk API error: {e}")
            raise

    def _save_debug_response(self, raw: str, entry_count: int) -> None:
        """Save raw API response to output/debug/gemini_chunks/ for post-mortem inspection."""
        try:
            debug_dir = os.path.join("output", "debug", "gemini_chunks")
            os.makedirs(debug_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            path = os.path.join(debug_dir, f"{ts}_chunk_{entry_count}entries.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(raw)
        except Exception as e:
            self.logger.warning(f"Could not save debug response: {e}")

    @staticmethod
    def _repair_json(text: str) -> str:
        """
        Attempt to repair common Gemini JSON quirks:
        0. Trailing commas before closing brace/bracket (e.g. last entry ends with ,\n})
        1. Bare/half-quoted integer keys at line start (MUST run before Pass 2)
           36:   → "36":   (both quotes missing)
           36":  → "36":   (opening quote missing — the common Gemini bug)
        2. Unescaped control characters inside string values

        Pass 1 (key repair) MUST run before Pass 2 (control chars).
        If keys are malformed (e.g. 36":), the char-by-char state machine
        misidentifies the ": as string content, corrupting everything after it.
        """
        # Pass 0: remove trailing commas before closing braces/brackets (e.g. last key ends with ,\n})
        repaired = re.sub(r',(\s*[}\]])', r'\1', text)

        # Pass 1: fix keys FIRST so Pass 2's state machine sees valid JSON structure
        repaired = re.sub(r'^(\s*)(\d+)"?(\s*:)', r'\1"\2"\3', repaired, flags=re.MULTILINE)

        # Pass 2: walk char-by-char, escape ALL bare control characters inside strings
        ESCAPE_MAP = {
            '\n': '\\n',
            '\r': '\\r',
            '\t': '\\t',
            '\b': '\\b',
            '\f': '\\f',
        }
        result: list = []
        in_string = False
        escaped = False
        for ch in repaired:
            if escaped:
                result.append(ch)
                escaped = False
            elif ch == "\\" and in_string:
                result.append(ch)
                escaped = True
            elif ch == '"':
                result.append(ch)
                in_string = not in_string
            elif in_string and ch in ESCAPE_MAP:
                result.append(ESCAPE_MAP[ch])
            elif in_string and ord(ch) < 0x20:
                # Any other ASCII control character → unicode escape
                result.append(f'\\u{ord(ch):04x}')
            else:
                result.append(ch)

        return "".join(result)

    @staticmethod
    def _extract_partial_json(text: str) -> dict:
        """
        Last-resort extraction: try progressively shorter prefixes of the JSON
        until we get a valid (possibly incomplete) object by closing it ourselves.
        Returns whatever entries were successfully parsed before the malformed point.
        """
        # Truncate at the last clean comma-then-newline before a key line
        # so we can close the object and parse what we have.
        lines = text.split("\n")
        for i in range(len(lines) - 1, 0, -1):
            # Try closing the object at line i
            candidate = "\n".join(lines[:i]).rstrip().rstrip(",") + "\n}"
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
        return {}

    def _parse_batch_response(self, response_text: str, expected_count: int, original_texts: Optional[List[str]] = None) -> List[str]:
        """
        Parse indexed JSON-object response and return ordered list of translations.

        Expected format:  {"1": "trans1", "2": "trans2", ...}

        If the model merges or skips an entry (wrong key count), we log a warning
        and fall back to the original text for the missing key — rather than
        hard-failing the whole chunk and losing all other translations.

        Raises ValueError only on completely unparseable JSON or non-object response.
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
            # Attempt repair: control chars in values, unquoted/half-quoted integer keys
            repaired = self._repair_json(cleaned)
            try:
                parsed = json.loads(repaired)
                self.logger.warning(
                    "Gemini response had JSON formatting quirks — repaired and parsed successfully."
                )
            except json.JSONDecodeError:
                # Hard fail — saves debug file already written, stops wasting daily limits
                raise ValueError(
                    f"Gemini response is not valid JSON and could not be repaired: {e}\n"
                    f"Response (first 500 chars): {response_text[:500]}"
                )

        if not isinstance(parsed, dict):
            raise ValueError(
                f"Gemini response is not a JSON object. Got: {type(parsed).__name__}. "
                f"Response (first 300 chars): {response_text[:300]}"
            )

        # Reconstruct positional list, falling back to original text for missing keys
        results: List[str] = []
        missing_keys: List[int] = []
        for i in range(1, expected_count + 1):
            key = str(i)
            if key in parsed:
                results.append(str(parsed[key]))
            else:
                missing_keys.append(i)
                fallback = (original_texts[i - 1] if original_texts and i - 1 < len(original_texts) else "")
                results.append(fallback)

        if missing_keys:
            self.logger.warning(
                f"Gemini merged/skipped {len(missing_keys)} subtitle entries "
                f"(keys {missing_keys}). Kept original text for those entries."
            )

        return results

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
