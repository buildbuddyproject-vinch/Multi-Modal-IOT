from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.run_eda import run_mimic_eda, run_physionet_eda
from src.data.schema import CLINICAL_CHANNELS

HEADER = "HR|O2Sat|Temp|SBP|MAP|DBP|Resp|EtCO2|BaseExcess|HCO3|FiO2|pH|PaCO2|SaO2|AST|BUN|Alkalinephos|Calcium|Chloride|Creatinine|Bilirubin_direct|Glucose|Lactate|Magnesium|Phosphate|Potassium|Bilirubin_total|TroponinI|Hct|Hgb|PTT|WBC|Fibrinogen|Platelets|Age|Gender|Unit1|Unit2|HospAdmTime|ICULOS|SepsisLabel"


def _write_patient(set_dir: Path, patient_id: str, n_rows: int, septic: bool, seed: int) -> None:
    rng = np.random.default_rng(seed)
    lines = [HEADER]
    for t in range(1, n_rows + 1):
        values = ["NaN"] * 34
        values[0] = f"{70 + rng.integers(-5, 5)}"   # HR
        values[6] = f"{18 + rng.integers(-3, 3)}"    # Resp
        values[4] = f"{85 + rng.integers(-5, 5)}"    # MAP
        values[1] = f"{96 + rng.integers(-2, 2)}"    # O2Sat
        values[21] = f"{100 + rng.integers(-10, 10)}"  # Glucose
        label = 1 if (septic and t >= n_rows - 1) else 0
        demo = ["60", "1", "NaN", "NaN", "-1.0", str(t)]
        lines.append("|".join(values + demo + [str(label)]))
    (set_dir / f"{patient_id}.psv").write_text("\n".join(lines))


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    set_a = tmp_path / "training_setA"
    set_a.mkdir()
    (tmp_path / "training_setB").mkdir()  # load_physionet_dataset's default set_names expects both
    for i in range(25):
        _write_patient(set_a, f"p{i:06d}", n_rows=25, septic=(i % 5 == 0), seed=i)
    return tmp_path


@pytest.fixture
def processed_dir(tmp_path: Path) -> Path:
    d = tmp_path / "processed"
    d.mkdir()
    n_channels = len(CLINICAL_CHANNELS)
    rng = np.random.default_rng(0)
    X = rng.normal(size=(50, 8, n_channels)).astype(np.float32)
    y = rng.integers(0, 2, size=50)
    np.savez_compressed(d / "train.npz", X=X, y=y, patient_ids=np.array([f"p{i}" for i in range(50)]), window_end_time=np.arange(50))
    return d


def test_physionet_eda_produces_all_artifacts(raw_dir, processed_dir, tmp_path):
    output_dir = tmp_path / "eda_output"
    summary = run_physionet_eda(raw_dir=raw_dir, processed_dir=processed_dir, output_dir=output_dir, limit=None)

    expected_stats = [
        "descriptive_statistics.csv", "label_group_statistics.csv", "missingness_report.csv",
        "missingness_by_patient.csv", "correlation_matrix.csv", "top_correlated_pairs.csv",
        "feature_importance.csv",
    ]
    for name in expected_stats:
        path = output_dir / "stats" / name
        assert path.exists(), f"missing {path}"
        assert path.stat().st_size > 0

    expected_plots = [
        "missingness_by_channel.png", "correlation_heatmap.png", "distributions_by_label.png",
        "feature_importance.png",
    ]
    for name in expected_plots:
        path = output_dir / "plots" / name
        assert path.exists(), f"missing {path}"
        assert path.stat().st_size > 0

    assert summary["n_patients"] == 25
    assert summary["top_missing_channel"] is not None


def test_physionet_eda_handles_missing_processed_dir_gracefully(raw_dir, tmp_path):
    output_dir = tmp_path / "eda_output_no_processed"
    summary = run_physionet_eda(raw_dir=raw_dir, processed_dir=tmp_path / "does_not_exist", output_dir=output_dir, limit=None)
    assert not (output_dir / "stats" / "feature_importance.csv").exists()
    assert summary["top_important_channel"] is None


def test_mimic_eda_produces_artifacts(tmp_path):
    processed_mimic_dir = tmp_path / "mimic_processed"
    processed_mimic_dir.mkdir()
    pd.DataFrame({"patient_id": ["1", "2"], "age": [60, 70], "sex": ["F", "M"], "unit_admitted": ["MICU", "SICU"]}).to_parquet(processed_mimic_dir / "patients.parquet")
    pd.DataFrame({"patient_id": ["1", "1", "2"], "channel": ["HR", "HR", "Glucose"], "value": [80.0, 82.0, 100.0], "charttime": pd.to_datetime(["2150-01-01", "2150-01-01", "2150-01-01"])}).to_parquet(processed_mimic_dir / "vitals_long.parquet")

    output_dir = tmp_path / "eda_output_mimic"
    summary = run_mimic_eda(processed_mimic_dir, output_dir)

    assert (output_dir / "stats" / "mimic_channel_coverage.csv").exists()
    assert (output_dir / "stats" / "mimic_demographics.json").exists()
    assert (output_dir / "plots" / "mimic_channel_coverage.png").exists()
    assert summary["n_patients"] == 2


def test_mimic_eda_handles_missing_files_gracefully(tmp_path):
    summary = run_mimic_eda(tmp_path / "nonexistent", tmp_path / "eda_out")
    assert summary == {}
