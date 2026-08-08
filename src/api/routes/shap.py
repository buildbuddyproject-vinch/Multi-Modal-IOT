"""Exposes prediction_history (SHAP/LIME explanation) documents, produced by
src/models/explainability (Step 6), through the API for the dashboard's
explanation panel (Step 9)."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import get_current_user, get_patient_repo, get_prediction_history_repo
from src.api.ownership import get_owned_patient
from src.api.schemas.common import mongo_doc_to_dict
from src.api.schemas.shap import ShapExplanationCreate, ShapExplanationOut
from src.database.mongodb.repositories import PatientRepository, PredictionHistoryRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/shap", tags=["shap"])


@router.post("", response_model=ShapExplanationOut, status_code=status.HTTP_201_CREATED)
def create_explanation(
    payload: ShapExplanationCreate,
    repo: PredictionHistoryRepository = Depends(get_prediction_history_repo),
    patient_repo: PatientRepository = Depends(get_patient_repo),
    user: dict = Depends(get_current_user),
) -> ShapExplanationOut:
    get_owned_patient(payload.patient_id, user, patient_repo)
    top_features = [f.model_dump() for f in payload.top_contributing_features] if payload.top_contributing_features else None
    explanation_id = repo.create(
        payload.prediction_id, payload.patient_id, payload.shap_values,
        shap_plot_type=payload.shap_plot_type,
        top_contributing_features=top_features,
        explanation_method=payload.explanation_method,
    )
    doc = repo.get_by_prediction_id(payload.prediction_id)
    logger.info("Created SHAP explanation %s for prediction %s", explanation_id, payload.prediction_id)
    return ShapExplanationOut(**mongo_doc_to_dict(doc))


@router.get("/prediction/{prediction_id}", response_model=ShapExplanationOut)
def get_explanation_by_prediction(
    prediction_id: str,
    repo: PredictionHistoryRepository = Depends(get_prediction_history_repo),
    patient_repo: PatientRepository = Depends(get_patient_repo),
    user: dict = Depends(get_current_user),
) -> ShapExplanationOut:
    doc = repo.get_by_prediction_id(prediction_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no SHAP explanation found for prediction '{prediction_id}'")
    get_owned_patient(doc["patient_id"], user, patient_repo)
    return ShapExplanationOut(**mongo_doc_to_dict(doc))


@router.get("/patient/{patient_id}", response_model=list[ShapExplanationOut])
def get_explanations_by_patient(
    patient_id: str,
    limit: int = 50,
    repo: PredictionHistoryRepository = Depends(get_prediction_history_repo),
    patient_repo: PatientRepository = Depends(get_patient_repo),
    user: dict = Depends(get_current_user),
) -> list[ShapExplanationOut]:
    get_owned_patient(patient_id, user, patient_repo)
    docs = repo.get_by_patient(patient_id, limit=limit)
    return [ShapExplanationOut(**mongo_doc_to_dict(doc)) for doc in docs]
