"""Authentication routes."""

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash

from models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/api/login", methods=["POST"])
def login():
    """Authenticate user and create session."""
    data = request.get_json()

    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "Username and password are required"}), 400

    user = User.query.filter_by(username=data["username"]).first()

    if not user or not check_password_hash(user.password_hash, data["password"]):
        return jsonify({"error": "Invalid username or password"}), 401

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
