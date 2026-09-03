"""Synthetic donation bundles for tests.

`make_bundle` writes a zip in the shape src/lib/donationPayload.ts produces,
with enough plays across several months to exercise every chart, plus a
library and a playlist covering some of the URIs.
"""

import json
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from donation_reports import fonts

URIS = [f"spotify:track:{i:022d}" for i in range(1, 13)]
ARTISTS = ["Artist A", "Artist B", "Artist C"]
LIBRARY_URIS = URIS[:3]
PLAYLIST_URIS = URIS[3:6]


def streaming_entries(*, start: str = "2025-08-01T10:00:00Z", days: int = 200, per_day: int = 3) -> list[dict]:
    """Deterministic plays: `per_day` plays a day for `days` days from `start`."""
    t0 = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ")
    entries = []
    n = 0
    for d in range(days):
        for k in range(per_day):
            uri = URIS[(n * 7) % len(URIS)]
            ts = t0 + timedelta(days=d, hours=(k * 5) % 24)
            entries.append({
                "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "ms_played": 120_000 + (n % 5) * 30_000,
                "master_metadata_track_name": f"Track {URIS.index(uri) + 1}",
                "master_metadata_album_artist_name": ARTISTS[URIS.index(uri) % 3],
                "spotify_track_uri": uri,
                "shuffle": n % 2 == 0,
                "skipped": n % 4 == 0,
                "reason_start": "popup" if n % 9 == 0 else "trackdone",
                "reason_end": "backbtn" if n % 11 == 0 else "trackdone",
            })
            n += 1
    return entries


def library_payload() -> dict:
    return {"tracks": [{"uri": u, "track": f"Track {i}", "artist": ARTISTS[i % 3]}
                       for i, u in enumerate(LIBRARY_URIS, start=1)]}


def playlists_payload() -> dict:
    return {"playlists": [{
        "name": "Test playlist",
        "items": [{"track": {"trackUri": u, "trackName": f"Track {i}"}} for i, u in enumerate(PLAYLIST_URIS)],
    }]}


def make_bundle(
    directory: Path,
    *,
    code: str = "ABC12",
    stamp: str = "20260901-101500",
    donation_id: int = 12,
    streaming: list | None | str = "default",
    library: dict | None | str = "default",
    playlists: dict | None | str = "default",
    sidecar: bool = True,
    raw_members: dict[str, bytes] | None = None,
) -> Path:
    """Write donation_<code>__<stamp>__<id>.zip (+ sidecar) into `directory`.

    Pass None for a member to omit it. `raw_members` overrides member bytes,
    for malformed-content cases.
    """
    directory.mkdir(parents=True, exist_ok=True)
    name = f"donation_{code}__{stamp}__{donation_id}.zip"
    path = directory / name
    members: dict[str, bytes] = {}
    if streaming is not None:
        entries = streaming_entries() if streaming == "default" else streaming
        members["streaming_history.json"] = json.dumps(entries).encode()
    if library is not None:
        members["your_library.json"] = json.dumps(library_payload() if library == "default" else library).encode()
    if playlists is not None:
        members["playlists.json"] = json.dumps(playlists_payload() if playlists == "default" else playlists).encode()
    members.update(raw_members or {})
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for member, data in members.items():
            zf.writestr(member, data)
    if sidecar:
        (directory / f"{name}.json").write_text(json.dumps({
            "donor_code": code, "submitted_at": "2026-09-01T10:15:00+00:00", "consent_version": "v1.0",
        }))
    return path


@pytest.fixture
def donations_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data" / "donations"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def assets_dir(tmp_path: Path) -> Path:
    """An assets dir with no fonts and no images: the fallback path."""
    d = tmp_path / "assets"
    (d / "fonts").mkdir(parents=True)
    (d / "images").mkdir(parents=True)
    return d


@pytest.fixture(autouse=True)
def _reset_fonts():
    fonts.reset_for_tests()
    yield
    fonts.reset_for_tests()
