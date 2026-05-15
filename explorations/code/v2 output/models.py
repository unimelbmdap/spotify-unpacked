from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal, Dict

# --- SETTINGS MODELS ---

class BehavioralBandSettings(BaseSettings):
    """Provisional placeholder thresholds for behavioral bands. To be calibrated."""
    skip_low_max: float = 0.1104
    skip_medium_max: float = 0.3669
    shuffle_low_max: float = 0.2643
    shuffle_medium_max: float = 0.4397
    active_selection_low_max: float = 0.0523
    active_selection_medium_max: float = 0.2516
    min_data_sufficiency: int = 100
    signal_dominance_threshold: float = 0.6
    platform_dominance_threshold: float = 0.5
    
    model_config = SettingsConfigDict(env_prefix="SPOTIFY_", env_file=".env", env_file_encoding="utf-8", extra="ignore")


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
    
    model_config = SettingsConfigDict(env_prefix="EMOTION_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Instantiate configured instances
behavior_settings = BehavioralBandSettings()
emotion_settings = EmotionProfileSettings()

# --- OUTPUT SCHEMA MODELS ---

class BandedBehavioralProfile(BaseModel):
    """Simplified JSON payload for the frontend."""
    # Raw Rates
    skip_rate: float
    shuffle_rate: float
    active_selection_score: float
    
    # Bands
    skip_level: Literal["Low", "Medium", "High", "Unknown"]
    shuffle_level: Literal["Low", "Medium", "High", "Unknown"]
    deliberate_level: Literal["Low", "Medium", "High", "Unknown"]
    
    # Supporting Attributes
    platform_distribution: Dict[str, float]
    platform_mode: str
    
    # Final Interpretation
    behavioral_label_primary: Literal["Receptive (Provisional)", "Responsive (Provisional)", "Deliberate (Provisional)", "Mixed (Provisional)", "Insufficient Data"]
    classification_confidence: Literal["High", "Medium", "Low", "Baseline", "None"]
    behavioral_basis_note: str

class EmotionProfileResult(BaseModel):
    """Structured output schema for emotional profiling (Layer 2)."""
    person_id: str
    profile_label: str
    profile_description: str
    intentionality_band: str
    emotional_range_band: str
    pressure_signal_band: str
    match_coverage_percent: float
    profile_basis_note: str
    profile_conf: float
    heavy_share_raw: float
    heavy_share_cred: float
    upbeat_share_raw: float
    upbeat_share_cred: float
    exam_peak_share_raw: float
    exam_tail_ratio: float
    disclaimer: str
