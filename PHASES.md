# Phase Breakdown — AI Software Engineering Intelligence Platform

> This file details every phase, its features, tasks, and acceptance criteria.
> Cross-reference with `PROJECT_JOURNAL.md` for progress status.

---

## Phase 1 — Foundation & Core RAG

**Goal**: A working end-to-end system where a developer can connect a GitHub repo and ask questions about it with cited answers.

**Features from spec**: #1, #2, #3, #4, #5

**Status**: ✅ Complete

---

### 1.1 — Project Bootstrap

- [ ] Choose and finalize tech stack
- [ ] Set up monorepo structure (`backend/`, `frontend/`, `docs/`)
- [ ] Configure environment (`.env.example`, Docker Compose)
- [ ] Set up linting, formatting, pre-commit hooks
- [ ] Initialize PostgreSQL schema (repositories, files, chunks, embeddings metadata)

**Acceptance**: Project runs locally with `docker-compose up`

---

### 1.2 — GitHub Repository Integration (#1)

- [ ] GitHub OAuth app setup
- [ ] Repository connection API (`POST /repos/connect`)
- [ ] Clone or fetch repository via GitHub API / git clone
- [ ] Language and framework detection (heuristics on file extensions + config files)
- [ ] Read source files, README, docs/, config files
- [ ] Store repository metadata in PostgreSQL
- [ ] GitHub Webhook endpoint for push events → trigger re-index

**Acceptance**: Can connect a real GitHub repo and see it listed in the system

---

### 1.3 — Intelligent Code Parsing (#2)

- [ ] Integrate Tree-sitter (multi-language: Python, JavaScript/TypeScript, Go, Java, etc.)
- [ ] Extract from each file:
  - [ ] File path, language
  - [ ] Classes (name, line range, docstring)
  - [ ] Functions/methods (name, args, return type, line range, docstring)
  - [ ] Imports/dependencies
  - [ ] Top-level variables and constants
- [ ] Build an in-memory/DB representation of code structure
- [ ] Chunk code intelligently (by function/class boundaries, not fixed tokens)
- [ ] Store chunks in PostgreSQL with metadata (file, symbol, line range)

**Acceptance**: Parse a Python/JS file and return structured symbol table

---

### 1.4 — Vector Embeddings & Storage (#2, #4)

- [ ] Choose and set up vector database (Qdrant recommended)
- [ ] Embed code chunks using an embedding model
- [ ] Store embeddings with rich metadata (file, function, class, language, line range)
- [ ] Build embedding pipeline that runs after parsing
- [ ] Support incremental re-embedding when files change

**Acceptance**: Can run embedding pipeline on a repo and query similar chunks

---

### 1.5 — Hybrid RAG Retrieval (#4)

- [ ] Implement **vector search** against the vector DB
- [ ] Implement **BM25 / keyword search** (using Elasticsearch or BM25Okapi)
- [ ] Implement **fusion / reranking** (Reciprocal Rank Fusion or a cross-encoder reranker)
- [ ] Build unified retriever interface: `retrieve(query, repo_id, top_k) → List[Chunk]`
- [ ] Tune retrieval parameters

**Acceptance**: Given a query, retriever returns relevant code chunks from the repo

---

### 1.6 — AI Q&A with Citations (#3, #5)

- [ ] Build LLM prompt templates for code Q&A
- [ ] Assemble context from retrieved chunks into prompt
- [ ] Call LLM (OpenAI GPT-4 / Anthropic Claude)
- [ ] Parse LLM response and attach source citations:
  - File path
  - Function/class name
  - Line range
- [ ] Q&A API endpoint: `POST /repos/{id}/query`
- [ ] Response format:
  ```json
  {
    "answer": "...",
    "citations": [
      { "file": "src/auth/service.py", "symbol": "authenticate_user", "lines": "42-68" }
    ]
  }
  ```

**Acceptance**: Ask "Where is authentication implemented?" and get a correct, cited answer

---

### 1.7 — Basic Frontend (#3)

