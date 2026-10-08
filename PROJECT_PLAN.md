# AI Software Engineering Intelligence Platform — Project Plan

This file is the practical handoff document for the project. It records what is already working, what is intentionally incomplete, and the order for future development.

## Current status

- Phase 1 — Foundation & Core RAG: **complete**
- Phase 2 — Repository Intelligence: **complete**
- Phase 3 — Developer Productivity: **in progress**
- Latest verified baseline: **42 backend tests passing** and the Next.js production build passing
- Repository: `https://github.com/krishnaansh77/AI-Engineering-platform.git`
- Local workspace: `/Users/ayushpatel/AI Software Engineering Intelligence Platform`
- Railway deployment: backend, PostgreSQL, Redis, Celery worker, and frontend are all **Online** in the production environment.
- Live frontend: `https://zoological-mercy-production-8922.up.railway.app`
- Live backend: `https://ai-engineering-platform-production.up.railway.app`
- Latest production verification: Railway frontend deployment `07eed5b` is active; the public dashboard and repository detail page show the Phase 3 label and expose accessible headings, labels, navigation, buttons, form controls, and status regions.

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
- Added a deterministic PostgreSQL/pgvector + Redis seeded benchmark job in CI
- Surfaced answer citation coverage in the repository quality dashboard
- Added accessible labels, live regions, alert semantics, and selection states across core repository and chat controls
- Added explicit user-triggered Markdown export for generated documentation previews without automatic repository writes
- Added guarded GitHub documentation saves: diff preview first, explicit confirmation required, documentation-only paths, bounded content, and optimistic SHA protection against stale overwrites
- Added global visible keyboard focus styling and reduced-motion support
- Added form associations, validation announcements, and error visibility for repository and intelligence panels
- Completed a static accessibility pass over interactive controls; fixed the remaining issue-panel error-state and feedback-control semantics
- Fixed indexing progress step updates and exposed the active step through an accessible live status
- Added helpful versus unhelpful citation coverage breakdowns for feedback-driven quality analysis
- Added real PostgreSQL/pgvector endpoint smoke tests for retrieval evaluation and feedback citation aggregation, executed in the seeded CI job
- Added a PostgreSQL-backed indexing pipeline integration test with mocked external services
- Added reusable RAG evaluation documentation for repository-specific benchmarks
- Added quota-safe indexing behavior: when an already-indexed repository hits an embedding-provider quota, its previous complete index remains available with an explicit retry warning instead of becoming unusable.
- Added and validated `docs/rag-benchmark.ai-engineering-platform.json` with 10 questions for this repository. Baseline against the seeded local index: Recall@5 **0.60**, MRR **0.545**, expected-file hit rate **0.80**, average retrieval latency **712.87 ms**.

Phase 3 feature work is complete. One provider-dependent retrieval validation remains; the browser accessibility smoke check, repository benchmark authoring, retrieval improvement, and quota resilience are complete.
- Phase 4 — Production & Advanced Capabilities: **in progress**

## Important current behavior and limitations

- Issue intelligence depends on GitHub API connectivity. Public repositories can work without a token; private or rate-limited access needs `GITHUB_PAT` in the local `.env` file.
- Never paste API keys or PATs into chat or commit them. Put them only in local `.env`, which is ignored by Git.
- Documentation and test coverage are heuristic signals, not replacements for runtime coverage or human review.
- Commit impact analysis uses the files available in the local shallow clone.
- Formal RAG evaluation now has a repository-specific 10-case benchmark; the current baseline is recorded above. Metadata-aware ranking for exact file-path and symbol queries is now implemented; the benchmark should be rerun after the Gemini embedding quota resets because the attempted full re-index was rate-limited.
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

3. **Controlled documentation generation** — save flow complete
   - Generate a draft only on explicit user action for one selected source file.
   - Return citation metadata and show the draft in the UI before any save action.
   - Enforce a 50 KB source limit and a 1,200-token output limit; no automatic file writes are performed.
   - Added explicit user-approved Markdown export/download and a repository save flow with a unified diff, explicit confirmation, bounded documentation paths, and current-blob SHA protection.

4. **RAG evaluation expansion**
   - Expanded the starter benchmark to 10 representative questions and added validation tests for benchmark files.
   - Added reusable instructions for tailoring expected files and running 10–20 question benchmarks per target repository, plus a verified benchmark for this platform itself.
   - Answer-level citation coverage, helpful-rate reporting, and helpful-versus-unhelpful citation breakdowns are now surfaced in the quality dashboard; query responses now also report the fraction of returned citations explicitly referenced by the answer, with UI visibility in chat. The first 10-case baseline identifies evaluation-ranking and secret-scan retrieval as the main tuning gaps.
   - CI validates the benchmark template and runs retrieval evaluation against a seeded PostgreSQL/pgvector repository.

### Phase 3B — Quality and safety

1. Add mocked integration tests for GitHub, Redis, indexing, search, and issue analysis — core GitHub, parser, graph, cache, schema, PR-analysis, retrieval-evaluation, feedback, and indexing boundaries are covered in unit or database-backed CI tests.
2. Add API rate limits and request-size limits where appropriate — baseline, endpoint-specific protection, and ASGI middleware tests complete.
3. Add structured error codes and user-facing retry guidance — baseline provider, GitHub, PR, rate-limit, and request-size errors complete.
4. Add basic secret-pattern scanning as an opt-in, clearly labeled heuristic — complete for common private-key, AWS-key, and assignment-style API-key patterns; future work may add more languages and false-positive controls.
5. Improve accessibility and responsive behavior across the repository detail page — static audit complete, and live browser verification completed for navigation, headings, labels, buttons, disabled states, status regions, and repository controls. A full automated WCAG audit remains optional hardening rather than a Phase 3 blocker.

### CI status

The repository now has `.github/workflows/ci.yml`. It uses mock providers for backend tests, does not require Gemini or GitHub secrets, and runs on pushes to `master` and pull requests targeting `master`.

### Phase 4 — Production and advanced capabilities

- Authentication and RBAC — foundation complete: user accounts, salted PBKDF2 password hashes, JWT access tokens, role field, registration/login/identity endpoints, Alembic migrations `003_users` and `004_repository_owners`, repository ownership, and a frontend account screen. Repository and query APIs now require authentication; authenticated members can connect, re-index, and delete their own repositories; admins/owners retain global mutation access. The frontend redirects unauthenticated API requests to `/auth`. Ownership migration is applied locally and Alembic is at head.
- Authentication hardening — complete: `/auth/*` requests now use a dedicated low per-minute Redis rate limit, with regression coverage for login throttling and existing API limits.
- Multi-repository workspaces — foundation and basic management complete: migration `005_workspaces` adds workspaces and memberships, new accounts receive a default owner workspace, newly connected repositories are attached to it, `/auth/workspaces` plus the account page expose memberships and roles, and migration `006_workspace_invitations` adds secure seven-day hashed-token invitations with email-matched one-time acceptance. Authenticated users can now create workspaces, and workspace owners/admins can rename them from the account page.
- Workspace management remains in progress: active workspace switching and repository listing/connection are workspace-scoped, and repository-specific API/query routes now enforce owner or workspace-membership access; pending-invitation management/revocation and richer member management are future extensions.
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
