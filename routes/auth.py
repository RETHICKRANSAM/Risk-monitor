"""Authentication routes."""

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash

from models import User

auth_bp = Blueprint("auth", __name__)


from security.rate_limiter import rate_limit, reset_rate_limit


@auth_bp.route("/api/login", methods=["POST"])
@auth_bp.route("/api/auth/login", methods=["POST"])
@rate_limit(max_requests=25, window_seconds=60)
def login():
    """Authenticate user and create session."""
    data = request.get_json()

    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "Username and password are required"}), 400

    user = User.query.filter_by(username=data["username"]).first()

    if not user or not check_password_hash(user.password_hash, data["password"]):
        return jsonify({"error": "Invalid username or password"}), 401

    # Reset failed attempts counter on success
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote_addr or "127.0.0.1"
    reset_rate_limit(f"auth.login:{client_ip}")

    # Set session
    session["user_id"] = user.id
    session["username"] = user.username
    session["name"] = user.name
    session["role"] = user.role
    session["org_id"] = user.org_id
    session["org_name"] = user.organization.name

    return jsonify(
        {
            "message": "Login successful",
            "user": user.to_dict(),
        }
    )


@auth_bp.route("/api/logout", methods=["POST"])
def logout():
    """Clear session."""
    session.clear()
    return jsonify({"message": "Logged out successfully"})


@auth_bp.route("/api/me", methods=["GET"])
def get_current_user():
    """Return current user info."""
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    from middleware import get_current_user_info

    return jsonify(get_current_user_info())
