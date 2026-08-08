"""Quick feature-importance baseline for EDA purposes.

This is a RandomForest baseline over the last timestep of each pre-built window
(src/data/preprocessing/windowing.py output) -- fast and dependency-light. It answers
"which channels look most predictive at a glance" for the EDA report; it is not the
final model (that is the hybrid CNN/Bi-LSTM/Transformer built in Step 4/5, and any
XGBoost/LightGBM benchmarking happens there against the real evaluation metrics).
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier


def load_last_timestep_features(npz_path: Path) -> tuple[np.ndarray, np.ndarray]:
    with np.load(npz_path) as data:
        X_windows, y = data["X"], data["y"]
    X_last = X_windows[:, -1, :]  # most recent reading in each window
    return X_last, y


def compute_random_forest_importance(
    X: np.ndarray,
    y: np.ndarray,
    feature_names: list[str],
    n_estimators: int = 200,
    max_depth: int = 12,
    random_state: int = 42,
    class_weight: str = "balanced",
) -> pd.DataFrame:
    if X.shape[0] == 0:
        raise ValueError("cannot compute feature importance on an empty dataset")
    model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
        class_weight=class_weight,
        n_jobs=-1,
    )
    model.fit(X, y)
    importance = pd.DataFrame({"channel": feature_names, "importance": model.feature_importances_})
    return importance.sort_values("importance", ascending=False).reset_index(drop=True)
