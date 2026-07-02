# syntax=docker/dockerfile:1.7

# ---------- Builder: install deps into a venv with uv ----------
FROM python:3.12-slim-bookworm AS builder

# Pin uv to a known version for reproducibility (bump as needed).
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install dependencies first (cached layer) without installing the project itself.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Now bring in the source and install the project.
COPY pyproject.toml uv.lock /app/
COPY app /app/app
COPY consent /app/consent
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---------- Runtime: slim image with JRE + the prebuilt venv ----------
FROM python:3.12-slim-bookworm AS runtime

# OpenJDK is needed only when MEDIAFLUX_CLIENT=aterm. We install it
# unconditionally so production and dev images are byte-identical (~200 MB).
# OpenJDK 17 is the most recent JRE in Debian Bookworm's default repo;
# aterm needs Java 8+ so this is plenty.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        openjdk-17-jre-headless ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# Optional: pin a known aterm.jar download. Replace ATERM_DOWNLOAD_URL with the
# version documented at
# https://rcs-knowledge-hub.atlassian.net/wiki/spaces/KB/pages/5474212
# When unset, the image runs in stub mode without it.
ARG ATERM_DOWNLOAD_URL=""
RUN mkdir -p /opt/mediaflux \
    && if [ -n "$ATERM_DOWNLOAD_URL" ]; then \
         curl -fsSL "$ATERM_DOWNLOAD_URL" -o /opt/mediaflux/aterm.jar; \
       fi

WORKDIR /app
COPY --from=builder /app /app

# Use the venv's executables directly (no `uv run` overhead in the runtime).
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
EXPOSE 8000

# --proxy-headers + --forwarded-allow-ips=* make uvicorn honour Caddy's
# X-Forwarded-Proto/For, so behind the HTTPS reverse proxy the app builds
# https:// URLs (sqladmin assets + login form) and audits the real client IP.
# Safe here: the backend is only reachable via Caddy, never published publicly.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
