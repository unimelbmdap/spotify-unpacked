"""Render each donation shape through the in-process path and check the PDF."""

import re
from pathlib import Path

import pytest

from donation_reports import fonts
from donation_reports.cli import render_bundle
from tests.conftest import make_bundle, streaming_entries

PAGE_RE = re.compile(rb"/Type\s*/Page\b")


def _page_count(pdf: bytes) -> int:
    return len(PAGE_RE.findall(pdf))


@pytest.mark.parametrize("kind", ["full", "streaming_only", "library_only", "playlists_only", "pre_window"])
def test_renders_three_pages(kind: str, donations_dir: Path, assets_dir: Path, tmp_path: Path):
    kwargs = {
        "full": {},
        "streaming_only": {"library": None, "playlists": None},
        "library_only": {"streaming": None, "playlists": None},
        "playlists_only": {"streaming": None, "library": None},
        "pre_window": {"streaming": streaming_entries(start="2024-01-01T10:00:00Z", days=30)},
    }[kind]
    bundle = make_bundle(donations_dir, **kwargs)

    companion, report = render_bundle(bundle, tmp_path / "out", version=7, assets_dir=assets_dir)

    assert companion.name.endswith("__v07.json") and report.name.endswith("__v07.pdf")
    pdf = report.read_bytes()
    assert pdf.startswith(b"%PDF")
    assert _page_count(pdf) == 3
    assert report.stat().st_size > 10_000


def test_streaming_only_variant_gets_its_own_name(donations_dir: Path, assets_dir: Path, tmp_path: Path):
    bundle = make_bundle(donations_dir)
    companion, report = render_bundle(bundle, tmp_path / "out", version=1, assets_dir=assets_dir,
                                      variant="streaming-only")
    assert report.name.endswith("__v01__streaming-only.pdf")
    assert companion.name.endswith("__v01__streaming-only.json")


def test_missing_fonts_fall_back_without_error(assets_dir: Path, caplog):
    fonts.configure(assets_dir)
    assert fonts.heading_family() == ["DejaVu Sans"]
    assert "fonts missing" in caplog.text


def test_bundled_fonts_are_registered(tmp_path: Path):
    """When font files are present they register and Metropolis becomes the heading face."""
    import matplotlib.font_manager as fm

    dejavu = Path(fm.findfont("DejaVu Sans"))
    assets = tmp_path / "assets"
    (assets / "fonts").mkdir(parents=True)
    # Any real TTF proves registration (the family name comes from the file).
    # A variable-font file must be skipped, whatever family it claims.
    (assets / "fonts" / "Literata-Regular.ttf").write_bytes(dejavu.read_bytes())
    (assets / "fonts" / "Literata-VariableFont_opsz,wght.ttf").write_bytes(b"not a font")
    (assets / "fonts" / "Poppins[wght].ttf").write_bytes(b"not a font")
    names = fonts.register_fonts(assets / "fonts")
    assert names == {"DejaVu Sans"}


def test_archetype_images_are_drawn_when_present(donations_dir: Path, tmp_path: Path):
    """With profile_*.jpg under assets/images the poster embeds them (PDF grows)."""
    from PIL import Image

    bare = tmp_path / "bare"
    (bare / "fonts").mkdir(parents=True)
    (bare / "images").mkdir()
    with_images = tmp_path / "with_images"
    (with_images / "fonts").mkdir(parents=True)
    (with_images / "images").mkdir()
    for key in ("receptive", "responsive", "deliberate"):
        Image.new("RGB", (400, 300), color=(200, 30, 30)).save(with_images / "images" / f"profile_{key}.jpg")

    bundle = make_bundle(donations_dir)
    _, plain = render_bundle(bundle, tmp_path / "out_plain", version=1, assets_dir=bare)
    fonts.reset_for_tests()
    _, illustrated = render_bundle(bundle, tmp_path / "out_img", version=1, assets_dir=with_images)

    assert illustrated.stat().st_size > plain.stat().st_size
    assert _page_count(illustrated.read_bytes()) == 3


def test_packaged_images_are_present():
    """The three archetype images the team supplied ship with the package."""
    images = Path(__file__).resolve().parent.parent / "assets" / "images"
    for key in ("receptive", "responsive", "deliberate"):
        assert (images / f"profile_{key}.jpg").is_file(), key
