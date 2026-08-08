"""Password hashing (passlib/bcrypt) and JWT issuing/verification (python-jose)
for dashboard login (Step 9). Signed with settings.api_secret_key -- set a real
secret via .env before deploying anywhere outside a dev machine."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.config.settings import get_settings

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 8  # one clinical shift

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(password, hashed_password)


def create_access_token(username: str, role: str, expires_minutes: int = JWT_EXPIRE_MINUTES) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, get_settings().api_secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, get_settings().api_secret_key, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
