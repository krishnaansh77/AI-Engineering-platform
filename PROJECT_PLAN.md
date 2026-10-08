# AI Software Engineering Intelligence Platform — Project Plan

This file is the practical handoff document for the project. It records what is already working, what is intentionally incomplete, and the order for future development.

## Current status

- Phase 1 — Foundation & Core RAG: **complete**
- Phase 2 — Repository Intelligence: **complete**
- Phase 3 — Developer Productivity: **in progress**
- Latest verified baseline: **24 backend tests passing** and the Next.js production build passing
- Repository: `https://github.com/krishnaansh77/AI-Engineering-platform.git`
- Local workspace: `/Users/ayushpatel/AI Software Engineering Intelligence Platform`

The project is running with Docker Compose: PostgreSQL + pgvector, Redis, FastAPI, Celery worker, and Next.js.

## What has been built

### Phase 1 — Foundation & Core RAG

- GitHub repository connection, shallow clone/update, language and framework detection
- Incremental indexing with webhook-triggered re-indexing
- Tree-sitter parsing for Python, JavaScript, and TypeScript
- Function/class/method/module chunks with symbols, imports, docstrings, and line ranges
- PostgreSQL + pgvector storage
- Hybrid retrieval: vector search + BM25 + Reciprocal Rank Fusion
- Gemini/OpenAI provider abstraction for LLMs and embeddings
- Codebase Q&A with source citations
- Redis response caching with re-index-aware invalidation
- Answer feedback storage and quality summaries
- Query latency and retrieval observability

### Phase 2 — Repository Intelligence

- File dependency graph with Python and JS/TS import resolution
- Symbol metadata attached to graph nodes
- Searchable graph explorer with imports and reverse references
- Three-hop dependency impact analysis
- Secure, bounded source previews with path-traversal protection
- Architecture layer inference and cross-layer relationships
- Git commit history with changed files, insertions, deletions, and impact counts
- Selectable commit review analysis
- Repository onboarding tour showing key connected files and symbols
- Test-to-source relationship heuristics
- Semantic code search without an LLM call
- Documentation inventory and safe previews
- Technical-debt signals for high connectivity and large code chunks
- Symbol-level documentation quality coverage
- Downloadable Markdown repository intelligence report

### Phase 3 — Developer Productivity currently implemented

- Latest-change / PR-style analysis for local commits
- Review any indexed commit from the Git history panel
- Base/head PR comparison by branch or commit SHA, including changed files, insertions/deletions, tests, documentation, and downstream dependency impact
- GitHub issue listing and issue-to-code relevance analysis
- RAG evaluation endpoint with Recall@K and MRR
- RAG evaluation UI supporting multiple benchmark cases
- Per-case and average retrieval latency in evaluation results
- Reviewable starter benchmark template at `docs/rag-benchmark.example.json`
- CI-friendly benchmark runner at `backend/scripts/run_rag_benchmark.py` with optional quality thresholds

Phase 3 is not finished yet. The remaining work is listed below.

## Important current behavior and limitations

- Issue intelligence depends on GitHub API connectivity. Public repositories can work without a token; private or rate-limited access needs `GITHUB_PAT` in the local `.env` file.
- Never paste API keys or PATs into chat or commit them. Put them only in local `.env`, which is ignored by Git.
- Documentation and test coverage are heuristic signals, not replacements for runtime coverage or human review.
- Commit impact analysis uses the files available in the local shallow clone.
- Formal RAG evaluation requires benchmark questions and expected file paths; one live smoke benchmark currently returns Recall@3 `1.0` and MRR `1.0` for database initialization.
- Gemini quota limits can temporarily return a controlled `503`; Redis caching reduces repeated LLM calls but does not remove provider limits.

## Next work plan

### Phase 3A — Finish developer productivity

1. **Real PR comparison** — complete
   - Accept base/head branches or commit SHAs through the API and repository UI.
   - Produce changed-file summary, dependency impact, related tests, and documentation warnings.
   - Covered by regression tests for commit comparison and diff statistics.

2. **Issue intelligence hardening**
   - Add GitHub API retry/backoff and clearer rate-limit messages.
   - Cache issue metadata in Redis.
   - Support closed issues and configurable issue state.
   - Add issue analysis tests using mocked GitHub responses.

3. **Automatic documentation generation**
   - Generate module/function documentation only on explicit user action.
   - Require citation-backed output and show a preview before saving.
   - Add provider-cost protection and a maximum generation scope.

4. **RAG evaluation expansion**
   - Expand the starter benchmark to 10–20 representative questions for the target repositories.
   - Add answer-level citation hit rate and helpful-rate reporting; retrieval evaluation currently measures Recall@K, MRR, and latency.
   - Run the benchmark runner in CI against a seeded test repository.

### Phase 3B — Quality and safety

1. Add mocked integration tests for GitHub, Redis, indexing, search, and issue analysis.
2. Add API rate limits and request-size limits where appropriate.
3. Add structured error codes and user-facing retry guidance.
4. Add basic secret-pattern scanning as an opt-in, clearly labeled heuristic.
5. Improve accessibility and responsive behavior across the repository detail page.

### Phase 4 — Production and advanced capabilities

- Authentication and RBAC
- Multi-repository workspaces
- GitHub App instead of PAT-only access
- Full PR and branch comparison
- Advanced RAG evaluation and feedback-driven retrieval improvements
- Cost dashboards and provider usage controls
- Observability dashboards and alerting
- Local LLM mode through Ollama or another compatible provider
- Specialized code, Git, documentation, and review agents

## Inputs that may be needed from the owner

No input is required for the next local development steps. When ready, the following will improve quality:

1. **Benchmark set:** 10–20 real questions with expected file paths for RAG evaluation.
2. **GitHub PAT:** place it locally in `.env` only if private repositories or higher GitHub API limits are needed.
3. **Deployment target:** choose later between local-only, Render/Fly.io/Railway, or Vercel plus a hosted backend/database.
4. **Priority choice for Phase 3:** documentation generation, real PR comparison, issue intelligence hardening, or evaluation/CI.

## Development and verification checklist

From the repository root:

```bash
docker compose up -d
PYTHONPATH=backend pytest -q
docker compose exec -T frontend npm run build
docker compose exec -T redis redis-cli ping
```

Expected baseline at the time this plan was written:

- Backend tests: `24 passed`
- After the evaluation milestone: `25 passed`
- After the PR comparison milestone: `26 passed`
- Frontend build: successful
- Redis: `PONG`
- Backend health: `database=healthy`

Before every commit:

- Do not expose secrets in output or source files.
- Add or update tests for backend behavior.
- Run the backend test suite and frontend build.
- Verify live endpoints inside the backend container when host networking is unavailable.
- Commit in a focused unit and push to `master` only after verification.
