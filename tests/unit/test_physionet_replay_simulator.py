import math

import pandas as pd

from src.data.schema import ALL_COLUMNS, CLINICAL_CHANNELS
from src.data.simulation.physionet_replay_simulator import PatientStream, select_demo_patient_ids


def _write_psv(path, rows: list[dict]):
    columns = [c for c in ALL_COLUMNS if c != "patient_id"]
    df = pd.DataFrame(rows, columns=columns)
    df.to_csv(path, sep="|", index=False)


def _row(hr=80.0, iculos=1, sepsis_label=0) -> dict:
    row = {c: float("nan") for c in ALL_COLUMNS if c != "patient_id"}
    row["HR"] = hr
    row["ICULOS"] = iculos
    row["SepsisLabel"] = sepsis_label
    return row


def test_patient_stream_converts_nan_channels_to_none(tmp_path):
    psv_path = tmp_path / "p000001.psv"
    _write_psv(psv_path, [_row(hr=90.0)])
    stream = PatientStream("p000001", psv_path, pd.read_csv(psv_path, sep="|"))

    payload = stream.next_payload()
    assert payload["patient_id"] == "p000001"
    assert payload["source"] == "physionet_sim"
    assert payload["channels"]["HR"] == 90.0
    assert payload["channels"]["Temp"] is None  # NaN in the source file


def test_patient_stream_advances_timestamp_by_one_simulated_hour_per_row(tmp_path):
    psv_path = tmp_path / "p000002.psv"
    _write_psv(psv_path, [_row(hr=80.0, iculos=1), _row(hr=85.0, iculos=2)])
    stream = PatientStream("p000002", psv_path, pd.read_csv(psv_path, sep="|"))

    first = stream.next_payload()
    second = stream.next_payload()
    from datetime import datetime
    dt1 = datetime.fromisoformat(first["timestamp"])
    dt2 = datetime.fromisoformat(second["timestamp"])
    assert (dt2 - dt1).total_seconds() == 3600
    assert first["channels"]["HR"] == 80.0
    assert second["channels"]["HR"] == 85.0


def test_patient_stream_loops_back_to_start_after_exhausting_rows(tmp_path):
    psv_path = tmp_path / "p000003.psv"
    _write_psv(psv_path, [_row(hr=80.0)])
    stream = PatientStream("p000003", psv_path, pd.read_csv(psv_path, sep="|"))

    stream.next_payload()
    looped = stream.next_payload()
    assert looped["channels"]["HR"] == 80.0
    assert stream.row_index == 1


def test_select_demo_patient_ids_prefers_a_mix_of_septic_and_stable(tmp_path):
    for i, sepsis_flag in enumerate([1, 0, 0, 1, 0], start=1):
        _write_psv(tmp_path / f"p{i:06d}.psv", [_row(sepsis_label=sepsis_flag)])

    selected = select_demo_patient_ids(tmp_path, n_septic=2, n_stable=2)
    assert len(selected) == 4
    assert "p000001" in selected  # septic
    assert "p000004" in selected  # septic
    assert "p000002" in selected  # stable
