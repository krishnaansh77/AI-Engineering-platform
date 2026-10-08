"""Authentication endpoints for Phase 4."""
import uuid
import hashlib
import secrets
import re
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse, WorkspaceResponse, WorkspaceCreate, WorkspaceUpdate, WorkspaceInvitationCreate, WorkspaceInvitationResponse, WorkspaceMemberResponse, WorkspaceMemberUpdate
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


async def require_repository_access(repo_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Require global admin access or membership in the repository's workspace."""
    from app.models.repository import Repository

    if user.role in {"owner", "admin"}:
        stmt = select(Repository).where(Repository.id == repo_id)
    else:
        access = or_(
            Repository.owner_id == user.id,
            Repository.workspace_id.in_(select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user.id)),
        )
        stmt = select(Repository).where(Repository.id == repo_id, access)
    if not await db.scalar(stmt):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {repo_id} not found")


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


def _workspace_slug(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-") or "workspace"
    return f"{base}-{secrets.token_hex(4)}"


@router.post("/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(payload: WorkspaceCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> WorkspaceResponse:
    workspace = Workspace(name=payload.name.strip(), slug=_workspace_slug(payload.name))
    db.add(workspace)
    await db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner"))
    await db.commit()
    return WorkspaceResponse(id=workspace.id, name=workspace.name, slug=workspace.slug, role="owner")


@router.patch("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(workspace_id: uuid.UUID, payload: WorkspaceUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> WorkspaceResponse:
    membership = await db.scalar(select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user.id))
    if not membership or membership.role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only workspace owners and admins can rename a workspace.")
    workspace = await db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    workspace.name = payload.name.strip()
    await db.commit()
    return WorkspaceResponse(id=workspace.id, name=workspace.name, slug=workspace.slug, role=membership.role)


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
    return WorkspaceInvitationResponse(id=invitation.id, workspace_id=workspace_id, email=email, role=invitation.role, expires_at=invitation.expires_at, invite_token=token, accepted_at=invitation.accepted_at)


async def _require_workspace_admin(workspace_id: uuid.UUID, user: User, db: AsyncSession) -> WorkspaceMember:
    membership = await db.scalar(select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user.id))
    if not membership or membership.role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only workspace owners and admins can manage workspace members.")
    return membership


@router.get("/workspaces/{workspace_id}/invitations", response_model=list[WorkspaceInvitationResponse])
async def list_invitations(workspace_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[WorkspaceInvitationResponse]:
    await _require_workspace_admin(workspace_id, user, db)
    rows = await db.scalars(select(WorkspaceInvitation).where(WorkspaceInvitation.workspace_id == workspace_id, WorkspaceInvitation.accepted_at.is_(None)).order_by(WorkspaceInvitation.created_at.desc()))
    return [WorkspaceInvitationResponse(id=item.id, workspace_id=item.workspace_id, email=item.email, role=item.role, expires_at=item.expires_at, accepted_at=item.accepted_at) for item in rows.all()]


@router.delete("/workspaces/{workspace_id}/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(workspace_id: uuid.UUID, invitation_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> None:
    await _require_workspace_admin(workspace_id, user, db)
    invitation = await db.scalar(select(WorkspaceInvitation).where(WorkspaceInvitation.id == invitation_id, WorkspaceInvitation.workspace_id == workspace_id, WorkspaceInvitation.accepted_at.is_(None)))
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending invitation not found.")
    await db.delete(invitation)
    await db.commit()


@router.get("/workspaces/{workspace_id}/members", response_model=list[WorkspaceMemberResponse])
async def list_members(workspace_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[WorkspaceMemberResponse]:
    await _require_workspace_admin(workspace_id, user, db)
    rows = await db.execute(select(WorkspaceMember, User.email).join(User, User.id == WorkspaceMember.user_id).where(WorkspaceMember.workspace_id == workspace_id).order_by(WorkspaceMember.created_at))
    return [WorkspaceMemberResponse(user_id=membership.user_id, email=email, role=membership.role, created_at=membership.created_at) for membership, email in rows.all()]


@router.patch("/workspaces/{workspace_id}/members/{member_id}", response_model=WorkspaceMemberResponse)
async def update_member(workspace_id: uuid.UUID, member_id: uuid.UUID, payload: WorkspaceMemberUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> WorkspaceMemberResponse:
    actor = await _require_workspace_admin(workspace_id, user, db)
    membership = await db.scalar(select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == member_id))
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace member not found.")
    if membership.role == "owner" or (actor.role == "admin" and membership.role == "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the workspace owner can change this member.")
    membership.role = payload.role
    await db.commit()
    member = await db.get(User, member_id)
    return WorkspaceMemberResponse(user_id=membership.user_id, email=member.email, role=membership.role, created_at=membership.created_at)


@router.delete("/workspaces/{workspace_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(workspace_id: uuid.UUID, member_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> None:
    actor = await _require_workspace_admin(workspace_id, user, db)
    if member_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot remove yourself from a workspace.")
    membership = await db.scalar(select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == member_id))
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace member not found.")
    if membership.role == "owner" or (actor.role == "admin" and membership.role == "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the workspace owner can remove this member.")
    await db.delete(membership)
    await db.commit()


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
