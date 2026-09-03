import json
from pathlib import Path

import pytest

from donation_reports.constants import WINDOW_START
from donation_reports.loader import BundleError, build_streaming_frame, load_bundle
from tests.conftest import make_bundle, streaming_entries


def test_loads_all_three_members(donations_dir: Path):
    path = make_bundle(donations_dir)
    streaming, library, playlists = load_bundle(path)
    assert len(streaming) == 600
    assert len(library["tracks"]) == 3
    assert len(playlists["playlists"]) == 1


def test_missing_members_default_to_empty(donations_dir: Path):
    path = make_bundle(donations_dir, library=None, playlists=None)
    streaming, library, playlists = load_bundle(path)
    assert streaming
    assert library == {"tracks": []}
    assert playlists == {"playlists": []}


def test_library_only_bundle(donations_dir: Path):
    path = make_bundle(donations_dir, streaming=None, playlists=None)
    streaming, library, playlists = load_bundle(path)
    assert streaming == []
    assert library["tracks"]
    assert build_streaming_frame(streaming).empty


def test_not_a_zip(donations_dir: Path):
    path = donations_dir / "donation_X__20260901-101500__1.zip"
    path.write_bytes(b"definitely not a zip")
    with pytest.raises(BundleError, match="not a readable zip"):
        load_bundle(path)


def test_member_not_json(donations_dir: Path):
    path = make_bundle(donations_dir, raw_members={"streaming_history.json": b"{not json"})
    with pytest.raises(BundleError, match="not valid JSON"):
        load_bundle(path)


def test_member_wrong_type(donations_dir: Path):
    path = make_bundle(donations_dir, raw_members={"streaming_history.json": json.dumps({"a": 1}).encode()})
    with pytest.raises(BundleError, match="must be a list"):
        load_bundle(path)


def test_frame_filters_window_and_non_tracks():
    entries = streaming_entries(start="2024-12-30T10:00:00Z", days=4, per_day=1)
    entries.append({**entries[0], "spotify_track_uri": None})  # podcast/local file row
    df = build_streaming_frame(entries)
    assert (df["date_key"] >= WINDOW_START).all()
    assert len(df) == 2  # 2024-12-30 and 2024-12-31 dropped; None-URI row dropped
    assert {"hour", "weekday_idx", "month_key", "date_key", "minutes_rounded"} <= set(df.columns)


def test_frame_applies_assumed_timezone():
    entries = streaming_entries(start="2025-06-01T20:00:00Z", days=1, per_day=1)
    df = build_streaming_frame(entries)
    assert df["date_key"].iloc[0] == "2025-06-02"  # 20:00Z + 10h rolls to the next day
    assert int(df["hour"].iloc[0]) == 6


def test_frame_empty_when_everything_precedes_window():
    entries = streaming_entries(start="2024-01-01T10:00:00Z", days=10, per_day=1)
    assert build_streaming_frame(entries).empty


def test_frame_missing_required_field_raises():
    entries = [{k: v for k, v in e.items() if k != "shuffle"} for e in streaming_entries(days=2, per_day=1)]
    with pytest.raises(BundleError, match="shuffle"):
        build_streaming_frame(entries)


def test_frame_non_numeric_ms_played_raises():
    entries = streaming_entries(days=2, per_day=1)
    entries[0]["ms_played"] = "lots"
    with pytest.raises(BundleError, match="ms_played"):
        build_streaming_frame(entries)
