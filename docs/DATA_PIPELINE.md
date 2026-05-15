# Data Pipeline & Processing

The Spotify Unpacked pipeline transforms raw JSON exports from Spotify into the research-grade data consumed by the Vue dashboard.

## 1. Raw Data Ingestion

The instrument expects files from the **Spotify Extended Streaming History** export:
- `Streaming_History_Audio_*.json`
- `Playlist.json`
- `YourLibrary.json`

## 2. Python Pre-processing (`research_pipeline/`)

The instrument uses a dedicated research pipeline to transform raw data into behavioral and emotional profiles.

### `scripts/audit_profiling.py`
- **Purpose**: Analyzes streaming history for behavioral shares (Skip, Shuffle, Selection).
- **Output**: Automatically deploys `audit_summary_{id}.json` to `public/data/`.
- **Visualization**: Automatically triggers `visualization.py`.

### `scripts/visualization.py`
- **Purpose**: Generates PNG charts (Heatmaps, Taxonomy, Source) for local research auditing.
- **Output**: Saves plots to `local_reports/` and updates `audit_visual_report.md`.

### `scripts/calibrate_thresholds.py`
- **Purpose**: Calculates cohort-wide quartiles to calibrate the "Low/Medium/High" bands.
- **Output**: Automatically updates the pipeline `.env` file with new threshold values.

### `scripts/emotion_profiles.py`
- **Purpose**: Calculates the **Emotion Regulation Profile** (e.g., The Processor, The Uplifter).
- **Output**: Automatically deploys `student_profiles.json` to `public/data/`.

### `kaggle/build_emotion_map.py` (Manual Step)
- **Purpose**: Merges Kaggle datasets into an optimized lookup table.
- **Output**: Deploys `public/emotion_map.json`.

---

## 3. Frontend Data Flow

Once files are uploaded to the `DataPanel.vue`, the following process occurs in `src/stores/data.ts`:

### Mapping Logic
1. **URI Match**: Tracks are first checked against the `uri_map` (278k dataset).
2. **Name Match**: If no URI match, it checks `name_map` (Track Name + Artist Name) against the 500k dataset.
3. **Niche Fallback**: If neither matches, the track is tagged as `niche_selection`.

### Imputation
For tracks that are unmapped, the instrument performs a **Nearest-Neighbor Imputation**:
- It carries forward the previous known emotional state to fill gaps.
- This allows for a continuous "Timeline of Affect" even when Spotify's metadata is incomplete.
- Imputed data is visually distinct (Amber) in the **Match Coverage** chart.

---

## 4. JSON Schemas

### `audit_summary_{id}.json`
```json
{
  "behavioral_profile": {
    "behavioral_label_primary": "Deliberate",
    "classification_confidence": "High",
    "receptive_share": 0.15,
    "responsive_share": 0.25,
    "deliberate_share": 0.60,
    "behavioral_basis_note": "Driven primarily by library interactions..."
  }
}
```

### `emotion_map.json`
```json
{
  "uri_map": {
    "spotify:track:123...": { "emotion_mapped": "calm", "valence": 0.8, "arousal": 0.2 }
  },
  "name_map": {
    "track name|||artist name": { "emotion_mapped": "joy" }
  }
}
```
