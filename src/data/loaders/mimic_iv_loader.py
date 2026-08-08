"""Loader for the MIMIC-IV Clinical Database Demo v2.2.

Role (per docs/architecture/system_architecture.md): schema understanding, dashboard/
backend testing, and historical visualization — NOT model training. This loader maps
MIMIC-IV's chartevents/labevents itemid-based schema onto the same canonical channel
names used by PhysioNet (src/data/schema.py), so the rest of the system (database,
API, dashboard) can treat both sources identically.

Item IDs are resolved dynamically from d_items.csv / d_labitems.csv by label match
rather than hardcoded, so this loader stays correct even if a different MIMIC-IV
export has different itemids for the same concept.
"""
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from src.data.schema import CLINICAL_CHANNELS

logger = logging.getLogger(__name__)

# Candidate d_items labels (chartevents) per vital channel, in priority order.
CHARTEVENTS_LABEL_CANDIDATES: dict[str, list[str]] = {
    "HR": ["Heart Rate"],
    "O2Sat": ["O2 saturation pulseoxymetry"],
    "Temp": ["Temperature Celsius", "Temperature Fahrenheit"],
    "SBP": ["Non Invasive Blood Pressure systolic", "Arterial Blood Pressure systolic"],
    "MAP": ["Non Invasive Blood Pressure mean", "Arterial Blood Pressure mean"],
    "DBP": ["Non Invasive Blood Pressure diastolic", "Arterial Blood Pressure diastolic"],
    "Resp": ["Respiratory Rate"],
    "EtCO2": ["EtCO2", "End Tidal CO2"],
    "SaO2": ["Arterial O2 Saturation"],
}

# Channels whose source itemid is reported in Fahrenheit and must be converted to Celsius.
FAHRENHEIT_CHARTEVENTS_LABELS = {"Temperature Fahrenheit"}

# Candidate d_labitems labels (labevents) per lab channel, in priority order.
LABEVENTS_LABEL_CANDIDATES: dict[str, list[str]] = {
    "BaseExcess": ["Base Excess"],
    "HCO3": ["Bicarbonate"],
    "FiO2": ["Inspired O2 Fraction", "Oxygen"],
    "pH": ["pH"],
    "PaCO2": ["pCO2"],
    "AST": ["Asparate Aminotransferase (AST)"],
    "BUN": ["Urea Nitrogen"],
    "Alkalinephos": ["Alkaline Phosphatase"],
    "Calcium": ["Calcium, Total"],
    "Chloride": ["Chloride"],
    "Creatinine": ["Creatinine"],
    "Bilirubin_direct": ["Bilirubin, Direct"],
    "Glucose": ["Glucose"],
    "Lactate": ["Lactate"],
    "Magnesium": ["Magnesium"],
    "Phosphate": ["Phosphate"],
    "Potassium": ["Potassium"],
    "Bilirubin_total": ["Bilirubin, Total"],
    "TroponinI": ["Troponin I"],
    "Hct": ["Hematocrit"],
    "Hgb": ["Hemoglobin"],
    "PTT": ["PTT"],
    "WBC": ["White Blood Cells"],
    "Fibrinogen": ["Fibrinogen, Functional", "Fibrinogen"],
    "Platelets": ["Platelet Count"],
}

def _itemid_event_counts(csv_path: Path) -> pd.Series:
    """Count actual rows per itemid in a (large) events file, reading only that column.

    MIMIC-IV commonly has multiple itemids for the same clinical concept (different
    measurement sources/eras); the dictionary alone can't tell which one this dataset
    actually uses, so candidate itemids are ranked by real event volume, not by a
    fixed category preference.
    """
    return pd.read_csv(csv_path, usecols=["itemid"])["itemid"].value_counts()


def _resolve_chartevents_mapping(d_items: pd.DataFrame, event_counts: pd.Series) -> dict[str, dict]:
    items = d_items[d_items["linksto"] == "chartevents"]
    mapping: dict[str, dict] = {}
    for channel, candidates in CHARTEVENTS_LABEL_CANDIDATES.items():
        matches = items[items["label"].str.lower().isin([c.lower() for c in candidates])]
        if matches.empty:
            continue
        matches = matches.assign(_count=matches["itemid"].map(event_counts).fillna(0))
        best = matches.sort_values("_count", ascending=False).iloc[0]
        if best["_count"] <= 0:
            continue
        mapping[channel] = {
            "itemid": int(best["itemid"]),
            "label": best["label"],
            "is_fahrenheit": best["label"] in FAHRENHEIT_CHARTEVENTS_LABELS,
        }
    return mapping


def _resolve_labevents_mapping(d_labitems: pd.DataFrame, event_counts: pd.Series) -> dict[str, dict]:
    blood_items = d_labitems[d_labitems["fluid"] == "Blood"]
    mapping: dict[str, dict] = {}
    for channel, candidates in LABEVENTS_LABEL_CANDIDATES.items():
        matches = blood_items[blood_items["label"].str.lower().isin([c.lower() for c in candidates])]
        if matches.empty:
            continue
        matches = matches.assign(_count=matches["itemid"].map(event_counts).fillna(0))
        best = matches.sort_values("_count", ascending=False).iloc[0]
        if best["_count"] <= 0:
            continue
        mapping[channel] = {"itemid": int(best["itemid"]), "label": best["label"]}
    return mapping


