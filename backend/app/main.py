"""FastAPI main application entrypoint."""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.query import router as query_router
from app.api.repos import router as repos_router
from app.api.webhook import router as webhook_router
from app.config import settings
from app.database import create_all_tables, engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aise")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event handler for startup and shutdown routines."""
    logger.info("Initializing AI Software Engineering Intelligence Platform backend...")
    try:
        await create_all_tables()
        logger.info("Database tables and pgvector extension initialized successfully.")
    except Exception as e:
        logger.warning("Could not auto-create database tables on startup: %s", e)
    yield
    logger.info("Shutting down AI Software Engineering Intelligence Platform backend...")
    await engine.dispose()


app = FastAPI(
    title="AI Software Engineering Intelligence Platform",
    description=(
        "Continuous analysis of repository code, architecture, dependencies, "
        "and Git history with hybrid RAG and verifiable source citations."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(repos_router)
app.include_router(query_router)
app.include_router(webhook_router)


@app.get("/", tags=["status"])
async def root() -> dict:
    """Root info endpoint."""
    return {
        "platform": "AI Software Engineering Intelligence Platform",
        "phase": "Phase 1 - Foundation & Core RAG",
        "status": "online",
        "docs_url": "/docs",
        "llm_provider": settings.LLM_PROVIDER,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
    }


@app.get("/health", tags=["status"])
async def health_check() -> dict:
    """Comprehensive health check endpoint for monitoring."""
    db_status = "healthy"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {e}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "app_env": settings.APP_ENV,
    }
