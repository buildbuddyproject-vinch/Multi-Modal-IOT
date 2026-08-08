"""FastAPI application entry point.

Run with: uvicorn src.api.main:app --reload
Swagger UI: http://localhost:8000/docs
"""
import logging

from bson.errors import InvalidId
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import alerts, audit, auth, health, patients, predictions, reports, shap, vitals
from src.config.settings import get_settings
from src.utils.logging_config import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sepsis ICU Prediction API",
    description="Backend for the Multi-Modal IoT and Deep Learning Framework for "
                "Early Prediction of Sepsis in Smart ICU Environments.",
    version="0.1.0",
)

# Dashboard (Step 9, Plotly Dash) runs on a different port -- allow it in dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(vitals.router)
app.include_router(predictions.router)
app.include_router(alerts.router)
app.include_router(shap.router)
app.include_router(audit.router)
app.include_router(reports.router)


@app.exception_handler(InvalidId)
def handle_invalid_object_id(request: Request, exc: InvalidId) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": f"invalid id format: {exc}"})


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"message": "Sepsis ICU Prediction API", "docs": "/docs"}
