import pandas as pd
import os
import json
import sys

# Add parent directory for core.models import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.models import emotion_settings

# CONFIGURATION
INPUT_CSV_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "input_data")
OUTPUT_JSON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "public", "data")

def generate_emotion_profiles():
    print("Loading wrapped aggregate measures...")
    measures_path = os.path.join(INPUT_CSV_DIR, 'wrapped_aggregate_measures.csv')
    try:
        measures_df = pd.read_csv(measures_path)
    except FileNotFoundError:
        print(f"Error: Could not find {measures_path}. Run wrapped_layer.py first.")
        return

    profiles = []
    disclaimer = "Note: This profile is descriptive, not diagnostic, and is based on listening patterns, not mental health assessment."

    for pid in measures_df['person_id'].unique():
        user_m = measures_df[measures_df['person_id'] == pid].set_index('metric_name')['metric_value_num'].to_dict()
        
        # Extract metrics (with defaults)
        coverage_raw = user_m.get('match_coverage_percent_raw', 0)
        coverage_conf = user_m.get('coverage_cred_conf', 0)
        heavy_raw = user_m.get('heavy_share_raw', 0)
        heavy_cred = user_m.get('heavy_share_cred', 0)
        upbeat_raw = user_m.get('upbeat_share_raw', 0)
        upbeat_cred = user_m.get('upbeat_share_cred', 0)
        diversity_raw = user_m.get('emotional_diversity_raw', 0)
        entropy_exp = user_m.get('emotion_entropy_exp', 0)
        conc_tail = user_m.get('emotion_conc_tail', 0)
        daypart_tail = user_m.get('daypart_conc_tail', 0)
        exam_ratio = user_m.get('exam_tail_ratio', 0)
        anchor_tail = user_m.get('anchor_exposure_tail', 0)
        intent_cred = user_m.get('intentionality_score_cred', 0)

        # Sub-bands
        intent_band = "High" if intent_cred > emotion_settings.intent_high_cred else "Moderate" if intent_cred >= emotion_settings.intent_moderate_cred else "Low"
        range_band = "Wide-ranging" if (diversity_raw >= 5 and entropy_exp > 2.0) else "Narrow" if (diversity_raw <= 3 and entropy_exp < 1.5) else "Balanced"
        pressure_band = "High" if exam_ratio > emotion_settings.pressure_high_exam_tail else "Moderate" if exam_ratio >= emotion_settings.pressure_moderate_exam_tail else "Low"

        # PRECEDENCE LOGIC
        label = ""
        desc = ""
        
        if coverage_raw < emotion_settings.min_coverage_raw or coverage_conf < emotion_settings.min_coverage_conf:
            label = "Provisional Profile"
            desc = "Your matched listening is currently too sparse to confidently determine a distinct emotion regulation style."
        elif daypart_tail > emotion_settings.time_specific_daypart_tail or exam_ratio > emotion_settings.pressure_high_exam_tail:
            label = "The Time-Specific Listener"
            desc = "Your profile suggests highly contextual music use, relying heavily on specific routines or high-pressure periods."
        elif heavy_raw > emotion_settings.processor_heavy_raw and heavy_cred > emotion_settings.processor_heavy_cred and anchor_tail > emotion_settings.processor_anchor_tail:
            label = "The Processor"
            desc = "Your listening may help you sit with and process feelings, using music for reflection during heavier emotional periods."
        elif upbeat_raw > emotion_settings.uplifter_upbeat_raw and upbeat_cred > emotion_settings.uplifter_upbeat_cred:
            label = "The Uplifter"
            desc = "Your strong upbeat profile suggests you frequently use music as a tool to lift your mood or maintain high energy."
        elif entropy_exp < emotion_settings.stabiliser_entropy_max and anchor_tail > emotion_settings.stabiliser_anchor_tail:
            label = "The Stabiliser"
            desc = "Music seems to act as a stabilizer for you, creating steadiness and familiarity through narrower emotional ranges."
        elif diversity_raw >= emotion_settings.explorer_diversity_min and entropy_exp > emotion_settings.explorer_entropy_min and conc_tail < emotion_settings.explorer_conc_tail_max:
            label = "The Explorer"
            desc = "Your profile shows highly flexible music use, adapting choices dynamically across a wide emotional range."
        else:
            label = "Mixed / Emerging Pattern"
            desc = "Your listening habits show a blend of different routines and emotional styles without one overwhelming tendency."

        profiles.append({
            'person_id': pid,
            'profile_label': label,
            'profile_description': desc,
            'intentionality_band': intent_band,
            'emotional_range_band': range_band,
            'pressure_signal_band': pressure_band,
            'profile_conf': float(coverage_conf),
            'disclaimer': disclaimer
        })

    # Save CSV locally for research audit
    local_csv = os.path.join(INPUT_CSV_DIR, 'student_profiles.csv')
    pd.DataFrame(profiles).to_csv(local_csv, index=False)
    print(f"Successfully generated {local_csv}")

    # DEPLOY TO PUBLIC FOLDER
    os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)
    
    # Save CSV (for current Vue Presentation Store)
    deploy_path_csv = os.path.join(OUTPUT_JSON_DIR, 'student_profiles.csv')
    pd.DataFrame(profiles).to_csv(deploy_path_csv, index=False)
    print(f"[!] Deployed emotion profiles CSV to '{deploy_path_csv}'")
    
    # Save JSON (for future use/backups)
    deploy_path_json = os.path.join(OUTPUT_JSON_DIR, 'student_profiles.json')
    with open(deploy_path_json, 'w') as f:
        json.dump(profiles, f, indent=4)

if __name__ == "__main__":
    generate_emotion_profiles()
