# AI Software Engineering Intelligence Platform — Project Journal

> **Purpose**: This file is the **single source of truth** for everything that has been built, decided, and changed.
> Every time work is done on this project, this file is updated. Future-you (or a collaborator) should be able to read this and know exactly where things stand.

---

## Project Overview

**One-line summary**: An AI-powered platform that continuously analyzes a software repository's code, architecture, dependencies, Git history, and documentation to help developers understand, navigate, and assess the impact of changes in large codebases.

**Repository**: `/Users/ayushpatel/AI Software Engineering Intelligence Platform`

**Started**: 2026-09-27  
**Current Phase**: Phase 1 (Foundation & Core RAG) — Implementation Complete & Verifiable

---

## Phase Roadmap

| Phase | Name | Status | Features |
|-------|------|--------|----------|
| **Phase 1** | Foundation & Core RAG | 🚧 In Progress | GitHub integration, AST code parsing, hybrid RAG, Q&A, source citations |
| **Phase 2** | Software Engineering Intelligence | 🔲 Planned | Architecture explorer, dependency graph, Git history, change impact analysis |
| **Phase 3** | Developer Productivity | 🔲 Planned | PR analysis, issue intelligence, test intelligence, automated documentation |
| **Phase 4** | Production & Advanced | 🔲 Planned | Multi-repo, autonomous agents, RAG evaluation, RBAC, observability, local LLM |

---

## Milestone Log

### Phase 1 — Foundation & Core RAG

- **2026-09-27 — Project Initialization & Planning**
  - Outlined the 4-phase architectural plan and 29 core features.
  - Initialized `PROJECT_JOURNAL.md`, `PHASES.md`, and `docs/architecture.md`.
  - Created `.env.example`, `.gitignore`, and `docker-compose.yml` defining PostgreSQL + pgvector, Redis, FastAPI Backend, Celery Worker, and Next.js Frontend.

- **2026-09-28 — Frontend Architecture & UI Components**
  - Scaffolded Next.js 14 App Router frontend with TypeScript and Tailwind CSS.
  - Implemented typed API client (`frontend/src/lib/api.ts`) for all repository, status, and query endpoints.
  - Built reusable components: `RepoCard`, `StatusBadge`, `CitationCard`, `ChatMessage`, `IndexingProgress`, and `EmptyState`.
  - Created pages:
    - `/` Dashboard with repository cards and empty states.
    - `/repos/new` Connect Repository form with validation and pipeline explanation.
    - `/repos/[id]` Repository details, live indexing status poller, and statistics.
    - `/repos/[id]/chat` Interactive codebase Q&A with message history, starter questions, and source citations.
    - `/docs` Platform architecture overview.

- **2026-09-30 — Complete Backend Implementation & Provider Abstraction**
  - Built Provider Abstraction Layer:
    - `LLMProvider` interface and `OpenAIProvider` with configurable model, temperature, and tokens.
    - `EmbeddingProvider` interface and `OpenAIEmbeddingProvider` with automatic batching.
    - Provider factories enabling zero-code provider switching via environment variables.
  - Implemented async PostgreSQL + pgvector database models: `Repository`, `SourceFile`, and `CodeChunk`.
  - Built `GitHubService` supporting authenticated PAT cloning, shallow pulls, file filtering, language/framework detection, SHA-256 incremental hashing, and HMAC webhook verification.
  - Implemented `ParserService` using Tree-sitter for Python, JavaScript, and TypeScript, extracting AST functions, classes, methods, docstrings, imports, and splitting oversized chunks.
  - Implemented `EmbeddingService` adding rich context headers (`[language, type, symbol, docstring]`) to code chunks.
  - Implemented `RetrievalService` for Hybrid RAG: pgvector cosine distance search + BM25Okapi sparse search + Reciprocal Rank Fusion (RRF, k=60).
  - Implemented `LLMService` constructing structured context prompts and returning answers with exact citations.
  - Implemented `IndexingService` orchestrating the full pipeline (clone → detect → parse → embed → upsert) and incremental re-indexing.
  - Built Celery worker tasks (`index_repository_task`, `reindex_files_task`) with in-process asyncio fallback.
  - Built FastAPI API routes: `/repos` (connect, list, get, reindex, delete, stats, files), `/repos/{id}/query`, and `/webhook/github`.
  - Added Alembic migration configuration and initial migration script (`001_initial.py`).

