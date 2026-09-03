"""PDF rendering of a DonorStats: dashboard, month-by-month grid, archetype poster.

Moved from explorations/code/GenerateInterviewerPDF.py. Drawing code is
unchanged apart from: fonts and archetype images are optional (see fonts.py
and ARCHETYPE_PROFILE_IMAGE_NAMES), the footer carries the generator version,
and an empty analysis window renders a message instead of charts.
"""

import colorsys
import textwrap
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Patch

from donation_reports.constants import BAR_CHART_MONTHS_SHOWN
from donation_reports.fonts import heading_family
from donation_reports.stats import (
    ARCHETYPE_CONFIG,
    ARCHETYPE_ORDER,
    DAY_LABELS,
    TIME_SEGMENT_LABELS,
    DonorStats,
    _recent_month_keys,
)

matplotlib.use("Agg")


@dataclass(frozen=True)
class RenderContext:
    """Per-run rendering inputs that are not part of the donor's data."""

    version: int
    assets_dir: Path


NO_STREAMING_MESSAGE = (
    "No listening history falls inside the analysis window, so monthly listening "
    "patterns cannot be shown."
)

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
    "Thank you for donating your data. This project has human research ethics approval\n"
    "from The University of Melbourne. Project ID: 35042."
)


def draw_footer(ax, participant_code, version):
    draw_grey_box(ax)
    # Three lines: the ethics sentence alone overruns A4 width at a readable
    # size, and the code/version line is what an interviewer scans for.
    ax.text(0.5, 0.5, f"{FOOTER_THANKS_TEXT}\nParticipant code: {participant_code}  |  Report v{version}",
            ha="center", va="center", fontsize=8,
            color=INK_SECONDARY, transform=ax.transAxes, linespacing=1.25)

def draw_section_heading(ax, text):
    ax.axis("off")
    ax.text(0.5, 0.5, text, ha="center", va="center", color=INK_PRIMARY, fontsize=13,
            fontweight="bold", fontfamily=heading_family(), transform=ax.transAxes)


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
            color=INK_PRIMARY, fontfamily=heading_family(), transform=ax.transAxes)

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
    cell_ax.set_title(title, color=INK_PRIMARY, fontsize=10, pad=8, fontfamily=heading_family())

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
# Number of grid columns on the monthly stats grid page; rows are however
# many are needed to fit the trailing window (see build_monthly_grid_page).
MONTHLY_GRID_COLUMNS = 4


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
    ax.set_title("Your monthly listening patterns", color=INK_PRIMARY, fontsize=9, pad=12, fontfamily=heading_family())
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
                 color=INK_PRIMARY, fontsize=9, pad=12, fontfamily=heading_family())


# Fraction of the card's own height it's shifted up by within its GridSpec
# cell, so the card sits higher on the page than its cell's plain top-aligned
# position (leaving the freed space below, ahead of the footer).
CARD_RAISE_FRACTION = 0.15


# Draws one "trading card" for an archetype: image on top, label/score/short
# text/description below, inside a coloured border keyed to the archetype's
# accent colour. card_spec is this card's cell within the 1x3 GridSpec row.
# Gap between the bottom of the summary paragraph and the top of the
# description, as a fraction of the card's text axes height.
SUMMARY_TO_DESCRIPTION_GAP = 0.05


def draw_archetype_card(fig, card_spec, key, donor, ctx: RenderContext):
    cfg = ARCHETYPE_CONFIG[key]
    is_strongest = key == donor.strongest_archetype

    inner = card_spec.subgridspec(2, 1, height_ratios=[0.5, 0.5], hspace=0.05)

    img_ax = fig.add_subplot(inner[0])
    img_ax.axis("off")
    img_ax.set_facecolor("none")
    image_path = ctx.assets_dir / "images" / f"profile_{key}.jpg"
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

    # No explicit fontfamily here (unlike other Poppins headings): Poppins
    # has no glyph for the star, so this relies on the rcParams font.family
    # fallback chain to pick it up from DejaVu Sans per-glyph.
    label_text = cfg["short_label"].upper() + ("  ★" if is_strongest else "")
    text_ax.text(0.5, 1, label_text, ha="center", va="top", fontsize=10, fontweight="bold",
                 color=INK_PRIMARY, transform=text_ax.transAxes)
    # Short, second-person summary sits as its own paragraph above the
    # longer analytical description. Bold INK_PRIMARY (rather than the
    # archetype accent) keeps it readable: the receptive accent in
    # particular is too low-contrast against the page for body-sized text.
    # Pulled up close under the heading now that the score percentage
    # above it has been removed.
    summary = text_ax.text(0, 0.85, wrap(cfg["short_text"], 35, 6), ha="left", va="top",
                           fontsize=9, color=INK_PRIMARY, fontweight="bold",
                           transform=text_ax.transAxes, linespacing=1.0)
    # The summary runs to four, five or six lines depending on the archetype,
    # so the description is anchored a fixed gap below the summary's measured
    # extent rather than at a fixed y. Measuring needs a renderer; Agg's is
    # available before the figure is saved.
    renderer = fig.canvas.get_renderer()
    summary_bottom = text_ax.transAxes.inverted().transform(
        (0, summary.get_window_extent(renderer=renderer).y0)
    )[1]
    description_top = summary_bottom - SUMMARY_TO_DESCRIPTION_GAP
    # width/max_lines are tuned against this card's actual text_ax size (see
    # draw_archetype_card geometry) so the longest description clears the
    # footer; longer descriptions truncate with an ellipsis.
    text_ax.text(0, description_top, wrap(donor.archetype_descriptions[key], 40, 14),
                 ha="left", va="top", fontsize=8.5, color=INK_SECONDARY,
                 transform=text_ax.transAxes, linespacing=1.0)


