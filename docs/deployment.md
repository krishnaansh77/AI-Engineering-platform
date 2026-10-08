# Deployment Runbook

This document describes the production deployment requirements for the AI Software Engineering Intelligence Platform. It does not deploy anything by itself.

For the selected hosting target, see the [Railway deployment checklist](railway-deployment.md).

## Required services

- FastAPI backend
- Celery worker
- PostgreSQL with the pgvector extension
- Redis
- Next.js frontend
- Persistent storage for cloned repositories, or a replacement object-storage strategy

The backend and worker must use the same database, Redis, and repository storage configuration.

## Required configuration

Set these values in the hosting provider's secret/configuration store, never in Git:

```text
DATABASE_URL
REDIS_URL
CELERY_BROKER_URL
CELERY_RESULT_BACKEND
LLM_PROVIDER
EMBEDDING_PROVIDER
GOOGLE_API_KEY or OPENAI_API_KEY
GITHUB_PAT                 # only for private repositories or higher API limits
GITHUB_WEBHOOK_SECRET      # only when GitHub webhooks are enabled
SECRET_KEY
CORS_ORIGINS
```

Use `LLM_PROVIDER=mock` and `EMBEDDING_PROVIDER=mock` only for local tests. Production requires a configured provider and a vector dimension matching the selected embedding model.

## Deployment sequence

1. Build and publish the backend and frontend images.
2. Start PostgreSQL and Redis.
3. Run database migrations:

   ```bash
   alembic upgrade head
   ```

4. Start the backend and wait for `/health` to report healthy database and Redis dependencies.
5. Start the Celery worker.
6. Start the frontend with `NEXT_PUBLIC_API_URL` pointing to the backend URL.
7. Connect a test public repository and verify indexing, search, Q&A, citations, and feedback.
8. Configure GitHub webhooks only after the signed webhook endpoint has been tested.

## Health and smoke checks

```bash
curl -fsS "$BACKEND_URL/health"
curl -fsS "$BACKEND_URL/"
```

The health response should report `status: healthy`, `database: healthy`, and `redis: healthy`.

## Production safeguards

- Put the frontend and backend behind HTTPS.
- Restrict `CORS_ORIGINS` to the deployed frontend origin.
- Do not expose PostgreSQL or Redis publicly.
- Set provider budgets and monitor quota failures.
- Keep repository clone storage persistent and access-controlled.
- Verify both Docker build contexts exclude `.env`, Git metadata, caches, and generated dependencies before publishing images.
- Run the opt-in secret scan before indexing sensitive repositories, understanding that it is heuristic.
- Configure log retention without logging API keys, PATs, prompts containing secrets, or generated source unnecessarily.

## Rollback

1. Stop traffic to the new backend/frontend release.
2. Roll back images to the previous known-good versions.
3. Do not downgrade the database automatically. Review migration compatibility first.
4. Re-run `/health` and a repository search smoke test.
5. Investigate failed worker jobs before resuming indexing.

## Current status

Deployment has not been performed. The local Docker Compose stack is the verified development environment. A hosting target and domain are still required before a real deployment can be executed.
