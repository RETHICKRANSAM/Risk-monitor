"""Middleware for role-based access control and organization filtering."""

from functools import wraps

from flask import jsonify, session

# Role hierarchy and permissions
ROLE_PERMISSIONS = {
    "release_engineer": {
        "can_view_dashboard": True,
        "can_view_risk_detail": True,
        "can_approve_release": True,
        "can_submit_release": True,
        "can_submit_metrics": True,
        "can_view_evidence": True,
        "can_view_audit": False,
        "org_restricted": True,
    },
    "compliance_officer": {
        "can_view_dashboard": True,
        "can_view_risk_detail": True,
        "can_approve_release": True,
        "can_submit_release": False,
        "can_submit_metrics": False,
        "can_view_evidence": True,
        "can_view_audit": True,
        "org_restricted": True,
    },
    "sre": {
        "can_view_dashboard": True,
        "can_view_risk_detail": True,
        "can_approve_release": False,
        "can_submit_release": True,
        "can_submit_metrics": True,
        "can_view_evidence": True,
        "can_view_audit": False,
        "org_restricted": True,
    },
    "external_partner": {
        "can_view_dashboard": True,
        "can_view_risk_detail": True,
        "can_approve_release": False,
        "can_submit_release": False,
        "can_submit_metrics": False,
        "can_view_evidence": False,
        "can_view_audit": False,
        "org_restricted": True,
    },
    "auditor": {
        "can_view_dashboard": True,
        "can_view_risk_detail": True,
        "can_approve_release": False,
        "can_submit_release": False,
        "can_submit_metrics": False,
        "can_view_evidence": True,
        "can_view_audit": True,
        "org_restricted": False,  # Auditors can see all orgs
    },
}


def login_required(f):
    """Decorator to require authentication, with prototype session fallback."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request
        if "user_id" not in session:
            # Check query param, header, or initialize default demo session
            user_param = request.headers.get("X-User") or request.args.get("user") or "alice_re"
            session["user_id"] = user_param
            session["username"] = user_param
            session["name"] = "Alice Johnson" if "alice" in user_param else user_param
            session["role"] = "auditor" if "audit" in user_param else ("compliance_officer" if "co" in user_param else "release_engineer")
            session["org_id"] = None if "audit" in user_param else "BankA"
        return f(*args, **kwargs)

    return decorated_function


def require_permission(permission):
    """Decorator to require a specific permission."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return jsonify({"error": "Authentication required"}), 401

            role = session.get("role")
            if not role or role not in ROLE_PERMISSIONS:
                return jsonify({"error": "Invalid role"}), 403

            if not ROLE_PERMISSIONS[role].get(permission, False):
                return jsonify({"error": f"Permission denied: {permission}"}), 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def get_org_filter():
    """Get the organization filter for the current user.
    Returns None if user can see all orgs (e.g., auditor).
    """
    role = session.get("role")
    if not role:
        return None

    permissions = ROLE_PERMISSIONS.get(role, {})
    if permissions.get("org_restricted", True):
        return session.get("org_id")
    return None


def get_current_user_info():
    """Get current user info from session."""
    return {
        "user_id": session.get("user_id"),
        "username": session.get("username"),
        "name": session.get("name"),
        "role": session.get("role"),
        "org_id": session.get("org_id"),
        "org_name": session.get("org_name"),
        "permissions": ROLE_PERMISSIONS.get(str(session.get("role")), {}),
    }
