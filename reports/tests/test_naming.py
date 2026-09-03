from pathlib import Path

import pytest

from donation_reports.naming import parse_bundle_name, version_tag


def test_parses_backend_bundle_name():
    name = parse_bundle_name(Path("/x/donation_ABC12__20260901-101500__12.zip"))
    assert name is not None
    assert name.code == "ABC12"
    assert name.stamp == "20260901-101500"
    assert name.donation_id == 12
    assert name.stem == "donation_ABC12__20260901-101500__12"
    assert name.zip_name == "donation_ABC12__20260901-101500__12.zip"
    assert name.sidecar_name == "donation_ABC12__20260901-101500__12.zip.json"


def test_is_not_anchored_on_the_year():
    assert parse_bundle_name("donation_Z__20270101-000000__1.zip") is not None


def test_codes_with_underscores_and_hyphens():
    name = parse_bundle_name("donation_MDAP-TEST_x__20260901-101500__3.zip")
    assert name is not None
    assert name.code == "MDAP-TEST_x"
    assert name.donation_id == 3


@pytest.mark.parametrize("bad", [
    "donation_ABC.zip",
    "donation_ABC__2026__12.zip",
    "donation_ABC__20260901-101500__12.pdf",
    "donation_ABC__20260901-101500__12.zip.json",
    "snap-20260901T000000Z.db",
    "ABC__20260901-101500__12.zip",
])
def test_rejects_non_bundles(bad):
    assert parse_bundle_name(bad) is None


def test_versioned_artefact_names():
    name = parse_bundle_name("donation_ABC__20260901-101500__12.zip")
    assert name is not None
    assert version_tag(1) == "v01"
    assert name.report_name(1) == "donation_ABC__20260901-101500__12__v01.pdf"
    assert name.companion_name(1) == "donation_ABC__20260901-101500__12__v01.json"
    assert name.failed_name(2) == "donation_ABC__20260901-101500__12__v02.failed.json"
    assert name.claim_name(1) == "donation_ABC__20260901-101500__12__v01.lock"


def test_any_version_glob_matches_reports_only(tmp_path: Path):
    name = parse_bundle_name("donation_ABC__20260901-101500__12.zip")
    assert name is not None
    (tmp_path / name.report_name(3)).touch()
    (tmp_path / name.failed_name(3)).touch()
    (tmp_path / name.companion_name(3)).touch()
    matches = sorted(p.name for p in tmp_path.glob(name.report_glob_any_version()))
    assert matches == [name.report_name(3)]
