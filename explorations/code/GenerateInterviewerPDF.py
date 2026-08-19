# 2026 Spotify wrapped unwrapped
## FFAM-MDAP Collab
### Per-donor interviewer dashboard, rendered as a 2-page PDF (dashboard + archetype poster)
### Code written by Claude, Reviewed and adapted by Amanda Belton
import colorsys
import dataclasses
import json
import logging
import re
import textwrap
import zipfile
from datetime import datetime
from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Patch

# Metropolis is used for headings only (via explicit fontfamily="Metropolis"
# on title/suptitle calls below), everything else keeps the fallback stack.
# It's installed as a user font (~/Library/Fonts) but matplotlib's font cache
# is built once and doesn't pick up newly-installed fonts on its own, so
# register its files explicitly rather than relying on the cache. This
# particular Metropolis distribution also has broken OS/2 usWeightClass
# metadata (Thin/ExtraLight/Light/Regular all self-report as weight 400), so
# re-tag each file's weight from its filename or matplotlib's font matcher
# picks an arbitrary one of those four for "regular"/"semibold" weight text.
_METROPOLIS_WEIGHTS = {
    "thin": 100, "extralight": 200, "light": 300, "regular": 400,
    "medium": 500, "semibold": 600, "bold": 700, "extrabold": 800, "black": 900,
}
for _font_dir in ("/Library/Fonts", str(Path.home() / "Library/Fonts")):
    for _font_path in Path(_font_dir).glob("Metropolis-*.otf"):
        fm.fontManager.addfont(str(_font_path))
for _i, _entry in enumerate(fm.fontManager.ttflist):
    if _entry.name == "Metropolis":
        _stem = Path(_entry.fname).stem.lower().replace("metropolis-", "").replace("italic", "")
        if _stem in _METROPOLIS_WEIGHTS:
            fm.fontManager.ttflist[_i] = dataclasses.replace(_entry, weight=_METROPOLIS_WEIGHTS[_stem])

# Track/artist/playlist names can contain CJK or other non-Latin text; DejaVu
# Sans (matplotlib's default) can't render it, so prefer a broader-coverage
# font where available. Emoji glyphs still won't render (no colour-font
# support in matplotlib's text renderer) — that's a known, accepted gap.
# font.family is set directly to this list (rather than via the font.sans-serif
# alias) because only that form makes matplotlib fall back per-glyph across
# fonts — going through font.sans-serif picks one font for an entire string
# and silently drops any glyph that font lacks (e.g. CJK in Helvetica Neue).
plt.rcParams["font.family"] = ["Literata", "Arial Unicode MS", "PingFang HK", "Hiragino Sans GB", "DejaVu Sans"]
plt.rcParams["font.weight"] = "regular"
plt.rcParams["axes.titleweight"] = "bold"
plt.rcParams["axes.unicode_minus"] = False

# Building the per-glyph fallback chain above means matplotlib resolves every
# family in font.family for every weight used, not just whichever one ends up
# rendering a given piece of text. Literata (the one that actually renders
# Latin text) has all the weights used below and matches exactly; the other
# families exist purely as CJK/Unicode fallbacks and only ship one or two
# static weights, so matplotlib logs a "Failed to find font weight" warning
# every time it can't match one for them, even though they're never used for
# the weight-carrying Latin text. Harmless, but noisy — drop it to error level.
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR.parent / "AggregatedVisualisations" / "Data"
OUTPUT_DIR = BASE_DIR / "Output"
ASSETS_DIR = BASE_DIR.parent / "public"

INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
SPOTIFY_GREEN = "#1DB954"
CAPTION_GREEN = "#0E6631"
GRIDLINE = "#e1e0d9"
SURFACE = "#fcfcfb"

# Monthly listening bar chart series colours (library/playlists vs algorithmic/other).
LIBRARY_PLAYLIST_COLOR = "#4682b4"
ALGORITHM_OTHER_COLOR = "#ff7f50"
# Library-vs-playlist breakdown bar reuses the two colours above for its
# algorithm/other segment and pairs LIBRARY_PLAYLIST_COLOR with a second,
# lighter blue for playlists (so library/playlists read as one blue family,
# leaving coral for algorithm/other). Chosen via the dataviz skill's palette
# validator: clears CVD/normal-vision separation (>=15 dE) against both
# LIBRARY_PLAYLIST_COLOR and ALGORITHM_OTHER_COLOR.
PLAYLIST_COLOR = "#7ab3d9"


def hsla_to_hex(hue, saturation, lightness):
    r, g, b = colorsys.hls_to_rgb(hue / 360, lightness, saturation)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


RADAR_COLOR = SPOTIFY_GREEN

# Accent colour used per-archetype for the poster's card borders/scores.
ARCHETYPE_ACCENT_COLORS = {
    "receptive": "#c28fb2",
    "responsive": "#a909e9",
    "deliberate": "#8110b1",
}

# streaming_history.json timestamps are UTC with no per-donor timezone info;
# assume AEST (UTC+10, no daylight saving), same assumption as
# AggregatedDonorVisualisations.py.
ASSUMED_TZ_OFFSET_HOURS = 10

# Matches WINDOW_START in src/lib/dateWindow.ts: the study's analysis window
# that the live dashboard bounds streaming history to (library/playlists are
# not bounded by it, same as the frontend).
WINDOW_START = "2025-01-01"

DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Four fixed 6-hour buckets covering the day, in display (top-to-bottom) order.
# hour // 6 gives 0=12-6am, 1=6-12am, 2=12-6pm, 3=6pm-12am; the -1 % 4 rotates
# that so the row order below (Morning first) lines up.
TIME_SEGMENT_LABELS = ["Morning", "Afternoon", "Evening", "Night"]

# Ported from src/lib/archetypeConfig.ts. Bands are {min, max} over a 0-1 rate;
# a missing min/max defaults to 0/1. Tie-break order for the strongest
# archetype follows this declaration order (receptive, responsive,
# deliberate), matching the frontend's radar label order.
ARCHETYPE_ORDER = ["receptive", "responsive", "deliberate"]

ARCHETYPE_CONFIG = {
    "receptive": {
        "label": "Receptiveness",
        "short_label": "Receptive",
        "short_text": "You usually trust Spotify to choose music for you. You're happy to listen to the songs, playlists, or artists it recommends, rather than deciding everything yourself.",
        "algorithmic": {"min": 0.2, "max": 0.7, "weight": 1},
        "description": (
            "Receptiveness is associated with algorithmic affordances like the platform "
            "recommendations for algorithmic-driven discovery. This is interpreted as high "
            "trust in the curation of their listening experience by the platform."
        ),
    },
    "responsive": {
        "label": "Responsiveness",
        "short_label": "Responsive",
        "short_text": "You actively interact with Spotify while you listen. You might search for new music, shuffle your playlist, or skip songs to shape what you hear.",
        "description": (
            "Responsiveness is associated with active searching for new music, using shuffle, "
            "and using skip to curate the listening experience. This is interpreted as being "
            "responsive to the platform's suggestions and interactions."
        ),
        "shuffle": {"min": 0.1, "weight": 1 / 3},
        "skip": {"min": 0.05, "weight": 1 / 3},
        "reason": {"max": 0.1, "weight": 1 / 3},
    },
    "deliberate": {
        "label": "Deliberate",
        "short_label": "Deliberate",
        "short_text": "You prefer to choose your own music. You mainly listen to playlists, albums, or songs you've already saved and like to decide exactly what plays and in what order.",
        "description": (
            "Deliberate listening is associated with relying on a user's Spotify library and "
            "fixed ordering of playlists and albums. This is interpreted as a more deliberate "
            "and user-directed curation of the listening experience"
        ),
        "shuffle": {"min": 1.0, "max": 0, "weight": 1 / 4},
        "skip": {"min": 0.05, "max": 0, "weight": 1 / 4},
        "reason": {"min": 0.1, "max": 0, "weight": 1 / 4},
        "algorithmic": {"min": 0.7, "max": 0.2, "weight": 1 / 4},
    },
}

