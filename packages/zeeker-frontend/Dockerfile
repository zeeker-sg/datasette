# Phase 2 frontend placeholder. Pattern from docs.astral.sh/uv/guides/integration/fastapi/.
# Deliberately NO sqlite / curl / wget — frontend talks to datasette only via HTTP
# (DEC-5 / REQ-frontend-data-via-http). The urllib-based healthcheck in compose
# uses the Python stdlib that's already in the slim image.

FROM python:3.12-slim

# Pull uv binary from the official astral image (no apt-get needed).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy lockfile + pyproject first for layer caching.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache --no-install-project

# Copy source + README (referenced by pyproject.toml `readme = "README.md"`)
# and install the package itself.
COPY src/ ./src/
COPY README.md ./README.md
RUN uv sync --frozen --no-cache

# Internal port; NOT published to host (caddy reaches it via bridge network).
EXPOSE 8000

# Run uvicorn directly (matches existing root Dockerfile style).
# --host 0.0.0.0 so the container's bridge IP can receive traffic from caddy.
CMD ["uv", "run", "uvicorn", "zeeker_frontend.main:app", "--host", "0.0.0.0", "--port", "8000"]
