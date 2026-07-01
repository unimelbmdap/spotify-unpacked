# Deployment notes (Plan A → cloud)

This file records what changes when moving from local Docker to a hosted
environment. Implementation of the hosted deployment is **out of scope for
Plan A**; this is a checklist for the follow-up.

## Mandatory before exposing publicly

- Place behind a reverse proxy (Caddy / nginx / cloud LB) terminating TLS.
- Enforce `client_max_body_size 200M` (or platform equivalent) at the proxy.
- Restrict `/api/admin/*` **and** `/admin` (the sqladmin browser panel) to UoM IP
  ranges at the proxy or via a firewall rule.
- Set `ADMIN_SESSION_SECRET` to an independent random value (used to sign the
  `/admin` session cookie); do not rely on the `IP_HASH_SALT` fallback in prod.
- Inject `MEDIAFLUX_TOKEN`, `IP_HASH_SALT`, `ADMIN_PASSWORD` from a secret
  store, never from a committed file.
- Set `APP_ALLOWED_ORIGINS` to the production SPA origin only.
- Persist the SQLite database on a durable volume; back it up daily (e.g.
  Litestream → object storage).

## Monitoring

- Probe `/api/health` from the platform's health-check.
- Ship structured logs (the app already writes JSON to stdout) to your log
  store (Splunk / cloud logging).
- Alert on any sustained increase in `donate_failed` or `donate_reject` audit
  events — these indicate either Mediaflux trouble or code-probing.

## Rotating the Mediaflux token

1. Issue a new token via the UoM token portal (same proxy account, same role,
   same scope).
2. Update the secret in the deployment platform.
3. Restart the container.
4. Run `scripts/e2e_smoke.sh` against the live host as a smoke check.
5. Revoke the old token via the portal.

## Out of scope (deferred to a future plan)

- Per-user admin accounts / SSO.
- Resumable uploads.
- Multi-region or HA backend.
- Donor-facing donation history.
