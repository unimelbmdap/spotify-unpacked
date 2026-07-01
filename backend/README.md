# Mediaflux Donation Backend

FastAPI service that accepts Spotify-export donations from anonymous donors
(validated by pre-issued participant codes). Each donation is stored as a zip
bundle plus a metadata sidecar on a local volume; a separate offline job
(deferred) later syncs bundles to a single MDAP-owned Mediaflux project.

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

## Participant codes (whitelist)

Donations require a valid participant code. Codes are human-friendly, matched
case-insensitively, and stored in the `participant_codes` table.

- **Seed file:** point `PARTICIPANT_CODES_FILE` at a CSV (`code,max_uses,label`;
  see `scripts/sample_data/participant_codes.csv`). It's loaded at startup and
  re-read on demand via `POST /api/admin/codes/reload` (admin auth + the
  `X-Admin-Request: 1` header). The real file belongs under `data/` (gitignored).
- **Validation:** `POST /api/codes/validate` with `{"code": "..."}` returns
  `{"valid": true|false}` for the donate page's up-front check (code in the body,
  not the URL, to keep it out of logs; rate-limited by `RATE_LIMIT_VALIDATE`). The
  authoritative check is the atomic reservation done at `POST /api/donate`.
- **Admin API:** `POST/GET/PATCH /api/admin/codes` still manage codes directly.
- **Admin panel:** a browser UI at `/admin` (sqladmin) for CRUD over codes plus a
  "Reload from seed file" action, and read-only views of donations and the audit
  log. Log in with `ADMIN_USERNAME`/`ADMIN_PASSWORD`. Restrict `/admin` to trusted
  IPs at the reverse proxy, same as `/api/admin/*`.

See `docs/superpowers/specs/2026-07-01-participant-code-whitelist-design.md` for
this feature's design and `local/2026-04-30-mediaflux-donation-design.md` for the
original (pre-pivot) backend design.
