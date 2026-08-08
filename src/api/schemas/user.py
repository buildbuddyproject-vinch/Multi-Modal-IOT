from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

UserRole = Literal["admin", "clinician"]


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8)
    role: UserRole = "clinician"


class UserOut(BaseModel):
    id: str
    username: str
    role: str
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str
