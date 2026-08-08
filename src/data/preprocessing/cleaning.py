"""Missing-value handling for the PhysioNet channel matrix.

Strategy (chosen to avoid leakage and reflect how ICU monitoring actually works --
a reading stays clinically valid until the next measurement):
1. Per patient, per channel: forward-fill (a reading holds until superseded), then
   backward-fill (covers leading NaNs before the first real reading).
2. Any values still missing (a channel never measured for that patient) are filled
   with a population statistic computed on the TRAIN split only, then applied to all
   splits -- this is the only step where cross-patient information is used, so it must
   never be fit on val/test data.
"""
import pandas as pd

from src.data.schema import CLINICAL_CHANNELS, PATIENT_ID_COLUMN, TIME_COLUMN


def forward_backward_fill(df: pd.DataFrame, channels: list[str] = CLINICAL_CHANNELS) -> pd.DataFrame:
    df = df.sort_values([PATIENT_ID_COLUMN, TIME_COLUMN]).copy()
    grouped = df.groupby(PATIENT_ID_COLUMN, group_keys=False)[channels]
    df[channels] = grouped.apply(lambda g: g.ffill().bfill())
    return df


def compute_train_medians(df: pd.DataFrame, split_col: str = "split", channels: list[str] = CLINICAL_CHANNELS) -> dict[str, float]:
    train = df[df[split_col] == "train"]
    medians = train[channels].median(numeric_only=True)
    return medians.fillna(0.0).to_dict()


def fill_remaining_with_medians(df: pd.DataFrame, medians: dict[str, float], channels: list[str] = CLINICAL_CHANNELS) -> pd.DataFrame:
    df = df.copy()
    for channel in channels:
        df[channel] = df[channel].fillna(medians.get(channel, 0.0))
    return df


def clean_physionet(df: pd.DataFrame, split_col: str = "split", channels: list[str] = CLINICAL_CHANNELS) -> tuple[pd.DataFrame, dict[str, float]]:
    """Full cleaning pipeline. `df` must already have a `split_col` column
    (see src/data/preprocessing/split.py) so medians are computed train-only."""
    filled = forward_backward_fill(df, channels)
    medians = compute_train_medians(filled, split_col, channels)
    cleaned = fill_remaining_with_medians(filled, medians, channels)
    assert cleaned[channels].isna().sum().sum() == 0, "channels must be fully imputed after cleaning"
    return cleaned, medians
