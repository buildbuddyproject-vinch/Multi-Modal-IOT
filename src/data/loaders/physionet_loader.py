"""Loader for the PhysioNet/CinC 2019 Sepsis Challenge dataset (pipe-separated .psv files,
one file per patient, one row per ICU hour)."""
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
from tqdm import tqdm

from src.data.schema import ALL_COLUMNS, LABEL_COLUMN, PATIENT_ID_COLUMN, TIME_COLUMN

DEFAULT_SET_NAMES = ("training_setA", "training_setB")


def list_patient_files(raw_dir: Path, set_names: Iterable[str] = DEFAULT_SET_NAMES) -> list[Path]:
    """Return all .psv patient files across the given training sets, sorted for determinism."""
    files: list[Path] = []
    for set_name in set_names:
        set_dir = Path(raw_dir) / set_name
        if not set_dir.exists():
            raise FileNotFoundError(f"PhysioNet set directory not found: {set_dir}")
        files.extend(sorted(set_dir.glob("*.psv")))
    if not files:
        raise FileNotFoundError(f"No .psv files found under {raw_dir} for sets {list(set_names)}")
    return sorted(files)


def load_patient_file(filepath: Path) -> pd.DataFrame:
    """Load one patient's .psv file into a DataFrame with a patient_id column."""
    df = pd.read_csv(filepath, sep="|")
    df.insert(0, PATIENT_ID_COLUMN, filepath.stem)
    return df


def load_physionet_dataset(
    raw_dir: Path,
    set_names: Iterable[str] = DEFAULT_SET_NAMES,
    limit: Optional[int] = None,
    show_progress: bool = True,
) -> pd.DataFrame:
    """Load and concatenate PhysioNet patient files into one long DataFrame.

    Parameters
    ----------
    raw_dir: root directory containing training_setA/ and training_setB/
    set_names: which subdirectories to include
    limit: if given, only load the first `limit` patient files (for fast dev/test runs)
    """
    files = list_patient_files(raw_dir, set_names)
    if limit is not None:
        files = files[:limit]

    frames = []
    iterator = tqdm(files, desc="Loading PhysioNet patients") if show_progress else files
    for filepath in iterator:
        frames.append(load_patient_file(filepath))

    combined = pd.concat(frames, ignore_index=True)
    missing_cols = set(ALL_COLUMNS) - set(combined.columns)
    if missing_cols:
        raise ValueError(f"PhysioNet data is missing expected columns: {sorted(missing_cols)}")
    combined = combined[ALL_COLUMNS].sort_values([PATIENT_ID_COLUMN, TIME_COLUMN]).reset_index(drop=True)
    combined[LABEL_COLUMN] = combined[LABEL_COLUMN].astype(int)
    return combined
