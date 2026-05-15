# Component & Visualization Guide

This document describes the key Vue components and the custom visualization logic used in the Spotify Unpacked instrument.

## 🧱 Core Components

### `BehavioralProfileCard.vue`
- **Purpose**: Displays the Layer 2 behavioral profile using the **Banded Model**.
- **Props**: `profile: BehavioralProfile`.
- **Visuals**: Displays Skip, Shuffle, and Selection scores mapped into color-coded bands (Low/Medium/High). Includes Platform Context detection.

### `AuditView.vue`
- **Purpose**: The **Behavioral Audit Sandbox** interface.
- **Function**: Allows researchers to toggle between different subject audit summaries (`audit_summary_{id}.json`) to validate classification logic.

### `DataPanel.vue`
- **Purpose**: The primary data entry point.
- **Logic**: Handles local file parsing and triggers the mapping logic in `DataStore`.

### `VisualisationPanel.vue`
- **Purpose**: A responsive wrapper for the active chart. Ensures the dashboard layout remains stable during resizes.

---

## 🎭 Presentation Layer (Layer 3)

Located in `src/components/presentation/`, these components visualize the **Emotion Regulation Profiles**.

### `UserDirectory.vue`
- **Purpose**: A searchable table of all subject profiles (`student_profiles.csv`).
- **Function**: Allows researchers to select a participant to view their detailed regulation persona.

### `ProfileOverview.vue`
- **Purpose**: The "Face" of the Emotion Regulation Profile.
- **Visuals**: Displays the persona label (e.g., *The Processor*), detailed description, and qualitative bands (Intentionality, Range, Pressure).
- **Confidence**: Visualizes the **Actuarial Weight (Z)** to indicate classification reliability.

### `ThresholdCalibration.vue`
- **Purpose**: A research utility to visualize the distribution of metrics across the cohort.
- **Function**: Helps researchers tune the thresholds used in `models.py` and the Python pipeline.

---

## 📊 Chart.js Visualizations (`ChartDisplay.vue`)

We use several custom plugins to enhance the research capabilities of standard Chart.js charts.

### 1. `peakAndShiftPlugin`
- **Peaks**: Automatically identifies 7-day peaks for each emotion and displays the corresponding emoji.
- **Shifts (🔄)**: Detects when a new emotion becomes dominant.

### 2. `emotionBackgroundPlugin`
- **Mixed Shading**: Dynamically blends the background colors of the chart based on the weighted emotional occupancy of all active datasets.

### 3. `needlePlugin`
- **Synchronized Cursor**: Renders a vertical line across all charts (Line and Bar) that follows the user's focus, allowing for cross-metric comparison at a specific point in time.

### 4. `annotationPlugin` (Academic Context)
- Renders labeled boxes for SWOTVAC and Exams above the 100% line, ensuring research context is always visible without obstructing the data.

---

## 🎨 Design System

The app uses **Tailwind CSS** and **shadcn-vue** for its UI primitives.
- **Colors**: Curated HSL palettes for both Light and Dark modes.
- **Typography**: Inter (Sans) and Mono fonts for data readability.
- **Theming**: Controlled via `useDark()` from `@vueuse/core`.
