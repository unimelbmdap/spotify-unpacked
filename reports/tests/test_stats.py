from pathlib import Path

import pandas as pd

from donation_reports.loader import build_streaming_frame, load_bundle
from donation_reports.stats import ARCHETYPE_CONFIG, ARCHETYPE_ORDER, DonorStats
from tests.conftest import make_bundle


def _donor(path: Path) -> DonorStats:
    streaming, library, playlists = load_bundle(path)
    return DonorStats("ABC12", build_streaming_frame(streaming), library, playlists)


def test_full_bundle_flags_and_scores(donations_dir: Path):
    donor = _donor(make_bundle(donations_dir))
    assert donor.has_library and donor.has_playlist and donor.has_any_library_data
    assert set(donor.archetype_scores) == set(ARCHETYPE_ORDER)
    for score in donor.archetype_scores.values():
        assert 0.0 <= score <= 1.0
    assert donor.strongest_archetype in ARCHETYPE_ORDER
    assert donor.top_artist and donor.top_song and donor.top_playlist
    assert donor.top_playlist["name"] == "Test playlist"
    assert len(donor.monthly_stats) >= 6
    assert donor.heatmap_hours.shape == (4, 7)
    assert len(donor.date_keys) == len(donor.by_date_library) == len(donor.by_date_other)


def test_streaming_only_bundle(donations_dir: Path):
    donor = _donor(make_bundle(donations_dir, library=None, playlists=None))
    assert not donor.has_library and not donor.has_playlist and not donor.has_any_library_data
    # Without library or playlist data the algorithmic share is meaningless,
    # so receptive and deliberate are pinned to zero (as in the web app).
    assert donor.archetype_scores["receptive"] == 0.0
    assert donor.archetype_scores["deliberate"] == 0.0
    assert donor.top_playlist is None
    assert "we do not have your library or playlist data" in donor.archetype_descriptions["receptive"]


def test_library_only_bundle_has_no_streaming(donations_dir: Path):
    donor = _donor(make_bundle(donations_dir, streaming=None, playlists=None))
    assert donor.has_library and not donor.has_playlist
    assert donor.date_keys == []
    assert donor.monthly_stats == []
    assert donor.top_artist is None and donor.top_song is None and donor.top_playlist is None
    assert donor.strongest_archetype == ARCHETYPE_ORDER[0]  # all zero: tie-break order
    assert all(score == 0.0 for score in donor.archetype_scores.values())
    assert not donor.has_streaming
    assert "cannot be assessed" in donor.archetype_descriptions["deliberate"]


def test_playlists_only_bundle(donations_dir: Path):
    donor = _donor(make_bundle(donations_dir, streaming=None, library=None))
    assert not donor.has_library and donor.has_playlist
    assert donor.date_keys == []


def test_empty_frame_is_handled():
    donor = DonorStats("X", pd.DataFrame(), {"tracks": []}, {"playlists": []})
    assert donor.date_keys == []
    assert donor.heatmap_hours.sum() == 0


def test_archetype_config_carries_text_and_bands():
    for key in ARCHETYPE_ORDER:
        cfg = ARCHETYPE_CONFIG[key]
        assert {"label", "short_label", "short_text", "description"} <= set(cfg)
    assert ARCHETYPE_CONFIG["receptive"]["algorithmic"]["weight"] == 1
    assert set(ARCHETYPE_CONFIG["deliberate"]) >= {"shuffle", "skip", "reason", "algorithmic"}


def test_zero_minute_month_reads_as_no_data():
    """Rows that all round to 0 minutes must not produce a '0 min' month card."""
    from donation_reports.loader import build_streaming_frame
    from tests.conftest import streaming_entries

    entries = streaming_entries(start="2025-06-01T10:00:00Z", days=40, per_day=1)
    for e in entries:
        if e["ts"].startswith("2025-07"):
            e["ms_played"] = 5_000  # 5 seconds: rounds to 0 minutes
    donor = DonorStats("X", build_streaming_frame(entries), {"tracks": []}, {"playlists": []})
    by_label = {m["month_label"]: m for m in donor.monthly_stats}
    assert "total_minutes" in by_label["Jun 2025"]
    assert "total_minutes" not in by_label["Jul 2025"]


def test_recent_month_keys_empty_input():
    from donation_reports.stats import _recent_month_keys

    assert _recent_month_keys([], 12) == []
