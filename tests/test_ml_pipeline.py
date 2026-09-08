"""Unit and integration tests for the ML/DL pipeline and API endpoints."""

import pytest
from app import create_app
from ml_pipeline.service import MLRiskEngine


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def engine():
    return MLRiskEngine.get_instance()


def test_ml_risk_engine_singleton(engine):
    """Ensure engine loads models and is a valid singleton."""
    assert engine is not None
    assert engine.preprocessor is not None
    assert engine.xgboost is not None
    assert engine.random_forest is not None
    assert engine.iso_forest is not None
    assert engine.autoencoder is not None
    assert engine.dl_classifier is not None


def test_ml_prediction_output_structure(engine):
    """Test prediction schema on sample network telemetry."""
    sample = {
        "duration": 0,
        "protocol_type": "tcp",
        "service": "http",
        "flag": "SF",
        "src_bytes": 215,
        "dst_bytes": 450,
        "wrong_fragment": 0,
        "num_failed_logins": 0,
        "num_compromised": 0,
        "serror_rate": 0.0,
        "dst_host_srv_serror_rate": 0.0,
        "dst_host_rerror_rate": 0.0,
    }
    result = engine.predict(sample)

    assert "ml_models" in result
    assert "dl_models" in result
    assert "composite_risk_score" in result
    assert "decision" in result

    # Check model subkeys
    assert "xgboost" in result["ml_models"]
    assert "random_forest" in result["ml_models"]
    assert "isolation_forest" in result["ml_models"]
    assert "deep_autoencoder" in result["dl_models"]
    assert "deep_mlp" in result["dl_models"]

    # Decision validity
    assert result["decision"] in ["ALLOW", "PAUSE", "BLOCK"]
    assert 0.0 <= result["composite_risk_score"] <= 100.0


def test_api_ml_metrics_endpoint(client):
    """Test GET /api/ml/metrics returns benchmark data."""
    response = client.get("/api/ml/metrics")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert "benchmarks" in data
    assert len(data["benchmarks"]) >= 4


def test_api_ml_predict_endpoint(client):
    """Test POST /api/ml/predict-risk returns prediction."""
    payload = {
        "protocol_type": "tcp",
        "service": "private",
        "flag": "REJ",
        "wrong_fragment": 1,
        "num_compromised": 2,
    }
    response = client.post("/api/ml/predict-risk", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert "result" in data
    assert data["result"]["decision"] in ["ALLOW", "PAUSE", "BLOCK"]
