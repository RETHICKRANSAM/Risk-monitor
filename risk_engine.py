"""Risk scoring engine for Pre-Release Risk Monitor.

Implements rule-based risk scoring with data cleaning, imputation,
and smoothing as specified in the PRD.
"""

from typing import TypedDict


class RiskRule(TypedDict):
    condition: str
    field: str
    threshold: float
    operator: str
    score: int
    label: str


# ============================================================
# Risk Scoring Rules (PRD Section 13)
# ============================================================
RULES: list[RiskRule] = [
    {
        "condition": "error_rate > 3",
        "field": "error_rate",
        "threshold": 3.0,
        "operator": ">",
        "score": 40,
        "label": "High error rate (>3%)",
    },
    {
        "condition": "latency_ms > 500",
        "field": "latency_ms",
        "threshold": 500.0,
        "operator": ">",
        "score": 25,
        "label": "High latency (>500ms)",
    },
    {
        "condition": "canary_error_rate > 2",
        "field": "canary_error_rate",
        "threshold": 2.0,
        "operator": ">",
        "score": 25,
        "label": "Canary error rate elevated (>2%)",
    },
    {
        "condition": "error_budget_remaining < 20",
        "field": "error_budget_remaining",
        "threshold": 20.0,
        "operator": "<",
        "score": 10,
        "label": "Low error budget remaining (<20%)",
    },
]

# Decision thresholds
ALLOW_MAX = 39
PAUSE_MAX = 59
# 60+ = BLOCK


def clean_metrics(metrics_dict):
    """Clean and validate incoming metrics data.

    - Convert to float where possible
    - Remove impossible values (e.g., availability > 100)
    - Clamp values to valid ranges
    """
    cleaned = {}

    # Convert all values to float to prevent TypeError on > or < comparisons
    for k, v in metrics_dict.items():
        if v is not None and str(v).strip() != "":
            try:
                cleaned[k] = float(v)
            except ValueError:
                cleaned[k] = None
        else:
            cleaned[k] = None

    # Cap availability at 100%
    if cleaned.get("availability") is not None:
        if cleaned["availability"] > 100:
            cleaned["availability"] = None  # Mark as missing for imputation
        elif cleaned["availability"] < 0:
            cleaned["availability"] = None

    # Error rate cannot be negative
    if cleaned.get("error_rate") is not None and cleaned["error_rate"] < 0:
        cleaned["error_rate"] = None

    # Latency cannot be negative
    if cleaned.get("latency_ms") is not None and cleaned["latency_ms"] < 0:
        cleaned["latency_ms"] = None

    # Error budget remaining should be 0-100
    if cleaned.get("error_budget_remaining") is not None:
        if (
            cleaned["error_budget_remaining"] < 0
            or cleaned["error_budget_remaining"] > 100
        ):
            cleaned["error_budget_remaining"] = None

    # Canary error rate cannot be negative
    if (
        cleaned.get("canary_error_rate") is not None
        and cleaned["canary_error_rate"] < 0
    ):
        cleaned["canary_error_rate"] = None

    return cleaned


