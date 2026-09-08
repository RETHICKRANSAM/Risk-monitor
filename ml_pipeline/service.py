"""Unified ML & DL Risk Scoring Service.

Provides real-time inference across:
1. XGBoost (Supervised Multi-Class Severity & Probability)
2. Random Forest (Supervised Ensemble Baseline)
3. Isolation Forest (Unsupervised Anomaly Detector & Outlier Score)
4. PyTorch Deep Autoencoder (Unsupervised Reconstruction Loss & Bottleneck Scoring)

Combines outputs into an enterprise composite risk score (0-100) and recommendation.
"""

from __future__ import annotations

import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]


import joblib
import numpy as np
import pandas as pd
import torch

from ml_pipeline.preprocess import (
    CATEGORICAL_COLS,
    MODELS_DIR,
    REVERSE_LABEL_MAPPING,
)
from ml_pipeline.train_dl import DeepAutoencoder, DeepRiskClassifier

SEVERITY_WEIGHTS = {
    "Info": 0,
    "Low": 25,
    "Medium": 50,
    "High": 75,
    "Critical": 100,
}


class MLRiskEngine:
    """Production ML/DL Risk Scoring Engine."""

    _instance = None

    def __init__(self):
        self.preprocessor_meta: dict[str, Any] | None = None
        self.preprocessor = None
        self.iso_forest = None
        self.random_forest = None
        self.xgboost = None
        self.autoencoder = None
        self.dl_classifier = None
        self.ae_metadata: dict[str, Any] | None = None
        self._load_models()

    @classmethod
    def get_instance(cls) -> MLRiskEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_models(self):
        # 1. Preprocessor
        prep_path = MODELS_DIR / "preprocessor.joblib"
        if prep_path.exists():
            self.preprocessor_meta = joblib.load(prep_path)
            if self.preprocessor_meta is not None:
                self.preprocessor = self.preprocessor_meta.get("preprocessor")

        # 2. ML Models
        iso_path = MODELS_DIR / "isolation_forest.joblib"
        if iso_path.exists():
            loaded_iso = joblib.load(iso_path)
            if isinstance(loaded_iso, dict):
                self.iso_forest = loaded_iso.get("model")
                self.iso_threshold = float(loaded_iso.get("threshold", 0.0))
            else:
                self.iso_forest = loaded_iso
                self.iso_threshold = 0.0


        rf_path = MODELS_DIR / "random_forest.joblib"
        if rf_path.exists():
            self.random_forest = joblib.load(rf_path)

        xgb_path = MODELS_DIR / "xgboost.joblib"
        if xgb_path.exists():
            self.xgboost = joblib.load(xgb_path)

        # 3. DL Models (PyTorch)
        ae_path = MODELS_DIR / "autoencoder.pth"
        if ae_path.exists():
            ckpt = torch.load(ae_path, map_location="cpu", weights_only=False)
            self.ae_metadata = ckpt
            self.autoencoder = DeepAutoencoder(
                input_dim=ckpt["input_dim"], latent_dim=ckpt["latent_dim"]
            )
            self.autoencoder.load_state_dict(ckpt["model_state_dict"])
            self.autoencoder.eval()

        dl_cls_path = MODELS_DIR / "dl_classifier.pth"
        if dl_cls_path.exists():
            ckpt = torch.load(dl_cls_path, map_location="cpu", weights_only=False)
            self.dl_classifier = DeepRiskClassifier(
                input_dim=ckpt["input_dim"], num_classes=ckpt["num_classes"]
            )
            self.dl_classifier.load_state_dict(ckpt["model_state_dict"])
            self.dl_classifier.eval()

    def predict(self, record: dict[str, Any]) -> dict[str, Any]:
        """Runs full ML and DL prediction pipeline on a single telemetry record."""
        if self.preprocessor is None or self.preprocessor_meta is None:
            raise RuntimeError("Preprocessor artifact not loaded.")

        df = pd.DataFrame([record])

        # Fill any missing expected numerical columns with 0
        numerical_cols = self.preprocessor_meta.get("numerical_cols", [])
        for col in numerical_cols:
            if col not in df.columns:
                df[col] = 0.0

        # Fill any missing categorical columns with sensible defaults
        for col in CATEGORICAL_COLS:
            if col not in df.columns:
                df[col] = "unknown"

        # Transform features
        X_scaled = self.preprocessor.transform(df)
        X_tensor = torch.tensor(X_scaled, dtype=torch.float32)

        results: dict[str, Any] = {
            "ml_models": {},
            "dl_models": {},
            "composite_risk_score": 0,
            "decision": "ALLOW",
        }

        # 1. XGBoost Prediction
        xgb_severity = "Info"
        xgb_conf = 0.0
        if self.xgboost:
            xgb_class_idx = int(self.xgboost.predict(X_scaled)[0])
            xgb_severity = REVERSE_LABEL_MAPPING.get(xgb_class_idx, "Info")
            xgb_probs = self.xgboost.predict_proba(X_scaled)[0]
            xgb_conf = float(xgb_probs[xgb_class_idx])
            results["ml_models"]["xgboost"] = {
                "predicted_severity": xgb_severity,
                "confidence": round(xgb_conf, 4),
                "class_probabilities": {
                    REVERSE_LABEL_MAPPING[i]: round(float(p), 4)
                    for i, p in enumerate(xgb_probs)
                },
            }

        # 2. Random Forest Prediction
        if self.random_forest:
            rf_class_idx = int(self.random_forest.predict(X_scaled)[0])
            rf_severity = REVERSE_LABEL_MAPPING.get(rf_class_idx, "Info")
            rf_probs = self.random_forest.predict_proba(X_scaled)[0]
            results["ml_models"]["random_forest"] = {
                "predicted_severity": rf_severity,
                "confidence": round(float(rf_probs[rf_class_idx]), 4),
            }

        # 3. Isolation Forest Outlier Score
        iso_score = 0.0
        is_iso_anomaly = False
        if self.iso_forest:
            raw_decision = -float(self.iso_forest.decision_function(X_scaled)[0])
            threshold = getattr(self, "iso_threshold", 0.0)
            is_iso_anomaly = bool(raw_decision > threshold)
            iso_score = max(0.0, min(100.0, (raw_decision - threshold + 0.1) * 200.0))
            results["ml_models"]["isolation_forest"] = {
                "is_anomaly": is_iso_anomaly,
                "anomaly_score": round(iso_score, 1),
                "raw_decision": round(raw_decision, 4),
            }


        # 4. Deep Autoencoder Reconstruction Loss
        ae_score = 0.0
        if self.autoencoder and self.ae_metadata:
            with torch.no_grad():
                mse = float(self.autoencoder.compute_reconstruction_error(X_tensor)[0])
            max_err = max(self.ae_metadata.get("max_error", 2.0), 1.0)
            ae_score = min(100.0, (mse / max_err) * 100.0)
            is_ae_anomaly = mse > self.ae_metadata.get("threshold", 0.5)
            results["dl_models"]["deep_autoencoder"] = {
                "reconstruction_error": round(mse, 4),
                "threshold": round(self.ae_metadata.get("threshold", 0.5), 4),
                "is_anomaly": bool(is_ae_anomaly),
                "reconstruction_risk_score": round(ae_score, 1),
            }

        # 5. Deep MLP Classifier
        if self.dl_classifier:
            with torch.no_grad():
                logits = self.dl_classifier(X_tensor)
                probs = torch.softmax(logits, dim=1)[0].numpy()
                dl_class_idx = int(np.argmax(probs))
            results["dl_models"]["deep_mlp"] = {
                "predicted_severity": REVERSE_LABEL_MAPPING.get(dl_class_idx, "Info"),
                "confidence": round(float(probs[dl_class_idx]), 4),
            }

        # 6. Composite Enterprise Risk Score Calculation
        base_severity_score = SEVERITY_WEIGHTS.get(xgb_severity, 0)
        composite = (
            0.50 * base_severity_score
            + 0.25 * iso_score
            + 0.25 * ae_score
        )
        composite = max(0.0, min(100.0, composite))
        results["composite_risk_score"] = round(composite, 1)

        # Recommendation based on project decision thresholds
        if composite >= 60.0:
            results["decision"] = "BLOCK"
        elif composite >= 40.0:
            results["decision"] = "PAUSE"
        else:
            results["decision"] = "ALLOW"

        return results
