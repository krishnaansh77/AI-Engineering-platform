# Django compatibility API

This service is the incremental migration layer for the platform. It provides
native Django routes for migrated endpoints and forwards uncovered `/api/*`
requests to the legacy FastAPI service so the production application can keep
working while endpoint parity is completed.

## Local run

```bash
cd django_backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
LEGACY_API_URL=http://localhost:8000 python manage.py runserver 8100
```

The compatibility API is available at `http://localhost:8100/api/`.

With Docker Compose, start the existing stack plus this opt-in service from the
repository root:

```bash
docker compose --profile django up -d
```

The existing FastAPI service remains on port `8000`; Django is on port `8100`.

For Railway, the included Dockerfile starts Gunicorn and respects Railway's
`PORT` variable. Set `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`,
`LEGACY_API_URL`, and `DJANGO_ALLOWED_HOSTS` through the service environment.

## Migration rule

When an endpoint is reimplemented in Django, add the Django route before the
catch-all proxy route and add a contract test. Do not delete the FastAPI route
until both clients and production checks use the Django implementation.
