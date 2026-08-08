from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

from src.api.schemas.common import ExplanationMethod


class TopContributingFeature(BaseModel):
    feature: str
    value: float
    contribution: float


class ShapExplanationCreate(BaseModel):
    prediction_id: str
    patient_id: str
    shap_values: dict[str, float]
    shap_plot_type: Optional[Literal["summary", "waterfall", "force"]] = None
    top_contributing_features: Optional[list[TopContributingFeature]] = None
    explanation_method: ExplanationMethod = "shap"


class ShapExplanationOut(BaseModel):
    id: str
    prediction_id: str
    patient_id: str
    shap_values: dict[str, float]
    shap_plot_type: Optional[str] = None
    top_contributing_features: list[dict] = []
    explanation_method: str
    created_at: Optional[datetime] = None
