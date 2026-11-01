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

For Vercel, set the project root to `frontend_v2`. The current deployment uses
the explicit `/api/*` rewrite in `vercel.json` to the live compatibility API;
the SPA fallback comes after that rule so API requests are not rewritten to
`index.html`. When the Django service receives a public Railway domain, replace
that rewrite destination with the Django origin. Do not put API tokens in
frontend environment variables.

For local testing against a running Django service, set
`window.__AISE_API_BASE__` before `app.js` or use the default same-origin
`/api` path behind a local reverse proxy.
