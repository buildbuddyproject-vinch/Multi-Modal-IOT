import logging
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import get_alert_repo, get_audit_repo, get_current_user, get_patient_repo
from src.api.ownership import get_owned_patient
from src.api.schemas.alert import AlertAcknowledge, AlertCreate, AlertOut
from src.api.schemas.common import RiskLevel, mongo_doc_to_dict
from src.database.mongodb.repositories import AlertRepository, AuditLogRepository, PatientRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
def create_alert(
    payload: AlertCreate,
    repo: AlertRepository = Depends(get_alert_repo),
    audit_repo: AuditLogRepository = Depends(get_audit_repo),
    patient_repo: PatientRepository = Depends(get_patient_repo),
    user: dict = Depends(get_current_user),
) -> AlertOut:
    """Manual alert creation (e.g. a clinician-raised concern that isn't tied to
    a model prediction) -- the automatic path is POST /predictions, which runs
    every prediction through the Step 10 alert engine."""
    get_owned_patient(payload.patient_id, user, patient_repo)
    fields = payload.model_dump(exclude={"patient_id", "risk_level", "message"})
    alert_id = repo.create(payload.patient_id, payload.risk_level, payload.message, **fields)
    logger.warning("Alert created for patient %s: risk=%s message=%r", payload.patient_id, payload.risk_level, payload.message)
    audit_repo.log(actor="system", action="alert_dispatched", target_type="alert", target_id=alert_id,
                    details={"patient_id": payload.patient_id, "risk_level": payload.risk_level, "source": "manual"})
    doc = repo.collection.find_one({"_id": ObjectId(alert_id)})
    return AlertOut(**mongo_doc_to_dict(doc))


@router.get("", response_model=list[AlertOut])
def list_alerts(
    patient_id: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    risk_level: Optional[RiskLevel] = None,
    limit: int = 100,
    repo: AlertRepository = Depends(get_alert_repo),
    patient_repo: PatientRepository = Depends(get_patient_repo),
    user: dict = Depends(get_current_user),
) -> list[AlertOut]:
    if patient_id is not None:
        get_owned_patient(patient_id, user, patient_repo)
        owned_patient_ids = None
    else:
        owned_patient_ids = [p["patient_id"] for p in patient_repo.list_patients(created_by=user["username"], limit=10_000)]
    docs = repo.list_alerts(patient_id=patient_id, patient_ids=owned_patient_ids, acknowledged=acknowledged, risk_level=risk_level, limit=limit)
    return [AlertOut(**mongo_doc_to_dict(doc)) for doc in docs]


@router.patch("/{alert_id}/acknowledge", response_model=dict)
def acknowledge_alert(
    alert_id: str,
    payload: AlertAcknowledge,
    repo: AlertRepository = Depends(get_alert_repo),
    audit_repo: AuditLogRepository = Depends(get_audit_repo),
    patient_repo: PatientRepository = Depends(get_patient_repo),
    user: dict = Depends(get_current_user),
) -> dict:
    alert_doc = repo.collection.find_one({"_id": ObjectId(alert_id)})
    if alert_doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"alert '{alert_id}' not found")
    get_owned_patient(alert_doc["patient_id"], user, patient_repo)

    acknowledged = repo.acknowledge(alert_id, payload.acknowledged_by)
    if not acknowledged:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"alert '{alert_id}' not found")
    logger.info("Alert %s acknowledged by %s", alert_id, payload.acknowledged_by)
    audit_repo.log(actor=payload.acknowledged_by, action="alert_acknowledged", target_type="alert", target_id=alert_id,
                    details={"patient_id": alert_doc["patient_id"]})
    return {"acknowledged": True}
