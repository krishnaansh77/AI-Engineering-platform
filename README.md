# AI Software Engineering Intelligence Platform

> An AI-powered platform that continuously analyzes a software repository's code, architecture, dependencies, Git history, and documentation to help developers understand, navigate, and assess the impact of changes in large codebases.

---

## Architecture

```
GitHub Repository
      ↓
Clone + File Discovery
      ↓
Tree-sitter AST Parser (Python · JS · TS)
      ↓
Smart Code Chunker (by function / class boundary)
      ↓
Embedding Pipeline ──→ PostgreSQL + pgvector
      ↓                          ↕
BM25 Index ←──── Hybrid Retriever (RRF Fusion)
      ↓
LLM (OpenAI GPT-4o)
      ↓
Answer + Source Citations (file · function · lines)
```

## Phase Roadmap

| Phase | Features | Status |
|-------|----------|--------|
| **Phase 1** | GitHub integration · Code parsing · Hybrid RAG · Q&A · Citations | 🚧 In Progress |
| **Phase 2** | Dependency graph · Architecture explorer · Git history · Change impact | 🔲 Planned |
| **Phase 3** | PR analysis · Onboarding · Issue intelligence · Test coverage · Debt | 🔲 Planned |
| **Phase 4** | RBAC · RAG eval · Multi-repo · Agents · Observability · Local LLM | 🔲 Planned |

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- OpenAI API key
- GitHub Personal Access Token (`repo` scope)

### Setup

```bash
# 1. Clone this repository
git clone <this-repo>
cd "AI Software Engineering Intelligence Platform"

# 2. Configure environment
cp .env.example .env
# Edit .env — fill in OPENAI_API_KEY and GITHUB_PAT

# 3. Start everything
docker-compose up --build

# 4. Open the UI
open http://localhost:3000

# 5. Run database migrations (first time only)
docker-compose exec backend alembic upgrade head
```

### Usage

1. Open `http://localhost:3000`
2. Paste a GitHub repository URL and your PAT
3. Wait for indexing to complete
4. Ask questions about the codebase

---

## Project Structure

```
.
├── PROJECT_JOURNAL.md      ← Living record of all work done
├── PHASES.md               ← Detailed phase breakdown + task lists
├── docker-compose.yml
├── .env.example
├── backend/                ← FastAPI application
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/         ← SQLAlchemy ORM models
│   │   ├── api/            ← Route handlers
│   │   ├── services/       ← Business logic
│   │   ├── providers/      ← LLM + Embedding provider abstraction
│   │   └── workers/        ← Celery async tasks
│   ├── alembic/            ← DB migrations
│   └── requirements.txt
├── frontend/               ← Next.js application
│   └── src/
│       ├── app/            ← App Router pages
│       ├── components/     ← React components
│       └── lib/            ← API client, utilities
└── docs/                   ← Architecture diagrams, notes
```

## Provider Abstraction

The LLM and Embedding layers are fully abstracted:

```python
# Switch LLM provider with one env var
LLM_PROVIDER=openai      # or: anthropic (Phase 4)

# Switch embedding provider with one env var
EMBEDDING_PROVIDER=openai  # or: local (Phase 4, Ollama)
```

---

## Key Files to Know

| File | Purpose |
|------|---------|
| `PROJECT_JOURNAL.md` | Everything that has been built and decided |
| `PHASES.md` | Full task breakdown for all 4 phases |
| `backend/app/providers/` | LLM + Embedding provider abstraction |
| `backend/app/services/parser_service.py` | Tree-sitter AST parsing |
| `backend/app/services/retrieval_service.py` | Hybrid RAG (BM25 + vector + RRF) |
| `backend/app/services/indexing_service.py` | Full indexing pipeline orchestration |

---

## Contributing / Continuing

See `PROJECT_JOURNAL.md` for the full history of decisions and milestones.
See `PHASES.md` for the current task checklist.
