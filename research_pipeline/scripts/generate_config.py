import os
import json
import sys

# Add the parent directory of 'scripts' to sys.path so we can import 'core.models'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.models import behavior_settings, emotion_settings, visual_settings

def generate_frontend_config():
    """Dumps relevant Pydantic settings into a config.json for the Vue frontend."""
    # Combine settings into a single dict
    config = {
        # Visual Settings
        "peak_min_share": visual_settings.peak_min_share,
        "peak_proximity_days": visual_settings.peak_proximity_days,
        "shift_lead_threshold": visual_settings.shift_lead_threshold,
        "shift_cooldown_days": visual_settings.shift_cooldown_days,
        "data_min_track_duration_ms": visual_settings.min_track_duration_ms,

        # Emotion Profile Settings (for personas)
        "stabiliser_entropy_max": emotion_settings.stabiliser_entropy_max,
        "processor_heavy_raw": emotion_settings.processor_heavy_raw,
        "calm_share_min": 0.30,  # Fallback mappings for the frontend's provisional logic
        "uplifter_upbeat_raw": emotion_settings.uplifter_upbeat_raw,
        "explorer_entropy_min": emotion_settings.explorer_entropy_min
    }

    # Define output path in public/data
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "public", "data")
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, "config.json")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)
        
    print(f"Successfully generated frontend configuration at: {output_file}")

if __name__ == "__main__":
    generate_frontend_config()