# 'fwdbtn' is excluded since it's the same underlying event 'skipped' already
# captures (counted separately via skip_rate).
RESPONSIVE_REASON_END_VALUES = {"endplay", "backbtn"}
RESPONSIVE_REASON_START_VALUES = {"popup"}

ARCHETYPE_PROFILE_IMAGES = {
    "receptive": ASSETS_DIR / "profile_receptive.jpg",
    "responsive": ASSETS_DIR / "profile_responsive.jpg",
    "deliberate": ASSETS_DIR / "profile_deliberate.jpg",
}


def band_score(rate, band):
    lo = band.get("min", 0)
    hi = band.get("max", 1)
    return min(max((rate - lo) / (hi - lo), 0), 1)


# Ported from InterviewerVizPanel.vue's showLevelAsText/joinWithAnd/archetypeCaptions.
def show_level_as_text(score):
    if score < 0.33:
        return "Low"
    if score < 0.66:
        return "Medium"
    return "High"


def join_with_and(parts):
    if len(parts) <= 1:
        return "".join(parts)
    if len(parts) == 2:
        return " and ".join(parts)
    return f"{', '.join(parts[:-1])}, and {parts[-1]}"


def format_minutes(minutes):
    minutes = round(minutes)
    if minutes < 60:
        return f"{minutes} min"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h" if mins == 0 else f"{hours}h {mins}m"


def format_playlist_duration(minutes):
    hours = minutes / 60
    if hours < 2:
        nearest = max(1, round(hours))
        return f"{nearest} hour" if nearest == 1 else f"{nearest} hours"
    nearest = round(hours)
    diff = hours - nearest
    if abs(diff) < (0.5 / 60):  # within 30 seconds of the hour mark
        return f"{nearest} hours"
    qualifier = "nearly" if diff < 0 else "just over"
    return f"{qualifier} {nearest} hours"


def participant_code_from_filename(path: Path) -> str:
    match = re.match(r"donation_([\w-]+)__2026", path.name)
    return match.group(1) if match else path.stem


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_donor_raw(zip_path: Path):
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        streaming = json.loads(zf.read("streaming_history.json")) if "streaming_history.json" in names else []
        library = json.loads(zf.read("your_library.json")) if "your_library.json" in names else {"tracks": []}
        playlists = json.loads(zf.read("playlists.json")) if "playlists.json" in names else {"playlists": []}
    return streaming, library, playlists


def build_streaming_frame(raw_entries) -> pd.DataFrame:
    df = pd.DataFrame(raw_entries)
    if df.empty:
        return df

    df = df[df["master_metadata_track_name"].notna() & df["spotify_track_uri"].notna()]
    df = df[df["ts"].str.slice(0, 10) >= WINDOW_START]
    if df.empty:
        return df

    local_dt = pd.to_datetime(df["ts"]) + pd.Timedelta(hours=ASSUMED_TZ_OFFSET_HOURS)
    df = df.assign(
        local_dt=local_dt,
        hour=local_dt.dt.hour,
        weekday_idx=local_dt.dt.weekday,  # Monday=0 ... Sunday=6, matches DAY_LABELS
        month_key=local_dt.dt.strftime("%Y-%m"),
        month_label=local_dt.dt.strftime("%b %Y"),
        date_key=local_dt.dt.strftime("%Y-%m-%d"),
        date_label=local_dt.dt.strftime("%-d %b %Y"),
        minutes_rounded=(df["ms_played"] / 60000).round().astype(int),
    )
    return df


def _top_playlist_in(playlists, df):
    """Playlist with the most plays within df, selected the same way as the
    dashboard's "Most played playlist" tile (most plays, ties none); reused
    per-month by DonorStats._compute_monthly_grid."""
    best = None
    for playlist in playlists:
        uris = {
            item["track"]["trackUri"]
            for item in playlist.get("items", [])
            if item.get("track") and item["track"].get("trackUri")
        }
        if not uris:
            continue
        mask = df["spotify_track_uri"].isin(uris)
        plays = int(mask.sum())
        if plays == 0:
            continue
        minutes = df.loc[mask, "ms_played"].sum() / 60000
        if best is None or plays > best["plays"]:
            best = {"name": playlist.get("name") or "Untitled playlist", "plays": plays, "minutes": minutes}
    return best


