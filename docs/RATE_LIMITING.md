# API Rate Limiting

## Overview

The Gemini provider includes robust rate limiting to prevent exceeding API quotas and avoid DOS-ing Google's servers. Rate limits are **persistent across sessions** and **shared across multiple app instances**.

## Actual Gemini API Limits (from Google AI Studio)

### Free Tier Rate Limits by Model

| Model | RPM | TPM | RPD |
|-------|-----|-----|-----|
| **gemini-2.5-flash** | **5** | **250K** | **20** |
| **gemini-3-flash** | **5** | **250K** | **20** |
| **gemini-2.5-flash-lite** | **10** | **250K** | **20** |
| gemini-embedding-1.0 | 100 | 30K | 1K |
| gemini-2.5-flash-tts | 3 | 10K | 10 |
| gemma-3-* | 30 | 15K | 14.4K |
| gemini-2.5-flash-native-audio | Unlimited | 1M | Unlimited |

**Legend:**
- **RPM** = Requests Per Minute
- **TPM** = Tokens Per Minute  
- **RPD** = Requests Per Day

⚠️ **CRITICAL**: The free tier has a **hard limit of 20 requests per day** for most models!

## Features

### ✅ Multi-Level Rate Limiting
- **Per-minute**: Varies by model (5-10 requests/minute for free tier)
  - gemini-2.5-flash: 5 req/min
  - gemini-3-flash: 5 req/min
  - gemini-2.5-flash-lite: 10 req/min
- **Per-hour**: ~50 requests/hour (to stay under 20 req/day)
- **Per-day**: **ONLY 20 requests/day** (critical limitation!)
- **Token limits**: **250K tokens/minute**

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
#   "per_minute": {"requests": "3/5", "tokens": "750000/250000"},
#   "per_day": {"requests": "12/20"},
#   "total_records": 12,
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
# For gemini-2.5-flash or gemini-3-flash (5 req/min)
RateLimitConfig(
    requests_per_minute=5,       # 5 requests per minute (free tier)
    requests_per_hour=300,       # ~300 requests per hour
    requests_per_day=7200,       # ~7,200 requests per day
    tokens_per_minute=900000     # Token limits vary by model
)

# For gemini-2.5-flash-lite (10 req/min)
RateLimitConfig(
    requests_per_minute=10,      # 10 requests per minute (free tier)
    requests_per_hour=600,       # ~600 requests per hour
    requests_per_day=14400,      # ~14,400 requests per day
    tokens_per_minute=1000000    # Token limits vary by model
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

### "Rate limit: X/5 requests per minute"
- You've hit the per-minute limit (Gemini free tier is very restrictive!)
- App will automatically wait ~1 minute before retrying
- Consider using gemini-2.5-flash-lite (10 req/min) if available
- Or switch to MarianMT backend for faster batch processing

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
