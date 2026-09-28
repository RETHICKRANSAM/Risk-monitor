"""Rollback Management and Circuit Breaker API Routes."""

from flask import Blueprint, jsonify, request
from services.rollback_service import (
    _load_rollback_events,
    get_rollback_config,
    save_rollback_config,
    trigger_automated_rollback,
)

rollbacks_bp = Blueprint("rollbacks", __name__)


@rollbacks_bp.route("/api/rollbacks", methods=["GET"])
def list_rollbacks():
    """List all automated circuit-breaker rollback events."""
    events = _load_rollback_events()
    return jsonify({
        "rollbacks": events,
        "count": len(events),
    }), 200


@rollbacks_bp.route("/api/rollbacks/trigger", methods=["POST"])
def manual_trigger():
    """Manually invoke a circuit-breaker rollback."""
    data = request.get_json(force=True, silent=True) or {}
    release_id = data.get("release_id", "MANUAL-TRIGGER")
    reason = data.get("reason", "Operator manual circuit breaker activation")
    risk_score = data.get("risk_score", 100)
    target_version = data.get("target_version", "v1.0-stable")

    event = trigger_automated_rollback(
        release_id=release_id,
        reason=reason,
        risk_score=risk_score,
        metrics=data.get("metrics"),
        target_version=target_version,
    )
    return jsonify({
        "message": "Rollback executed successfully",
        "rollback": event,
    }), 201


@rollbacks_bp.route("/api/rollbacks/config", methods=["GET", "POST"])
def rollback_config():
    """Get or update rollback webhook configuration."""
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        cfg = get_rollback_config()
        if "webhook_url" in data:
            cfg["webhook_url"] = data["webhook_url"]
        if "enabled" in data:
            cfg["enabled"] = bool(data["enabled"])
        if "target_orchestrator" in data:
            cfg["target_orchestrator"] = data["target_orchestrator"]
        save_rollback_config(cfg)
        return jsonify({"message": "Configuration updated", "config": cfg}), 200
    return jsonify({"config": get_rollback_config()}), 200
