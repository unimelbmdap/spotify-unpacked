import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import sys
import glob

# Add parent directory to sys.path for core.models import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.models import behavior_settings

# CONFIGURATION
INPUT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "input_data")
LOCAL_REPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "local_reports")
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

sns.set_theme(style="whitegrid")

def load_extended_history(folder):
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
        except Exception:
            pass
            
    if all_streams:
        return pd.DataFrame(all_streams)
    return pd.DataFrame()

def load_search_queries(folder):
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

def calculate_metrics(data_dir, subjects):
    """Calculates metrics for all subjects to create cohort baseline."""
    subject_metrics = []

    for subject in subjects:
        subject_path = os.path.join(data_dir, subject)
        df = load_extended_history(subject_path)
        
        if df.empty or len(df) < behavior_settings.min_data_sufficiency:
            continue
            
        # 1. Skip Rate
        skip_rate = 0.0
        if 'skipped' in df.columns and 'reason_end' in df.columns:
            df['skipped_bool'] = df['skipped'].fillna(False).astype(bool)
            skip_reasons = ['fwdbtn', 'backbtn', 'endplay']
            df['proxy_skip'] = df['skipped_bool'] | df['reason_end'].isin(skip_reasons)
            skip_rate = df['proxy_skip'].mean()
            
        # 2. Shuffle Rate
        shuffle_rate = 0.0
        if 'shuffle' in df.columns:
            shuffle_rate = df['shuffle'].fillna(False).astype(bool).mean()
            
        # 3. Active Selection Score
        manual_start_count = 0
        if 'reason_start' in df.columns:
            manual_starts = df['reason_start'].isin(['clickrow', 'playbtn'])
            manual_start_count = manual_starts.sum()

        search_df = load_search_queries(subject_path)
        successful_searches = 0
        if not search_df.empty and 'searchInteractionURIs' in search_df.columns:
            search_df['has_interaction'] = search_df['searchInteractionURIs'].apply(lambda x: len(x) > 0 if isinstance(x, list) else False)
            successful_searches = search_df['has_interaction'].sum()

        active_selection_score = (successful_searches + manual_start_count) / len(df)
            
        subject_metrics.append({
            "subject": subject,
            "skip_rate": skip_rate,
            "shuffle_rate": shuffle_rate,
            "active_selection_score": active_selection_score
        })

    return pd.DataFrame(subject_metrics)

def visualize_calibration_bands(metrics_df, columns):
    """Generates a distribution plot with shaded bands."""
    fig, axes = plt.subplots(len(columns), 1, figsize=(12, 5 * len(columns)))
    if len(columns) == 1: axes = [axes]
    
    colors = {'low': 'green', 'med': 'orange', 'high': 'red', 'line': 'black'}

    for i, col in enumerate(columns):
        ax = axes[i]
        data = metrics_df[col]
        q1 = data.quantile(0.25)
        q3 = data.quantile(0.75)
        
        sns.kdeplot(data, ax=ax, fill=False, color=colors['line'], linewidth=2, zorder=3, clip=(0, 1), bw_adjust=0.8)
        sns.rugplot(data, ax=ax, color=colors['line'], alpha=0.5)
        
        line = ax.get_lines()[-1]
        x, y = line.get_data()
        
        ax.fill_between(x, 0, y, where=(x <= q1), color=colors['low'], alpha=0.3, label=f'Low (< {q1:.3f})')
        ax.fill_between(x, 0, y, where=((x >= q1) & (x <= q3)), color=colors['med'], alpha=0.3, label=f'Medium ({q1:.3f}-{q3:.3f})')
        ax.fill_between(x, 0, y, where=(x >= q3), color=colors['high'], alpha=0.3, label=f'High (> {q3:.3f})')
        
        ax.set_title(f'Cohort Band Calibration: {col.replace("_", " ").title()}', fontsize=16, fontweight='bold')
        ax.set_xlabel('Score / Rate')
        ax.set_ylabel('Density')
        ax.legend(loc='upper right')

    plt.tight_layout()
    os.makedirs(LOCAL_REPORT_DIR, exist_ok=True)
    out_path = os.path.join(LOCAL_REPORT_DIR, 'behavioral_threshold_calibration.png')
    plt.savefig(out_path, dpi=300)
    print(f"\n[!] Calibration graph saved as '{out_path}'")

def calibrate_thresholds():
    if not os.path.exists(INPUT_DATA_DIR):
        print(f"Data directory {INPUT_DATA_DIR} not found.")
        return

    subjects = [d for d in os.listdir(INPUT_DATA_DIR) if os.path.isdir(os.path.join(INPUT_DATA_DIR, d))]
    
    if not subjects:
        print("No subjects found in input_data.")
        return

    metrics_df = calculate_metrics(INPUT_DATA_DIR, subjects)

    if metrics_df.empty:
        print("No valid subject data for calibration.")
        return

    # Generate Visualization
    cols_to_plot = ["skip_rate", "shuffle_rate", "active_selection_score"]
    visualize_calibration_bands(metrics_df, cols_to_plot)

    print("\n" + "="*60)
    print(" BEHAVIORAL COHORT BANDS (Quartile-Based)")
    print("="*60)
    
    updates = {}
    for col in cols_to_plot:
        q1 = metrics_df[col].quantile(0.25)
        q3 = metrics_df[col].quantile(0.75)
        prefix = f"SPOTIFY_{col.upper()}"
        updates[f"{prefix}_LOW_MAX"] = q1
        updates[f"{prefix}_MEDIUM_MAX"] = q3
        
        print(f"\n--- {col.upper()} ---")
        print(f"  [LOW]    0.0000 -> {q1:.4f}")
        print(f"  [MEDIUM] {q1:.4f} -> {q3:.4f}")
        print(f"  [HIGH]   {q3:.4f} -> 1.0000")

    # --- AUTOMATIC .ENV UPDATE ---
    env_lines = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r") as f:
            env_lines = f.readlines()
    
    for key, val in updates.items():
        found = False
        new_line = f"{key}={val:.4f}\n"
        for i, line in enumerate(env_lines):
            if line.startswith(f"{key}="):
                env_lines[i] = new_line
                found = True
                break
        if not found:
            env_lines.append(new_line)
            
    with open(ENV_PATH, "w") as f:
        f.writelines(env_lines)
        
    print(f"\n[!] Automatically updated {ENV_PATH} with new calibrated thresholds.")

if __name__ == "__main__":
    calibrate_thresholds()
