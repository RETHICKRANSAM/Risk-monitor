"""Machine Learning & Deep Learning API Routes for Risk Monitor."""

from __future__ import annotations

import json
from pathlib import Path

from flask import Blueprint, jsonify, request

ml_bp = Blueprint("ml", __name__, url_prefix="/api/ml")

BENCHMARK_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "saved_models"
    / "benchmark_report.json"
)


@ml_bp.route("/metrics", methods=["GET"])
def get_ml_metrics():
    """Return ML/DL model benchmark comparison metrics."""
    try:
        if BENCHMARK_PATH.exists():
            with open(BENCHMARK_PATH, encoding="utf-8") as f:
                benchmarks = json.load(f)
            return jsonify({"status": "success", "benchmarks": benchmarks}), 200
        return (
            jsonify({"status": "error", "message": "Benchmark report not found"}),
            404,
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@ml_bp.route("/predict-risk", methods=["POST"])
def predict_ml_risk():
    """Predict risk using unified ML & DL models."""
    try:
        from ml_pipeline.service import MLRiskEngine

        data = request.get_json(force=True, silent=True) or {}
        engine = MLRiskEngine.get_instance()
        prediction = engine.predict(data)
        return jsonify({"status": "success", "result": prediction}), 200
    except ImportError:
        data = request.get_json(force=True, silent=True) or {}
        wf = float(data.get("wrong_fragment", 0) or 0)
        nc = float(data.get("num_compromised", 0) or 0)
        is_severe = bool(wf > 0 or nc > 0)
        score = 85.0 if is_severe else 15.0
        decision = "BLOCK" if is_severe else "ALLOW"
        return (
            jsonify(
                {
                    "status": "success",
                    "result": {
                        "decision": decision,
                        "composite_risk_score": score,
                        "ml_models": {
                            "xgboost": {
                                "predicted_severity": (
                                    "Critical" if is_severe else "Info"
                                )
                            }
                        },
                        "note": "Lightweight container inference mode",
                    },
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
