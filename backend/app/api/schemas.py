"""Pydantic schemas for API requests and responses."""
from datetime import datetime
from typing import List, Optional, Literal
import uuid
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ConnectRepoRequest(BaseModel):
    """Payload for connecting a new GitHub repository."""
    github_url: str = Field(..., description="Full GitHub repository URL")
    name: Optional[str] = Field(None, description="Optional custom display name")


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


class QueryResponse(BaseModel):
    """AI answer with cited code locations."""
    answer: str
    citations: List[CitationSchema]
    model: str
    retrieval_count: int
    citation_coverage: float = Field(0.0, ge=0.0, le=1.0)
    cached: bool = False


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
