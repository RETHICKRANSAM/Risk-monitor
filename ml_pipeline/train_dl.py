"""Train Deep Learning architectures (PyTorch) on Network Risk Telemetry.

Architectures:
1. Deep Autoencoder (DAE) for Unsupervised Representation Learning & Anomaly Scoring.
2. Deep Multi-Layer Perceptron (MLP) with Batch Normalization & Dropout for Multi-Class Risk Classification.
"""

from __future__ import annotations

import json
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]


import numpy as np
import torch
from sklearn.metrics import accuracy_score, classification_report, f1_score
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from ml_pipeline.preprocess import (
    LABEL_MAPPING,
    MODELS_DIR,
    REVERSE_LABEL_MAPPING,
    load_and_preprocess,
)

# -------------------------------------------------------------
# Deep Learning PyTorch Models
# -------------------------------------------------------------


class DeepAutoencoder(nn.Module):
    """Deep Autoencoder for unsupervised anomaly detection and reconstruction loss."""

    def __init__(self, input_dim: int, latent_dim: int = 16):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.BatchNorm1d(64),
            nn.LeakyReLU(0.2),
            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.LeakyReLU(0.2),
            nn.Linear(32, latent_dim),
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 32),
            nn.BatchNorm1d(32),
            nn.LeakyReLU(0.2),
            nn.Linear(32, 64),
            nn.BatchNorm1d(64),
            nn.LeakyReLU(0.2),
            nn.Linear(64, input_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        latent = self.encoder(x)
        reconstruction = self.decoder(latent)
        return reconstruction

    def compute_reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
        """Returns per-sample MSE error."""
        with torch.no_grad():
            recon = self.forward(x)
            mse = torch.mean((x - recon) ** 2, dim=1)
        return mse


class DeepRiskClassifier(nn.Module):
    """Deep Multi-Layer Perceptron for Risk Severity Classification."""

    def __init__(self, input_dim: int, num_classes: int = 5):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.25),
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Linear(32, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)


# -------------------------------------------------------------
# Training Routines
# -------------------------------------------------------------


def train_autoencoder(
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_bin_train: np.ndarray,
    y_bin_test: np.ndarray,
    epochs: int = 15,
    batch_size: int = 64,
    lr: float = 0.002,
) -> tuple[DeepAutoencoder, dict]:
    """Trains Deep Autoencoder strictly on normal baseline traffic for peak zero-day separation."""
    print("\n" + "=" * 60)
    print("[TRAIN DL] Training Deep Autoencoder (Normal Baseline Bottleneck)...")
    print("=" * 60)

    input_dim = int(X_train.shape[1])
    model = DeepAutoencoder(input_dim=input_dim, latent_dim=16)

    # Train strictly on normal traffic
    X_normal = X_train[y_bin_train == 0]
    tensor_train = torch.tensor(X_normal, dtype=torch.float32)
    tensor_test = torch.tensor(X_test, dtype=torch.float32)

    dataset = TensorDataset(tensor_train, tensor_train)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)

    start_time = time.time()
    model.train()
    for epoch in range(1, epochs + 1):
        total_loss = 0.0
        for batch_x, _ in loader:
            optimizer.zero_grad()
            recon = model(batch_x)
            loss = criterion(recon, batch_x)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * batch_x.size(0)

        epoch_loss = total_loss / len(dataset)
        if epoch % 5 == 0 or epoch == 1:
            print(f"  [Epoch {epoch:02d}/{epochs:02d}] Reconstruction MSE Loss: {epoch_loss:.4f}")

    train_time = time.time() - start_time

    # Evaluate on test set
    model.eval()
    with torch.no_grad():
        test_recon_errors = model.compute_reconstruction_error(tensor_test).numpy()

    # Optimal threshold calibrated to normal proportion
    threshold = float(np.percentile(test_recon_errors, 100 * (1 - np.mean(y_bin_train))))
    pred_anomalies = (test_recon_errors > threshold).astype(int)

    acc = accuracy_score(y_bin_test, pred_anomalies)
    f1 = f1_score(y_bin_test, pred_anomalies, average="macro")


    metrics = {
        "model_name": "Deep Autoencoder",
        "type": "Unsupervised Deep Representation",
        "input_dim": input_dim,
        "latent_dim": 16,
        "training_time_sec": round(train_time, 3),
        "mean_test_recon_error": round(float(np.mean(test_recon_errors)), 4),
        "max_test_recon_error": round(float(np.max(test_recon_errors)), 4),
        "anomaly_threshold": round(threshold, 4),
        "test_anomaly_accuracy": round(float(acc), 4),
        "test_anomaly_f1": round(float(f1), 4),
    }

    print(
        f"[AUTOENCODER] Trained in {train_time:.2f}s | "
        f"Mean Recon Error: {metrics['mean_test_recon_error']} | Threshold: {threshold:.4f}"
    )

    model_path = MODELS_DIR / "autoencoder.pth"
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "input_dim": input_dim,
            "latent_dim": 16,
            "threshold": threshold,
            "min_error": float(np.min(test_recon_errors)),
            "max_error": float(np.percentile(test_recon_errors, 99)),
        },
        model_path,
    )
    print(f"[AUTOENCODER] Model checkpoint saved to {model_path}")

    return model, metrics


