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
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
CELERY_BROKER_URL=${{Redis.REDIS_URL}}
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}
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
NEXT_PUBLIC_API_URL=/api
BACKEND_URL=https://<backend-public-domain>
```

The frontend calls `/api` on its own origin. Next.js rewrites those requests to
`BACKEND_URL`, so the browser does not depend on cross-origin API calls.

After the frontend domain is generated, set the backend variable for local and
direct API clients:

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
7. Configure the worker start command and Railway-linked PostgreSQL/Redis variables.
8. Add the frontend service with root directory `/frontend`.
9. Configure `/api` + `BACKEND_URL`, then generate the frontend public domain.
10. Restrict backend `CORS_ORIGINS` to the frontend domain.
11. Verify `/health`, indexing, search, Q&A, citations, feedback, and worker indexing.

## CLI commands after authentication

```bash
railway link
railway environment edit --service-config backend source.rootDirectory /backend
railway environment edit --service-config worker source.rootDirectory /backend
railway environment edit --service-config frontend source.rootDirectory /frontend
```

Do not put secret values in shell history or commit them. Prefer Railway’s Variables UI.

## Current deployment

Railway project is active in production. The current public domains are:

- Frontend: `https://zoological-mercy-production-8922.up.railway.app`
- Backend: `https://ai-engineering-platform-production.up.railway.app`

The backend, worker, PostgreSQL, Redis, and frontend services have all been
verified Online. Keep `GOOGLE_API_KEY` and `SECRET_KEY` in Railway’s secret
variables only; never put them in this file or in Git.
