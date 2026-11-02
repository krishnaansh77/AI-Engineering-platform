# AISE Platform — Continuation Handoff

This file is the source of truth for continuing the redesign if the account,
model, or Codex session changes. Update it after every meaningful milestone.

## User-approved direction

- Redesign the product so every visible screen reflects a real working feature.
- Replace the TypeScript frontend with JavaScript, HTML, and CSS.
- Replace the FastAPI API layer with Django/Django REST Framework.
- Deploy the frontend on Vercel.
- Keep production available during the migration; do not remove the current
  Railway deployment until the replacement passes the acceptance checks.
- Preserve the existing Python analysis services where possible instead of
  rewriting proven indexing, parsing, retrieval, GitHub, and LLM logic.
- Make the repository easy for another AI to resume without chat history.

## Current repository state

- Workspace: `/Users/ayushpatel/AI Software Engineering Intelligence Platform`
- Git branch: `master`
- Current production frontend:
  `https://zoological-mercy-production-8922.up.railway.app`
- Current production backend:
  `https://ai-engineering-platform-production.up.railway.app`
- Redesigned Vercel frontend alias:
  `https://ai-engineering-platform-frontendv2-topaz.vercel.app`
- Existing deployment services: frontend, FastAPI backend, Celery worker,
  PostgreSQL/pgvector, and Redis on Railway.
- Local Docker stack is running with FastAPI, PostgreSQL/pgvector, Redis, and
  Celery worker. The redesigned frontend is served locally from
  `frontend_v2/` at `http://localhost:3000` for browser smoke testing.
- The current Vercel production alias is live and verified:
  `https://ai-engineering-platform-frontendv2-topaz.vercel.app`.
- Django compatibility service added under `django_backend/`. It exposes
  `/health`, forwards uncovered `/api/*` routes to FastAPI, and now owns the
  migrated auth, workspace, repository, structural-intelligence, and Git
  intelligence routes. It is intentionally not wired into production yet.
- The migration and deployment changes are committed on `master`. Preserve
  unrelated user changes if they appear in a later working tree.

## Target architecture

```text
Vercel
  vanilla JS + HTML + CSS frontend
          |
          | same-origin API proxy / HTTPS
          v
Railway
  Django + Django REST Framework API
  Celery worker
  PostgreSQL + pgvector
  Redis
          |
          v
  Existing Python services for parsing, indexing, retrieval, GitHub,
  architecture, history, issue intelligence, documentation, and LLM providers
```

Vercel should host the browser application only. The Django API, Celery,
database, Redis, and repository workspace require a server/worker environment
and should remain on Railway or an equivalent service.

## Migration strategy

1. Inventory the existing API contract and map every current frontend screen to
   a real backend capability.
2. Add Django as a compatibility API alongside FastAPI; do not remove FastAPI
   yet.
3. Reuse existing service modules and database schema wherever practical.
4. Build the vanilla JS/HTML/CSS frontend against the compatibility contract.
5. Add automated API and browser smoke tests for every screen and critical
   action.
6. Deploy the new frontend to a Vercel preview and point it at the Django
   staging API.
7. Cut production over only after the acceptance checklist below passes.
8. Retire FastAPI only after the Django API has parity and production has been
   stable.

### Completed migration slices

- [x] Added continuation handoff and migration source of truth.
- [x] Added Django compatibility service scaffold with health endpoint and
  restricted API proxy.
- [x] Confirmed the scaffold is syntactically valid with Python compilation.
- [x] Added an opt-in `django` Docker Compose profile and Django Dockerfile;
  the existing default Compose stack is unchanged.
- [x] Migrated read-only repository list/detail routes to native Django using
  unmanaged models against the existing PostgreSQL schema, including bearer
  token validation and workspace visibility filtering.
- [x] Added the first vanilla JavaScript/HTML/CSS redesign under
  `frontend_v2/`, with functional auth, dashboard, repository connect/detail,
  re-index, chat, account/usage, and documentation routes backed by the API.
