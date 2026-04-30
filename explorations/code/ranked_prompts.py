import pandas as pd
import numpy as np

# Load data
try:
    songs_df = pd.read_csv('elicitation_songs.csv')
    periods_df = pd.read_csv('elicitation_periods.csv')
    emotions_df = pd.read_csv('elicitation_emotions.csv')
except FileNotFoundError:
    print("Please ensure elicitation_songs.csv, elicitation_periods.csv, and elicitation_emotions.csv are in the current directory.")
    exit()

def generate_prompts_for_user(pid):
    prompts = []
    
    user_songs = songs_df[songs_df['person_id'] == pid].copy()
    user_periods = periods_df[periods_df['person_id'] == pid].copy()
    user_emotions = emotions_df[emotions_df['person_id'] == pid].copy()
    
    if user_emotions.empty: return None
    
    coverage = user_emotions.iloc[0]['match_coverage_percent']
    diversity = user_emotions.iloc[0]['emotional_diversity']
    
    # --- 1. SONG PROMPTS ---
    if not user_songs.empty:
        # The Habit Song
        habit_song = user_songs.sort_values(by=['days_listened', 'total_minutes'], ascending=[False, False]).iloc[0]
        score = 8.0 # High baseline score
        prompts.append({
            'category': 'SONGS',
            'type': 'The Habit Song',
            'score': score,
            'text': f"I noticed you returned to '{habit_song['master_metadata_track_name']}' by {habit_song['master_metadata_album_artist_name']} on {habit_song['days_listened']} different days. What was happening around that time that made you keep coming back to it?",
            'rationale': f"Selected because it has the highest sustained daily repeat behavior ({habit_song['days_listened']} days)."
        })
        
        # The Intentional Pick
        intentional_songs = user_songs[user_songs['playlist_share'] < 0.2]
        if not intentional_songs.empty:
            intent_song = intentional_songs.sort_values('repeat_count', ascending=False).iloc[0]
            score = 7.0 + (1 - intent_song['playlist_share']) * 2 # Max 9.0
            prompts.append({
                'category': 'SONGS',
                'type': 'The Intentional Pick',
                'score': score,
                'text': f"You almost always actively searched for '{intent_song['master_metadata_track_name']}' ({intent_song['playlist_share']*100:.0f}% from playlists) rather than letting it play on shuffle. Why is this a 'go-to' track for you?",
                'rationale': f"Selected because of high repeat count ({intent_song['repeat_count']} plays) combined with low playlist reliance."
            })

    # --- 2. PERIOD PROMPTS ---
    if not user_periods.empty:
        # Daypart Baseline Shift
        # Calculate user's baseline daypart shares
        dayparts = ['share_late_night', 'share_morning', 'share_afternoon', 'share_evening']
        baselines = user_periods[dayparts].mean()
        
        # Find the month with the biggest deviation
        user_periods['max_deviation'] = 0.0
        user_periods['deviant_daypart'] = ''
        
        for idx, row in user_periods.iterrows():
            max_dev = 0
            dev_dp = ''
            for dp in dayparts:
                dev = row[dp] - baselines[dp]
                if dev > max_dev:
                    max_dev = dev
                    dev_dp = dp
            user_periods.at[idx, 'max_deviation'] = max_dev
            user_periods.at[idx, 'deviant_daypart'] = dev_dp
            
        most_deviant = user_periods.sort_values('max_deviation', ascending=False).iloc[0]
        if most_deviant['max_deviation'] > 0.2: # 20% shift from norm
            dp_clean = most_deviant['deviant_daypart'].replace('share_', '').replace('_', ' ')
            score = 6.0 + (most_deviant['max_deviation'] * 10)
            prompts.append({
                'category': 'PERIODS',
                'type': 'Routine Shift',
                'score': score,
                'text': f"In {most_deviant['year_month']}, your listening spiked heavily in the {dp_clean} window ({most_deviant[most_deviant['deviant_daypart']]*100:.0f}%, usually {baselines[most_deviant['deviant_daypart']]*100:.0f}%). What changed in your routine?",
                'rationale': f"Selected because {dp_clean} listening deviated {most_deviant['max_deviation']*100:.0f}% above the participant's baseline."
            })
            
        # Exam Soundtrack
        exam_months = user_periods[user_periods['exam_season_share'] > 0.3]
        if not exam_months.empty:
            exam_month = exam_months.sort_values('total_minutes_month', ascending=False).iloc[0]
            score = 7.5
            prompts.append({
                'category': 'PERIODS',
                'type': 'Exam Soundtrack',
                'score': score,
                'text': f"During the exam/SWOTVAC period in {exam_month['year_month']}, your dominant song was '{exam_month['top_song']}'. Does your music serve a specific purpose when you are stressed?",
                'rationale': f"Selected because this month overlapped significantly ({exam_month['exam_season_share']*100:.0f}%) with the academic calendar."
            })

    # --- 3. EMOTION PROMPTS ---
    # Coverage Blind Spot
    if coverage < 40:
        score = 10.0 - (coverage / 10) # Lower coverage = higher score
        prompts.append({
            'category': 'EMOTIONS',
            'type': 'Methodological Blind Spot',
            'score': score,
            'text': f"We could only match about {coverage:.0f}% of your music to our emotion database. Looking at the songs we missed, how would you describe their vibe? Are they niche or instrumental?",
            'rationale': f"Selected due to critically low data coverage ({coverage:.1f}%)."
        })
        
    # Emotional Diversity
    if diversity < 4:
        score = 8.5
        prompts.append({
            'category': 'EMOTIONS',
            'type': 'Narrow Affective Range',
            'score': score,
            'text': f"Your profile shows you rely on music for a very specific, narrow set of moods. Do you use music mostly for specific functional tasks rather than exploring different feelings?",
            'rationale': f"Selected because the user engaged meaningfully with only {diversity} distinct emotion classes."
        })
        
    # Affective Arc
    sad_share = user_emotions.iloc[0].get('share_sadness', 0) + user_emotions.iloc[0].get('share_sad', 0)
    upbeat_share = user_emotions.iloc[0].get('share_happy', 0) + user_emotions.iloc[0].get('share_joy', 0) + user_emotions.iloc[0].get('share_energetic', 0)
    
    if sad_share > 0.40:
        score = 7.0 + (sad_share * 5)
        prompts.append({
            'category': 'EMOTIONS',
            'type': 'Affective Tendency',
            'score': score,
            'text': f"Our model suggests about {sad_share*100:.0f}% of your matched music leans toward sadness or melancholy. Does this resonate with how you were using music, or does the label feel wrong?",
            'rationale': f"Selected because the Sad/Sadness share dominates ({sad_share*100:.0f}%)."
        })
    elif upbeat_share > 0.60:
        score = 7.0 + (upbeat_share * 5)
        prompts.append({
            'category': 'EMOTIONS',
            'type': 'Affective Tendency',
            'score': score,
            'text': f"Our model suggests over {upbeat_share*100:.0f}% of your matched music leans toward upbeat, happy, or energetic. Does this resonate with how you use music?",
            'rationale': f"Selected because Upbeat emotions dominate ({upbeat_share*100:.0f}%)."
        })

    # Sort prompts by score and take top 5
    prompts = sorted(prompts, key=lambda x: x['score'], reverse=True)[:5]
    
    # Formatting output
    print(f"==================================================")
    print(f" PARTICIPANT: {pid.upper()}")
    print(f" Summary: {user_songs['total_minutes'].sum():.0f} mins total | {coverage:.1f}% Emotion Match Coverage")
    print(f"==================================================\n")
    
    for p in prompts:
        print(f"[{p['category']}] {p['type']} (Strength: {p['score']:.1f}/10)")
        print(f"  Prompt:    \"{p['text']}\"")
        print(f"  Rationale: {p['rationale']}\n")

if __name__ == "__main__":
    for pid in sorted(songs_df['person_id'].unique()):
        generate_prompts_for_user(pid)
