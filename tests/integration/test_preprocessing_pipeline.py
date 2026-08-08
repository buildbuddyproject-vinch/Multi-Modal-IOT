import json
from pathlib import Path

import numpy as np
import pytest

from src.data.preprocessing.pipeline import run_physionet_pipeline
from src.data.schema import CLINICAL_CHANNELS

HEADER = "HR|O2Sat|Temp|SBP|MAP|DBP|Resp|EtCO2|BaseExcess|HCO3|FiO2|pH|PaCO2|SaO2|AST|BUN|Alkalinephos|Calcium|Chloride|Creatinine|Bilirubin_direct|Glucose|Lactate|Magnesium|Phosphate|Potassium|Bilirubin_total|TroponinI|Hct|Hgb|PTT|WBC|Fibrinogen|Platelets|Age|Gender|Unit1|Unit2|HospAdmTime|ICULOS|SepsisLabel"


def _write_patient(set_dir: Path, patient_id: str, n_rows: int, septic: bool, seed: int) -> None:
    rng = np.random.default_rng(seed)
    lines = [HEADER]
    for t in range(1, n_rows + 1):
        # sparsely-observed channels: most NaN, HR/Glucose always present
        values = ["NaN"] * 34
        values[0] = f"{70 + rng.integers(-5, 5)}"  # HR
        values[21] = f"{100 + rng.integers(-10, 10)}"  # Glucose
        label = 1 if (septic and t >= n_rows - 1) else 0
        demo = ["60", "1", "NaN", "NaN", "-1.0", str(t)]
        lines.append("|".join(values + demo + [str(label)]))
    (set_dir / f"{patient_id}.psv").write_text("\n".join(lines))


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    set_a = tmp_path / "training_setA"
    set_a.mkdir()
    for i in range(30):
        _write_patient(set_a, f"p{i:06d}", n_rows=12, septic=(i % 5 == 0), seed=i)
    return tmp_path


def test_full_pipeline_produces_expected_artifacts(raw_dir, tmp_path):
    output_dir = tmp_path / "processed"
    metadata = run_physionet_pipeline(
        raw_dir=raw_dir,
        output_dir=output_dir,
        set_names=("training_setA",),
        window_size=4,
        stride=1,
        val_size=0.2,
        test_size=0.2,
        random_state=0,
        show_progress=False,
    )

    assert (output_dir / "train.npz").exists()
    assert (output_dir / "val.npz").exists()
    assert (output_dir / "test.npz").exists()
    assert (output_dir / "metadata.json").exists()

    saved_metadata = json.loads((output_dir / "metadata.json").read_text())
    assert saved_metadata["channels"] == CLINICAL_CHANNELS
    assert saved_metadata["n_channels"] == 34

    train_ids = set(saved_metadata["patient_ids"]["train"])
    val_ids = set(saved_metadata["patient_ids"]["val"])
    test_ids = set(saved_metadata["patient_ids"]["test"])
    assert train_ids.isdisjoint(val_ids)
    assert train_ids.isdisjoint(test_ids)
    assert val_ids.isdisjoint(test_ids)
    assert train_ids | val_ids | test_ids == {f"p{i:06d}" for i in range(30)}

    for split_name in ("train", "val", "test"):
        with np.load(output_dir / f"{split_name}.npz", allow_pickle=True) as data:
            X, y, patient_ids = data["X"], data["y"], data["patient_ids"]
            assert X.ndim == 3
            assert X.shape[1] == 4  # window_size
            assert X.shape[2] == 34  # n_channels
            assert not np.isnan(X).any()
            assert len(y) == X.shape[0] == len(patient_ids)
            assert set(patient_ids) <= set(saved_metadata["patient_ids"][split_name])


def test_pipeline_respects_limit(raw_dir, tmp_path):
    output_dir = tmp_path / "processed_limited"
    metadata = run_physionet_pipeline(
        raw_dir=raw_dir,
        output_dir=output_dir,
        set_names=("training_setA",),
        limit=10,
        window_size=4,
        val_size=0.2,
        test_size=0.2,
        random_state=0,
        show_progress=False,
    )
    total_patients = sum(len(v) for v in metadata["patient_ids"].values())
    assert total_patients == 10
