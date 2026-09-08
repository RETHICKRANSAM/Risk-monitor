"""Release management routes."""

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

from middleware import get_org_filter, login_required, require_permission
from models import Organization, Release, RiskDecision, db

releases_bp = Blueprint("releases", __name__)


@releases_bp.route("/api/release", methods=["POST"])
@require_permission("can_submit_release")
def create_release():
    """Create a new release event (FR-1)."""
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    required_fields = ["release_id", "org", "version"]
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Lookup organization
    org = Organization.query.filter_by(name=data["org"]).first()
    if not org:
        return jsonify({"error": f"Organization not found: {data['org']}"}), 404

    # Check RBAC - user can only create releases for their org
    user_org_id = session.get("org_id")
    user_role = session.get("role")
    if user_role != "auditor" and org.id != user_org_id:
        return jsonify({"error": "Cannot create release for another organization"}), 403

    # Check if release already exists
    existing = Release.query.filter_by(
        release_id=data["release_id"], org_id=org.id
    ).first()
    if existing:
        return jsonify({"error": f"Release {data['release_id']} already exists"}), 409

    release = Release(
        release_id=data["release_id"],
        org_id=org.id,
        version=data["version"],
        stage=data.get("stage", "canary"),
        deployed_at=datetime.now(timezone.utc),
    )

    db.session.add(release)
    db.session.commit()

    return jsonify(
        {
            "message": "Release created successfully",
            "release": release.to_dict(),
        }
    ), 201


@releases_bp.route("/api/releases", methods=["GET"])
@login_required
def list_releases():
    """List releases filtered by organization."""
    org_filter = get_org_filter()

    query = Release.query

    if org_filter:
        query = query.filter_by(org_id=org_filter)

    # Optional filters
    org_name = request.args.get("org")
    if org_name:
        org = Organization.query.filter_by(name=org_name).first()
        if org:
            query = query.filter_by(org_id=org.id)

    stage = request.args.get("stage")
    if stage:
        query = query.filter_by(stage=stage)

    releases = query.order_by(Release.deployed_at.desc()).all()

    result = []
    for release in releases:
        release_dict = release.to_dict()
        # Attach latest decision if any
        latest_decision = (
            RiskDecision.query.filter_by(
                release_id=release.id,
            )
            .order_by(RiskDecision.decided_at.desc())
            .first()
        )
        if latest_decision:
            release_dict["latest_decision"] = latest_decision.to_dict()
        else:
            release_dict["latest_decision"] = None
        result.append(release_dict)

    return jsonify({"releases": result})


@releases_bp.route("/api/release/<release_id>", methods=["GET"])
@login_required
def get_release(release_id):
    """Get release details including metrics and decisions."""
    release = Release.query.filter_by(release_id=release_id).first()

    if not release:
        return jsonify({"error": "Release not found"}), 404

    # Check org access
    org_filter = get_org_filter()
    if org_filter and release.org_id != org_filter:
        return jsonify({"error": "Access denied"}), 403

    release_dict = release.to_dict()
    release_dict["metrics"] = [m.to_dict() for m in release.metrics]
    release_dict["decisions"] = [d.to_dict() for d in release.decisions]

    return jsonify({"release": release_dict})


@releases_bp.route("/api/release/<release_id>/approve", methods=["POST"])
@require_permission("can_approve_release")
def approve_release(release_id):
    """Approve or reject a release rollout continuation."""
    data = request.get_json() or {}

    release = Release.query.filter_by(release_id=release_id).first()
    if not release:
        return jsonify({"error": "Release not found"}), 404

    org_filter = get_org_filter()
    if org_filter and release.org_id != org_filter:
        return jsonify({"error": "Access denied"}), 403

    action = data.get("action", "approve")  # 'approve' or 'reject'

    if action == "approve":
        release.stage = "production"
        reviewer_note = f"Approved by {session.get('name', 'unknown')}"
    else:
        release.stage = "canary"  # Keep in canary
        reviewer_note = f"Rejected by {session.get('name', 'unknown')}: {data.get('reason', 'No reason given')}"

    # Record the decision
    decision = RiskDecision(
        release_id=release.id,
        risk_score=0,
        decision="ALLOW" if action == "approve" else "BLOCK",
        reasons=reviewer_note,
        reviewer=session.get("username"),
    )

    db.session.add(decision)
    db.session.commit()

    return jsonify(
        {
            "message": f"Release {action}d successfully",
            "release": release.to_dict(),
            "decision": decision.to_dict(),
        }
    )
