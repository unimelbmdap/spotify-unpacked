import pandas as pd

def generate_profiles():
    print("Loading wrapped aggregate measures and elicitation tables...")
    try:
        measures_df = pd.read_csv('wrapped_aggregate_measures.csv')
    except FileNotFoundError:
        print("Error: Could not find required CSV files. Run generate_wrapped_layer.py first.")
        return

    profiles = []
    disclaimer = "Note: This profile is descriptive, not diagnostic, and is based on listening patterns, not mental health assessment."

    for pid in measures_df['person_id'].unique():
        user_measures = measures_df[measures_df['person_id'] == pid].set_index('metric_name')['metric_value_num'].to_dict()
        
        # Load Raw Metrics
        coverage_raw = user_measures.get('match_coverage_percent_raw', 0)
        heavy_raw = user_measures.get('heavy_share_raw', 0)
        upbeat_raw = user_measures.get('upbeat_share_raw', 0)
        diversity_raw = user_measures.get('emotional_diversity_raw', 0)
        intent_raw = user_measures.get('intentionality_score_raw', 0)
        top2_raw = user_measures.get('top2_emotion_share_raw', 0)
        exam_peak_share_raw = user_measures.get('exam_peak_share_raw', 0)
        
        # Load Actuarial Companions
        coverage_conf = user_measures.get('coverage_cred_conf', 0)
        heavy_cred = user_measures.get('heavy_share_cred', 0)
        upbeat_cred = user_measures.get('upbeat_share_cred', 0)
        exam_tail_ratio = user_measures.get('exam_tail_ratio', 0)
        daypart_conc_tail = user_measures.get('daypart_conc_tail', 0)
        anchor_exposure_tail = user_measures.get('anchor_exposure_tail', 0)
        emotion_entropy_exp = user_measures.get('emotion_entropy_exp', 0)
        emotion_conc_tail = user_measures.get('emotion_conc_tail', 0)
        intent_cred = user_measures.get('intentionality_score_cred', 0)

        # --- SUB-SCORES ---
        intent_band = "High" if intent_cred > 15 else "Moderate" if intent_cred >= 5 else "Low"
        range_band = "Wide-ranging" if (diversity_raw >= 5 and emotion_entropy_exp > 2.0) else "Narrow" if (diversity_raw <= 3 and emotion_entropy_exp < 1.5) else "Balanced"
        pressure_band = "High" if exam_tail_ratio > 2.0 else "Moderate" if exam_tail_ratio >= 1.2 else "Low"

        # --- PRECEDENCE LOGIC (DUAL TRIGGER) ---
        profile_label = ""
        profile_desc = ""
        profile_basis = ""

        if coverage_raw < 15.0 or coverage_conf < 0.15:
            profile_label = "Provisional Profile"
            profile_desc = "Your matched listening is currently too sparse to confidently determine a distinct emotion regulation style. The patterns below are based on the small portion of your listening we could match."
            profile_basis = f"Coverage triggered low-confidence fallback (Raw: {coverage_raw:.1f}%, Cred: {coverage_conf:.2f})."
            
        elif daypart_conc_tail > 0.60 or exam_tail_ratio > 2.0:
            profile_label = "The Time-Specific Listener"
            profile_desc = "Your profile suggests highly contextual music use. Whether it's a dominant daily rhythm or a massive spike during exam season, you seem to rely on music most heavily for specific routines or high-pressure periods."
            profile_basis = f"Triggered by extreme daypart concentration ({daypart_conc_tail*100:.1f}%) or high exam-tail ratio ({exam_tail_ratio:.2f})."
            
        elif heavy_raw > 0.35 and heavy_cred > 0.30 and anchor_exposure_tail > 0.05:
            profile_label = "The Processor"
            profile_desc = "Your listening may help you sit with and process feelings. With a reliance on heavier/introspective moods and familiar anchor songs, your profile suggests music may support reflection during heavier emotional periods."
            profile_basis = f"Triggered by dominance of heavy emotions (Raw: {heavy_raw*100:.1f}%, Cred: {heavy_cred*100:.1f}%) and anchor exposure ({anchor_exposure_tail*100:.1f}%)."
            
        elif upbeat_raw > 0.45 and upbeat_cred > 0.40:
            profile_label = "The Uplifter"
            profile_desc = "Your listening leans heavily toward energizing and resetting. Your strong upbeat profile suggests you frequently use music as a tool to lift your mood or maintain high energy."
            profile_basis = f"Triggered by strong dominance of upbeat emotions (Raw: {upbeat_raw*100:.1f}%, Cred: {upbeat_cred*100:.1f}%)."
            
        elif emotion_entropy_exp < 1.5 and anchor_exposure_tail > 0.10:
            profile_label = "The Stabiliser"
            profile_desc = "Music seems to act as a stabilizer for you. By sticking to a narrower emotional range and returning frequently to deliberate anchor songs, you appear to use music to create steadiness and familiarity."
            profile_basis = f"Triggered by narrow emotional entropy ({emotion_entropy_exp:.2f}) combined with strong anchor routines ({anchor_exposure_tail*100:.1f}%)."
            
        elif diversity_raw >= 4 and emotion_entropy_exp > 2.0 and emotion_conc_tail < 0.50:
            profile_label = "The Explorer"
            profile_desc = "Your profile shows highly flexible music use. By spanning a wide emotional range without getting locked into a single mood, you seem to adapt your music choices dynamically to whatever the situation demands."
            profile_basis = f"Triggered by high emotional entropy ({emotion_entropy_exp:.2f}) without extreme concentrations (Tail: {emotion_conc_tail:.2f})."
            
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
            'match_coverage_percent': coverage_raw,
            'profile_basis_note': profile_basis,
            'profile_conf': coverage_conf,
            'heavy_share_raw': heavy_raw,
            'heavy_share_cred': heavy_cred,
            'upbeat_share_raw': upbeat_raw,
            'upbeat_share_cred': upbeat_cred,
            'exam_peak_share_raw': exam_peak_share_raw,
            'exam_tail_ratio': exam_tail_ratio,
            'disclaimer': disclaimer
        })

    pd.DataFrame(profiles).to_csv('student_profiles.csv', index=False)
    print("Successfully generated student_profiles.csv")

if __name__ == "__main__":
    generate_profiles()
