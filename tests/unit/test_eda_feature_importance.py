from pathlib import Path

import numpy as np
import pytest

from src.eda.feature_importance import compute_random_forest_importance, load_last_timestep_features


def test_load_last_timestep_features(tmp_path: Path):
    X = np.arange(2 * 3 * 4, dtype=np.float32).reshape(2, 3, 4)  # 2 windows, 3 timesteps, 4 channels
    y = np.array([0, 1])
    npz_path = tmp_path / "windows.npz"
    np.savez_compressed(npz_path, X=X, y=y)

    X_last, y_loaded = load_last_timestep_features(npz_path)
    assert X_last.shape == (2, 4)
    np.testing.assert_array_equal(X_last[0], X[0, -1, :])
    np.testing.assert_array_equal(y_loaded, y)


def test_feature_importance_ranks_informative_channel_higher():
    rng = np.random.default_rng(0)
    n = 500
    informative = rng.normal(size=n)
    noise = rng.normal(size=n)
    y = (informative > 0).astype(int)
    X = np.column_stack([informative, noise])

    importance = compute_random_forest_importance(X, y, feature_names=["informative", "noise"], n_estimators=100)
    assert importance.iloc[0]["channel"] == "informative"
    assert importance.iloc[0]["importance"] > importance.iloc[1]["importance"]
    assert importance["importance"].sum() == pytest.approx(1.0, abs=1e-6)


def test_feature_importance_raises_on_empty_input():
    with pytest.raises(ValueError):
        compute_random_forest_importance(np.empty((0, 3)), np.empty((0,)), feature_names=["a", "b", "c"])
