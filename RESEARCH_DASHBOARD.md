# Spotify Unpacked: Research Dashboard

## 2026 FFAM-MDAP Research Collaboration

This document provides a comprehensive overview of the technical structure and research capabilities of the Spotify Unpacked instrument.

---

## Requirements

To enable the emotion mapping and temporal trend features, the following file must be present in the project:
- **`emotion_map.json`**: This file contains the dual-dataset mapping logic (Ekman/Thayer). 
  - **Source**: Downloadable from the project **OneDrive**.
  - **Location**: Place this file in the `public/` directory (or ensure it is uploaded via the Data Panel if implemented as a runtime requirement).

---

## Project Structure

```
spotify-unpacked/
├── download/                     # Download instructions for Spotify data
├── e2e/                          # End-to-end tests (Playwright)
├── explorations/                  # Python research & logic prototyping
├── public/                        # Static assets
├── src/
│   ├── __tests__/                 # Unit tests (Vitest)
│   ├── assets/
│   │   └── main.css               # Design system & global styles
│   ├── components/
│   │   ├── AppHeader.vue          # Top navigation & theme controls
│   │   ├── ControlsPanel.vue      # View selection & global research controls
│   │   ├── DataPanel.vue          # Functional Spotify JSON upload & data stats
│   │   ├── VisualisationPanel.vue # Dashboard layout wrapper
│   │   └── ui/                    # shadcn-vue primitive components
│   ├── lib/
│   │   └── utils.ts               # Style utility helpers
│   ├── router/
│   │   └── index.ts               # App routing logic
│   ├── stores/
│   │   ├── data.ts                # CORE: Data processing, emotion mapping & academic dates
│   │   └── visualisation.ts       # UI state management
│   ├── views/
│   │   └── DashboardView.vue      # Main research layout
│   ├── visualisations/
│   │   ├── ChartDisplay.vue      # Primary chart engine & custom plugins
│   │   └── chart-setup.ts        # Chart.js global configuration
│   ├── App.vue                    # Root application component
│   └── main.ts                    # Entry point
└── vite.config.ts                 # Build & development configuration
```

### Key Areas

#### `src/views/` — Pages

- **DashboardView** — The primary research interface. Lays out three horizontally resizable panels (Data, Visualisation, Controls) to maximize temporal data visibility.

#### `src/components/` — UI building blocks

- **AppHeader** — Site title, theme toggle, and research methodology overview.
- **DataPanel** — A functional drop-zone for Spotify Extended Streaming History. It processes all data locally in the browser and provides real-time dataset coverage statistics.
- **VisualisationPanel** — Central wrapper that renders the active research chart within a high-fidelity container.
- **ControlsPanel** — View selector for switching between 8 different research-grade visualisations.

#### `src/visualisations/` — Chart rendering

- **ChartDisplay.vue** — The dashboard engine. It reads mapping data from Pinia and implements custom Chart.js plugins for the synchronized temporal needle, emotion background blending, automated shift detection, and non-obstructive academic headers.
- **chart-setup.ts** — Registers global Chart.js components, scales (including `TimeScale`), and the `annotationPlugin`.

#### `src/stores/` — State management

- **data.ts** — The core of the instrument. Handles the merging of streaming files, the dual-dataset emotion mapping logic, and the calculation of UniMelb academic stress periods.
- **visualisation.ts** — Manages the active view state and temporal synchronization across all chart instances.

---

## Key Research Features

### 1. Advanced Temporal Analysis
- **Emotion Trends**: Tracks emotional occupancy over time using both Ekman and Thayer mappings.
- **Mixed-Emotion Backgrounds**: Dynamic background shading reflecting weighted emotion blending.
- **Emotion Shift Indicators**: Automated marking (🔄) of significant emotional transitions.

### 2. High-Precision Metrics
- **Sentiment Deviation**: A "tug-of-war" comparison of positive and negative valence.
- **Match Coverage**: Real-time audit of **Observed** vs. **Imputed** data quality.
- **Precision Hover**: 2-decimal percentage tooltips synchronized across all views.

### 3. Academic Context
- **UniMelb Calendar**: Automated SWOTVAC and Exam period tracking.
- **Header Positioning**: Academic dates are displayed above the data area to prevent visual interference.
