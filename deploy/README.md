# Production deployment

Two containers:

- **backend** — FastAPI + the sqladmin panel (`../backend/Dockerfile`). SQLite and
  donation bundles live on a persistent volume. Not exposed publicly.
- **caddy** — builds the Vue SPA and serves it, terminates TLS, enforces the
  200 MB upload cap, restricts `/admin` + `/api/admin` to trusted IPs, and
  reverse-proxies `/api` and `/admin` to the backend.

- **mflux-sync** — mirrors `/data/donations` on the shared volume to Mediaflux
  every `MFLUX_SCAN_INTERVAL` (`mflux-sync/`).
- **report-gen** — renders a per-donor PDF plus companion JSON for each new
  donation bundle into `/data/donations/reports/`, which mflux-sync then mirrors
  (`../reports/`, see its README for retry and regeneration commands).

## Quick start

```bash
cd deploy
cp .env.example .env          # then edit: domain, admin IPs, secrets
docker compose -f docker-compose.prod.yml up -d --build
```

Validate config without starting anything:

```bash
docker compose -f docker-compose.prod.yml config >/dev/null && echo OK
docker run --rm -v "$PWD/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2-alpine caddy validate --config /etc/caddy/Caddyfile
```

## TLS options

The Caddyfile defaults to **automatic HTTPS**: set `SITE_ADDRESS` to a real
domain with ports 80/443 reachable and `ACME_EMAIL`, and Caddy provisions a
Let's Encrypt certificate (persisted in the `caddy-data` volume).

Two alternatives, depending on where MDAP places this:

- **UoM-provided certificate:** add `tls /etc/caddy/cert.pem /etc/caddy/key.pem`
  inside the site block and mount the cert/key into the caddy container.
- **TLS terminated upstream (cloud load balancer):** set `SITE_ADDRESS=:80`,
  drop the `email` global option, and let the LB handle certs. If the LB adds
  `X-Forwarded-For`, switch the admin matcher from `remote_ip` to `client_ip`
  and set `trusted_proxies` so the real client IP is used for the allow-list.

## Things to know

- **Same-origin frontend.** `VITE_API_BASE_URL` is baked into the SPA at build
  time (empty = same origin). It's set to `""` in `docker-compose.prod.yml`, so
  the browser calls `/api` and `/admin` on the Caddy host. Changing it later
  means rebuilding the caddy image, not just restarting.
- **Base path.** `vite.config.ts` defaults `base` to `/spotify-unpacked/` for the
  GitHub Pages subpath deploy. This image builds with `VITE_BASE=/` (set in the
  compose build args) so assets and routes resolve at the domain root. If you
  ever serve under a subpath here, change that arg to match.
- **Single backend replica.** SQLite is a single-writer embedded DB, so run one
  backend. Scaling out would require moving to Postgres (and Redis for the rate
  limiter). Fine for a single research cohort.
- **Whitelist codes.** Manage via the `/admin` panel, or drop a
  `participant_codes.csv` onto the `donation-data` volume at
  `/app/data/participant_codes.csv` (loaded at startup; reload from the panel).
- **Backups.** The backend writes a daily `VACUUM INTO` snapshot to
  `donations/_db-backups/` on the shared volume; the `mflux-sync` service already
  mirrors that directory, so snapshots land in Mediaflux next to the bundles with
  no extra wiring. Tunable via `BACKUP_ENABLED` / `BACKUP_INTERVAL_HOURS` /
  `BACKUP_DIR`. Snapshots are never overwritten (mflux-sync is upload-only), so
  they accumulate as versioned history; prune old local snapshots if the
  `--csum-check` rehash cost grows. For a sub-24h RPO, add Litestream on top.
- **Admin IPs are required.** `ADMIN_ALLOWED_IPS` must be set; if blank, all
  admin access is denied by design.
