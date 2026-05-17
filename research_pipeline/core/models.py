import os
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class BehavioralBandSettings(BaseSettings):
    """Thresholds for behavioral banding (Skip, Shuffle, Selection)."""
    skip_low_max: float = 0.1104
    skip_medium_max: float = 0.2523
    shuffle_low_max: float = 0.1245
    shuffle_medium_max: float = 0.3567
    active_selection_low_max: float = 0.0523
    active_selection_medium_max: float = 0.2516
    min_data_sufficiency: int = 100
    signal_dominance_threshold: float = 0.6
    platform_dominance_threshold: float = 0.5
    
    # Updated to look one level up from the scripts directory
    model_config = SettingsConfigDict(
        env_prefix="SPOTIFY_", 
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"), 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

class EmotionProfileSettings(BaseSettings):
    """Configuration for emotional regulation labeling thresholds."""
    # Sub-score bands
    intent_high_cred: float = 15.0
    intent_moderate_cred: float = 5.0
    pressure_high_exam_tail: float = 2.0
    pressure_moderate_exam_tail: float = 1.2
    
    # Provisional fallback
    min_coverage_raw: float = 15.0
    min_coverage_conf: float = 0.15
    
    # Profile triggers
    time_specific_daypart_tail: float = 0.60
    processor_heavy_raw: float = 0.35
    processor_heavy_cred: float = 0.30
    processor_anchor_tail: float = 0.05
    uplifter_upbeat_raw: float = 0.45
    uplifter_upbeat_cred: float = 0.40
    stabiliser_entropy_max: float = 1.5
    stabiliser_anchor_tail: float = 0.10
    explorer_diversity_min: int = 4
    explorer_entropy_min: float = 2.0
    explorer_conc_tail_max: float = 0.50
    
    model_config = SettingsConfigDict(
        env_prefix="EMOTION_", 
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"), 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

class VisualSettings(BaseSettings):
    """Configuration for frontend visualization and analysis thresholds."""
    peak_min_share: float = 20.0
    peak_proximity_days: int = 7
    shift_lead_threshold: float = 10.0
    shift_cooldown_days: int = 5
    min_track_duration_ms: int = 30000

    model_config = SettingsConfigDict(
        env_prefix="VISUAL_", 
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"), 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

# Instantiate configured instances
behavior_settings = BehavioralBandSettings()
emotion_settings = EmotionProfileSettings()
visual_settings = VisualSettings()

class BandedBehavioralProfile(BaseModel):
    """Schema for the Banded Behavioral Profile exported to the frontend."""
    skip_rate: float
    shuffle_rate: float
    active_selection_score: float
    skip_level: str  # Low, Medium, High
    shuffle_level: str
    deliberate_level: str
    platform_distribution: Dict[str, float]
    platform_mode: str
    behavioral_label_primary: str
    classification_confidence: str
    behavioral_basis_note: str
