"""Missing-value analysis on raw (pre-imputation) data."""
import pandas as pd


def missingness_report(df: pd.DataFrame, channels: list[str]) -> pd.DataFrame:
    """Per-channel missing count/percentage, sorted worst-first."""
    n_total = len(df)
    n_missing = df[channels].isna().sum()
    report = pd.DataFrame({
        "channel": channels,
        "n_missing": n_missing.values,
        "n_total": n_total,
        "pct_missing": (100.0 * n_missing / n_total).values,
    })
    return report.sort_values("pct_missing", ascending=False).reset_index(drop=True)


def missingness_by_patient_summary(df: pd.DataFrame, channels: list[str], patient_id_col: str) -> pd.DataFrame:
    """Average per-patient missing rate per channel -- distinguishes 'measured
    occasionally for everyone' from 'never measured for some patients'."""
    per_patient_missing = df.groupby(patient_id_col)[channels].apply(lambda g: g.isna().mean())
    return per_patient_missing.mean().rename("avg_per_patient_missing_rate").reset_index().rename(columns={"index": "channel"})
