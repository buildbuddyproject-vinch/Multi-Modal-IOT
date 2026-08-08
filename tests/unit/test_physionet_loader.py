from pathlib import Path

import pandas as pd
import pytest

from src.data.loaders.physionet_loader import list_patient_files, load_patient_file, load_physionet_dataset
from src.data.schema import ALL_COLUMNS, LABEL_COLUMN, PATIENT_ID_COLUMN

HEADER = "HR|O2Sat|Temp|SBP|MAP|DBP|Resp|EtCO2|BaseExcess|HCO3|FiO2|pH|PaCO2|SaO2|AST|BUN|Alkalinephos|Calcium|Chloride|Creatinine|Bilirubin_direct|Glucose|Lactate|Magnesium|Phosphate|Potassium|Bilirubin_total|TroponinI|Hct|Hgb|PTT|WBC|Fibrinogen|Platelets|Age|Gender|Unit1|Unit2|HospAdmTime|ICULOS|SepsisLabel"
NAN_ROW = "|".join(["NaN"] * 34)


def _row(iculos: int, label: int, hr="NaN") -> str:
    values = [hr] + ["NaN"] * 33
    demo = ["65", "1", "NaN", "NaN", "-1.0", str(iculos)]
    return "|".join(values + demo + [str(label)])


def _write_patient_file(tmp_path: Path, set_name: str, patient_id: str, n_rows: int, septic: bool = False) -> Path:
    set_dir = tmp_path / set_name
    set_dir.mkdir(parents=True, exist_ok=True)
    filepath = set_dir / f"{patient_id}.psv"
    lines = [HEADER]
    for t in range(1, n_rows + 1):
        label = 1 if (septic and t == n_rows) else 0
        lines.append(_row(t, label, hr=str(70 + t)))
    filepath.write_text("\n".join(lines))
    return filepath


@pytest.fixture
def raw_dir(tmp_path):
    _write_patient_file(tmp_path, "training_setA", "p000001", n_rows=5, septic=False)
    _write_patient_file(tmp_path, "training_setA", "p000002", n_rows=8, septic=True)
    _write_patient_file(tmp_path, "training_setB", "p100001", n_rows=3, septic=False)
    return tmp_path


def test_list_patient_files_finds_all_sets(raw_dir):
    files = list_patient_files(raw_dir)
    assert len(files) == 3
    assert {f.stem for f in files} == {"p000001", "p000002", "p100001"}


def test_list_patient_files_missing_dir_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        list_patient_files(tmp_path)


def test_load_patient_file_adds_patient_id(raw_dir):
    filepath = raw_dir / "training_setA" / "p000001.psv"
    df = load_patient_file(filepath)
    assert (df[PATIENT_ID_COLUMN] == "p000001").all()
    assert len(df) == 5


def test_load_physionet_dataset_combines_and_orders(raw_dir):
    df = load_physionet_dataset(raw_dir, limit=None, show_progress=False)
    assert list(df.columns) == ALL_COLUMNS
    assert df[PATIENT_ID_COLUMN].nunique() == 3
    assert len(df) == 5 + 8 + 3
    # sorted by patient then time
    p2 = df[df[PATIENT_ID_COLUMN] == "p000002"]
    assert list(p2["ICULOS"]) == list(range(1, 9))
    assert df[LABEL_COLUMN].dtype == int


def test_load_physionet_dataset_respects_limit(raw_dir):
    df = load_physionet_dataset(raw_dir, limit=1, show_progress=False)
    assert df[PATIENT_ID_COLUMN].nunique() == 1


def test_septic_patient_has_positive_label(raw_dir):
    df = load_physionet_dataset(raw_dir, show_progress=False)
    p2 = df[df[PATIENT_ID_COLUMN] == "p000002"]
    assert p2[LABEL_COLUMN].sum() == 1
    assert p2[LABEL_COLUMN].iloc[-1] == 1
