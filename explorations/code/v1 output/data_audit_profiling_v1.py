import pandas as pd
import numpy as np
import os
import glob
import json

def load_extended_history(folder="."):
    """
    Loads Spotify Extended Streaming History files.
    """
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
        df = pd.DataFrame(all_streams)
        return df
    else:
        return pd.DataFrame()

def run_data_audit(df, subject_id="aggregate"):
    """
    Executes the basic data profiling checklist (v1).
    """
    if df.empty:
        print("No streaming data found to audit.")
        return

    print("="*60)
    print(" SPOTIFY DATA AUDIT PROFILING (v1) ")
    print("="*60)
    
    # Standardize timestamp and duration fields
    time_col = 'ts' if 'ts' in df.columns else 'endTime' if 'endTime' in df.columns else None
    ms_col = 'ms_played' if 'ms_played' in df.columns else 'msPlayed' if 'msPlayed' in df.columns else None
    
    if time_col:
        df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
        df['year'] = df[time_col].dt.year
        df['month'] = df[time_col].dt.month
        df['hour'] = df[time_col].dt.hour
        df['weekday'] = df[time_col].dt.day_name()

    # 1. Missingness
    missing = (df.isnull().sum() / len(df)) * 100
    missing_nonzero = missing[missing > 0].sort_values(ascending=False)

    # 2. Skip Logic Check
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
            skip_by_year.to_csv(f'audit_skip_validation_{subject_id}_v1.csv')

    # Distributions
    bool_cols = ['shuffle', 'skipped', 'incognito_mode']
    cat_cols = ['reason_start', 'reason_end', 'conn_country', 'platform']

    results = {
        "dataset_shape": {"rows": len(df), "cols": len(df.columns)},
        "date_coverage": {
            "start": str(df[time_col].min()) if time_col else None,
            "end": str(df[time_col].max()) if time_col else None
        },
        "missingness": missing_nonzero.to_dict() if not missing_nonzero.empty else {},
        "boolean_proportions": {},
        "categorical_distributions": {}
    }

    for col in bool_cols:
        if col in df.columns:
            results["boolean_proportions"][col] = df[col].value_counts(dropna=False, normalize=True).to_dict()

    for col in cat_cols:
        if col in df.columns:
            results["categorical_distributions"][col] = df[col].value_counts(dropna=False, normalize=True).to_dict()

    if 'skipped' in df.columns and 'reason_end' in df.columns:
        results["skip_diagnostics"] = {
            "raw_skip_rate": float(raw_skip_rate),
            "proxy_skip_rate": float(proxy_skip_rate)
        }

    with open(f'audit_summary_{subject_id}_v1.json', 'w') as f:
        json.dump(results, f, indent=4)
    print(f"[!] Saved v1 audit summary to 'audit_summary_{subject_id}_v1.json'")

if __name__ == "__main__":
    data_dir = "./data" 
    subjects = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
    
    if not subjects:
        df_streams = load_extended_history(data_dir)
        run_data_audit(df_streams, "aggregate")
    else:
        for subject in subjects:
            subject_path = os.path.join(data_dir, subject)
            df_streams = load_extended_history(subject_path)
            if not df_streams.empty:
                run_data_audit(df_streams, subject)
        
        df_all = load_extended_history(data_dir)
        run_data_audit(df_all, "aggregate")
