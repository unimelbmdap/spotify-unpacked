# syntax=docker/dockerfile:1.7

# ---------- Builder: install deps into a venv with uv ----------
FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

COPY pyproject.toml uv.lock /app/
COPY donation_reports /app/donation_reports
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---------- Fonts: pinned, checksum-verified downloads ----------
FROM python:3.12-slim-bookworm AS fonts
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /fonts
COPY scripts/fetch_fonts.sh /fetch_fonts.sh
RUN sh /fetch_fonts.sh /fonts

# ---------- Runtime ----------
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app
COPY --from=builder /app /app
COPY assets /app/assets
COPY --from=fonts /fonts/ /app/assets/fonts/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp/mpl \
    REPORT_DONATIONS_DIR=/data/donations \
    REPORT_ASSETS_DIR=/app/assets

# Warm matplotlib's font cache so the first render does not pay for it.
RUN python -c "from pathlib import Path; from donation_reports import fonts; fonts.configure(Path('/app/assets'))"

CMD ["python", "-m", "donation_reports", "run"]
