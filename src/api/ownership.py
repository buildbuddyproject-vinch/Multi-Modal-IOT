"""Shared ownership-check helper. Every patient -- and everything scoped
under one (vitals, predictions, alerts, SHAP explanations, PDF reports) --
belongs to exactly the account that created it (src/api/routes/patients.py).
A 404 (not 403) is raised for a patient that exists but isn't owned by the
caller, so one account can't even confirm another account's patient_id
exists."""
from fastapi import HTTPException, status

from src.database.mongodb.repositories import PatientRepository


def get_owned_patient(patient_id: str, user: dict, patient_repo: PatientRepository) -> dict:
    doc = patient_repo.get_by_patient_id(patient_id)
    if doc is None or doc.get("created_by") != user["username"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"patient '{patient_id}' not found")
    return doc
