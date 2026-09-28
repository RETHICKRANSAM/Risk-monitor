"""Authentication and RBAC Security Regression Tests.

Verifies:
1. URL query parameters (e.g. ?user=iris_audit) CANNOT bypass authentication or impersonate auditor.
2. X-User headers CANNOT bypass authentication.
3. Authenticated users CANNOT escalate privileges by appending query parameters.
4. Server-side RBAC is strictly enforced for protected actions.
5. Sessions must be explicitly established via /api/login and invalidated upon /api/logout.
"""

import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config.update({"TESTING": True})
    with app.test_client() as client:
        yield client


def test_unauthenticated_requests_return_401(client):
    """Unauthenticated access to protected routes must be rejected."""
    resp = client.get("/api/dashboard")
    assert resp.status_code == 401
    assert "error" in resp.get_json()


def test_query_param_impersonation_rejected(client):
    """CRITICAL REGRESSION: ?user=iris_audit must NOT bypass auth or impersonate auditor."""
    # Test dashboard with ?user=iris_audit
    resp = client.get("/api/dashboard?user=iris_audit")
    assert resp.status_code == 401
    assert "error" in resp.get_json()

    # Test audit history with ?user=iris_audit
    resp = client.get("/api/audit?user=iris_audit")
    assert resp.status_code == 401

    # Test /api/me with ?user=iris_audit
    resp = client.get("/api/me?user=iris_audit")
    assert resp.status_code == 401


def test_header_impersonation_rejected(client):
    """X-User header must NOT bypass authentication."""
    resp = client.get("/api/dashboard", headers={"X-User": "iris_audit"})
    assert resp.status_code == 401

    resp = client.get("/api/me", headers={"X-User": "iris_audit"})
    assert resp.status_code == 401


def test_authenticated_user_cannot_privilege_escalate_via_url(client):
    """A logged-in user cannot change their identity or role using query parameters."""
    # Log in as release engineer (Alice)
    login_resp = client.post(
        "/api/login",
        json={"username": "alice_re", "password": "demo123"},
    )
    assert login_resp.status_code == 200

    # Verify identity is Alice
    me_resp = client.get("/api/me")
    assert me_resp.status_code == 200
    assert me_resp.get_json()["username"] == "alice_re"
    assert me_resp.get_json()["role"] == "release_engineer"

    # Attempt to impersonate auditor via ?user=iris_audit
    me_tampered = client.get("/api/me?user=iris_audit")
    assert me_tampered.status_code == 200
    # Role must STILL be release_engineer, NOT auditor
    assert me_tampered.get_json()["username"] == "alice_re"
    assert me_tampered.get_json()["role"] == "release_engineer"


def test_rbac_server_side_enforcement(client):
    """Server-side RBAC blocks unauthorized actions regardless of client parameters."""
    # Hank is external_partner (cannot approve releases, cannot submit releases)
    client.post(
        "/api/login",
        json={"username": "hank_ep", "password": "demo123"},
    )

    # Attempt to submit release -> must return 403 Forbidden
    resp = client.post(
        "/api/release",
        json={"release_id": "SEC-TEST-01", "org": "GovAgency", "version": "1.0"},
    )
    assert resp.status_code == 403

    # Attempt to approve release -> must return 403 Forbidden
    resp = client.post(
        "/api/release/REL-001/approve",
        json={"action": "approve"},
    )
    assert resp.status_code == 403


def test_logout_clears_session(client):
    """Logging out properly invalidates the session."""
    client.post(
        "/api/login",
        json={"username": "alice_re", "password": "demo123"},
    )
    assert client.get("/api/dashboard").status_code == 200

    logout_resp = client.post("/api/logout")
    assert logout_resp.status_code == 200

    # Subsequent request must be 401
    assert client.get("/api/dashboard").status_code == 401
