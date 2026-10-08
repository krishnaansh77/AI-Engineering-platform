# AI Software Engineering Intelligence Platform — Project Plan

This file is the practical handoff document for the project. It records what is already working, what is intentionally incomplete, and the order for future development.

## Current status

- Phase 1 — Foundation & Core RAG: **complete**
- Phase 2 — Repository Intelligence: **complete**
- Phase 3 — Developer Productivity: **in progress**
- Latest verified baseline: **24 backend tests passing** and the Next.js production build passing
- Repository: `https://github.com/krishnaansh77/AI-Engineering-platform.git`
- Local workspace: `/Users/ayushpatel/AI Software Engineering Intelligence Platform`
- Railway deployment: backend, PostgreSQL, Redis, Celery worker, and frontend are all **Online** in the production environment.
- Live frontend: `https://zoological-mercy-production-8922.up.railway.app`
- Live backend: `https://ai-engineering-platform-production.up.railway.app`

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
- Issue intelligence hardening with open/closed/all state selection, Redis caching, bounded retries, and mocked GitHub tests
- Explicit documentation generation preview for one bounded source file, with citation metadata, audience control, provider usage metadata, and no automatic saving
- Persisted citation counts for query events and feedback, with citation coverage and average citation metrics in quality reporting
- Best-effort Redis-backed API rate limiting and configurable request-size protection with structured `429` and `413` error payloads
- Standardized structured error details for provider outages, GitHub issue failures, and unavailable PR refs, with frontend parsing support
- Expanded boundary tests for GitHub retries/filtering, parser fallbacks, schema errors, dependency graph behavior, caching keys, and PR diff analysis
- Opt-in heuristic secret scan with redacted file/line findings and no automatic indexing-time execution
- GitHub Actions CI for backend tests, frontend production builds, and repository hygiene checks without provider secrets
- Docker readiness checks for the backend and dependency-gated frontend startup; README quick-start and security notes refreshed
- Backend status metadata now reflects Phase 3 and `/health` checks both PostgreSQL and Redis readiness
- Production deployment runbook added at `docs/deployment.md`; Railway production deployment is now active.
- Railway frontend uses a same-origin `/api` proxy backed by the private `BACKEND_URL` build variable, avoiding browser cross-origin failures.
- Railway worker runs Celery with `--concurrency=2` and uses Railway-linked PostgreSQL and Redis variables.
- Backend and frontend Docker build contexts now exclude local secrets, Git metadata, caches, and generated dependencies
- Railway-specific service mapping and deployment checklist added at `docs/railway-deployment.md`
- Accessibility polish across Phase 3 panels: labels for controls, visible keyboard focus states, and live alert/status regions
- RAG evaluation endpoint with Recall@K and MRR
- RAG evaluation UI supporting multiple benchmark cases
- Per-case and average retrieval latency in evaluation results
- Reviewable starter benchmark template at `docs/rag-benchmark.example.json`
- CI-friendly benchmark runner at `backend/scripts/run_rag_benchmark.py` with optional quality thresholds
- Expanded starter RAG benchmark to 10 repository questions with strict benchmark-file validation and runner tests
- Added expected-file hit rate to RAG evaluation summaries and the evaluation dashboard
- Added separate lower rate limits for provider/GitHub/scan-heavy endpoints
- Added ASGI middleware tests for request-size rejection, route-specific throttling, and Redis fail-open behavior
- Added CI validation for benchmark structure through the benchmark runner

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

2. **Issue intelligence hardening** — complete
   - Added bounded retry/backoff for transient GitHub failures and clearer rate-limit guidance.
   - Added five-minute Redis caching keyed by repository index version, issue state, and limit.
   - Added open, closed, and all issue states in the API and UI.
   - Added mocked GitHub response tests and invalid-state validation.

3. **Controlled documentation generation** — preview milestone complete
   - Generate a draft only on explicit user action for one selected source file.
   - Return citation metadata and show the draft in the UI before any save action.
   - Enforce a 50 KB source limit and a 1,200-token output limit; no automatic file writes are performed.
   - Future work: add an explicit user-approved export/save flow with a diff and confirmation.

4. **RAG evaluation expansion**
   - Expanded the starter benchmark to 10 representative questions and added validation tests for benchmark files.
   - Remaining: tailor expected files to each target repository and expand to 10–20 questions per target repository.
   - Remaining: add answer-level citation hit rate and helpful-rate reporting; retrieval evaluation now measures Recall@K, MRR, expected-file hit rate, and latency.
   - CI now validates the benchmark template; remaining: run retrieval evaluation in CI against a seeded PostgreSQL/pgvector repository.

### Phase 3B — Quality and safety

1. Add mocked integration tests for GitHub, Redis, indexing, search, and issue analysis — core GitHub, parser, graph, cache, schema, and PR-analysis boundaries are covered; database-backed endpoint tests remain.
2. Add API rate limits and request-size limits where appropriate — baseline, endpoint-specific protection, and ASGI middleware tests complete.
3. Add structured error codes and user-facing retry guidance — baseline provider, GitHub, PR, rate-limit, and request-size errors complete.
4. Add basic secret-pattern scanning as an opt-in, clearly labeled heuristic — complete for common private-key, AWS-key, and assignment-style API-key patterns; future work may add more languages and false-positive controls.
5. Improve accessibility and responsive behavior across the repository detail page — baseline labels, focus states, live regions, and responsive Phase 3 controls complete; a full WCAG audit remains future work.

### CI status

The repository now has `.github/workflows/ci.yml`. It uses mock providers for backend tests, does not require Gemini or GitHub secrets, and runs on pushes to `master` and pull requests targeting `master`.

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
3. **Deployment target:** Railway is selected and active; next deployment work is custom domains, monitoring, backups, and spend controls.
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
- After the issue intelligence milestone: `28 passed`
- After the boundary-test milestone: `32 passed, 1 skipped` (Tree-sitter-specific test is dependency-aware)
- After the secret-scan milestone: `34 passed, 1 skipped`
- Frontend build: successful
- Redis: `PONG`
- Backend health: `database=healthy`

Before every commit:

- Do not expose secrets in output or source files.
- Add or update tests for backend behavior.
- Run the backend test suite and frontend build.
- Verify live endpoints inside the backend container when host networking is unavailable.
- Commit in a focused unit and push to `master` only after verification.