- [x] Added working workspace creation and owner/admin rename controls to the
  redesigned account screen.
- [x] Migrated registration, login, and current-user identity routes to native
  Django, preserving the existing PBKDF2 password format and JWT claims.
- [x] Migrated authenticated workspace listing to native Django for the account
  screen.
- [x] Added native Django workspace creation and owner/admin rename endpoints;
  member and invitation management remain to be migrated.
- [x] Added native Django workspace invitations, revocation, acceptance, member
  listing, role changes, and member removal with hashed seven-day tokens and
  owner/admin safeguards.
- [x] Added native Django repository connect, re-index, and delete routes with
  workspace visibility and mutation authorization; indexing is dispatched to
  the existing Celery task through Redis.
- [x] Added redesigned frontend controls for repository re-index and guarded
  deletion.
- [x] Migrated repository statistics, indexed file inventory, and bounded
  secure source previews to native Django; the Django service now mounts the
  shared repository volume in Compose.
- [x] Wired the redesigned repository page to show indexed files and open
  bounded source previews through the native Django routes.
- [x] Added native Django structural intelligence services and routes for file
  dependency graphs, architecture layers, test relationships, repository tour,
  technical-debt signals, and documentation quality.
- [x] Migrated Git history, latest-change analysis, commit analysis, and base/
  head comparison to native Django using the shared clone volume and GitPython.
- [x] Added the first working dependency graph visualization to `frontend_v2/`:
  Cytoscape.js focus-plus-context rendering, one-time animated CoSE layout,
  direct import/dependant tracing, layer-aware node shapes, fit/re-layout/clear
  controls, and reduced-motion behavior. Design rationale and research sources
  are recorded in `docs/graph-visualization.md`.
- [x] Added Vercel API routing under `frontend_v2/vercel.json`; `/api/*` is
  explicitly rewritten to the live FastAPI API (which has root-level routes)
  before the SPA fallback. Replace the destination with
  `https://<django-origin>/api/:path*` when the Django Railway service gets a
  public domain. The browser continues to call same-origin `/api/*`.
- [x] Deployed `frontend_v2` to Vercel and verified the live alias loads. The
  unauthenticated `/api/auth/me` probe returns the expected `401 Authentication
  required` response through the Vercel rewrite.
- [!] Railway rejected creating a separate Django service because the current
  Free plan reached its resource provision limit. Existing FastAPI, frontend,
  worker, Redis, and Postgres production services were left untouched.
- [x] Added honest frontend indexing feedback: pending/indexing repositories
  show a live status notice and refresh automatically every five seconds until
  the repository reaches a terminal state. Connect and re-index actions now
  expose a disabled in-progress state while their request is running.
- [x] Added repository-tour and latest-change panels to the redesigned
  repository screen, including direct source-preview actions for key files.
- [x] Hardened the legacy repository response contract so older rows with
  missing branch, metadata, or count defaults no longer turn `/repos/connect`
  into a 500 response. Added a regression test; the containerized backend suite
  passed with 64 tests passed and 4 skipped before the graph regression.
- [x] Added Alembic migration `008_backfill_repository_stats` to repair legacy
  repository counters and indexing timestamps from `source_files` and
  `code_chunks`; the local Eternixx1 record now reports 26 files and 101 chunks.
- [x] Fixed dependency-graph resolution for common Next.js `@/*` and `~/*`
  aliases and improved frontend layer classification for `app/`, `components/`,
  `pages/`, `hooks/`, and `lib/`; the local Eternixx1 graph now resolves 15
  relationships instead of zero.
- [x] Reworked the V2 graph visualization in commit `c8adf3e`: the default is
  now a deterministic connected-file architecture map with stable layer
  columns, readable path-aware labels, visible edges, and an explicit All files
  scope for isolated files. The local Eternixx1 view shows 16 connected files,
  15 imports, and 10 isolated files hidden by default.
