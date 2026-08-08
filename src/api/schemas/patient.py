from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from src.api.schemas.common import PatientSourceDataset, PatientStatus


class PatientCreate(BaseModel):
    patient_id: str = Field(..., min_length=1, examples=["p000001"])
    source_dataset: PatientSourceDataset
    age: Optional[float] = Field(None, ge=0, le=130)
    sex: Optional[Literal["M", "F"]] = None
    unit_admitted: Optional[str] = None
    admission_time: Optional[datetime] = None
    current_status: PatientStatus = "active"


class PatientUpdate(BaseModel):
    age: Optional[float] = Field(None, ge=0, le=130)
    sex: Optional[Literal["M", "F"]] = None
    unit_admitted: Optional[str] = None
    current_status: Optional[PatientStatus] = None


class PatientOut(BaseModel):
    id: str
    patient_id: str
    source_dataset: str
    age: Optional[float] = None
    sex: Optional[str] = None
    unit_admitted: Optional[str] = None
    admission_time: Optional[datetime] = None
    current_status: str
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
