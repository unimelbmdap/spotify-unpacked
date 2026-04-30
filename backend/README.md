# Mediaflux Donation Backend

FastAPI service that accepts Spotify-export donations from anonymous donors
(validated by pre-issued participant codes) and pushes them into a single
MDAP-owned Mediaflux project.

## Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) — install with
  `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Docker (only if you want to run the containerised version)

## Local development

```bash
cd backend
uv sync                          # creates .venv and installs deps + dev tools
cp .env.example .env             # then edit .env to set IP_HASH_SALT and ADMIN_PASSWORD
uv run uvicorn app.main:app --reload
```

Visit <http://localhost:8000/docs> for the OpenAPI UI.

## Tests

```bash
uv run pytest -q
```

## Docker

```
docker compose up --build
```

See `local/2026-04-30-mediaflux-donation-design.md` for the full design.
