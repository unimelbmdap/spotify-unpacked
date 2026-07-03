# Mediaflux sync container — design

**Date:** 2026-07-03
**Status:** Approved (direction), pending spec review
**Branch:** `deployment`
**Project:** spotify-unpacked (donation backend + Vue SPA, deployed on MRC VM)

## Goal

Continuously mirror stored donation bundles from the local `donation-data`
volume up to the MDAP Mediaflux project, as a container in the **same
docker-compose stack** (portable, one `up` brings up the whole system). This
completes the deferred "store then sync" pipeline: the backend writes bundles to
disk on donation; this worker ships them to Mediaflux.

## Validated facts (from a real end-to-end manual test)

These are proven, not assumed, the design is built on them:

- The MRC VM can reach `mediaflux.researchsoftware.unimelb.edu.au:443` (the rsync
  port 6600 is firewalled outbound; **HTTPS/443 is open**).
- A **secure identity token** with the `participant-acm` role authenticates and
  can create assets (upload + modify, **no delete**).
- **`unimelb-mf-clients` v0.8.6** builds from source (`mvn -P platform-packages
  package`) and runs in a JRE container; `unimelb-mf-upload` uploaded the test
  donation (`.zip` + `.json` sidecar) successfully, checksum-verified, idempotent.
- The destination path is **`/projects/proj-4180_spotify_unpacked-1128.4.1450/donations`**
  (created automatically with `--create-parents`).

## Design decisions

