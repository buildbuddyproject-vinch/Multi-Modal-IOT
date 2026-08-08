import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from src.api.dependencies import get_current_user, get_patient_repo
from src.api.ownership import get_owned_patient
from src.api.schemas.common import PatientStatus, mongo_doc_to_dict
from src.api.schemas.patient import PatientCreate, PatientOut, PatientUpdate
from src.database.mongodb.repositories import PatientRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    repo: PatientRepository = Depends(get_patient_repo),
    user: dict = Depends(get_current_user),
) -> PatientOut:
    """`created_by` is derived from the caller's JWT, never accepted from the
    client -- every patient belongs to exactly the account that admitted them
    (this is the whole basis of the per-account privacy model), so it can't
    be spoofed the same way predicted_label/risk_level can't be (see
    src/api/schemas/prediction.py)."""
    if repo.get_by_patient_id(payload.patient_id) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"patient_id '{payload.patient_id}' already exists")
    fields = payload.model_dump(exclude={"patient_id", "source_dataset"})
    try:
        repo.create(payload.patient_id, payload.source_dataset, created_by=user["username"], **fields)
    except DuplicateKeyError:
        raise HTTPException(status.HTTP_409_CONFLICT, f"patient_id '{payload.patient_id}' already exists")
    logger.info("Created patient %s (owner=%s)", payload.patient_id, user["username"])
    return PatientOut(**mongo_doc_to_dict(repo.get_by_patient_id(payload.patient_id)))


@router.get("", response_model=list[PatientOut])
def list_patients(
    status_filter: Optional[PatientStatus] = None,
    limit: int = 100,
    repo: PatientRepository = Depends(get_patient_repo),
    user: dict = Depends(get_current_user),
) -> list[PatientOut]:
    docs = repo.list_patients(status=status_filter, created_by=user["username"], limit=limit)
    return [PatientOut(**mongo_doc_to_dict(doc)) for doc in docs]


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(
    patient_id: str,
    repo: PatientRepository = Depends(get_patient_repo),
    user: dict = Depends(get_current_user),
) -> PatientOut:
    return PatientOut(**mongo_doc_to_dict(get_owned_patient(patient_id, user, repo)))


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: str,
    payload: PatientUpdate,
    repo: PatientRepository = Depends(get_patient_repo),
    user: dict = Depends(get_current_user),
) -> PatientOut:
    get_owned_patient(patient_id, user, repo)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no fields to update")
    repo.update(patient_id, updates)
    logger.info("Updated patient %s: %s", patient_id, list(updates.keys()))
    return PatientOut(**mongo_doc_to_dict(repo.get_by_patient_id(patient_id)))


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: str,
    repo: PatientRepository = Depends(get_patient_repo),
    user: dict = Depends(get_current_user),
) -> None:
    get_owned_patient(patient_id, user, repo)
    repo.delete(patient_id)
    logger.info("Deleted patient %s", patient_id)
