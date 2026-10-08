from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://aise:aise_secret@localhost:5432/aise_db"

    @field_validator("DATABASE_URL")
    @classmethod
    def use_async_postgres_driver(cls, value: str) -> str:
        """Accept Railway's standard URL while keeping SQLAlchemy async-safe."""
        if value.startswith("postgres://"):
            return "postgresql+asyncpg://" + value.removeprefix("postgres://")
        if value.startswith("postgresql://"):
            return "postgresql+asyncpg://" + value.removeprefix("postgresql://")
        return value

    # ── Redis / Celery ────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # ── LLM Provider ─────────────────────────────────────────────────────────
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_LLM_MODEL: str = "gpt-4o"
    OPENAI_LLM_TEMPERATURE: float = 0.0
    OPENAI_LLM_MAX_TOKENS: int = 2048

    # Google Gemini
    GOOGLE_API_KEY: str = ""
    GEMINI_LLM_MODEL: str = "gemini-3.8-flash"

    # Anthropic (Phase 4)
    ANTHROPIC_API_KEY: str = ""

    # ── Embedding Provider ────────────────────────────────────────────────────
    EMBEDDING_PROVIDER: str = "openai"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    GEMINI_EMBEDDING_MODEL: str = "models/gemini-embedding-001"
    EMBEDDING_DIMENSION: int = 768  # 768 for Gemini embeddings, 1536 for OpenAI

    # ── GitHub ────────────────────────────────────────────────────────────────
    GITHUB_PAT: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""

    # ── Retrieval ─────────────────────────────────────────────────────────────
    RETRIEVAL_TOP_K: int = 20
    RETRIEVAL_FINAL_K: int = 5
    RERANKER_ENABLED: bool = False
    QUERY_CACHE_TTL_SECONDS: int = 900
    API_RATE_LIMIT_PER_MINUTE: int = 120
    API_MAX_REQUEST_BYTES: int = 1_000_000

    # ── Storage ───────────────────────────────────────────────────────────────
    REPOS_CLONE_DIR: str = "/repos"

    # ── App ───────────────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me-in-production"
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