- [ ] Simple React/Next.js app
- [ ] Connect Repository page (GitHub URL input)
- [ ] Indexing status/progress page
- [ ] Chat interface for Q&A
- [ ] Display citations with clickable file/line references

**Acceptance**: Can use the system entirely through the UI

---

### Phase 1 Exit Criteria

- [ ] Connect a GitHub repo and index it end-to-end
- [ ] Ask 5 different natural-language questions about the repo and get correct, cited answers
- [ ] Re-indexing triggered by a GitHub webhook push event works
- [ ] Everything runs via `docker-compose up`

---

---

## Phase 2 — Software Engineering Intelligence

**Goal**: The system understands the *structure and history* of a codebase, not just its content.

**Features from spec**: #6, #7, #8, #9, #10

**Status**: ✅ Complete | **Prerequisite**: Phase 1 complete

---

### 2.1 — Dependency Graph (#7)

- [ ] Build file-level import graph from parsing output
- [ ] Build function-level call graph (who calls whom)
- [ ] Store graph in a graph-friendly format (NetworkX → export to Neo4j or store as adjacency in PG)
- [ ] API to query:
  - `GET /repos/{id}/graph/file/{path}/dependencies`
  - `GET /repos/{id}/graph/function/{name}/callers`
  - `GET /repos/{id}/graph/function/{name}/callees`

**Acceptance**: Given `auth/service.py`, return all files it imports and all files that import it

---

### 2.2 — Architecture Explorer (#6)

- [ ] Analyze module/package structure
- [ ] Infer high-level layers (frontend, API, service, data, infra) using heuristics + LLM
- [ ] Generate architecture summary: text + structured data
- [ ] API: `GET /repos/{id}/architecture`
- [ ] Frontend: Interactive architecture diagram (using D3.js or React Flow)

**Acceptance**: Given a full-stack repo, produce a sensible layered architecture diagram

---

### 2.3 — Git History Intelligence (#9)

- [ ] Parse Git log: commits, authors, timestamps, changed files, diffs
- [ ] Store commit data in PostgreSQL
- [ ] Index commit messages for semantic search
- [ ] Answer questions like:
  - "When was `authenticate_user` introduced?"
  - "What changed in `auth/` recently?"
- [ ] API: `GET /repos/{id}/history?file=...&function=...`

**Acceptance**: Ask "What changed in the auth module in the last 30 days?" and get a summary

---

### 2.4 — Change Impact Analysis (#8) ⭐⭐⭐

- [ ] Given a function or file, compute:
  - Direct callers (from call graph)
  - Indirect callers (transitive closure)
  - Files that import this module
  - Related tests (by naming convention + call graph)
  - Recently co-changed files (from Git history)
- [ ] Score and rank impacted components by likelihood of breakage
- [ ] API: `POST /repos/{id}/impact` with `{ "symbol": "authenticate_user" }`
- [ ] Frontend: Impact visualization — show affected nodes on dependency graph

**Acceptance**: Select a function, get a ranked list of components that may be affected

---

### 2.5 — Commit Intelligence (#10)

- [ ] On new commit (via webhook): detect changed files
- [ ] Compute impact analysis automatically
- [ ] Identify related tests
- [ ] Identify docs that may be affected
- [ ] Store per-commit analysis report
- [ ] API: `GET /repos/{id}/commits/{sha}/analysis`

**Acceptance**: Push a commit → system generates an automatic impact report

---

### Phase 2 Exit Criteria

- [ ] Dependency graph browsable in UI
- [ ] Architecture diagram auto-generated for a real repo
- [ ] Change impact analysis returns meaningful results for a function with many callers
- [ ] Git history Q&A works
- [ ] Commit analysis report generated automatically on push

---

---

## Phase 3 — Developer Productivity

**Goal**: The system actively helps developers do their job — PR reviews, onboarding, issue triage, documentation.

**Features from spec**: #11, #12, #13, #14, #15, #16, #17, #18

**Status**: ✅ Complete | **Prerequisite**: Phase 2 complete

---

### 3.1 — Pull Request Analysis (#11)