def train_dl_classifier(
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    epochs: int = 15,
    batch_size: int = 64,
    lr: float = 0.001,
) -> tuple[DeepRiskClassifier, dict]:
    """Trains Deep MLP Classifier for risk severity."""
    print("\n" + "=" * 60)
    print("[TRAIN DL] Training Deep Risk Classifier (PyTorch MLP)...")
    print("=" * 60)

    input_dim = int(X_train.shape[1])
    num_classes = len(LABEL_MAPPING)

    model = DeepRiskClassifier(input_dim=input_dim, num_classes=num_classes)

    tensor_X_train = torch.tensor(X_train, dtype=torch.float32)
    tensor_y_train = torch.tensor(y_train, dtype=torch.long)
    tensor_X_test = torch.tensor(X_test, dtype=torch.float32)

    dataset = TensorDataset(tensor_X_train, tensor_y_train)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)

    start_time = time.time()
    model.train()
    for epoch in range(1, epochs + 1):
        total_loss = 0.0
        for batch_x, batch_y in loader:
            optimizer.zero_grad()
            logits = model(batch_x)
            loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * batch_x.size(0)

        epoch_loss = total_loss / len(dataset)
        if epoch % 5 == 0 or epoch == 1:
            print(f"  [Epoch {epoch:02d}/{epochs:02d}] CrossEntropy Loss: {epoch_loss:.4f}")

    train_time = time.time() - start_time

    # Inference & evaluation
    model.eval()
    inf_start = time.time()
    with torch.no_grad():
        logits = model(tensor_X_test)
        preds = torch.argmax(logits, dim=1).numpy()
    inf_time_per_sample_ms = ((time.time() - inf_start) / len(X_test)) * 1000

    acc = accuracy_score(y_test, preds)
    f1_macro = f1_score(y_test, preds, average="macro")
    f1_weighted = f1_score(y_test, preds, average="weighted")

    target_names = [REVERSE_LABEL_MAPPING[i] for i in sorted(REVERSE_LABEL_MAPPING.keys())]
    report = classification_report(y_test, preds, target_names=target_names, output_dict=True)

    metrics = {
        "model_name": "PyTorch Deep MLP",
        "type": "Supervised Deep Neural Network",
        "training_time_sec": round(train_time, 3),
        "latency_per_sample_ms": round(inf_time_per_sample_ms, 3),
        "test_accuracy": round(float(acc), 4),
        "test_f1_macro": round(float(f1_macro), 4),
        "test_f1_weighted": round(float(f1_weighted), 4),
        "classification_report": report,
    }

    print(
        f"[DEEP MLP] Trained in {train_time:.2f}s | Accuracy: {acc:.4f} | F1 Macro: {f1_macro:.4f}"
    )

    model_path = MODELS_DIR / "dl_classifier.pth"
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "input_dim": input_dim,
            "num_classes": num_classes,
        },
        model_path,
    )
    print(f"[DEEP MLP] Model checkpoint saved to {model_path}")

    return model, metrics


def main():
    X_train, X_test, y_train, y_test, y_bin_train, y_bin_test, _, _ = (
        load_and_preprocess()
    )

    _, ae_metrics = train_autoencoder(X_train, X_test, y_bin_train, y_bin_test, epochs=15)
    _, mlp_metrics = train_dl_classifier(X_train, X_test, y_train, y_test, epochs=20)


    all_dl_metrics = {
        "deep_autoencoder": ae_metrics,
        "deep_mlp_classifier": mlp_metrics,
    }

    metrics_file = MODELS_DIR / "dl_metrics.json"
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(all_dl_metrics, f, indent=2)
    print(f"\n[TRAIN DL] All DL metrics saved to: {metrics_file}")


if __name__ == "__main__":
    main()
