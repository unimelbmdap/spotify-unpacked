import pandas as pd
import numpy as np
import os
import glob
import json

def load_extended_history(folder="."):
    """Loads Spotify Extended Streaming History files."""
    all_jsons = glob.glob(os.path.join(folder, "**", "*.json"), recursive=True)
    # Strictly match 'Streaming_History_Audio' patterns as requested
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
                        uri = None
                        if 'track' in item and item['track']:
                            uri = item['track'].get('trackUri')
                        elif 'localTrack' in item and item['localTrack']:
                            uri = item['localTrack'].get('uri')
                        if uri:
                            uris.add(uri)
        except Exception as e:
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
                    if 'uri' in item:
                        uris.add(item['uri'])
        except Exception as e:
            pass
    return uris

def bucket_taxonomy(df):
    """Maps reason_start and reason_end to higher-level behavioral taxonomy."""
    # Start buckets
    start_mapping = {
        'clickrow': 'Deliberate',
        'playbtn': 'Deliberate',
        'search': 'Deliberate',
        'trackdone': 'Receptive',
        'fwdbtn': 'Responsive',
        'backbtn': 'Responsive',
        'appload': 'Contextual / Resume',
        'remote': 'Remote-Controlled'
    }
    
    # End buckets
    end_mapping = {
        'clickrow': 'Deliberate',
        'playbtn': 'Deliberate',
        'search': 'Deliberate',
        'trackdone': 'Receptive',
        'fwdbtn': 'Responsive',
        'backbtn': 'Responsive',
        'endplay': 'Responsive',
        'appload': 'Contextual / Resume',
        'remote': 'Remote-Controlled'
    }
    
    if 'reason_start' in df.columns:
        df['reason_start_bucket'] = df['reason_start'].map(start_mapping).fillna('System / Noise')
    if 'reason_end' in df.columns:
        df['reason_end_bucket'] = df['reason_end'].map(end_mapping).fillna('System / Noise')
    
    return df

