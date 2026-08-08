"""Sliding-window tensor generation for the sequence model.

The PhysioNet 2019 challenge label is already defined as "sepsis onset within the next
6 hours as of this ICU hour", so no additional label shifting is needed: a window
[t-window_size+1, ..., t] is labeled with SepsisLabel at hour t.

Patients with fewer timesteps than `window_size` are left-padded by repeating their
first timestep's values -- simpler than a masking mechanism, and acceptable at
window sizes this small (default 8h) relative to typical ICU stays.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.data.schema import CLINICAL_CHANNELS, LABEL_COLUMN, PATIENT_ID_COLUMN, TIME_COLUMN


@dataclass(frozen=True)
class WindowedDataset:
    X: np.ndarray            # (n_windows, window_size, n_channels)
    y: np.ndarray            # (n_windows,)
    patient_ids: np.ndarray  # (n_windows,) which patient each window belongs to
    window_end_time: np.ndarray  # (n_windows,) ICULOS of the last timestep in each window


def _windows_for_patient(values: np.ndarray, labels: np.ndarray, window_size: int, stride: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n_timesteps, n_channels = values.shape
    if n_timesteps < window_size:
        pad_len = window_size - n_timesteps
        pad = np.repeat(values[:1], pad_len, axis=0)
        values = np.vstack([pad, values])
        labels = np.concatenate([np.repeat(labels[:1], pad_len), labels])
        n_timesteps = values.shape[0]

    end_indices = list(range(window_size - 1, n_timesteps, stride))
    windows = np.empty((len(end_indices), window_size, n_channels), dtype=np.float32)
    window_labels = np.empty(len(end_indices), dtype=np.int64)
    window_ends = np.empty(len(end_indices), dtype=np.int64)
    for i, end in enumerate(end_indices):
        windows[i] = values[end - window_size + 1: end + 1]
        window_labels[i] = labels[end]
        window_ends[i] = end
    return windows, window_labels, window_ends


def build_windows(
    df: pd.DataFrame,
    window_size: int = 8,
    stride: int = 1,
    channels: list[str] = CLINICAL_CHANNELS,
) -> WindowedDataset:
    if df[channels].isna().any().any():
        raise ValueError("build_windows requires fully-imputed channels; run cleaning first")

    all_X, all_y, all_pid, all_end = [], [], [], []
    for patient_id, group in df.sort_values([PATIENT_ID_COLUMN, TIME_COLUMN]).groupby(PATIENT_ID_COLUMN):
        values = group[channels].to_numpy(dtype=np.float32)
        labels = group[LABEL_COLUMN].to_numpy(dtype=np.int64)
        windows, window_labels, window_ends = _windows_for_patient(values, labels, window_size, stride)
        all_X.append(windows)
        all_y.append(window_labels)
        all_pid.extend([patient_id] * len(window_labels))
        all_end.append(window_ends)

    return WindowedDataset(
        X=np.concatenate(all_X, axis=0),
        y=np.concatenate(all_y, axis=0),
        patient_ids=np.array(all_pid),
        window_end_time=np.concatenate(all_end, axis=0),
    )
