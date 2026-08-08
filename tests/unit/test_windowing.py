import numpy as np
import pandas as pd
import pytest

from src.data.preprocessing.windowing import build_windows

CHANNELS = ["HR", "Glucose"]


def _patient_df(patient_id: str, n_rows: int, septic_at: int | None = None) -> pd.DataFrame:
    rows = []
    for t in range(1, n_rows + 1):
        label = 1 if septic_at == t else 0
        rows.append({"patient_id": patient_id, "ICULOS": t, "HR": float(70 + t), "Glucose": float(100 + t), "SepsisLabel": label})
    return pd.DataFrame(rows)


def test_window_shape_for_long_patient():
    df = _patient_df("p1", n_rows=10)
    windowed = build_windows(df, window_size=4, stride=1, channels=CHANNELS)
    # timesteps 4..10 inclusive as window ends = 7 windows
    assert windowed.X.shape == (7, 4, 2)
    assert windowed.y.shape == (7,)
    assert (windowed.patient_ids == "p1").all()


def test_window_values_are_contiguous_and_ordered():
    df = _patient_df("p1", n_rows=6)
    windowed = build_windows(df, window_size=3, stride=1, channels=CHANNELS)
    # first window covers ICULOS 1,2,3 -> HR values 71,72,73
    np.testing.assert_allclose(windowed.X[0, :, 0], [71.0, 72.0, 73.0])


def test_short_patient_is_left_padded_not_dropped():
    df = _patient_df("p1", n_rows=2)
    windowed = build_windows(df, window_size=5, stride=1, channels=CHANNELS)
    assert windowed.X.shape[0] == 1  # exactly one window, padded up to window_size
    assert windowed.X.shape[1] == 5
    # padded rows repeat the first real timestep's HR value (71.0)
    np.testing.assert_allclose(windowed.X[0, :3, 0], [71.0, 71.0, 71.0])
    np.testing.assert_allclose(windowed.X[0, 3:, 0], [71.0, 72.0])


def test_label_taken_from_window_end_not_window_start():
    df = _patient_df("p1", n_rows=6, septic_at=6)
    windowed = build_windows(df, window_size=3, stride=1, channels=CHANNELS)
    assert windowed.y[-1] == 1
    assert windowed.y[:-1].sum() == 0


def test_multiple_patients_are_independent():
    df = pd.concat([_patient_df("p1", 5), _patient_df("p2", 5, septic_at=5)], ignore_index=True)
    windowed = build_windows(df, window_size=3, stride=1, channels=CHANNELS)
    assert set(windowed.patient_ids) == {"p1", "p2"}
    p2_mask = windowed.patient_ids == "p2"
    assert windowed.y[p2_mask][-1] == 1


def test_build_windows_rejects_missing_values():
    df = _patient_df("p1", n_rows=5)
    df.loc[2, "HR"] = np.nan
    with pytest.raises(ValueError):
        build_windows(df, window_size=3, channels=CHANNELS)


def test_stride_reduces_window_count():
    df = _patient_df("p1", n_rows=10)
    dense = build_windows(df, window_size=4, stride=1, channels=CHANNELS)
    sparse = build_windows(df, window_size=4, stride=2, channels=CHANNELS)
    assert sparse.X.shape[0] < dense.X.shape[0]
