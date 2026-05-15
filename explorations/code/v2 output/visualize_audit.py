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
    """Finds all audit summary and skip validation files in the directory."""
    summary_files = glob.glob(os.path.join(directory, "audit_summary_*.json"))
    skip_files = glob.glob(os.path.join(directory, "audit_skip_validation_*.csv"))
    return summary_files, skip_files

def plot_skip_reliability(csv_path, subject_name):
    """Plots the Raw vs Proxy skip rate over time."""
    df = pd.read_csv(csv_path)
    if 'year' not in df.columns:
        df = df.rename(columns={'Unnamed: 0': 'year'})
    
    plt.figure(figsize=(10, 5))
    plt.plot(df['year'], df['Raw_Skip_Rate'], marker='o', label='Raw Skip Rate (Official Flag)', color='#1DB954', linewidth=2)
    plt.plot(df['year'], df['Proxy_Skip_Rate'], marker='s', linestyle='--', label='Proxy Skip Rate (Behavioral)', color='#191414', alpha=0.7)
    
    plt.title(f"Skip Reliability Check: {subject_name.upper()}", fontsize=14, fontweight='bold')
    plt.xlabel("Year")
    plt.ylabel("Skip Rate (%)")
    plt.ylim(0, 105)
    plt.legend()
    plt.tight_layout()
    
    output_path = f"audit_plot_skip_{subject_name}.png"
    plt.savefig(output_path)
    plt.close()
    return output_path

def plot_taxonomy(data, subject_name):
    """Plots the Receptive/Responsive/Deliberate taxonomy as a horizontal bar chart."""
    if "categorical_distributions" not in data or "reason_start_bucket" not in data["categorical_distributions"]:
        return None
        
    dist = data["categorical_distributions"]["reason_start_bucket"]
    s = pd.Series(dist).sort_values(ascending=True) * 100
    
    plt.figure(figsize=(10, 5))
    colors = sns.color_palette("viridis", len(s))
    s.plot(kind='barh', color=colors)
    plt.title(f"Behavioral Taxonomy: {subject_name.upper()}", fontsize=14, fontweight='bold')
    plt.xlabel("Percentage of Streams (%)")
    plt.tight_layout()
    
    output_path = f"audit_plot_taxonomy_{subject_name}.png"
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
    
    # Draw center circle to make it a donut
    centre_circle = plt.Circle((0,0),0.70,fc='white')
    fig = plt.gcf()
    fig.gca().add_artist(centre_circle)
    
    plt.title(f"Source Composition: {subject_name.upper()}", fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    output_path = f"audit_plot_source_{subject_name}.png"
    plt.savefig(output_path)
    plt.close()
    return output_path

def plot_routine_heatmap(data, subject_name):
    """Plots the 7x24 weekday/hour matrix as a heatmap."""
    if "routine_heatmap" not in data:
        return None
        
    hm_data = data["routine_heatmap"]
    df = pd.DataFrame.from_dict(hm_data, orient='index')
    
    # Sort columns numerically (0-23)
    df.columns = df.columns.astype(int)
    df = df.sort_index(axis=1)
    
    plt.figure(figsize=(12, 6))
    sns.heatmap(df, cmap="YlGnBu", cbar_kws={'label': 'Stream Count'})
    plt.title(f"Listening Routine Heatmap: {subject_name.upper()}", fontsize=14, fontweight='bold')
    plt.xlabel("Hour of Day")
    plt.ylabel("Day of Week")
    plt.tight_layout()
    
    output_path = f"audit_plot_heatmap_{subject_name}.png"
    plt.savefig(output_path)
    plt.close()
    return output_path

def create_markdown_summary(data, subject_name):
    """Creates a small markdown table of the key dataset stats."""
    shape = data.get("dataset_shape", {})
    coverage = data.get("date_coverage", {})
    
    table = f"""
### Audit Summary: {subject_name.upper()}
| Metric | Value |
| :--- | :--- |
| Total Streams | {shape.get('rows', 0):,} |
| Start Date | {coverage.get('start', 'N/A')} |
| End Date | {coverage.get('end', 'N/A')} |
"""
    return table

if __name__ == "__main__":
    summaries, skips = load_audit_files()
    
    if not summaries:
        print("No audit result files found.")
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
            if tax_img: full_report += f"\n![Behavioral Taxonomy]({tax_img})\n"
            
            # Source Composition
            src_img = plot_source_composition(data, subject_id)
            if src_img: full_report += f"\n![Source Composition]({src_img})\n"
            
            # Routine Heatmap
            hm_img = plot_routine_heatmap(data, subject_id)
            if hm_img: full_report += f"\n![Routine Heatmap]({hm_img})\n"
            
            # Skip Reliability
            skip_path = f"audit_skip_validation_{subject_id}.csv"
            if os.path.exists(skip_path):
                skip_img = plot_skip_reliability(skip_path, subject_id)
                full_report += f"\n![Skip Reliability]({skip_img})\n"
            
            full_report += "\n---\n"
            
        with open("audit_visual_report.md", "w") as f:
            f.write(full_report)
            
        print("\n" + "="*60)
        print(" VISUALIZATION COMPLETE ")
        print(f" Results saved to: audit_visual_report.md and associated PNGs ")
        print("="*60)
