"""Orchestrates the full Step 2 preprocessing pipeline for both datasets.

PhysioNet 2019 -> load -> patient-level split -> clean (train-fit) -> normalize
(train-fit) -> sliding windows -> save train/val/test .npz + metadata.json.

MIMIC-IV Demo -> load -> map onto the canonical schema -> save cleaned tables
(no windowing/training split -- this dataset's role is schema/dashboard testing,
not model training; see docs/architecture/system_architecture.md).
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np

from src.data.loaders.mimic_iv_loader import load_patients, load_vitals_long, resolve_item_mapping
from src.data.loaders.physionet_loader import DEFAULT_SET_NAMES, load_physionet_dataset
from src.data.preprocessing.cleaning import clean_physionet
from src.data.preprocessing.normalization import normalize_physionet
from src.data.preprocessing.split import add_split_column, split_patients
from src.data.preprocessing.windowing import build_windows
from src.data.schema import CLINICAL_CHANNELS

logger = logging.getLogger(__name__)


def run_physionet_pipeline(
    raw_dir: Path,
    output_dir: Path,
    set_names=DEFAULT_SET_NAMES,
    limit: Optional[int] = None,
    window_size: int = 8,
    stride: int = 1,
    val_size: float = 0.15,
    test_size: float = 0.15,
    random_state: int = 42,
    show_progress: bool = True,
) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading PhysioNet dataset from %s", raw_dir)
    df = load_physionet_dataset(raw_dir, set_names=set_names, limit=limit, show_progress=show_progress)

    logger.info("Splitting %d patients (val=%.2f, test=%.2f)", df["patient_id"].nunique(), val_size, test_size)
    split = split_patients(df, val_size=val_size, test_size=test_size, random_state=random_state)
    df = add_split_column(df, split)

    logger.info("Cleaning (forward/backward fill + train-median imputation)")
    cleaned, medians = clean_physionet(df, channels=CLINICAL_CHANNELS)

    logger.info("Normalizing (z-score, fit on train only)")
    normalized, scaler = normalize_physionet(cleaned, channels=CLINICAL_CHANNELS)

    counts = {}
    for split_name in ("train", "val", "test"):
        subset = normalized[normalized["split"] == split_name]
        logger.info("Building %s windows (window_size=%d, stride=%d)", split_name, window_size, stride)
        windowed = build_windows(subset, window_size=window_size, stride=stride, channels=CLINICAL_CHANNELS)
        out_path = output_dir / f"{split_name}.npz"
        np.savez_compressed(
            out_path,
            X=windowed.X,
            y=windowed.y,
            patient_ids=windowed.patient_ids,
            window_end_time=windowed.window_end_time,
        )
        counts[split_name] = {
            "n_patients": subset["patient_id"].nunique(),
            "n_windows": int(windowed.X.shape[0]),
            "positive_rate": float(windowed.y.mean()) if len(windowed.y) else 0.0,
        }
        logger.info("Saved %s -> %s (%s)", split_name, out_path, counts[split_name])

    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "physionet_2019",
        "set_names": list(set_names),
        "limit": limit,
        "window_size": window_size,
        "stride": stride,
        "channels": CLINICAL_CHANNELS,
        "n_channels": len(CLINICAL_CHANNELS),
        "split_sizes": {"val_size": val_size, "test_size": test_size, "random_state": random_state},
        "patient_ids": {"train": split.train_ids, "val": split.val_ids, "test": split.test_ids},
        "train_medians": medians,
        "scaler": scaler.to_dict(),
        "counts": counts,
    }
    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))
    logger.info("Saved metadata -> %s", metadata_path)
    return metadata


def run_mimic_iv_pipeline(raw_dir: Path, output_dir: Path) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Resolving MIMIC-IV Demo channel -> itemid mapping")
    mapping = resolve_item_mapping(raw_dir)

    logger.info("Loading MIMIC-IV Demo patients table")
    patients = load_patients(raw_dir)
    patients_path = output_dir / "patients.parquet"
    patients.to_parquet(patients_path, index=False)

    logger.info("Loading MIMIC-IV Demo vitals (long format)")
    vitals = load_vitals_long(raw_dir, mapping)
    vitals_path = output_dir / "vitals_long.parquet"
    vitals.to_parquet(vitals_path, index=False)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "mimic_iv_demo",
        "n_patients": int(patients["patient_id"].nunique()),
        "n_vitals_rows": int(len(vitals)),
        "resolved_channels": {k: {kk: vv for kk, vv in v.items()} for k, v in mapping.items()},
        "unresolved_channels": sorted(set(CLINICAL_CHANNELS) - set(mapping.keys())),
        "outputs": {"patients": str(patients_path), "vitals_long": str(vitals_path)},
    }
    report_path = output_dir / "mapping_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    logger.info("Saved MIMIC-IV mapping report -> %s", report_path)
    return report