- [ ] GitHub PR webhook integration
- [ ] For each PR: summarize changes, identify affected components, suggest tests
- [ ] Post analysis as a GitHub PR comment (optional)
- [ ] API: `POST /repos/{id}/pr-analysis` with `{ "pr_number": 42 }`

---

### 3.2 — Code Explanation (#13)

- [ ] For any function/class, generate:
  - Purpose, Inputs, Outputs, Dependencies
  - Who calls it, what it calls
  - Related tests
  - Recent change history
- [ ] API: `GET /repos/{id}/explain?symbol=authenticate_user`

---

### 3.3 — Developer Onboarding Tour (#14)

- [ ] Auto-generate a structured "tour" of the repo:
  - Architecture overview
  - Important modules
  - Core workflows
  - Key APIs
  - Development setup guide
  - Recent significant changes
- [ ] API: `GET /repos/{id}/onboarding-tour`

---

### 3.4 — Issue / Ticket Intelligence (#15)

- [ ] GitHub Issues integration (OAuth scope: `repo`)
- [ ] For an issue: find relevant files, similar past issues, related commits
- [ ] API: `POST /repos/{id}/issue-analysis` with `{ "issue_number": 142 }`

---

### 3.5 — Semantic Code Search (#16)

- [ ] Dedicated search UI (not just Q&A)
- [ ] Search by meaning across all code symbols
- [ ] Filter by language, file path, symbol type
- [ ] API: `GET /repos/{id}/search?q=user+authentication`

---

### 3.6 — Test Intelligence (#17)

- [ ] Map source functions ↔ test functions (naming convention + call graph)
- [ ] Identify functions with no tests
- [ ] Show test coverage gaps
- [ ] API: `GET /repos/{id}/test-coverage?symbol=...`

---

### 3.7 — Technical Debt Indicators (#18)

