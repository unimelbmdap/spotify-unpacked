"""Per-donor statistics derived from a donation bundle.

Moved from explorations/code/GenerateInterviewerPDF.py; the maths is unchanged.
Archetype bands and weights come from constants.json (shared with the frontend
via src/lib/__tests__/reportConstants.spec.ts).
"""

from datetime import datetime

import numpy as np
import pandas as pd

from donation_reports.constants import (
    ARCHETYPE_BANDS,
    BAR_CHART_MONTHS_SHOWN,
    RESPONSIVE_REASON_END_VALUES,
    RESPONSIVE_REASON_START_VALUES,
    band_score,
)

DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Four fixed 6-hour buckets covering the day, in display (top-to-bottom) order.
# hour // 6 gives 0=12-6am, 1=6-12am, 2=12-6pm, 3=6pm-12am; the -1 % 4 rotates
# that so the row order below (Morning first) lines up.
TIME_SEGMENT_LABELS = ["Morning", "Afternoon", "Evening", "Night"]

# Ported from src/lib/archetypeConfig.ts. Bands are {min, max} over a 0-1 rate;
# a missing min/max defaults to 0/1. Tie-break order for the strongest

# Copy shown on the poster page. Bands and weights are merged in from
# constants.json below so the numbers have one source on the Python side.
ARCHETYPE_ORDER = ["receptive", "responsive", "deliberate"]

_ARCHETYPE_TEXT = {
    "receptive": {
        "label": "Receptiveness",
        "short_label": "Receptive",
        "short_text": "You usually trust Spotify to choose music for you. You're happy to listen to the songs, playlists, or artists it recommends, rather than deciding everything yourself.",
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
    },
}

ARCHETYPE_CONFIG = {
    key: {**_ARCHETYPE_TEXT[key], **ARCHETYPE_BANDS[key]} for key in ARCHETYPE_ORDER
}


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


def _recent_month_keys(date_keys, months_shown):
    """Trailing (year, month) tuples ending at the last day in date_keys,
    clipped to not run earlier than the first day actually in the data."""
    if not date_keys:
        return []
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
        # No plays in the window: every rate above is 0, which the inverted
        # deliberate bands would read as a perfect deliberate score. Report
        # nothing rather than something misleading. (Only reachable for
        # library-only / playlist-only donations or history that predates the
        # window; the web app requires streaming history so never hits this.)
        self.has_streaming = not recent_df.empty
        if not self.has_streaming:
            self.archetype_scores = {key: 0.0 for key in self.archetype_scores}

        best_score = max(self.archetype_scores.values()) if self.archetype_scores else 0
        self.strongest_archetype = next(
            key for key in ARCHETYPE_ORDER if self.archetype_scores.get(key) == best_score
        )

        self._compute_archetype_descriptions()
        self._compute_top_tiles(recent_df)
        self._compute_monthly_grid(recent_df)

    def _compute_archetype_descriptions(self):
        cfg = ARCHETYPE_CONFIG
        if not self.has_streaming:
            self.archetype_descriptions = {
                key: (
                    f"{cfg[key]['label']} cannot be assessed because no listening history "
                    f"falls inside the analysis window. {cfg[key]['description']}"
                )
                for key in ARCHETYPE_ORDER
            }
            return
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
            # A month can have streaming rows that all round down to 0
            # minutes (e.g. a single very-quick listen), which should read as
            # "no listening data" rather than a "0 min" total with a peak day
            # of 0 minutes.
            total_minutes = int(month_df["minutes_rounded"].sum()) if not month_df.empty else 0
            if total_minutes <= 0:
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
                "total_minutes": total_minutes,
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

