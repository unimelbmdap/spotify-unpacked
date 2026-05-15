import pandas as pd
import numpy as np
import os
import glob
import json
import subprocess
from models import behavior_settings, BandedBehavioralProfile

def load_extended_history(folder="."):
    """Loads Spotify Extended Streaming History files."""
    all_jsons = glob.glob(os.path.join(folder, "**", "*.json"), recursive=True)
    streaming_files = [
        f for f in all_jsons 
        if "Streaming_History" in os.path.basename(f) 
        and "Audio" in os.path.basename(f)
    ]
        
    all_streams = []
    for f in streaming_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                all_streams.extend(data)
        except Exception as e:
            print(f"Error loading {f}: {e}")
            
    if all_streams:
        return pd.DataFrame(all_streams)
    return pd.DataFrame()

def load_search_queries(folder="."):
    """Loads Spotify SearchQueries files."""
    all_jsons = glob.glob(os.path.join(folder, "**", "*.json"), recursive=True)
    search_files = [f for f in all_jsons if "SearchQueries" in os.path.basename(f)]
        
    all_searches = []
    for f in search_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                all_searches.extend(data)
        except Exception:
            pass
            
    if all_searches:
        return pd.DataFrame(all_searches)
    return pd.DataFrame()

def load_playlists(folder="."):
    """Loads Playlist*.json and returns a set of track URIs."""
    playlist_files = glob.glob(os.path.join(folder, "**", "Playlist*.json"), recursive=True)
    uris = set()
    for f in playlist_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                for p in data.get('playlists', []):
                    for item in p.get('items', []):
                        uri = item.get('track', {}).get('trackUri') or item.get('localTrack', {}).get('uri')
                        if uri: uris.add(uri)
        except Exception:
            pass
    return uris

def load_library(folder="."):
    """Loads YourLibrary.json and returns a set of track URIs."""
    library_files = glob.glob(os.path.join(folder, "**", "YourLibrary*.json"), recursive=True)
    uris = set()
    for f in library_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                for item in data.get('tracks', []):
                    if 'uri' in item: uris.add(item['uri'])
        except Exception:
            pass
    return uris

def assign_behavioral_profile(skip_rate, shuffle_rate, active_selection_score, platform_dist, platform_mode, total_plays, start_dominant_type, end_dominant_type):
    """Assigns behavioral bands and provisional label based on raw rates and selection scores."""
    if total_plays < behavior_settings.min_data_sufficiency:
        return BandedBehavioralProfile(
            skip_rate=0.0,
            shuffle_rate=0.0,
            active_selection_score=0.0,
            skip_level="Unknown",
            shuffle_level="Unknown",
            deliberate_level="Unknown",
            platform_distribution={},
            platform_mode="Unknown",
            behavioral_label_primary="Insufficient Data",
            classification_confidence="None",
            behavioral_basis_note=f"Insufficient data to classify (only {total_plays} valid plays)."
        ).model_dump()

    def get_band(rate, low_max, medium_max):
        if pd.isna(rate): return "Unknown"
        if rate <= low_max: return "Low"
        if rate <= medium_max: return "Medium"
        return "High"

    skip_level = get_band(skip_rate, behavior_settings.skip_low_max, behavior_settings.skip_medium_max)
    shuffle_level = get_band(shuffle_rate, behavior_settings.shuffle_low_max, behavior_settings.shuffle_medium_max)
    active_selection_level = get_band(active_selection_score, behavior_settings.active_selection_low_max, behavior_settings.active_selection_medium_max)

    # Label Logic
    # 1. Responsive Priority (High Friction/Activity)
    # If skipping is high, the user is actively adjusting, regardless of shuffle.
    if skip_level == "High":
        label = "Responsive (Provisional)"
        confidence = "High" if active_selection_level == "High" else "Medium"
        note = "High skip rate indicates active adjustment (Responsive). " + \
               ("High active selection suggests purposeful but highly selective listening." if active_selection_level == "High" else "")
    
    # 2. Deliberate Priority (High Selection, Low Friction)
    elif active_selection_level in ["Medium", "High"]:
        label = "Deliberate (Provisional)"
        confidence = "High" if skip_level == "Low" and shuffle_level == "Low" else "Medium"
        note = "High active selection reflects Deliberate listening when paired with lower-friction playback."
        
    # 3. Receptive Priority (Low Activity)
    elif skip_level == "Low" and active_selection_level == "Low":
        label = "Receptive (Provisional)"
        confidence = "High" if shuffle_level in ["Medium", "High"] else "Medium"
        note = "Low skip and low active selection evidence suggest a more passive listening style."
    else:
        label = "Mixed (Provisional)"
        confidence = "Baseline"
        note = "Signals point in different directions; no dominant behavioral style identified."

    return BandedBehavioralProfile(
        skip_rate=float(skip_rate),
        shuffle_rate=float(shuffle_rate),
        active_selection_score=float(active_selection_score),
        skip_level=skip_level,
        shuffle_level=shuffle_level,
        deliberate_level=active_selection_level,
        platform_distribution=platform_dist,
        platform_mode=platform_mode,
        behavioral_label_primary=label,
        classification_confidence=confidence,
        behavioral_basis_note=note
    ).model_dump()

