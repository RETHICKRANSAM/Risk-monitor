"""Tests for Sliding-Window Rate Limiter and Brute-Force Defense."""

from security.rate_limiter import is_rate_limited, reset_rate_limit


def test_rate_limiter_permits_under_threshold():
    """Requests under threshold must be allowed."""
    key = "test_ip_allow"
    reset_rate_limit(key)
    for _ in range(5):
        limited, _ = is_rate_limited(key, max_requests=10, window_seconds=30)
        assert not limited


def test_rate_limiter_blocks_over_threshold():
    """Requests exceeding limit in window must be blocked."""
    key = "test_ip_block"
    reset_rate_limit(key)
    for _ in range(5):
        is_rate_limited(key, max_requests=5, window_seconds=30)

    # 6th attempt must be blocked
    limited, retry_after = is_rate_limited(key, max_requests=5, window_seconds=30)
    assert limited is True
    assert retry_after > 0


def test_rate_limiter_reset():
    """Resetting cleared attempts allows fresh requests immediately."""
    key = "test_ip_reset"
    reset_rate_limit(key)
    for _ in range(3):
        is_rate_limited(key, max_requests=3, window_seconds=30)

    limited, _ = is_rate_limited(key, max_requests=3, window_seconds=30)
    assert limited is True

    reset_rate_limit(key)
    limited, _ = is_rate_limited(key, max_requests=3, window_seconds=30)
    assert limited is False
