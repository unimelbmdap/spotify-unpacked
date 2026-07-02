# Spotify Unwrapped Unpacked

## 2026 MDAP research collaboration

## Project Structure

```
spotify-unpacked/
├── e2e/                               # End-to-end tests (Playwright)
│   └── vue.spec.ts                    # Browser-based integration tests
├── explorations/                      # Python data exploration scripts
│   ├── code/
│   │   ├── ExplorePlaylists.py               # Playlist usage analysis and visualisations
│   │   └── InitialExplorationofSpotifyJSONfiles.py  # Initial Spotify export exploration
│   └── images/                        # Output charts from exploration scripts
├── public/                            # Static assets served as-is, incl. download-step panel images
├── src/
│   ├── __tests__/                     # Unit tests (Vitest)
│   │   └── App.spec.ts
│   ├── assets/
│   │   └── main.css                   # Global styles and Tailwind imports
│   ├── components/
│   │   ├── AppHeader.vue              # Top bar — title, view nav links, theme toggle, about popover
│   │   ├── BanCard.vue                # "Big number" stat card (label + value + optional caption)
│   │   ├── ControlsPanel.vue          # Dashboard's right sidebar — chart type selector (placeholder) and donate link
│   │   ├── DataPanel.vue              # Left sidebar on every view — file drop zone, dataset stats, clear button
│   │   ├── DonationPanel.vue          # Card linking to the donate page
│   │   ├── DownloadHelp.vue           # Card linking to the download-instructions page
│   │   ├── FileCard.vue               # Per-file-type upload status card with an info tooltip (used by UploadPanel)
│   │   ├── FileDropZone.vue           # Drag/drop + click-to-browse zone; unzips .zip uploads (used by DataPanel)
│   │   ├── FilesProgressPanel.vue     # Dataset-completeness card, superseded by StatsCard — currently unused
│   │   ├── InterviewerVizPanel.vue    # Interviewer view's charts — stacked listening area, archetype radar, hour/day polar charts
│   │   ├── ParticipantVizPanel.vue    # Participant view's charts — month-by-month explorer with a slider
│   │   ├── StatsCard.vue              # Dataset-completeness card driven by the required file types
│   │   ├── UploadPanel.vue            # Dashboard's central upload UI — BAN stats plus a FileCard per expected file type
│   │   └── ui/                        # shadcn-vue primitives (button, card, dialog, dropdown-menu, popover, resizable, scroll-area, select, slider)
│   ├── composables/
│   │   ├── useChartOptions.ts         # Shared Chart.js option builders (cartesian/radial), dark-mode aware
│   │   └── useFileDrop.ts             # Drag/drop state plus directory/zip flattening shared by the drop zones
│   ├── lib/
│   │   ├── archetypeConfig.ts         # Band/weight config for the receptiveness/responsiveness/deliberate scores
│   │   ├── fileTypes.ts               # Definitions of the expected Spotify export file types
│   │   ├── monthlyStats.ts            # Top track/artist helpers for a given month's entries
│   │   ├── parser.ts                  # Parses Spotify export JSON into `MusicEntry` records
│   │   ├── unzip.ts                   # Extracts .json files from an uploaded .zip
│   │   └── utils.ts                   # Tailwind class-merge helper (`cn()`)
│   ├── router/
│   │   └── index.ts                   # Vue Router config (/, /donate, /downloadsteps, /interviewer, /myspotify)
│   ├── stores/
│   │   ├── counter.ts                 # Example Pinia store (unused placeholder)
│   │   ├── data.ts                    # Core data store — parses uploaded files and derives all listening-time & archetype stats
│   │   └── visualisation.ts           # Tracks the selected chart type for the (currently unused) ControlsPanel dropdown
│   ├── views/
│   │   ├── DashboardView.vue          # Upload entry point — three resizable panels (data, upload, controls)
│   │   ├── DonateView.vue             # Data donation page (placeholder)
│   │   ├── DownloadSteps.vue          # Step-by-step Spotify data request/download instructions
│   │   ├── InterviewerView.vue        # Interviewer-facing layout — DataPanel + InterviewerVizPanel
│   │   └── ParticipantView.vue        # Participant-facing layout — DataPanel + ParticipantVizPanel
│   ├── visualisations/
│   │   ├── ChartDisplay.vue           # Generic chart-type renderer with dark mode support — currently unused
│   │   ├── chart-setup.ts             # Registers Chart.js plugins and controllers
│   │   └── UploadStatusViz.vue        # "Processing your upload" placeholder screen — currently unused, not routed
│   ├── App.vue                        # Root component — renders the header and router view
│   └── main.ts                        # App entry point — mounts Vue, Pinia, Router, Chart.js
├── components.json                    # shadcn-vue configuration
├── eslint.config.ts                   # ESLint + Oxlint + Playwright/Vitest rules
├── index.html                         # HTML shell — Vite entry point
├── package.json                       # Dependencies, scripts, and Node version requirements
├── playwright.config.ts               # E2E test config (Chromium, Firefox, WebKit)
├── vite.config.ts                     # Vite build config with Vue, DevTools, and Tailwind plugins
├── vitest.config.ts                   # Unit test config
└── tsconfig*.json                     # TypeScript configs (app, node, vitest)
```

