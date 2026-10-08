# Railway Deployment Checklist

Railway does not run the local Compose file as one process. Each Compose service becomes a Railway service, with private networking replacing the local Compose network.

## Services to create

| Railway service | Root directory | Start command | Public? |
|---|---|---|---|
| `backend` | `/backend` | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` | Yes |
| `worker` | `/backend` | `celery -A app.workers.celery_app worker --loglevel=info --concurrency=2` | No |
| `frontend` | `/frontend` | `npm run start -- --hostname 0.0.0.0 --port $PORT` | Yes |
| `postgres` | Railway PostgreSQL template | managed | No |
| `redis` | Railway Redis template | managed | No |

Use the repository’s existing Dockerfile from each service root. Railway supports isolated monorepo services with separate root directories.

## Backend variables

Set these on both `backend` and `worker`:

```text
DATABASE_URL=${{postgres.DATABASE_URL}}
REDIS_URL=${{redis.REDIS_URL}}
CELERY_BROKER_URL=${{redis.REDIS_URL}}
CELERY_RESULT_BACKEND=${{redis.REDIS_URL}}
LLM_PROVIDER=gemini
EMBEDDING_PROVIDER=gemini
GOOGLE_API_KEY=<Railway secret>
GEMINI_LLM_MODEL=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=models/text-embedding-004
EMBEDDING_DIMENSION=768
GITHUB_PAT=<optional Railway secret>
GITHUB_WEBHOOK_SECRET=<optional Railway secret>
SECRET_KEY=<new production secret>
APP_ENV=production
REPOS_CLONE_DIR=/repos
```

Attach a persistent Railway volume to `backend` and `worker` at `/repos` if repository clones must survive restarts.

## Frontend variables

```text
NEXT_PUBLIC_API_URL=https://<backend-public-domain>
```

After the frontend domain is generated, set the backend variable:

```text
CORS_ORIGINS=https://<frontend-public-domain>
```

## Deployment order

1. Create an empty Railway project.
2. Add PostgreSQL and Redis templates.
3. Add the backend service from GitHub with root directory `/backend`.
4. Configure backend variables and add its public domain.
5. Run `alembic upgrade head` as a one-time backend migration command.
6. Add the worker service from the same repository with root directory `/backend`.
7. Add the frontend service with root directory `/frontend`.
8. Restrict backend `CORS_ORIGINS` to the frontend domain.
9. Verify `/health`, indexing, search, Q&A, citations, feedback, and worker indexing.

## CLI commands after authentication

```bash
railway link
railway environment edit --service-config backend source.rootDirectory /backend
railway environment edit --service-config worker source.rootDirectory /backend
railway environment edit --service-config frontend source.rootDirectory /frontend
```

Do not put secret values in shell history or commit them. Prefer Railway’s Variables UI.

## Current blocker

No Railway project has been created or authorized from this workspace yet. Deployment can begin once Railway CLI/dashboard access is authenticated and the destination project is selected.
