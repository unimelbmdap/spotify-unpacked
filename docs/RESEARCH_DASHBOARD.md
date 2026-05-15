# Spotify Unpacked: Research Dashboard

## 2026 FFAM-MDAP Research Collaboration

> [!TIP]
> View the complete [**Documentation Hub**](file:///d:/Github/spotify-unpacked/docs/DOCUMENTATION_MAP.md) for detailed research methodologies and technical guides.

This document provides a high-level overview of the technical structure and research capabilities of the Spotify Unpacked instrument.

---

## Requirements

To enable the emotion mapping and temporal trend features, the following file must be present in the project:
- **`emotion_map.json`**: This file contains the dual-dataset mapping logic (Ekman/Thayer). 
  - **Source**: Generated via `kaggle/build_emotion_map.py` or downloaded from OneDrive.
  - **Location**: Place this file in the `public/` directory.

---

## Project Structure

```
spotify-unpacked/
├── docs/                         # NEW: Project Documentation Hub
├── e2e/                          # End-to-end tests (Playwright)
├── research_pipeline/          # NEW: Core research & profiling pipeline
│   ├── .env                    # Calibrated thresholds for Pydantic models
│   ├── core/                   # Shared Pydantic models (models.py)
│   ├── scripts/                # Active behavioral & emotional scripts
│   ├── input_data/             # Subject data folders (ama, angie, etc.)
│   └── local_reports/          # Generated local audit charts (PNG)
├── kaggle/
│   └── build_emotion_map.py      # Script to generate emotion_map.json
├── public/                        # Static assets
│   ├── data/                      # AUTOMATED: JSON summaries (Vue source)
│   └── emotion_map.json           # Required mapping file
├── src/
│   ├── __tests__/                 # Unit tests (Vitest)
│   ├── assets/
│   │   └── main.css               # Design system & global styles
│   ├── components/
│   │   ├── AppHeader.vue          # Top navigation & theme controls
│   │   ├── BehavioralProfileCard.vue # NEW: Banded behavioral visualization
│   │   ├── ControlsPanel.vue      # View selection & global research controls
│   │   ├── DataPanel.vue          # Spotify JSON upload & data stats
│   │   ├── DownloadHelp.vue       # Instructions for Spotify data export
│   │   ├── FileDropZone.vue       # Interactive data ingest component
│   │   ├── StatsCard.vue          # Dataset coverage reporting
│   │   ├── VisualisationPanel.vue # Dashboard layout wrapper
│   │   ├── presentation/          # High-level presentation components
│   │   ├── ui/                    # shadcn-vue primitive components
│   │   └── wrapped/               # "Wrapped" style summary components
│   ├── composables/
│   │   └── useAuditSummary.ts     # NEW: Summary data loading logic
│   ├── stores/
│   │   ├── data.ts                # CORE: Temporal mapping & academic logic
│   │   └── visualisation.ts       # UI state management
│   ├── views/
│   │   ├── DashboardView.vue      # Primary temporal research layout
│   │   └── AuditView.vue          # NEW: Behavioral Audit Sandbox
│   ├── visualisations/
│   │   ├── ChartDisplay.vue       # Primary chart engine & custom plugins
│   │   └── chart-setup.ts         # Chart.js global configuration
│   ├── App.vue                    # Root application component
│   └── main.ts                    # Entry point
└── vite.config.ts                 # Build & development configuration
```

---

## Key Research Features

### 1. Advanced Temporal Analysis (Layer 1)
- **Emotion Trends**: Tracks emotional occupancy over time using both Ekman and Thayer mappings.
- **Mixed-Emotion Backgrounds**: Dynamic background shading reflecting weighted emotion blending.
- **Academic Context**: Automated UniMelb SWOTVAC and Exam period tracking.

### 2. Behavioral Profiling (Layer 2)
The instrument now supports a **Banded Behavioral Model** that transforms raw signals into qualitative labels:
- **Banded Signals**: Raw Skip, Shuffle, and Active Selection scores are mapped into Low/Medium/High bands.
- **Active Selection Metric**: Redefines "Deliberate" behavior using `SearchQueries.json` follow-through rather than simple playback codes.
- **Platform Context**: Automated detection of primary platform (iOS, Desktop, Connected Devices).

### 3. High-Precision Metrics
- **Sentiment Deviation**: A "tug-of-war" comparison of positive and negative valence.
- **Match Coverage**: Real-time audit of **Observed** vs. **Imputed** data quality.
- **Precision Hover**: 2-decimal percentage tooltips synchronized across all views.

---

## Key Areas

#### `src/views/` — Pages
- **DashboardView** — The primary research interface. Lays out three horizontally resizable panels (Data, Visualisation, Controls) to maximize temporal data visibility.
- **AuditView** — The Behavioral Audit Sandbox. Loads pre-processed behavioral summaries to validate "Banded" research labels.

#### `src/components/` — UI building blocks
- **AppHeader** — Site title, theme toggle, and research methodology overview.
- **DataPanel** — A functional drop-zone for Spotify Extended Streaming History. It processes all data locally in the browser and provides real-time dataset coverage statistics.
- **VisualisationPanel** — Central wrapper that renders the active research chart within a high-fidelity container.
- **ControlsPanel** — View selector for switching between 8 different research-grade visualisations.
- **BehavioralProfileCard** — Renders the Layer 2 behavioral profile, including Skip/Shuffle/Selection bands and platform context.
- **FileDropZone** — Component for local browser-side processing of large Spotify JSON exports.
- **StatsCard** — Provides visual feedback on data sufficiency and coverage.

#### `src/visualisations/` — Chart rendering
- **ChartDisplay.vue** — The dashboard engine. It reads mapping data from Pinia and implements custom Chart.js plugins for the synchronized temporal needle, emotion background blending, automated shift detection, and non-obstructive academic headers.
- **chart-setup.ts** — Registers global Chart.js components, scales (including `TimeScale`), and the `annotationPlugin`.

#### `src/stores/` — State management
- **data.ts** — The core of the instrument. Handles the merging of streaming files, the dual-dataset emotion mapping logic, and the calculation of UniMelb academic stress periods.
- **visualisation.ts** — Manages the active view state and temporal synchronization across all chart instances.

---

## Data Pipeline & Automation (`research_pipeline/`)

The instrument relies on an automated research pipeline to prepare data for the dashboard.

### 1. Behavioral & Emotional Profiling
- **`scripts/audit_profiling.py`**: The behavioral engine. Maps skips, shuffle, and selection into the Banded Model.
- **`scripts/emotion_profiles.py`**: Assigns Layer 3 Emotion Regulation Personas (e.g., *The Processor*).
- **`scripts/visualization.py`**: Generates PNG charts for local research auditing.
- **`scripts/calibrate_thresholds.py`**: Statistical utility to tune bands based on cohort quartiles.
- **Automated Deployment**: JSON summaries are saved directly to `public/data/` for immediate Vue dashboard consumption.

### 2. Emotion Mapping Generation
The core mapping logic for Ekman and Thayer emotions is pre-processed in the `kaggle/` folder:
- **Script**: `kaggle/build_emotion_map.py`
- **Output**: Automatically deploys `public/emotion_map.json`.
