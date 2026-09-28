"""In-Memory Sliding-Window Rate Limiter for Brute-Force & DoS Protection."""

from collections import defaultdict
from functools import wraps
import threading
import time
from flask import jsonify, request

_attempts = defaultdict(list)
_lock = threading.Lock()


def is_rate_limited(key: str, max_requests: int = 15, window_seconds: int = 60) -> tuple[bool, int]:
    """Check if key has exceeded allowed request threshold in sliding window."""
    now = time.time()
    cutoff = now - window_seconds
    with _lock:
        timestamps = [t for t in _attempts[key] if t > cutoff]
        _attempts[key] = timestamps

        if len(timestamps) >= max_requests:
            oldest = timestamps[0]
            retry_after = max(1, int(window_seconds - (now - oldest)))
            return True, retry_after

        _attempts[key].append(now)
        return False, max_requests - len(_attempts[key])


def reset_rate_limit(key: str):
    """Clear recorded attempts for key upon successful authentication."""
    with _lock:
        if key in _attempts:
            del _attempts[key]


def rate_limit(max_requests: int = 15, window_seconds: int = 60):
    """Decorator to enforce request rate limits on sensitive endpoints."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Client IP identifier
            client_ip = (
                request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                or request.remote_addr
                or "127.0.0.1"
            )
            key = f"{request.endpoint}:{client_ip}"
            limited, val = is_rate_limited(key, max_requests, window_seconds)
            if limited:
                resp = jsonify({
                    "error": "Too many requests. Rate limit exceeded.",
                    "retry_after": val,
                })
                resp.status_code = 429
                resp.headers["Retry-After"] = str(val)
                return resp
            return f(*args, **kwargs)
        return decorated_function
    return decorator