class DonorStats:
    def __init__(self, participant_code: str, streaming: pd.DataFrame, library: dict, playlists: dict):
        self.participant_code = participant_code
        self.streaming = streaming
        self.playlists = playlists.get("playlists", [])

        library_uris = {t["uri"] for t in library.get("tracks", []) if t.get("uri")}
        playlist_uris = {
            item["track"]["trackUri"]
            for pl in self.playlists
            for item in pl.get("items", [])
            if item.get("track") and item["track"].get("trackUri")
        }
        self.has_library = len(library_uris) > 0
        self.has_playlist = len(playlist_uris) > 0
        self.has_library_data = self.has_library and self.has_playlist
        self.has_any_library_data = self.has_library or self.has_playlist
        combined_library_uris = library_uris | playlist_uris

        if not streaming.empty:
            uris = streaming["spotify_track_uri"]
            # Library takes priority when a track is saved to both library and
            # a playlist, so this three-way split stays consistent with
            # is_library's pre-existing union-based (library OR playlist) flag.
            source = np.where(
                uris.isin(library_uris), "library",
                np.where(uris.isin(playlist_uris), "playlist", "other"),
            )
            self.streaming = streaming.assign(is_library=uris.isin(combined_library_uris), source=source)
        self._compute()

    def _by(self, df, column, n, labels_are_range=True):
        totals = df.groupby(column)["ms_played"].sum().reindex(range(n) if labels_are_range else None, fill_value=0)
        return (totals / 3_600_000).round(1).tolist()

    def _compute(self):
        df = self.streaming

        if not df.empty:
            lib_df = df[df["is_library"]]
            other_df = df[~df["is_library"]]
            by_date_lib = lib_df.groupby("date_key")["minutes_rounded"].sum() if not lib_df.empty else pd.Series(dtype=int)
            by_date_other = other_df.groupby("date_key")["minutes_rounded"].sum() if not other_df.empty else pd.Series(dtype=int)
            existing_keys = sorted(set(by_date_lib.index) | set(by_date_other.index))
            # Fill gaps (days with zero listening) so the x-axis reflects
            # true elapsed calendar time instead of compressing over them.
            full_range = pd.date_range(existing_keys[0], existing_keys[-1], freq="D")
            date_keys = full_range.strftime("%Y-%m-%d").tolist()
            self.date_keys = date_keys
            self.date_labels = full_range.strftime("%-d %b %Y").tolist()
            self.by_date_library = [int(by_date_lib.get(k, 0)) for k in date_keys]
            self.by_date_other = [int(by_date_other.get(k, 0)) for k in date_keys]

            # Library-only/playlist-only split of by_date_library above, for
            # the three-way breakdown bar (see "source" column in __init__).
            library_only_df = df[df["source"] == "library"]
            playlist_df = df[df["source"] == "playlist"]
            by_date_lib_only = library_only_df.groupby("date_key")["minutes_rounded"].sum() if not library_only_df.empty else pd.Series(dtype=int)
            by_date_playlist = playlist_df.groupby("date_key")["minutes_rounded"].sum() if not playlist_df.empty else pd.Series(dtype=int)
            self.by_date_library_only = [int(by_date_lib_only.get(k, 0)) for k in date_keys]
            self.by_date_playlist = [int(by_date_playlist.get(k, 0)) for k in date_keys]

            # Trailing-12-month slice of streaming rows, so the top-tiles,
            # day/time heatmap, and archetype scores describe the same
            # window as the monthly bar charts below them instead of the
            # donor's whole donated history (see _recent_month_keys).
            recent_months = _recent_month_keys(date_keys, BAR_CHART_MONTHS_SHOWN)
            recent_prefixes = {f"{y:04d}-{m:02d}" for y, m in recent_months}
            recent_df = df[df["date_key"].str.slice(0, 7).isin(recent_prefixes)]
        else:
            self.date_keys, self.date_labels, self.by_date_library, self.by_date_other = [], [], [], []
            self.by_date_library_only, self.by_date_playlist = [], []
            recent_df = df

        total_ms = recent_df["ms_played"].sum() if not recent_df.empty else 0
        recent_other_df = recent_df[~recent_df["is_library"]] if not recent_df.empty else recent_df

        if not recent_df.empty:
            # See TIME_SEGMENT_LABELS for the bucket/rotation rationale.
            segment_idx = ((recent_df["hour"] // 6) - 1) % 4
            cell_ms = recent_df.assign(segment_idx=segment_idx).groupby(["segment_idx", "weekday_idx"])["ms_played"].sum()
            heatmap_ms = np.zeros((len(TIME_SEGMENT_LABELS), len(DAY_LABELS)))
            for (segment, day), ms in cell_ms.items():
                heatmap_ms[segment, day] = ms
            self.heatmap_hours = heatmap_ms / 3_600_000
        else:
            self.heatmap_hours = np.zeros((len(TIME_SEGMENT_LABELS), len(DAY_LABELS)))

        shuffle_rate = recent_df["shuffle"].fillna(False).astype(bool).mean() if not recent_df.empty else 0
        skip_rate = recent_df["skipped"].fillna(False).astype(bool).mean() if not recent_df.empty else 0
        if not recent_df.empty:
            reason_mask = recent_df["reason_end"].isin(RESPONSIVE_REASON_END_VALUES) | recent_df["reason_start"].isin(RESPONSIVE_REASON_START_VALUES)
            responsive_reason_rate = reason_mask.mean()
        else:
            responsive_reason_rate = 0
        algorithmic_rate = (recent_other_df["ms_played"].sum() / total_ms) if total_ms > 0 else 0

        self.shuffle_rate = shuffle_rate
        self.skip_rate = skip_rate
        self.responsive_reason_rate = responsive_reason_rate
        self.algorithmic_rate = algorithmic_rate

        cfg = ARCHETYPE_CONFIG
        self.archetype_scores = {
            "receptive": (
                cfg["receptive"]["algorithmic"]["weight"] * band_score(algorithmic_rate, cfg["receptive"]["algorithmic"])
                if self.has_any_library_data else 0.0
            ),
            "responsive": (
                cfg["responsive"]["shuffle"]["weight"] * band_score(shuffle_rate, cfg["responsive"]["shuffle"])
                + cfg["responsive"]["skip"]["weight"] * band_score(skip_rate, cfg["responsive"]["skip"])
                + cfg["responsive"]["reason"]["weight"] * band_score(responsive_reason_rate, cfg["responsive"]["reason"])
            ),
            "deliberate": (
                (
                    cfg["deliberate"]["shuffle"]["weight"] * band_score(shuffle_rate, cfg["deliberate"]["shuffle"])
                    + cfg["deliberate"]["skip"]["weight"] * band_score(skip_rate, cfg["deliberate"]["skip"])
                    + cfg["deliberate"]["reason"]["weight"] * band_score(responsive_reason_rate, cfg["deliberate"]["reason"])
                    + cfg["deliberate"]["algorithmic"]["weight"] * band_score(algorithmic_rate, cfg["deliberate"]["algorithmic"])
                ) if self.has_any_library_data else 0.0
            ),
        }
        best_score = max(self.archetype_scores.values()) if self.archetype_scores else 0
        self.strongest_archetype = next(
            key for key in ARCHETYPE_ORDER if self.archetype_scores.get(key) == best_score
        )

        self._compute_archetype_descriptions()
        self._compute_top_tiles(recent_df)
        self._compute_monthly_grid(recent_df)

    def _compute_archetype_descriptions(self):
        cfg = ARCHETYPE_CONFIG
        shuffle_pct = round(self.shuffle_rate * 100)
        skip_pct = round(self.skip_rate * 100)
        reason_pct = round(self.responsive_reason_rate * 100)
        other_pct = round(self.algorithmic_rate * 100)

        # Library/playlist source phrasing: both cfg["receptive"] and
        # cfg["deliberate"] lean on algorithmic_rate, which is only meaningful
        # relative to whichever of library/playlists was actually donated -
        # e.g. a donor with playlists but no library export gets their % of
        # listening outside those playlists, not "outside library and
        # playlists" like a donor who gave both.
        if self.has_library and self.has_playlist:
            source_phrase = "your library and playlists"
            source_note = None
        elif self.has_playlist:
            source_phrase = "your playlists"
            source_note = "we did not receive your library data"
        elif self.has_library:
            source_phrase = "your library"
            source_note = "we did not receive your playlist data"
        else:
            source_phrase = None
            source_note = None

        responsive_parts = []
        if band_score(self.shuffle_rate, cfg["responsive"]["shuffle"]) > 0:
            responsive_parts.append(f"shuffle use ({shuffle_pct}% of plays)")
        if band_score(self.skip_rate, cfg["responsive"]["skip"]) > 0:
            responsive_parts.append(f"skips ({skip_pct}% of plays)")
        if band_score(self.responsive_reason_rate, cfg["responsive"]["reason"]) > 0:
            responsive_parts.append(f"back/popup-driven track changes ({reason_pct}% of plays)")

        if self.has_any_library_data:
            receptive_caveat = f" ({source_note})" if source_note else " (algorithm & other)"
            receptive_desc = (
                f"{cfg['receptive']['label']} is at {show_level_as_text(self.archetype_scores['receptive'])} - "
                f"This is based on your {other_pct}% listening time coming from outside "
                f"{source_phrase}{receptive_caveat}. {cfg['receptive']['description']}"
            )
        else:
            receptive_desc = (
                f"{cfg['receptive']['label']} is at Low (0%) because we do not have your library or "
                f"playlist data. {cfg['receptive']['description']}"
            )

        if self.has_any_library_data:
            deliberate_parts = []
            if band_score(self.shuffle_rate, cfg["deliberate"]["shuffle"]) > 0:
                deliberate_parts.append(f"low shuffle use ({shuffle_pct}% of plays)")
            if band_score(self.skip_rate, cfg["deliberate"]["skip"]) > 0:
                deliberate_parts.append(f"skips above a baseline rate ({skip_pct}% of plays)")
            if band_score(self.responsive_reason_rate, cfg["deliberate"]["reason"]) > 0:
                deliberate_parts.append(f"few back/popup-driven track changes ({reason_pct}% of plays)")
            if band_score(self.algorithmic_rate, cfg["deliberate"]["algorithmic"]) > 0:
                algo_caveat = f", {source_note}" if source_note else ""
                deliberate_parts.append(f"low algorithm-driven listening ({other_pct}% of listening time{algo_caveat})")
            deliberate_desc = (
                f"{cfg['deliberate']['label']} is at {show_level_as_text(self.archetype_scores['deliberate'])} - "
                + (f"Based on {join_with_and(deliberate_parts)}. " if deliberate_parts else "")
                + cfg["deliberate"]["description"]
            )
        else:
            deliberate_desc = (
                f"{cfg['deliberate']['label']} is at Low (0%) because we do not have your library or "
                f"playlist data. {cfg['deliberate']['description']}"
            )

        self.archetype_descriptions = {
            "receptive": receptive_desc,
            "responsive": (
                f"{cfg['responsive']['label']} is at {show_level_as_text(self.archetype_scores['responsive'])} - "
                + (f"Based on {join_with_and(responsive_parts)}. " if responsive_parts else "")
                + cfg["responsive"]["description"]
            ),
            "deliberate": deliberate_desc,
        }

    def _compute_top_tiles(self, df):
        self.top_artist = None
        self.top_song = None
        self.top_playlist = None
        if df.empty:
            return

        artist_counts = df.groupby("master_metadata_album_artist_name").size().sort_values(ascending=False)
        if not artist_counts.empty:
            top_artist_name = artist_counts.index[0]
            artist_rows = df[df["master_metadata_album_artist_name"] == top_artist_name]
            month_counts = artist_rows.groupby("month_key").size().sort_index()
            peak_month_key = month_counts.idxmax()
            peak_month_label = artist_rows[artist_rows["month_key"] == peak_month_key]["month_label"].iloc[0]
            self.top_artist = {
                "name": top_artist_name,
                "plays": int(artist_counts.iloc[0]),
                "peak_month": peak_month_label,
            }

        song_counts = df.groupby("spotify_track_uri").size().sort_values(ascending=False)
        if not song_counts.empty:
            top_uri = song_counts.index[0]
            song_rows = df[df["spotify_track_uri"] == top_uri]
            month_counts = song_rows.groupby("month_key").size().sort_index()
            peak_month_key = month_counts.idxmax()
            peak_month_label = song_rows[song_rows["month_key"] == peak_month_key]["month_label"].iloc[0]
            self.top_song = {
                "title": song_rows["master_metadata_track_name"].iloc[0],
                "artist": song_rows["master_metadata_album_artist_name"].iloc[0],
                "plays": int(song_counts.iloc[0]),
                "peak_month": peak_month_label,
            }

        self.top_playlist = _top_playlist_in(self.playlists, df)

    def _compute_monthly_grid(self, recent_df):
        """Per-month stats (total listening time, single busiest day, top
        song, top artist) for the same trailing window as the monthly bar
        chart (see BAR_CHART_MONTHS_SHOWN), one entry per month oldest-first.
        Months with no plays still get an entry so the grid page always shows
        a full window of cards."""
        months = _recent_month_keys(self.date_keys, BAR_CHART_MONTHS_SHOWN) if self.date_keys else []
        self.monthly_stats = []
        for year, month in months:
            month_key = f"{year:04d}-{month:02d}"
            month_label = datetime(year, month, 1).strftime("%b %Y")
            month_df = recent_df[recent_df["month_key"] == month_key] if not recent_df.empty else recent_df
            if month_df.empty:
                self.monthly_stats.append({"month_label": month_label})
                continue

            by_day = month_df.groupby("date_key")["minutes_rounded"].sum()
            peak_date_key = by_day.idxmax()
            peak_day = {
                "label": datetime.strptime(peak_date_key, "%Y-%m-%d").strftime("%A %-d %b %y"),
                "minutes": int(by_day.max()),
            }

            top_artist = None
            artist_counts = month_df.groupby("master_metadata_album_artist_name").size().sort_values(ascending=False)
            if not artist_counts.empty:
                top_artist = {"name": artist_counts.index[0], "plays": int(artist_counts.iloc[0])}

            top_song = None
            song_counts = month_df.groupby("spotify_track_uri").size().sort_values(ascending=False)
            if not song_counts.empty:
                top_uri = song_counts.index[0]
                song_row = month_df[month_df["spotify_track_uri"] == top_uri].iloc[0]
                top_song = {
                    "title": song_row["master_metadata_track_name"],
                    "artist": song_row["master_metadata_album_artist_name"],
                    "plays": int(song_counts.iloc[0]),
                }

            top_playlist = _top_playlist_in(self.playlists, month_df)

            # Library/playlist/other minute split for this month, feeding the
            # small source-breakdown bar at the bottom of the month's card;
            # only meaningful (and only shown) when the donor gave library or
            # playlist data at all, same gating as the dashboard page's
            # breakdown bar.
            source_minutes = None
            if self.has_any_library_data:
                source_totals = month_df.groupby("source")["minutes_rounded"].sum()
                source_minutes = {
                    "library": int(source_totals.get("library", 0)),
                    "playlist": int(source_totals.get("playlist", 0)),
                    "other": int(source_totals.get("other", 0)),
                }

            self.monthly_stats.append({
                "month_label": month_label,
                "total_minutes": int(month_df["minutes_rounded"].sum()),
                "peak_day": peak_day,
                "top_song": top_song,
                "top_artist": top_artist,
                "top_playlist": top_playlist,
                "source_minutes": source_minutes,
            })

        # Flag the single month that carries each year-wide superlative, so
        # the grid page can pick these out in CAPTION_GREEN: the month with
        # the most total listening time, the single busiest day, the month
        # whose top artist was played most often, the month whose top song
        # was played most often, and the month whose top playlist was played
        # most often (each compared across all months in the grid, not
        # per-card).
        complete = [(i, m) for i, m in enumerate(self.monthly_stats) if "total_minutes" in m]
        if complete:
            top_total_idx = max(complete, key=lambda im: im[1]["total_minutes"])[0]
            self.monthly_stats[top_total_idx]["is_top_total"] = True

            top_peak_day_idx = max(complete, key=lambda im: im[1]["peak_day"]["minutes"])[0]
            self.monthly_stats[top_peak_day_idx]["is_top_peak_day"] = True

            artist_candidates = [(i, m) for i, m in complete if m["top_artist"]]
            if artist_candidates:
                top_artist_idx = max(artist_candidates, key=lambda im: im[1]["top_artist"]["plays"])[0]
                self.monthly_stats[top_artist_idx]["is_top_artist"] = True

            song_candidates = [(i, m) for i, m in complete if m["top_song"]]
            if song_candidates:
                top_song_idx = max(song_candidates, key=lambda im: im[1]["top_song"]["plays"])[0]
                self.monthly_stats[top_song_idx]["is_top_song"] = True

            playlist_candidates = [(i, m) for i, m in complete if m["top_playlist"]]
            if playlist_candidates:
                top_playlist_idx = max(playlist_candidates, key=lambda im: im[1]["top_playlist"]["plays"])[0]
                self.monthly_stats[top_playlist_idx]["is_top_playlist"] = True


def load_all_donors(data_dir: Path):
    donors = []
    for zip_path in sorted(data_dir.glob("donation_*.zip")):
        participant_code = participant_code_from_filename(zip_path)
        raw_streaming, library, playlists = load_donor_raw(zip_path)
        streaming = build_streaming_frame(raw_streaming)
        donors.append(DonorStats(participant_code, streaming, library, playlists))
        # MDAP-TEST donors also get a streaming-only variant (library/playlist
        # data dropped) so the "no library or playlist data" rendering path
        # can be checked iteratively without needing a real donor missing
        # that data.
        if "MDAP-TEST" in participant_code:
            donors.append(DonorStats(
                f"{participant_code}-streaming-only", streaming,
                {"tracks": []}, {"playlists": []},
            ))
    return donors


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------

def style_axes(ax):
    ax.set_facecolor(SURFACE)
    ax.tick_params(colors=INK_SECONDARY)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRIDLINE)
    ax.spines["bottom"].set_color(GRIDLINE)
    ax.grid(axis="y", color=GRIDLINE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


def draw_grey_box(ax):
    ax.axis("off")
    ax.set_facecolor(SURFACE)


FOOTER_THANKS_TEXT = (
    "Thank you for your donating your data. This project has human research ethics approval from The University of Melbourne. Project ID: 35042."
)


def draw_footer(ax, participant_code):
    draw_grey_box(ax)
    ax.text(0.5, 0.62, f"{FOOTER_THANKS_TEXT} Participant code: {participant_code}", ha="center", va="center", fontsize=7,
            color=INK_SECONDARY, transform=ax.transAxes, linespacing=1.3)

def draw_section_heading(ax, text):
    ax.axis("off")
    ax.text(0.5, 0.5, text, ha="center", va="center", color=INK_PRIMARY, fontsize=13,
            fontweight="bold", fontfamily="Metropolis", transform=ax.transAxes)


def wrap(text, width, max_lines):
    lines = []
    for paragraph in text.split("\n\n"):
        lines.extend(textwrap.wrap(paragraph, width=width) or [""])
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip() + "…"
    return "\n".join(lines)


def draw_tile(ax, label, value, subtitle_line=None, caption=None):
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor=SURFACE, edgecolor=GRIDLINE, linewidth=1))
    ax.text(0.5, 0.86, label, ha="center", va="center", fontsize=8.5, color=INK_SECONDARY, fontweight="medium",
            transform=ax.transAxes)
    ax.text(0.5, 0.56, wrap(value, 18, 2), ha="center", va="center", fontsize=13, color=INK_PRIMARY,
            fontweight="bold", transform=ax.transAxes, linespacing=.75)
    if subtitle_line:
        ax.text(0.5, 0.32, wrap(subtitle_line, 24, 1), ha="center", va="center", fontsize=8,
                color=INK_SECONDARY, transform=ax.transAxes)
    if caption:
        ax.text(0.5, 0.14, wrap(caption, 26, 2), ha="center", va="center", fontsize=8,
                color=CAPTION_GREEN, transform=ax.transAxes, linespacing=.75)