def resolve_item_mapping(mimic_dir: Path) -> dict[str, dict]:
    """Resolve every canonical channel to the MIMIC-IV itemid that actually has data.

    Returns a dict: channel -> {"source": "chartevents"|"labevents", "itemid": int, ...}
    Channels with no itemid that has real events are simply absent (stay NaN downstream).
    """
    d_items = pd.read_csv(mimic_dir / "icu" / "d_items.csv")
    d_labitems = pd.read_csv(mimic_dir / "hosp" / "d_labitems.csv")
    chart_counts = _itemid_event_counts(mimic_dir / "icu" / "chartevents.csv")
    lab_counts = _itemid_event_counts(mimic_dir / "hosp" / "labevents.csv")

    mapping: dict[str, dict] = {}
    for channel, info in _resolve_chartevents_mapping(d_items, chart_counts).items():
        mapping[channel] = {"source": "chartevents", **info}
    for channel, info in _resolve_labevents_mapping(d_labitems, lab_counts).items():
        if channel not in mapping:  # chartevents takes priority if both exist
            mapping[channel] = {"source": "labevents", **info}

    unresolved = [c for c in CLINICAL_CHANNELS if c not in mapping]
    if unresolved:
        logger.info("MIMIC-IV Demo: %d/%d channels unresolved (no itemid with real events): %s",
                     len(unresolved), len(CLINICAL_CHANNELS), unresolved)
    return mapping


def load_patients(mimic_dir: Path) -> pd.DataFrame:
    patients = pd.read_csv(mimic_dir / "hosp" / "patients.csv")
    admissions = pd.read_csv(mimic_dir / "hosp" / "admissions.csv", usecols=["subject_id", "hadm_id", "admittime", "dischtime"])
    icustays = pd.read_csv(mimic_dir / "icu" / "icustays.csv", usecols=["subject_id", "hadm_id", "stay_id", "first_careunit", "intime", "outtime", "los"])

    merged = icustays.merge(admissions, on=["subject_id", "hadm_id"], how="left")
    merged = merged.merge(patients[["subject_id", "gender", "anchor_age"]], on="subject_id", how="left")
    merged = merged.rename(columns={
        "subject_id": "patient_id", "first_careunit": "unit_admitted",
        "gender": "sex", "anchor_age": "age", "intime": "admission_time",
    })
    merged["patient_id"] = merged["patient_id"].astype(str)
    merged["source_dataset"] = "mimic_iv_demo"
    return merged[["patient_id", "stay_id", "age", "sex", "unit_admitted", "admission_time", "outtime", "los", "source_dataset"]]


def load_vitals_long(mimic_dir: Path, mapping: Optional[dict[str, dict]] = None) -> pd.DataFrame:
    """Return a long-format table: patient_id, charttime, channel, value.

    This is the shape that maps 1:1 onto the MongoDB `vitals` collection when grouped
    by (patient_id, charttime) into a `channels` sub-document.
    """
    if mapping is None:
        mapping = resolve_item_mapping(mimic_dir)

    frames: list[pd.DataFrame] = []

    chart_channels = {c: m for c, m in mapping.items() if m["source"] == "chartevents"}
    if chart_channels:
        chart_itemids = {m["itemid"] for m in chart_channels.values()}
        itemid_to_channel = {m["itemid"]: c for c, m in chart_channels.items()}
        chartevents = pd.read_csv(
            mimic_dir / "icu" / "chartevents.csv",
            usecols=["subject_id", "charttime", "itemid", "valuenum"],
        )
        chartevents = chartevents[chartevents["itemid"].isin(chart_itemids)].dropna(subset=["valuenum"])
        chartevents["channel"] = chartevents["itemid"].map(itemid_to_channel)
        for label_info in chart_channels.values():
            if label_info.get("is_fahrenheit"):
                fahrenheit_mask = chartevents["itemid"] == label_info["itemid"]
                chartevents.loc[fahrenheit_mask, "valuenum"] = (
                    (chartevents.loc[fahrenheit_mask, "valuenum"] - 32) * 5.0 / 9.0
                )
        chartevents = chartevents.rename(columns={"subject_id": "patient_id", "valuenum": "value"})
        frames.append(chartevents[["patient_id", "charttime", "channel", "value"]])

    lab_channels = {c: m for c, m in mapping.items() if m["source"] == "labevents"}
    if lab_channels:
        lab_itemids = {m["itemid"] for m in lab_channels.values()}
        itemid_to_channel = {m["itemid"]: c for c, m in lab_channels.items()}
        labevents = pd.read_csv(
            mimic_dir / "hosp" / "labevents.csv",
            usecols=["subject_id", "charttime", "itemid", "valuenum"],
        )
        labevents = labevents[labevents["itemid"].isin(lab_itemids)].dropna(subset=["valuenum"])
        labevents["channel"] = labevents["itemid"].map(itemid_to_channel)
        labevents = labevents.rename(columns={"subject_id": "patient_id", "valuenum": "value"})
        frames.append(labevents[["patient_id", "charttime", "channel", "value"]])

    if not frames:
        return pd.DataFrame(columns=["patient_id", "charttime", "channel", "value"])

    combined = pd.concat(frames, ignore_index=True)
    combined["patient_id"] = combined["patient_id"].astype(str)
    combined["charttime"] = pd.to_datetime(combined["charttime"])
    combined["source"] = "mimic_iv_demo"
    return combined.sort_values(["patient_id", "charttime"]).reset_index(drop=True)
