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
    except ImportError as e:
        return (
            jsonify(
                {
                    "status": "partial",
                    "message": f"ML pipeline libraries not installed: {e}",
                }
            ),
            501,
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
