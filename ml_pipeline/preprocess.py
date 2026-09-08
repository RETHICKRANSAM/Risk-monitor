"""Data preprocessing pipeline for Network Security and Risk Telemetry.

Loads raw network telemetry (Test_data.csv), generates risk severity labels,
encodes categorical features, scales numerical features, and saves
the reusable preprocessor artifact.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Ensure UTF-8 output on Windows consoles with non-ASCII paths
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# Directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = DATA_DIR / "saved_models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_DATA_PATH = DATA_DIR / "Test_data.csv"

CATEGORICAL_COLS = ["protocol_type", "service", "flag"]
LABEL_MAPPING = {
    "Info": 0,
    "Low": 1,
    "Medium": 2,
    "High": 3,
    "Critical": 4,
}
REVERSE_LABEL_MAPPING = {v: k for k, v in LABEL_MAPPING.items()}


def compute_severity(row: Any) -> str:
    """Computes enterprise security severity based on risk indicators."""
    try:
        wf = (
            float(row["wrong_fragment"])
            if "wrong_fragment" in row and row["wrong_fragment"] is not None
            else 0.0
        )
        fl = (
            float(row["num_failed_logins"])
            if "num_failed_logins" in row and row["num_failed_logins"] is not None
            else 0.0
        )
        nc = (
            float(row["num_compromised"])
            if "num_compromised" in row and row["num_compromised"] is not None
            else 0.0
        )
        se = (
            float(row["serror_rate"])
            if "serror_rate" in row and row["serror_rate"] is not None
            else 0.0
        )

        dse = (
            float(row["dst_host_srv_serror_rate"])
            if "dst_host_srv_serror_rate" in row and row["dst_host_srv_serror_rate"] is not None
            else 0.0
        )
        dre = (
            float(row["dst_host_rerror_rate"])
            if "dst_host_rerror_rate" in row and row["dst_host_rerror_rate"] is not None
            else 0.0
        )
    except (ValueError, TypeError, KeyError):
        return "Info"

    if wf > 0 or fl > 0 or nc > 0:
        return "Critical"
    elif se > 0.5 or dse > 0.5:
        return "High"
    elif dre > 0.5:
        return "Medium"
    flag_val = str(row.get("flag", "SF") if hasattr(row, "get") else "SF")
    if flag_val != "SF":
        return "Low"
    return "Info"


def load_and_preprocess(
    csv_path: Path | str = DEFAULT_DATA_PATH,
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple[Any, ...]:
    """Loads CSV, fits preprocessor, and returns transformed train/test data."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Data file not found: {csv_path}")

    print(f"[PREPROCESS] Loading dataset from: {csv_path}")
    df = pd.read_csv(csv_path)

    # 1. Generate severity labels and binary anomaly flags
    severities = [compute_severity(row) for _, row in df.iterrows()]
    y_multiclass = np.array([LABEL_MAPPING.get(s, 0) for s in severities], dtype=np.int64)
    y_binary = np.array([1 if y > 0 else 0 for y in y_multiclass], dtype=np.int64)

    # 2. Identify numerical vs categorical features
    numerical_cols = [c for c in df.columns if c not in CATEGORICAL_COLS]

    print(
        f"[PREPROCESS] Dataset shape: {df.shape} | "
        f"Categorical: {len(CATEGORICAL_COLS)} | Numerical: {len(numerical_cols)}"
    )

    # 3. Build ColumnTransformer
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_COLS,
            ),
            ("num", StandardScaler(), numerical_cols),
        ]
    )

    X_train_df, X_test_df, y_train, y_test, y_bin_train, y_bin_test = (
        train_test_split(
            df,
            y_multiclass,
            y_binary,
            test_size=test_size,
            random_state=random_state,
            stratify=y_multiclass,
        )
    )

    print("[PREPROCESS] Fitting ColumnTransformer on training split...")
    X_train_raw = preprocessor.fit_transform(X_train_df)
    X_test_raw = preprocessor.transform(X_test_df)

    X_train = np.asarray(X_train_raw)
    X_test = np.asarray(X_test_raw)

    # Extract transformed feature names
    cat_names = preprocessor.named_transformers_["cat"].get_feature_names_out(
        CATEGORICAL_COLS
    )
    feature_names = list(cat_names) + numerical_cols

    # Save artifacts
    pipeline_metadata = {
        "preprocessor": preprocessor,
        "feature_names": feature_names,
        "categorical_cols": CATEGORICAL_COLS,
        "numerical_cols": numerical_cols,
        "label_mapping": LABEL_MAPPING,
        "reverse_label_mapping": REVERSE_LABEL_MAPPING,
    }
    artifact_path = MODELS_DIR / "preprocessor.joblib"
    joblib.dump(pipeline_metadata, artifact_path)
    print(
        f"[PREPROCESS] Preprocessor and metadata saved to: {artifact_path} ({len(feature_names)} features)"
    )

    return (
        X_train,
        X_test,
        y_train,
        y_test,
        y_bin_train,
        y_bin_test,
        preprocessor,
        feature_names,
    )


if __name__ == "__main__":
    X_train, X_test, y_train, y_test, y_bin_train, y_bin_test, _, feats = (
        load_and_preprocess()
    )
    print(f"X_train shape: {X_train.shape}, X_test shape: {X_test.shape}")
    print(f"y_train distribution: {np.bincount(y_train)}")
    print(f"y_test distribution: {np.bincount(y_test)}")
