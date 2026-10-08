"""Authentication endpoints for Phase 4."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.database import get_db
from app.models.user import User
from app.services.auth_service import create_access_token, decode_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["authentication"])
bearer = HTTPBearer(auto_error=False)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    email = payload.email.strip().lower()
    existing = await db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with that email already exists.")
    user = User(email=email, password_hash=hash_password(payload.password), role="member")
    db.add(user)
    await db.flush()
    return AuthResponse(access_token=create_access_token(user.id, user.role), user=UserResponse.model_validate(user))


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    email = payload.email.strip().lower()
    user = await db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    return AuthResponse(access_token=create_access_token(user.id, user.role), user=UserResponse.model_validate(user))


async def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: AsyncSession = Depends(get_db)) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    try:
        claims = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(str(claims["sub"]))
    except (ValueError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token.")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account not found.")
    return user


def require_roles(*allowed_roles: str):
    """Build a dependency that permits only the supplied RBAC roles."""
    async def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your account does not have permission for this action.")
        return user
    return dependency


def assert_repository_owner(user: User, owner_id: uuid.UUID | None) -> None:
    """Allow admins/owners globally; members may mutate their own repositories."""
    if owner_id is not None and user.role not in {"owner", "admin"} and owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to modify this repository.")


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user)
