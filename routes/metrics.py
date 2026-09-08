"""Metrics submission routes."""

from flask import Blueprint, jsonify, request

from middleware import get_org_filter, login_required, require_permission
from models import DeploymentMetric, Release, RiskDecision, db
from risk_engine import evaluate_release

metrics_bp = Blueprint("metrics", __name__)


@metrics_bp.route("/api/metrics", methods=["POST"])
@require_permission("can_submit_metrics")
def submit_metrics():
    """Submit deployment metrics for a release (FR-2).
    Automatically triggers risk evaluation.
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    if not data.get("release_id"):
        return jsonify({"error": "release_id is required"}), 400

    # Find the release
    release = Release.query.filter_by(release_id=data["release_id"]).first()
    if not release:
        return jsonify({"error": f"Release not found: {data['release_id']}"}), 404

    # Check org access
    org_filter = get_org_filter()
    if org_filter and release.org_id != org_filter:
        return jsonify({"error": "Access denied"}), 403

    # Create metrics record
    metric = DeploymentMetric(
        release_id=release.id,
        error_rate=_safe_float(data.get("error_rate")),
        latency_ms=_safe_int(data.get("latency_ms")),
        availability=_safe_float(data.get("availability")),
        error_budget_remaining=_safe_float(data.get("error_budget_remaining")),
        canary_error_rate=_safe_float(data.get("canary_error_rate")),
        canary_latency_delta=_safe_int(data.get("canary_latency_delta")),
        cpu_usage=_safe_float(data.get("cpu_usage")),
        memory_usage=_safe_float(data.get("memory_usage")),
    )

    db.session.add(metric)
    db.session.flush()

    # Get historical metrics for smoothing
    historical = (
        DeploymentMetric.query.filter_by(
            release_id=release.id,
        )
        .filter(
            DeploymentMetric.id != metric.id,
        )
        .order_by(DeploymentMetric.created_at.asc())
        .all()
    )

    historical_dicts = [m.to_dict() for m in historical]

    # Check if canary data is available
    canary_available = (
        data.get("canary_error_rate") is not None
        or data.get("canary_latency_delta") is not None
    )

    # Run risk evaluation
    metrics_dict = metric.to_dict()
    evaluation = evaluate_release(
        metrics_dict,
        historical_metrics=historical_dicts or None,
        canary_available=canary_available,
    )

    # Store the risk decision (FR-6)
    reasons_text = (
        "; ".join(
            [r["rule"] for r in evaluation.get("reasons", [])],
        )
        if evaluation.get("reasons")
        else "No risk factors triggered"
    )

    decision = RiskDecision(
        release_id=release.id,
        risk_score=evaluation["risk_score"],
        decision=evaluation["decision"],
        reasons=reasons_text,
        reviewer="system",
    )

    db.session.add(decision)
    db.session.commit()

    return jsonify(
        {
            "message": "Metrics submitted and evaluated",
            "metrics": metric.to_dict(),
            "evaluation": {
                "risk_score": evaluation["risk_score"],
                "decision": evaluation["decision"],
                "reasons": evaluation.get("reasons", []),
                "warnings": evaluation.get("warnings"),
            },
            "decision": decision.to_dict(),
        }
    ), 201


@metrics_bp.route("/api/metrics/<release_id>", methods=["GET"])
@login_required
def get_metrics(release_id):
    """Get all metrics for a release."""
    release = Release.query.filter_by(release_id=release_id).first()
    if not release:
        return jsonify({"error": "Release not found"}), 404

    org_filter = get_org_filter()
    if org_filter and release.org_id != org_filter:
        return jsonify({"error": "Access denied"}), 403

    metrics = (
        DeploymentMetric.query.filter_by(
            release_id=release.id,
        )
        .order_by(DeploymentMetric.created_at.asc())
        .all()
    )

    return jsonify(
        {
            "release_id": release_id,
            "metrics": [m.to_dict() for m in metrics],
        }
    )


def _safe_float(val):
    """Safely convert to float, return None on failure."""
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val):
    """Safely convert to int, return None on failure."""
    if val is None or val == "":
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None
