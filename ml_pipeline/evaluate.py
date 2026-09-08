"""Comprehensive Evaluation & Comparison Suite across ML and DL models."""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]


import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, f1_score

from ml_pipeline.preprocess import (
    MODELS_DIR,
    load_and_preprocess,
)
from ml_pipeline.train_dl import DeepAutoencoder, DeepRiskClassifier


def evaluate_all() -> list[dict[str, Any]]:
    print("\n" + "=" * 70)
    print("      COMPREHENSIVE MACHINE LEARNING & DEEP LEARNING BENCHMARK")
    print("=" * 70)

    # 1. Load Data
    _, X_test, _, y_test, _, y_bin_test, _, _ = load_and_preprocess()
    tensor_X_test = torch.tensor(X_test, dtype=torch.float32)

    results: list[dict[str, Any]] = []

    # 2. Evaluate XGBoost
    xgb_path = MODELS_DIR / "xgboost.joblib"
    if xgb_path.exists():
        xgb = joblib.load(xgb_path)
        t0 = time.time()
        preds = xgb.predict(X_test)
        inf_ms = ((time.time() - t0) / len(X_test)) * 1000
        acc = accuracy_score(y_test, preds)
        f1_m = f1_score(y_test, preds, average="macro")
        f1_w = f1_score(y_test, preds, average="weighted")
        results.append(
            {
                "Algorithm": "XGBoost Classifier",
                "Category": "Machine Learning (GBDT)",
                "Task": "Multi-class Severity",
                "Accuracy (%)": round(float(acc) * 100, 2),
                "F1 Macro (%)": round(float(f1_m) * 100, 2),
                "F1 Weighted (%)": round(float(f1_w) * 100, 2),
                "Latency (ms/sample)": round(inf_ms, 3),
            }
        )

    # 3. Evaluate Random Forest
    rf_path = MODELS_DIR / "random_forest.joblib"
    if rf_path.exists():
        rf = joblib.load(rf_path)
        t0 = time.time()
        preds = rf.predict(X_test)
        inf_ms = ((time.time() - t0) / len(X_test)) * 1000
        acc = accuracy_score(y_test, preds)
        f1_m = f1_score(y_test, preds, average="macro")
        f1_w = f1_score(y_test, preds, average="weighted")
        results.append(
            {
                "Algorithm": "Random Forest",
                "Category": "Machine Learning (Ensemble)",
                "Task": "Multi-class Severity",
                "Accuracy (%)": round(float(acc) * 100, 2),
                "F1 Macro (%)": round(float(f1_m) * 100, 2),
                "F1 Weighted (%)": round(float(f1_w) * 100, 2),
                "Latency (ms/sample)": round(inf_ms, 3),
            }
        )

    # 4. Evaluate PyTorch Deep MLP
    dl_mlp_path = MODELS_DIR / "dl_classifier.pth"
    if dl_mlp_path.exists():
        ckpt = torch.load(dl_mlp_path, map_location="cpu", weights_only=False)
        dl_model = DeepRiskClassifier(ckpt["input_dim"], ckpt["num_classes"])
        dl_model.load_state_dict(ckpt["model_state_dict"])
        dl_model.eval()

        t0 = time.time()
        with torch.no_grad():
            logits = dl_model(tensor_X_test)
            preds = torch.argmax(logits, dim=1).numpy()
        inf_ms = ((time.time() - t0) / len(X_test)) * 1000
        acc = accuracy_score(y_test, preds)
        f1_m = f1_score(y_test, preds, average="macro")
        f1_w = f1_score(y_test, preds, average="weighted")
        results.append(
            {
                "Algorithm": "PyTorch Deep MLP",
                "Category": "Deep Learning (Neural Net)",
                "Task": "Multi-class Severity",
                "Accuracy (%)": round(float(acc) * 100, 2),
                "F1 Macro (%)": round(float(f1_m) * 100, 2),
                "F1 Weighted (%)": round(float(f1_w) * 100, 2),
                "Latency (ms/sample)": round(inf_ms, 3),
            }
        )

    # 5. Evaluate Isolation Forest (Anomaly)
    iso_path = MODELS_DIR / "isolation_forest.joblib"
    if iso_path.exists():
        loaded_iso = joblib.load(iso_path)
        if isinstance(loaded_iso, dict):
            iso = loaded_iso["model"]
            threshold = loaded_iso.get("threshold", 0.0)
        else:
            iso = loaded_iso
            threshold = 0.0

        t0 = time.time()
        scores = -iso.decision_function(X_test)
        inf_ms = ((time.time() - t0) / len(X_test)) * 1000
        pred_bin = (scores > threshold).astype(int)
        acc = accuracy_score(y_bin_test, pred_bin)
        f1_m = f1_score(y_bin_test, pred_bin, average="macro")

        results.append(
            {
                "Algorithm": "Isolation Forest",
                "Category": "Machine Learning (Unsupervised)",
                "Task": "Zero-Day Anomaly Detection",
                "Accuracy (%)": round(float(acc) * 100, 2),
                "F1 Macro (%)": round(float(f1_m) * 100, 2),
                "F1 Weighted (%)": "N/A (Binary)",
                "Latency (ms/sample)": round(inf_ms, 3),
            }
        )

    # 6. Evaluate Deep Autoencoder (Anomaly)
    ae_path = MODELS_DIR / "autoencoder.pth"
    if ae_path.exists():
        ckpt = torch.load(ae_path, map_location="cpu", weights_only=False)
        ae = DeepAutoencoder(ckpt["input_dim"], ckpt["latent_dim"])
        ae.load_state_dict(ckpt["model_state_dict"])
        ae.eval()

        t0 = time.time()
        with torch.no_grad():
            mse = ae.compute_reconstruction_error(tensor_X_test).numpy()
        inf_ms = ((time.time() - t0) / len(X_test)) * 1000

        pred_bin = (mse > ckpt["threshold"]).astype(int)
        acc = accuracy_score(y_bin_test, pred_bin)
        f1_m = f1_score(y_bin_test, pred_bin, average="macro")
        results.append(
            {
                "Algorithm": "Deep Autoencoder",
                "Category": "Deep Learning (Unsupervised)",
                "Task": "Bottleneck Reconstruction Loss",
                "Accuracy (%)": round(float(acc) * 100, 2),
                "F1 Macro (%)": round(float(f1_m) * 100, 2),
                "F1 Weighted (%)": "N/A (Continuous MSE)",
                "Latency (ms/sample)": round(inf_ms, 3),
            }
        )

    df_report = pd.DataFrame(results)
    print("\n" + df_report.to_string(index=False))

    out_file = MODELS_DIR / "benchmark_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[EVALUATE] Report saved to: {out_file}")
    return results


if __name__ == "__main__":
    evaluate_all()