def draw_no_data_message(ax, message):
    ax.axis("off")
    ax.text(0.5, 0.5, message, ha="center", va="center", color=INK_SECONDARY, fontsize=9,
            transform=ax.transAxes, wrap=True)


def draw_month_stat_card(ax, stats):
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor=SURFACE, edgecolor=GRIDLINE, linewidth=1))
    ax.text(0.5, 0.94, stats["month_label"], ha="center", va="top", fontsize=10.5, fontweight="bold",
            color=INK_PRIMARY, fontfamily="Metropolis", transform=ax.transAxes)

    if "total_minutes" not in stats:
        ax.text(0.5, 0.5, "No listening data\nthis month", ha="center", va="center", fontsize=8.5,
                color=INK_SECONDARY, transform=ax.transAxes, linespacing=1.6)
        return

    x = 0.09
    peak_day = stats["peak_day"]
    top_song = stats["top_song"]
    top_artist = stats["top_artist"]
    top_playlist = stats["top_playlist"]

    # Year-wide superlatives (see _compute_monthly_grid) render in
    # CAPTION_GREEN instead of INK_PRIMARY so the single standout month for
    # each stat reads at a glance across the whole grid page.
    total_color = CAPTION_GREEN if stats.get("is_top_total") else INK_PRIMARY
    peak_day_color = CAPTION_GREEN if stats.get("is_top_peak_day") else INK_PRIMARY
    song_color = CAPTION_GREEN if stats.get("is_top_song") else INK_PRIMARY
    artist_color = CAPTION_GREEN if stats.get("is_top_artist") else INK_PRIMARY
    playlist_color = CAPTION_GREEN if stats.get("is_top_playlist") else INK_PRIMARY

    # Five stat blocks now share the card's vertical space (see TOP PLAYLIST
    # below), so the rhythm is tighter than a 4-block card would need:
    # 0.055 between a block's own label/value/subtext lines, 0.065 between
    # one block's last line and the next block's label.
    ax.text(x, 0.86, "TOTAL LISTENING TIME", ha="left", va="top", fontsize=6, color=INK_SECONDARY,
            fontweight="medium", transform=ax.transAxes)
    ax.text(x, 0.805, format_minutes(stats["total_minutes"]), ha="left", va="top", fontsize=8.5,
            color=total_color, fontweight="bold", transform=ax.transAxes)

    ax.text(x, 0.74, "HIGHEST DAY", ha="left", va="top", fontsize=6, color=INK_SECONDARY,
            fontweight="medium", transform=ax.transAxes)
    ax.text(x, 0.685, wrap(peak_day["label"], 24, 1), ha="left", va="top", fontsize=8.5,
            color=peak_day_color, fontweight="bold", transform=ax.transAxes)
    ax.text(x, 0.63, f"{format_minutes(peak_day['minutes'])} that day", ha="left", va="top", fontsize=7,
            color=INK_SECONDARY, transform=ax.transAxes)

    ax.text(x, 0.565, "TOP SONG", ha="left", va="top", fontsize=6, color=INK_SECONDARY,
            fontweight="medium", transform=ax.transAxes)
    if top_song:
        ax.text(x, 0.51, wrap(top_song["title"], 24, 1), ha="left", va="top", fontsize=8.5,
                color=song_color, fontweight="bold", transform=ax.transAxes)
        ax.text(x, 0.455, wrap(f"by {top_song['artist']}", 24, 1), ha="left", va="top", fontsize=7,
                color=INK_SECONDARY, transform=ax.transAxes)
    else:
        ax.text(x, 0.51, "—", ha="left", va="top", fontsize=8.5, color=INK_PRIMARY, transform=ax.transAxes)

    ax.text(x, 0.39, "TOP ARTIST", ha="left", va="top", fontsize=6, color=INK_SECONDARY,
            fontweight="medium", transform=ax.transAxes)
    ax.text(x, 0.335, wrap(top_artist["name"], 24, 1) if top_artist else "—", ha="left", va="top", fontsize=8.5,
            color=artist_color if top_artist else INK_PRIMARY, fontweight="bold", transform=ax.transAxes)

    # No label at all when the donor has no playlist data for this month
    # (rather than a "TOP PLAYLIST" / "—" pair) - left as blank space.
    if top_playlist:
        ax.text(x, 0.27, "TOP PLAYLIST", ha="left", va="top", fontsize=6, color=INK_SECONDARY,
                fontweight="medium", transform=ax.transAxes)
        ax.text(x, 0.215, wrap(top_playlist["name"], 24, 1), ha="left", va="top", fontsize=8.5,
                color=playlist_color, fontweight="bold", transform=ax.transAxes)
        # Held further above the card's bottom edge (0.16 vs. the other
        # sections' ~0.055 value-to-subtext gap) so descenders clear the card
        # border below - this is the last line in the card.
        ax.text(x, 0.16, f"{format_playlist_duration(top_playlist['minutes'])} listened", ha="left", va="top",
                fontsize=7, color=INK_SECONDARY, transform=ax.transAxes)

    if stats["source_minutes"]:
        draw_month_source_bar(ax, stats["source_minutes"])


