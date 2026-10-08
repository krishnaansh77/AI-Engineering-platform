"""Authentication endpoints for Phase 4."""
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse, WorkspaceResponse, WorkspaceInvitationCreate, WorkspaceInvitationResponse
from app.database import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.models.workspace_invitation import WorkspaceInvitation
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
    workspace = Workspace(name=f"{email}'s workspace", slug=f"workspace-{user.id.hex[:12]}")
    db.add(workspace)
    await db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner"))
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


@router.get("/workspaces", response_model=list[WorkspaceResponse])
async def workspaces(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[WorkspaceResponse]:
    rows = await db.execute(
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(Workspace.created_at)
    )
    return [WorkspaceResponse(id=workspace.id, name=workspace.name, slug=workspace.slug, role=role) for workspace, role in rows.all()]


@router.post("/workspaces/{workspace_id}/invitations", response_model=WorkspaceInvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(workspace_id: uuid.UUID, payload: WorkspaceInvitationCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> WorkspaceInvitationResponse:
    membership = await db.scalar(select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user.id))
    if not membership or membership.role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only workspace owners and admins can invite members.")
    email = payload.email.strip().lower()
    token = secrets.token_urlsafe(32)
    invitation = WorkspaceInvitation(workspace_id=workspace_id, invited_by=user.id, email=email, role=payload.role, token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=datetime.now(timezone.utc) + timedelta(days=7))
    db.add(invitation)
    await db.flush()
    return WorkspaceInvitationResponse(id=invitation.id, workspace_id=workspace_id, email=email, role=invitation.role, expires_at=invitation.expires_at, invite_token=token)


@router.post("/invitations/accept", response_model=WorkspaceResponse)
async def accept_invitation(token: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> WorkspaceResponse:
    token_hash = hashlib.sha256(token.strip().encode()).hexdigest()
    invitation = await db.scalar(select(WorkspaceInvitation).where(WorkspaceInvitation.token_hash == token_hash))
    now = datetime.now(timezone.utc)
    if not invitation or invitation.accepted_at is not None or invitation.expires_at <= now or invitation.email != user.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation is invalid, expired, already accepted, or addressed to another email.")
    existing = await db.scalar(select(WorkspaceMember).where(WorkspaceMember.workspace_id == invitation.workspace_id, WorkspaceMember.user_id == user.id))
    if not existing:
        db.add(WorkspaceMember(workspace_id=invitation.workspace_id, user_id=user.id, role=invitation.role))
    invitation.accepted_at = now
    workspace = await db.get(Workspace, invitation.workspace_id)
    return WorkspaceResponse(id=workspace.id, name=workspace.name, slug=workspace.slug, role=invitation.role)
