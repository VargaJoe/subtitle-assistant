"""Persistent legacy quotas never approve a request that remains over quota."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from subtitle_translator.core.rate_limiter import APIRateLimiter, RateLimitConfig, UsageRecord


ROOT = Path(__file__).resolve().parents[2]


class RateLimiterTests(unittest.TestCase):
    def setUp(self):
        temporary_root = ROOT / "temp" / "rate-limiter-tests"
        temporary_root.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=temporary_root)
        self.addCleanup(self.temporary.cleanup)
        self.now = 100000.0
        self.monotonic = 1000.0
        self.sleeps = []
        self.after_sleep = None
        for target, effect in (
            ("time", lambda: self.now),
            ("monotonic", lambda: self.monotonic),
            ("sleep", self.sleep),
        ):
            mocked = patch(f"subtitle_translator.core.rate_limiter.time.{target}", side_effect=effect)
            mocked.start()
            self.addCleanup(mocked.stop)
        self.limiter = APIRateLimiter(storage_dir=Path(self.temporary.name))

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds
        self.monotonic += seconds
        if self.after_sleep is not None:
            self.after_sleep()

    def records(self, age, requests=1, tokens=0, count=1):
        return [UsageRecord(self.now - age, requests, tokens) for _ in range(count)]

    def test_allowed_request_keeps_no_wait_false_result(self):
        self.assertFalse(self.limiter.wait_if_needed())
        self.assertEqual(self.sleeps, [])
        self.assertTrue(self.limiter.check_rate_limit()[0])

    def test_minute_wait_rechecks_before_returning_true(self):
        self.limiter.usage_history = self.records(1, count=5)
        self.assertTrue(self.limiter.wait_if_needed(max_wait=60))
        self.assertEqual(self.sleeps, [60])
        self.assertTrue(self.limiter.check_rate_limit()[0])

    def test_hour_wait_uses_hour_window(self):
        self.limiter.config.requests_per_day = 1000
        self.limiter.usage_history = self.records(100, count=50)
        self.assertTrue(self.limiter.wait_if_needed(max_wait=3600))
        self.assertEqual(self.sleeps, [3501])
        self.assertTrue(self.limiter.check_rate_limit()[0])

    def test_daily_wait_within_budget_can_succeed(self):
        self.limiter.usage_history = self.records(86400 - 10, count=20)
        self.assertTrue(self.limiter.wait_if_needed(max_wait=11))
        self.assertEqual(self.sleeps, [11])
        self.assertTrue(self.limiter.check_rate_limit()[0])

    def test_daily_wait_over_budget_does_not_sleep(self):
        self.limiter.usage_history = self.records(3600, count=20)
        self.assertFalse(self.limiter.wait_if_needed(max_wait=3600))
        self.assertEqual(self.sleeps, [])

    def test_minute_quota_cannot_hide_exhausted_daily_quota(self):
        self.limiter.usage_history = self.records(1, count=5) + self.records(3600, count=15)
        self.assertFalse(self.limiter.wait_if_needed(max_wait=3600))
        self.assertEqual(self.sleeps, [])
        self.assertFalse(self.limiter.check_rate_limit()[0])

    def test_token_wait_expires_enough_usage_not_only_the_oldest_record(self):
        self.limiter.usage_history = self.records(59, tokens=10000) + self.records(1, tokens=240000)
        self.assertTrue(self.limiter.wait_if_needed(tokens=20000, max_wait=60))
        self.assertEqual(self.sleeps, [60])
        self.assertTrue(self.limiter.check_rate_limit(tokens=20000)[0])

    def test_request_wait_expires_enough_weighted_records(self):
        self.limiter.usage_history = self.records(59) + self.records(1, requests=5)
        self.assertTrue(self.limiter.wait_if_needed(max_wait=60))
        self.assertEqual(self.sleeps, [60])
        self.assertTrue(self.limiter.check_rate_limit()[0])

    def test_simultaneous_minute_and_hour_quotas_use_the_longer_wait(self):
        self.limiter.config.requests_per_day = 1000
        self.limiter.usage_history = self.records(1, count=5) + self.records(100, count=45)
        self.assertTrue(self.limiter.wait_if_needed(max_wait=3600))
        self.assertEqual(self.sleeps, [3501])
        self.assertTrue(self.limiter.check_rate_limit()[0])

    def test_request_larger_than_token_quota_fails_without_sleeping(self):
        self.assertFalse(self.limiter.wait_if_needed(tokens=250001, max_wait=3600))
        self.assertEqual(self.sleeps, [])

    def test_wait_budget_is_shared_across_rechecks_after_new_usage(self):
        self.limiter.config = RateLimitConfig(requests_per_minute=1, requests_per_day=1000)
        self.limiter.usage_history = self.records(50)
        self.after_sleep = lambda: self.limiter.usage_history.extend(self.records(0))
        self.assertFalse(self.limiter.wait_if_needed(max_wait=60))
        self.assertEqual(self.sleeps, [11])
        self.assertFalse(self.limiter.check_rate_limit()[0])

    def test_new_usage_during_sleep_can_be_waited_out_with_remaining_budget(self):
        self.limiter.config = RateLimitConfig(requests_per_minute=1, requests_per_day=1000)
        self.limiter.usage_history = self.records(50)

        def one_new_request():
            self.limiter.usage_history.extend(self.records(0))
            self.after_sleep = None

        self.after_sleep = one_new_request
        self.assertTrue(self.limiter.wait_if_needed(max_wait=80))
        self.assertEqual(self.sleeps, [11, 61])
        self.assertTrue(self.limiter.check_rate_limit()[0])

    def test_usage_survives_a_new_limiter_instance(self):
        self.limiter.record_usage(requests=2, tokens=123)
        reloaded = APIRateLimiter(storage_dir=Path(self.temporary.name))
        self.assertEqual(reloaded.usage_history, [UsageRecord(self.now, requests=2, tokens=123)])
        self.assertEqual(reloaded.get_stats()["per_minute"], {"requests": "2/5", "tokens": "123/250000"})


if __name__ == "__main__":
    unittest.main()
