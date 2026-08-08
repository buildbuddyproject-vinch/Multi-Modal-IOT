import logging

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from src.api.dependencies import (
    get_alert_repo,
    get_current_user,
    get_patient_repo,
    get_prediction_history_repo,
    get_prediction_repo,
    get_vitals_repo,
)
from src.api.ownership import get_owned_patient
from src.api.schemas.common import mongo_doc_to_dict
from src.database.mongodb.repositories import (
    AlertRepository,
    PatientRepository,
    PredictionHistoryRepository,
    PredictionRepository,
    VitalsRepository,
)
from src.reports.patient_report_pdf import build_patient_report_pdf

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/patients", tags=["reports"])


@router.get("/{patient_id}/report")
def get_patient_report(
    patient_id: str,
    patient_repo: PatientRepository = Depends(get_patient_repo),
    vitals_repo: VitalsRepository = Depends(get_vitals_repo),
    prediction_repo: PredictionRepository = Depends(get_prediction_repo),
    shap_repo: PredictionHistoryRepository = Depends(get_prediction_history_repo),
    alert_repo: AlertRepository = Depends(get_alert_repo),
    user: dict = Depends(get_current_user),
) -> Response:
    """Renders the same vitals/prediction/SHAP/alert history the Patient
    Detail dashboard page (Step 9) shows, as a print-ready PDF (Step 12+) --
    a pure read of already-authoritative data, so it carries no risk of
    diverging from what a clinician sees on screen."""
    patient_doc = get_owned_patient(patient_id, user, patient_repo)

    vitals_docs = vitals_repo.get_history(patient_id, limit=200)
    prediction_docs = prediction_repo.get_history(patient_id, limit=200)
    alert_docs = alert_repo.list_alerts(patient_id=patient_id, limit=100)

    shap_doc = None
    latest_prediction = prediction_repo.get_latest(patient_id)
    if latest_prediction is not None:
        shap_doc = shap_repo.get_by_prediction_id(str(latest_prediction["_id"]))

    pdf_bytes = build_patient_report_pdf(
        patient=mongo_doc_to_dict(patient_doc),
        vitals_history=[mongo_doc_to_dict(d) for d in vitals_docs],
        prediction_history=[mongo_doc_to_dict(d) for d in prediction_docs],
        shap_explanation=mongo_doc_to_dict(shap_doc) if shap_doc else None,
        alerts=[mongo_doc_to_dict(d) for d in alert_docs],
    )
    logger.info("Generated PDF report for patient %s (%d bytes)", patient_id, len(pdf_bytes))

    filename = f"{patient_id}_sepsis_report.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
