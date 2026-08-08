"""Read-only audit trail (Step 10) -- admin-only, per docs/architecture/database_design.md
("audit_logs ... Admin API")."""
from typing import Optional

from fastapi import APIRouter, Depends

from src.api.dependencies import get_audit_repo, get_current_admin, get_patient_repo
from src.api.schemas.audit_log import AuditLogOut
from src.api.schemas.common import mongo_doc_to_dict
from src.database.mongodb.repositories import AuditLogRepository, PatientRepository

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
def list_audit_logs(
    action: Optional[str] = None,
    limit: int = 100,
    repo: AuditLogRepository = Depends(get_audit_repo),
    patient_repo: PatientRepository = Depends(get_patient_repo),
    admin: dict = Depends(get_current_admin),
) -> list[AuditLogOut]:
    owned_patient_ids = [p["patient_id"] for p in patient_repo.list_patients(created_by=admin["username"], limit=10_000)]
    docs = repo.list_logs(action=action, limit=limit, actor=admin["username"], patient_ids=owned_patient_ids)
    return [AuditLogOut(**mongo_doc_to_dict(doc)) for doc in docs]
