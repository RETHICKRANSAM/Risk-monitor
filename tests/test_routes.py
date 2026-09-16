import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
        }
    )
    with app.test_client() as client:
        yield client


def test_routes(client):
    page_routes = ["/", "/dashboard", "/risk-detail", "/evidence", "/audit", "/health"]
    for r in page_routes:
        resp = client.get(r)
        assert resp.status_code == 200, f"Failed for {r}: {resp.status_code}"
        print(f"Page {r}: {resp.status_code} ({len(resp.data)} bytes)")


def test_api_endpoints(client):
    # Test dashboard API
    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "summary" in data or "recent_releases" in data

    # Test health check
    resp = client.get("/health")
    assert resp.status_code == 200

    # Test deployments list
    resp = client.get("/api/deployments")
    assert resp.status_code == 200

    # Test risk evaluation API
    payload = {
        "failed_tests": 0,
        "critical_vulnerabilities": 0,
        "high_vulnerabilities": 0,
        "warning_count": 0,
        "error_count": 0,
        "health_status": "healthy",
    }
    resp = client.post("/api/risk/evaluate", json=payload)
    assert resp.status_code == 200
    res_data = resp.get_json()
    assert res_data["decision"] == "ALLOW"
    print("API endpoints: ALL PASS")
