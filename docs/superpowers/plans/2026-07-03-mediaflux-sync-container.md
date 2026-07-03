# Mediaflux Sync Container Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a containerised worker to the compose stack that continuously mirrors stored donation bundles from the local `donation-data` volume up to the MDAP Mediaflux project via `unimelb-mf-upload` over HTTPS.

**Architecture:** A long-running `mflux-sync` container runs a loop of one-shot `unimelb-mf-upload` invocations (each a full server-side compare, so it backfills and stays idempotent), reading `/data/donations` read-only. Two small backend changes support it: donation temp files move out of the watched directory, and the admin panel hides the (unpopulated) sync columns.

**Tech Stack:** Docker (multi-stage), Maven + JRE 17, `unimelb-mf-clients` v0.8.6 (Java), FastAPI/SQLModel backend, sqladmin.

## Global Constraints

- Branch: `deployment` (all work committed here; do not touch `main`).
- `unimelb-mf-clients` **v0.8.6**, source archive sha256 `5b56894439950f8a4b41e847ce38d3f42c35127eb827ad6f443e7895291c211b` (verify in build).
- Java runtime: **eclipse-temurin:17-jre**; build: **maven:3-eclipse-temurin-17**.
- Upload command must **never** include `--sync-delete-assets` / `--hard-delete-assets` (upload-only; least privilege).
- Mediaflux host `mediaflux.researchsoftware.unimelb.edu.au`, port `443`, transport `https`.
- Destination is the **parent** collection `MFLUX_DEST_PARENT`; bundles land in `$MFLUX_DEST_PARENT/donations` (default parent `/projects/proj-4180_spotify_unpacked-1128.4.1450`).
- Australian English spelling in new identifiers/comments; no em-dashes in prose/comments.
- Backend: Python 3.12, run tests with `backend/.venv/bin/pytest`. The full backend suite (currently 109 tests) must stay green.
- Config precedence: image `ENV` defaults, overridable by `env_file: .env`. The token (`MFLUX_TOKEN`) lives only in the gitignored `deploy/.env`.

---

### Task 1: Backend — write donation temp files outside the watched tree

**Files:**
- Modify: `backend/app/services/storage.py` (the temp-path block, ~lines 40-58)
- Create: `backend/tests/test_storage.py`

**Interfaces:**
- Consumes: existing `store_bundle(*, source_zip: Path, asset_name: str, sidecar: dict, target_dir: Path) -> StoredBundle` (signature unchanged).
- Produces: same signature; new behaviour = temp files are staged in `target_dir.parent / ".tmp"`, never inside `target_dir`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_storage.py`:
```python
from pathlib import Path

from app.services.storage import store_bundle


def test_temp_files_are_staged_outside_target_dir(tmp_path, monkeypatch):
    """The sync watches target_dir; partial .tmp files must never appear there.

    We spy on os.replace to capture where each temp file was staged before the
    atomic rename into target_dir, and assert none were inside target_dir.
    """
    import app.services.storage as storage

    src = tmp_path / "src.zip"
    src.write_bytes(b"PK\x03\x04 fake zip bytes")
    target = tmp_path / "donations"

    staged_parents = []
    real_replace = storage.os.replace

    def spy_replace(a, b):
        staged_parents.append(Path(a).parent)
        return real_replace(a, b)

    monkeypatch.setattr(storage.os, "replace", spy_replace)

    result = store_bundle(
        source_zip=src,
        asset_name="donation_X__20260101-000000__1.zip",
        sidecar={"donor_code": "X"},
        target_dir=target,
    )

    # os.replace ran for both zip + sidecar, and neither was staged ANYWHERE
    # inside the recursively-watched donations tree (target/.tmp would still be
    # scanned, so `!= target` is too weak — use is_relative_to).
    assert staged_parents, "expected os.replace to be called"
    assert all(not parent.is_relative_to(target) for parent in staged_parents)

    # end state: only the final files live in the watched dir, no dotfiles/.tmp
    names = sorted(p.name for p in target.iterdir())
    assert names == [
        "donation_X__20260101-000000__1.zip",
        "donation_X__20260101-000000__1.zip.json",
    ]
    assert result.bundle_path.exists() and result.sidecar_path.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/test_storage.py -q`
Expected: FAIL, the `is_relative_to(target)` assertion is False because the current code stages `.tmp` inside `target_dir` (which IS relative to `target`).

- [ ] **Step 3: Implement — stage temp files in a sibling `.tmp` dir**

In `backend/app/services/storage.py`, replace the temp-path setup and the mkdir line. Change from:
```python
    target_dir.mkdir(parents=True, exist_ok=True)

    final_zip = target_dir / asset_name
    final_json = target_dir / f"{asset_name}.json"
    tmp_zip = target_dir / f".{asset_name}.tmp"
    tmp_json = target_dir / f".{asset_name}.json.tmp"
