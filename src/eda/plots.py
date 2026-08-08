"""Matplotlib/seaborn plot generation for the Step 3 EDA report.

Every function saves a PNG to `output_path` and returns that path, so callers
(scripts/run_eda.py and its tests) can assert the artifact actually exists.
"""
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: no display needed to generate files
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid")


def _save(fig: plt.Figure, output_path: Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_missingness_bar(missing_df: pd.DataFrame, output_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 10))
    sns.barplot(data=missing_df, y="channel", x="pct_missing", ax=ax, color="#4C72B0")
    ax.set_xlabel("% Missing")
    ax.set_ylabel("Channel")
    ax.set_title("Missing Value Percentage by Channel (raw, pre-imputation)")
    return _save(fig, output_path)


def plot_correlation_heatmap(corr: pd.DataFrame, output_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(14, 12))
    sns.heatmap(corr, cmap="coolwarm", center=0, square=True, ax=ax, cbar_kws={"shrink": 0.7})
    ax.set_title("Channel Correlation Matrix (pairwise, min_periods=30)")
    return _save(fig, output_path)


def plot_feature_importance_bar(importance_df: pd.DataFrame, output_path: Path, top_n: int = 20) -> Path:
    top = importance_df.head(top_n)
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.barplot(data=top, y="channel", x="importance", ax=ax, color="#55A868")
    ax.set_title(f"Top {top_n} Channels by RandomForest Importance (EDA baseline)")
    return _save(fig, output_path)


def plot_distributions_grid(df: pd.DataFrame, channels: list[str], label_col: str, output_path: Path, n_cols: int = 6) -> Path:
    n_rows = math.ceil(len(channels) / n_cols)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(3.2 * n_cols, 2.8 * n_rows))
    axes = axes.flatten()
    for i, channel in enumerate(channels):
        ax = axes[i]
        subset = df[[channel, label_col]].dropna()
        for label_value, color in [(0, "#4C72B0"), (1, "#C44E52")]:
            values = subset.loc[subset[label_col] == label_value, channel]
            if len(values) > 1:
                sns.kdeplot(values, ax=ax, color=color, label=f"label={label_value}", fill=True, alpha=0.3, warn_singular=False)
        ax.set_title(channel, fontsize=9)
        ax.set_xlabel("")
        ax.set_ylabel("")
    for j in range(len(channels), len(axes)):
        axes[j].axis("off")
    axes[0].legend(fontsize=7)
    fig.suptitle("Channel Distributions by SepsisLabel (0=no sepsis, 1=sepsis)", y=1.01)
    fig.tight_layout()
    return _save(fig, output_path)


def plot_patient_timeseries(df: pd.DataFrame, patient_id_col: str, time_col: str, channels: list[str], patient_ids: list[str], output_path: Path) -> Path:
    n_patients = len(patient_ids)
    fig, axes = plt.subplots(n_patients, 1, figsize=(10, 3.2 * n_patients), sharex=False)
    if n_patients == 1:
        axes = [axes]
    for ax, patient_id in zip(axes, patient_ids):
        patient_df = df[df[patient_id_col] == patient_id].sort_values(time_col)
        for channel in channels:
            ax.plot(patient_df[time_col], patient_df[channel], marker="o", markersize=2, label=channel)
        septic = bool(patient_df.get("SepsisLabel", pd.Series([0])).max())
        ax.set_title(f"Patient {patient_id} (ever septic: {septic})")
        ax.set_xlabel("ICU Length of Stay (hours)")
        ax.legend(fontsize=7, ncol=len(channels))
    fig.tight_layout()
    return _save(fig, output_path)