# Left/right margin (matching draw_month_stat_card's own text margin x=0.09)
# and vertical band the source bar sits in, low enough in the card to clear
# the "top playlist" block's last line above it (see draw_month_stat_card).
MONTH_SOURCE_BAR_MARGIN = 0.09
MONTH_SOURCE_BAR_Y = 0.025
MONTH_SOURCE_BAR_HEIGHT = 0.055


def draw_month_source_bar(ax, source_minutes):
    """Small horizontal stacked bar at the bottom of a month card, showing
    that month's library/playlist/other listening-time split. Reuses the
    dashboard page's library_playlist_other_bar_chart colours so the two
    pages read as one palette; see draw_source_legend for what the colours
    mean (drawn once at the top of the grid page rather than per card)."""
    total = sum(source_minutes.values())
    if total <= 0:
        return
    bar_ax = ax.inset_axes(
        [MONTH_SOURCE_BAR_MARGIN, MONTH_SOURCE_BAR_Y, 1 - 2 * MONTH_SOURCE_BAR_MARGIN, MONTH_SOURCE_BAR_HEIGHT],
        transform=ax.transAxes)
    bar_ax.axis("off")
    bar_ax.set_facecolor("none")
    left = 0
    for key, color in (
        ("library", LIBRARY_PLAYLIST_COLOR),
        ("playlist", PLAYLIST_COLOR),
        ("other", ALGORITHM_OTHER_COLOR),
    ):
        minutes = source_minutes[key]
        if minutes <= 0:
            continue
        bar_ax.barh(0, minutes, left=left, height=1, color=color, alpha=0.8,
                    edgecolor=SURFACE, linewidth=1)
        left += minutes
    bar_ax.set_xlim(0, total)
    bar_ax.set_ylim(-0.5, 0.5)


def draw_source_legend(ax):
    """Shared colour key for draw_month_source_bar, drawn once at the top of
    the grid page instead of repeating text on every card."""
    draw_grey_box(ax)
    handles = [
        Patch(facecolor=LIBRARY_PLAYLIST_COLOR, alpha=0.8, label="Library"),
        Patch(facecolor=PLAYLIST_COLOR, alpha=0.8, label="Playlists"),
        Patch(facecolor=ALGORITHM_OTHER_COLOR, alpha=0.8, label="Algorithm & Other"),
    ]
    ax.legend(handles=handles, loc="center", ncol=3, frameon=False, fontsize=8,
              labelcolor=INK_SECONDARY, handlelength=1.2, handleheight=1.2, columnspacing=1.5)


