"""Dashboard and evidence report routes."""

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from middleware import get_org_filter, login_required, require_permission
from models import DeploymentMetric, Organization, Release, RiskDecision, db

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/api/dashboard", methods=["GET"])
@login_required
def get_dashboard():
    """Return dashboard summary data (filtered by org/role)."""
    org_filter = get_org_filter()

    # Base query
    release_query = Release.query
    if org_filter:
        release_query = release_query.filter_by(org_id=org_filter)

    total_releases = release_query.count()

    # Get decision counts
    decision_counts = {"ALLOW": 0, "PAUSE": 0, "BLOCK": 0}

    # Get latest decision for each release
    releases = release_query.all()
    recent_releases = []

    for release in releases:
        latest_decision = (
            RiskDecision.query.filter_by(
                release_id=release.id,
            )
            .order_by(RiskDecision.decided_at.desc())
            .first()
        )

        if latest_decision:
            decision_counts[latest_decision.decision] = (
                decision_counts.get(latest_decision.decision, 0) + 1
            )

        latest_metric = (
            DeploymentMetric.query.filter_by(
                release_id=release.id,
            )
            .order_by(DeploymentMetric.created_at.desc())
            .first()
        )

        recent_releases.append(
            {
                **release.to_dict(),
                "latest_decision": latest_decision.to_dict()
                if latest_decision
                else None,
                "latest_metric": latest_metric.to_dict() if latest_metric else None,
            }
        )

    # Sort by deployed_at descending
    # Average risk score
    avg_query = db.session.query(func.avg(RiskDecision.risk_score))
    if org_filter:
        avg_query = avg_query.join(
            Release, RiskDecision.release_id == Release.id
        ).filter(Release.org_id == org_filter)
    avg_risk = avg_query.scalar()

    # Risk score distribution for charts
    risk_distribution = []
    all_decisions = db.session.query(RiskDecision).all()
    for d in all_decisions:
        rel = db.session.get(Release, d.release_id)
        if org_filter and rel and rel.org_id != org_filter:
            continue
        risk_distribution.append(
            {
                "release_id": rel.release_id if rel else None,
                "risk_score": d.risk_score,
                "decision": d.decision,
                "decided_at": d.decided_at.isoformat() if d.decided_at else None,
            }
        )

    # Sort recent_releases using a safer key (handling None)
    recent_releases.sort(key=lambda r: r.get("deployed_at") or "", reverse=True)

    # Organization breakdown
    org_breakdown = []
    if not org_filter:
        orgs = Organization.query.all()
        for org in orgs:
            org_releases = Release.query.filter_by(org_id=org.id).count()
            org_breakdown.append(
                {
                    "org_id": org.id,
                    "org_name": org.name,
                    "release_count": org_releases,
                }
            )

    return jsonify(
        {
            "summary": {
                "total_releases": total_releases,
                "allowed": decision_counts.get("ALLOW", 0),
                "paused": decision_counts.get("PAUSE", 0),
                "blocked": decision_counts.get("BLOCK", 0),
                "average_risk_score": round(float(avg_risk), 1) if avg_risk else 0,
            },
            "recent_releases": recent_releases[:20],
            "org_breakdown": org_breakdown,
            "risk_distribution": risk_distribution,
        }
    )


@dashboard_bp.route("/api/report/<release_id>", methods=["GET"])
@login_required
def get_evidence_report(release_id):
    """Return full evidence report for a release (FR-6)."""
    release = Release.query.filter_by(release_id=release_id).first()

    if not release:
        return jsonify({"error": "Release not found"}), 404

    # Check org access
    org_filter = get_org_filter()
    if org_filter and release.org_id != org_filter:
        return jsonify({"error": "Access denied"}), 403

    # Gather all evidence
    metrics = (
        DeploymentMetric.query.filter_by(
            release_id=release.id,
        )
        .order_by(DeploymentMetric.created_at.asc())
        .all()
    )

    decisions = (
        RiskDecision.query.filter_by(
            release_id=release.id,
        )
        .order_by(RiskDecision.decided_at.asc())
        .all()
    )

    return jsonify(
        {
            "report": {
                "release": release.to_dict(),
                "organization": release.organization.to_dict()
                if release.organization
                else None,
                "metrics_history": [m.to_dict() for m in metrics],
                "decision_history": [d.to_dict() for d in decisions],
                "current_stage": release.stage,
                "total_evaluations": len(decisions),
                "final_decision": decisions[-1].to_dict() if decisions else None,
            },
        }
    )


@dashboard_bp.route("/api/audit", methods=["GET"])
@require_permission("can_view_audit")
def get_audit_history():
    """Return audit history of all deployment decisions."""
    org_filter = get_org_filter()

    # Get all decisions with release info
    query = db.session.query(RiskDecision, Release).join(
        Release,
        RiskDecision.release_id == Release.id,
    )

    if org_filter:
        query = query.filter(Release.org_id == org_filter)

    # Date filters
    from_date = request.args.get("from")
    to_date = request.args.get("to")
    decision_filter = request.args.get("decision")
    org_name_filter = request.args.get("org")

    if from_date:
        from datetime import datetime

        try:
            query = query.filter(
                RiskDecision.decided_at >= datetime.fromisoformat(from_date)
            )
        except ValueError:
            pass

    if to_date:
        from datetime import datetime

        try:
            query = query.filter(
                RiskDecision.decided_at <= datetime.fromisoformat(to_date)
            )
        except ValueError:
            pass

    if decision_filter:
        query = query.filter(RiskDecision.decision == decision_filter.upper())

    if org_name_filter:
        org = Organization.query.filter_by(name=org_name_filter).first()
        if org:
            query = query.filter(Release.org_id == org.id)

    results = query.order_by(RiskDecision.decided_at.desc()).all()

    audit_records = []
    for decision, release in results:
        audit_records.append(
            {
                **decision.to_dict(),
                "release_info": release.to_dict(),
            }
        )

    return jsonify(
        {
            "audit_records": audit_records,
            "total_count": len(audit_records),
        }
    )


@dashboard_bp.route("/api/organizations", methods=["GET"])
@login_required
def list_organizations():
    """List all organizations (for filter dropdowns)."""
    org_filter = get_org_filter()

    if org_filter:
        orgs = Organization.query.filter_by(id=org_filter).all()
    else:
        orgs = Organization.query.all()

    return jsonify({"organizations": [o.to_dict() for o in orgs]})
