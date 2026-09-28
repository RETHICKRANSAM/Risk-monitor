"""Tests for Inbound CI/CD Webhook Ingestion (GitHub Actions and Jenkins)."""

import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config.update({"TESTING": True})
    with app.test_client() as client:
        yield client


def test_github_webhook_processing(client):
    """Verify ingestion and parsing of GitHub push/release webhook payload."""
    payload = {
        "ref": "refs/heads/release-v2.5",
        "repository": {"full_name": "fintech/core-payments"},
        "head_commit": {
            "id": "e4f5a6b7c8d9",
            "message": "fix: update transaction reconciliation logic",
            "author": {"username": "alex.dev"},
        },
    }
    resp = client.post(
        "/api/webhooks/github",
        json=payload,
        headers={"X-GitHub-Event": "push"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["event"]["branch"] == "release-v2.5"
    assert data["event"]["commit_sha"] == "e4f5a6b7"
    assert data["event"]["author"] == "alex.dev"


def test_jenkins_webhook_processing(client):
    """Verify ingestion of Jenkins build notification webhook."""
    payload = {
        "job_name": "deploy-production-canary",
        "build_number": 42,
        "status": "SUCCESS",
        "commit_sha": "9a8b7c6d",
    }
    resp = client.post("/api/webhooks/jenkins", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["event"]["job_name"] == "deploy-production-canary"
    assert data["event"]["build_number"] == 42


def test_webhook_logs_retrieval(client):
    """Verify retrieval of recent webhook activity logs."""
    resp = client.get("/api/webhooks/logs")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "events" in data
    assert isinstance(data["events"], list)