def heatmap_chart(fig, cell_ax, cbar_ax, matrix, row_labels, col_labels, color_hex, title):
    cmap = LinearSegmentedColormap.from_list("seq", [SURFACE, color_hex])
    vmax = matrix.max() if matrix.max() > 0 else 1
    im = cell_ax.imshow(matrix, cmap=cmap, vmin=0, vmax=vmax, aspect="auto")

    cell_ax.set_xticks(range(len(col_labels)))
    cell_ax.set_xticklabels(col_labels, color=INK_SECONDARY, fontsize=8)
    cell_ax.set_yticks(range(len(row_labels)))
    cell_ax.set_yticklabels(row_labels, color=INK_SECONDARY, fontsize=8)
    cell_ax.tick_params(length=0)
    for spine in cell_ax.spines.values():
        spine.set_visible(False)
    # 2px surface-colour gap between cells, drawn as minor gridlines rather
    # than a border on each cell (see dataviz skill: "surface gap" spacer).
    cell_ax.set_xticks(np.arange(-0.5, len(col_labels), 1), minor=True)
    cell_ax.set_yticks(np.arange(-0.5, len(row_labels), 1), minor=True)
    cell_ax.grid(which="minor", color=SURFACE, linewidth=2)
    cell_ax.tick_params(which="minor", length=0)
    cell_ax.set_title(title, color=INK_PRIMARY, fontsize=10, pad=8, fontfamily="Metropolis")

    cbar = fig.colorbar(im, cax=cbar_ax)
    cbar.set_ticks([0, vmax])
    cbar.set_ticklabels(["Low", "High"])
    cbar.ax.tick_params(colors=INK_SECONDARY, labelsize=7, length=0)
    cbar.outline.set_visible(False)


def radar_chart(ax, labels, values, max_value=100):
    n = len(labels)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    plot_values = values + values[:1]
    plot_angles = angles + angles[:1]
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.plot(plot_angles, plot_values, color=RADAR_COLOR, linewidth=2)
    ax.fill(plot_angles, plot_values, color=RADAR_COLOR, alpha=0.25)
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, color=INK_PRIMARY, fontsize=10)
    ax.set_ylim(0, max_value)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["Low", "", "", "High"], color=INK_SECONDARY, fontsize=7)
    ax.set_facecolor(SURFACE)
    ax.spines["polar"].set_color(GRIDLINE)
    ax.grid(color=GRIDLINE, linewidth=0.6)


# Number of trailing months shown in the monthly listening bar chart and the
# monthly stats grid page; both read the same trailing window.
BAR_CHART_MONTHS_SHOWN = 12

# Number of grid columns on the monthly stats grid page; rows are however
# many are needed to fit the trailing window (see build_monthly_grid_page).
MONTHLY_GRID_COLUMNS = 4


def _recent_month_keys(date_keys, months_shown):
    """Trailing (year, month) tuples ending at the last day in date_keys,
    clipped to not run earlier than the first day actually in the data."""
    last = datetime.strptime(date_keys[-1], "%Y-%m-%d")
    first = datetime.strptime(date_keys[0], "%Y-%m-%d")
    months = []
    y, m = last.year, last.month
    for _ in range(months_shown):
        if (y, m) < (first.year, first.month):
            break
        months.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    months.reverse()
    return months




def _recent_month_totals(date_keys, by_date_library, by_date_other, months_shown):
    """Trailing per-month (library, other) minute totals, aggregated from the
    same daily date_keys/by_date_* arrays as calendar_heatmap_chart and
    clipped by the same rule (see _recent_month_keys)."""
    months = _recent_month_keys(date_keys, months_shown)
    periods = pd.to_datetime(date_keys).to_period("M")
    totals = pd.DataFrame({"period": periods, "library": by_date_library, "other": by_date_other}) \
        .groupby("period")[["library", "other"]].sum()

    labels, library_minutes, other_minutes = [], [], []
    for year, month in months:
        period = pd.Period(f"{year:04d}-{month:02d}")
        labels.append(datetime(year, month, 1).strftime("%b %Y"))
        row = totals.loc[period] if period in totals.index else None
        library_minutes.append(row["library"] if row is not None else 0)
        other_minutes.append(row["other"] if row is not None else 0)
    return labels, library_minutes, other_minutes


