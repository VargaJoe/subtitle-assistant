#!/usr/bin/env python3
"""
Demo of rate limiting functionality for Gemini provider.
Shows how rate limits are tracked across sessions.
"""

from subtitle_translator.core.rate_limiter import APIRateLimiter, RateLimitConfig


def demo_rate_limiting():
    """Demonstrate rate limiting with persistent storage."""
    
    print("\n" + "="*60)
    print("GEMINI PROVIDER RATE LIMITING DEMO")
    print("="*60)
    
    # Create rate limiter
    limiter = APIRateLimiter(
        provider_name="gemini_demo",
        config=RateLimitConfig(
            requests_per_minute=5,  # Low for demo
            requests_per_hour=20,
            requests_per_day=50,
            tokens_per_minute=10000
        )
    )
    
    print(f"\n📊 Storage Location: {limiter.usage_file}")
    print("This file persists across sessions and multiple instances!")
    
    # Show initial stats
    print("\n📈 Current Usage Statistics:")
    stats = limiter.get_stats()
    for key, value in stats.items():
        if key != 'storage_file':
            print(f"  {key}: {value}")
    
    # Simulate some API calls
    print("\n\n🚀 Simulating API calls...")
    for i in range(3):
        print(f"\nCall {i+1}:")
        
        is_allowed, error = limiter.check_rate_limit(tokens=100)
        if is_allowed:
            print("  ✓ Rate limit OK")
            limiter.record_usage(requests=1, tokens=100)
            print("  ✓ Usage recorded")
        else:
            print(f"  ✗ Rate limit exceeded: {error}")
    
    # Show updated stats
    print("\n📈 Updated Usage Statistics:")
    stats = limiter.get_stats()
    for key, value in stats.items():
        if key != 'storage_file':
            print(f"  {key}: {value}")
    
    # Demonstrate persistence message
    print("\n\n🔄 PERSISTENCE ACROSS SESSIONS:")
    print("  If you run this script again, the usage stats will still be there!")
    print("  The rate limiter tracks usage in: data/rate_limits/gemini_demo_usage.json")
    
    # Show the actual file location
    print(f"\n📁 File: {limiter.usage_file}")
    print(f"   Exists: {limiter.usage_file.exists()}")
    
    print("\n" + "="*60)
    print("Rate limiting prevents DOS-ing the API across sessions!")
    print("="*60 + "\n")


if __name__ == "__main__":
    demo_rate_limiting()
