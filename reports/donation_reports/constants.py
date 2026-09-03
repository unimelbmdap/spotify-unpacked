"""Analysis constants, loaded from constants.json.

The JSON is the single source on the Python side. The frontend keeps its own
copies in src/lib/dateWindow.ts and src/lib/archetypeConfig.ts; a Vitest
compares them to this file so drift fails the frontend test run.
"""

import json
from pathlib import Path

_DATA = json.loads((Path(__file__).parent / "constants.json").read_text(encoding="utf-8"))

# Study analysis window start ('YYYY-MM-DD'). Streaming plays before this date
# are dropped; library and playlists are not bounded by it.
WINDOW_START: str = _DATA["window_start"]

# Number of trailing months shown in the monthly listening bar chart and the
# monthly stats grid page; both read the same trailing window.
BAR_CHART_MONTHS_SHOWN: int = _DATA["bar_chart_months_shown"]

# Bands are {min, max, weight} over a 0-1 rate; a missing min/max defaults to
# 0/1 (see band_score).
ARCHETYPE_BANDS: dict[str, dict[str, dict[str, float]]] = _DATA["archetypes"]

# 'fwdbtn' is excluded since it's the same underlying event 'skipped' already
# captures (counted separately via skip_rate).
RESPONSIVE_REASON_END_VALUES: frozenset[str] = frozenset(_DATA["responsive_reason_end_values"])
RESPONSIVE_REASON_START_VALUES: frozenset[str] = frozenset(_DATA["responsive_reason_start_values"])

# streaming_history.json timestamps are UTC with no per-donor timezone info;
# assume AEST (UTC+10, no daylight saving). Python-only: the frontend renders
# in the browser's local time.
ASSUMED_TZ_OFFSET_HOURS = 10


def band_score(rate: float, band: dict[str, float]) -> float:
    """Position of `rate` within the band, clamped to [0, 1].

    Mirrors bandScore in src/lib/archetypeConfig.ts.
    """
    lo = band.get("min", 0)
    hi = band.get("max", 1)
    return min(max((rate - lo) / (hi - lo), 0), 1)