- [x] Replaced the default V2 graph entry point with a compact Repository story
  map: a one-sentence summary, a main row for **Screens people use → Work after
  a click → Data and outside services** when those stages exist, and a compact
  support row for shared building blocks, app-frame files, tests, and setup.
  It is derived from conservative folder heuristics and is intentionally a
  conceptual explanation rather than a claim about every exact import. A
  separate **Developer file map** tab retains Cytoscape import detail. The local
  Eternixx1 smoke test verified the compact blueprint and stage drill-down; the
  backend suite remains `65 passed, 4 skipped`.
- [x] Started the Phase 4 feedback loop in the redesigned frontend: chat answers
  now expose Helpful/Not helpful controls backed by the protected feedback API,
  and repository detail shows the aggregate helpful rate and rating count.
- [x] Added the first no-cost Phase 4 observability surface to the redesigned
  Account page. It aggregates live API health, query count/latency, recorded
  tokens, estimated cost, and answer helpful rate across accessible repositories.
- [x] Added an opt-in V2 Security quick check that calls the existing heuristic
  secret-scan endpoint and displays only redacted findings, file locations, and
  confidence. Full Bandit/ESLint security integration remains open.

### No-cost production decision

- Keep the Vercel frontend on the current free deployment and keep the existing
  Railway FastAPI service as the production API. This is the stable, verified
  path and does not require a plan upgrade or payment.
- Do not delete or repurpose an existing Railway service just to make room for
  Django; that could take down the working production API, worker, database, or
  Redis service.
- The native Django compatibility layer remains in the repository and is ready
  for a future free service slot. When a free slot is available, deploy
  `django_backend/`, give it a public domain, verify its health and contract
  checks, then change the Vercel `/api/:path*` destination in
  `frontend_v2/vercel.json` to `https://<django-origin>/api/:path*`.
- No paid upgrade, paid add-on, custom domain, or secret was added as part of
  this deployment.

### Verification recorded on 2026-11-02

- Vercel root: HTTP 200.
- Vercel `/api/health`: HTTP 200; database and Redis healthy.
- Vercel `/api/auth/me`: HTTP 401 with the expected authentication error.
- Vercel `/api/repos`: HTTP 401 with the expected authentication error.
- `django_backend/` Python compilation: passed.
- Frontend JavaScript syntax check: passed.
- Full containerized backend pytest: `65 passed, 4 skipped`.
- Local frontend JavaScript syntax check: passed.
- Local browser smoke checks: authenticated dashboard, repository detail,
  corrected stats, dependency graph, source preview, and chat route loaded.

### Immediate next slice

- [x] Add Django contract tests for health, auth forwarding, JSON forwarding,
  timeout, and unavailable-backend errors.
- [x] Add a Django service Dockerfile and Compose profile without changing the
  current default production path. *(See `docker-compose.yml`.)*
- [x] Migrate one read-only repository endpoint from proxy to Django REST
  Framework. Native Django list/detail routes are in place; database-backed
  response parity verification remains.
- [x] Migrate the core authentication endpoints to native Django. Database and
  production parity verification remain.
- [x] Migrate authenticated workspace listing to native Django. Workspace
  mutation and invitation routes remain.
- [x] Migrate workspace creation and rename to native Django. Member and
  invitation management remain.
- [x] Migrate workspace invitations and member management to native Django.
  Database-backed behavior still needs integration verification.
- [x] Migrate repository connect, re-index, and delete to native Django. Celery
  and database integration verification remain.
- [x] Migrate repository stats, file inventory, and source preview to native
  Django. Database-backed verification remains.
- [x] Migrate structural intelligence summaries to native Django. Database-backed
  graph parity verification remains.
- [x] Migrate Git history and commit comparison to native Django. Clone-volume
  integration verification remains.
