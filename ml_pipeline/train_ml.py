"""Train Machine Learning algorithms on Network Risk Telemetry.

Algorithms:
1. Isolation Forest (Unsupervised Anomaly Detection)
2. Random Forest Classifier (Supervised Multi-class Ensemble)
3. XGBoost Classifier (Gradient Boosted Trees)
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]


import joblib
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from xgboost import XGBClassifier

from ml_pipeline.preprocess import (
    MODELS_DIR,
    REVERSE_LABEL_MAPPING,
    load_and_preprocess,
)


def train_isolation_forest(
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_bin_train: np.ndarray,
    y_bin_test: np.ndarray,
) -> tuple[IsolationForest, dict]:
    """Trains Isolation Forest on normal baseline traffic for maximum zero-day separation."""
    print("\n" + "=" * 60)
    print("[TRAIN ML] Training Isolation Forest (Normal-Baseline One-Class)...")
    print("=" * 60)

    start_time = time.time()
    # Train strictly on normal baseline traffic
    X_normal = X_train[y_bin_train == 0]
    iso_forest = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        random_state=42,
        n_jobs=-1,
    )
    iso_forest.fit(X_normal)
    train_time = time.time() - start_time

    # Score test records (inverting raw decision function: higher = more anomalous)
    scores = -iso_forest.decision_function(X_test)
    # Calibrate threshold to validation anomaly proportion
    threshold = float(np.percentile(scores, 100 * (1 - np.mean(y_bin_train))))
    pred_binary = (scores > threshold).astype(int)

    acc = accuracy_score(y_bin_test, pred_binary)
    f1 = f1_score(y_bin_test, pred_binary, average="macro")

    metrics = {
        "model_name": "Isolation Forest",
        "type": "Unsupervised Anomaly Detection",
        "training_time_sec": round(train_time, 3),
        "test_accuracy": round(float(acc), 4),
        "test_f1_macro": round(float(f1), 4),
        "threshold": round(threshold, 4),
        "anomaly_ratio_detected": round(float(np.mean(pred_binary)), 4),
    }

    print(
        f"[ISO FOREST] Trained in {train_time:.2f}s | Accuracy: {acc * 100:.2f}% | F1: {f1 * 100:.2f}%"
    )

    model_path = MODELS_DIR / "isolation_forest.joblib"
    joblib.dump({"model": iso_forest, "threshold": threshold}, model_path)
    print(f"[ISO FOREST] Model saved to {model_path}")

    return iso_forest, metrics



def train_random_forest(
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    feature_names: list[str],
) -> tuple[RandomForestClassifier, dict]:
    """Trains Random Forest Classifier for multi-class risk severity."""
    print("\n" + "=" * 60)
    print("[TRAIN ML] Training Random Forest Classifier (Supervised Bagging)...")
    print("=" * 60)

    start_time = time.time()
    rf = RandomForestClassifier(
        n_estimators=150,
        max_depth=16,
        random_state=42,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)
    train_time = time.time() - start_time

    # Inference & metrics
    inf_start = time.time()
    preds = rf.predict(X_test)
    inf_time_per_sample_ms = ((time.time() - inf_start) / len(X_test)) * 1000

    acc = accuracy_score(y_test, preds)
    f1_macro = f1_score(y_test, preds, average="macro")
    f1_weighted = f1_score(y_test, preds, average="weighted")

    # Top feature importances
    importances = rf.feature_importances_
    top_indices = np.argsort(importances)[::-1][:10]
    top_features = [
        {"feature": feature_names[i], "importance": round(float(importances[i]), 4)}
        for i in top_indices
    ]

    target_names = [REVERSE_LABEL_MAPPING[i] for i in sorted(REVERSE_LABEL_MAPPING.keys())]
    report = classification_report(y_test, preds, target_names=target_names, output_dict=True)

    metrics = {
        "model_name": "Random Forest",
        "type": "Supervised Tree Ensemble",
        "training_time_sec": round(train_time, 3),
        "latency_per_sample_ms": round(inf_time_per_sample_ms, 3),
        "test_accuracy": round(float(acc), 4),
        "test_f1_macro": round(float(f1_macro), 4),
        "test_f1_weighted": round(float(f1_weighted), 4),
        "top_features": top_features,
        "classification_report": report,
    }

    print(
        f"[RANDOM FOREST] Trained in {train_time:.2f}s | Accuracy: {acc:.4f} | F1 Macro: {f1_macro:.4f}"
    )

    model_path = MODELS_DIR / "random_forest.joblib"
    joblib.dump(rf, model_path)
    print(f"[RANDOM FOREST] Model saved to {model_path}")

    return rf, metrics


def train_xgboost(
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    feature_names: list[str],
) -> tuple[XGBClassifier, dict]:
    """Trains XGBoost Classifier for multi-class risk severity."""
    print("\n" + "=" * 60)
    print("[TRAIN ML] Training XGBoost Classifier (Gradient Boosted Decision Trees)...")
    print("=" * 60)

    start_time = time.time()
    xgb = XGBClassifier(
        n_estimators=150,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        eval_metric="mlogloss",
    )
    xgb.fit(X_train, y_train)
    train_time = time.time() - start_time

    # Inference & metrics
    inf_start = time.time()
    preds = xgb.predict(X_test)
    inf_time_per_sample_ms = ((time.time() - inf_start) / len(X_test)) * 1000

    acc = accuracy_score(y_test, preds)
    f1_macro = f1_score(y_test, preds, average="macro")
    f1_weighted = f1_score(y_test, preds, average="weighted")

    # Top feature importances
    importances = xgb.feature_importances_
    top_indices = np.argsort(importances)[::-1][:10]
    top_features = [
        {"feature": feature_names[i], "importance": round(float(importances[i]), 4)}
        for i in top_indices
    ]

    target_names = [REVERSE_LABEL_MAPPING[i] for i in sorted(REVERSE_LABEL_MAPPING.keys())]
    report = classification_report(y_test, preds, target_names=target_names, output_dict=True)

    metrics = {
        "model_name": "XGBoost",
        "type": "Gradient Boosted Decision Trees",
        "training_time_sec": round(train_time, 3),
        "latency_per_sample_ms": round(inf_time_per_sample_ms, 3),
        "test_accuracy": round(float(acc), 4),
        "test_f1_macro": round(float(f1_macro), 4),
        "test_f1_weighted": round(float(f1_weighted), 4),
        "top_features": top_features,
        "classification_report": report,
    }

    print(
        f"[XGBOOST] Trained in {train_time:.2f}s | Accuracy: {acc:.4f} | F1 Macro: {f1_macro:.4f}"
    )

    model_path = MODELS_DIR / "xgboost.joblib"
    joblib.dump(xgb, model_path)
    print(f"[XGBOOST] Model saved to {model_path}")

    return xgb, metrics


def main():
    X_train, X_test, y_train, y_test, y_bin_train, y_bin_test, _, feature_names = (
        load_and_preprocess()
    )

    _, iso_metrics = train_isolation_forest(X_train, X_test, y_bin_train, y_bin_test)

    _, rf_metrics = train_random_forest(X_train, X_test, y_train, y_test, feature_names)
    _, xgb_metrics = train_xgboost(X_train, X_test, y_train, y_test, feature_names)

    all_ml_metrics = {
        "isolation_forest": iso_metrics,
        "random_forest": rf_metrics,
        "xgboost": xgb_metrics,
    }

    metrics_file = MODELS_DIR / "ml_metrics.json"
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(all_ml_metrics, f, indent=2)
    print(f"\n[TRAIN ML] All ML metrics saved to: {metrics_file}")


if __name__ == "__main__":
    main()