---

## Decisions & Architecture Choices

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-09-27 | 4-Phase MVP roadmap | Scope control — deliver working Q&A first, then layer on structural analysis and developer intelligence |
| 2026-09-27 | OpenAI as default LLM & Embeddings | Proven quality and stable API; isolated behind provider interfaces for zero-lock-in |
| 2026-09-27 | Python, JavaScript, TypeScript for Phase 1 | High industry relevance while keeping Tree-sitter parsing robust and focused |
| 2026-09-27 | PostgreSQL + pgvector | Unified database for relational metadata, symbols, and vector embeddings without extra vector DB cluster |
| 2026-09-27 | Hybrid RAG (Vector + BM25 + RRF) | Code search requires exact identifier lookup (BM25) as well as conceptual understanding (embeddings) |
| 2026-09-27 | PAT auth initially → GitHub App later | Minimizes setup friction in Phase 1; webhook support retained for push-triggered re-indexing |
| 2026-09-28 | Next.js 14 App Router + Tailwind | Modern, responsive developer UI with SSR and App Router architecture |
| 2026-09-30 | In-process asyncio fallback for Celery | Allows testing and running the backend both in Docker Compose (with Celery) and in standalone dev mode |

---

## Technology Stack

| Layer | Technology | Status |
|-------|-----------|--------|
| **Backend Framework** | FastAPI (Python 3.11/asyncio) | ✅ Implemented |
| **Vector Database** | PostgreSQL 16 + pgvector | ✅ Implemented |
| **ORM / Migration** | SQLAlchemy 2.0 (asyncpg) + Alembic | ✅ Implemented |
| **Embedding Model** | OpenAI `text-embedding-3-small` (via abstraction) | ✅ Implemented |
| **LLM** | OpenAI `gpt-4o` (via abstraction) | ✅ Implemented |
| **Code Parser** | Tree-sitter (Python, JS, TS grammars) | ✅ Implemented |
| **Lexical Search** | BM25Okapi (`rank-bm25`) | ✅ Implemented |
| **Fusion / Rerank** | Reciprocal Rank Fusion (RRF, k=60) | ✅ Implemented |
| **Task Queue** | Celery + Redis | ✅ Implemented |
| **Git Integration** | GitPython + GitHub Webhooks | ✅ Implemented |
| **Frontend** | Next.js 14 + TypeScript + Tailwind CSS | ✅ Implemented |

---

## File Structure

```
AI Software Engineering Intelligence Platform/
├── PROJECT_JOURNAL.md          ← Master project record (You are here)
├── PHASES.md                   ← Full 4-phase breakdown & checklist
├── README.md                   ← Project overview & quick start
├── docker-compose.yml          ← PostgreSQL, Redis, Backend, Worker, Frontend
├── .env.example                ← Environment template
├── .gitignore
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/001_initial.py
│   └── app/
│       ├── main.py             ← FastAPI entrypoint & health checks
│       ├── config.py           ← Pydantic settings
│       ├── database.py         ← Async engine & session factory
│       ├── models/             ← SQLAlchemy models (Repository, SourceFile, CodeChunk)
│       ├── providers/          ← Abstract LLM & Embedding interfaces & implementations
│       ├── services/           ← GitHubService, ParserService, EmbeddingService, RetrievalService, LLMService, IndexingService
│       ├── api/                ← FastAPI routers (/repos, /query, /webhook) & Pydantic schemas
│       └── workers/            ← Celery app & background tasks
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── src/
│       ├── app/                ← Next.js pages (Dashboard, Connect, Repo Detail, Chat, Docs)
│       ├── components/         ← Reusable UI components
│       └── lib/                ← API client (Axios) & utility helpers
└── docs/
    └── architecture.md         ← System diagrams and data flow documentation
```

---

*Last updated: 2026-09-30*
