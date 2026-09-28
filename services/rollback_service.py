"""Automated Rollback Circuit-Breaker Service.

Dispatches instant rollback triggers to orchestrators (Kubernetes / ArgoCD / Slack)
whenever a BLOCK risk decision is reached by the risk evaluation engine.
"""

import hashlib
import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

from services.event_stream import broadcast_event

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
ROLLBACKS_FILE = os.path.join(DATA_DIR, "rollback_events.json")
CONFIG_FILE = os.path.join(DATA_DIR, "rollback_config.json")


def get_rollback_config() -> dict:
    """Load rollback target configuration."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to load rollback config: %s", e)
    return {
        "enabled": True,
        "webhook_url": os.getenv("ROLLBACK_WEBHOOK_URL", ""),
        "auto_rollback_on_block": True,
        "target_orchestrator": "kubernetes-argocd",
    }


def save_rollback_config(config: dict):
    """Save rollback configuration atomically."""
    os.makedirs(DATA_DIR, exist_ok=True)
    temp_file = f"{CONFIG_FILE}.tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        os.replace(temp_file, CONFIG_FILE)
    except OSError as e:
        logger.error("Failed to write rollback config: %s", e)
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass


def list_rollback_events() -> list:
    """Retrieve history of automated rollback events."""
    if not os.path.exists(ROLLBACKS_FILE):
        return []
    try:
        with open(ROLLBACKS_FILE, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Failed to load rollback events: %s", e)
        return []


def _save_rollback_events(events: list):
    """Persist rollback events list atomically."""
    os.makedirs(DATA_DIR, exist_ok=True)
    temp_file = f"{ROLLBACKS_FILE}.tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2)
        os.replace(temp_file, ROLLBACKS_FILE)
    except OSError as e:
        logger.error("Failed to persist rollback events: %s", e)
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass


def trigger_automated_rollback(
    release_id: str,
    reason: str,
    risk_score: int,
    metrics: dict | None = None,
    target_version: str = "previous_stable",
) -> dict:
    """Execute automated circuit-breaker rollback and dispatch webhook."""
    now = datetime.now(timezone.utc).isoformat()
    raw_sig = f"{release_id}:{risk_score}:{now}"
    signature = hashlib.sha256(raw_sig.encode("utf-8")).hexdigest()
    event_id = signature[:12]

    event = {
        "event_id": event_id,
        "release_id": release_id,
        "status": "ROLLBACK_EXECUTED",
        "action": "HALT_AND_ROLLBACK",
        "reason": reason,
        "risk_score": risk_score,
        "target_version": target_version,
        "metrics_snapshot": metrics or {},
        "triggered_at": now,
        "circuit_breaker_hash": signature,
        "dispatch_status": "LOGGED_LOCAL_SIMULATOR",
    }

    # Dispatch to outbound webhook if configured
    config = get_rollback_config()
    webhook_url = config.get("webhook_url")
    if webhook_url and webhook_url.startswith("http"):
        try:
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(event).encode("utf-8"),
                headers={"Content-Type": "application/json", "X-Event-Type": "circuit_breaker_rollback"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=3.0)
            event["dispatch_status"] = "SENT"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            logger.warning("Rollback webhook dispatch error: %s", e)
            event["dispatch_status"] = f"FAILED: {e}"

    # Persist event atomically
    events = list_rollback_events()
    events.insert(0, event)
    _save_rollback_events(events[:100])

    # Broadcast live SSE update to UI
    broadcast_event("rollback_executed", event)

    return event
