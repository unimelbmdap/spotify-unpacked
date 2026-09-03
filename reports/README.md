# Donation reports

Renders a per-donor PDF report (dashboard, month-by-month grid, archetype
poster) plus a companion JSON for every donation bundle the backend stores,
and drops them where `mflux-sync` already mirrors to Mediaflux.

In production this runs as the `report-gen` service in
`deploy/docker-compose.prod.yml`. Design and decisions:
`docs/superpowers/specs/2026-09-02-donation-report-pipeline-design.md`.

## How it works

```
/data/donations/donation_<code>__<ts>__<id>.zip  (+ .zip.json sidecar)
        │  poll every REPORT_SCAN_INTERVAL
        ▼
report-gen: for each bundle with no report at any version and no
            current-version failure marker, render in a child process
        │  staged in /data/.tmp/reports, then os.replace
        ▼
/data/donations/reports/
    donation_<code>__<ts>__<id>__v01.json   companion (provenance + stats)
    donation_<code>__<ts>__<id>__v01.pdf    report
    donation_<code>__<ts>__<id>__v01.failed.json   on error
        │  mflux-sync (unchanged)
        ▼
Mediaflux …/donations/reports/
```

- **Nothing is overwritten.** The generator version is in every filename.
  Bumping `GENERATOR_VERSION` in `donation_reports/version.py` affects new
  donations only; existing reports stay as they are.
- **Retry or regenerate by hand:**
  `docker compose -f deploy/docker-compose.prod.yml run --rm report-gen python -m donation_reports run --once --force [--only CODE]`.
  `--force` ignores older-version reports and failure markers, and skips
  bundles that already have a current-version PDF.
- **Failures** are recorded as `…__vNN.failed.json` beside the reports (error
  class, message, traceback) and in the container log. They are not retried
  automatically.

## Local development

```bash
cd reports
uv sync
scripts/fetch_fonts.sh              # Poppins, Literata, Noto CJK, Noto Emoji into assets/fonts
uv run pytest -q
uv run python -m donation_reports render ../local/<bundle>.zip --out /tmp/reports
uv run python -m donation_reports render ../local/<bundle>.zip --out /tmp/reports --variant streaming-only
```

Without the fonts the renderer falls back to DejaVu Sans and logs one
warning; emoji and CJK characters in track names then render as boxes.

## Fonts and images

Fonts are all Google Fonts under the Open Font Licence and are fetched with
pinned checksums by `scripts/fetch_fonts.sh` (locally and at image build):
Poppins for headings, Literata for body text, Noto Sans CJK JP and monochrome
Noto Emoji as fallbacks for track and playlist names. Nothing is committed
under `assets/fonts/`. Variable-font files are skipped on load so weights
resolve to the static files.

The archetype poster images `assets/images/profile_receptive.jpg`,
`profile_responsive.jpg`, `profile_deliberate.jpg` are committed. The renderer
skips them if they are ever missing. matplotlib downsamples them to the drawn
size on save, so the 2480px originals add well under 100 KB to each PDF.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `REPORT_DONATIONS_DIR` | `/data/donations` | Where the backend writes bundles; reports go in its `reports/` subdir |
| `REPORT_TMP_DIR` | `<donations>/../.tmp/reports` | Staging dir, must be on the same filesystem and outside the mirrored tree |
| `REPORT_SCAN_INTERVAL` | `60` | Seconds between scans |
| `REPORT_RENDER_TIMEOUT` | `600` | Seconds before a child render is killed and marked failed |
| `REPORT_ASSETS_DIR` | package `assets/` | Fonts and images |

## Shared constants

`donation_reports/constants.json` holds the analysis window start, months
shown, and the archetype bands and weights. The frontend keeps its own copies
in `src/lib/dateWindow.ts` and `src/lib/archetypeConfig.ts`;
`src/lib/__tests__/reportConstants.spec.ts` fails if they drift. Change both
together.
