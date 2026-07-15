"""Scheduled SQLite backups.

A periodic ``VACUUM INTO`` snapshot of the donations DB, written under the
donations tree so the existing mflux-sync loop mirrors it to Mediaflux with no
extra wiring. Snapshots are timestamped and never overwritten, so they
accumulate as versioned history (mflux-sync is upload-only and never deletes).
"""

import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.engine import make_url

logger = logging.getLogger("app")

SNAPSHOT_GLOB = "snap-*.db"


def sqlite_path_from_url(database_url: str) -> Path | None:
    """Filesystem path of the SQLite DB, or None if it cannot be snapshotted.

    Returns None for non-sqlite URLs and for in-memory databases, neither of
    which can be copied to a file on disk.
    """
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite"):
        return None
    if not url.database or url.database == ":memory:":
        return None
    return Path(url.database)


def latest_snapshot_age_hours(backup_dir: Path, *, now: datetime) -> float | None:
    """Age in hours of the most recent snapshot, or None if there are none."""
    if not backup_dir.is_dir():
        return None
    mtimes = [p.stat().st_mtime for p in backup_dir.glob(SNAPSHOT_GLOB)]
    if not mtimes:
        return None
    return (now.timestamp() - max(mtimes)) / 3600.0


def create_snapshot(db_path: Path, backup_dir: Path, *, now: datetime) -> Path:
    """Write a consistent ``VACUUM INTO`` snapshot and return its path.

    The temp file is written to the DB's own parent directory (outside the
    donations tree that mflux-sync mirrors) and atomically renamed into
    ``backup_dir`` on the same filesystem, so the uploader never sees a
    half-written file.
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    final = backup_dir / f"snap-{stamp}.db"
    tmp = db_path.parent / f".snap-{stamp}.db.tmp"
    try:
        # VACUUM INTO does not reliably accept a bound parameter across SQLite
        # versions, so inline the (server-controlled) path with single-quote
        # escaping rather than passing it as a query parameter.
        escaped = str(tmp).replace("'", "''")
        con = sqlite3.connect(str(db_path))
        try:
            con.execute(f"VACUUM INTO '{escaped}'")
        finally:
            con.close()
        # Atomic on one filesystem. If backup_dir is misconfigured onto a
        # separate mount, os.replace raises EXDEV here and the temp is cleaned
        # up below rather than orphaned.
        os.replace(tmp, final)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return final


def cleanup_stale_temp(db_path: Path) -> None:
    """Remove leftover `.snap-*.db.tmp` files (e.g. from a crash mid-vacuum)."""
    for stale in db_path.parent.glob(".snap-*.db.tmp"):
        stale.unlink(missing_ok=True)


def prune_old_snapshots(backup_dir: Path, keep: int) -> list[Path]:
    """Delete all but the newest `keep` snapshots. keep <= 0 keeps everything.

    Snapshot names are timestamp-sortable, so lexical order is chronological.
    Only the local copy is pruned; mflux-sync has already shipped each snapshot
    to Mediaflux, which is never deleted from.
    """
    if keep <= 0 or not backup_dir.is_dir():
        return []
    snaps = sorted(backup_dir.glob(SNAPSHOT_GLOB))
    removed = snaps[:-keep] if len(snaps) > keep else []
    for p in removed:
        p.unlink(missing_ok=True)
    return removed


async def maybe_snapshot(
    database_url: str,
    backup_dir: Path,
    interval_hours: float,
    *,
    now: datetime,
    retention: int = 0,
) -> Path | None:
    """Snapshot the DB if the newest snapshot is older than ``interval_hours``.

    Returns the new snapshot path, or None if a recent snapshot already exists
    (or the DB is not a snapshotable SQLite file). The blocking vacuum runs in a
    worker thread so the event loop is never stalled. After a successful
    snapshot, prunes local copies beyond ``retention`` (0 = keep all).
    """
    db_path = sqlite_path_from_url(database_url)
    if db_path is None:
        return None
    age = latest_snapshot_age_hours(backup_dir, now=now)
    if age is not None and age < interval_hours:
        return None
    path = await asyncio.to_thread(create_snapshot, db_path, backup_dir, now=now)
    if retention > 0:
        for pruned in prune_old_snapshots(backup_dir, retention):
            logger.info("pruned old db backup: %s", pruned)
    return path


async def run_backup_loop(
    database_url: str,
    backup_dir: Path,
    interval_hours: float,
    retention: int = 0,
) -> None:
    """Periodically snapshot the DB until cancelled.

    Checks every hour (or every interval, whichever is shorter) and dumps when
    due, rather than sleeping a full interval between dumps: a restart never
    skips more than the check window, and a restart storm cannot spam snapshots
    because a fresh one suppresses the next. Never raises out of the loop.
    """
    db_path = sqlite_path_from_url(database_url)
    if db_path is None:
        logger.warning("db backup disabled: %s is not a file-backed sqlite DB", database_url)
        return
    # Clear any temp file orphaned by a crash/kill during a previous vacuum.
    cleanup_stale_temp(db_path)
    check_secs = max(60.0, min(3600.0, interval_hours * 3600.0))
    logger.info(
        "db backup loop: %s every ~%.0fh (checking every %.0fs, keep %d)",
        backup_dir,
        interval_hours,
        check_secs,
        retention,
    )
    while True:
        try:
            path = await maybe_snapshot(
                database_url,
                backup_dir,
                interval_hours,
                now=datetime.now(timezone.utc),
                retention=retention,
            )
            if path is not None:
                logger.info("db backup written: %s", path)
        except Exception:
            logger.exception("db backup cycle failed; will retry next check")
        await asyncio.sleep(check_secs)
