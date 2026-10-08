"""FastAPI main application entrypoint."""
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis import asyncio as redis
from sqlalchemy import text

from app.api.query import router as query_router
from app.api.repos import router as repos_router
from app.api.webhook import router as webhook_router
from app.config import settings
from app.database import create_all_tables, engine
from app.services.rate_limit_service import rate_limit_for_path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aise")


class SafetyMiddleware:
    """Apply request-size and best-effort Redis rate limits to API traffic."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope.get("path", "").startswith(("/repos", "/query")):
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length) > settings.API_MAX_REQUEST_BYTES:
                    response = JSONResponse(status_code=413, content={"error": {"code": "REQUEST_TOO_LARGE", "message": "Request body exceeds the configured size limit."}})
                    await response(scope, receive, send)
                    return
            except ValueError:
                pass
        client_host = (scope.get("client") or ("unknown", 0))[0]
        limit, route_bucket = rate_limit_for_path(
            scope.get("path", ""),
            settings.API_RATE_LIMIT_PER_MINUTE,
            settings.API_EXPENSIVE_RATE_LIMIT_PER_MINUTE,
        )
        bucket = int(time.time() // 60)
        key = f"aise:rate:{route_bucket}:{client_host}:{bucket}"
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            count = await client.incr(key)
            if count == 1:
                await client.expire(key, 60)
            if count > limit:
                response = JSONResponse(status_code=429, content={"error": {"code": "RATE_LIMITED", "message": "Too many requests. Retry after the current minute."}}, headers={"Retry-After": "60"})
                await response(scope, receive, send)
                return
        except Exception as exc:
            logger.warning("Rate limiter unavailable; allowing request: %s", exc)
        finally:
            await client.aclose()
        await self.app(scope, receive, send)


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

app.add_middleware(SafetyMiddleware)

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
        "phase": "Phase 3 - Developer Productivity & Safety",
        "status": "online",
        "docs_url": "/docs",
        "llm_provider": settings.LLM_PROVIDER,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
    }


@app.get("/health", tags=["status"])
async def health_check() -> dict:
    """Comprehensive database and Redis health check endpoint for monitoring."""
    db_status = "healthy"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {e}"

    redis_status = "healthy"
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await redis_client.ping()
    except Exception as e:
        redis_status = f"unhealthy: {e}"
    finally:
        await redis_client.aclose()

    return {
        "status": "healthy" if db_status == "healthy" and redis_status == "healthy" else "degraded",
        "database": db_status,
        "redis": redis_status,
        "app_env": settings.APP_ENV,
    }
