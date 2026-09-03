"""Companion JSON written beside each PDF.

An explicit allowlist of JSON-native summaries from DonorStats: provenance,
what was donated, and the numbers the charts were drawn from. Never the raw
streaming rows or playlist contents.
"""

from datetime import UTC, datetime
from typing import Any

import numpy as np

from donation_reports.constants import BAR_CHART_MONTHS_SHOWN, WINDOW_START
from donation_reports.naming import BundleName
from donation_reports.stats import DonorStats
from donation_reports.version import COMPANION_SCHEMA


def _native(value: Any) -> Any:
    """Recursively convert numpy scalars/arrays to plain Python for json.dumps."""
    if isinstance(value, dict):
        return {str(k): _native(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_native(v) for v in value]
    if isinstance(value, np.ndarray):
        return _native(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    return value


def build_companion(
    donor: DonorStats,
    bundle: BundleName,
    *,
    version: int,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    generated_at = generated_at or datetime.now(UTC)
    stats = {
        "shuffle_rate": donor.shuffle_rate,
        "skip_rate": donor.skip_rate,
        "responsive_reason_rate": donor.responsive_reason_rate,
        "algorithmic_rate": donor.algorithmic_rate,
        "archetype_scores": donor.archetype_scores,
        "strongest_archetype": donor.strongest_archetype,
        "top_artist": donor.top_artist,
        "top_song": donor.top_song,
        "top_playlist": donor.top_playlist,
        "monthly_stats": donor.monthly_stats,
        "date_keys": donor.date_keys,
        "by_date_library": donor.by_date_library,
        "by_date_other": donor.by_date_other,
        "by_date_library_only": donor.by_date_library_only,
        "by_date_playlist": donor.by_date_playlist,
        "heatmap_hours": donor.heatmap_hours,
    }
    return _native({
        "schema": COMPANION_SCHEMA,
        "generator_version": version,
        "generated_at": generated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_bundle": bundle.zip_name,
        "participant_code": bundle.code,
        "donation_id": bundle.donation_id,
        "has_library": bool(donor.has_library),
        "has_playlists": bool(donor.has_playlist),
        "streaming_rows_in_window": int(len(donor.streaming.index)),
        "window_start": WINDOW_START,
        "months_shown": BAR_CHART_MONTHS_SHOWN,
        "stats": stats,
    })
