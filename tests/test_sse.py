"""Tests for Real-Time Event Streaming (Server-Sent Events) Service."""

from services.event_stream import broadcast_event, event_generator, subscribe, unsubscribe


def test_sse_subscribe_and_broadcast():
    """Verify subscribing, publishing, and receiving real-time event frames."""
    q = subscribe()
    try:
        broadcast_event("test_event", {"message": "hello live stream"})
        gen = event_generator(q, timeout=0.5)

        # First frame is connected status
        frame1 = next(gen)
        assert "event: connected" in frame1

        # Second frame is our broadcast event
        frame2 = next(gen)
        assert "event: test_event" in frame2
        assert "hello live stream" in frame2
    finally:
        unsubscribe(q)
