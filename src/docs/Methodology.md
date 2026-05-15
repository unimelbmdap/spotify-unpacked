# Research Methodology: Spotify Unpacked

This document details the data science and visualization principles used in this tool to transform raw Spotify Streaming History into a high-fidelity research instrument.

## 1. Emotion Mapping Datasets

The tool utilizes two distinct models to interpret emotional content, allowing for cross-verification between "what the lyrics say" and "how the music sounds."

### Semantic Model (500k Dataset)
*   **Source:** Ekman-derived classification trained on a corpus of 500,000 song lyrics.
*   **Emotions:** JOY, LOVE, SURPRISE, SADNESS, ANGER, FEAR.
*   **Focus:** Captures the literal meaning, storytelling, and sentiment of the lyrics.

### Acoustic Model (278k Dataset)
*   **Source:** Thayer-derived classification trained on 278,000 tracks using Spotify Audio Features.
*   **Emotions:** HAPPY, ENERGETIC, SAD, CALM.
*   **Focus:** Captures the "vibe" of the music—energy levels, tempo, danceability, and musical valence.

## 2. Temporal Visualization Logic

### Mixed Emotion Shading
The background color of the temporal charts represents a **weighted blend** of the dominant emotions present on that day. 
*   **Calculation:** If a day consists of 70% JOY (Yellow) and 30% SADNESS (Blue), the background will render as a soft mix of these primary colors.
*   **Purpose:** This allows researchers to immediately identify periods of emotional "ambivalence" or conflict (e.g., happy music with sad lyrics).

### Peak & Shift Detection
*   **Weekly Peaks:** Marked with the dominant emotion emoji, these represent the highest emotional intensity for a 7-day rolling window.
*   **Emotion Shifts (⚡):** Indicated by a bolt icon, these markers appear when the dominant emotion changes significantly from the previous period, highlighting pivot points in a participant's listening history.

## 3. Academic Shading
To ground the data in a student's lived experience, UniMelb academic dates are overlaid on the timeline:
*   **SWOTVAC (Yellow):** Study periods leading up to exams.
*   **EXAMS (Pink/Red):** Formal examination periods.
This allows researchers to see how academic stress correlates with emotional listening patterns.

## 4. Data Imputation
When raw streaming data lacks a direct emotion match (e.g., niche tracks), the tool uses **persistence-based imputation**. It assumes that if a user is listening to a specific playlist or in a specific session, the surrounding emotional state likely persists. This "fills the gaps" to provide a continuous narrative for qualitative analysis.
