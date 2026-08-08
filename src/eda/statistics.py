"""Descriptive statistics per channel, computed on raw (pre-imputation) data so
missingness/measurement-frequency effects are visible."""
import pandas as pd


def compute_descriptive_stats(df: pd.DataFrame, channels: list[str]) -> pd.DataFrame:
    """Return one row per channel: count, mean, std, min, 25/50/75%, max, pct_missing."""
    desc = df[channels].describe().T
    desc["pct_missing"] = 100.0 * (1 - desc["count"] / len(df))
    desc.index.name = "channel"
    return desc.reset_index()


def compute_label_group_stats(df: pd.DataFrame, channels: list[str], label_col: str) -> pd.DataFrame:
    """Mean/std per channel, split by label value (e.g. SepsisLabel 0 vs 1) --
    a quick signal of which channels separate septic from non-septic readings."""
    grouped = df.groupby(label_col)[channels].agg(["mean", "std"])
    grouped.columns = [f"{channel}_{stat}" for channel, stat in grouped.columns]
    return grouped.reset_index()
