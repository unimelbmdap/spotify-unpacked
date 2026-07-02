# Production deployment

Two containers:

- **backend** — FastAPI + the sqladmin panel (`../backend/Dockerfile`). SQLite and
  donation bundles live on a persistent volume. Not exposed publicly.
- **caddy** — builds the Vue SPA and serves it, terminates TLS, enforces the
  200 MB upload cap, restricts `/admin` + `/api/admin` to trusted IPs, and
  reverse-proxies `/api` and `/admin` to the backend.

The Mediaflux sync job is intentionally out of scope here (deferred / to be done
another way). When it lands it reads the shared `donation-data` volume.

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

## Basic-auth gate (pre-launch)

Caddy puts a shared username/password in front of the **public** site (SPA +
public API) so it stays private during early feedback. The admin surfaces
(`/admin`, `/api/admin`) are excluded, they keep their IP allow-list and own
login. Set `BASIC_AUTH_USER` in `.env` (default `spotify`), then set the hash
with this helper from the `deploy/` directory (it hashes the password and
applies the `$`->`$$` escaping Compose needs):

```bash
read -rsp 'Basic-auth password: ' P; echo
HASH=$(sudo docker run --rm caddy:2-alpine caddy hash-password --plaintext "$P")
sed -i "s|^BASIC_AUTH_HASH=.*|BASIC_AUTH_HASH=$(printf '%s' "$HASH" | sed 's/\$/\$\$/g')|" .env
unset P; echo "BASIC_AUTH_HASH set."
```

To rotate the password later, re-run this and `docker compose ... up -d` (no
rebuild needed; Caddy reads it from the env). To remove the gate entirely,
delete the `import basicgate` lines from `Caddyfile` and rebuild.

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
- **Backups (deferred).** Per `../backend/DEPLOYMENT.md`, add Litestream (as a
  sidecar or a process in the backend image) to stream the SQLite file to object
  storage. Not wired here yet.
- **Admin IPs are required.** `ADMIN_ALLOWED_IPS` must be set; if blank, all
  admin access is denied by design.
