# Real Mediaflux smoke test (manual)

Runs an end-to-end donation against the **live** MDAP test namespace using the
real `aterm` Java client.

## Prerequisites
- A working `backend/.env` with:
  - `MEDIAFLUX_CLIENT=aterm`
  - `MEDIAFLUX_HOST`, `MEDIAFLUX_PORT`, `MEDIAFLUX_TOKEN` populated
  - `MEDIAFLUX_NAMESPACE` pointing at MDAP's **test** sub-namespace (NOT production)
  - `ATERM_JAR_PATH=/opt/mediaflux/aterm.jar`
- `aterm.jar` either downloaded into the image (set `ATERM_DOWNLOAD_URL` build-arg) or volume-mounted at `/opt/mediaflux/aterm.jar`
- Network egress from your dev machine to `mediaflux.researchsoftware.unimelb.edu.au:443`

## Steps

1. **Build the image with the jar baked in** (replace URL with the version-pinned download from RCS):

   ```bash
   docker compose build --build-arg ATERM_DOWNLOAD_URL="https://example.unimelb.edu.au/aterm-1.6.x.jar"
   ```

2. **Start the backend:**

   ```bash
   docker compose up -d
   sleep 5
   ```

3. **Run the smoke script** (creates a code, donates, lists, then verifies retry rejection):

   ```bash
   ADMIN_PASSWORD=... ./scripts/e2e_smoke.sh
   ```

4. **Verify in Mediaflux Desktop:** log in as an MDAP admin, navigate to
   `<MEDIAFLUX_NAMESPACE>`, and confirm:
   - A new sub-namespace exists named `<code>_<timestamp>_<donation_id>`
   - The sample JSON file is present inside it
   - The asset has the `donation:donor` metadata document attached with the
     correct `donor_code`, `consent_version`, `submitted_at`, etc.

5. **Test rollback (inject a failure):**
   - Temporarily set `MEDIAFLUX_NAMESPACE` to a path the token cannot write to.
   - Re-run the donate call from the smoke script — expect HTTP 502.
   - Restore the namespace and re-run with the same code; it should succeed
     because the failed attempt didn't burn the use.

6. **Tear down:**

   ```bash
   docker compose down
   ```

## What to do if it fails

| Symptom | Likely cause | Action |
|---|---|---|
| 401 from `aterm` | Wrong / expired token | Reissue token via UoM portal |
| `ConnectException` | Network egress blocked | Check VPN / proxy |
| `quota exceeded` | Project quota hit | Increase quota via Research Computing Portal |
| Asset created without metadata document | `donation:donor` schema not registered | Register schema in Mediaflux Desktop's Metadata Library |