def run_data_audit(df, subject_id="aggregate", playlist_uris=set(), library_uris=set()):
    """Executes the v2 data profiling checklist."""
    if df.empty:
        print("No streaming data found to audit.")
        return

    print("="*60)
    print(f" DATA AUDIT PROFILING: {subject_id.upper()} ")
    print("="*60)
    
    # Standardize time
    time_col = 'ts' if 'ts' in df.columns else 'endTime' if 'endTime' in df.columns else None
    ms_col = 'ms_played' if 'ms_played' in df.columns else 'msPlayed' if 'msPlayed' in df.columns else None
    
    if time_col:
        df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
        df['year'] = df[time_col].dt.year
        df['hour'] = df[time_col].dt.hour
        df['weekday'] = df[time_col].dt.day_name()
    
    # Process Source Classification
    if 'spotify_track_uri' in df.columns:
        df['is_from_playlist'] = df['spotify_track_uri'].isin(playlist_uris) if playlist_uris else False
        df['library_flag'] = df['spotify_track_uri'].isin(library_uris) if library_uris else False
        
        # 4-way flag
        conditions = [
            (df['is_from_playlist'] == True) & (df['library_flag'] == False),
            (df['is_from_playlist'] == False) & (df['library_flag'] == True),
            (df['is_from_playlist'] == True) & (df['library_flag'] == True)
        ]
        choices = ['Playlist only', 'Library only', 'Both']
        df['source_class'] = np.select(conditions, choices, default='Discovery / Neither')
    
    # Taxonomy Buckets
    df = bucket_taxonomy(df)
    
    # Skip Diagnostics
    raw_skip_rate, proxy_skip_rate = 0, 0
    if 'skipped' in df.columns and 'reason_end' in df.columns:
        df['skipped_bool'] = df['skipped'].fillna(False).astype(bool)
        raw_skip_rate = df['skipped_bool'].mean() * 100
        
        skip_reasons = ['fwdbtn', 'backbtn', 'endplay']
        df['proxy_skip'] = df['skipped_bool'] | df['reason_end'].isin(skip_reasons)
        proxy_skip_rate = df['proxy_skip'].mean() * 100
        
        if 'year' in df.columns:
            skip_by_year = df.groupby('year').agg(
                Raw_Skip_Rate=('skipped_bool', lambda x: x.mean() * 100),
                Proxy_Skip_Rate=('proxy_skip', lambda x: x.mean() * 100)
            )
            skip_by_year.to_csv(f'audit_skip_validation_{subject_id}.csv')
            print(f"[!] Saved skip reliability to 'audit_skip_validation_{subject_id}.csv'")

    # Results Payload
    results = {
        "dataset_shape": {"rows": len(df), "cols": len(df.columns)},
        "date_coverage": {
            "start": str(df[time_col].min()) if time_col else None,
            "end": str(df[time_col].max()) if time_col else None
        },
        "missingness": (df.isnull().sum() / len(df) * 100).sort_values(ascending=False).head(10).to_dict(),
        "boolean_proportions": {},
        "categorical_distributions": {},
        "source_composition": {},
        "cross_tabs": {},
        "routine_heatmap": {}
    }

    if ms_col:
        short_plays = (df[ms_col] < 30000).mean() * 100
        results["duration_stats"] = {
            "median_ms": float(df[ms_col].median()),
            "short_play_percent": float(short_plays)
        }

    # Booleans
    bool_cols = ['shuffle', 'skipped', 'incognito_mode']
    for col in bool_cols:
        if col in df.columns:
            results["boolean_proportions"][col] = df[col].value_counts(dropna=False, normalize=True).to_dict()

    # Categorical
    cat_cols = ['reason_start', 'reason_end', 'reason_start_bucket', 'reason_end_bucket', 'conn_country', 'platform']
    for col in cat_cols:
        if col in df.columns:
            results["categorical_distributions"][col] = df[col].value_counts(dropna=False, normalize=True).to_dict()

    # Source Composition
    if 'source_class' in df.columns:
        results["source_composition"] = df['source_class'].value_counts(normalize=True).to_dict()

    # Cross Tabs
    if 'reason_start_bucket' in df.columns and 'source_class' in df.columns:
        ct = pd.crosstab(df['reason_start_bucket'], df['source_class'], normalize='index') * 100
        results["cross_tabs"]["reason_start_x_source"] = ct.to_dict()

    if 'shuffle' in df.columns and 'is_from_playlist' in df.columns:
        ct = pd.crosstab(df['shuffle'], df['is_from_playlist'], normalize='index') * 100
        # Convert boolean keys to strings for JSON serialization
        ct.index = ct.index.astype(str)
        ct.columns = ct.columns.astype(str)
        results["cross_tabs"]["shuffle_x_playlist"] = ct.to_dict()

    # Heatmap (7x24 Matrix)
    if 'weekday' in df.columns and 'hour' in df.columns:
        weekdays_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        hm = pd.crosstab(df['weekday'], df['hour'])
        hm = hm.reindex(weekdays_order).fillna(0).astype(int)
        # Ensure all 24 hours exist
        for h in range(24):
            if h not in hm.columns:
                hm[h] = 0
        hm = hm[range(24)] # Sort columns
        # Convert integer columns to string for JSON serialization
        hm.columns = hm.columns.astype(str)
        results["routine_heatmap"] = hm.to_dict(orient='index')

    if 'skipped' in df.columns and 'reason_end' in df.columns:
        results["skip_diagnostics"] = {
            "raw_skip_rate": float(raw_skip_rate),
            "proxy_skip_rate": float(proxy_skip_rate)
        }

    with open(f'audit_summary_{subject_id}.json', 'w') as f:
        json.dump(results, f, indent=4)
    print(f"[!] Saved full audit summary to 'audit_summary_{subject_id}.json'")

if __name__ == "__main__":
    data_dir = "./data" 
    subjects = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
    
    if not subjects:
        print(f"No subjects found. Running aggregate audit.")
        df_streams = load_extended_history(data_dir)
        playlists = load_playlists(data_dir)
        library = load_library(data_dir)
        run_data_audit(df_streams, "aggregate", playlists, library)
    else:
        all_playlists = set()
        all_library = set()
        
        for subject in subjects:
            subject_path = os.path.join(data_dir, subject)
            df_streams = load_extended_history(subject_path)
            
            p_uris = load_playlists(subject_path)
            l_uris = load_library(subject_path)
            
            all_playlists.update(p_uris)
            all_library.update(l_uris)
            
            if not df_streams.empty:
                run_data_audit(df_streams, subject, p_uris, l_uris)
            else:
                print(f"No streaming data found for {subject}.")
        
        # Aggregate
        df_all = load_extended_history(data_dir)
        if not df_all.empty:
            run_data_audit(df_all, "aggregate", all_playlists, all_library)
