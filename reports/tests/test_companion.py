import json
from datetime import UTC, datetime
from pathlib import Path

from donation_reports.companion import build_companion
from donation_reports.loader import build_streaming_frame, load_bundle
from donation_reports.naming import parse_bundle_name
from donation_reports.stats import DonorStats
from tests.conftest import make_bundle

REQUIRED_TOP_LEVEL = {
    "schema", "generator_version", "generated_at", "source_bundle", "participant_code",
    "donation_id", "has_library", "has_playlists", "streaming_rows_in_window",
    "window_start", "months_shown", "stats",
}
REQUIRED_STATS = {
    "shuffle_rate", "skip_rate", "responsive_reason_rate", "algorithmic_rate",
    "archetype_scores", "strongest_archetype", "top_artist", "top_song", "top_playlist",
    "monthly_stats", "date_keys", "by_date_library", "by_date_other",
    "by_date_library_only", "by_date_playlist", "heatmap_hours",
}


def _companion(path: Path, version: int = 1) -> dict:
    name = parse_bundle_name(path)
    assert name is not None
    streaming, library, playlists = load_bundle(path)
    donor = DonorStats(name.code, build_streaming_frame(streaming), library, playlists)
    return build_companion(donor, name, version=version,
                           generated_at=datetime(2026, 9, 2, 4, 11, 9, tzinfo=UTC))


def test_is_json_serialisable_with_plain_types(donations_dir: Path):
    doc = _companion(make_bundle(donations_dir))
    text = json.dumps(doc)  # raises on numpy types
    assert json.loads(text) == doc
    assert isinstance(doc["stats"]["heatmap_hours"], list)
    assert all(isinstance(v, float) for row in doc["stats"]["heatmap_hours"] for v in row)


def test_required_keys_and_provenance(donations_dir: Path):
    doc = _companion(make_bundle(donations_dir, code="XYZ", donation_id=7), version=3)
    assert REQUIRED_TOP_LEVEL <= set(doc)
    assert REQUIRED_STATS <= set(doc["stats"])
    assert doc["generator_version"] == 3
    assert doc["generated_at"] == "2026-09-02T04:11:09Z"
    assert doc["source_bundle"] == "donation_XYZ__20260901-101500__7.zip"
    assert doc["participant_code"] == "XYZ"
    assert doc["donation_id"] == 7
    assert doc["has_library"] is True and doc["has_playlists"] is True
    assert doc["streaming_rows_in_window"] == 600


def test_never_contains_raw_streaming_rows(donations_dir: Path):
    doc = _companion(make_bundle(donations_dir))
    text = json.dumps(doc)
    assert "spotify:track:" not in text
    assert "ms_played" not in text


def test_library_only_bundle(donations_dir: Path):
    doc = _companion(make_bundle(donations_dir, streaming=None, playlists=None))
    assert doc["has_library"] is True and doc["has_playlists"] is False
    assert doc["streaming_rows_in_window"] == 0
    assert doc["stats"]["date_keys"] == []
    assert doc["stats"]["top_artist"] is None