```
to:
```python
    target_dir.mkdir(parents=True, exist_ok=True)
    # Stage temp files OUTSIDE the watched donations dir so the Mediaflux sync
    # (which has no file-exclude option) can never scan a half-written file.
    # Same filesystem as target_dir, so os.replace() stays atomic.
    tmp_dir = target_dir.parent / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    final_zip = target_dir / asset_name
    final_json = target_dir / f"{asset_name}.json"
    tmp_zip = tmp_dir / f"{asset_name}.tmp"
    tmp_json = tmp_dir / f"{asset_name}.json.tmp"
```
(The rest of the function, `shutil.copyfile` / `write_text` / `os.replace` / except cleanup / return, is unchanged.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/pytest tests/test_storage.py -q && .venv/bin/pytest -q`
Expected: new test PASSES; full suite still green (110 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/storage.py backend/tests/test_storage.py
git commit -m "fix(backend): stage donation temp files outside the watched donations dir"
```

---

### Task 2: Backend — hide unpopulated sync columns from the admin panel

**Files:**
- Modify: `backend/app/admin_panel.py` (`DonationAdmin.column_list`, ~lines 130-138)
- Modify: `backend/tests/test_admin_panel.py` (add a guard test)

**Interfaces:**
- Consumes: `DonationAdmin` class in `app/admin_panel.py`; `Donation` model.
- Produces: `DonationAdmin.column_list` no longer contains `Donation.synced_at` or `Donation.mediaflux_asset_id`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_admin_panel.py`:
```python
def test_donation_admin_hides_unpopulated_sync_columns():
    # v1 does not populate synced_at / mediaflux_asset_id, so they must not be
    # shown (an always-empty column reads as "never synced").
    from app.admin_panel import DonationAdmin

    keys = [c.key for c in DonationAdmin.column_list]
    assert "synced_at" not in keys
    assert "mediaflux_asset_id" not in keys
    # the useful columns remain
    assert "code" in keys and "status" in keys
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/test_admin_panel.py::test_donation_admin_hides_unpopulated_sync_columns -q`
Expected: FAIL (`synced_at`/`mediaflux_asset_id` currently in `column_list`).

- [ ] **Step 3: Implement — drop the two columns**

In `backend/app/admin_panel.py`, `DonationAdmin.column_list`, remove the last two entries. Change from:
```python
    column_list = [
        Donation.id,
        Donation.code,
        Donation.status,
        Donation.submitted_at,
        Donation.storage_path,
        Donation.synced_at,
        Donation.mediaflux_asset_id,
    ]
```
to:
```python
    column_list = [
        Donation.id,
        Donation.code,
        Donation.status,
        Donation.submitted_at,
        Donation.storage_path,
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/pytest tests/test_admin_panel.py -q && .venv/bin/pytest -q`
Expected: PASS; full suite green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/admin_panel.py backend/tests/test_admin_panel.py
git commit -m "change(admin): hide unpopulated synced_at/mediaflux_asset_id columns"
```

---

### Task 3: Sync image — Dockerfile + entrypoint

**Files:**
- Create: `deploy/mflux-sync/Dockerfile`
- Create: `deploy/mflux-sync/entrypoint.sh`

**Interfaces:**
- Produces: an image whose entrypoint validates config and loops `java -cp /opt/mf.jar unimelb.mf.client.sync.cli.MFUpload --dest "$MFLUX_DEST_PARENT" --create-parents --csum-check --nb-workers 2 /data/donations` every `MFLUX_SCAN_INTERVAL` seconds. Reads `MFLUX_HOST/PORT/TRANSPORT/TOKEN` (client-native), `MFLUX_DEST_PARENT`, `MFLUX_SCAN_INTERVAL` from env.
- Note (verified): `unimelb-mf-clients-<v>-jar-with-dependencies.jar` (what the Dockerfile copies) is **byte-identical** (same sha256) to the distribution's `lib/unimelb-mf-clients.jar` used in the successful manual upload, and running `MFUpload` from it directly is the exact invocation that was validated. Step 4 re-verifies it.

- [ ] **Step 1: Create the entrypoint script**

Create `deploy/mflux-sync/entrypoint.sh`:
```sh
#!/bin/sh
# Continuously mirror /data/donations into Mediaflux with one-shot uploads.
# Each cycle is a full server-side compare (idempotent + backfills existing files).
set -eu

# Validate required config up front and exit with a clear message if missing.
# (With restart: unless-stopped this crash-loops with logs naming the missing
#  var, rather than silently running with bad config.)
: "${MFLUX_TOKEN:?MFLUX_TOKEN is required (secure identity token)}"
: "${MFLUX_DEST_PARENT:?MFLUX_DEST_PARENT is required (parent collection path)}"
: "${MFLUX_SCAN_INTERVAL:=300}"

echo "mflux-sync: /data/donations -> ${MFLUX_DEST_PARENT}/donations every ${MFLUX_SCAN_INTERVAL}s"

while true; do
  # MFLUX_HOST/PORT/TRANSPORT/TOKEN are read from the environment by the client.
  java -cp /opt/mf.jar unimelb.mf.client.sync.cli.MFUpload \
    --dest "$MFLUX_DEST_PARENT" --create-parents --csum-check --nb-workers 2 \
    /data/donations \
    || echo "mflux-sync: upload cycle failed; retrying in ${MFLUX_SCAN_INTERVAL}s"
  sleep "$MFLUX_SCAN_INTERVAL"
done
```

- [ ] **Step 2: Create the Dockerfile**

Create `deploy/mflux-sync/Dockerfile`:
```dockerfile
# syntax=docker/dockerfile:1.7

# ---------- Build unimelb-mf-clients from pinned, checksum-verified source ----------
FROM maven:3-eclipse-temurin-17 AS build
ARG MF_CLIENTS_VERSION=0.8.6
ARG MF_CLIENTS_SHA256=5b56894439950f8a4b41e847ce38d3f42c35127eb827ad6f443e7895291c211b
WORKDIR /build
ADD https://gitlab.unimelb.edu.au/resplat-mediaflux/unimelb-mf-clients/-/archive/v${MF_CLIENTS_VERSION}/unimelb-mf-clients-v${MF_CLIENTS_VERSION}.tar.gz src.tgz
RUN echo "${MF_CLIENTS_SHA256}  src.tgz" | sha256sum -c - \
 && tar xzf src.tgz --strip-components=1 \
 && mvn -q -DskipTests -P platform-packages package

# ---------- Runtime: JRE + the self-contained client jar + loop entrypoint ----------
FROM eclipse-temurin:17-jre
ARG MF_CLIENTS_VERSION=0.8.6
COPY --from=build /build/target/unimelb-mf-clients-${MF_CLIENTS_VERSION}-jar-with-dependencies.jar /opt/mf.jar
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
# Connection defaults (token + dest come from the environment / .env).
ENV MFLUX_HOST=mediaflux.researchsoftware.unimelb.edu.au \
    MFLUX_PORT=443 \
    MFLUX_TRANSPORT=https \
    MFLUX_SCAN_INTERVAL=300
ENTRYPOINT ["/entrypoint.sh"]
```

- [ ] **Step 3: Build the image**

Run: `cd deploy && docker build -t donation-mflux-sync:test mflux-sync`
Expected: build succeeds (sha256 check passes, Maven builds, jar copied).

- [ ] **Step 4: Verify the client jar runs**

Run: `docker run --rm --entrypoint java donation-mflux-sync:test -cp /opt/mf.jar unimelb.mf.client.sync.cli.MFUpload --version`
Expected: prints a version line (proves the jar + main class are correct).

- [ ] **Step 5: Verify fail-fast on missing config**

Run: `docker run --rm donation-mflux-sync:test; echo "exit=$?"`
Expected: prints `MFLUX_TOKEN is required (secure identity token)` (or similar) and `exit=1` (no token supplied → the entrypoint exits non-zero immediately, does not loop).

- [ ] **Step 6: Commit**

```bash
git add deploy/mflux-sync/Dockerfile deploy/mflux-sync/entrypoint.sh
git commit -m "feat(deploy): mflux-sync image (unimelb-mf-clients build + one-shot upload loop)"
```

---

### Task 4: Compose service + `.env.example`

**Files:**
- Modify: `deploy/docker-compose.prod.yml` (add `mflux-sync` service)
- Modify: `deploy/.env.example` (document the `MFLUX_*` vars)

**Interfaces:**
- Consumes: the `donation-data` named volume (already defined); the `mflux-sync` image from Task 3.
- Produces: a `mflux-sync` compose service that builds `deploy/mflux-sync/`, reads `.env`, mounts donations read-only.

- [ ] **Step 1: Add the compose service**

In `deploy/docker-compose.prod.yml`, after the `caddy:` service block and before `volumes:`, add:
```yaml
  mflux-sync:
    build:
      context: mflux-sync
    image: donation-mflux-sync:prod
    restart: unless-stopped
    # MFLUX_TOKEN + MFLUX_DEST_PARENT (and any overrides) come from .env;
    # host/port/transport/interval have image defaults.
    env_file:
      - .env
    volumes:
      # Source is the same volume the backend writes to, mounted read-only.
      - donation-data:/data:ro
```

- [ ] **Step 2: Add config to `.env.example`**

Append to `deploy/.env.example`:
```
# ---- Mediaflux sync (mflux-sync container) ----
# Parent collection; bundles land in $MFLUX_DEST_PARENT/donations.
MFLUX_DEST_PARENT=/projects/proj-4180_spotify_unpacked-1128.4.1450
# Secure identity token (participant-acm role) from the token portal:
# https://mediaflux.researchsoftware.unimelb.edu.au/token-portal/
# If the token ever contains a literal `$`, double it to `$$` (see .env header note).
MFLUX_TOKEN=
# Optional overrides (defaults baked into the image):
# MFLUX_HOST=mediaflux.researchsoftware.unimelb.edu.au
# MFLUX_PORT=443
# MFLUX_TRANSPORT=https
# MFLUX_SCAN_INTERVAL=300
```

- [ ] **Step 3: Validate the compose file**

Run (needs a `.env`; create a throwaway one if absent):
```bash
cd deploy
[ -f .env ] || cp .env.example .env   # only if you don't already have one
docker compose -f docker-compose.prod.yml config >/dev/null && echo "compose OK"
```
Expected: `compose OK` (the `mflux-sync` service parses; build context resolves to `deploy/mflux-sync`).

- [ ] **Step 4: Commit**

```bash
git add deploy/docker-compose.prod.yml deploy/.env.example
git commit -m "feat(deploy): add mflux-sync compose service + document MFLUX_* env"
```

---

### Task 5: Deploy + verify on the VM (operator-run; real Mediaflux)

This task writes to real Mediaflux, so the operator runs the upload steps.
It proves backfill against a read-only source (guards the daemon-backfill risk)
and integrity, then retires the throwaway `/volume/mflux-sync` scaffold.

**Files:** none (operational).

- [ ] **Step 1: Ship the code to the VM**

On the VM:
```bash
cd /volume/spotify-unpacked && git pull --ff-only
# ensure MFLUX_TOKEN + MFLUX_DEST_PARENT are set + non-empty (without printing them)
grep -q '^MFLUX_TOKEN=.' deploy/.env && grep -q '^MFLUX_DEST_PARENT=.' deploy/.env \
  && echo "both set" || echo "MISSING one of MFLUX_TOKEN / MFLUX_DEST_PARENT"
```
Expected: `both set`.

- [ ] **Step 2: Build + start the whole stack (backend rebuilt for the storage change)**

```bash
cd /volume/spotify-unpacked/deploy
sudo docker compose -f docker-compose.prod.yml up -d --build
sudo docker compose -f docker-compose.prod.yml ps
```
Expected: `backend` healthy, `caddy` up, `mflux-sync` up.

- [ ] **Step 3: Confirm backfill happened (existing donation uploaded from a read-only mount)**

```bash
sudo docker compose -f docker-compose.prod.yml logs --since 5m mflux-sync
```
Expected: log shows an upload cycle that either uploaded the pre-existing test
donation or reported it already present (0 failed). If the client errors that it
cannot write to a read-only source, add a writable scratch volume to the service
(`mflux-sync-state:/state`) and a matching top-level volume, then rebuild.

- [ ] **Step 4: Verify integrity against Mediaflux**

```bash
# Run INSIDE the container so $MFLUX_DEST_PARENT expands from the container env
# (the operator shell doesn't have it). MFCheck compares local vs Mediaflux.
cd /volume/spotify-unpacked/deploy
sudo docker compose -f docker-compose.prod.yml exec -T mflux-sync sh -c \
  'java -cp /opt/mf.jar unimelb.mf.client.sync.cli.MFCheck --dest "$MFLUX_DEST_PARENT" /data/donations'
```
Expected: reports the local files match the Mediaflux assets (0 differences).
(`unimelb.mf.client.sync.cli.MFCheck` is the verified check entrypoint in the jar.)

- [ ] **Step 5: Retire the throwaway scaffold**

```bash
sudo rm -rf /volume/mflux-sync   # the manual-test client + wrapper script
```

---

## Notes for the implementer

- Do not add `--sync-delete-assets`; the sync must never delete Mediaflux assets.
- The `donation-data` volume is mounted read-only into `mflux-sync`; the backend
  is the only writer. Temp files now live in `/app/data/.tmp` (outside the
  watched `/app/data/donations`), so the read-only sync mount only sees complete
  bundles.
- Config precedence: the image ships `ENV` defaults; `.env` (via `env_file`)
  overrides them. `MFLUX_TOKEN` must only ever live in the gitignored `.env`.
