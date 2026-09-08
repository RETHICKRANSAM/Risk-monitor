from risk_engine import (
    calculate_risk_score,
    clean_metrics,
    determine_decision,
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
