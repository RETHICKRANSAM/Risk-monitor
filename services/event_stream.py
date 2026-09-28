"""Real-Time Event Streaming (Server-Sent Events) Service for Falcon Eye.

Allows web clients (dashboards, audit monitors) to receive live updates
whenever deployment decisions, metrics, or rollbacks are recorded.
"""

import json
import queue
import threading
import time
from collections.abc import Generator

# Thread-safe subscriber list
_subscribers: list[queue.Queue] = []
_lock = threading.Lock()


def subscribe() -> queue.Queue:
    """Subscribe a client to real-time events."""
    q = queue.Queue(maxsize=100)
    with _lock:
        _subscribers.append(q)
    return q


def unsubscribe(q: queue.Queue):
    """Remove client from subscribers."""
    with _lock:
        if q in _subscribers:
            _subscribers.remove(q)


def broadcast_event(event_type: str, data: dict):
    """Publish an event to all active SSE subscribers."""
    payload = {
        "event": event_type,
        "timestamp": time.time(),
        "data": data,
    }
    with _lock:
        stale = []
        for q in _subscribers:
            try:
                q.put_nowait(payload)
            except queue.Full:
                stale.append(q)
        for s in stale:
            if s in _subscribers:
                _subscribers.remove(s)


def event_generator(q: queue.Queue, timeout: float = 15.0) -> Generator[str, None, None]:
    """Yield SSE-formatted data frames, sending periodic heartbeats."""
    # Send initial connection frame
    yield f"event: connected\ndata: {json.dumps({'status': 'connected', 'time': time.time()})}\n\n"
    while True:
        try:
            msg = q.get(timeout=timeout)
            event_name = msg.get("event", "message")
            data_str = json.dumps(msg.get("data", {}))
            yield f"event: {event_name}\ndata: {data_str}\n\n"
        except queue.Empty:
            # Send SSE keep-alive comment
            yield ": ping\n\n"
