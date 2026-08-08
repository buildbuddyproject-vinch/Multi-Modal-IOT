import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.alerts.alert_engine import AlertEngine
from src.api.dependencies import get_alert_engine, get_audit_repo, get_current_user, get_patient_repo, get_prediction_repo
from src.api.ownership import get_owned_patient
from src.api.schemas.common import mongo_doc_to_dict
from src.api.schemas.prediction import PredictionCreate, PredictionOut
from src.database.mongodb.repositories import AuditLogRepository, PatientRepository, PredictionRepository
from src.models.inference.risk import predicted_label as compute_predicted_label
from src.models.inference.risk import probability_to_risk_level

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.post("", response_model=PredictionOut, status_code=status.HTTP_201_CREATED)
def create_prediction(
    payload: PredictionCreate,
    repo: PredictionRepository = Depends(get_prediction_repo),
    patient_repo: PatientRepository = Depends(get_patient_repo),
    audit_repo: AuditLogRepository = Depends(get_audit_repo),
    alert_engine: AlertEngine = Depends(get_alert_engine),
    user: dict = Depends(get_current_user),
) -> PredictionOut:
    get_owned_patient(payload.patient_id, user, patient_repo)
    fields = payload.model_dump(exclude={"patient_id"})
    risk_level = probability_to_risk_level(payload.sepsis_probability)
    prediction_id = repo.create(
        payload.patient_id, predicted_label=compute_predicted_label(payload.sepsis_probability), risk_level=risk_level, **fields
    )
    logger.info("Created prediction %s for patient %s (risk=%s)", prediction_id, payload.patient_id, risk_level)
    audit_repo.log(actor="system", action="prediction_run", target_type="prediction", target_id=prediction_id,
                    details={"patient_id": payload.patient_id, "risk_level": risk_level})

    prediction = mongo_doc_to_dict(repo.get_by_id(prediction_id))
    alert_engine.evaluate_and_dispatch(payload.patient_id, prediction)
    return PredictionOut(**prediction)


@router.get("/{patient_id}/latest", response_model=PredictionOut)
def get_latest_prediction(
    patient_id: str,
    repo: PredictionRepository = Depends(get_prediction_repo),
    patient_repo: PatientRepository = Depends(get_patient_repo),
    user: dict = Depends(get_current_user),
) -> PredictionOut:
    get_owned_patient(patient_id, user, patient_repo)
    doc = repo.get_latest(patient_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no predictions found for patient '{patient_id}'")
    return PredictionOut(**mongo_doc_to_dict(doc))


@router.get("/{patient_id}/history", response_model=list[PredictionOut])
def get_prediction_history(
    patient_id: str,
    limit: int = 100,
    repo: PredictionRepository = Depends(get_prediction_repo),
    patient_repo: PatientRepository = Depends(get_patient_repo),
    user: dict = Depends(get_current_user),
) -> list[PredictionOut]:
    get_owned_patient(patient_id, user, patient_repo)
    docs = repo.get_history(patient_id, limit=limit)
    return [PredictionOut(**mongo_doc_to_dict(doc)) for doc in docs]
