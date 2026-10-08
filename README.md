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
LLM (Gemini / OpenAI provider)
      ↓
Answer + Source Citations (file · function · lines)
```

## Phase Roadmap

| Phase | Features | Status |
|-------|----------|--------|
| **Phase 1** | GitHub integration · Code parsing · Hybrid RAG · Q&A · Citations | ✅ Complete |
| **Phase 2** | Dependency graph · Architecture explorer · Git history · Change impact | ✅ Complete |
| **Phase 3** | PR comparison · Issue intelligence · RAG evaluation · Documentation previews · Quality signals | 🟡 In progress |
| **Phase 4** | RBAC · Multi-repo · GitHub App · Agents · Observability · Local LLM | 🔲 Future |

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- LLM and embedding provider API key (Gemini is supported)
- GitHub Personal Access Token (`repo` scope)

### Setup

```bash
# 1. Clone this repository
git clone <this-repo>
cd "AI Software Engineering Intelligence Platform"

# 2. Configure environment
cp .env.example .env
# Edit .env — fill in the provider key and GITHUB_PAT when indexing private repositories

# 3. Start everything
docker compose up --build -d

# 4. Open the UI
open http://localhost:3000

# 5. Run database migrations
docker compose exec backend alembic upgrade head

# 6. Verify the local stack
docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"
docker compose exec redis redis-cli ping
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

See `PROJECT_PLAN.md` for the current implementation status, verified baseline, and future roadmap.
See `PHASES.md` for the detailed phase checklist.

## Security notes

- Keep `.env` local and never commit provider keys or GitHub PATs.
- Gemini/API quota failures are surfaced as retryable errors; local mock providers are available for CI.
- Secret scanning is opt-in and heuristic. It reports redacted file/line findings and does not replace a dedicated security scanner.
