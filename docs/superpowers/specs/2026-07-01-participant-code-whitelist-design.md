# Participant-code whitelist + donate flow — design

**Date:** 2026-07-01
**Status:** Approved, in implementation
**Branch:** `feat/participant-code-whitelist`
**Project:** spotify-unpacked (donation backend + Vue SPA)

## Goal

Let approved participants donate their Spotify export by entering a human-friendly
participant code on the donate page. Codes are managed as a whitelist that admins
maintain via a server-side seed file (with the existing admin API kept for ad-hoc
changes). The donate page validates the code up-front, then submits the donation,
which is authoritatively re-validated on the backend.

## Context (current state)

- The backend (`backend/`) already has the whole code storage + validation pipeline:
  `ParticipantCode` model (`backend/app/models.py`), a codes service
  (`backend/app/services/codes.py`), admin API (`backend/app/routes/admin.py`),
  and atomic allow-list reservation at donation time
  (`reserve_code` in `backend/app/services/donations.py`).
- The donate request path is decoupled from Mediaflux: it stores a zip bundle on
  disk and records the donation with status `stored`, returning a `donation_id`
  (no Mediaflux asset id). The Mediaflux sync job is deferred.
- The frontend `src/views/DonateView.vue` is a stub and there are **no** API calls
  anywhere in `src/`.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Code source | Human-friendly, admin-supplied via a seed file | User wants friendly, memorable codes; file is the simplest first step |
| Management | Seed file → DB now; admin API kept; admin UI deferred | Approach C: least work to a working whitelist, no lock-in |
| Case sensitivity | Case-insensitive (trim + uppercase on import and every lookup) | Forgiving for participants typing codes |
| Validation UX | Up-front check + authoritative re-check on submit | Avoids wasted large uploads; reservation stays the source of truth |
| Donate UI | Two-step: (1) enter/validate code, (2) consent + files + submit | Clear, gates the upload behind a valid code |

## Components

### Backend

1. **`codes` service additions** (`backend/app/services/codes.py`)
   - `import_codes(session, entries)`: idempotent upsert of caller-supplied codes.
     New codes inserted; existing codes update `max_uses`/`admin_label` only and
     **never** touch `uses` or `status` (revoked stays revoked, usage preserved).
     Each code validated against `CODE_REGEX`; invalid entries rejected/reported.
   - `is_code_valid(session, code)`: read-only check — exists AND `status == active`
     AND `uses < max_uses`. Does **not** reserve.
   - Code normalisation helper: `trim + uppercase` applied on import and in every
     lookup path (`is_code_valid`, `reserve_code`).

2. **Seed parser** (new `backend/app/services/code_seed.py`)
   - Parses CSV `code,max_uses,label` with `#` comments and blank lines skipped;
     `max_uses` (default 1) and `label` optional. Returns parsed entries + a list
     of skipped/invalid lines for logging. No DB access (pure/ testable).

3. **Public validate endpoint** (new `backend/app/routes/codes.py`)
   - `GET /api/codes/{code}` → `{ "valid": true|false }`. Returns plain `false`
     for unknown/revoked/exhausted/malformed alike (no enumeration signal).
   - Rate-limited via the existing slowapi limiter; new `rate_limit_validate`
     setting (default `20/minute`).

4. **Admin reload endpoint** (`backend/app/routes/admin.py`)
   - `POST /api/admin/codes/reload` → re-reads the seed file, upserts via
     `import_codes`, returns `{added, updated, skipped}`. Inherits `require_admin`
     (HTTP basic auth **and** `X-Admin-Request: 1`) like all admin routes.

5. **Startup wiring** (`backend/app/main.py` lifespan)
   - If the seed file exists, load + upsert once at startup and log a summary.

6. **Config** (`backend/app/config.py`)
   - `participant_codes_file: Path | None` (default `./data/participant_codes.csv`,
     on the already-mounted `./data` volume), `rate_limit_validate: str`.

7. **Schemas** (`backend/app/schemas.py`)
   - `CodeValidationResponse { valid: bool }`, `CodeReloadResponse { added, updated, skipped }`.

### Frontend

1. **API client** (new `src/lib/api.ts`)
   - Base URL from `VITE_API_BASE_URL` (dev default `http://localhost:8000`).
   - `checkCode(code): Promise<{valid: boolean}>` (GET), `getConsent()` (GET),
     `donate(formData, onProgress)` via `XMLHttpRequest` for upload progress.

2. **Donate view** (`src/views/DonateView.vue`, full rewrite)
   - State machine: `code → consentFiles → submitting → done | error`.
   - Step 1: code input → `checkCode`; inline error on invalid; valid unlocks step 2.
   - Step 2: fetch + show consent text/version, require accept checkbox, select
     `.json` files via existing `FileDropZone.vue`, client-side mirror of size/count
     limits for early feedback.
   - Submit: multipart `POST /api/donate` with `participant_code`, `consent_version`,
     `consent_accepted`, `app_version`, `files[]`. Map responses: `201` → success
     (shows donation id, "submitted/received", **not** "uploaded to Mediaflux");
     `401` → bounce to step 1; `409` → consent out of date; `413` → too large;
     `502` → storage error.

3. **Build config** — inject `app_version` from `package.json` via a Vite `define`;
   add `VITE_API_BASE_URL` to `.env` / example.

## Error handling & security

- Up-front check is convenience only; atomic `reserve_code` on submit remains
  authoritative (handles the check→submit race and double-use).
- Rate limiting on `/api/codes/{code}` (new) and `/api/donate` (existing).
- No new PII stored; `admin_label` remains admin-only and PII-free.

## Testing

- **Backend:** `import_codes` (insert / idempotent / preserve uses+status /
  invalid rejected / case-normalised), CSV parser (comments, blanks, bad lines),
  missing-file no-op, `is_code_valid` states, validate endpoint
  (active→true; unknown/revoked/exhausted→false; rate limit), reload endpoint
  (auth + CSRF header + summary).
- **Frontend:** vitest component tests for `DonateView` (code gate pass/fail,
  submit success, error mapping) with `api.ts` mocked; optional Playwright
  happy-path e2e.

## Out of scope (noted, deferred)

- Mediaflux sync job (scheduling, idempotency, `stored`→`complete`).
- ~~Admin UI for code management~~ — delivered via sqladmin at `/admin`
  (`app/admin_panel.py`): CRUD over codes with a normalisation hook, a
  "Reload from seed file" action, and read-only donation/audit views.
- General SQLite migration strategy (Alembic/startup migration) — deployment-phase;
  this feature adds no columns and is developed against a fresh DB.
- Pre-existing donate robustness (file placed on disk before DB commit with no
  cleanup on commit failure) — flagged by review, not introduced here.

## Codex review outcome

Codex reviewed the archived April design docs rather than this plan; its Mediaflux
/ sync-job findings reflect the pre-pivot design and don't apply. Three relevant
points were verified against current code and folded in: admin CSRF header on the
reload endpoint, success UI reflecting local-storage (donation id, not Mediaflux
asset), and the stale-`donations.db` / `create_all` migration caveat.