def impute_missing_values(metrics_dict, historical_metrics=None):
    """Impute missing values using median of historical data.
    Falls back to safe defaults if no historical data available.
    """
    # Default safe values (conservative — won't trigger alerts)
    defaults = {
        "error_rate": 1.0,
        "latency_ms": 200,
        "availability": 99.5,
        "error_budget_remaining": 50.0,
        "canary_error_rate": 1.0,
        "canary_latency_delta": 0,
        "cpu_usage": 40.0,
        "memory_usage": 40.0,
    }

    imputed = dict(metrics_dict)
    imputation_warnings = []

    if historical_metrics and len(historical_metrics) > 0:
        for field, default in defaults.items():
            if imputed.get(field) is None:
                # Extract valid float values from historical metrics
                valid_vals = []
                for hm in historical_metrics:
                    val = hm.get(field)
                    if val is not None and str(val).strip() != "":
                        try:
                            valid_vals.append(float(val))
                        except ValueError:
                            pass

                if valid_vals:
                    # Calculate median manually
                    valid_vals.sort()
                    n = len(valid_vals)
                    if n % 2 == 1:
                        median_val = valid_vals[n // 2]
                    else:
                        median_val = (valid_vals[n // 2 - 1] + valid_vals[n // 2]) / 2.0

                    imputed[field] = median_val
                    imputation_warnings.append(
                        f"{field} imputed with historical median ({median_val})"
                    )
                else:
                    imputed[field] = default
                    imputation_warnings.append(
                        f"{field} imputed with default ({default})"
                    )
    else:
        for field, default in defaults.items():
            if imputed.get(field) is None:
                imputed[field] = default
                imputation_warnings.append(f"{field} imputed with default ({default})")

    return imputed, imputation_warnings


def smooth_metrics(current_metrics, historical_metrics, window=3):
    """Apply moving-average smoothing to reduce noise.

    Uses the last `window` data points including current to smooth values.
    """
    if not historical_metrics or len(historical_metrics) < 1:
        return current_metrics

    smoothable_fields = ["error_rate", "latency_ms", "canary_error_rate"]
    smoothed = dict(current_metrics)

    recent = historical_metrics[-(window - 1) :]  # Last N-1 historical points
    all_points = recent + [current_metrics]

    for field in smoothable_fields:
        values = []
        for point in all_points:
            val = point.get(field)
            if val is not None:
                values.append(float(val))
        if len(values) >= 2:
            smoothed[field] = round(sum(values) / len(values), 3)

    return smoothed


def calculate_risk_score(metrics_dict):
    """Calculate risk score based on PRD rules.

    Returns:
        tuple: (total_score, list of triggered reasons)

    """
    total_score = 0
    reasons = []

    for rule in RULES:
        field = rule["field"]
        value = metrics_dict.get(field)

        if value is None:
            continue

        value = float(value)
        threshold = float(rule["threshold"])
        triggered = False

        if (rule["operator"] == ">" and value > threshold) or (
            rule["operator"] == "<" and value < threshold
        ):
            triggered = True

        if triggered:
            score_to_add = int(rule["score"])
            total_score += score_to_add
            reasons.append(
                {
                    "rule": rule["label"],
                    "value": value,
                    "threshold": threshold,
                    "score_added": score_to_add,
                }
            )

    return total_score, reasons


def determine_decision(risk_score):
    """Map risk score to deployment decision."""
    if risk_score <= ALLOW_MAX:
        return "ALLOW"
    if risk_score <= PAUSE_MAX:
        return "PAUSE"
    return "BLOCK"


def evaluate_release(metrics_dict, historical_metrics=None, canary_available=True):
    """Full risk evaluation pipeline for a release.

    Steps:
    1. Clean metrics (remove impossible values)
    2. Impute missing values
    3. Smooth noisy metrics
    4. Calculate risk score
    5. Determine decision

    Args:
        metrics_dict: Current deployment metrics
        historical_metrics: List of previous metrics dicts for this release
        canary_available: Whether canary results are available

    Returns:
        dict: Evaluation result with score, decision, reasons, warnings

    """
    warnings = []

    # Step 1: Clean
    cleaned = clean_metrics(metrics_dict)

    # Step 2: Impute
    imputed, imputation_warnings = impute_missing_values(cleaned, historical_metrics)
    warnings.extend(imputation_warnings)

    # Step 3: Smooth (Edge Case 2: temporary spike handling)
    if historical_metrics:
        smoothed = smooth_metrics(imputed, historical_metrics)
    else:
        smoothed = imputed

    # Step 4: Calculate risk score
    risk_score, reasons = calculate_risk_score(smoothed)

    # Step 5: Determine decision
    decision = determine_decision(risk_score)

    # Edge Case 3: Delayed canary result
    if not canary_available:
        warnings.append("Canary results not yet available.")
        if decision == "ALLOW":
            decision = "PAUSE"
            reasons.append(
                {
                    "rule": "Canary results delayed",
                    "value": None,
                    "threshold": None,
                    "score_added": 0,
                }
            )
            warnings.append("Release set to PAUSE because canary is missing.")

    return {
        "risk_score": risk_score,
        "decision": decision,
        "reasons": reasons,
        "warnings": warnings or None,
        "metrics_used": smoothed,
    }


def batch_evaluate(records):
    """Evaluate a batch of deployment records.
    Useful for evaluation against synthetic data.

    Args:
        records: List of dicts with metric fields

    Returns:
        List of evaluation results with ground truth comparison

    """
    results = []

    for record in records:
        metrics = {
            "error_rate": record.get("error_rate"),
            "latency_ms": record.get("latency_ms"),
            "availability": record.get("availability"),
            "error_budget_remaining": record.get("error_budget_remaining"),
            "canary_error_rate": record.get("canary_error_rate"),
            "canary_latency_delta": record.get("canary_latency_delta"),
        }

        # Convert string values to numbers
        for key, val in metrics.items():
            if isinstance(val, str):
                try:
                    metrics[key] = float(val) if val else None
                except ValueError:
                    metrics[key] = None

        evaluation = evaluate_release(metrics)
        evaluation["release_id"] = record.get("release_id")
        evaluation["is_harmful_ground_truth"] = record.get("is_harmful")

        results.append(evaluation)

    return results


# ============================================================
# Deployment Risk Evaluation (API-facing)
# ============================================================
# Scoring weights for deployment risk factors
DEPLOYMENT_WEIGHTS = {
    "failed_tests": 15,
    "critical_vulnerabilities": 40,
    "high_vulnerabilities": 20,
    "warning_count": 2,
    "error_count": 5,
}
UNHEALTHY_PENALTY = 50


def evaluate_deployment_risk(data):
    """Rule-based deployment risk scorer for the /api/risk/evaluate endpoint.

    Scoring logic:
        failed_tests × 15
        critical_vulnerabilities × 40
        high_vulnerabilities × 20
        warning_count × 2
        error_count × 5
        unhealthy system → +50

    Decision rules:
        risk_score ≥ 80 → BLOCK
        risk_score ≥ 50 → PAUSE
        otherwise → ALLOW

    Args:
        data: dict with keys: failed_tests, critical_vulnerabilities,
              high_vulnerabilities, warning_count, error_count, health_status

    Returns:
        dict: risk_score, decision, reasons[]

    """
    risk_score = 0
    reasons = []

    # Extract values with defaults
    failed_tests = int(data.get("failed_tests", 0))
    critical_vulns = int(data.get("critical_vulnerabilities", 0))
    high_vulns = int(data.get("high_vulnerabilities", 0))
    warning_count = int(data.get("warning_count", 0))
    error_count = int(data.get("error_count", 0))
    health_status = str(data.get("health_status", "healthy")).lower()

    # Calculate component scores
    if failed_tests > 0:
        score = failed_tests * DEPLOYMENT_WEIGHTS["failed_tests"]
        risk_score += score
        reasons.append(
            {
                "factor": "failed_tests",
                "value": failed_tests,
                "weight": DEPLOYMENT_WEIGHTS["failed_tests"],
                "score_added": score,
                "detail": f"{failed_tests} failed test(s) × {DEPLOYMENT_WEIGHTS['failed_tests']} = +{score}",
            }
        )

    if critical_vulns > 0:
        score = critical_vulns * DEPLOYMENT_WEIGHTS["critical_vulnerabilities"]
        risk_score += score
        reasons.append(
            {
                "factor": "critical_vulnerabilities",
                "value": critical_vulns,
                "weight": DEPLOYMENT_WEIGHTS["critical_vulnerabilities"],
                "score_added": score,
                "detail": f"{critical_vulns} critical vulnerability(ies) × {DEPLOYMENT_WEIGHTS['critical_vulnerabilities']} = +{score}",  # noqa: E501
            }
        )

    if high_vulns > 0:
        score = high_vulns * DEPLOYMENT_WEIGHTS["high_vulnerabilities"]
        risk_score += score
        reasons.append(
            {
                "factor": "high_vulnerabilities",
                "value": high_vulns,
                "weight": DEPLOYMENT_WEIGHTS["high_vulnerabilities"],
                "score_added": score,
                "detail": f"{high_vulns} high vulnerability(ies) × {DEPLOYMENT_WEIGHTS['high_vulnerabilities']} = +{score}",  # noqa: E501
            }
        )

    if warning_count > 0:
        score = warning_count * DEPLOYMENT_WEIGHTS["warning_count"]
        risk_score += score
        reasons.append(
            {
                "factor": "warning_count",
                "value": warning_count,
                "weight": DEPLOYMENT_WEIGHTS["warning_count"],
                "score_added": score,
                "detail": f"{warning_count} warning(s) × {DEPLOYMENT_WEIGHTS['warning_count']} = +{score}",
            }
        )

    if error_count > 0:
        score = error_count * DEPLOYMENT_WEIGHTS["error_count"]
        risk_score += score
        reasons.append(
            {
                "factor": "error_count",
                "value": error_count,
                "weight": DEPLOYMENT_WEIGHTS["error_count"],
                "score_added": score,
                "detail": f"{error_count} error(s) × {DEPLOYMENT_WEIGHTS['error_count']} = +{score}",
            }
        )

    if health_status in ("unhealthy", "critical", "degraded"):
        risk_score += UNHEALTHY_PENALTY
        reasons.append(
            {
                "factor": "health_status",
                "value": health_status,
                "weight": UNHEALTHY_PENALTY,
                "score_added": UNHEALTHY_PENALTY,
                "detail": f'Unhealthy system status "{health_status}" = +{UNHEALTHY_PENALTY}',
            }
        )

    # Decision
    if risk_score >= 80:
        decision = "BLOCK"
    elif risk_score >= 50:
        decision = "PAUSE"
    else:
        decision = "ALLOW"

    return {
        "risk_score": risk_score,
        "decision": decision,
        "reasons": reasons,
        "input": {
            "failed_tests": failed_tests,
            "critical_vulnerabilities": critical_vulns,
            "high_vulnerabilities": high_vulns,
            "warning_count": warning_count,
            "error_count": error_count,
            "health_status": health_status,
        },
    }
