"""Seed a small deterministic repository for the CI RAG benchmark."""
import asyncio
import uuid
from datetime import datetime, timezone

from app.database import AsyncSessionLocal, create_all_tables, engine
from app.models.code_chunk import CodeChunk
from app.models.repository import Repository
from app.models.source_file import SourceFile
from app.providers.embedding.mock_embedding import MockEmbeddingProvider


REPOSITORY_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
FILES = {
    "backend/app/database.py": "database initialized with SQLAlchemy async engine and sessions",
    "backend/app/api/repos.py": "repository API routes connect repositories and expose repository endpoints",
    "backend/app/services/retrieval_service.py": "hybrid retrieval combines vector search BM25 and Reciprocal Rank Fusion",
    "backend/app/workers/tasks.py": "background indexing tasks process repository files with Celery",
    "backend/app/workers/celery_app.py": "Celery worker is configured for background indexing tasks",
    "backend/app/services/evaluation_service.py": "retrieval evaluation metrics calculate Recall MRR and latency",
    "backend/app/api/query.py": "query API exposes retrieval evaluation and repository questions",
    "backend/app/providers/llm/gemini_provider.py": "Gemini provider generates content using the Google GenAI client",
    "backend/app/providers/llm/factory.py": "provider factory selects the configured LLM provider",
    "backend/app/providers/embedding/gemini_embedding.py": "Gemini embedding provider creates retrieval embeddings",
    "backend/app/services/indexing_service.py": "repository indexing parses files creates chunks and stores embeddings",
    "backend/app/services/query_cache.py": "query cache keys include the repository index version and normalized question",
    "backend/app/services/github_service.py": "GitHub service retrieves source previews and repository metadata",
    "backend/app/services/secret_scan_service.py": "secret scan detects and redacts private keys and API key patterns",
}


async def seed() -> None:
    await create_all_tables()
    provider = MockEmbeddingProvider()
    async with AsyncSessionLocal() as session:
        repository = Repository(
            id=REPOSITORY_ID,
            name="ci-rag-fixture",
            full_name="ci/rag-fixture",
            github_url="https://github.com/ci/rag-fixture",
            default_branch="main",
            languages=["python"],
            frameworks=["FastAPI"],
            status="ready",
            file_count=len(FILES),
            chunk_count=len(FILES),
            last_indexed_at=datetime.now(timezone.utc),
        )
        session.add(repository)
        for path, content in FILES.items():
            file_id = uuid.uuid4()
            session.add(SourceFile(
                id=file_id,
                repository_id=REPOSITORY_ID,
                file_path=path,
                language="python",
                size_bytes=len(content),
                line_count=1,
                content_hash=uuid.uuid5(uuid.NAMESPACE_URL, path).hex,
            ))
            embedding = await provider.embed_single(content)
            session.add(CodeChunk(
                id=uuid.uuid4(),
                repository_id=REPOSITORY_ID,
                file_id=file_id,
                file_path=path,
                language="python",
                chunk_type="module",
                symbol_name=path.rsplit("/", 1)[-1].removesuffix(".py"),
                start_line=1,
                end_line=1,
                content=content,
                imports=[],
                embedding=embedding,
            ))
        await session.commit()
    print(REPOSITORY_ID)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
