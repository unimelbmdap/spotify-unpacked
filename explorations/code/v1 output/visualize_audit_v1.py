import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
import glob

# Set the style for the plots
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)

def load_audit_files(directory="."):
    """Finds all v1 audit summary and skip validation files."""
    summary_files = glob.glob(os.path.join(directory, "audit_summary_*_v1.json"))
    return summary_files

def plot_skip_reliability(csv_path, subject_name):
    """Plots the Raw vs Proxy skip rate over time."""
    df = pd.read_csv(csv_path)
    if 'year' not in df.columns:
        df = df.rename(columns={'Unnamed: 0': 'year'})
    
    plt.figure(figsize=(10, 5))
    plt.plot(df['year'], df['Raw_Skip_Rate'], marker='o', label='Raw Skip Rate', color='#1DB954')
    plt.plot(df['year'], df['Proxy_Skip_Rate'], marker='s', label='Proxy Skip Rate', color='#191414', alpha=0.7)
    plt.title(f"v1 Skip Reliability: {subject_name.upper()}")
    plt.ylim(0, 105)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"audit_plot_skip_{subject_name}_v1.png")
    plt.close()

def plot_behavioral_distributions(json_path, subject_name):
    """Plots basic Reason Start distribution."""
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    if "categorical_distributions" in data and "reason_start" in data["categorical_distributions"]:
        dist = data["categorical_distributions"]["reason_start"]
        s = pd.Series(dist).sort_values(ascending=False).head(10) * 100
        plt.figure(figsize=(10, 6))
        sns.barplot(x=s.values, y=s.index, palette="viridis")
        plt.title(f"v1 How Music Starts: {subject_name.upper()}")
        plt.tight_layout()
        plt.savefig(f"audit_plot_behavior_{subject_name}_v1.png")
        plt.close()

if __name__ == "__main__":
    summaries = load_audit_files()
    if not summaries:
        print("No v1 audit files found. Run 'data_audit_profiling_v1.py' first.")
    else:
        for summary_path in summaries:
            subject_id = os.path.basename(summary_path).replace("audit_summary_", "").replace("_v1.json", "")
            print(f"Visualizing v1 for {subject_id}...")
            plot_behavioral_distributions(summary_path, subject_id)
            skip_path = f"audit_skip_validation_{subject_id}_v1.csv"
            if os.path.exists(skip_path):
                plot_skip_reliability(skip_path, subject_id)