### Key areas

#### `src/views/` — Pages

- **DashboardView** — The upload page. Lays out three horizontally resizable panels (data, upload, controls) using shadcn-vue's `ResizablePanel` components.
- **DonateView** — Placeholder for a future data donation workflow.
- **DownloadSteps** — Renders the step-by-step panel images for requesting and downloading a Spotify data export.
- **InterviewerView** / **ParticipantView** — Two audience-specific layouts, each pairing the shared `DataPanel` sidebar with their own visualisation panel (`InterviewerVizPanel` / `ParticipantVizPanel`). Both read from the same Pinia data store, so uploaded data persists when navigating between them client-side.

#### `src/components/` — UI building blocks

- **AppHeader** — Site title, nav links between Dashboard/Interviewer/Participant, a sun/moon/system theme toggle, and an about popover.
- **DataPanel** — Sidebar shown on every view: `FileDropZone` for uploads, `StatsCard` for dataset completeness, `DownloadHelp` link, and a clear-data button.
- **UploadPanel** — Dashboard-only central upload UI: BAN-style summary stats plus a `FileCard` per expected file type, each showing upload status and an explanatory tooltip.
- **FileDropZone** / **FileCard** — Drop-zone and per-file-type status primitives, built on the `useFileDrop` composable; handle drag/drop, click-to-browse, and `.zip` extraction.
- **StatsCard** — Current dataset-completeness card (required file types); **FilesProgressPanel** is an earlier version of the same idea, no longer wired up.
- **InterviewerVizPanel** / **ParticipantVizPanel** — The two audience-specific chart panels described above.
- **BanCard** — Small reusable "big number" stat tile used across both viz panels and `UploadPanel`.
- **DonationPanel** / **DownloadHelp** — Cards linking to `/donate` and `/downloadsteps` respectively.
- **ControlsPanel** — Chart-type dropdown and donate link; the dropdown is a UI placeholder not yet wired to a live chart (see `ChartDisplay.vue` below).
- **ui/** — Auto-generated shadcn-vue primitive components (button, card, dialog, dropdown-menu, popover, resizable, scroll-area, select, slider). These are scaffolded by the `shadcn` CLI and generally shouldn't be edited by hand.

#### `src/composables/` — Shared reactive logic

- **useFileDrop.ts** — Drag-over/processing state plus directory and `.zip` flattening, shared by `FileDropZone` and `UploadPanel`.
- **useChartOptions.ts** — Builds dark-mode-aware Chart.js option objects (cartesian and radial) reused across the viz panels.

#### `src/lib/` — Parsing and domain logic

- **parser.ts** — Parses raw Spotify export JSON (streaming history, library, playlists) into typed `MusicEntry` records.
- **fileTypes.ts** — Declares the expected export file types and the copy shown in `FileCard`/`StatsCard` tooltips.
- **unzip.ts** — Extracts `.json` entries from an uploaded `.zip` file.
- **monthlyStats.ts** — Top-track/top-artist helpers for a given month's entries.
- **archetypeConfig.ts** — Band/weight configuration behind the receptiveness, responsiveness, and deliberate listening-archetype scores.
- **utils.ts** — Tailwind class-merge helper (`cn()`).

#### `src/visualisations/` — Chart rendering

- **chart-setup.ts** — Registers every Chart.js controller, scale, and plugin the app uses so they're available globally.
- **ChartDisplay.vue** — Generic renderer that reads a selected chart type from the Pinia store; not currently used by any view (superseded by the audience-specific viz panels).
- **UploadStatusViz.vue** — "We're processing your upload" placeholder screen; not currently routed anywhere.

#### `src/stores/` — State management (Pinia)

- **data.ts** — The core store. Parses and de-duplicates uploaded files (`loadFiles`), and derives all listening-time, library-vs-algorithm, and archetype-score computeds consumed across the app.
- **visualisation.ts** — Holds the `selectedChart` ref written by `ControlsPanel`; currently has no reader (`ChartDisplay` is unused).
- **counter.ts** — Boilerplate example store, not currently used.

#### `explorations/` — Python analysis notebooks

Standalone Python scripts used for early-stage data exploration of Spotify JSON exports. They load playlist and streaming history files, build pandas DataFrames, and produce charts (saved to `explorations/images/`). These aren't part of the web app — they're reference material for understanding the data.