| Decision | Choice | Rationale |
|---|---|---|
| Transport | `unimelb-mf-upload` (Java, HTTPS/443) | Only reachable method from the VM; already validated |
| Cadence | **Loop of one-shot uploads** every `MFLUX_SCAN_INTERVAL` (a long-running container, but NOT the client's `--daemon` flag) | Each one-shot run does a full server-side compare, so it provably backfills pre-existing files, uploads new ones, and recovers after a crash. The `--daemon` flag's "new since last run" start behaviour is unproven for backfill (see plan-review). |
| Sync tracking | **None (v1)** | The client's server-side compare guarantees idempotency; a DB `synced_at`/`mediaflux_asset_id` reconcile is deferred |
| Panel display | **Hide** `synced_at` + `mediaflux_asset_id` columns | We don't populate them in v1, showing always-empty columns is misleading |
| Deletes | **Never** (`--sync-delete-assets` omitted) | Upload-only; local bundles are the durable copy, sync must not delete |
| Temp-file isolation | Backend writes temp files **outside** the watched `donations/` tree | `unimelb-mf-upload` has no file exclude flag; keeping partial `.tmp` files out of the watched dir guarantees only complete files are ever uploaded |
| Packaging | Service in `docker-compose.prod.yml` | Portability; single stack |
| Metadata | Sidecar `.json` rides alongside the `.zip` | Already produced; no Mediaflux asset-metadata plumbing needed |

## Components

### 1. `deploy/mflux-sync/Dockerfile` (multi-stage)
- **Build stage** (`maven:3-eclipse-temurin-17`): download the pinned
  unimelb-mf-clients source archive (v0.8.6), `mvn -q -DskipTests -P
  platform-packages package`, extract the produced
  `target/unimelb-mf-clients-<v>.zip` distribution.
- **Runtime stage** (`eclipse-temurin:17-jre`): copy the distribution to
  `/opt/unimelb-mf-clients`, put `bin/unix` on `PATH`. A small entrypoint runs
  the upload daemon.
- Version pinned via `ARG MF_CLIENTS_VERSION=0.8.6`; the build also verifies a
  pinned **sha256 of the source archive** (fail the build on mismatch) so the
  image is reproducible even if the tag's archive were to change.

### 2. Entrypoint (`deploy/mflux-sync/entrypoint.sh`)
```
#!/bin/sh
set -eu
# Fail fast on missing required config (rather than restart-looping on auth error)
: "${MFLUX_TOKEN:?MFLUX_TOKEN is required}"
: "${MFLUX_DEST_PARENT:?MFLUX_DEST_PARENT is required}"
: "${MFLUX_SCAN_INTERVAL:=300}"

while true; do
  unimelb-mf-upload \
    --dest "$MFLUX_DEST_PARENT" --create-parents --csum-check \
    --nb-workers 2 \
    /data/donations || echo "upload cycle failed; will retry next interval"
  sleep "$MFLUX_SCAN_INTERVAL"
done
```
- **One-shot loop, not `--daemon`**: each cycle is a full scan + server-side
  compare, so it uploads any file not already in Mediaflux (backfill on first
  run, new files thereafter). A failed cycle logs and retries next interval,
  never exits the loop.
- **`MFLUX_DEST_PARENT`** is the **parent** collection (the project root). The
  client appends the source directory name, so bundles land in
  `$MFLUX_DEST_PARENT/donations`, exactly what the manual test did (dest =
  project root, source = `/data/donations`, assets appeared under `.../donations/`).
- Connection via env: `MFLUX_HOST`, `MFLUX_PORT`, `MFLUX_TRANSPORT`, `MFLUX_TOKEN`
  (the client reads these natively).
- Logs to stdout (captured by `docker logs`).

### 3. Compose service `mflux-sync` (in `docker-compose.prod.yml`)
- `build: { context: mflux-sync }` (relative to `deploy/`, i.e. `deploy/mflux-sync/`).
- `env_file: [.env]` for `MFLUX_TOKEN` and the rest.
- `environment:` defaults for `MFLUX_HOST` / `MFLUX_PORT` / `MFLUX_TRANSPORT` /
  `MFLUX_DEST_PARENT` / `MFLUX_SCAN_INTERVAL`.
- `volumes: [ donation-data:/data:ro ]` — read-only source.
- `restart: unless-stopped`. No published ports. No `depends_on` (only needs the
  volume, independent of backend/caddy).

### 4. Admin panel change (`backend/app/admin_panel.py`)
Remove `Donation.synced_at` and `Donation.mediaflux_asset_id` from
`DonationAdmin.column_list` (keep `id`, `code`, `status`, `submitted_at`,
`storage_path`). The `status` column stays (it reflects the donation-write
lifecycle: `pending`/`stored`/`failed`, not Mediaflux state).

### 5. Config (`deploy/.env` + `.env.example`)
Add, with the token already present in the operator's gitignored `.env`:
```
MFLUX_HOST=mediaflux.researchsoftware.unimelb.edu.au
MFLUX_PORT=443
MFLUX_TRANSPORT=https
# PARENT collection. The uploaded source dir ("donations") is appended, so the
# final collection is $MFLUX_DEST_PARENT/donations. (Configured value != final path.)
MFLUX_DEST_PARENT=/projects/proj-4180_spotify_unpacked-1128.4.1450
MFLUX_SCAN_INTERVAL=300
MFLUX_TOKEN=            # secure identity token (participant-acm); operator fills
```

### 6. Backend change: keep temp files out of the watched tree (`backend/app/services/storage.py`)
Currently `store_bundle` writes `.<name>.tmp` / `.<name>.json.tmp` **inside** the
`donations/` dir before `os.replace`. Since the sync watches that dir and
`unimelb-mf-upload` has no file-exclude flag, a scan mid-write could upload a
partial temp file. Change: write temp files to a sibling dir **outside** the
watched tree (e.g. `target_dir.parent / ".tmp"`), still on the same filesystem so
`os.replace` into `donations/` stays atomic. Result: `donations/` only ever
contains complete files. (Backend-only change; add a test asserting no `.tmp`
artifact ever appears in the donations dir.)

## Data flow

```
donation (browser) → backend → writes bundle+sidecar to donation-data volume
                                             │  (read-only mount)
                                             ▼
mflux-sync loop: every MFLUX_SCAN_INTERVAL, one-shot scan /data/donations,
   upload any file not already in Mediaflux → $MFLUX_DEST_PARENT/donations
   (full server-side compare each cycle = idempotent + backfill; --csum-check
    verifies integrity). Backend temp files live outside /data/donations, so
    only complete bundles are ever visible to the sync.
```
No database interaction. The Mediaflux server's asset comparison is the source
of truth for "already synced."

## Error handling & resilience

- **Missing config:** the entrypoint validates `MFLUX_TOKEN` / `MFLUX_DEST_PARENT`
  are non-empty and **exits with a clear message** if not (no silent auth
  restart-loop). `.env.example` ships an empty `MFLUX_TOKEN`, so this catches an
  un-filled deploy immediately.
- **A failed upload cycle** (network blip, transient auth) logs and **retries on
  the next interval**, the loop never exits. `--nb-retries` (default 2) covers
  in-cycle retries.
- **Crash / restart:** `restart: unless-stopped` → next cycle re-scans →
  server-compare skips already-uploaded files (safe, idempotent).
- **No deletes ever:** local bundles are never removed by the sync; they remain
  the durable copy. (Local retention/cleanup is a separate future concern.)

## Read-only mount — verify in implementation

The one-shot loop only ever *reads* `/data/donations` (idempotency is
server-side), so a **read-only** mount should work. Implementation must confirm a
one-shot `unimelb-mf-upload` run succeeds against a read-only source; if it needs
a writable scratch/log dir, add a small dedicated writable volume
(`mflux-sync-state:/state`) rather than making the donation data writable.

## Security

- Token in gitignored `deploy/.env`, injected via `env_file` (not committed, not
  in process args as it was during the manual test).
- Least privilege: `participant-acm` (create/modify, **no delete**).
- Recommend IP-restricting the token to the VM's egress IP `45.113.233.80/32` in
  the token portal.
- Source mount is read-only.

## Testing

- **Temp-file isolation (backend, automated):** a `storage.py` test that after
  `store_bundle`, the `donations/` dir contains only the final `.zip` + `.json`
  and **no `.tmp`/dotfile artifact** (guards High-1).
- **Config fail-fast (automated):** the entrypoint (or a small helper) exits
  non-zero with a clear message when `MFLUX_TOKEN`/`MFLUX_DEST_PARENT` are blank.
- **Admin panel (automated):** a `test_admin_panel.py` test asserting
  `DonationAdmin.column_list` no longer contains `synced_at`/`mediaflux_asset_id`.
- **Image build:** `cd deploy && docker compose -f docker-compose.prod.yml build
  mflux-sync` succeeds; `docker run <img> unimelb-mf-upload --version` runs.
- **Compose validation:** `cd deploy && docker compose -f docker-compose.prod.yml
  config` parses with the new service.
- **Backfill against read-only source (manual/required):** point the container
  at a **pre-populated read-only** `/data/donations` (e.g. a throwaway test
  namespace) and confirm the first cycle uploads the pre-existing files — proves
  backfill + the read-only mount (guards High-2). If it can't, add the writable
  scratch volume noted above.
- **Integrity (manual, documented):** `unimelb-mf-check` compares
  `/data/donations` against the Mediaflux destination and reports a match.
- Backend suite must remain green (`storage.py` + admin are the only backend edits).

## Out of scope (v1, noted)

- DB sync-status reconcile (flip rows to `complete`, populate
  `synced_at`/`mediaflux_asset_id`) — deferred; the columns stay in the schema.
- Local bundle retention/cleanup after successful sync.
- Mediaflux **asset metadata** (we ship the sidecar file instead of populating a
  `donation:donor` doc-type).
- A periodic automated `unimelb-mf-check` loop (per-file `--csum-check` on upload
  covers integrity for v1).

## Portability note

The service builds the client from a pinned source version and reads all
configuration from `.env`, so the whole stack (`backend` + `caddy` + `mflux-sync`)
is portable to any Docker host that has the token and network egress to Mediaflux.
