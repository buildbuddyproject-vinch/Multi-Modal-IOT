"""Z-score normalization, fit on the train split only and applied to every split."""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.data.schema import CLINICAL_CHANNELS


@dataclass(frozen=True)
class ScalerStats:
    mean: dict[str, float]
    std: dict[str, float]

    def to_dict(self) -> dict:
        return {"mean": self.mean, "std": self.std}

    @classmethod
    def from_dict(cls, data: dict) -> "ScalerStats":
        return cls(mean=data["mean"], std=data["std"])


def fit_scaler(df: pd.DataFrame, split_col: str = "split", channels: list[str] = CLINICAL_CHANNELS) -> ScalerStats:
    train = df[df[split_col] == "train"]
    mean = train[channels].mean()
    std = train[channels].std().replace(0.0, 1.0).fillna(1.0)
    return ScalerStats(mean=mean.to_dict(), std=std.to_dict())


def apply_scaler(df: pd.DataFrame, scaler: ScalerStats, channels: list[str] = CLINICAL_CHANNELS) -> pd.DataFrame:
    df = df.copy()
    for channel in channels:
        df[channel] = (df[channel] - scaler.mean[channel]) / scaler.std[channel]
    return df


def normalize_physionet(df: pd.DataFrame, split_col: str = "split", channels: list[str] = CLINICAL_CHANNELS) -> tuple[pd.DataFrame, ScalerStats]:
    scaler = fit_scaler(df, split_col, channels)
    normalized = apply_scaler(df, scaler, channels)
    return normalized, scaler
