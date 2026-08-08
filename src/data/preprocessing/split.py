"""Patient-level train/validation/test split.

Splitting must happen on patient_id (never on individual rows/timesteps) and before any
statistic (median, mean, std) is computed for imputation or normalization -- otherwise
information about validation/test patients leaks into the training statistics.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from src.data.schema import LABEL_COLUMN, PATIENT_ID_COLUMN


@dataclass(frozen=True)
class PatientSplit:
    train_ids: list[str]
    val_ids: list[str]
    test_ids: list[str]

    def assign(self, patient_id: str) -> str:
        if patient_id in self._train_set:
            return "train"
        if patient_id in self._val_set:
            return "val"
        if patient_id in self._test_set:
            return "test"
        raise KeyError(f"patient_id {patient_id!r} was not part of this split")

    def __post_init__(self):
        object.__setattr__(self, "_train_set", set(self.train_ids))
        object.__setattr__(self, "_val_set", set(self.val_ids))
        object.__setattr__(self, "_test_set", set(self.test_ids))


def _safe_stratified_split(ids: np.ndarray, labels: np.ndarray, test_size: float, random_state: int):
    """Stratified split that falls back to a plain split if a class has too few
    members to stratify (only relevant for tiny/dev datasets, e.g. --limit runs)."""
    _, class_counts = np.unique(labels, return_counts=True)
    stratify = labels if class_counts.min() >= 2 else None
    return train_test_split(ids, labels, test_size=test_size, stratify=stratify, random_state=random_state)


def split_patients(
    df: pd.DataFrame,
    val_size: float = 0.15,
    test_size: float = 0.15,
    random_state: int = 42,
) -> PatientSplit:
    """Split unique patient_ids into train/val/test, stratified by whether the patient
    ever has a positive SepsisLabel (keeps the sepsis prevalence roughly equal across splits).
    """
    per_patient = df.groupby(PATIENT_ID_COLUMN)[LABEL_COLUMN].max().reset_index()
    ids = per_patient[PATIENT_ID_COLUMN].values
    ever_septic = per_patient[LABEL_COLUMN].values

    train_ids, holdout_ids, train_labels, holdout_labels = _safe_stratified_split(
        ids, ever_septic, test_size=val_size + test_size, random_state=random_state,
    )
    relative_test_size = test_size / (val_size + test_size)
    val_ids, test_ids, _, _ = _safe_stratified_split(
        holdout_ids, holdout_labels, test_size=relative_test_size, random_state=random_state,
    )

    assert set(train_ids).isdisjoint(val_ids)
    assert set(train_ids).isdisjoint(test_ids)
    assert set(val_ids).isdisjoint(test_ids)

    return PatientSplit(
        train_ids=sorted(train_ids.tolist()),
        val_ids=sorted(val_ids.tolist()),
        test_ids=sorted(test_ids.tolist()),
    )


def add_split_column(df: pd.DataFrame, split: PatientSplit) -> pd.DataFrame:
    df = df.copy()
    df["split"] = df[PATIENT_ID_COLUMN].map(split.assign)
    return df
