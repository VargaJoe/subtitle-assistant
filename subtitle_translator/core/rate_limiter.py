"""
Rate limiter for API usage tracking.

Tracks API usage with persistent storage across sessions.
Supports per-minute, per-hour, per-day limits.
"""

import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limits based on Gemini API actual limits."""
    # Gemini Free Tier Actual Limits (from AI Studio):
    # gemini-2.5-flash: 5 RPM, 250K TPM, 20 RPD
    # gemini-3-flash: 5 RPM, 250K TPM, 20 RPD
    # gemini-2.5-flash-lite: 10 RPM, 250K TPM, 20 RPD
    requests_per_minute: int = 5  # RPM: 5 for flash/3-flash, 10 for flash-lite
    requests_per_hour: int = 50  # Calculated from RPD limit
    requests_per_day: int = 20  # RPD: ONLY 20 requests per day on free tier!
    tokens_per_minute: int = 250000  # TPM: 250K tokens per minute
    tokens_per_hour: Optional[int] = None
    tokens_per_day: Optional[int] = None


@dataclass
class UsageRecord:
    """Single API usage record."""
    timestamp: float  # Unix timestamp
    requests: int = 1
    tokens: int = 0


class APIRateLimiter:
    """
    Thread-safe rate limiter with persistent storage.
    
    Tracks API usage across sessions to prevent rate limit violations.
    Uses a JSON file in the project's data directory.
    """
    
    def __init__(
        self,
        provider_name: str = "gemini",
        config: Optional[RateLimitConfig] = None,
        storage_dir: Optional[Path] = None
    ):
        """
        Initialize rate limiter.
        
        Args:
            provider_name: Name of the API provider (e.g., "gemini", "openai")
            config: Rate limit configuration
            storage_dir: Directory to store usage records (default: project data dir)
        """
        self.provider_name = provider_name
        self.config = config or RateLimitConfig()
        
        # Setup storage directory
        if storage_dir is None:
            storage_dir = Path(__file__).parent.parent.parent / "data" / "rate_limits"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.usage_file = self.storage_dir / f"{provider_name}_usage.json"
        self.lock = threading.Lock()
        
        # Load existing usage data
        self.usage_history: list[UsageRecord] = self._load_usage()
        
    def _load_usage(self) -> list[UsageRecord]:
        """Load usage history from file."""
        if not self.usage_file.exists():
            return []
        
        try:
            with open(self.usage_file, 'r') as f:
                data = json.load(f)
                return [UsageRecord(**record) for record in data]
        except Exception as e:
            logger.warning(f"Failed to load usage history: {e}")
            return []
    
    def _save_usage(self) -> None:
        """Save usage history to file."""
        try:
            with open(self.usage_file, 'w') as f:
                json.dump([asdict(record) for record in self.usage_history], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save usage history: {e}")
    
    def _cleanup_old_records(self) -> None:
        """Remove records older than 24 hours."""
        cutoff_time = time.time() - (24 * 3600)
        self.usage_history = [r for r in self.usage_history if r.timestamp > cutoff_time]
    
    def _get_recent_usage(self, seconds: int) -> tuple[int, int]:
        """
        Get usage in the last N seconds.
        
        Returns:
            (request_count, token_count)
        """
        cutoff_time = time.time() - seconds
        recent = [r for r in self.usage_history if r.timestamp > cutoff_time]
        
        total_requests = sum(r.requests for r in recent)
        total_tokens = sum(r.tokens for r in recent)
        
        return total_requests, total_tokens
    
    def check_rate_limit(self, tokens: int = 0) -> tuple[bool, Optional[str]]:
        """
        Check if rate limit would be exceeded.
        
        Args:
            tokens: Number of tokens about to be used
            
        Returns:
            (is_allowed, error_message)
        """
        with self.lock:
            self._cleanup_old_records()
            
            # Check per-minute limit
            req_1m, tokens_1m = self._get_recent_usage(60)
            if req_1m >= self.config.requests_per_minute:
                return False, (
                    f"Rate limit: {req_1m}/{self.config.requests_per_minute} "
                    f"requests per minute. Wait before retrying."
                )
            if tokens_1m + tokens > self.config.tokens_per_minute:
                return False, (
                    f"Rate limit: {tokens_1m}/{self.config.tokens_per_minute} "
                    f"tokens per minute. Wait before retrying."
                )
            
            # Check per-hour limit
            req_1h, tokens_1h = self._get_recent_usage(3600)
            if req_1h >= self.config.requests_per_hour:
                return False, (
                    f"Rate limit: {req_1h}/{self.config.requests_per_hour} "
                    f"requests per hour. Try again in 1 hour."
                )
            
            # Check per-day limit
            req_1d, tokens_1d = self._get_recent_usage(86400)
            if req_1d >= self.config.requests_per_day:
                return False, (
                    f"Rate limit: {req_1d}/{self.config.requests_per_day} "
                    f"requests per day. Try again tomorrow."
                )
            
            return True, None
    
    def record_usage(self, requests: int = 1, tokens: int = 0) -> None:
        """
        Record API usage.
        
        Args:
            requests: Number of requests made
            tokens: Number of tokens used
        """
        with self.lock:
            record = UsageRecord(
                timestamp=time.time(),
                requests=requests,
                tokens=tokens
            )
            self.usage_history.append(record)
            self._save_usage()
    
    def wait_if_needed(self, tokens: int = 0, max_wait: int = 3600) -> bool:
        """
        Wait if rate limit would be exceeded.
        
        Args:
            tokens: Number of tokens about to be used
            max_wait: Maximum seconds to wait (default: 1 hour)
            
        Returns:
            True if waited, False if would exceed max_wait
        """
        is_allowed, error_msg = self.check_rate_limit(tokens)
        if is_allowed:
            return False
        
        # Calculate wait time based on oldest record in current window
        with self.lock:
            req_1m, _ = self._get_recent_usage(60)
            if req_1m >= self.config.requests_per_minute:
                # Wait until oldest request in last minute expires
                cutoff = time.time() - 60
                oldest = min((r.timestamp for r in self.usage_history 
                             if r.timestamp > cutoff), default=time.time())
                wait_time = (oldest + 60) - time.time() + 1
            else:
                wait_time = 1  # Short wait
        
        if wait_time > max_wait:
            logger.error(f"Would need to wait {wait_time}s, exceeds max_wait {max_wait}s")
            return False
        
        if wait_time > 0:
            logger.warning(f"Rate limit approaching. Waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current usage statistics."""
        with self.lock:
            self._cleanup_old_records()
            
            req_1m, tokens_1m = self._get_recent_usage(60)
            req_1h, tokens_1h = self._get_recent_usage(3600)
            req_1d, tokens_1d = self._get_recent_usage(86400)
            
            return {
                "provider": self.provider_name,
                "per_minute": {
                    "requests": f"{req_1m}/{self.config.requests_per_minute}",
                    "tokens": f"{tokens_1m}/{self.config.tokens_per_minute}"
                },
                "per_hour": {
                    "requests": f"{req_1h}/{self.config.requests_per_hour}"
                },
                "per_day": {
                    "requests": f"{req_1d}/{self.config.requests_per_day}"
                },
                "total_records": len(self.usage_history),
                "storage_file": str(self.usage_file)
            }
    
    def reset_stats(self) -> None:
        """Clear all usage history."""
        with self.lock:
            self.usage_history = []
            self._save_usage()
            logger.info(f"Rate limit stats reset for {self.provider_name}")
