import pandas as pd

def generate_profiles():
    print("Loading wrapped aggregate measures and elicitation tables...")
    try:
        measures_df = pd.read_csv('wrapped_aggregate_measures.csv')
        emotions_df = pd.read_csv('elicitation_emotions.csv')
        periods_df = pd.read_csv('elicitation_periods.csv')
    except FileNotFoundError:
        print("Error: Could not find required CSV files. Run generate_wrapped_layer.py and the elicitation step first.")
        return

    profiles = []
    disclaimer = "Note: This profile is descriptive, not diagnostic, and is based on listening patterns, not mental health assessment."

    for pid in measures_df['person_id'].unique():
        user_measures = measures_df[measures_df['person_id'] == pid].set_index('metric_name')['metric_value_num'].to_dict()
        user_emo = emotions_df[emotions_df['person_id'] == pid]
        user_periods = periods_df[periods_df['person_id'] == pid]
        
        # Load precomputed aggregates
        coverage = user_measures.get('match_coverage_percent', 0)
        heavy_share = user_measures.get('heavy_share', 0)
        upbeat_share = user_measures.get('upbeat_share', 0)
        anchor_days = user_measures.get('anchor_song_days', 0)
        intentionality = user_measures.get('intentionality_score', 0)
        exam_share = user_measures.get('exam_peak_share', 0)
        top2_share = user_measures.get('top2_emotion_share', 0)
        
        # Pull diversity directly from emotions table
        diversity = user_emo.iloc[0]['emotional_diversity'] if not user_emo.empty else 0
        
        # Compute numeric daypart share safely
        if not user_periods.empty:
            daypart_cols = ['share_late_night', 'share_morning', 'share_afternoon', 'share_evening', 'share_night']
            available_cols = [c for c in daypart_cols if c in user_periods.columns]
            dominant_daypart_share = user_periods[available_cols].mean().max() if available_cols else 0
        else:
            dominant_daypart_share = 0

        # --- SUB-SCORES ---
        intent_band = "High" if intentionality > 15 else "Moderate" if intentionality >= 5 else "Low"
        range_band = "Wide-ranging" if diversity >= 5 else "Balanced" if diversity == 4 else "Narrow"
        pressure_band = "High" if exam_share > 0.50 else "Moderate" if exam_share >= 0.25 else "Low"

        # --- PRECEDENCE LOGIC ---
        profile_label = ""
        profile_desc = ""
        profile_basis = ""

        if coverage < 15.0:
            profile_label = "Provisional Profile"
            profile_desc = "Your matched listening is currently too sparse to confidently determine a distinct emotion regulation style. The patterns below are based on the small portion of your listening we could match."
            profile_basis = f"Coverage triggered low-confidence fallback ({coverage:.1f}%)."
            
        elif dominant_daypart_share > 0.60 or exam_share > 0.40:
            profile_label = "The Time-Specific Listener"
            profile_desc = "Your profile suggests highly contextual music use. Whether it's a dominant daily rhythm or a massive spike during exam season, you seem to rely on music most heavily for specific routines or high-pressure periods."
            profile_basis = "Triggered by extreme daypart concentration or high exam-season reliance."
            
        elif heavy_share > 0.40 and anchor_days > 15:
            profile_label = "The Processor"
            profile_desc = "Your listening may help you sit with and process feelings. With a reliance on heavier/introspective moods and familiar anchor songs, your profile suggests music may support reflection during heavier emotional periods."
            profile_basis = "Triggered by dominance of heavy emotions and returning to anchor songs."
            
        elif upbeat_share > 0.50 and heavy_share < 0.20:
            profile_label = "The Uplifter"
            profile_desc = "Your listening leans heavily toward energizing and resetting. Your strong upbeat profile suggests you frequently use music as a tool to lift your mood or maintain high energy."
            profile_basis = "Triggered by strong dominance of upbeat emotions."
            
        elif diversity <= 3 and (anchor_days > 20 or intentionality > 10):
            profile_label = "The Stabiliser"
            profile_desc = "Music seems to act as a stabilizer for you. By sticking to a narrower emotional range and returning frequently to deliberate anchor songs, you appear to use music to create steadiness and familiarity."
            profile_basis = "Triggered by narrow emotional range combined with strong anchor routines."
            
        elif diversity >= 4 and top2_share < 0.60:
            profile_label = "The Explorer"
            profile_desc = "Your profile shows highly flexible music use. By spanning a wide emotional range without getting locked into a single mood, you seem to adapt your music choices dynamically to whatever the situation demands."
            profile_basis = "Triggered by high emotional diversity without extreme concentrations."
            
        else:
            profile_label = "Mixed / Emerging Pattern"
            profile_desc = "Your listening habits show a blend of different routines and emotional styles without one overwhelming tendency. You seem to use music flexibly across various contexts."
            profile_basis = "Fallback profile; no specific regulation style was dominant."

        profiles.append({
            'person_id': pid,
            'profile_label': profile_label,
            'profile_description': profile_desc,
            'intentionality_band': intent_band,
            'emotional_range_band': range_band,
            'pressure_signal_band': pressure_band,
            'match_coverage_percent': coverage,
            'profile_basis_note': profile_basis,
            'disclaimer': disclaimer
        })

    pd.DataFrame(profiles).to_csv('student_profiles.csv', index=False)
    print("Successfully generated student_profiles.csv")

if __name__ == "__main__":
    generate_profiles()