- [x] Start the frontend shell conversion to JavaScript/HTML/CSS while keeping
  the same API contract. Initial auth, dashboard, repository, chat, account,
  and documentation routes are in `frontend_v2/`; feature parity and browser
  verification remain.
- [x] Start Phase 4 feedback-loop delivery in `frontend_v2/`: answer ratings
  and repository-level feedback summary are wired to the existing API.
- [x] Added a no-cost observability surface for query count, latency, token usage,
  estimated cost, health, and feedback trends on the redesigned Account page.
- [x] Added structured JSON request logs, safe correlation IDs, response headers,
  and request duration/status fields without adding paid infrastructure.
- [x] Added a CI static security job that runs Bandit high-confidence checks on
  backend Python source.
- [ ] Phase 4 next: add OpenTelemetry-compatible tracing and a trace viewer/export
  path, keeping the no-cost deployment constraint. Frontend ESLint security rules
  are also still open.
- [ ] Phase 4 later: finish Django database-backed parity verification before
  attempting any production API cutover; the current Railway free-plan limit
  still blocks provisioning a separate Django service.

## Feature parity checklist

- [ ] Authentication: register, login, logout/session expiry, current user
- [ ] Workspace creation, switching, invitations, roles, member removal
- [ ] Repository connect, list, detail, re-index, delete
- [ ] Indexing progress and error recovery
- [x] Codebase chat with citations and feedback
- [ ] Semantic/keyword code search
- [ ] Dependency graph and impact analysis
- [ ] Architecture explorer
- [ ] Git history and commit analysis
- [ ] PR/branch comparison
- [ ] GitHub issue listing and issue analysis
- [ ] Repository tour
- [ ] Documentation inventory and quality signals
- [ ] Documentation preview, download, and guarded GitHub save
- [ ] Technical debt and test intelligence
- [ ] Optional secret scan with redaction
- [ ] RAG evaluation, latency, citation, and usage metrics
- [ ] Markdown repository report export
- [ ] Accessible loading, error, empty, disabled, and success states
- [ ] Responsive layout for desktop and narrow screens

## Required secrets and external access

No secrets are needed to begin the code migration. Do not paste secrets into
chat or commit them. When deployment work begins, configure them through the
hosting provider's secret UI.

Likely required values:

- `SECRET_KEY`
- `DATABASE_URL` for PostgreSQL/pgvector
- `REDIS_URL`
- One LLM provider key: Gemini, OpenAI, or another supported provider
- An embedding provider key/model configuration
- `GITHUB_PAT` for private repositories or higher API limits, or GitHub App
  credentials for the preferred production flow
- Django allowed hosts, CORS/CSRF origins, and frontend API base URL
- Vercel project/team access when the Vercel connector is available
- `DJANGO_API_URL` in Vercel, set to the Railway Django service origin without
  `/api` appended

## Definition of done

- The new frontend is deployed on Vercel.
- Django API and workers are deployed and healthy on Railway.
- Every feature in the parity checklist has a working UI path or is explicitly
  marked unavailable with a truthful explanation.
- No screen contains placeholder buttons or fake success states.
- Backend tests, frontend build, API smoke tests, and browser smoke tests pass.
- Production health checks, authentication, repository indexing, chat, and one
  end-to-end intelligence workflow are verified after deployment.
- This handoff file and `PROJECT_PLAN.md` describe the actual state, not an
  aspirational roadmap.

## Resume instructions for another AI

1. Read this file, `PROJECT_PLAN.md`, `README.md`, and `git status`.
2. Preserve unrelated or pre-existing user changes.
3. Inspect the latest commit and update this file before making a large
   architectural change.
4. Run the smallest relevant tests before and after each migration slice.
5. Never deploy uncommitted redesign work without explicit user approval.
6. If an API key, Vercel team, GitHub installation, or database is required,
   ask the user for access instructions—not the secret value in chat.

*Last updated: 2026-11-02*
