from pathlib import Path

import pandas as pd
import pytest

from src.data.loaders.mimic_iv_loader import load_patients, load_vitals_long, resolve_item_mapping


@pytest.fixture
def mimic_dir(tmp_path: Path) -> Path:
    (tmp_path / "hosp").mkdir()
    (tmp_path / "icu").mkdir()

    pd.DataFrame({
        "itemid": [220045, 220277, 220179, 999999],
        "label": ["Heart Rate", "O2 saturation pulseoxymetry", "Non Invasive Blood Pressure systolic", "Unrelated Alarm"],
        "linksto": ["chartevents", "chartevents", "chartevents", "chartevents"],
    }).to_csv(tmp_path / "icu" / "d_items.csv", index=False)

    pd.DataFrame({
        "itemid": [50931, 50813, 50813, 99999],
        "label": ["Glucose", "Lactate", "Lactate", "Some Urine Test"],
        "fluid": ["Blood", "Blood", "Blood", "Urine"],
        "category": ["Chemistry", "Blood Gas", "Blood Gas", "Chemistry"],
    }).to_csv(tmp_path / "hosp" / "d_labitems.csv", index=False)

    pd.DataFrame({
        "subject_id": [1, 1, 1, 2],
        "charttime": ["2150-01-01 01:00:00", "2150-01-01 02:00:00", "2150-01-01 02:00:00", "2150-01-01 01:00:00"],
        "itemid": [220045, 220045, 220277, 220179],
        "valuenum": [80.0, 85.0, 97.0, 120.0],
    }).to_csv(tmp_path / "icu" / "chartevents.csv", index=False)

    pd.DataFrame({
        "subject_id": [1, 1, 2],
        "charttime": ["2150-01-01 01:30:00", "2150-01-01 03:00:00", "2150-01-01 01:30:00"],
        "itemid": [50931, 50813, 50931],
        "valuenum": [110.0, 1.4, 95.0],
    }).to_csv(tmp_path / "hosp" / "labevents.csv", index=False)

    pd.DataFrame({
        "subject_id": [1, 2],
        "gender": ["F", "M"],
        "anchor_age": [65, 72],
        "anchor_year": [2150, 2150],
        "anchor_year_group": ["2017-2019", "2017-2019"],
        "dod": ["", ""],
    }).to_csv(tmp_path / "hosp" / "patients.csv", index=False)

    pd.DataFrame({
        "subject_id": [1, 2],
        "hadm_id": [10, 20],
        "admittime": ["2150-01-01 00:00:00", "2150-01-01 00:00:00"],
        "dischtime": ["2150-01-05 00:00:00", "2150-01-03 00:00:00"],
    }).to_csv(tmp_path / "hosp" / "admissions.csv", index=False)

    pd.DataFrame({
        "subject_id": [1, 2],
        "hadm_id": [10, 20],
        "stay_id": [100, 200],
        "first_careunit": ["MICU", "SICU"],
        "intime": ["2150-01-01 00:30:00", "2150-01-01 00:30:00"],
        "outtime": ["2150-01-04 00:00:00", "2150-01-02 00:00:00"],
        "los": [3.0, 1.0],
    }).to_csv(tmp_path / "icu" / "icustays.csv", index=False)

    return tmp_path


def test_resolve_item_mapping_picks_highest_volume_itemid(mimic_dir):
    mapping = resolve_item_mapping(mimic_dir)
    assert mapping["HR"]["itemid"] == 220045
    assert mapping["HR"]["source"] == "chartevents"
    assert mapping["O2Sat"]["itemid"] == 220277
    assert mapping["SBP"]["itemid"] == 220179
    assert mapping["Glucose"]["itemid"] == 50931
    assert mapping["Lactate"]["itemid"] == 50813
    # channels with no matching label at all must be absent, not guessed
    assert "Temp" not in mapping
    assert "TroponinI" not in mapping


def test_load_vitals_long_shapes_and_units(mimic_dir):
    mapping = resolve_item_mapping(mimic_dir)
    vitals = load_vitals_long(mimic_dir, mapping)
    assert set(vitals.columns) == {"patient_id", "charttime", "channel", "value", "source"}
    assert (vitals["source"] == "mimic_iv_demo").all()
    assert vitals["patient_id"].dtype == object
    hr_rows = vitals[(vitals["patient_id"] == "1") & (vitals["channel"] == "HR")]
    assert sorted(hr_rows["value"].tolist()) == [80.0, 85.0]


def test_load_patients_merges_demographics(mimic_dir):
    patients = load_patients(mimic_dir)
    assert len(patients) == 2
    assert set(patients["patient_id"]) == {"1", "2"}
    assert (patients["source_dataset"] == "mimic_iv_demo").all()
    row1 = patients[patients["patient_id"] == "1"].iloc[0]
    assert row1["age"] == 65
    assert row1["sex"] == "F"
    assert row1["unit_admitted"] == "MICU"
