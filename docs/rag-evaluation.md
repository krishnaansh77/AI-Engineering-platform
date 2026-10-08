# RAG evaluation

The platform evaluates retrieval without making an LLM call. Each benchmark case
contains a natural-language question and one or more file paths that should be
retrieved.

## Create a repository benchmark

Copy `docs/rag-benchmark.example.json` and replace the expected paths with files
from the indexed repository:

```json
{
  "name": "my repository benchmark",
  "top_k": 5,
  "cases": [
    {
      "question": "How is the database initialized?",
      "expected_files": ["src/database.py"]
    }
  ]
}
```

Use 10–20 questions covering API routes, indexing, configuration, error
handling, tests, and the most important domain features. Expected paths must be
repository-relative and should identify the files a developer would inspect to
answer the question.

## Run locally

Validate a benchmark without contacting a provider or API:

```bash
python backend/scripts/run_rag_benchmark.py \
  --validate-only \
  --benchmark docs/rag-benchmark.example.json
```

Run it against an indexed repository through the local backend:

```bash
PYTHONPATH=backend python backend/scripts/run_rag_benchmark.py \
  --repo-id <repository-uuid> \
  --base-url http://localhost:8000 \
  --benchmark docs/my-repository-benchmark.json \
  --min-recall 0.5 \
  --min-mrr 0.2
```

The result reports Recall@K, MRR, expected-file hit rate, matched files, and
retrieval latency. Use mock providers for repeatable, zero-cost CI runs; use a
real embedding provider only when measuring production retrieval quality.

For a fully local, zero-cost evaluation, set `EMBEDDING_PROVIDER=mock` before
indexing the repository and use the same provider for evaluation queries. Do
not mix mock query vectors with an index built using Gemini or OpenAI vectors.

## Interpreting results

- **Recall@K**: how many expected files were retrieved on average.
- **MRR**: how high the first expected file ranked.
- **Expected-file hit rate**: percentage of questions with at least one expected
  file retrieved.
- **Latency**: retrieval time only; it excludes LLM generation.

Retrieval metrics do not prove that an answer is correct. Pair them with answer
feedback and citation coverage from the repository quality dashboard.
