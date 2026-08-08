import numpy as np
import pandas as pd
import pytest

from src.data.preprocessing.normalization import ScalerStats, apply_scaler, fit_scaler, normalize_physionet

CHANNELS = ["HR", "Glucose"]


def _df():
    return pd.DataFrame({
        "split": ["train", "train", "train", "val", "test"],
        "HR": [70.0, 80.0, 90.0, 500.0, -100.0],       # val/test outliers must not affect train stats
        "Glucose": [100.0, 100.0, 100.0, 9999.0, -9999.0],
    })


def test_fit_scaler_uses_train_only():
    scaler = fit_scaler(_df(), "split", CHANNELS)
    assert scaler.mean["HR"] == pytest.approx(80.0)
    assert scaler.mean["Glucose"] == pytest.approx(100.0)


def test_fit_scaler_handles_zero_std_without_div_by_zero():
    df = pd.DataFrame({"split": ["train", "train"], "HR": [80.0, 80.0], "Glucose": [1.0, 2.0]})
    scaler = fit_scaler(df, "split", CHANNELS)
    assert scaler.std["HR"] == 1.0  # replaced from 0 to avoid division by zero


def test_apply_scaler_produces_zero_mean_unit_std_on_train():
    df = _df()
    scaler = fit_scaler(df, "split", CHANNELS)
    normalized = apply_scaler(df, scaler, CHANNELS)
    train_rows = normalized[df["split"] == "train"]
    assert train_rows["HR"].mean() == pytest.approx(0.0, abs=1e-9)
    assert train_rows["HR"].std(ddof=1) == pytest.approx(1.0, abs=1e-9)


def test_normalize_physionet_round_trip():
    df = _df()
    normalized, scaler = normalize_physionet(df, "split", CHANNELS)
    denormalized_hr = normalized["HR"] * scaler.std["HR"] + scaler.mean["HR"]
    assert denormalized_hr.tolist() == pytest.approx(df["HR"].tolist())


def test_scaler_stats_roundtrip_dict():
    scaler = ScalerStats(mean={"HR": 80.0}, std={"HR": 5.0})
    restored = ScalerStats.from_dict(scaler.to_dict())
    assert restored == scaler
