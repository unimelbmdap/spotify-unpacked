import json
from pathlib import Path

import pytest

from donation_reports import constants
from donation_reports.constants import ARCHETYPE_BANDS, band_score


def test_json_loads_and_matches_module():
    raw = json.loads((Path(constants.__file__).parent / "constants.json").read_text())
    assert constants.WINDOW_START == raw["window_start"]
    assert constants.BAR_CHART_MONTHS_SHOWN == raw["bar_chart_months_shown"]
    assert set(ARCHETYPE_BANDS) == {"receptive", "responsive", "deliberate"}
    assert constants.RESPONSIVE_REASON_END_VALUES == {"endplay", "backbtn"}
    assert constants.RESPONSIVE_REASON_START_VALUES == {"popup"}


def test_weights_sum_to_one_per_archetype():
    for key, bands in ARCHETYPE_BANDS.items():
        total = sum(b["weight"] for b in bands.values())
        assert total == pytest.approx(1.0), key


@pytest.mark.parametrize(("rate", "band", "expected"), [
    (0.0, {"min": 0.2, "max": 0.7}, 0.0),
    (0.2, {"min": 0.2, "max": 0.7}, 0.0),
    (0.45, {"min": 0.2, "max": 0.7}, 0.5),
    (0.7, {"min": 0.2, "max": 0.7}, 1.0),
    (0.9, {"min": 0.2, "max": 0.7}, 1.0),
    (0.05, {"max": 0.1}, 0.5),          # missing min defaults to 0
    (0.55, {"min": 0.1}, 0.5),          # missing max defaults to 1
    (0.0, {"min": 1.0, "max": 0}, 1.0), # inverted band: high score at the low end
    (1.0, {"min": 1.0, "max": 0}, 0.0),
])
def test_band_score_matches_frontend_bandscore(rate, band, expected):
    assert band_score(rate, band) == pytest.approx(expected)


def test_deliberate_algorithmic_mirrors_receptive():
    """deliberate.algorithmic == 1 - receptive.algorithmic at every rate (as in archetypeConfig.ts)."""
    rec = ARCHETYPE_BANDS["receptive"]["algorithmic"]
    dlb = ARCHETYPE_BANDS["deliberate"]["algorithmic"]
    for rate in (0.0, 0.2, 0.35, 0.5, 0.7, 1.0):
        assert band_score(rate, dlb) == pytest.approx(1 - band_score(rate, rec))
