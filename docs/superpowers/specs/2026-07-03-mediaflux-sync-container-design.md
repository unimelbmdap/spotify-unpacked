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
| Cadence | **Daemon mode** (`--daemon --daemon-scan-interval`) | Built-in continuous scan; no cron to manage |
| Sync tracking | **None (v1)** | The client's server-side compare guarantees idempotency; a DB `synced_at`/`mediaflux_asset_id` reconcile is deferred |
| Panel display | **Hide** `synced_at` + `mediaflux_asset_id` columns | We don't populate them in v1, showing always-empty columns is misleading |
| Deletes | **Never** (`--sync-delete-assets` omitted) | Upload-only; local bundles are the durable copy, sync must not delete |
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
- Version pinned via an `ARG MF_CLIENTS_VERSION=0.8.6` for reproducibility.

### 2. Entrypoint / command
```
unimelb-mf-upload \
  --dest "$MFLUX_DEST" --create-parents --csum-check \
  --daemon --daemon-scan-interval "$MFLUX_SCAN_INTERVAL" \
  --nb-workers 2 \
  /data/donations
```
- `MFLUX_DEST` is the **parent** collection (the project root). The client
  appends the source directory name, so bundles land in `$MFLUX_DEST/donations`
  — this is exactly what the manual test did (dest = project root, source =
  `/data/donations`, assets appeared under `.../donations/`).
- Connection via env: `MFLUX_HOST`, `MFLUX_PORT`, `MFLUX_TRANSPORT`, `MFLUX_TOKEN`
  (the client reads these natively).
- Logs to stdout (captured by `docker logs`).

### 3. Compose service `mflux-sync` (in `docker-compose.prod.yml`)
- `build: { context: mflux-sync }` (relative to `deploy/`, i.e. `deploy/mflux-sync/`).
- `env_file: [.env]` for `MFLUX_TOKEN` and the rest.
- `environment:` defaults for `MFLUX_HOST/PORT/TRANSPORT/DEST/SCAN_INTERVAL`.
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
# Parent collection; bundles land under $MFLUX_DEST/donations (source dir name).
MFLUX_DEST=/projects/proj-4180_spotify_unpacked-1128.4.1450
MFLUX_SCAN_INTERVAL=300
MFLUX_TOKEN=            # secure identity token (participant-acm); operator fills
```

## Data flow

```
donation (browser) → backend → writes bundle+sidecar to donation-data volume
                                             │  (read-only mount)
                                             ▼
mflux-sync daemon: every MFLUX_SCAN_INTERVAL, scan /data/donations,
   upload new/changed files → Mediaflux $MFLUX_DEST/donations
   (server-side compare = idempotent; --csum-check verifies integrity)
```
No database interaction. The Mediaflux server's asset comparison is the source
of truth for "already synced."

## Error handling & resilience

- **Crash / restart:** `restart: unless-stopped` → daemon restarts → re-scans →
  server-compare skips already-uploaded files (safe, idempotent).
- **Network blips:** `--nb-retries` (default 2); the next scan retries anyway.
- **Auth failure:** logged to stdout; container restarts. Tokens have no expiry
  (per the portal), so steady-state auth is stable.
- **No deletes ever:** local bundles are never removed by the sync; they remain
  the durable copy. (Local retention/cleanup is a separate future concern.)

## Read-only mount — the one thing to verify in implementation

Daemon mode "only uploads new files since the process last executed." This
should be **in-memory** state (idempotency is otherwise server-side), so a
**read-only** `/data` mount should work. Implementation must confirm this; if the
daemon requires a writable state/log dir, add a small dedicated writable volume
(e.g. `mflux-sync-state:/state`) rather than making the donation data writable.

## Security

- Token in gitignored `deploy/.env`, injected via `env_file` (not committed, not
  in process args as it was during the manual test).
- Least privilege: `participant-acm` (create/modify, **no delete**).
- Recommend IP-restricting the token to the VM's egress IP `45.113.233.80/32` in
  the token portal.
- Source mount is read-only.

## Testing

- **Image build test:** `docker build deploy/mflux-sync` succeeds; `docker run
  <img> unimelb-mf-upload --version` (or `--help`) runs (proves the build).
- **Compose validation:** `docker compose -f docker-compose.prod.yml config`
  parses with the new service.
- **Admin panel:** a backend test asserting `DonationAdmin.column_list` no longer
  contains `synced_at`/`mediaflux_asset_id` (guards the "hide sync info" intent).
- **Manual verification (documented):** on the VM, `unimelb-mf-check` compares
  `/data/donations` against the Mediaflux destination and reports a match.
- Backend suite must remain green (the admin change is the only backend edit).

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
