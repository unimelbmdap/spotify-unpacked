import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlmodel import select

from app.db import init_db, make_engine, session_maker
from app.models import CodeStatus, Donation, DonationStatus, ParticipantCode
from app.services.codes import generate_codes
from app.services.donations import (
    CodeUnavailable,
    UploadFile,
    perform_donation,
    reserve_code,
)


@pytest.fixture
async def session(tmp_path):
    engine = make_engine(f"sqlite+aiosqlite:///{tmp_path/'t.db'}")
    await init_db(engine)
    Session = session_maker(engine)
    async with Session() as s:
        yield s
    await engine.dispose()


def _bundle(tmp_path: Path, names: list[str]) -> tuple[UploadFile, list[str]]:
    """Build a fake zip bundle on disk plus a list of original filenames.

    The donate route is what actually zips the donor's files; perform_donation
    just expects a path to a non-empty file it can copy into storage.
    """
    p = tmp_path / "bundle.zip"
    p.write_bytes(b"PK\x03\x04fakezip")
    return UploadFile(filename="bundle.zip", path=p, size=p.stat().st_size), names


@pytest.mark.asyncio
async def test_reserve_code_increments_uses_atomically(session):
    [c] = await generate_codes(session, count=1, max_uses=1)
    await session.commit()
    assert await reserve_code(session, code=c.code) is True
    await session.commit()

    refreshed = await session.get(ParticipantCode, c.code)
    assert refreshed.uses == 1


@pytest.mark.asyncio
async def test_reserve_code_returns_false_when_exhausted(session):
    [c] = await generate_codes(session, count=1, max_uses=1)
    await session.commit()
    await reserve_code(session, code=c.code)
    await session.commit()
    assert await reserve_code(session, code=c.code) is False


@pytest.mark.asyncio
async def test_reserve_code_returns_false_when_revoked(session):
    [c] = await generate_codes(session, count=1)
    c.status = CodeStatus.revoked
    session.add(c)
    await session.commit()
    assert await reserve_code(session, code=c.code) is False


@pytest.mark.asyncio
async def test_reserve_unknown_code_returns_false(session):
    assert await reserve_code(session, code="nope") is False


@pytest.mark.asyncio
async def test_perform_donation_stores_bundle_and_sidecar(session, tmp_path):
    [c] = await generate_codes(session, count=1, max_uses=1)
    await session.commit()

    storage_dir = tmp_path / "storage"
    bundle, names = _bundle(tmp_path, ["a.json", "b.json"])

    result = await perform_donation(
        session,
        storage_dir=storage_dir,
        code=c.code,
        consent_version="v1.0",
        consent_accepted_at=datetime(2026, 5, 29, 1, 0, tzinfo=timezone.utc),
        client_ip_hash="h",
        app_version="dev",
        bundle=bundle,
        original_filenames=names,
    )

    await session.commit()
    refreshed = await session.get(ParticipantCode, c.code)
    [donation] = (await session.exec(select(Donation))).all()

    assert refreshed.uses == 1
    assert donation.status == DonationStatus.stored
    assert donation.completed_at is not None
    assert donation.storage_path is not None
    # The donation hasn't been pushed to Mediaflux yet — sync is offline.
    assert donation.synced_at is None
    assert donation.mediaflux_asset_id is None

    # The bundle was placed in the storage dir under a "donation_…" name
    # plus a sidecar JSON with donor metadata.
    bundle_on_disk = Path(donation.storage_path)
    assert bundle_on_disk.exists()
    assert bundle_on_disk.parent == storage_dir
    assert bundle_on_disk.name.startswith("donation_")
    assert c.code in bundle_on_disk.name
    assert bundle_on_disk.name.endswith(".zip")

    sidecar = bundle_on_disk.with_name(bundle_on_disk.name + ".json")
    assert sidecar.exists()
    meta = json.loads(sidecar.read_text())
    assert meta["donor_code"] == c.code
    assert meta["consent_version"] == "v1.0"
    assert meta["original_filenames"] == ["a.json", "b.json"]

    # Per-file results echo the original filenames; asset_id is the
    # donation id (no Mediaflux id yet).
    assert [r.filename for r in result.results] == ["a.json", "b.json"]
    assert {r.asset_id for r in result.results} == {str(donation.id)}
    assert all(r.status == "ok" for r in result.results)
    assert result.donation_id == donation.id


@pytest.mark.asyncio
async def test_perform_donation_releases_code_and_marks_failed_on_storage_error(
    session, tmp_path
):
    [c] = await generate_codes(session, count=1, max_uses=1)
    await session.commit()

    # Point storage at a path that can't be created (a regular file, not
    # a dir, so mkdir(parents=True) will OSError).
    storage_dir = tmp_path / "blocker"
    storage_dir.write_bytes(b"not a directory")

    bundle, names = _bundle(tmp_path, ["a.json"])

    with pytest.raises(OSError):
        await perform_donation(
            session,
            storage_dir=storage_dir,
            code=c.code,
            consent_version="v1.0",
            consent_accepted_at=datetime.now(timezone.utc),
            client_ip_hash="h",
            app_version="dev",
            bundle=bundle,
            original_filenames=names,
        )

    await session.commit()
    refreshed = await session.get(ParticipantCode, c.code)
    [donation] = (await session.exec(select(Donation))).all()

    # Code use was released; donation marked failed.
    assert refreshed.uses == 0
    assert donation.status == DonationStatus.failed
    assert donation.storage_path is None


@pytest.mark.asyncio
async def test_perform_donation_raises_when_code_unavailable(session, tmp_path):
    bundle, names = _bundle(tmp_path, ["a.json"])
    with pytest.raises(CodeUnavailable):
        await perform_donation(
            session,
            storage_dir=tmp_path / "storage",
            code="nope",
            consent_version="v1.0",
            consent_accepted_at=datetime.now(timezone.utc),
            client_ip_hash="h",
            app_version="dev",
            bundle=bundle,
            original_filenames=names,
        )


def test_store_bundle_is_atomic(tmp_path):
    """store_bundle should never leave a half-written file visible."""
    from app.services.storage import store_bundle

    src = tmp_path / "in.zip"
    src.write_bytes(b"PK\x03\x04donor-data")
    target_dir = tmp_path / "store"

    result = store_bundle(
        source_zip=src,
        asset_name="donation_X__T__1.zip",
        sidecar={"donor_code": "X", "consent_version": "v1.0"},
        target_dir=target_dir,
    )

    assert result.bundle_path.exists()
    assert result.sidecar_path.exists()
    # Atomic-write tempfiles must have been cleaned up.
    leftovers = [p for p in target_dir.iterdir() if p.name.startswith(".")]
    assert leftovers == []
    # Contents intact.
    assert result.bundle_path.read_bytes() == b"PK\x03\x04donor-data"
    assert json.loads(result.sidecar_path.read_text())["donor_code"] == "X"
    # File permissions sane.
    assert os.stat(result.bundle_path).st_size == len(b"PK\x03\x04donor-data")
