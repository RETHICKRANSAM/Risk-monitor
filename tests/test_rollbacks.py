"""Tests for Automated Circuit-Breaker Rollback Service and API."""

import pytest
from app import create_app
from services.rollback_service import trigger_automated_rollback


@pytest.fixture
def client():
    app = create_app()
    app.config.update({"TESTING": True})
    with app.test_client() as client:
        yield client


def test_trigger_automated_rollback_direct():
    """Verify circuit-breaker rollback generation and SHA-256 seal."""
    event = trigger_automated_rollback(
        release_id="REL-SEC-999",
        reason="Canary divergence > 4.5%",
        risk_score=85,
        target_version="v2.4.0",
    )
    assert event["status"] == "ROLLBACK_EXECUTED"
    assert event["action"] == "HALT_AND_ROLLBACK"
    assert len(event["circuit_breaker_hash"]) == 64  # SHA-256 hash
    assert event["release_id"] == "REL-SEC-999"


def test_rollback_api_endpoints(client):
    """Verify REST API for listing and manually triggering rollbacks."""
    # Trigger via API
    resp = client.post(
        "/api/rollbacks/trigger",
        json={
            "release_id": "API-TEST-01",
            "reason": "Test circuit breaker invocation",
            "risk_score": 90,
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["rollback"]["status"] == "ROLLBACK_EXECUTED"

    # List rollbacks
    list_resp = client.get("/api/rollbacks")
    assert list_resp.status_code == 200
    list_data = list_resp.get_json()
    assert list_data["count"] >= 1


def test_rollback_configuration(client):
    """Verify updating and inspecting rollback webhook target settings."""
    resp = client.post(
        "/api/rollbacks/config",
        json={"webhook_url": "https://argocd.corp.internal/api/webhook", "enabled": True},
    )
    assert resp.status_code == 200
    cfg = resp.get_json()["config"]
    assert cfg["webhook_url"] == "https://argocd.corp.internal/api/webhook"
