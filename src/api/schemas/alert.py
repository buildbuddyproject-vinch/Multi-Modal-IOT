from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from src.api.schemas.common import RiskLevel


class AlertCreate(BaseModel):
    patient_id: str
    risk_level: RiskLevel
    message: str
    prediction_id: Optional[str] = None
    channels_dispatched: Optional[list[str]] = None
    dispatch_status: Optional[dict[str, str]] = None


class AlertAcknowledge(BaseModel):
    acknowledged_by: str


class AlertOut(BaseModel):
    id: str
    patient_id: str
    prediction_id: Optional[str] = None
    risk_level: str
    message: str
    channels_dispatched: list[str] = []
    dispatch_status: dict = {}
    acknowledged: bool
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
