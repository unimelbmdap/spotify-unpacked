"""Read a donation bundle into the raw structures DonorStats expects.

A bundle is the zip the frontend builds in src/lib/donationPayload.ts:
`streaming_history.json` (list), `your_library.json` ({"tracks": [...]}) and
`playlists.json` ({"playlists": [...]}). Any subset may be present. Anything
malformed raises BundleError with a plain message that ends up in the failure
marker.
"""

import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from donation_reports.constants import ASSUMED_TZ_OFFSET_HOURS, WINDOW_START

STREAMING_MEMBER = "streaming_history.json"
LIBRARY_MEMBER = "your_library.json"
PLAYLISTS_MEMBER = "playlists.json"

# Columns build_streaming_frame and DonorStats index directly.
REQUIRED_STREAMING_FIELDS = (
    "ts",
    "ms_played",
    "master_metadata_track_name",
    "master_metadata_album_artist_name",
    "spotify_track_uri",
    "shuffle",
    "skipped",
    "reason_start",
    "reason_end",
)


class BundleError(Exception):
    """The bundle cannot be rendered; the message is safe to record in a marker."""


def _read_member(zf: zipfile.ZipFile, name: str, expected_type: type, default):
    if name not in zf.namelist():
        return default
    try:
        value = json.loads(zf.read(name))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise BundleError(f"{name} is not valid JSON: {exc}") from exc
    if not isinstance(value, expected_type):
        raise BundleError(f"{name} must be a {expected_type.__name__}, got {type(value).__name__}")
    return value


def load_bundle(zip_path: Path) -> tuple[list, dict, dict]:
    """(streaming entries, library, playlists) from a bundle zip.

    Missing members default to empty; DonorStats treats an empty library or
    playlist set as "not donated".
    """
    try:
        zf = zipfile.ZipFile(zip_path)
    except (zipfile.BadZipFile, OSError) as exc:
        raise BundleError(f"not a readable zip: {exc}") from exc
    with zf:
        streaming = _read_member(zf, STREAMING_MEMBER, list, [])
        library = _read_member(zf, LIBRARY_MEMBER, dict, {"tracks": []})
        playlists = _read_member(zf, PLAYLISTS_MEMBER, dict, {"playlists": []})
    if not isinstance(library.get("tracks", []), list):
        raise BundleError(f"{LIBRARY_MEMBER} 'tracks' must be a list")
    if not isinstance(playlists.get("playlists", []), list):
        raise BundleError(f"{PLAYLISTS_MEMBER} 'playlists' must be a list")
    return streaming, library, playlists


def build_streaming_frame(raw_entries: list) -> pd.DataFrame:
    """Streaming entries -> DataFrame with the derived time columns DonorStats uses.

    Rows without a track name or URI (podcasts, local files) and rows before
    WINDOW_START are dropped. Returns an empty frame when nothing remains.
    """
    entries = [e for e in raw_entries if isinstance(e, dict)]
    if not entries:
        return pd.DataFrame()
    df = pd.DataFrame(entries)
    missing = [c for c in REQUIRED_STREAMING_FIELDS if c not in df.columns]
    if missing:
        raise BundleError(f"{STREAMING_MEMBER} entries lack required fields: {', '.join(missing)}")

    df = df[df["master_metadata_track_name"].notna() & df["spotify_track_uri"].notna()]
    df = df[df["ts"].map(lambda v: isinstance(v, str))]
    df = df[df["ts"].str.slice(0, 10) >= WINDOW_START]
    if df.empty:
        return pd.DataFrame()

    try:
        local_dt = pd.to_datetime(df["ts"], utc=True).dt.tz_localize(None) + np.timedelta64(
            ASSUMED_TZ_OFFSET_HOURS, "h"
        )
    except (ValueError, TypeError) as exc:
        raise BundleError(f"{STREAMING_MEMBER} has an unparseable ts: {exc}") from exc
    ms_played = pd.to_numeric(df["ms_played"], errors="coerce")
    if ms_played.isna().any():
        raise BundleError(f"{STREAMING_MEMBER} has a non-numeric ms_played")
    df = df.assign(
        ms_played=ms_played,
        local_dt=local_dt,
        hour=local_dt.dt.hour,
        weekday_idx=local_dt.dt.weekday,  # Monday=0 ... Sunday=6, matches DAY_LABELS
        month_key=local_dt.dt.strftime("%Y-%m"),
        month_label=local_dt.dt.strftime("%b %Y"),
        date_key=local_dt.dt.strftime("%Y-%m-%d"),
        date_label=local_dt.dt.strftime("%-d %b %Y"),
        minutes_rounded=(ms_played / 60000).round().astype(int),
    )
    return df


def streaming_only(library: dict, playlists: dict) -> tuple[dict, dict]:
    """Empty library and playlists, for exercising the no-library rendering path."""
    del library, playlists
    return {"tracks": []}, {"playlists": []}
