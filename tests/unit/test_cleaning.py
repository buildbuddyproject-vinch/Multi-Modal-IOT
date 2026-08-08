import numpy as np
import pandas as pd
import pytest

from src.data.preprocessing.cleaning import (
    clean_physionet,
    compute_train_medians,
    fill_remaining_with_medians,
    forward_backward_fill,
)

CHANNELS = ["HR", "Glucose"]


def test_forward_fill_holds_last_value():
    df = pd.DataFrame({
        "patient_id": ["p1", "p1", "p1", "p1"],
        "ICULOS": [1, 2, 3, 4],
        "HR": [80.0, np.nan, np.nan, 90.0],
        "Glucose": [np.nan, np.nan, 110.0, np.nan],
    })
    out = forward_backward_fill(df, CHANNELS)
    assert list(out["HR"]) == [80.0, 80.0, 80.0, 90.0]
    # Glucose: backward-fill covers the leading NaNs, then forward-fill holds 110
    assert list(out["Glucose"]) == [110.0, 110.0, 110.0, 110.0]


def test_forward_fill_does_not_cross_patients():
    df = pd.DataFrame({
        "patient_id": ["p1", "p1", "p2", "p2"],
        "ICULOS": [1, 2, 1, 2],
        "HR": [80.0, np.nan, np.nan, 95.0],
        "Glucose": [np.nan, np.nan, np.nan, np.nan],
    })
    out = forward_backward_fill(df, CHANNELS)
    assert list(out["HR"]) == [80.0, 80.0, 95.0, 95.0]


def test_channel_never_measured_stays_nan_after_ffill():
    df = pd.DataFrame({
        "patient_id": ["p1", "p1"],
        "ICULOS": [1, 2],
        "HR": [80.0, 82.0],
        "Glucose": [np.nan, np.nan],
    })
    out = forward_backward_fill(df, CHANNELS)
    assert out["Glucose"].isna().all()


def test_train_medians_computed_only_from_train_split():
    df = pd.DataFrame({
        "patient_id": ["p1", "p2"],
        "split": ["train", "test"],
        "HR": [80.0, 500.0],  # test outlier must not leak into the train median
        "Glucose": [100.0, 999.0],
    })
    medians = compute_train_medians(df, "split", CHANNELS)
    assert medians["HR"] == 80.0
    assert medians["Glucose"] == 100.0


def test_fill_remaining_with_medians():
    df = pd.DataFrame({"HR": [80.0, np.nan], "Glucose": [np.nan, np.nan]})
    filled = fill_remaining_with_medians(df, {"HR": 80.0, "Glucose": 100.0}, CHANNELS)
    assert filled["HR"].tolist() == [80.0, 80.0]
    assert filled["Glucose"].tolist() == [100.0, 100.0]


def test_clean_physionet_end_to_end_has_no_nans():
    df = pd.DataFrame({
        "patient_id": ["p1", "p1", "p2", "p2"],
        "ICULOS": [1, 2, 1, 2],
        "split": ["train", "train", "test", "test"],
        "HR": [80.0, np.nan, np.nan, np.nan],
        "Glucose": [np.nan, np.nan, np.nan, np.nan],
    })
    cleaned, medians = clean_physionet(df, "split", CHANNELS)
    assert cleaned[CHANNELS].isna().sum().sum() == 0
    # p2 never had Glucose measured -> filled with the train-only median
    assert cleaned.loc[cleaned["patient_id"] == "p2", "Glucose"].iloc[0] == medians["Glucose"]
