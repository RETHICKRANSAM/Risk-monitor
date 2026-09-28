"""Automated Rollback Circuit-Breaker Service.

Dispatches instant rollback triggers to orchestrators (Kubernetes / ArgoCD / Slack)
whenever a BLOCK risk decision is reached by the risk evaluation engine.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
import urllib.request
import urllib.error
from services.event_stream import broadcast_event

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
ROLLBACKS_FILE = os.path.join(DATA_DIR, "rollback_events.json")
CONFIG_FILE = os.path.join(DATA_DIR, "rollback_config.json")


def get_rollback_config() -> dict:
    """Load rollback target configuration."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "enabled": True,
        "webhook_url": os.getenv("ROLLBACK_WEBHOOK_URL", ""),
        "auto_rollback_on_block": True,
        "target_orchestrator": "kubernetes-argocd",
    }


def save_rollback_config(config: dict):
    """Save rollback configuration."""
    os.makedirs(DATA_DIR, exist_ok=True)
    temp_file = f"{CONFIG_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    os.replace(temp_file, CONFIG_FILE)


def _load_rollback_events() -> list:
    if os.path.exists(ROLLBACKS_FILE):
        try:
            with open(ROLLBACKS_FILE, encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    return []


def _save_rollback_events(events: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    temp_file = f"{ROLLBACKS_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)
    os.replace(temp_file, ROLLBACKS_FILE)


def trigger_automated_rollback(
    release_id: str,
    reason: str,
    risk_score: int,
    metrics: dict = None,
    target_version: str = "previous_stable",
) -> dict:
    """Execute automated circuit-breaker rollback and dispatch webhook."""
    now = datetime.now(timezone.utc).isoformat()
    raw_sig = f"{release_id}:{risk_score}:{now}"
    signature = hashlib.sha256(raw_sig.encode("utf-8")).hexdigest()

    event = {
        "event_id": hashlib.md5(raw_sig.encode("utf-8")).hexdigest()[:10],
        "release_id": release_id,
        "status": "ROLLBACK_EXECUTED",
        "action": "HALT_AND_ROLLBACK",
        "reason": reason,
        "risk_score": risk_score,
        "target_version": target_version,
        "metrics_snapshot": metrics or {},
        "triggered_at": now,
        "circuit_breaker_hash": signature,
    }

    # Persist event
    events = _load_rollback_events()
    events.insert(0, event)
    _save_rollback_events(events[:100])

    # Broadcast live SSE update to UI
    broadcast_event("rollback_executed", event)

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
        except Exception as e:
            event["dispatch_status"] = f"FAILED: {e}"
    else:
        event["dispatch_status"] = "LOGGED_LOCAL_SIMULATOR"

    return event
