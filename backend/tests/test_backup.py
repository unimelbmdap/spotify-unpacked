import asyncio
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.services.backup import (
    cleanup_stale_temp,
    create_snapshot,
    latest_snapshot_age_hours,
    maybe_snapshot,
    prune_old_snapshots,
    sqlite_path_from_url,
)

# Fixed reference instant so snapshot filenames and ages are deterministic.
NOW = datetime(2026, 7, 16, 3, 0, 0, tzinfo=timezone.utc)


def _make_db(path: Path, rows: int = 3) -> None:
    con = sqlite3.connect(str(path))
    con.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    con.executemany("INSERT INTO t (v) VALUES (?)", [(f"row{i}",) for i in range(rows)])
    con.commit()
    con.close()


def _age_file(path: Path, *, hours_before: float) -> None:
    m = (NOW - timedelta(hours=hours_before)).timestamp()
    os.utime(path, (m, m))


def test_sqlite_path_from_url_absolute():
    assert sqlite_path_from_url("sqlite+aiosqlite:////app/data/donations.db") == Path(
        "/app/data/donations.db"
    )


def test_sqlite_path_from_url_relative():
    assert sqlite_path_from_url("sqlite+aiosqlite:///./donations.db") == Path("./donations.db")


def test_sqlite_path_from_url_rejects_memory_and_other_engines():
    # No database part -> in-memory sqlite, which cannot be snapshotted.
    assert sqlite_path_from_url("sqlite+aiosqlite://") is None
    assert sqlite_path_from_url("postgresql+asyncpg://host/db") is None


def test_create_snapshot_is_a_consistent_copy(tmp_path):
    db = tmp_path / "donations.db"
    _make_db(db, rows=5)
    backup_dir = tmp_path / "donations" / "_db-backups"

    snap = create_snapshot(db, backup_dir, now=NOW)

    assert snap.name == "snap-20260716T030000Z.db"
    con = sqlite3.connect(str(snap))
    try:
        assert con.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 5
    finally:
        con.close()
    # No partial temp file left next to the DB (outside the synced tree).
    assert not list(tmp_path.glob(".snap-*.tmp"))


def test_latest_snapshot_age_hours_none_when_absent(tmp_path):
    assert latest_snapshot_age_hours(tmp_path / "missing", now=NOW) is None
    empty = tmp_path / "b"
    empty.mkdir()
    assert latest_snapshot_age_hours(empty, now=NOW) is None


def test_latest_snapshot_age_hours_uses_newest(tmp_path):
    backup_dir = tmp_path / "b"
    backup_dir.mkdir()
    old = backup_dir / "snap-old.db"
    old.write_bytes(b"x")
    _age_file(old, hours_before=10)
    new = backup_dir / "snap-new.db"
    new.write_bytes(b"x")
    _age_file(new, hours_before=2)

    assert latest_snapshot_age_hours(backup_dir, now=NOW) == pytest.approx(2.0, abs=0.01)


def test_maybe_snapshot_dumps_when_no_prior_snapshot(tmp_path):
    db = tmp_path / "donations.db"
    _make_db(db)
    backup_dir = tmp_path / "donations" / "_db-backups"
    url = f"sqlite+aiosqlite:///{db}"

    out = asyncio.run(maybe_snapshot(url, backup_dir, 24.0, now=NOW))

    assert out is not None and out.exists()


def test_maybe_snapshot_skips_when_recent(tmp_path):
    db = tmp_path / "donations.db"
    _make_db(db)
    backup_dir = tmp_path / "donations" / "_db-backups"
    backup_dir.mkdir(parents=True)
    prior = backup_dir / "snap-existing.db"
    prior.write_bytes(b"x")
    _age_file(prior, hours_before=1)
    url = f"sqlite+aiosqlite:///{db}"

    out = asyncio.run(maybe_snapshot(url, backup_dir, 24.0, now=NOW))

    assert out is None
    assert list(backup_dir.glob("snap-*.db")) == [prior]


def test_maybe_snapshot_dumps_when_stale(tmp_path):
    db = tmp_path / "donations.db"
    _make_db(db)
    backup_dir = tmp_path / "donations" / "_db-backups"
    backup_dir.mkdir(parents=True)
    prior = backup_dir / "snap-existing.db"
    prior.write_bytes(b"x")
    _age_file(prior, hours_before=25)
    url = f"sqlite+aiosqlite:///{db}"

    out = asyncio.run(maybe_snapshot(url, backup_dir, 24.0, now=NOW))

    assert out is not None and out.exists() and out != prior


def test_maybe_snapshot_none_for_non_sqlite(tmp_path):
    out = asyncio.run(maybe_snapshot("postgresql+asyncpg://host/db", tmp_path, 24.0, now=NOW))
    assert out is None


def test_cleanup_stale_temp_removes_orphaned_tmp(tmp_path):
    (tmp_path / ".snap-old.db.tmp").write_bytes(b"partial")
    (tmp_path / "donations.db").write_bytes(b"real")  # must survive
    cleanup_stale_temp(tmp_path / "donations.db")
    assert not list(tmp_path.glob(".snap-*.tmp"))
    assert (tmp_path / "donations.db").exists()


def test_prune_old_snapshots_keeps_newest(tmp_path):
    backup_dir = tmp_path / "b"
    backup_dir.mkdir()
    # Timestamp-sortable names; newest last.
    names = [f"snap-2026071{i}T000000Z.db" for i in range(5)]
    for n in names:
        (backup_dir / n).write_bytes(b"x")

    removed = prune_old_snapshots(backup_dir, keep=2)

    assert sorted(p.name for p in removed) == names[:3]
    assert sorted(p.name for p in backup_dir.glob("snap-*.db")) == names[3:]


def test_prune_old_snapshots_keep_zero_is_noop(tmp_path):
    backup_dir = tmp_path / "b"
    backup_dir.mkdir()
    (backup_dir / "snap-a.db").write_bytes(b"x")
    assert prune_old_snapshots(backup_dir, keep=0) == []
    assert len(list(backup_dir.glob("snap-*.db"))) == 1


def test_maybe_snapshot_prunes_after_writing(tmp_path):
    db = tmp_path / "donations.db"
    _make_db(db)
    backup_dir = tmp_path / "donations" / "_db-backups"
    backup_dir.mkdir(parents=True)
    # Two pre-existing snapshots, both stale, so a new one is due and tips us
    # over keep=2. Age both, else the newer one's fresh mtime reads as recent.
    for n in ("snap-20260101T000000Z.db", "snap-20260102T000000Z.db"):
        (backup_dir / n).write_bytes(b"x")
        _age_file(backup_dir / n, hours_before=48)
    url = f"sqlite+aiosqlite:///{db}"

    new = asyncio.run(maybe_snapshot(url, backup_dir, 24.0, now=NOW, retention=2))

    assert new is not None
    kept = sorted(p.name for p in backup_dir.glob("snap-*.db"))
    assert len(kept) == 2
    assert new.name in kept
    # Oldest was pruned; the newest pre-existing one is kept.
    assert "snap-20260101T000000Z.db" not in kept


def test_wal_mode_enabled_on_engine_connections(tmp_path):
    import asyncio as _asyncio

    from app.db import make_engine

    async def _check() -> str | None:
        engine = make_engine(f"sqlite+aiosqlite:///{tmp_path/'w.db'}")
        async with engine.connect() as conn:
            from sqlalchemy import text

            mode = (await conn.execute(text("PRAGMA journal_mode"))).scalar()
        await engine.dispose()
        return mode

    assert (_asyncio.run(_check()) or "").lower() == "wal"
