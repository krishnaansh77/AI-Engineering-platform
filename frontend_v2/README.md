# AISE frontend v2

This is the vanilla JavaScript/HTML/CSS redesign. It is intentionally separate
from the existing Next.js frontend until feature parity and browser smoke tests
are complete.

Run locally from the repository root with any static server, for example:

```bash
python3 -m http.server 4173 --directory frontend_v2
```

The app expects `/api/*` to be served by the Django compatibility API (or a
same-origin proxy to the existing FastAPI API).

For Vercel, set the project root to `frontend_v2` and configure the
`DJANGO_API_URL` environment variable to the Railway Django origin, without a
trailing `/api` path. `api/[...path].js` keeps browser requests same-origin and
forwards them to Django; do not put API tokens in frontend environment
variables. The included `vercel.json` keeps hash-based client routes working on
refresh.

For local testing against a running Django service, set
`window.__AISE_API_BASE__` before `app.js` or use the default same-origin
`/api` path behind a local reverse proxy.
