import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
import glob

# CONFIGURATION
INPUT_JSON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "public", "data")
LOCAL_REPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "local_reports")

# Set the style for the plots
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)

def load_audit_files():
    """Finds all audit summary files in the public data directory."""
    summary_files = glob.glob(os.path.join(INPUT_JSON_DIR, "audit_summary_*.json"))
    return summary_files

def plot_taxonomy(data, subject_name):
    """Plots the Receptive/Responsive/Deliberate taxonomy."""
    if "behavioral_profile" not in data:
        return None
        
    profile = data["behavioral_profile"]
    labels = ['Skip Rate', 'Shuffle Rate', 'Selection']
    values = [profile['skip_rate'] * 100, profile['shuffle_rate'] * 100, profile['active_selection_score'] * 100]
    
    plt.figure(figsize=(10, 5))
    colors = sns.color_palette("viridis", 3)
    plt.barh(labels, values, color=colors)
    plt.title(f"Behavioral Signal Bands: {subject_name.upper()}", fontsize=14, fontweight='bold')
    plt.xlabel("Score (%)")
    plt.xlim(0, 100)
    plt.tight_layout()
    
    output_path = os.path.join(LOCAL_REPORT_DIR, f"audit_plot_taxonomy_{subject_name}.png")
    plt.savefig(output_path)
    plt.close()
    return output_path

def plot_source_composition(data, subject_name):
    """Plots the 4-way Source classification as a donut chart."""
    if "source_composition" not in data:
        return None
        
    source_comp = data["source_composition"]
    labels = list(source_comp.keys())
    sizes = [float(v) * 100 for v in source_comp.values()]
    
    plt.figure(figsize=(8, 8))
    colors = ['#1DB954', '#535353', '#B3B3B3', '#191414']
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors[:len(labels)], startangle=140, pctdistance=0.85)
    
    centre_circle = plt.Circle((0,0),0.70,fc='white')
    fig = plt.gcf()
    fig.gca().add_artist(centre_circle)
    
    plt.title(f"Source Composition: {subject_name.upper()}", fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    output_path = os.path.join(LOCAL_REPORT_DIR, f"audit_plot_source_{subject_name}.png")
    plt.savefig(output_path)
    plt.close()
    return output_path

def plot_routine_heatmap(data, subject_name):
    """Plots the 7x24 weekday/hour matrix as a heatmap."""
    if "routine_heatmap" not in data:
        return None
        
    hm_data = data["routine_heatmap"]
    df = pd.DataFrame.from_dict(hm_data, orient='index')
    
    df.columns = df.columns.astype(int)
    df = df.sort_index(axis=1)
    
    plt.figure(figsize=(12, 6))
    sns.heatmap(df, cmap="YlGnBu", cbar_kws={'label': 'Stream Count'})
    plt.title(f"Listening Routine Heatmap: {subject_name.upper()}", fontsize=14, fontweight='bold')
    plt.xlabel("Hour of Day")
    plt.ylabel("Day of Week")
    plt.tight_layout()
    
    output_path = os.path.join(LOCAL_REPORT_DIR, f"audit_plot_heatmap_{subject_name}.png")
    plt.savefig(output_path)
    plt.close()
    return output_path

def create_markdown_summary(data, subject_name):
    """Creates a small markdown table of the key dataset stats."""
    shape = data.get("dataset_shape", {})
    coverage = data.get("date_coverage", {})
    profile = data.get("behavioral_profile", {})
    
    table = f"""
### Audit Summary: {subject_name.upper()}
| Metric | Value |
| :--- | :--- |
| **Label** | **{profile.get('behavioral_label_primary', 'N/A')}** |
| Confidence | {profile.get('classification_confidence', 'N/A')} |
| Total Streams | {shape.get('rows', 0):,} |
| Start Date | {coverage.get('start', 'N/A')} |
| End Date | {coverage.get('end', 'N/A')} |
"""
    return table

if __name__ == "__main__":
    os.makedirs(LOCAL_REPORT_DIR, exist_ok=True)
    summaries = load_audit_files()
    
    if not summaries:
        print(f"No audit result files found in {INPUT_JSON_DIR}")
    else:
        print(f"Generating visualizations for {len(summaries)} subjects...")
        full_report = "# Spotify v2 Data Audit Visual Report\n"
        
        for summary_path in summaries:
            summary_filename = os.path.basename(summary_path)
            subject_id = summary_filename.replace("audit_summary_", "").replace(".json", "")
            print(f"Processing subject: {subject_id}...")
            
            with open(summary_path, 'r') as f:
                data = json.load(f)
            
            full_report += create_markdown_summary(data, subject_id)
            
            # Taxonomy
            tax_img = plot_taxonomy(data, subject_id)
            if tax_img: full_report += f"\n![Behavioral Taxonomy](local_reports/{os.path.basename(tax_img)})\n"
            
            # Source Composition
            src_img = plot_source_composition(data, subject_id)
            if src_img: full_report += f"\n![Source Composition](local_reports/{os.path.basename(src_img)})\n"
            
            # Routine Heatmap
            hm_img = plot_routine_heatmap(data, subject_id)
            if hm_img: full_report += f"\n![Routine Heatmap](local_reports/{os.path.basename(hm_img)})\n"
            
            full_report += "\n---\n"
            
        report_path = os.path.join(os.path.dirname(LOCAL_REPORT_DIR), "audit_visual_report.md")
        with open(report_path, "w") as f:
            f.write(full_report)
            
        print("\n" + "="*60)
        print(" VISUALIZATION COMPLETE ")
        print(f" Results saved to: research_pipeline/local_reports/ ")
        print("="*60)
