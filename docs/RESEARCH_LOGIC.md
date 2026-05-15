# Research Logic & Methodologies

This document outlines the theoretical frameworks and analytical logic used to transform raw Spotify data into behavioral and emotional insights.

## 1. Behavioral Taxonomies (Banded Model)

The instrument classifies listening sessions into four provisional categories using a **Banded Model**. Raw behavioral signals are mapped into `Low`, `Medium`, or `High` levels before a final label is assigned.

### Primary Signal Families
- **Skip Rate**: A proxy for "Listening Friction". High skip rates suggest active rejection of content.
- **Shuffle Rate**: A proxy for "Curation Reliance". High shuffle suggest the user is relying on randomized discovery.
- **Active Selection**: A proxy for "Intentionality". Calculated using `SearchQueries.json` follow-through and manual `clickrow`/`playbtn` events.

| Category | Description | Banding Logic |
| :--- | :--- | :--- |
| **Receptive (Provisional)** | Passive listening, algorithmically driven. | Low skip + Low active selection. |
| **Responsive (Provisional)** | High-interaction, mood-adjusting listening. | High skip + Medium/High shuffle. |
| **Deliberate (Provisional)** | High-intent, active selection. | High active selection score + Low friction. |
| **Mixed (Provisional)** | Conflicting signals. | All other combinations. |

---

## 2. Emotion Mapping Frameworks

We use two distinct datasets to map tracks to emotional states:

### Ekman Model (500k Dataset)
Maps tracks to 6 discrete emotional states:
- **Joy**, **Love**, **Surprise**, **Sadness**, **Anger**, **Fear**.
- *Usage*: Primarily used for high-level sentiment tracking and "Tug of War" valence analysis.

### Thayer Model (278k Dataset)
Maps tracks to a 2D circumplex model of affect (Valence/Arousal):
- **Happy** (High Valence, High Arousal)
- **Energetic** (Low Valence, High Arousal)
- **Sad** (Low Valence, Low Arousal)
- **Calm** (High Valence, Low Arousal)
- *Usage*: Used for temporal "mood" trends and precision behavioral profiling.

---

## 3. Academic Context (UniMelb)

The instrument automatically identifies "Academic Stress Periods" based on the University of Melbourne calendar:
- **SWOTVAC**: Transition periods before exams (often marked by high-arousal or repetitive listening).
- **Exams**: High-stakes periods (often marked by "Calm" or "Deep-Focus" profiles).

### Date Mapping
The logic is located in `src/stores/data.ts` in the `getAcademicDates(year)` function. It uses approximate dates (e.g., SWOTVAC starts ~May 24 for S1).

---

## 4. Advanced Metrics

### Emotion Shift Detection (🔄)
An automated detection of significant transitions in dominant emotional occupancy.
- **Logic**: Triggered when a new emotion takes a lead of >10% over the previous dominant emotion, with a cooldown of at least 5 days to prevent noise.

### High-Arousal Dissonance
Detected when there is a significant mismatch between the user's usual "Baseline" and a sudden spike in high-arousal tracks (Anger/Fear/Energetic), often correlating with academic deadlines.

---

## 5. Emotion Regulation Profiles (Layer 3)

The instrument assigns high-level "Regulation Personas" based on a combination of emotional occupancy, entropy (diversity), and temporal spikes.

| Profile | Description | Primary Triggers |
| :--- | :--- | :--- |
| **The Processor** | Uses music to sit with and process heavy feelings. | High "Heavy" share + Anchor track reliance. |
| **The Uplifter** | Uses music to energize and reset mood. | High "Upbeat" share + High Valence. |
| **The Stabiliser** | Uses music for steadiness and familiarity. | Low emotional entropy + High anchor routines. |
| **The Explorer** | Flexible, dynamic music use. | High emotional entropy + Wide range. |
| **The Time-Specific** | Contextual/Routine dependent listening. | Extreme daypart or exam-season concentrations. |

### Precedence Model
Because users often show multiple traits, the profiling script (`generate_profiles.py`) implements a **Precedence Model**. For example, a massive Exam spike (Time-Specific) will override a general "Uplifter" tendency to highlight the most statistically significant behavioral deviation.
