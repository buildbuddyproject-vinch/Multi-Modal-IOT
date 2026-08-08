import numpy as np
import pandas as pd
import pytest

from src.eda.correlation import compute_correlation_matrix, top_correlated_pairs
from src.eda.missingness import missingness_by_patient_summary, missingness_report

CHANNELS = ["A", "B", "C"]


def test_missingness_report_sorted_worst_first():
    df = pd.DataFrame({
        "A": [1.0, np.nan, np.nan, np.nan],  # 75% missing
        "B": [1.0, 2.0, np.nan, np.nan],      # 50% missing
        "C": [1.0, 2.0, 3.0, 4.0],            # 0% missing
    })
    report = missingness_report(df, CHANNELS)
    assert report.iloc[0]["channel"] == "A"
    assert report.iloc[0]["pct_missing"] == pytest.approx(75.0)
    assert report.iloc[-1]["channel"] == "C"
    assert report.iloc[-1]["pct_missing"] == pytest.approx(0.0)


def test_missingness_by_patient_summary_averages_across_patients():
    df = pd.DataFrame({
        "patient_id": ["p1", "p1", "p2", "p2"],
        "A": [1.0, np.nan, np.nan, np.nan],  # p1: 50% missing, p2: 100% missing -> avg 75%
        "B": [1.0, 2.0, 3.0, 4.0],
        "C": [1.0, 2.0, 3.0, 4.0],
    })
    summary = missingness_by_patient_summary(df, CHANNELS, "patient_id")
    a_row = summary[summary["channel"] == "A"].iloc[0]
    assert a_row["avg_per_patient_missing_rate"] == pytest.approx(0.75)


def test_correlation_matrix_perfect_correlation():
    df = pd.DataFrame({"A": range(50), "B": [x * 2 for x in range(50)], "C": np.random.default_rng(0).normal(size=50)})
    corr = compute_correlation_matrix(df, ["A", "B", "C"])
    assert corr.loc["A", "B"] == pytest.approx(1.0)


def test_correlation_respects_min_periods_for_sparse_pairs():
    # fewer than 30 overlapping non-null values -> NaN, not a spurious correlation
    df = pd.DataFrame({"A": [1.0, 2.0, 3.0] + [np.nan] * 47, "B": [3.0, 2.0, 1.0] + [np.nan] * 47})
    corr = compute_correlation_matrix(df, ["A", "B"])
    assert pd.isna(corr.loc["A", "B"])


def test_top_correlated_pairs_excludes_diagonal_and_duplicates():
    df = pd.DataFrame({"A": range(50), "B": [x * 2 for x in range(50)], "C": [-x for x in range(50)]})
    corr = compute_correlation_matrix(df, ["A", "B", "C"])
    top = top_correlated_pairs(corr, top_n=5)
    assert len(top) == 3  # only 3 unique off-diagonal pairs possible for 3 channels
    pair_sets = [frozenset([row.feature_a, row.feature_b]) for row in top.itertuples()]
    assert len(pair_sets) == len(set(pair_sets))  # no duplicates
    assert top.iloc[0]["correlation"] == pytest.approx(1.0, abs=1e-6)
