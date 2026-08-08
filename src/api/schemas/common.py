"""Shared response-shaping helpers and Literal types matching
docs/architecture/database_design.md's enumerated fields exactly."""
from typing import Literal

from bson import ObjectId

RiskLevel = Literal["Low", "Medium", "High", "Critical"]
VitalsSource = Literal["physionet_sim", "mimic_replay", "iot_sensor"]
PatientSourceDataset = Literal["physionet_2019", "mimic_iv_demo", "live"]
PatientStatus = Literal["active", "discharged", "deceased"]
ExplanationMethod = Literal["shap", "lime"]


def mongo_doc_to_dict(doc: dict) -> dict:
    """Converts a MongoDB document into a JSON-serializable dict: `_id` -> `id`
    (str), and any other ObjectId-valued fields (e.g. `prediction_id`) -> str."""
    out = dict(doc)
    if "_id" in out:
        out["id"] = str(out.pop("_id"))
    for key, value in out.items():
        if isinstance(value, ObjectId):
            out[key] = str(value)
    return out
