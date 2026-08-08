import pandas as pd
import pytest

from src.data.preprocessing.split import add_split_column, split_patients


def _make_df(n_healthy=40, n_septic=10, rows_per_patient=5):
    rows = []
    for i in range(n_healthy):
        pid = f"healthy_{i}"
        for t in range(1, rows_per_patient + 1):
            rows.append({"patient_id": pid, "ICULOS": t, "HR": 80.0, "SepsisLabel": 0})
    for i in range(n_septic):
        pid = f"septic_{i}"
        for t in range(1, rows_per_patient + 1):
            label = 1 if t == rows_per_patient else 0
            rows.append({"patient_id": pid, "ICULOS": t, "HR": 90.0, "SepsisLabel": label})
    return pd.DataFrame(rows)


def test_split_is_disjoint_and_covers_all_patients():
    df = _make_df()
    split = split_patients(df, val_size=0.2, test_size=0.2, random_state=0)
    all_ids = set(df["patient_id"].unique())
    split_ids = set(split.train_ids) | set(split.val_ids) | set(split.test_ids)
    assert split_ids == all_ids
    assert set(split.train_ids).isdisjoint(split.val_ids)
    assert set(split.train_ids).isdisjoint(split.test_ids)
    assert set(split.val_ids).isdisjoint(split.test_ids)


def test_split_proportions_are_approximately_correct():
    df = _make_df(n_healthy=80, n_septic=20)
    split = split_patients(df, val_size=0.15, test_size=0.15, random_state=1)
    n_total = 100
    assert abs(len(split.train_ids) - 0.7 * n_total) <= 2
    assert abs(len(split.val_ids) - 0.15 * n_total) <= 2
    assert abs(len(split.test_ids) - 0.15 * n_total) <= 2


def test_split_stratifies_sepsis_prevalence():
    df = _make_df(n_healthy=80, n_septic=20)
    split = split_patients(df, val_size=0.2, test_size=0.2, random_state=2)
    for ids in (split.train_ids, split.val_ids, split.test_ids):
        septic_fraction = sum(1 for pid in ids if pid.startswith("septic_")) / len(ids)
        assert 0.1 <= septic_fraction <= 0.3  # true prevalence is 0.2


def test_assign_raises_for_unknown_patient():
    df = _make_df(n_healthy=30, n_septic=8)
    split = split_patients(df, val_size=0.2, test_size=0.2, random_state=0)
    with pytest.raises(KeyError):
        split.assign("not_a_real_patient")


def test_add_split_column_matches_assignment():
    df = _make_df(n_healthy=30, n_septic=8)
    split = split_patients(df, val_size=0.2, test_size=0.2, random_state=0)
    out = add_split_column(df, split)
    assert set(out["split"].unique()) <= {"train", "val", "test"}
    for pid in out["patient_id"].unique():
        expected = split.assign(pid)
        assert (out.loc[out["patient_id"] == pid, "split"] == expected).all()
