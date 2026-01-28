# API Rate Limiting

## Overview

The Gemini provider includes robust rate limiting to prevent exceeding API quotas and avoid DOS-ing Google's servers. Rate limits are **persistent across sessions** and **shared across multiple app instances**.

## Features

### ✅ Multi-Level Rate Limiting
- **Per-minute**: 60 requests/minute (Gemini free tier)
- **Per-hour**: 1000 requests/hour (conservative estimate)
- **Per-day**: 10,000 requests/day (conservative estimate)
- **Token limits**: 1M tokens/minute

### ✅ Persistent Tracking
- Usage tracked in `data/rate_limits/gemini_usage.json`
- Survives app restarts
- Shared across multiple app instances
- JSON format for easy inspection

### ✅ Intelligent Throttling
- Automatically waits before retrying when limit approached
- Configurable max wait time (default: 1 hour)
- Thread-safe for concurrent translations
- Graceful error messages

### ✅ Transparent Integration
- Built into GeminiProvider
- Automatic token estimation
- No code changes needed in translator

## How It Works

### Storage Location
```
data/rate_limits/gemini_usage.json
```

### File Format
```json
[
  {
    "timestamp": 1706374800.123,
    "requests": 1,
    "tokens": 250
  },
  {
    "timestamp": 1706374801.456,
    "requests": 1,
    "tokens": 320
  }
]
```

### Rate Limit Checks

Before each translation request:
1. Estimate tokens needed (~4 chars per token)
2. Check all active limits (1min, 1hr, 1day)
3. If limit would be exceeded:
   - Automatically wait until oldest request expires
   - Maximum wait: 1 hour (default)
4. Record usage after successful API call

## Example Usage

### Check Rate Limit Status
```python
from subtitle_translator.core.rate_limiter import APIRateLimiter

limiter = APIRateLimiter(provider_name="gemini")
is_allowed, error_msg = limiter.check_rate_limit(tokens=500)

if not is_allowed:
    print(f"Cannot translate: {error_msg}")
else:
    print("OK to proceed with translation")
```

### View Current Statistics
```python
stats = limiter.get_stats()
print(stats)
# Output:
# {
#   "provider": "gemini",
#   "per_minute": {"requests": "23/60", "tokens": "450000/1000000"},
#   "per_hour": {"requests": "245/1000"},
#   "per_day": {"requests": "2340/10000"},
#   "total_records": 2340,
#   "storage_file": "data/rate_limits/gemini_usage.json"
# }
```

### Wait for Rate Limit to Reset
```python
# Waits until oldest request in current window expires
waited = limiter.wait_if_needed(tokens=500, max_wait=3600)
if waited:
    print("Waited for rate limit to reset")
else:
    print("Would exceed max_wait time")
```

## Multiple Instances

If you start multiple instances of the app:

```powershell
# Terminal 1
python main.py --input file1.srt --backend gemini

# Terminal 2 (at same time)
python main.py --input file2.srt --backend gemini
```

**Both instances share the same rate limit counter!** This prevents DOS attacks when multiple processes run simultaneously.

## Configuration

### Default Limits (Gemini Free Tier)
```python
RateLimitConfig(
    requests_per_minute=60,      # Requests per minute
    requests_per_hour=1000,      # Requests per hour
    requests_per_day=10000,      # Requests per day
    tokens_per_minute=1000000    # Tokens per minute (1M)
)
```

### Custom Configuration
```python
from subtitle_translator.core.rate_limiter import APIRateLimiter, RateLimitConfig

config = RateLimitConfig(
    requests_per_minute=30,      # Your custom limit
    requests_per_hour=500,
    requests_per_day=5000,
    tokens_per_minute=500000
)

limiter = APIRateLimiter(
    provider_name="gemini",
    config=config
)
```

## Monitoring

### View Rate Limit File
```powershell
cat data/rate_limits/gemini_usage.json | ConvertFrom-Json
```

### Check Current Usage
```python
from subtitle_translator.config import Config
from subtitle_translator.translator import SubtitleTranslator

config = Config()
translator = SubtitleTranslator(config)

# After some translations with Gemini backend
provider = translator.get_provider()
stats = provider.rate_limiter.get_stats()
print(stats)
```

### Reset Statistics
```python
limiter.reset_stats()  # Clears all usage history
```

## Best Practices

### 1. Monitor Before Large Batches
```python
# Check usage before processing large file
stats = limiter.get_stats()
print(f"Already used: {stats['per_day']['requests']}")

# If already at high usage, consider waiting or using different backend
```

### 2. Handle Rate Limit Errors Gracefully
```python
try:
    result = translator.translate_text(text, backend="gemini")
except RuntimeError as e:
    if "Rate limit exceeded" in str(e):
        print(f"Rate limited: {e}")
        # Fall back to MarianMT or other backend
        result = translator.translate_text(text, backend="marian")
```

### 3. Use Batch Mode Efficiently
```python
# Batch translation respects rate limits per request
# Spreading out requests is better than rapid-fire
translator.config.translation_mode = "line-by-line"  # Default (safe)
# vs
translator.config.translation_mode = "batch"  # Faster but uses more quota faster
```

## Troubleshooting

### "Rate limit: X/60 requests per minute"
- You've hit the per-minute limit
- App will automatically wait ~1 minute before retrying
- Or wait before translating more

### "Rate limit: X/1000 requests per hour"
- You've hit the per-hour limit
- Already used most of your hourly quota
- Switch to MarianMT backend or wait 1 hour

### Storage File Corrupted
```python
# Reset and start fresh
limiter.reset_stats()

# Or manually delete
# rm data/rate_limits/gemini_usage.json
```

## Architecture

### Thread Safety
- Uses `threading.Lock()` for concurrent access
- Safe to use from multiple threads
- Safe for multiple processes (file-based coordination)

### Cleanup
- Automatically removes records older than 24 hours
- Prevents indefinite growth of JSON file
- Triggered on every `check_rate_limit()` call

### Persistence
- JSON format for human readability
- Stored in `data/rate_limits/` directory
- One file per provider (`gemini_usage.json`, etc.)

## See Also

- [Gemini API Rate Limits](https://ai.google.dev/docs/limits)
- [Best Practices for API Rate Limiting](https://cloud.google.com/architecture/rate-limiting-strategies-techniques)
