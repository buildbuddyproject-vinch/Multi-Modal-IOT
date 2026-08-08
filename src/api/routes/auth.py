"""Dashboard login (Step 9). The very first admin account is created out-of-band
by scripts/create_admin_user.py (there is no open self-registration endpoint --
new accounts are provisioned by an admin via POST /auth/register)."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import get_audit_repo, get_current_admin, get_current_user, get_user_repo
from src.api.schemas.common import mongo_doc_to_dict
from src.api.schemas.user import LoginRequest, TokenResponse, UserCreate, UserOut
from src.api.security import create_access_token, hash_password, verify_password
from src.database.mongodb.repositories import AuditLogRepository, UserRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    repo: UserRepository = Depends(get_user_repo),
    audit_repo: AuditLogRepository = Depends(get_audit_repo),
) -> TokenResponse:
    user = repo.get_by_username(payload.username)
    if user is None or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid username or password")
    repo.touch_last_login(payload.username)
    token = create_access_token(user["username"], user["role"])
    logger.info("User %s logged in", payload.username)
    audit_repo.log(actor=payload.username, action="login", target_type="user", target_id=payload.username)
    return TokenResponse(access_token=token, username=user["username"], role=user["role"])


@router.get("/me", response_model=UserOut)
def me(user: dict = Depends(get_current_user)) -> UserOut:
    return UserOut(**mongo_doc_to_dict(user))


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserCreate,
    repo: UserRepository = Depends(get_user_repo),
    _admin: dict = Depends(get_current_admin),
) -> UserOut:
    if repo.get_by_username(payload.username) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"username '{payload.username}' already exists")
    repo.create(payload.username, hash_password(payload.password), payload.role)
    logger.info("Admin %s registered new user %s (role=%s)", _admin["username"], payload.username, payload.role)
    return UserOut(**mongo_doc_to_dict(repo.get_by_username(payload.username)))


@router.get("/users", response_model=list[UserOut])
def list_users(repo: UserRepository = Depends(get_user_repo), _admin: dict = Depends(get_current_admin)) -> list[UserOut]:
    return [UserOut(**mongo_doc_to_dict(doc)) for doc in repo.list_users()]
