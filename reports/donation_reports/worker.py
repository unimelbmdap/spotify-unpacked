"""Scan the donations directory and render reports for bundles that lack one.

Idempotent by filesystem state, no database. See the design note
(docs/superpowers/specs/2026-09-02-donation-report-pipeline-design.md) for the
rules; the short version:

- A bundle counts only once its sidecar `.json` exists (the backend publishes
  the zip first, then the sidecar).
- Done = a PDF at ANY generator version, or a failure marker at the current
  version. `force` ignores both and skips only a current-version PDF, so
  nothing in reports/ is ever overwritten.
- Each bundle renders in a child process with a timeout; abnormal exit
  becomes a failure marker rather than a crash loop.
- Every file is staged under tmp_dir (outside the tree mflux-sync mirrors)
  and moved into reports/ with os.replace. Companion JSON lands before PDF.
- A per-bundle claim file (O_EXCL) stops a one-off `run --once --force` and
  the daemon from rendering the same bundle at the same time.
"""

import json
import logging
import os
import subprocess
import sys
import time
import traceback
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from donation_reports.naming import BundleName, parse_bundle_name
from donation_reports.version import GENERATOR_VERSION

logger = logging.getLogger("donation_reports.worker")

REPORTS_SUBDIR = "reports"


@dataclass(frozen=True)
class WorkerConfig:
    donations_dir: Path
    tmp_dir: Path
    assets_dir: Path
    version: int = GENERATOR_VERSION
    scan_interval: float = 60.0
    render_timeout: float = 600.0
    stale_claim_seconds: float | None = None  # default: 2 x render_timeout
    python: str = sys.executable

    @property
    def reports_dir(self) -> Path:
        return self.donations_dir / REPORTS_SUBDIR

    @property
    def stale_after(self) -> float:
        if self.stale_claim_seconds is not None:
            return self.stale_claim_seconds
        return 2 * self.render_timeout

    @staticmethod
    def from_env(env: Mapping[str, str] | None = None) -> "WorkerConfig":
        env = dict(os.environ) if env is None else env
        donations_dir = Path(env.get("REPORT_DONATIONS_DIR", "/data/donations"))
        tmp_dir = Path(env.get("REPORT_TMP_DIR", str(donations_dir.parent / ".tmp" / "reports")))
        default_assets = Path(__file__).resolve().parent.parent / "assets"
        assets_dir = Path(env.get("REPORT_ASSETS_DIR", str(default_assets)))
        return WorkerConfig(
            donations_dir=donations_dir,
            tmp_dir=tmp_dir,
            assets_dir=assets_dir,
            scan_interval=float(env.get("REPORT_SCAN_INTERVAL", "60")),
            render_timeout=float(env.get("REPORT_RENDER_TIMEOUT", "600")),
        )


@dataclass(frozen=True)
class Outcome:
    stem: str
    status: str  # rendered | failed | skipped
    seconds: float = 0.0
    error: str | None = None


@dataclass
class CycleSummary:
    pending: int = 0
    rendered: int = 0
    failed: int = 0
    skipped: int = 0
    seconds: float = 0.0
    outcomes: list[Outcome] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

def list_bundles(donations_dir: Path) -> list[tuple[Path, BundleName]]:
    """Bundles in `donations_dir` whose name parses and whose sidecar exists."""
    found = []
    for zip_path in sorted(donations_dir.glob("donation_*.zip")):
        name = parse_bundle_name(zip_path)
        if name is None:
            logger.warning("ignoring unparseable bundle name path=%s", zip_path.name)
            continue
        if not (donations_dir / name.sidecar_name).exists():
            logger.info("waiting for sidecar stem=%s", name.stem)
            continue
        found.append((zip_path, name))
    return found


def is_done(name: BundleName, reports_dir: Path, version: int, *, force: bool) -> bool:
    if (reports_dir / name.report_name(version)).exists():
        return True
    if force:
        return False
    if any(reports_dir.glob(name.report_glob_any_version())):
        return True
    return (reports_dir / name.failed_name(version)).exists()


def scan(
    cfg: WorkerConfig, *, force: bool = False, only: str | None = None
) -> list[tuple[Path, BundleName]]:
    reports_dir = cfg.reports_dir
    pending = []
    for zip_path, name in list_bundles(cfg.donations_dir):
        if only is not None and name.code.lower() != only.lower():
            continue
        if is_done(name, reports_dir, cfg.version, force=force):
            if force:
                logger.info("force: current-version report exists; bump GENERATOR_VERSION "
                            "to regenerate stem=%s", name.stem)
            continue
        pending.append((zip_path, name))
    return pending


# ---------------------------------------------------------------------------
# Claims and atomic publication
# ---------------------------------------------------------------------------

def _claim(cfg: WorkerConfig, name: BundleName) -> Path | None:
    """Create the claim file with O_EXCL; None if another live worker holds it."""
    cfg.tmp_dir.mkdir(parents=True, exist_ok=True)
    claim = cfg.tmp_dir / name.claim_name(cfg.version)
    try:
        fd = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        age = time.time() - claim.stat().st_mtime if claim.exists() else 0
        if age < cfg.stale_after:
            return None
        logger.warning("removing stale claim stem=%s age_seconds=%.0f", name.stem, age)
        claim.unlink(missing_ok=True)
        try:
            fd = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return None
    with os.fdopen(fd, "w") as fh:
        fh.write(f"{os.getpid()} {datetime.now(UTC).isoformat()}\n")
    return claim


