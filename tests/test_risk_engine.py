from risk_engine import (
    calculate_risk_score,
    clean_metrics,
    determine_decision,
    evaluate_release,
    impute_missing_values,
)


def test_clean_metrics():
    raw = {
        "error_rate": -1.0,
        "availability": 105.0,
        "latency_ms": 500,
    }
    cleaned = clean_metrics(raw)
    assert cleaned["error_rate"] is None
    assert cleaned["availability"] is None
    assert cleaned["latency_ms"] == 500


def test_impute_missing_values():
    raw = {"error_rate": None}
    imputed, warnings = impute_missing_values(raw)
    assert imputed["error_rate"] == 1.0  # default safe value
    assert len(warnings) > 0


def test_calculate_risk_score():
    metrics = {
        "error_rate": 4.0,  # > 3.0 -> +40
        "latency_ms": 600,  # > 500 -> +25
        "canary_error_rate": 1.0,  # OK
        "error_budget_remaining": 15.0,  # < 20 -> +10
    }
    score, reasons = calculate_risk_score(metrics)
    assert score == 75
    assert len(reasons) == 3


def test_determine_decision():
    assert determine_decision(20) == "ALLOW"
    assert determine_decision(45) == "PAUSE"
    assert determine_decision(80) == "BLOCK"


def test_evaluate_release_healthy_allow():
    """Healthy telemetry must result in risk score <= 39 and ALLOW decision."""
    healthy_metrics = {
        "error_rate": 0.5,
        "latency_ms": 150.0,
        "canary_error_rate": 0.2,
        "error_budget_remaining": 95.0,
        "availability": 99.9,
    }
    result = evaluate_release(healthy_metrics)
    assert result["risk_score"] == 0
    assert result["risk_score"] <= 39
    assert result["decision"] == "ALLOW"
    assert result["reasons"] == []


def test_evaluate_release_moderate_risk_pause():
    """Moderate risk (score 40-59) must yield PAUSE decision."""
    moderate_metrics = {
        "error_rate": 3.8,  # > 3.0 -> +40
        "latency_ms": 250.0,
        "canary_error_rate": 0.5,
        "error_budget_remaining": 70.0,
        "availability": 99.0,
    }
    result = evaluate_release(moderate_metrics)
    assert result["risk_score"] == 40
    assert 40 <= result["risk_score"] <= 59
    assert result["decision"] == "PAUSE"
    assert len(result["reasons"]) == 1
    assert result["reasons"][0]["rule"] == "High error rate (>3%)"


def test_evaluate_release_critical_risk_block():
    """Critical risk (score >= 60) must trigger circuit breaker and BLOCK decision."""
    critical_metrics = {
        "error_rate": 4.5,  # > 3.0 -> +40
        "latency_ms": 650.0,  # > 500 -> +25
        "canary_error_rate": 3.2,  # > 2.0 -> +25
        "error_budget_remaining": 10.0,  # < 20 -> +10
        "availability": 94.0,
    }
    result = evaluate_release(critical_metrics)
    assert result["risk_score"] == 100
    assert result["risk_score"] >= 60
    assert result["decision"] == "BLOCK"
    assert len(result["reasons"]) == 4


def test_evaluate_release_clean_impute_smooth_pipeline():
    """Verify that missing/noisy/invalid data traverses CLEAN -> IMPUTE -> SMOOTH -> SCORE -> DECIDE."""
    noisy_metrics = {
        "error_rate": -2.0,  # Invalid: should be cleaned to None, then imputed from history
        "latency_ms": 1200.0,  # Temporary spike
        "availability": 150.0,  # Invalid: capped/cleaned
        "canary_error_rate": None,  # Missing: should be imputed
        "error_budget_remaining": None,  # Missing: should be imputed
    }
    historical_metrics = [
        {"error_rate": 1.2, "latency_ms": 200.0, "canary_error_rate": 0.8},
        {"error_rate": 1.4, "latency_ms": 220.0, "canary_error_rate": 0.9},
    ]

    result = evaluate_release(noisy_metrics, historical_metrics=historical_metrics)

    # Imputation warnings must be present
    assert result["warnings"] is not None
    assert len(result["warnings"]) > 0

    # Cleaned and imputed metrics must be finite numbers
    used = result["metrics_used"]
    assert used["error_rate"] is not None
    assert used["error_rate"] >= 0
    assert used["canary_error_rate"] is not None
    assert used["error_budget_remaining"] is not None

    # Latency should be smoothed: average of (220 + 1200) / 2 = 710ms (window=3)
    assert used["latency_ms"] < 1200.0

    # Decision and score must be valid
    assert isinstance(result["risk_score"], int)
    assert result["decision"] in ("ALLOW", "PAUSE", "BLOCK")


def test_evaluate_release_delayed_canary_triggers_pause():
    """When canary results are unavailable, an otherwise healthy release must be PAUSED."""
    healthy_metrics = {
        "error_rate": 0.5,
        "latency_ms": 150.0,
        "canary_error_rate": 0.2,
        "error_budget_remaining": 95.0,
    }
    result = evaluate_release(healthy_metrics, canary_available=False)
    assert result["decision"] == "PAUSE"
    assert any("Canary" in r.get("rule", "") for r in result["reasons"])

