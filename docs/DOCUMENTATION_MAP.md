# Spotify Unpacked Documentation Hub

Welcome to the documentation for the Spotify Unpacked research instrument. This hub bridges the gap between the Python-based data research and the Vue-based visualisation interface.

## 📂 Documentation Structure

### 🗺️ Project Overview
- [**RESEARCH_DASHBOARD.md**](file:///d:/Github/spotify-unpacked/docs/RESEARCH_DASHBOARD.md)
  - High-level project overview and feature list.
  - Requirement checklist and technical structure.

### 🔬 Research & Methodology
- [**RESEARCH_LOGIC.md**](file:///d:/Github/spotify-unpacked/docs/RESEARCH_LOGIC.md)
  - Behavioral Taxonomies (**Banded Model**).
  - Emotion Mapping (Ekman 500k vs. Thayer 278k).
  - Academic Context (UniMelb Semester Patterns).

### ⚙️ Data Pipeline
- [**DATA_PIPELINE.md**](file:///d:/Github/spotify-unpacked/docs/DATA_PIPELINE.md)
  - Processing raw Spotify JSON exports.
  - Imputation logic and coverage auditing.
  - Python scripts overview (`explorations/`).

### 💻 Technical Implementation
- [**COMPONENTS.md**](file:///d:/Github/spotify-unpacked/src/components/COMPONENTS.md)
  - Vue Component Library (**BehavioralProfileCard**).
  - Audit Sandbox Interface (**AuditView**).
  - Chart.js Plugins (Needle, Peaks, Background Shading).
  - Pinia Stores (Data Management & Visualisation State).

---

## 🚀 Quick Start for Researchers
1. **Data Prep**: Use the Python scripts in `explorations/` to generate the `audit_summary_{id}.json` and `emotion_map.json`.
2. **Setup**: Place `emotion_map.json` in the `public/` folder.
3. **Run**: `npm run dev` to launch the dashboard.
4. **Analysis**: Upload your streaming history files to see the temporal trends and behavioral profiles.
