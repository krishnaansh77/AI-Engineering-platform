"""Pydantic schemas for API requests and responses."""
from datetime import datetime
from typing import List, Optional, Literal
import re
import uuid
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class ConnectRepoRequest(BaseModel):
    """Payload for connecting a new GitHub repository."""
    github_url: str = Field(..., description="Full GitHub repository URL")
    name: Optional[str] = Field(None, description="Optional custom display name")
    workspace_id: Optional[uuid.UUID] = None


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=8, max_length=200)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=1, max_length=200)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    role: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    role: str


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)


class WorkspaceUpdate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)


class WorkspaceInvitationCreate(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    role: Literal["member", "admin"] = "member"


class WorkspaceInvitationResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    email: str
    role: str
    expires_at: datetime
    invite_token: Optional[str] = None
    accepted_at: Optional[datetime] = None


class WorkspaceMemberResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    role: str
    created_at: datetime


class WorkspaceMemberUpdate(BaseModel):
    role: Literal["member", "admin"]


def _validate_version_ref(value: str) -> str:
    if value == "default":
        return value
    match = re.fullmatch(r"(branch|tag):([A-Za-z0-9][A-Za-z0-9._/-]{0,199})", value)
    if not match:
        raise ValueError("Version must be 'default', 'branch:<name>', or 'tag:<name>'.")
    ref_name = match.group(2)
    if (
        any(
            not part
            or part.startswith(".")
            or part.endswith(".")
            or ".." in part
            or part.lower().endswith(".lock")
            for part in ref_name.split("/")
        )
        or "@{" in ref_name
    ):
        raise ValueError("Version reference is not a valid Git ref name.")
    return value


class RepositoryVersionIndexRequest(BaseModel):
    """Request indexing one branch or tag without replacing the default index."""
    ref_type: Literal["branch", "tag"]
    ref_name: str = Field(..., min_length=1, max_length=200)

    @field_validator("ref_name")
    @classmethod
    def validate_ref_name(cls, value: str) -> str:
        _validate_version_ref(f"branch:{value}")
        return value


class RepositoryVersionCompareRequest(BaseModel):
    """Select two already indexed refs for an exact source diff."""
    base_ref: str = Field(..., min_length=1, max_length=255)
    head_ref: str = Field(..., min_length=1, max_length=255)

    @field_validator("base_ref", "head_ref")
    @classmethod
    def validate_version(cls, value: str) -> str:
        return _validate_version_ref(value)


class RepositoryVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version_ref: str
    ref_type: str
    ref_name: str
    status: str
    commit_sha: Optional[str] = None
    file_count: int = 0
    chunk_count: int = 0
    error_message: Optional[str] = None
    last_indexed_at: Optional[datetime] = None


class RepositoryResponse(BaseModel):
    """Public representation of a connected repository."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    full_name: str
    github_url: str
    description: Optional[str] = None
    default_branch: str
    status: str
    error_message: Optional[str] = None
    languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    file_count: int = 0
    chunk_count: int = 0
    last_indexed_at: Optional[datetime] = None
    created_at: datetime
    workspace_id: Optional[uuid.UUID] = None

    @field_validator("default_branch", mode="before")
    @classmethod
    def normalize_default_branch(cls, value: str | None) -> str:
        # Older repository rows may predate the non-null database default.
        return value or "main"

    @field_validator("languages", "frameworks", mode="before")
    @classmethod
    def normalize_metadata_lists(cls, value: list[str] | None) -> list[str]:
        # Keep the response contract stable for rows created before JSON
        # metadata defaults were enforced.
        return value or []

    @field_validator("file_count", "chunk_count", mode="before")
    @classmethod
    def normalize_counts(cls, value: int | None) -> int:
        return value or 0


class RepoStatsResponse(BaseModel):
    """Aggregate statistics for a repository."""
    file_count: int
    chunk_count: int
    languages: List[str]
    frameworks: List[str]
    last_indexed_at: Optional[datetime] = None


class SourceFileResponse(BaseModel):
    """Details of an indexed source file."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    version_ref: str = "default"
    file_path: str
    language: str
    size_bytes: int
    line_count: int
    content_hash: str
    created_at: datetime


class CitationSchema(BaseModel):
    """Source code citation for an answer."""
    file_path: str
    symbol_name: Optional[str] = None
    chunk_type: str
    start_line: int
    end_line: int


class QueryRequest(BaseModel):
    """Developer question payload."""
    question: str = Field(..., min_length=1, description="Question about the repository")
    top_k: int = Field(5, ge=1, le=20, description="Number of source chunks to retrieve")
    version_ref: str = Field("default", min_length=1, max_length=255)

    @field_validator("version_ref")
    @classmethod
    def validate_version(cls, value: str) -> str:
        return _validate_version_ref(value)


class AgentRequest(BaseModel):
    """Bounded repository-agent question payload."""
    question: str = Field(..., min_length=1, max_length=4000)
    top_k: int = Field(5, ge=1, le=10)
    version_ref: str = Field("default", min_length=1, max_length=255)

    @field_validator("version_ref")
    @classmethod
    def validate_version(cls, value: str) -> str:
        return _validate_version_ref(value)


class QueryResponse(BaseModel):
    """AI answer with cited code locations."""
    answer: str
    citations: List[CitationSchema]
    model: str
    retrieval_count: int
    citation_coverage: float = Field(0.0, ge=0.0, le=1.0)
    cached: bool = False
    version_ref: str = "default"


class AgentResponse(QueryResponse):
    tools_used: List[str] = Field(default_factory=list)


class SearchResultSchema(BaseModel):
    file_path: str
    symbol_name: Optional[str] = None
    chunk_type: str
    start_line: int
    end_line: int
    snippet: str
    score: float


class SearchResponse(BaseModel):
    results: List[SearchResultSchema]
    query: str


class EvaluationCase(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    expected_files: List[str] = Field(..., min_length=1, max_length=20)


class EvaluationRequest(BaseModel):
    cases: List[EvaluationCase] = Field(..., min_length=1, max_length=50)
    top_k: int = Field(5, ge=1, le=20)
    version_ref: str = Field("default", min_length=1, max_length=255)

    @field_validator("version_ref")
    @classmethod
    def validate_version(cls, value: str) -> str:
        return _validate_version_ref(value)


class PRComparisonRequest(BaseModel):
    """Base and head refs for local PR-style comparison."""
    base: str = Field(..., min_length=1, max_length=200)
    head: str = Field(..., min_length=1, max_length=200)


class DocumentationPreviewRequest(BaseModel):
    """Request an unsaved, citation-backed documentation draft."""
    file_path: str = Field(..., min_length=1, max_length=500)
    audience: str = Field("developers", min_length=1, max_length=100)


class DocumentationSaveRequest(BaseModel):
    """Preview or explicitly commit generated documentation to GitHub."""
    file_path: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1, max_length=50_000)
    branch: str = Field("main", min_length=1, max_length=200)
    commit_message: str = Field("Update generated documentation", min_length=1, max_length=200)
    confirm: bool = False


class FeedbackRequest(BaseModel):
    """User rating for a generated repository answer."""
    question: str = Field(..., min_length=1, max_length=10000)
    rating: Literal["helpful", "not_helpful"]
    model: str = Field(..., min_length=1, max_length=100)
    retrieval_count: int = Field(0, ge=0, le=100)
    citation_count: int = Field(0, ge=0, le=100)
