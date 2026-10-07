# Architecture — Phase 1

## System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         Next.js Frontend                        │
│  Connect Repo  │  Repo Dashboard  │  Chat Q&A + Citations       │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP (REST)
┌────────────────────────────▼────────────────────────────────────┐
│                      FastAPI Backend                            │
│                                                                 │
│  /repos         /repos/{id}/query       /webhook/github        │
└──────────┬──────────────────┬───────────────────────┬───────────┘
           │                  │                       │
    ┌──────▼──────┐   ┌───────▼──────┐      ┌────────▼────────┐
    │  Indexing   │   │  Retrieval   │      │  Celery Worker  │
    │  Pipeline   │   │  Service     │      │  (async tasks)  │
    └──────┬──────┘   └───────┬──────┘      └─────────────────┘
           │                  │
    ┌──────▼──────┐   ┌───────▼──────────────────────────────┐
    │  Tree-sitter│   │         Hybrid RAG                   │
    │  Parser     │   │                                      │
    │  Python     │   │  Vector Search (pgvector cosine)     │
    │  JS / TS    │   │        +                             │
    └──────┬──────┘   │  BM25 Keyword Search (rank-bm25)    │
           │          │        ↓                             │
    ┌──────▼──────┐   │  RRF Fusion (Reciprocal Rank Fusion) │
    │  Embedding  │   └───────┬──────────────────────────────┘
    │  Provider   │           │
    │  (abstract) │   ┌───────▼──────┐
    │  OpenAI     │   │  LLM Provider│
    └──────┬──────┘   │  (abstract)  │
           │          │  OpenAI      │
    ┌──────▼──────────▼─────────────┐
    │     PostgreSQL + pgvector     │
    │  repositories                 │
    │  source_files                 │
    │  code_chunks (+ embeddings)   │
    └───────────────────────────────┘
```

## Provider Abstraction

```
LLMProvider (ABC)
├── OpenAIProvider        ← Phase 1
└── AnthropicProvider     ← Phase 4

EmbeddingProvider (ABC)
├── OpenAIEmbeddingProvider   ← Phase 1
└── LocalEmbeddingProvider    ← Phase 4 (Ollama)
```

## Data Flow — Indexing

```
GitHub URL
    │
    ▼
GitHubService.clone_repository()
    │  (git clone with PAT)
    ▼
GitHubService.list_source_files()
    │  (.py / .js / .ts files only)
    ▼
ParserService.parse_file()
    │  (Tree-sitter AST → ParsedChunk[])
    │  chunks by function/class boundary
    ▼
EmbeddingService.embed_chunks()
    │  (OpenAI text-embedding-3-small)
    │  prefix: "code: {content}"
    ▼
PostgreSQL upsert
    │  source_files + code_chunks records
    │  embedding vector stored in pgvector
    ▼
Repository status → "ready"
```

## Data Flow — Q&A Query

```
User question: "Where is authentication implemented?"
    │
    ▼
EmbeddingService.embed_query()
    │  prefix: "query: {question}"
    ▼
    ├── Vector Search (pgvector cosine_similarity, top 20)
    └── BM25 Search (rank_bm25, top 20)
             │
             ▼
    RRF Fusion → top 5 chunks
             │
             ▼
    LLM Prompt Assembly
    │  System: "You are an expert SE assistant. Cite file/function/lines."
    │  Context: retrieved chunks formatted with file/symbol/line headers
    │  User: original question
             │
             ▼
    OpenAI GPT-4o
             │
             ▼
    QueryAnswer { answer, citations[] }
```

## Database Schema

```sql
repositories
  id UUID PK
  name TEXT
  full_name TEXT          -- e.g. "tiangolo/fastapi"
  github_url TEXT
  clone_path TEXT
  status TEXT             -- pending | indexing | ready | error
  languages JSONB
  frameworks JSONB
  file_count INT
  chunk_count INT
  last_indexed_at TIMESTAMPTZ
  created_at TIMESTAMPTZ

source_files
  id UUID PK
  repository_id UUID FK
  file_path TEXT          -- relative path
  language TEXT
  content_hash TEXT       -- SHA256, used for incremental re-index
  line_count INT
  size_bytes INT

code_chunks
  id UUID PK
  repository_id UUID FK
  file_id UUID FK
  file_path TEXT          -- denormalized for fast retrieval
  chunk_type TEXT         -- function | class | method | module
  symbol_name TEXT
  parent_symbol TEXT      -- class name if method
  start_line INT
  end_line INT
  content TEXT
  docstring TEXT
  imports JSONB
  embedding vector(1536)  -- pgvector

-- Index
CREATE INDEX ON code_chunks USING ivfflat (embedding vector_cosine_ops);
```
