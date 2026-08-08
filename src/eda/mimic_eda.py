"""Lightweight EDA for the MIMIC-IV Demo dataset (schema/coverage checks only --
this dataset is not used for model training, see docs/architecture/system_architecture.md)."""
import pandas as pd


def channel_coverage(vitals_long: pd.DataFrame) -> pd.DataFrame:
    """Number of readings and distinct patients covered per channel."""
    coverage = vitals_long.groupby("channel").agg(
        n_readings=("value", "count"),
        n_patients=("patient_id", "nunique"),
    )
    return coverage.sort_values("n_readings", ascending=False).reset_index()


def patient_demographics_summary(patients: pd.DataFrame) -> dict:
    return {
        "n_patients": int(patients["patient_id"].nunique()),
        "age_mean": float(patients["age"].mean()),
        "age_std": float(patients["age"].std()),
        "sex_counts": patients.drop_duplicates("patient_id")["sex"].value_counts().to_dict(),
        "unit_counts": patients["unit_admitted"].value_counts().to_dict(),
    }
