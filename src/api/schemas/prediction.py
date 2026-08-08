from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PredictionCreate(BaseModel):
    """`predicted_label` and `risk_level` are NOT accepted here -- they're
    derived server-side from `sepsis_probability` (src/models/inference/risk.py)
    so that every caller (Step 9's seed script, Step 11's simulator, a future
    IoT gateway) is held to the same authoritative threshold, and so the Step 10
    alert engine can trust `risk_level` when deciding whether to notify anyone."""
    patient_id: str
    sepsis_probability: float = Field(..., ge=0.0, le=1.0)
    model_version: str
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    inference_latency_ms: Optional[float] = None


class PredictionOut(BaseModel):
    id: str
    patient_id: str
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    sepsis_probability: float
    predicted_label: int
    model_version: str
    risk_level: str
    inference_latency_ms: Optional[float] = None
    created_at: Optional[datetime] = None
