"""Font registration for matplotlib.

Every .ttf/.otf under `<assets>/fonts/` is registered explicitly. Matplotlib's
font cache is built once and does not pick up files it was not pointed at, so
registration is the only reliable way to make bundled fonts visible in a
container. Missing files degrade to the rcParams fallback stack with a single
warning, so the package renders anywhere (tests, a laptop without fonts) and
the container renders as designed.
"""

import dataclasses
import logging
from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

logger = logging.getLogger("donation_reports.fonts")

HEADING_FAMILY = "Poppins"

# Body stack in preference order. Only families that actually registered are
# kept, so matplotlib does not log a findfont warning per missing family.
BODY_STACK = ["Literata", "Noto Sans CJK JP", "Noto Emoji", "DejaVu Sans"]

# Some Poppins distributions have broken OS/2 usWeightClass metadata
# (Thin/ExtraLight/Light/Regular all self-report as weight 400), so each
# file's weight is re-tagged from its filename or the font matcher picks an
# arbitrary one of those four for "regular"/"semibold". The Google Fonts
# statics fetched by scripts/fetch_fonts.sh are correct; this keeps a locally
# installed copy honest too.
_HEADING_WEIGHTS = {
    "thin": 100, "extralight": 200, "light": 300, "regular": 400,
    "medium": 500, "semibold": 600, "bold": 700, "extrabold": 800, "black": 900,
}

_registered: set[str] = set()
_configured = False


def register_fonts(fonts_dir: Path) -> set[str]:
    """Register every font file under `fonts_dir`; return the family names found."""
    names: set[str] = set()
    for path in sorted(fonts_dir.glob("*")):
        if path.suffix.lower() not in {".ttf", ".otf"}:
            continue
        # Variable-font files register under the same family as the statics
        # with duplicate style entries; which wins a weight lookup then depends
        # on directory order, and the default instance renders noticeably
        # condensed. Only static weights are ever registered.
        if "VariableFont" in path.name or "[" in path.name:
            continue
        try:
            fm.fontManager.addfont(str(path))
            names.add(fm.FontProperties(fname=str(path)).get_name())
        except Exception as exc:  # noqa: BLE001 - a bad font must not stop rendering
            logger.warning("font not loaded path=%s error=%s", path, exc)
    if HEADING_FAMILY in names:
        for i, entry in enumerate(fm.fontManager.ttflist):
            if entry.name != HEADING_FAMILY:
                continue
            stem = Path(entry.fname).stem.lower()
            stem = stem.replace(HEADING_FAMILY.lower() + "-", "").replace("italic", "")
            if stem in _HEADING_WEIGHTS:
                weight = _HEADING_WEIGHTS[stem]
                fm.fontManager.ttflist[i] = dataclasses.replace(entry, weight=weight)
    return names


def configure(assets_dir: Path) -> None:
    """Register bundled fonts and set the rcParams used by render.py. Idempotent."""
    global _configured, _registered
    if _configured:
        return
    fonts_dir = assets_dir / "fonts"
    _registered = register_fonts(fonts_dir) if fonts_dir.is_dir() else set()

    stack = [name for name in BODY_STACK if name in _registered or name == "DejaVu Sans"]
    wanted = [*BODY_STACK, HEADING_FAMILY]
    missing = [name for name in wanted if name not in _registered and name != "DejaVu Sans"]
    if missing:
        logger.warning("fonts missing, falling back: %s (looked in %s)",
                       ", ".join(missing), fonts_dir)

    plt.rcParams["font.family"] = stack
    plt.rcParams["font.weight"] = "regular"
    plt.rcParams["axes.titleweight"] = "bold"
    plt.rcParams["axes.unicode_minus"] = False
    # Fallback families ship one or two static weights, so matplotlib logs a
    # "Failed to find font weight" warning for every weight it cannot match
    # in them even though Literata (when present) carries the text. Harmless
    # but noisy; keep font_manager at error level.
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    _configured = True


def heading_family() -> str | list[str]:
    """Family for headings: Poppins when registered, else the body stack."""
    if HEADING_FAMILY in _registered:
        return HEADING_FAMILY
    return list(plt.rcParams["font.family"])


def reset_for_tests() -> None:
    global _configured, _registered
    _configured = False
    _registered = set()