- [ ] Compute per-file / per-function signals:
  - Coupling score (# dependencies)
  - Churn rate (commit frequency)
  - Complexity (function length, nesting depth)
  - Test coverage
  - Documentation staleness
- [ ] Aggregate into a "debt score"
- [ ] Dashboard: heatmap of problematic areas

---

### 3.8 — Automatic Documentation (#12)

- [ ] LLM-generate docstrings for undocumented functions
- [ ] Generate module-level READMEs
- [ ] Generate architecture documentation
- [ ] Export as Markdown

---

### Phase 3 Exit Criteria

- [ ] PR analysis produces a useful summary for a real PR
- [ ] Onboarding tour of an unfamiliar repo is coherent and accurate
- [ ] Semantic search finds `verify_credentials()` when searching "user authentication"
- [ ] Technical debt dashboard shows a meaningful heatmap
- [ ] Test gap detection correctly identifies untested functions

---

---

## Phase 4 — Production & Advanced

**Goal**: Make the system production-grade, scalable, secure, and advanced.

**Features from spec**: #19, #20, #21, #22, #23, #24, #25, #26, #27, #28, #29

**Status**: 🚧 In Progress | **Prerequisite**: Phase 3 complete

---

### 4.1 — Authentication & RBAC (#26)

- [x] User accounts (password registration/login; GitHub OAuth remains open)
- [x] Role-based access: member, owner/admin safeguards, and workspace roles
- [x] Per-repository permissions through ownership/workspace membership

---

### 4.2 — Observability (#27)

- [x] Structured JSON request logs with safe correlation IDs
- [x] Metrics: query latency, retrieval latency, LLM latency, token usage
- [x] Optional FastAPI request tracing over OTLP; disabled unless an endpoint is configured
- [x] Dashboard: no-cost account/workspace observability panel using live health, query, token, and feedback metrics

---

### 4.3 — RAG Evaluation (#24)

- [x] Build eval dataset: question → expected citations
- [x] Measure: Recall@K, MRR, expected-file hit rate, latency, and citation coverage
- [x] Run eval suite in CI against the seeded retrieval database
- [ ] Display eval results in admin dashboard

---

### 4.4 — Feedback Loop (#25)

- [x] 👍 / 👎 buttons on Q&A responses
- [x] Store negative feedback + query for later analysis
- [x] Use feedback to identify retrieval and citation-quality failures

---

### 4.5 — Multi-Repository Support (#20)

- [x] Workspace-scoped repository ownership and membership foundation
- [ ] Cross-repo dependency graph
- [x] Cross-repository hybrid code search for accessible ready repositories
- [x] Manifest-based downstream impact candidates across accessible repositories

---

### 4.6 — Repository Knowledge Graph (#22)

- [ ] Full Neo4j knowledge graph: Function → File → Module → Service → Repo → Commit
- [ ] Graph query API
- [ ] Graph visualization in UI

---

### 4.7 — Version-Aware RAG (#21)

- [ ] Index multiple branches/tags
- [ ] Answer queries scoped to a specific version
- [ ] "How did X change from v1 to v2?"

---

### 4.8 — Security Analysis Integration (#19)

- [x] Opt-in heuristic secret scan with redacted findings and an accessible V2 repository UI
- [x] Run Bandit high-confidence checks on backend Python source in CI
- [x] Add ESLint security rules for the vanilla JavaScript frontend in CI
- [ ] Display findings with: location, why it matters, relevant code, suggested fix

---

### 4.9 — Cost Optimization (#28)

- [x] Query result caching (Redis)
- [ ] Route simple queries to smaller/cheaper models
- [ ] Context compression before LLM call
- [x] Embedding reuse — skip re-embedding unchanged files

---

### 4.10 — Local LLM Mode (#29)

- [x] Ollama chat integration
- [x] Configurable: `LLM_PROVIDER=ollama`
- [x] Configurable: `EMBEDDING_PROVIDER=local` using Ollama `/api/embed`
- [ ] Test with Llama 3 / Mistral

---

### 4.11 — AI Agent Layer (#23)

- [ ] Orchestrator agent
- [ ] Specialized sub-agents: Code Agent, Git Agent, Docs Agent
- [ ] LangGraph or similar orchestration framework
- [ ] Tool definitions: search_code, get_file, get_history, get_impact, get_tests

---

### Phase 4 Exit Criteria

- [ ] System handles 10+ repositories simultaneously
- [ ] RAG evaluation suite passing defined thresholds
- [ ] RBAC enforced: developer cannot access repos they're not assigned to
- [ ] Local LLM mode works with Ollama + Llama 3
- [ ] Observability dashboard live

---

---

## Feature-to-Phase Matrix

| # | Feature | Phase |
|---|---------|-------|
| 1 | GitHub Repository Integration | Phase 1 |
| 2 | Intelligent Code Understanding | Phase 1 |
| 3 | AI Codebase Q&A | Phase 1 |
| 4 | Hybrid RAG | Phase 1 |
| 5 | Source Citations | Phase 1 |
| 6 | Architecture Explorer | Phase 2 |
| 7 | Dependency Graph | Phase 2 |
| 8 | Change Impact Analysis | Phase 2 |
| 9 | Git History Intelligence | Phase 2 |
| 10 | Commit Intelligence | Phase 2 |
| 11 | Pull Request Analysis | Phase 3 |
| 12 | Automatic Documentation | Phase 3 |
| 13 | Code Explanation | Phase 3 |
| 14 | Developer Onboarding | Phase 3 |
| 15 | Issue / Ticket Intelligence | Phase 3 |
| 16 | Semantic Code Search | Phase 3 |
| 17 | Test Intelligence | Phase 3 |
| 18 | Technical Debt Indicators | Phase 3 |
| 19 | Security Analysis Integration | Phase 4 |
| 20 | Multi-Repository Understanding | Phase 4 |
| 21 | Version-Aware RAG | Phase 4 |
| 22 | Repository Knowledge Graph | Phase 4 |
| 23 | AI Agent Layer | Phase 4 |
| 24 | RAG Evaluation | Phase 4 |
| 25 | Feedback Loop | Phase 4 |
| 26 | Authentication & RBAC | Phase 4 |
| 27 | Observability | Phase 4 |
| 28 | Cost Optimization | Phase 4 |
| 29 | Local LLM Mode | Phase 4 |
