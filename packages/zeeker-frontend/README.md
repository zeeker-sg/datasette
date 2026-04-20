# zeeker-frontend

FastAPI + Jinja2 frontend for `data.zeeker.sg`. **Placeholder package** — real HTML routes arrive in Phases 4–6 of milestone M2. See `.planning/ROADMAP.md`.

This package deliberately does not install a SQLite client and has no access to the `./data` directory. All data is read from the internal Datasette service via HTTP (`http://zeeker-datasette:8001/...json`) per DEC-5 / REQ-frontend-data-via-http.

## Local dev

```bash
cd packages/zeeker-frontend
uv sync
uv run pytest -q
uv run uvicorn zeeker_frontend.main:app --reload --port 8000
curl http://localhost:8000/frontend-test
```
