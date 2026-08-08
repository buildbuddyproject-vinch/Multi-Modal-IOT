"""Vitals ingestion + historical retrieval -- this is the "History" API group:
the dashboard's time-series charts (Step 9) read from GET /vitals/{patient_id}/history."""
import logging
from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import get_current_user, get_patient_repo, get_vitals_repo
from src.api.ownership import get_owned_patient
from src.api.schemas.common import mongo_doc_to_dict
from src.api.schemas.vitals import VitalsIn, VitalsOut
from src.database.mongodb.repositories import PatientRepository, VitalsRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/vitals", tags=["vitals"])


@router.post("", response_model=VitalsOut, status_code=status.HTTP_201_CREATED)
def ingest_vitals(
    payload: VitalsIn,
    repo: VitalsRepository = Depends(get_vitals_repo),
    patient_repo: PatientRepository = Depends(get_patient_repo),
    user: dict = Depends(get_current_user),
) -> VitalsOut:
    get_owned_patient(payload.patient_id, user, patient_repo)
    channels = payload.channels.model_dump()
    vitals_id = repo.insert_vitals(payload.patient_id, payload.timestamp, payload.source, channels, payload.ingest_seq)
    doc = repo.collection.find_one({"_id": ObjectId(vitals_id)})
    return VitalsOut(**mongo_doc_to_dict(doc))


@router.get("/{patient_id}/latest", response_model=VitalsOut)
def get_latest_vitals(
    patient_id: str,
    repo: VitalsRepository = Depends(get_vitals_repo),
    patient_repo: PatientRepository = Depends(get_patient_repo),
    user: dict = Depends(get_current_user),
) -> VitalsOut:
    get_owned_patient(patient_id, user, patient_repo)
    doc = repo.get_latest(patient_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no vitals found for patient '{patient_id}'")
    return VitalsOut(**mongo_doc_to_dict(doc))


@router.get("/{patient_id}/history", response_model=list[VitalsOut])
def get_vitals_history(
    patient_id: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 1000,
    repo: VitalsRepository = Depends(get_vitals_repo),
    patient_repo: PatientRepository = Depends(get_patient_repo),
    user: dict = Depends(get_current_user),
) -> list[VitalsOut]:
    get_owned_patient(patient_id, user, patient_repo)
    docs = repo.get_history(patient_id, start=start, end=end, limit=limit)
    return [VitalsOut(**mongo_doc_to_dict(doc)) for doc in docs]
