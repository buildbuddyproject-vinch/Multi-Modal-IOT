from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: str
    actor: str
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    details: dict = {}
    timestamp: Optional[datetime] = None