def run_data_audit(df, search_df, subject_id="aggregate", playlist_uris=set(), library_uris=set()):
    """Executes the merged data profiling checklist."""
    if df.empty:
        print("No streaming data found to audit.")
        return

    print("="*60)
    print(f" DATA AUDIT PROFILING: {subject_id.upper()} ")
    print("="*60)
    
    total_plays = len(df)
    time_col = 'ts' if 'ts' in df.columns else 'endTime' if 'endTime' in df.columns else None
    
    if time_col:
        df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
        df['weekday'] = df[time_col].dt.day_name()
        df['hour'] = df[time_col].dt.hour
        df['year'] = df[time_col].dt.year

    # 1. Source Classification
    if 'spotify_track_uri' in df.columns:
        df['is_from_playlist'] = df['spotify_track_uri'].isin(playlist_uris)
        df['library_flag'] = df['spotify_track_uri'].isin(library_uris)
        conditions = [
            (df['is_from_playlist'] == True) & (df['library_flag'] == False),
            (df['is_from_playlist'] == False) & (df['library_flag'] == True),
            (df['is_from_playlist'] == True) & (df['library_flag'] == True)
        ]
        choices = ['Playlist only', 'Library only', 'Both']
        df['source_class'] = np.select(conditions, choices, default='Discovery / Neither')

    # 2. Skip Rate
    skip_rate = 0.0
    if 'skipped' in df.columns and 'reason_end' in df.columns:
        df['skipped_bool'] = df['skipped'].fillna(False).astype(bool)
        skip_reasons = ['fwdbtn', 'backbtn', 'endplay']
        df['proxy_skip'] = df['skipped_bool'] | df['reason_end'].isin(skip_reasons)
        skip_rate = df['proxy_skip'].mean()

    # 3. Shuffle Rate
    shuffle_rate = 0.0
    if 'shuffle' in df.columns:
        shuffle_rate = df['shuffle'].fillna(False).astype(bool).mean()

    # 4. Active Selection Score
    manual_start_count = 0
    if 'reason_start' in df.columns:
        manual_starts = df['reason_start'].isin(['clickrow', 'playbtn'])
        manual_start_count = manual_starts.sum()

    successful_searches = 0
    if not search_df.empty and 'searchInteractionURIs' in search_df.columns:
        search_df['has_interaction'] = search_df['searchInteractionURIs'].apply(lambda x: len(x) > 0 if isinstance(x, list) else False)
        successful_searches = search_df['has_interaction'].sum()

    active_selection_score = (successful_searches + manual_start_count) / total_plays

    # 5. Platform Distribution
    platform_dist = {}
    platform_mode = "Mixed"
    if 'platform' in df.columns:
        def normalize_platform(p):
            p = str(p).lower()
            if "ios" in p: return "ios"
            if "android" in p: return "android"
            if "windows" in p: return "windows_web"
            if "osx" in p or "mac" in p: return "mac_web"
            if "cast" in p or "sonos" in p: return "connected_device"
            return "other"
        df['platform_family'] = df['platform'].apply(normalize_platform)
        platform_dist = df['platform_family'].value_counts(normalize=True).to_dict()
        if platform_dist:
            top_p, top_s = list(platform_dist.items())[0]
            if top_s >= behavior_settings.platform_dominance_threshold: platform_mode = str(top_p)

    # 6. Behavioral Profile
    profile = assign_behavioral_profile(
        skip_rate=skip_rate, shuffle_rate=shuffle_rate, 
        active_selection_score=active_selection_score,
        platform_dist=platform_dist, platform_mode=platform_mode,
        total_plays=total_plays, start_dominant_type="Mixed", end_dominant_type="Mixed"
    )

    # 7. Routine Heatmap (Preserved from original)
    routine_heatmap = {}
    if 'weekday' in df.columns and 'hour' in df.columns:
        weekdays_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        hm = pd.crosstab(df['weekday'], df['hour'])
        hm = hm.reindex(weekdays_order).fillna(0).astype(int)
        for h in range(24):
            if h not in hm.columns: hm[h] = 0
        hm = hm[range(24)]
        hm.columns = hm.columns.astype(str)
        routine_heatmap = hm.to_dict(orient='index')

    # 8. Source Composition & Cross Tabs (Preserved)
    source_composition = {}
    if 'source_class' in df.columns:
        source_composition = df['source_class'].value_counts(normalize=True).to_dict()

    # Final Payload
    results = {
        "behavioral_profile": profile,
        "routine_heatmap": routine_heatmap,
        "source_composition": source_composition,
        "dataset_shape": {"rows": len(df), "cols": len(df.columns)},
        "date_coverage": {
            "start": str(df[time_col].min()) if time_col else None,
            "end": str(df[time_col].max()) if time_col else None
        }
    }

    with open(f'audit_summary_{subject_id}.json', 'w') as f:
        json.dump(results, f, indent=4)
    print(f"[!] Saved behavioral summary to 'audit_summary_{subject_id}.json'")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "data")
    if not os.path.exists(data_dir): data_dir = "./data"
    
    subjects = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
    
    if not subjects:
        df_streams = load_extended_history(data_dir)
        search_df = load_search_queries(data_dir)
        playlists = load_playlists(data_dir)
        library = load_library(data_dir)
        run_data_audit(df_streams, search_df, "aggregate", playlists, library)
    else:
        all_streams, all_searches = [], []
        all_playlists, all_library = set(), set()
        for s in subjects:
            spath = os.path.join(data_dir, s)
            df = load_extended_history(spath)
            sdf = load_search_queries(spath)
            p = load_playlists(spath)
            l = load_library(spath)
            if not df.empty:
                run_data_audit(df, sdf, s, p, l)
                all_streams.append(df)
                if not sdf.empty: all_searches.append(sdf)
                all_playlists.update(p)
                all_library.update(l)
        
        if all_streams:
            df_all = pd.concat(all_streams)
            sdf_all = pd.concat(all_searches) if all_searches else pd.DataFrame()
            run_data_audit(df_all, sdf_all, "aggregate", all_playlists, all_library)

        # Automatically trigger visualization
        print("\n" + "="*60)
        print(" TRIGGERING VISUALIZATION ")
        print("="*60)
        try:
            subprocess.run(["python", "visualize_audit_v2.py"], check=True)
        except Exception as e:
            print(f"Error triggering visualization: {e}")
