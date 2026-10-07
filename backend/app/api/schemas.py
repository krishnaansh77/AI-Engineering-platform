"""Pydantic schemas for API requests and responses."""
from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ConnectRepoRequest(BaseModel):
    """Payload for connecting a new GitHub repository."""
    github_url: str = Field(..., description="Full GitHub repository URL")
    name: Optional[str] = Field(None, description="Optional custom display name")


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
