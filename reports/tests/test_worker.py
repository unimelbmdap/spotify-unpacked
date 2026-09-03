"""Worker behaviour: scan rules, atomic publication, failure markers, claims.

Rendering runs in a child process (`python -m donation_reports render-one`),
exactly as in production, so these tests exercise the real subprocess path.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from donation_reports import worker
from donation_reports.naming import parse_bundle_name
from donation_reports.worker import (
    WorkerConfig,
    is_done,
    list_bundles,
    process_bundle,
    run_once,
    scan,
)
from tests.conftest import make_bundle


@pytest.fixture
def cfg(donations_dir: Path, assets_dir: Path) -> WorkerConfig:
    return WorkerConfig(
        donations_dir=donations_dir,
        tmp_dir=donations_dir.parent / ".tmp" / "reports",
        assets_dir=assets_dir,
        version=1,
        render_timeout=120,
    )


def _reports(cfg: WorkerConfig) -> list[str]:
    return sorted(p.name for p in cfg.reports_dir.glob("*")) if cfg.reports_dir.exists() else []


# --- scan -------------------------------------------------------------------

def test_list_bundles_requires_sidecar_and_parseable_name(donations_dir: Path):
    make_bundle(donations_dir, code="A", donation_id=1)
    make_bundle(donations_dir, code="B", donation_id=2, sidecar=False)
    (donations_dir / "donation_weird.zip").write_bytes(b"x")
    (donations_dir / "_db-backups").mkdir()
    (donations_dir / "_db-backups" / "snap-1.db").write_bytes(b"x")
    names = [n.code for _, n in list_bundles(donations_dir)]
    assert names == ["A"]


def test_is_done_rules(tmp_path: Path):
    name = parse_bundle_name("donation_A__20260901-101500__1.zip")
    assert name is not None
    reports = tmp_path
    assert not is_done(name, reports, 2, force=False)

    (reports / name.failed_name(2)).touch()
    assert is_done(name, reports, 2, force=False)
    assert not is_done(name, reports, 2, force=True)      # force retries a failure
    (reports / name.failed_name(2)).unlink()

    (reports / name.report_name(1)).touch()               # older version report
    assert is_done(name, reports, 2, force=False)         # a bump does not regenerate
    assert not is_done(name, reports, 2, force=True)      # force renders the new version

    (reports / name.report_name(2)).touch()
    assert is_done(name, reports, 2, force=True)          # never overwrite current version


def test_scan_only_filters_by_code_case_insensitively(cfg: WorkerConfig):
    make_bundle(cfg.donations_dir, code="ABC", donation_id=1)
    make_bundle(cfg.donations_dir, code="XYZ", donation_id=2)
    assert [n.code for _, n in scan(cfg, only="abc")] == ["ABC"]
    assert [n.code for _, n in scan(cfg)] == ["ABC", "XYZ"]


# --- process_bundle ---------------------------------------------------------

def test_renders_companion_then_pdf_and_leaves_no_temp_files(cfg: WorkerConfig):
    path = make_bundle(cfg.donations_dir)
    name = parse_bundle_name(path)
    assert name is not None

    outcome = process_bundle(cfg, path, name)

    assert outcome.status == "rendered", outcome
    assert _reports(cfg) == [name.companion_name(1), name.report_name(1)]
    pdf = (cfg.reports_dir / name.report_name(1)).read_bytes()
    assert pdf.startswith(b"%PDF")
    companion = json.loads((cfg.reports_dir / name.companion_name(1)).read_text())
    assert companion["source_bundle"] == name.zip_name
    assert not list(cfg.tmp_dir.glob("*"))  # claim and staging dir cleaned up
    assert not any(p.name.endswith(".tmp") for p in cfg.reports_dir.iterdir())


def test_corrupt_bundle_writes_failure_marker_and_loop_continues(cfg: WorkerConfig):
    bad = cfg.donations_dir / "donation_BAD__20260901-101500__1.zip"
    bad.write_bytes(b"not a zip")
    (cfg.donations_dir / (bad.name + ".json")).write_text("{}")
    good = make_bundle(cfg.donations_dir, code="GOOD", donation_id=2)

    summary = run_once(cfg)

    assert (summary.pending, summary.rendered, summary.failed) == (2, 1, 1)
    bad_name = parse_bundle_name(bad)
    good_name = parse_bundle_name(good)
    assert bad_name and good_name
    marker = json.loads((cfg.reports_dir / bad_name.failed_name(1)).read_text())
    assert marker["error"] == "BundleError"
    assert "not a readable zip" in marker["message"]
    assert marker["generator_version"] == 1
    assert (cfg.reports_dir / good_name.report_name(1)).exists()

    # Second cycle: both are done, nothing pending.
    assert run_once(cfg).pending == 0
    # Force retries the failure (still fails) but does not touch the good one.
    forced = run_once(cfg, force=True)
    assert (forced.pending, forced.failed) == (1, 1)


@pytest.mark.parametrize("kind", ["streaming_only", "library_only", "playlists_only", "pre_window"])
def test_renders_every_donation_shape(cfg: WorkerConfig, kind: str):
    from tests.conftest import streaming_entries

    kwargs = {
        "streaming_only": {"library": None, "playlists": None},
        "library_only": {"streaming": None, "playlists": None},
        "playlists_only": {"streaming": None, "library": None},
        "pre_window": {"streaming": streaming_entries(start="2024-01-01T10:00:00Z", days=30)},
    }[kind]
    path = make_bundle(cfg.donations_dir, **kwargs)
    name = parse_bundle_name(path)
    assert name is not None
    outcome = process_bundle(cfg, path, name)
    assert outcome.status == "rendered", outcome.error


def test_child_timeout_becomes_failure_marker(cfg: WorkerConfig, monkeypatch):
    path = make_bundle(cfg.donations_dir)
    name = parse_bundle_name(path)
    assert name is not None

    def slow(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="render-one", timeout=cfg.render_timeout, stderr=b"still going")

    monkeypatch.setattr(worker, "render_in_child", slow)
    outcome = process_bundle(cfg, path, name)
    assert outcome.status == "failed" and outcome.error == "RenderTimeout"
    marker = json.loads((cfg.reports_dir / name.failed_name(1)).read_text())
    assert marker["error"] == "RenderTimeout"
    assert "still going" in marker["traceback"]


def test_child_killed_by_signal_becomes_failure_marker(cfg: WorkerConfig, monkeypatch):
    path = make_bundle(cfg.donations_dir)
    name = parse_bundle_name(path)
    assert name is not None
    monkeypatch.setattr(
        worker, "render_in_child",
        lambda *a, **k: subprocess.CompletedProcess(args=[], returncode=-9, stdout="", stderr=""),
    )
    outcome = process_bundle(cfg, path, name)
    assert outcome.error == "RenderKilled"
    marker = json.loads((cfg.reports_dir / name.failed_name(1)).read_text())
    assert "signal 9" in marker["message"]


# --- claims -----------------------------------------------------------------

def test_live_claim_blocks_second_worker(cfg: WorkerConfig):
    path = make_bundle(cfg.donations_dir)
    name = parse_bundle_name(path)
    assert name is not None
    cfg.tmp_dir.mkdir(parents=True)
    (cfg.tmp_dir / name.claim_name(1)).write_text("other-pid")

    outcome = process_bundle(cfg, path, name)

    assert outcome.status == "skipped"
    assert _reports(cfg) == []
    assert (cfg.tmp_dir / name.claim_name(1)).exists()  # not ours to remove


def test_stale_claim_is_taken_over(cfg: WorkerConfig):
    path = make_bundle(cfg.donations_dir)
    name = parse_bundle_name(path)
    assert name is not None
    cfg.tmp_dir.mkdir(parents=True)
    claim = cfg.tmp_dir / name.claim_name(1)
    claim.write_text("dead-pid")
    old = time.time() - cfg.stale_after - 60
    os.utime(claim, (old, old))

    outcome = process_bundle(cfg, path, name)

    assert outcome.status == "rendered"
    assert not claim.exists()


# --- config -----------------------------------------------------------------

def test_config_from_env_defaults_and_overrides():
    cfg = WorkerConfig.from_env({})
    assert cfg.donations_dir == Path("/data/donations")
    assert cfg.reports_dir == Path("/data/donations/reports")
    assert cfg.tmp_dir == Path("/data/.tmp/reports")
    assert cfg.scan_interval == 60 and cfg.render_timeout == 600
    assert cfg.stale_after == 1200

    cfg = WorkerConfig.from_env({
        "REPORT_DONATIONS_DIR": "/x/donations", "REPORT_SCAN_INTERVAL": "5",
        "REPORT_RENDER_TIMEOUT": "30", "REPORT_TMP_DIR": "/y/tmp",
    })
    assert cfg.reports_dir == Path("/x/donations/reports")
    assert cfg.tmp_dir == Path("/y/tmp")
    assert (cfg.scan_interval, cfg.render_timeout, cfg.stale_after) == (5, 30, 60)
    assert cfg.python == sys.executable
