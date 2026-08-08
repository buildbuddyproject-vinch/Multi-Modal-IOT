import numpy as np
import pandas as pd
import pytest

from src.eda.statistics import compute_descriptive_stats, compute_label_group_stats

CHANNELS = ["HR", "Glucose"]


def _df():
    return pd.DataFrame({
        "HR": [70.0, 80.0, np.nan, 90.0],
        "Glucose": [100.0, np.nan, np.nan, np.nan],
        "SepsisLabel": [0, 0, 1, 1],
    })


def test_descriptive_stats_reports_count_and_missing_pct():
    stats = compute_descriptive_stats(_df(), CHANNELS)
    hr_row = stats[stats["channel"] == "HR"].iloc[0]
    assert hr_row["count"] == 3
    assert hr_row["pct_missing"] == pytest.approx(25.0)
    glucose_row = stats[stats["channel"] == "Glucose"].iloc[0]
    assert glucose_row["count"] == 1
    assert glucose_row["pct_missing"] == pytest.approx(75.0)


def test_descriptive_stats_mean_ignores_nan():
    stats = compute_descriptive_stats(_df(), CHANNELS)
    hr_row = stats[stats["channel"] == "HR"].iloc[0]
    assert hr_row["mean"] == pytest.approx(80.0)


def test_label_group_stats_splits_by_label():
    grouped = compute_label_group_stats(_df(), CHANNELS, "SepsisLabel")
    assert set(grouped["SepsisLabel"]) == {0, 1}
    row0 = grouped[grouped["SepsisLabel"] == 0].iloc[0]
    assert row0["HR_mean"] == pytest.approx(75.0)
