from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx
import git
from django.conf import settings
from django.db.models import Q
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from jose import JWTError, jwt
from celery import Celery

from .models import Repository, SourceFile, User, Workspace, WorkspaceInvitation, WorkspaceMember
from .graph import (
    build_architecture,
    build_debt,
    build_documentation_quality,
    build_file_graph,
    build_test_summary,
    build_tour,
)
from .git_intelligence import analyze_commit, compare_commits, history


logger = logging.getLogger(__name__)
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}
PASSWORD_ITERATIONS = 210_000


def _json_body(request: HttpRequest) -> dict:
    try:
        payload = json.loads(request.body or b"{}")
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return (
        f"pbkdf2_sha256${PASSWORD_ITERATIONS}$"
        f"{base64.urlsafe_b64encode(salt).decode()}$"
        f"{base64.urlsafe_b64encode(digest).decode()}"
    )


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode())
        expected = base64.urlsafe_b64decode(digest_text.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError):
        return False


def _access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def _user_payload(user: User) -> dict:
    return {"id": str(user.id), "email": user.email, "role": user.role}


def _auth_response(user: User) -> JsonResponse:
    return JsonResponse(
        {"access_token": _access_token(user), "token_type": "bearer", "user": _user_payload(user)}
    )


@csrf_exempt
def register(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    payload = _json_body(request)
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    if len(email) < 3 or len(email) > 320 or "@" not in email:
        return JsonResponse({"detail": "Enter a valid email address."}, status=422)
    if len(password) < 8 or len(password) > 200:
        return JsonResponse({"detail": "Password must be at least 8 characters."}, status=422)
    if User.objects.filter(email=email).exists():
        return JsonResponse({"detail": "An account with that email already exists."}, status=409)
    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    with transaction.atomic():
        user = User.objects.create(
            id=user_id,
            email=email,
            password_hash=_hash_password(password),
            role="member",
        )
        workspace = Workspace.objects.create(
            id=workspace_id,
            name=f"{email}'s workspace",
            slug=f"workspace-{user_id.hex[:12]}",
        )
        WorkspaceMember.objects.create(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            user_id=user.id,
            role="owner",
        )
    return _auth_response(user)


@csrf_exempt
def login(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    payload = _json_body(request)
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    user = User.objects.filter(email=email).first()
    if not user or not _verify_password(password, user.password_hash):
        return JsonResponse({"detail": "Invalid email or password."}, status=401)
    return _auth_response(user)


def me(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    user = _current_user(request)
    if not user:
        return JsonResponse({"detail": "Authentication required."}, status=401)
    return JsonResponse(_user_payload(user))


def workspaces(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        return create_workspace(request)
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    user = _current_user(request)
    if not user:
        return JsonResponse({"detail": "Authentication required."}, status=401)
    memberships = list(
        WorkspaceMember.objects.filter(user_id=user.id).values("workspace_id", "role")
    )
    workspace_ids = [membership["workspace_id"] for membership in memberships]
    workspaces_by_id = {
        workspace.id: workspace
        for workspace in Workspace.objects.filter(id__in=workspace_ids)
    }
    payload = [
        {
            "id": str(workspace.id),
            "name": workspace.name,
            "slug": workspace.slug,
            "role": membership["role"],
        }
        for membership in memberships
        if (workspace := workspaces_by_id.get(membership["workspace_id"])) is not None
    ]
    return JsonResponse(payload, safe=False)


@csrf_exempt
def create_workspace(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    user = _current_user(request)
    if not user:
        return JsonResponse({"detail": "Authentication required."}, status=401)
    name = str(_json_body(request).get("name", "")).strip()
    if len(name) < 2 or len(name) > 255:
        return JsonResponse({"detail": "Workspace name must be between 2 and 255 characters."}, status=422)
    slug_base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "workspace"
    workspace = Workspace.objects.create(
        id=uuid.uuid4(),
        name=name,
        slug=f"{slug_base}-{secrets.token_hex(4)}",
    )
    WorkspaceMember.objects.create(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        user_id=user.id,
        role="owner",
    )
    return JsonResponse(
        {
            "id": str(workspace.id),
            "name": workspace.name,
            "slug": workspace.slug,
            "role": "owner",
        },
        status=201,
    )


@csrf_exempt
def update_workspace(request: HttpRequest, workspace_id: uuid.UUID) -> JsonResponse:
    if request.method != "PATCH":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    user = _current_user(request)
    if not user:
        return JsonResponse({"detail": "Authentication required."}, status=401)
    membership = WorkspaceMember.objects.filter(
        workspace_id=workspace_id,
        user_id=user.id,
    ).first()
    if not membership or membership.role not in {"owner", "admin"}:
        return JsonResponse(
            {"detail": "Only workspace owners and admins can rename a workspace."},
            status=403,
        )
    workspace = Workspace.objects.filter(id=workspace_id).first()
    if not workspace:
        return JsonResponse({"detail": "Workspace not found."}, status=404)
    name = str(_json_body(request).get("name", "")).strip()
    if len(name) < 2 or len(name) > 255:
        return JsonResponse({"detail": "Workspace name must be between 2 and 255 characters."}, status=422)
    workspace.name = name
    workspace.save(update_fields=["name"])
    return JsonResponse(
        {
            "id": str(workspace.id),
            "name": workspace.name,
            "slug": workspace.slug,
            "role": membership.role,
        }
    )


def _workspace_admin(request: HttpRequest, workspace_id: uuid.UUID):
    user = _current_user(request)
    if not user:
        return None, JsonResponse({"detail": "Authentication required."}, status=401)
    membership = WorkspaceMember.objects.filter(
        workspace_id=workspace_id,
        user_id=user.id,
    ).first()
    if not membership or membership.role not in {"owner", "admin"}:
        return None, JsonResponse(
            {"detail": "Only workspace owners and admins can manage workspace members."},
            status=403,
        )
    return (user, membership), None


def _invitation_payload(invitation: WorkspaceInvitation, include_token: bool = False) -> dict:
    payload = {
        "id": str(invitation.id),
        "workspace_id": str(invitation.workspace_id),
        "email": invitation.email,
        "role": invitation.role,
        "expires_at": invitation.expires_at.isoformat(),
        "accepted_at": invitation.accepted_at.isoformat() if invitation.accepted_at else None,
    }
    if include_token:
        payload["invite_token"] = getattr(invitation, "invite_token", None)
    return payload


@csrf_exempt
def create_invitation(request: HttpRequest, workspace_id: uuid.UUID) -> JsonResponse:
    if request.method == "GET":
        return list_invitations(request, workspace_id)
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    actor_context, error = _workspace_admin(request, workspace_id)
    if error:
        return error
    user, _membership = actor_context
    payload = _json_body(request)
    email = str(payload.get("email", "")).strip().lower()
    role = str(payload.get("role", "member"))
    if len(email) < 3 or "@" not in email:
        return JsonResponse({"detail": "Enter a valid invitation email."}, status=422)
    if role not in {"member", "admin"}:
        return JsonResponse({"detail": "Invitation role must be member or admin."}, status=422)
    raw_token = secrets.token_urlsafe(32)
    invitation = WorkspaceInvitation.objects.create(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        invited_by=user.id,
        email=email,
        role=role,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    invitation.invite_token = raw_token
    return JsonResponse(_invitation_payload(invitation, include_token=True), status=201)


def list_invitations(request: HttpRequest, workspace_id: uuid.UUID) -> JsonResponse:
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    _actor_context, error = _workspace_admin(request, workspace_id)
    if error:
        return error
    invitations = WorkspaceInvitation.objects.filter(
        workspace_id=workspace_id,
        accepted_at__isnull=True,
    ).order_by("-created_at")
    return JsonResponse([_invitation_payload(item) for item in invitations], safe=False)


@csrf_exempt
def revoke_invitation(request: HttpRequest, workspace_id: uuid.UUID, invitation_id: uuid.UUID) -> HttpResponse:
    if request.method != "DELETE":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    _actor_context, error = _workspace_admin(request, workspace_id)
    if error:
        return error
    invitation = WorkspaceInvitation.objects.filter(
        id=invitation_id,
        workspace_id=workspace_id,
        accepted_at__isnull=True,
    ).first()
    if not invitation:
        return JsonResponse({"detail": "Pending invitation not found."}, status=404)
    invitation.delete()
    return HttpResponse(status=204)


def _member_payload(membership: WorkspaceMember, user: User) -> dict:
    return {
        "user_id": str(membership.user_id),
        "email": user.email,
        "role": membership.role,
        "created_at": membership.created_at.isoformat() if membership.created_at else None,
    }


def list_members(request: HttpRequest, workspace_id: uuid.UUID) -> JsonResponse:
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    _actor_context, error = _workspace_admin(request, workspace_id)
    if error:
        return error
    memberships = WorkspaceMember.objects.filter(workspace_id=workspace_id).order_by("created_at")
    users = {
        user.id: user
        for user in User.objects.filter(id__in=[item.user_id for item in memberships])
    }
    return JsonResponse(
        [_member_payload(item, users[item.user_id]) for item in memberships if item.user_id in users],
        safe=False,
    )


@csrf_exempt
def update_member(request: HttpRequest, workspace_id: uuid.UUID, member_id: uuid.UUID) -> HttpResponse:
    if request.method == "DELETE":
        return remove_member(request, workspace_id, member_id)
    if request.method != "PATCH":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    actor_context, error = _workspace_admin(request, workspace_id)
    if error:
        return error
    _user, actor_membership = actor_context
    membership = WorkspaceMember.objects.filter(
        workspace_id=workspace_id,
        user_id=member_id,
    ).first()
    if not membership:
        return JsonResponse({"detail": "Workspace member not found."}, status=404)
    if membership.role == "owner" or (actor_membership.role == "admin" and membership.role == "admin"):
        return JsonResponse({"detail": "Only the workspace owner can change this member."}, status=403)
    role = str(_json_body(request).get("role", ""))
    if role not in {"member", "admin"}:
        return JsonResponse({"detail": "Member role must be member or admin."}, status=422)
    membership.role = role
    membership.save(update_fields=["role"])
    user = User.objects.filter(id=member_id).first()
    if not user:
        return JsonResponse({"detail": "User account not found."}, status=404)
    return JsonResponse(_member_payload(membership, user))


@csrf_exempt
def remove_member(request: HttpRequest, workspace_id: uuid.UUID, member_id: uuid.UUID) -> HttpResponse:
    if request.method != "DELETE":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    actor_context, error = _workspace_admin(request, workspace_id)
    if error:
        return error
    user, actor_membership = actor_context
    if member_id == user.id:
        return JsonResponse({"detail": "You cannot remove yourself from a workspace."}, status=400)
    membership = WorkspaceMember.objects.filter(
        workspace_id=workspace_id,
        user_id=member_id,
    ).first()
    if not membership:
        return JsonResponse({"detail": "Workspace member not found."}, status=404)
    if membership.role == "owner" or (actor_membership.role == "admin" and membership.role == "admin"):
        return JsonResponse({"detail": "Only the workspace owner can remove this member."}, status=403)
    membership.delete()
    return HttpResponse(status=204)


def accept_invitation(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    user = _current_user(request)
    if not user:
        return JsonResponse({"detail": "Authentication required."}, status=401)
    payload = _json_body(request)
    raw_token = str(payload.get("token") or request.GET.get("token") or "").strip()
    now = datetime.now(timezone.utc)
    invitation = WorkspaceInvitation.objects.filter(
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest()
    ).first()
    if (
        not invitation
        or invitation.accepted_at is not None
        or invitation.expires_at <= now
        or invitation.email != user.email
    ):
        return JsonResponse(
            {"detail": "Invitation is invalid, expired, already accepted, or addressed to another email."},
            status=400,
        )
    existing = WorkspaceMember.objects.filter(
        workspace_id=invitation.workspace_id,
        user_id=user.id,
    ).first()
    if not existing:
        WorkspaceMember.objects.create(
            id=uuid.uuid4(),
            workspace_id=invitation.workspace_id,
            user_id=user.id,
            role=invitation.role,
        )
    invitation.accepted_at = now
    invitation.save(update_fields=["accepted_at"])
    workspace = Workspace.objects.filter(id=invitation.workspace_id).first()
    if not workspace:
        return JsonResponse({"detail": "Workspace not found."}, status=404)
    return JsonResponse(
        {
            "id": str(workspace.id),
            "name": workspace.name,
            "slug": workspace.slug,
            "role": invitation.role,
        }
    )


def health(request: HttpRequest) -> JsonResponse:
    """Liveness endpoint for Railway and future Vercel/API smoke checks."""
    return JsonResponse({"status": "ok", "service": "django-compatibility-api"})


def _current_user(request: HttpRequest) -> User | None:
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    try:
        claims = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = uuid.UUID(str(claims["sub"]))
    except (JWTError, KeyError, ValueError, TypeError):
        return None
    return User.objects.filter(id=user_id).first()


def _repository_payload(repo: Repository) -> dict:
    return {
        "id": str(repo.id),
        "name": repo.name,
        "full_name": repo.full_name,
        "github_url": repo.github_url,
        "description": repo.description,
        "default_branch": repo.default_branch,
        "status": repo.status,
        "error_message": repo.error_message,
        "languages": repo.languages or [],
        "frameworks": repo.frameworks or [],
        "file_count": repo.file_count,
        "chunk_count": repo.chunk_count,
        "last_indexed_at": repo.last_indexed_at.isoformat() if repo.last_indexed_at else None,
        "created_at": repo.created_at.isoformat() if repo.created_at else None,
        "workspace_id": str(repo.workspace_id) if repo.workspace_id else None,
    }


def _visible_repository_filter(request: HttpRequest, user: User):
    workspace_ids = list(
        WorkspaceMember.objects.filter(user_id=user.id).values_list("workspace_id", flat=True)
    )
    requested_workspace = request.GET.get("workspace_id")
    if requested_workspace:
        try:
            requested_workspace_id = uuid.UUID(requested_workspace)
        except ValueError:
            return None, JsonResponse({"detail": "Invalid workspace_id."}, status=422)
        if requested_workspace_id not in workspace_ids:
            return None, JsonResponse(
                {"detail": "You are not a member of the selected workspace."},
                status=403,
            )
        workspace_ids = [requested_workspace_id]
    return Q(owner_id=user.id) | Q(workspace_id__in=workspace_ids), None


def list_repositories(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    user = _current_user(request)
    if not user:
        return JsonResponse({"detail": "Authentication required."}, status=401)
    visibility, error = _visible_repository_filter(request, user)
    if error:
        return error
    repositories = Repository.objects.filter(visibility).order_by("-created_at")
    return JsonResponse([_repository_payload(repo) for repo in repositories], safe=False)


def repository_detail(request: HttpRequest, repo_id: uuid.UUID) -> JsonResponse:
    if request.method == "DELETE":
        return delete_repository(request, repo_id)
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    user = _current_user(request)
    if not user:
        return JsonResponse({"detail": "Authentication required."}, status=401)
    visibility, error = _visible_repository_filter(request, user)
    if error:
        return error
    repo = Repository.objects.filter(visibility, id=repo_id).first()
    if not repo:
        return JsonResponse({"detail": f"Repository {repo_id} not found"}, status=404)
    return JsonResponse(_repository_payload(repo))


def _extract_full_name(github_url: str) -> str:
    parsed = urlparse(github_url.rstrip("/"))
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        raise ValueError("Invalid GitHub URL. Use an https://github.com/owner/repository URL.")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError("Invalid GitHub URL. Must include an owner and repository name.")
    return f"{parts[0]}/{parts[1]}"


def _dispatch_indexing(repo_id: uuid.UUID) -> bool:
    try:
        celery = Celery("django_api", broker=settings.REDIS_URL)
        celery.send_task(settings.CELERY_INDEX_TASK, args=[str(repo_id)])
        return True
    except Exception:
        logger.exception("Could not enqueue indexing task for repository %s", repo_id)
        return False


def _repository_access(request: HttpRequest, repo_id: uuid.UUID):
    user = _current_user(request)
    if not user:
        return None, None, JsonResponse({"detail": "Authentication required."}, status=401)
    if user.role in {"owner", "admin"}:
        repo = Repository.objects.filter(id=repo_id).first()
    else:
        visibility, error = _visible_repository_filter(request, user)
        if error:
            return user, None, error
        repo = Repository.objects.filter(visibility, id=repo_id).first()
    if not repo:
        return user, None, JsonResponse({"detail": f"Repository {repo_id} not found"}, status=404)
    return user, repo, None


@csrf_exempt
def connect_repository(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    user = _current_user(request)
    if not user:
        return JsonResponse({"detail": "Authentication required."}, status=401)
    payload = _json_body(request)
    github_url = str(payload.get("github_url", "")).strip()
    try:
        full_name = _extract_full_name(github_url)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    existing = Repository.objects.filter(full_name=full_name).first()
    if existing:
        visibility, error = _visible_repository_filter(request, user)
        if error:
            return error
        if not Repository.objects.filter(visibility, id=existing.id).exists():
            return JsonResponse({"detail": "This repository is already connected to another workspace."}, status=409)
        if existing.status in {"ready", "indexing"}:
            return JsonResponse(_repository_payload(existing), status=200)
        existing.status = "pending"
        existing.error_message = None
        existing.save(update_fields=["status", "error_message"])
        _dispatch_indexing(existing.id)
        return JsonResponse(_repository_payload(existing), status=200)

    workspace_id = payload.get("workspace_id")
    membership_query = WorkspaceMember.objects.filter(user_id=user.id)
    if workspace_id:
        try:
            workspace_uuid = uuid.UUID(str(workspace_id))
        except ValueError:
            return JsonResponse({"detail": "Invalid workspace_id."}, status=422)
        membership = membership_query.filter(workspace_id=workspace_uuid).first()
        if not membership:
            return JsonResponse({"detail": "You are not a member of the selected workspace."}, status=403)
    else:
        membership = membership_query.order_by("created_at").first()
    name = str(payload.get("name") or full_name.rsplit("/", 1)[-1]).strip()
    repo = Repository.objects.create(
        id=uuid.uuid4(),
        name=name,
        full_name=full_name,
        github_url=github_url.rstrip("/"),
        status="pending",
        owner_id=user.id,
        workspace_id=membership.workspace_id if membership else None,
    )
    _dispatch_indexing(repo.id)
    return JsonResponse(_repository_payload(repo), status=201)


@csrf_exempt
def reindex_repository(request: HttpRequest, repo_id: uuid.UUID) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    user, repo, error = _repository_access(request, repo_id)
    if error:
        return error
    if user.role not in {"owner", "admin"} and repo.owner_id != user.id:
        return JsonResponse({"detail": "You do not have permission to modify this repository."}, status=403)
    repo.status = "pending"
    repo.error_message = None
    repo.save(update_fields=["status", "error_message"])
    queued = _dispatch_indexing(repo.id)
    return JsonResponse(
        {
            "message": "Reindexing triggered successfully" if queued else "Reindexing queued for retry.",
            "repository_id": str(repo.id),
        },
        status=202,
    )


@csrf_exempt
def delete_repository(request: HttpRequest, repo_id: uuid.UUID) -> HttpResponse:
    if request.method != "DELETE":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    user, repo, error = _repository_access(request, repo_id)
    if error:
        return error
    if user.role not in {"owner", "admin"} and repo.owner_id != user.id:
        return JsonResponse({"detail": "You do not have permission to modify this repository."}, status=403)
    repo.delete()
    return HttpResponse(status=204)


def repository_stats(request: HttpRequest, repo_id: uuid.UUID) -> JsonResponse:
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    _user, repo, error = _repository_access(request, repo_id)
    if error:
        return error
    return JsonResponse(
        {
            "file_count": repo.file_count,
            "chunk_count": repo.chunk_count,
            "languages": repo.languages or [],
            "frameworks": repo.frameworks or [],
            "last_indexed_at": repo.last_indexed_at.isoformat() if repo.last_indexed_at else None,
        }
    )


def _source_file_payload(source_file: SourceFile) -> dict:
    return {
        "id": str(source_file.id),
        "repository_id": str(source_file.repository_id),
        "file_path": source_file.file_path,
        "language": source_file.language,
        "size_bytes": source_file.size_bytes,
        "line_count": source_file.line_count,
        "content_hash": source_file.content_hash,
        "created_at": source_file.created_at.isoformat() if source_file.created_at else None,
    }


def repository_files(request: HttpRequest, repo_id: uuid.UUID) -> JsonResponse:
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    _user, _repo, error = _repository_access(request, repo_id)
    if error:
        return error
    files = SourceFile.objects.filter(repository_id=repo_id).order_by("file_path")
    return JsonResponse([_source_file_payload(item) for item in files], safe=False)


SOURCE_LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
    ".rs": "rust",
    ".css": "css",
    ".html": "html",
    ".md": "markdown",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
}


def repository_source(request: HttpRequest, repo_id: uuid.UUID, file_path: str) -> JsonResponse:
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    _user, repo, error = _repository_access(request, repo_id)
    if error:
        return error
    if repo.status != "ready":
        return JsonResponse(
            {"detail": "Repository must finish indexing before source is available."},
            status=409,
        )
    if not repo.clone_path:
        return JsonResponse({"detail": "Repository clone is unavailable."}, status=503)
    root = Path(repo.clone_path).resolve()
    candidate = (root / file_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return JsonResponse({"detail": "File path must stay inside the repository"}, status=400)
    if not candidate.is_file():
        return JsonResponse({"detail": "Source file not found"}, status=404)
    if candidate.stat().st_size > 200_000:
        return JsonResponse({"detail": "File is too large to preview"}, status=400)
    return JsonResponse(
        {
            "file_path": str(candidate.relative_to(root)),
            "language": SOURCE_LANGUAGES.get(candidate.suffix.lower(), "text"),
            "content": candidate.read_text(encoding="utf-8", errors="replace"),
        }
    )


def _ready_repository(request: HttpRequest, repo_id: uuid.UUID):
    _user, repo, error = _repository_access(request, repo_id)
    if error:
        return None, error
    if repo.status != "ready":
        return None, JsonResponse(
            {"detail": "Repository must finish indexing before this intelligence view is available."},
            status=409,
        )
    return repo, None


def repository_graph(request: HttpRequest, repo_id: uuid.UUID) -> JsonResponse:
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    _repo, error = _ready_repository(request, repo_id)
    if error:
        return error
    return JsonResponse(build_file_graph(repo_id))


def repository_architecture(request: HttpRequest, repo_id: uuid.UUID) -> JsonResponse:
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    _repo, error = _ready_repository(request, repo_id)
    if error:
        return error
    return JsonResponse(build_architecture(repo_id))


def repository_tests(request: HttpRequest, repo_id: uuid.UUID) -> JsonResponse:
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    _repo, error = _ready_repository(request, repo_id)
    if error:
        return error
    return JsonResponse(build_test_summary(repo_id))


def repository_tour(request: HttpRequest, repo_id: uuid.UUID) -> JsonResponse:
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    _repo, error = _ready_repository(request, repo_id)
    if error:
        return error
    return JsonResponse(build_tour(repo_id))


def repository_debt(request: HttpRequest, repo_id: uuid.UUID) -> JsonResponse:
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    _repo, error = _ready_repository(request, repo_id)
    if error:
        return error
    return JsonResponse(build_debt(repo_id))


def repository_documentation_quality(request: HttpRequest, repo_id: uuid.UUID) -> JsonResponse:
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    _repo, error = _ready_repository(request, repo_id)
    if error:
        return error
    return JsonResponse(build_documentation_quality(repo_id))


def _clone_repository(request: HttpRequest, repo_id: uuid.UUID):
    repo, error = _ready_repository(request, repo_id)
    if error:
        return None, error
    if not repo.clone_path:
        return None, JsonResponse({"detail": "Repository clone is unavailable."}, status=503)
    if not Path(repo.clone_path).is_dir():
        return None, JsonResponse({"detail": "Repository history is unavailable."}, status=503)
    return repo, None


def repository_history(request: HttpRequest, repo_id: uuid.UUID) -> JsonResponse:
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    repo, error = _clone_repository(request, repo_id)
    if error:
        return error
    try:
        commits = history(repo.clone_path, int(request.GET.get("limit", "20")))
    except (ValueError, OSError, git.exc.GitError):
        return JsonResponse({"detail": "Repository history is unavailable."}, status=503)
    return JsonResponse({"commits": commits, "count": len(commits)})


def latest_change(request: HttpRequest, repo_id: uuid.UUID) -> JsonResponse:
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    repo, error = _clone_repository(request, repo_id)
    if error:
        return error
    try:
        commit = git.Repo(repo.clone_path).head.commit.hexsha
        return JsonResponse(analyze_commit(repo.clone_path, commit))
    except (ValueError, OSError, git.exc.GitError):
        return JsonResponse({"detail": "Latest repository change is unavailable."}, status=503)


def commit_analysis(request: HttpRequest, repo_id: uuid.UUID, commit_sha: str) -> JsonResponse:
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    repo, error = _clone_repository(request, repo_id)
    if error:
        return error
    try:
        return JsonResponse(analyze_commit(repo.clone_path, commit_sha))
    except (ValueError, OSError, git.exc.GitError):
        return JsonResponse({"detail": "Commit analysis is unavailable."}, status=503)


@csrf_exempt
def compare_changes(request: HttpRequest, repo_id: uuid.UUID) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    repo, error = _clone_repository(request, repo_id)
    if error:
        return error
    payload = _json_body(request)
    base, head = str(payload.get("base", "")).strip(), str(payload.get("head", "")).strip()
    if not base or not head:
        return JsonResponse({"detail": "Both base and head commit references are required."}, status=422)
    try:
        return JsonResponse(compare_commits(repo.clone_path, base, head))
    except (ValueError, OSError, git.exc.GitError):
        return JsonResponse({"detail": "Commit comparison is unavailable."}, status=503)


def _forward_headers(request: HttpRequest) -> dict[str, str]:
    forwarded: dict[str, str] = {}
    for name in ("Authorization", "Accept", "Content-Type", "X-Request-ID"):
        value = request.headers.get(name)
        if value:
            forwarded[name] = value
    return forwarded


@csrf_exempt
def proxy_api(request: HttpRequest, path: str = "") -> HttpResponse:
    """Forward the existing API contract during the Django migration.

    This deliberately forwards only `/api/*`; it does not expose arbitrary
    outbound proxying. The legacy FastAPI service remains the source of truth
    until an endpoint is migrated and covered by a Django contract test.
    """
    target = f"{settings.LEGACY_API_URL}/{path}" if path else f"{settings.LEGACY_API_URL}/"
    try:
        response = httpx.request(
            method=request.method,
            url=target,
            params=request.GET.dict(),
            content=request.body if request.method not in {"GET", "HEAD"} else None,
            headers=_forward_headers(request),
            timeout=settings.API_PROXY_TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException:
        return JsonResponse(
            {
                "detail": {
                    "code": "LEGACY_API_TIMEOUT",
                    "message": "The API is taking too long to respond.",
                    "retryable": True,
                }
            },
            status=504,
        )
    except httpx.HTTPError:
        logger.exception("Django compatibility proxy could not reach legacy API")
        return JsonResponse(
            {
                "detail": {
                    "code": "LEGACY_API_UNAVAILABLE",
                    "message": "The API is temporarily unavailable.",
                    "retryable": True,
                }
            },
            status=503,
        )

    response_headers = {
        name: value
        for name, value in response.headers.items()
        if name.lower() not in HOP_BY_HOP_HEADERS | {"content-type", "content-length"}
    }
    return HttpResponse(
        response.content,
        status=response.status_code,
        content_type=response.headers.get("content-type"),
        headers=response_headers,
    )