def monthly_listening_bar_chart(ax, date_keys, by_date_library, by_date_other, has_library, has_playlist,
                                 months_shown=BAR_CHART_MONTHS_SHOWN):
    labels, library_minutes, other_minutes = _recent_month_totals(
        date_keys, by_date_library, by_date_other, months_shown)
    library_hours = np.array(library_minutes) / 60
    other_hours = np.array(other_minutes) / 60

    x = np.arange(len(labels))
    # Label reflects which of library/playlists the donor actually gave (see
    # combined_library_uris: this series already merges both sources), so a
    # donor with only one of the two isn't shown a legend entry for data they
    # never donated.
    if has_library and has_playlist:
        library_label = "Library + playlists"
    elif has_library:
        library_label = "Library"
    elif has_playlist:
        library_label = "Playlists"
    else:
        library_label = None

    # edgecolor=SURFACE draws the 2px surface-colour gap between the two
    # stacked segments (see dataviz skill: "surface gap" spacer) rather than
    # a border, which would add data-weight ink that isn't data.
    ax.bar(x, library_hours, color=LIBRARY_PLAYLIST_COLOR, alpha=0.6, edgecolor=SURFACE, linewidth=1.5,
           label=library_label)
    ax.bar(x, other_hours, bottom=library_hours, color=ALGORITHM_OTHER_COLOR, alpha=0.8, edgecolor=SURFACE,
           linewidth=1.5, label="Algorithm & Other" if library_label else None)

    # Total-listening-time label above each bar. Values wear a text token
    # (INK_PRIMARY), not either segment's series colour, since the label
    # names the combined total rather than one series (see dataviz skill:
    # direct labels stay in text ink).
    stack_top = library_hours + other_hours
    for xi, top, lib_m, oth_m in zip(x, stack_top, library_minutes, other_minutes):
        total_minutes = lib_m + oth_m
        if total_minutes <= 0:
            continue
        ax.text(xi, top, format_minutes(total_minutes), ha="center", va="bottom", fontsize=6.5,
                color=INK_PRIMARY, fontweight="medium")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, color=INK_SECONDARY, fontsize=7.5, rotation=45, ha="right")
    ax.set_title("Your monthly listening patterns", color=INK_PRIMARY, fontsize=9, pad=12, fontfamily="Metropolis")
    ax.set_ylabel("Monthly listening time in hours", color=INK_SECONDARY, fontsize=8)
    ax.tick_params(axis="both", length=0, labelsize=7.5, labelcolor=INK_SECONDARY)
    ax.grid(axis="y", color=GRIDLINE, linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    # Headroom for the total labels above the tallest bar, which the default
    # 5%-margin autoscale isn't tall enough to clear.
    max_top = stack_top.max() if len(stack_top) else 0
    if max_top > 0:
        ax.set_ylim(0, max_top * 1.18)


def _recent_totals_by_source(date_keys, by_date_library, by_date_playlist, by_date_other, months_shown):
    """Trailing-window total hours per source (library/playlist/other),
    aggregated from the same daily date_keys/by_date_* arrays and clipped by
    the same rule as _recent_month_totals (see _recent_month_keys)."""
    months = _recent_month_keys(date_keys, months_shown)
    if not months:
        return 0.0, 0.0, 0.0
    periods = pd.to_datetime(date_keys).to_period("M")
    totals = pd.DataFrame({
        "period": periods, "library": by_date_library, "playlist": by_date_playlist, "other": by_date_other,
    }).groupby("period")[["library", "playlist", "other"]].sum()
    month_index = pd.PeriodIndex([pd.Period(f"{y:04d}-{m:02d}") for y, m in months])
    matched = totals.reindex(month_index, fill_value=0)
    minutes_to_hours = 60
    return (matched["library"].sum() / minutes_to_hours,
            matched["playlist"].sum() / minutes_to_hours,
            matched["other"].sum() / minutes_to_hours)


def library_playlist_other_bar_chart(ax, library_hours, playlist_hours, other_hours, months_shown):
    """Single horizontal stacked bar showing the trailing-N-month split
    across library, playlists, and algorithm/other listening, where N is the
    actual number of months of data donated (up to BAR_CHART_MONTHS_SHOWN).
    Reuses the monthly bar chart's LIBRARY_PLAYLIST_COLOR/ALGORITHM_OTHER_COLOR
    for its library/other segments so the two charts read as one palette;
    PLAYLIST_COLOR is this chart's only new hue."""
    ax.set_facecolor(SURFACE)
    total_hours = library_hours + playlist_hours + other_hours
    if total_hours <= 0:
        draw_no_data_message(ax, "No listening time donated")
        return

    segments = [
        ("Library", library_hours, LIBRARY_PLAYLIST_COLOR),
        ("Playlists", playlist_hours, PLAYLIST_COLOR),
        ("Algorithm & Other", other_hours, ALGORITHM_OTHER_COLOR),
    ]

    left = 0.0
    for label, hours, color in segments:
        if hours <= 0:
            continue
        # edgecolor=SURFACE draws the same 2px surface-colour gap between
        # segments as the bar chart's stacked bars (see dataviz skill:
        # "surface gap" spacer).
        ax.barh(0, hours, left=left, height=0.6, color=color, alpha=0.8,
                 edgecolor=SURFACE, linewidth=1.5, label=label)
        pct = hours / total_hours * 100
        # Selective direct labels (see dataviz skill): only segments wide
        # enough for the "NN%" text to actually fit get one.
        if pct >= 6:
            ax.text(left + hours / 2, 0, f"{pct:.0f}%", ha="center", va="center",
                     color=SURFACE, fontsize=8, fontweight="bold")
        # Segment name, placed just below the bar.
        ax.text(left + hours / 2, -0.55, label, ha="center", va="top",
                 color=INK_SECONDARY, fontsize=7)
        left += hours

    ax.set_xlim(0, total_hours)
    # Asymmetric ylim (vs. the +/-0.5 the 0.6-height bar would centre on)
    # keeps the bar's clearance to its title above unchanged while padding
    # out extra blank space below it, so the bar sits higher in its row.
    # Shifted 10% (of the 1.8-unit range) further up from that baseline to
    # leave room for the segment-name labels below the bar.
    ax.set_ylim(-1.48, 0.32)
    ax.set_yticks([])
    ax.set_xticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    month_word = "month" if months_shown == 1 else "months"
    ax.set_title(f"Most recent {months_shown} {month_word} breakdown of listening time by source",
                 color=INK_PRIMARY, fontsize=9, pad=12, fontfamily="Metropolis")


# Fraction of the card's own height it's shifted up by within its GridSpec
# cell, so the card sits higher on the page than its cell's plain top-aligned
# position (leaving the freed space below, ahead of the footer).
CARD_RAISE_FRACTION = 0.15


# Draws one "trading card" for an archetype: image on top, label/score/short
# text/description below, inside a coloured border keyed to the archetype's
# accent colour. card_spec is this card's cell within the 1x3 GridSpec row.
def draw_archetype_card(fig, card_spec, key, donor):
    cfg = ARCHETYPE_CONFIG[key]
    is_strongest = key == donor.strongest_archetype

    inner = card_spec.subgridspec(2, 1, height_ratios=[0.55, 0.45], hspace=0.05)

    img_ax = fig.add_subplot(inner[0])
    img_ax.axis("off")
    img_ax.set_facecolor("none")
    image_path = ARCHETYPE_PROFILE_IMAGES[key]
    if image_path.exists():
        image = plt.imread(image_path)
        img_ax.imshow(image, aspect="equal")

    text_ax = fig.add_subplot(inner[1])
    text_ax.axis("off")
    text_ax.set_facecolor("none")

    # Raise the whole card (image + text) by CARD_RAISE_FRACTION of its own
    # height. Axes text isn't clipped to its axes' box, so the extra room
    # this opens up below the card is free for the added short_text
    # paragraph without touching the surrounding GridSpec rows.
    img_pos = img_ax.get_position()
    text_pos = text_ax.get_position()
    card_height = img_pos.y1 - text_pos.y0
    raise_by = CARD_RAISE_FRACTION * card_height
    img_ax.set_position([img_pos.x0, img_pos.y0 + raise_by, img_pos.width, img_pos.height])
    text_ax.set_position([text_pos.x0, text_pos.y0 + raise_by, text_pos.width, text_pos.height])

    # No explicit fontfamily here (unlike other Metropolis headings): Metropolis
    # has no glyph for the star, so this relies on the rcParams font.family
    # fallback chain to pick it up from DejaVu Sans per-glyph.
    label_text = cfg["short_label"].upper() + ("  ★" if is_strongest else "")
    text_ax.text(0.5, 1, label_text, ha="center", va="top", fontsize=9.5, fontweight="bold",
                 color=INK_PRIMARY, transform=text_ax.transAxes)
    # Short, second-person summary sits as its own paragraph above the
    # longer analytical description. Bold INK_PRIMARY (rather than the
    # archetype accent) keeps it readable: the receptive accent in
    # particular is too low-contrast against the page for body-sized text.
    # Pulled up close under the heading now that the score percentage
    # above it has been removed.
    text_ax.text(0, 0.85, wrap(cfg["short_text"], 40, 5), ha="left", va="top",
                 fontsize=8, color=INK_PRIMARY, fontweight="bold", transform=text_ax.transAxes, linespacing=1)
    # width/max_lines are tuned against this card's actual text_ax size (see
    # draw_archetype_card geometry) so a 9-line description just fits above
    # the card's bottom edge; longer descriptions truncate with an ellipsis.
    text_ax.text(0, 0.4, wrap(donor.archetype_descriptions[key], 40, 14), ha="left", va="top",
                 fontsize=8, color=INK_SECONDARY, transform=text_ax.transAxes, linespacing=1)


# ---------------------------------------------------------------------------
# Page builders
# ---------------------------------------------------------------------------

A4_PORTRAIT = (8.27, 11.69)


def build_dashboard_page(pdf: PdfPages, donor: DonorStats):
    fig = plt.figure(figsize=A4_PORTRAIT, facecolor=SURFACE)
    # Row 4 is a spacer giving the monthly bar chart's x-axis labels (row 3)
    # clearance above the day/time heatmap's title (row 5).
    gs = GridSpec(7, 1, figure=fig, height_ratios=[0.35, 1.3, 0.65, 3.55, 0.35, 2.7, 0.35],
                  hspace=0.6, top=0.94, bottom=0.03, left=0.06, right=0.94)

    draw_grey_box(fig.add_subplot(gs[0]))

    tile_gs = gs[1].subgridspec(1, 3, wspace=0.15)
    artist_ax, playlist_ax, song_ax = (fig.add_subplot(tile_gs[i]) for i in range(3))

    if donor.top_artist:
        draw_tile(artist_ax, "Most played artist", donor.top_artist["name"],
                   caption=f"Most played in {donor.top_artist['peak_month']}")
    else:
        draw_no_data_message(artist_ax, "No data available.")

    if donor.top_song:
        draw_tile(song_ax, "Most played song", donor.top_song["title"],
                   subtitle_line=f"by {donor.top_song['artist']}",
                   caption=f"Most played in {donor.top_song['peak_month']}")
    else:
        draw_no_data_message(song_ax, "No data available.")

    if donor.top_playlist:
        draw_tile(playlist_ax, "Most played playlist", donor.top_playlist["name"],
                   caption=f"{format_playlist_duration(donor.top_playlist['minutes'])} of listening time")
    else:
        draw_no_data_message(playlist_ax, wrap("Your Spotify data gives a breakdown of your listening patterns",30,3))

    # Dodgy layout adjustment up slightly relative to the tiles above and the monthly chart
    # below, rather than reworking the surrounding GridSpec's row heights.
    TITLE_BREAKDOWN_Y_SHIFT = 0.02
    # Dodgy layout adjustment up to
    # close the gap between it and the title.
    BREAKDOWN_EXTRA_Y_SHIFT = 0.02
    heading_ax = fig.add_subplot(gs[2])
    draw_section_heading(heading_ax, "Your listening patterns by month")
    heading_pos = heading_ax.get_position()
    heading_ax.set_position([heading_pos.x0, heading_pos.y0 + TITLE_BREAKDOWN_Y_SHIFT,
                              heading_pos.width, heading_pos.height])

    # The breakdown bar only adds meaningful information when there's a
    # library/playlist split to show at all; without it, the monthly bar
    # chart keeps the whole row (its original, taller height) rather than
    # leaving a gap.
    if donor.has_any_library_data:
        # A single-row bar needs far less height than the donut it replaced,
        # so the split leans further towards the monthly chart below it.
        month_gs = gs[3].subgridspec(2, 1, height_ratios=[1.4, 2.4], hspace=0.15)
        breakdown_row_gs = month_gs[0].subgridspec(1, 3, width_ratios=[0.06, 0.88, 0.06])
        breakdown_ax = fig.add_subplot(breakdown_row_gs[0, 1])
        library_hours_12m, playlist_hours_12m, other_hours_12m = _recent_totals_by_source(
            donor.date_keys, donor.by_date_library_only, donor.by_date_playlist, donor.by_date_other,
            BAR_CHART_MONTHS_SHOWN)
        months_donated = len(_recent_month_keys(donor.date_keys, BAR_CHART_MONTHS_SHOWN))
        library_playlist_other_bar_chart(breakdown_ax, library_hours_12m, playlist_hours_12m, other_hours_12m,
                                          months_donated)
        breakdown_pos = breakdown_ax.get_position()
        breakdown_ax.set_position([breakdown_pos.x0,
                                    breakdown_pos.y0 + TITLE_BREAKDOWN_Y_SHIFT + BREAKDOWN_EXTRA_Y_SHIFT,
                                    breakdown_pos.width, breakdown_pos.height])
        bar_row_gs = month_gs[1].subgridspec(1, 3, width_ratios=[0.06, 0.88, 0.06])
    else:
        bar_row_gs = gs[3].subgridspec(1, 3, width_ratios=[0.06, 0.88, 0.06])
    bar_ax = fig.add_subplot(bar_row_gs[0, 1])
    monthly_listening_bar_chart(bar_ax, donor.date_keys, donor.by_date_library, donor.by_date_other,
                                 donor.has_library, donor.has_playlist)

    # Unlike the timeseries chart above, this only needs streaming history
    # (no library/playlist split), so it's gated on streaming data alone.
    if not donor.streaming.empty:
        # Same outer [0.06, 0.88, 0.06] split as timeseries_gs above (left
        # margin, content, right margin) so the two charts' left/right edges
        # line up; the content column is then split again for the colorbar.
        heatmap_row_gs = gs[5].subgridspec(1, 3, width_ratios=[0.06, 0.88, 0.06])
        heatmap_gs = heatmap_row_gs[0, 1].subgridspec(1, 2, width_ratios=[0.92, 0.05], wspace=0.15)
        heatmap_ax = fig.add_subplot(heatmap_gs[0, 0])
        cbar_ax = fig.add_subplot(heatmap_gs[0, 1])
        heatmap_chart(fig, heatmap_ax, cbar_ax, donor.heatmap_hours, TIME_SEGMENT_LABELS, DAY_LABELS,
                      SPOTIFY_GREEN, "Your listening patterns by day of week and time of day")
    else:
        draw_no_data_message(fig.add_subplot(gs[5]),
                              "Time of day / day of week cannot be calculated without streaming history data.")

    draw_footer(fig.add_subplot(gs[6]), donor.participant_code)

    fig.suptitle(f"YOUR SPOTIFY WRAPPED UNPACKED", color=INK_PRIMARY, fontsize=20,
                 fontweight="bold", fontfamily="Metropolis", y=.9)
    pdf.savefig(fig, facecolor=SURFACE)
    plt.close(fig)


def build_monthly_grid_page(pdf: PdfPages, donor: DonorStats):
    fig = plt.figure(figsize=A4_PORTRAIT, facecolor=SURFACE)
    # Row 1 (legend) only carries content when the donor gave library or
    # playlist data (see draw_month_source_bar's own gating); it's kept in
    # the layout either way, drawn blank otherwise, so the grid below doesn't
    # shift position between donors.
    gs = GridSpec(4, 1, figure=fig, height_ratios=[0.35, 0.3, 8.95, 0.35],
                  hspace=0.15, top=0.94, bottom=0.03, left=0.06, right=0.94)

    draw_grey_box(fig.add_subplot(gs[0]))

    legend_ax = fig.add_subplot(gs[1])
    if donor.has_any_library_data:
        draw_source_legend(legend_ax)
    else:
        draw_grey_box(legend_ax)

    if donor.monthly_stats:
        cols = MONTHLY_GRID_COLUMNS
        rows = -(-len(donor.monthly_stats) // cols)  # ceil
        month_gs = gs[2].subgridspec(rows, cols, hspace=0.12, wspace=0.15)
        for i, stats in enumerate(donor.monthly_stats):
            r, c = divmod(i, cols)
            draw_month_stat_card(fig.add_subplot(month_gs[r, c]), stats)
    else:
        draw_no_data_message(fig.add_subplot(gs[2]),
                              "Month-by-month highlights cannot be calculated without streaming history data.")

    draw_footer(fig.add_subplot(gs[3]), donor.participant_code)

    fig.suptitle("YOUR MONTH-BY-MONTH HIGHLIGHTS", color=INK_PRIMARY, fontsize=20,
                 fontweight="bold", fontfamily="Metropolis", y=.9)
    pdf.savefig(fig, facecolor=SURFACE)
    plt.close(fig)


RADAR_INTRO_TEXT = (
    "We have analysed your Spotify listening history data to draw a picture of the "
    "interactions with the algorithm. This includes how often you have skipped songs and "
    "used shuffle as well as how much of your listening experience is driven by Spotify’s "
    "recommendations or by the playlist and library features."
)


def draw_radar_intro_text(ax, text):
    ax.axis("off")
    ax.text(0, .9, wrap(text, 45, 60), ha="left", va="top", fontsize=8,
            color=INK_SECONDARY, transform=ax.transAxes, linespacing=1)


def build_poster_page(pdf: PdfPages, donor: DonorStats):
    fig = plt.figure(figsize=A4_PORTRAIT, facecolor=SURFACE)
    gs = GridSpec(4, 1, figure=fig, height_ratios=[0.35, 4.2, 5.5, 0.35],
                  hspace=0.3, top=0.94, bottom=0.03, left=0.06, right=0.94)

    #draw_grey_box(fig.add_subplot(gs[0]))

    radar_row_gs = gs[1].subgridspec(1, 2, width_ratios=[0.3, 0.7], wspace=0.05)
    draw_radar_intro_text(fig.add_subplot(radar_row_gs[0]), RADAR_INTRO_TEXT)
    radar_col_gs = radar_row_gs[1].subgridspec(2, 1, height_ratios=[0.2, 0.8], hspace=0)
    radar_ax = fig.add_subplot(radar_col_gs[1], projection="polar")
    radar_labels = [ARCHETYPE_CONFIG[key]["short_label"] for key in ARCHETYPE_ORDER]
    radar_values = [round(donor.archetype_scores[key] * 100) for key in ARCHETYPE_ORDER]
    radar_chart(radar_ax, radar_labels, radar_values)

    # Three archetype "cards" (image on top, label/score/description below)
    # laid out side by side across the page width.
    cards_gs = gs[2].subgridspec(1, 3, wspace=0.12)
    for col, key in enumerate(ARCHETYPE_ORDER):
        draw_archetype_card(fig, cards_gs[col], key, donor)

    draw_footer(fig.add_subplot(gs[3]), donor.participant_code)

    fig.suptitle("UNPACKING YOUR PLATFORM INTERACTION DATA", color=INK_PRIMARY,
                 fontsize=20, fontweight="bold", fontfamily="Metropolis", y=0.9)
    pdf.savefig(fig, facecolor=SURFACE)
    plt.close(fig)


def generate_donor_pdf(donor: DonorStats, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{donor.participant_code}_dashboard.pdf"
    with PdfPages(output_path) as pdf:
        build_dashboard_page(pdf, donor)
        build_monthly_grid_page(pdf, donor)
        build_poster_page(pdf, donor)
    return output_path


def main():
    donors = load_all_donors(DATA_DIR)
    print(f"Loaded {len(donors)} donors from {DATA_DIR}")
    for donor in donors:
        output_path = generate_donor_pdf(donor, OUTPUT_DIR)
        print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
