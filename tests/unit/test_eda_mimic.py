import pandas as pd
import pytest

from src.eda.mimic_eda import channel_coverage, patient_demographics_summary


def test_channel_coverage_counts_readings_and_patients():
    vitals = pd.DataFrame({
        "patient_id": ["p1", "p1", "p2", "p1"],
        "channel": ["HR", "HR", "HR", "Glucose"],
        "value": [80.0, 82.0, 90.0, 100.0],
    })
    coverage = channel_coverage(vitals)
    hr_row = coverage[coverage["channel"] == "HR"].iloc[0]
    assert hr_row["n_readings"] == 3
    assert hr_row["n_patients"] == 2
    assert coverage.iloc[0]["channel"] == "HR"  # sorted by n_readings desc


def test_patient_demographics_summary():
    patients = pd.DataFrame({
        "patient_id": ["p1", "p2", "p3"],
        "age": [60, 70, 80],
        "sex": ["F", "M", "F"],
        "unit_admitted": ["MICU", "SICU", "MICU"],
    })
    summary = patient_demographics_summary(patients)
    assert summary["n_patients"] == 3
    assert summary["age_mean"] == pytest.approx(70.0)
    assert summary["sex_counts"] == {"F": 2, "M": 1}
    assert summary["unit_counts"]["MICU"] == 2