def _publish(src: Path, dest: Path) -> None:
    """Move a completed file into reports/ atomically (same filesystem)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    os.replace(src, dest)


def _write_failure_marker(cfg: WorkerConfig, name: BundleName, *, error: str, message: str,
                          detail: str | None = None) -> Path:
    marker = {
        "generator_version": cfg.version,
        "failed_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_bundle": name.zip_name,
        "error": error,
        "message": message,
        "traceback": detail,
    }
    tmp = cfg.tmp_dir / (name.failed_name(cfg.version) + ".tmp")
    tmp.write_text(json.dumps(marker, indent=2, sort_keys=True), encoding="utf-8")
    dest = cfg.reports_dir / name.failed_name(cfg.version)
    _publish(tmp, dest)
    return dest


# ---------------------------------------------------------------------------
# Rendering one bundle
# ---------------------------------------------------------------------------

def render_in_child(
    cfg: WorkerConfig, zip_path: Path, out_dir: Path
) -> subprocess.CompletedProcess:
    """Run `render-one` in a child process so OOM kills and hangs stay contained."""
    cmd = [
        cfg.python, "-m", "donation_reports", "render-one",
        str(zip_path), str(out_dir),
        "--version", str(cfg.version),
        "--assets-dir", str(cfg.assets_dir),
    ]
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=cfg.render_timeout, check=False
    )


def _tail(text: str, lines: int = 30) -> str:
    return "\n".join(text.strip().splitlines()[-lines:])


def process_bundle(cfg: WorkerConfig, zip_path: Path, name: BundleName) -> Outcome:
    started = time.monotonic()
    claim = _claim(cfg, name)
    if claim is None:
        logger.info("skipped: claimed by another worker stem=%s", name.stem)
        return Outcome(name.stem, "skipped")
    out_dir = cfg.tmp_dir / name.versioned_stem(cfg.version)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            result = render_in_child(cfg, zip_path, out_dir)
        except subprocess.TimeoutExpired as exc:
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            _write_failure_marker(cfg, name, error="RenderTimeout",
                                  message=f"render exceeded {cfg.render_timeout:.0f}s",
                                  detail=_tail(stderr))
            logger.error("failed   stem=%s version=%s error=RenderTimeout", name.stem, cfg.version)
            return Outcome(name.stem, "failed", time.monotonic() - started, "RenderTimeout")

        companion_tmp = out_dir / name.companion_name(cfg.version)
        report_tmp = out_dir / name.report_name(cfg.version)
        if result.returncode != 0 or not companion_tmp.exists() or not report_tmp.exists():
            error, message = _classify_child_failure(result)
            _write_failure_marker(cfg, name, error=error, message=message,
                                  detail=_tail(result.stderr))
            logger.error("failed   stem=%s version=%s error=%s", name.stem, cfg.version, error)
            return Outcome(name.stem, "failed", time.monotonic() - started, error)

        # Companion first: a PDF on disk always has its companion beside it.
        _publish(companion_tmp, cfg.reports_dir / name.companion_name(cfg.version))
        _publish(report_tmp, cfg.reports_dir / name.report_name(cfg.version))
        seconds = time.monotonic() - started
        logger.info("rendered stem=%s version=%s seconds=%.1f", name.stem, cfg.version, seconds)
        return Outcome(name.stem, "rendered", seconds)
    except Exception as exc:  # noqa: BLE001 - the loop must survive anything
        _write_failure_marker(cfg, name, error=type(exc).__name__, message=str(exc),
                              detail=traceback.format_exc())
        logger.exception("failed   stem=%s version=%s error=%s",
                         name.stem, cfg.version, type(exc).__name__)
        return Outcome(name.stem, "failed", time.monotonic() - started, type(exc).__name__)
    finally:
        for leftover in out_dir.glob("*") if out_dir.exists() else []:
            leftover.unlink(missing_ok=True)
        if out_dir.exists():
            out_dir.rmdir()
        claim.unlink(missing_ok=True)


def _classify_child_failure(result: subprocess.CompletedProcess) -> tuple[str, str]:
    if result.returncode < 0:
        return "RenderKilled", f"render process killed by signal {-result.returncode}"
    if result.returncode == 0:
        return "RenderIncomplete", "render exited 0 without producing both output files"
    # render-one prints `<ErrorClass>: <message>` as its last stderr line.
    last = _tail(result.stderr, 1)
    error, _, message = last.partition(": ")
    if not message:
        return "RenderError", last or f"exit code {result.returncode}"
    return error.strip() or "RenderError", message.strip()


# ---------------------------------------------------------------------------
# Cycles
# ---------------------------------------------------------------------------

def run_once(cfg: WorkerConfig, *, force: bool = False, only: str | None = None) -> CycleSummary:
    started = time.monotonic()
    summary = CycleSummary()
    pending = scan(cfg, force=force, only=only)
    summary.pending = len(pending)
    for zip_path, name in pending:
        outcome = process_bundle(cfg, zip_path, name)
        summary.outcomes.append(outcome)
        if outcome.status == "rendered":
            summary.rendered += 1
        elif outcome.status == "failed":
            summary.failed += 1
        else:
            summary.skipped += 1
    summary.seconds = time.monotonic() - started
    logger.info("cycle    pending=%d rendered=%d failed=%d skipped=%d seconds=%.1f",
                summary.pending, summary.rendered, summary.failed, summary.skipped, summary.seconds)
    return summary


def run_forever(cfg: WorkerConfig) -> None:
    logger.info("report-gen: %s -> %s every %.0fs version=%s",
                cfg.donations_dir, cfg.reports_dir, cfg.scan_interval, cfg.version)
    while True:
        try:
            run_once(cfg)
        except Exception:  # noqa: BLE001
            logger.exception("cycle failed; retrying after interval")
        time.sleep(cfg.scan_interval)