# ---------------------------------------------------------------------------
# Page builders
# ---------------------------------------------------------------------------

A4_PORTRAIT = (8.27, 11.69)


def build_dashboard_page(pdf: PdfPages, donor: DonorStats, ctx: RenderContext):
    fig = plt.figure(figsize=A4_PORTRAIT, facecolor=SURFACE)
    # Row 4 is a spacer giving the monthly bar chart's x-axis labels (row 3)
    # clearance above the day/time heatmap's title (row 5).
    gs = GridSpec(7, 1, figure=fig, height_ratios=[0.35, 1.3, 0.65, 3.55, 0.35, 2.55, 0.5],
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
    if not donor.date_keys:
        # Library-only or playlist-only donations, or streaming history that
        # falls entirely outside the analysis window: nothing to chart.
        bar_row_gs = None
        draw_no_data_message(fig.add_subplot(gs[3]), wrap(NO_STREAMING_MESSAGE, 70, 3))
    elif donor.has_any_library_data:
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
    if bar_row_gs is not None:
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

    draw_footer(fig.add_subplot(gs[6]), donor.participant_code, ctx.version)

    fig.suptitle("YOUR SPOTIFY WRAPPED UNPACKED", color=INK_PRIMARY, fontsize=20,
                 fontweight="bold", fontfamily=heading_family(), y=.9)
    pdf.savefig(fig, facecolor=SURFACE)
    plt.close(fig)


def build_monthly_grid_page(pdf: PdfPages, donor: DonorStats, ctx: RenderContext):
    fig = plt.figure(figsize=A4_PORTRAIT, facecolor=SURFACE)
    # Row 1 (legend) only carries content when the donor gave library or
    # playlist data (see draw_month_source_bar's own gating); it's kept in
    # the layout either way, drawn blank otherwise, so the grid below doesn't
    # shift position between donors.
    # Row 0 is the spacer under the suptitle; wider than the other pages' so
    # the legend sits clear of the title rather than crowding it.
    gs = GridSpec(4, 1, figure=fig, height_ratios=[0.75, 0.3, 8.4, 0.5],
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

    draw_footer(fig.add_subplot(gs[3]), donor.participant_code, ctx.version)

    fig.suptitle("YOUR MONTH-BY-MONTH HIGHLIGHTS", color=INK_PRIMARY, fontsize=20,
                 fontweight="bold", fontfamily=heading_family(), y=.9)
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
    ax.text(0, .9, wrap(text, 45, 60), ha="left", va="top", fontsize=10,
            color=INK_SECONDARY, transform=ax.transAxes, linespacing=1.2)


def build_poster_page(pdf: PdfPages, donor: DonorStats, ctx: RenderContext):
    fig = plt.figure(figsize=A4_PORTRAIT, facecolor=SURFACE)
    gs = GridSpec(4, 1, figure=fig, height_ratios=[0.35, 3.65, 5.9, 0.5],
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
        draw_archetype_card(fig, cards_gs[col], key, donor, ctx)

    draw_footer(fig.add_subplot(gs[3]), donor.participant_code, ctx.version)

    fig.suptitle("UNPACKING YOUR PLATFORM INTERACTION DATA", color=INK_PRIMARY,
                 fontsize=20, fontweight="bold", fontfamily=heading_family(), y=0.9)
    pdf.savefig(fig, facecolor=SURFACE)
    plt.close(fig)


def generate_donor_pdf(donor: DonorStats, output_path: Path, ctx: RenderContext) -> Path:
    """Render the three-page report for one donor to exactly `output_path`."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(output_path) as pdf:
        build_dashboard_page(pdf, donor, ctx)
        build_monthly_grid_page(pdf, donor, ctx)
        build_poster_page(pdf, donor, ctx)
    return output_path
