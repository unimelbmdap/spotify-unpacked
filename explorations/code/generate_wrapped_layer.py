import pandas as pd
import numpy as np

def generate_wrapped_layer():
    print("Loading elicitation tables...")
    try:
        songs_df = pd.read_csv('elicitation_songs.csv')
        periods_df = pd.read_csv('elicitation_periods.csv')
        emotions_df = pd.read_csv('elicitation_emotions.csv')
    except FileNotFoundError:
        print("Error: Could not find elicitation CSV files. Run the elicitation step first.")
        return

    measures = []
    cards = []

    # --- ACTUARIAL COHORT BASELINES ---
    # Compute median matched minutes (k) for credibility formula
    k_matched = emotions_df['matched_minutes'].median()
    
    # Compute cohort means for emotion shares
    cohort_heavy_share = (emotions_df['share_sad'] + emotions_df['share_sadness'] + emotions_df['share_fear']).mean()
    cohort_upbeat_share = (emotions_df['share_happy'] + emotions_df['share_joy'] + emotions_df['share_energetic']).mean()
    
    # Compute cohort mean intentionality
    all_intent_scores = []
    for pid in songs_df['person_id'].unique():
        user_songs = songs_df[songs_df['person_id'] == pid].copy()
        user_songs['intentionality_score'] = (1 - user_songs['playlist_share']) * np.log1p(user_songs['repeat_count'])
        candidates = user_songs[(user_songs['playlist_share'] < 0.2) & (user_songs['repeat_count'] >= 10)]
        if not candidates.empty:
            all_intent_scores.append(candidates['intentionality_score'].max())
    cohort_intentionality = np.mean(all_intent_scores) if all_intent_scores else 0

    # Helper function to map emotion labels for clean display
    def display_emotion_label(emotion_col):
        raw = emotion_col.replace('share_', '')
        if raw in ['sad', 'sadness']: return 'sadness'
        if raw in ['happy', 'joy']: return 'uplift'
        if raw == 'fear': return 'tension'
        if raw == 'anger': return 'intensity'
        return raw

    for pid in songs_df['person_id'].unique():
        user_songs = songs_df[songs_df['person_id'] == pid].copy()
        user_periods = periods_df[periods_df['person_id'] == pid].copy()
        user_emotions = emotions_df[emotions_df['person_id'] == pid].copy()

        if user_emotions.empty or user_periods.empty or user_songs.empty:
            continue

        emotions_row = user_emotions.iloc[0]
        
        # --- 1. COMPUTE AGGREGATE MEASURES ---
        
        # Volume
        total_mins = emotions_row['total_minutes']
        matched_mins = emotions_row['matched_minutes']
        coverage = emotions_row['match_coverage_percent']
        
        peak_month_row = user_periods.sort_values('total_minutes_month', ascending=False).iloc[0]
        peak_month_mins = peak_month_row['total_minutes_month']
        peak_month_share = peak_month_mins / total_mins if total_mins > 0 else 0

        # Credibility base
        z_u = matched_mins / (matched_mins + k_matched) if (matched_mins + k_matched) > 0 else 0

        measures.extend([
            {'person_id': pid, 'metric_name': 'total_minutes_raw', 'metric_value_num': total_mins, 'metric_value_text': f"{total_mins:,.0f}", 'metric_unit': 'minutes', 'metric_group': 'volume', 'source_table': 'elicitation_emotions.csv', 'metric_layer': 'raw'},
            {'person_id': pid, 'metric_name': 'match_coverage_percent_raw', 'metric_value_num': coverage, 'metric_value_text': f"{coverage:.1f}%", 'metric_unit': 'percent', 'metric_group': 'volume', 'source_table': 'elicitation_emotions.csv', 'metric_layer': 'raw'},
            {'person_id': pid, 'metric_name': 'coverage_cred_conf', 'metric_value_num': z_u, 'metric_value_text': f"{z_u:.2f}", 'metric_unit': 'score', 'metric_group': 'volume', 'source_table': 'derived', 'metric_layer': 'conf'},
            {'person_id': pid, 'metric_name': 'peak_month_minutes_raw', 'metric_value_num': peak_month_mins, 'metric_value_text': f"{peak_month_mins:,.0f}", 'metric_unit': 'minutes', 'metric_group': 'volume', 'source_table': 'elicitation_periods.csv', 'metric_layer': 'raw'},
            {'person_id': pid, 'metric_name': 'peak_month_share_raw', 'metric_value_num': peak_month_share, 'metric_value_text': f"{peak_month_share*100:.1f}%", 'metric_unit': 'percent', 'metric_group': 'volume', 'source_table': 'derived', 'metric_layer': 'raw'},
            {'person_id': pid, 'metric_name': 'peak_month_tail', 'metric_value_num': peak_month_share, 'metric_value_text': f"{peak_month_share*100:.1f}%", 'metric_unit': 'percent', 'metric_group': 'volume', 'source_table': 'derived', 'metric_layer': 'tail'}
        ])

        # Periods explicit metrics
        dayparts = ['share_late_night', 'share_night', 'share_morning', 'share_afternoon', 'share_evening']
        available_dayparts = [dp for dp in dayparts if dp in user_periods.columns]
        mean_dayparts = user_periods[available_dayparts].mean()
        dom_dp_raw = mean_dayparts.idxmax()
        dom_dp_clean = dom_dp_raw.replace('share_', '').replace('_', ' ')
        dom_dp_share = mean_dayparts.max()
        
        exam_peak_month = user_periods.sort_values('exam_season_share', ascending=False).iloc[0]
        exam_peak_share = exam_peak_month['exam_season_share']
        
        exam_months = user_periods[user_periods['exam_season_share'] > 0]
        non_exam_months = user_periods[user_periods['exam_season_share'] == 0]
        avg_exam = exam_months['total_minutes_month'].mean() if not exam_months.empty else 0
        avg_non_exam = non_exam_months['total_minutes_month'].mean() if not non_exam_months.empty else 0
        exam_tail_ratio = avg_exam / avg_non_exam if avg_non_exam > 0 else 0

        measures.extend([
            {'person_id': pid, 'metric_name': 'peak_month_raw', 'metric_value_num': 0, 'metric_value_text': peak_month_row['year_month'], 'metric_unit': 'month', 'metric_group': 'period', 'source_table': 'elicitation_periods.csv', 'metric_layer': 'raw'},
            {'person_id': pid, 'metric_name': 'dominant_daypart_raw', 'metric_value_num': 0, 'metric_value_text': dom_dp_clean, 'metric_unit': 'label', 'metric_group': 'period', 'source_table': 'derived', 'metric_layer': 'raw'},
            {'person_id': pid, 'metric_name': 'dominant_daypart_share_raw', 'metric_value_num': dom_dp_share, 'metric_value_text': f"{dom_dp_share*100:.1f}%", 'metric_unit': 'percent', 'metric_group': 'period', 'source_table': 'derived', 'metric_layer': 'raw'},
            {'person_id': pid, 'metric_name': 'daypart_conc_tail', 'metric_value_num': dom_dp_share, 'metric_value_text': f"{dom_dp_share*100:.1f}%", 'metric_unit': 'percent', 'metric_group': 'period', 'source_table': 'derived', 'metric_layer': 'tail'},
            {'person_id': pid, 'metric_name': 'exam_peak_share_raw', 'metric_value_num': exam_peak_share, 'metric_value_text': f"{exam_peak_share*100:.1f}%", 'metric_unit': 'percent', 'metric_group': 'period', 'source_table': 'elicitation_periods.csv', 'metric_layer': 'raw'},
            {'person_id': pid, 'metric_name': 'exam_tail_ratio', 'metric_value_num': exam_tail_ratio, 'metric_value_text': f"{exam_tail_ratio:.2f}", 'metric_unit': 'ratio', 'metric_group': 'period', 'source_table': 'derived', 'metric_layer': 'tail'}
        ])

        # Emotions
        emo_cols = [c for c in emotions_row.index if c.startswith('share_')]
        if len(emo_cols) > 0:
            emo_shares = emotions_row[emo_cols]
            emo_shares_sorted = emo_shares.sort_values(ascending=False)
            dom_emo = emo_shares_sorted.index[0]
            dom_emo_share = emo_shares_sorted.iloc[0]
            dom_emo_display = display_emotion_label(dom_emo)
            
            top2_share = emo_shares_sorted.iloc[0] + (emo_shares_sorted.iloc[1] if len(emo_shares_sorted) > 1 else 0)
            
            upbeat_share = emotions_row.get('share_happy', 0) + emotions_row.get('share_joy', 0) + emotions_row.get('share_energetic', 0)
            heavy_share = emotions_row.get('share_sad', 0) + emotions_row.get('share_sadness', 0) + emotions_row.get('share_fear', 0)

            # Actuarial Companions for Emotions
            heavy_share_cred = (z_u * heavy_share) + ((1 - z_u) * cohort_heavy_share)
            upbeat_share_cred = (z_u * upbeat_share) + ((1 - z_u) * cohort_upbeat_share)
            emotion_conc_tail = sum([p**2 for p in emo_shares if pd.notna(p)])
            emotion_entropy_exp = -sum([p * np.log(p) for p in emo_shares if p > 0 and pd.notna(p)])

            measures.extend([
                {'person_id': pid, 'metric_name': 'dominant_emotion_raw', 'metric_value_num': dom_emo_share, 'metric_value_text': dom_emo, 'metric_unit': 'label', 'metric_group': 'emotion', 'source_table': 'elicitation_emotions.csv', 'metric_layer': 'raw'},
                {'person_id': pid, 'metric_name': 'dominant_emotion_display', 'metric_value_num': dom_emo_share, 'metric_value_text': dom_emo_display, 'metric_unit': 'label', 'metric_group': 'emotion', 'source_table': 'derived', 'metric_layer': 'raw'},
                {'person_id': pid, 'metric_name': 'top2_emotion_share_raw', 'metric_value_num': top2_share, 'metric_value_text': f"{top2_share*100:.1f}%", 'metric_unit': 'percent', 'metric_group': 'emotion', 'source_table': 'derived', 'metric_layer': 'raw'},
                {'person_id': pid, 'metric_name': 'emotion_conc_tail', 'metric_value_num': emotion_conc_tail, 'metric_value_text': f"{emotion_conc_tail:.2f}", 'metric_unit': 'hhi', 'metric_group': 'emotion', 'source_table': 'derived', 'metric_layer': 'tail'},
                {'person_id': pid, 'metric_name': 'emotional_diversity_raw', 'metric_value_num': emotions_row.get('emotional_diversity', 0), 'metric_value_text': str(emotions_row.get('emotional_diversity', 0)), 'metric_unit': 'count', 'metric_group': 'emotion', 'source_table': 'elicitation_emotions.csv', 'metric_layer': 'raw'},
                {'person_id': pid, 'metric_name': 'emotion_entropy_exp', 'metric_value_num': emotion_entropy_exp, 'metric_value_text': f"{emotion_entropy_exp:.2f}", 'metric_unit': 'entropy', 'metric_group': 'emotion', 'source_table': 'derived', 'metric_layer': 'exp'},
                {'person_id': pid, 'metric_name': 'upbeat_share_raw', 'metric_value_num': upbeat_share, 'metric_value_text': f"{upbeat_share*100:.1f}%", 'metric_unit': 'percent', 'metric_group': 'emotion', 'source_table': 'derived', 'metric_layer': 'raw'},
                {'person_id': pid, 'metric_name': 'upbeat_share_cred', 'metric_value_num': upbeat_share_cred, 'metric_value_text': f"{upbeat_share_cred*100:.1f}%", 'metric_unit': 'percent', 'metric_group': 'emotion', 'source_table': 'derived', 'metric_layer': 'cred'},
                {'person_id': pid, 'metric_name': 'heavy_share_raw', 'metric_value_num': heavy_share, 'metric_value_text': f"{heavy_share*100:.1f}%", 'metric_unit': 'percent', 'metric_group': 'emotion', 'source_table': 'derived', 'metric_layer': 'raw'},
                {'person_id': pid, 'metric_name': 'heavy_share_cred', 'metric_value_num': heavy_share_cred, 'metric_value_text': f"{heavy_share_cred*100:.1f}%", 'metric_unit': 'percent', 'metric_group': 'emotion', 'source_table': 'derived', 'metric_layer': 'cred'}
            ])

        # Songs
        user_songs['intentionality_score'] = (1 - user_songs['playlist_share']) * np.log1p(user_songs['repeat_count'])
        anchor = user_songs.sort_values(by=['total_minutes'], ascending=False).iloc[0]
        
        anchor_exposure_tail = anchor['total_minutes'] / total_mins if total_mins > 0 else 0

        measures.extend([
            {'person_id': pid, 'metric_name': 'anchor_song_name_raw', 'metric_value_num': 0, 'metric_value_text': anchor['master_metadata_track_name'], 'metric_unit': 'song', 'metric_group': 'song', 'source_table': 'elicitation_songs.csv', 'metric_layer': 'raw'},
            {'person_id': pid, 'metric_name': 'anchor_song_minutes_raw', 'metric_value_num': anchor['total_minutes'], 'metric_value_text': f"{anchor['total_minutes']:.0f}", 'metric_unit': 'minutes', 'metric_group': 'song', 'source_table': 'elicitation_songs.csv', 'metric_layer': 'raw'},
            {'person_id': pid, 'metric_name': 'anchor_song_days_raw', 'metric_value_num': anchor['days_listened'], 'metric_value_text': str(anchor['days_listened']), 'metric_unit': 'days', 'metric_group': 'song', 'source_table': 'elicitation_songs.csv', 'metric_layer': 'raw'},
            {'person_id': pid, 'metric_name': 'anchor_exposure_tail', 'metric_value_num': anchor_exposure_tail, 'metric_value_text': f"{anchor_exposure_tail*100:.1f}%", 'metric_unit': 'percent', 'metric_group': 'song', 'source_table': 'derived', 'metric_layer': 'tail'}
        ])

        intentional_candidates = user_songs[(user_songs['playlist_share'] < 0.2) & (user_songs['repeat_count'] >= 10)]
        if not intentional_candidates.empty:
            intent_song = intentional_candidates.sort_values('intentionality_score', ascending=False).iloc[0]
            intent_raw = intent_song['intentionality_score']
            intent_cred = (z_u * intent_raw) + ((1 - z_u) * cohort_intentionality)
            
            measures.extend([
                {'person_id': pid, 'metric_name': 'intentional_song_name_raw', 'metric_value_num': 0, 'metric_value_text': intent_song['master_metadata_track_name'], 'metric_unit': 'song', 'metric_group': 'song', 'source_table': 'derived', 'metric_layer': 'raw'},
                {'person_id': pid, 'metric_name': 'intentionality_score_raw', 'metric_value_num': intent_raw, 'metric_value_text': f"{intent_raw:.2f}", 'metric_unit': 'score', 'metric_group': 'song', 'source_table': 'derived', 'metric_layer': 'raw'},
                {'person_id': pid, 'metric_name': 'intentionality_score_cred', 'metric_value_num': intent_cred, 'metric_value_text': f"{intent_cred:.2f}", 'metric_unit': 'score', 'metric_group': 'song', 'source_table': 'derived', 'metric_layer': 'cred'},
                {'person_id': pid, 'metric_name': 'intentional_song_repeat_count_raw', 'metric_value_num': intent_song['repeat_count'], 'metric_value_text': str(intent_song['repeat_count']), 'metric_unit': 'plays', 'metric_group': 'song', 'source_table': 'elicitation_songs.csv', 'metric_layer': 'raw'},
                {'person_id': pid, 'metric_name': 'intentional_song_playlist_share_raw', 'metric_value_num': intent_song['playlist_share'], 'metric_value_text': f"{intent_song['playlist_share']*100:.1f}%", 'metric_unit': 'percent', 'metric_group': 'song', 'source_table': 'elicitation_songs.csv', 'metric_layer': 'raw'}
            ])

        # --- 2. GENERATE WRAPPED CARDS ---
        # The cards will still refer to the raw values for narrative purposes
        card_order = 1

        # Card 1: Scale
        cards.append({
            'person_id': pid, 'card_order': card_order, 'card_type': 'listening_scale',
            'headline': f"You spent {total_mins:,.0f} minutes with your music.",
            'subheadline': "That’s the listening footprint behind your emotional recap.",
            'visual_type': 'big-number', 'confidence_note': ''
        }); card_order += 1

        # Card 2: Coverage Note
        cards.append({
            'person_id': pid, 'card_order': card_order, 'card_type': 'coverage_note',
            'headline': f"We could read {coverage:.1f}% of your listening emotionally.",
            'subheadline': f"That came from {emotions_row['matched_minutes']:,.0f} matched minutes in the reference set.",
            'visual_type': 'badge', 'confidence_note': 'Methodological limit'
        }); card_order += 1

        # Cards 3 & 4: Emotion (Suppressed if coverage < 15%)
        if coverage >= 15.0 and len(emo_cols) > 0:
            cards.append({
                'person_id': pid, 'card_order': card_order, 'card_type': 'dominant_emotion',
                'headline': f"Your matched listening leaned {dom_emo_display}.",
                'subheadline': f"{dom_emo_share*100:.1f}% of your matched listening carried that emotional signal.",
                'visual_type': 'badge-bar', 'confidence_note': f"Based on {coverage:.1f}% match rate"
            }); card_order += 1

            diversity = emotions_row['emotional_diversity']
            div_label = "wide-ranging" if diversity >= 5 else "balanced" if diversity == 4 else "narrow" if diversity == 3 else "focused"
            cards.append({
                'person_id': pid, 'card_order': card_order, 'card_type': 'emotional_range',
                'headline': f"Your emotional range was {div_label}.",
                'subheadline': f"Your matched listening spanned {diversity} emotional categories.",
                'visual_type': 'meter', 'confidence_note': f"Based on {coverage:.1f}% match rate"
            }); card_order += 1

        # Card 5: Anchor Song
        cards.append({
            'person_id': pid, 'card_order': card_order, 'card_type': 'anchor_song',
            'headline': f"One song stayed with you more than any other: {anchor['master_metadata_track_name']}.",
            'subheadline': f"You spent {anchor['total_minutes']:.0f} minutes on it across {anchor['days_listened']} different days.",
            'visual_type': 'cover-big-number', 'confidence_note': ''
        }); card_order += 1

        # Card 6: Intentional Pick
        if not intentional_candidates.empty:
            cards.append({
                'person_id': pid, 'card_order': card_order, 'card_type': 'intentional_pick',
                'headline': f"This was your deliberate go-to: {intent_song['master_metadata_track_name']}.",
                'subheadline': f"Its playlist share was only {intent_song['playlist_share']*100:.0f}%, but you still came back {intent_song['repeat_count']} times.",
                'visual_type': 'badge', 'confidence_note': ''
            }); card_order += 1

        # Card 7: Listening Clock
        cards.append({
            'person_id': pid, 'card_order': card_order, 'card_type': 'listening_clock',
            'headline': f"Your listening rhythm had a clear time signature: {dom_dp_clean}.",
            'subheadline': "That window carried the biggest share of your monthly listening pattern.",
            'visual_type': 'split-clock', 'confidence_note': ''
        }); card_order += 1

        # Card 8: Peak Month
        cards.append({
            'person_id': pid, 'card_order': card_order, 'card_type': 'peak_month',
            'headline': f"Your heaviest month was {peak_month_row['year_month']}.",
            'subheadline': f"You logged {peak_month_mins:.0f} minutes that month, led by {peak_month_row['top_song']}.",
            'visual_type': 'big-number', 'confidence_note': ''
        }); card_order += 1

    pd.DataFrame(measures).to_csv('wrapped_aggregate_measures.csv', index=False)
    pd.DataFrame(cards).to_csv('wrapped_cards.csv', index=False)
    print("Successfully generated wrapped_aggregate_measures.csv and wrapped_cards.csv")

if __name__ == "__main__":
    generate_wrapped_layer()
