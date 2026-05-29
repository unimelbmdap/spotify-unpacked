from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlmodel import select

from app.db import init_db, make_engine, session_maker
from app.mediaflux.client import StubMediafluxClient
from app.mediaflux.exceptions import MediafluxAssetCreateError
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
    """Build a fake zip bundle on disk plus a list of original filenames."""
    p = tmp_path / "bundle.zip"
    # The donation service doesn't inspect zip contents — any non-empty
    # file passes the StubMediafluxClient's exists check.
    p.write_bytes(b"PK\x03\x04")  # zip magic prefix; one byte would also work
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
async def test_perform_donation_happy_path(session, tmp_path):
    [c] = await generate_codes(session, count=1, max_uses=1)
    await session.commit()

    client = StubMediafluxClient()
    bundle, names = _bundle(tmp_path, ["a.json", "b.json"])

    result = await perform_donation(
        session,
        mediaflux=client,
        namespace="/projects", collection_id=42,
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

    assert refreshed.uses == 1
    assert donation.status == DonationStatus.complete
    assert donation.completed_at is not None
    # One bundle, one asset.
    assert len(client.created) == 1
    assert len(client.destroyed) == 0
    # Per-file results echo the original filenames but share the bundle's asset id.
    assert [r.filename for r in result.results] == ["a.json", "b.json"]
    assert {r.asset_id for r in result.results} == {client.created[0]}
    assert all(r.status == "ok" for r in result.results)
    assert result.donation_id == donation.id

    # The single create_asset call lands in the project namespace as a
    # zip-named bundle and is added to the donations collection.
    [call] = client.create_calls
    assert call["namespace"] == "/projects"
    assert call["collection_id"] == 42
    assert call["name"].startswith(c.code + "__")
    assert call["name"].endswith(".zip")


@pytest.mark.asyncio
async def test_perform_donation_rolls_back_on_partial_failure(session, tmp_path):
    [c] = await generate_codes(session, count=1, max_uses=1)
    await session.commit()

    # Fail on the only create_asset call (one bundle = one create_asset call).
    client = StubMediafluxClient(fail_after=0)
    bundle, names = _bundle(tmp_path, ["a.json", "b.json"])

    with pytest.raises(MediafluxAssetCreateError):
        await perform_donation(
            session,
            mediaflux=client,
            namespace="/projects", collection_id=42,
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

    # No asset was created (the stub failed before returning an id),
    # so there's nothing to destroy either.
    assert client.created == []
    assert client.destroyed == []
    # Use was not burned by a failed attempt.
    assert refreshed.uses == 0
    assert donation.status == DonationStatus.failed


@pytest.mark.asyncio
async def test_perform_donation_raises_when_code_unavailable(session, tmp_path):
    bundle, names = _bundle(tmp_path, ["a.json"])
    with pytest.raises(CodeUnavailable):
        await perform_donation(
            session,
            mediaflux=StubMediafluxClient(),
            namespace="/projects", collection_id=42,
            code="nope",
            consent_version="v1.0",
            consent_accepted_at=datetime.now(timezone.utc),
            client_ip_hash="h",
            app_version="dev",
            bundle=bundle,
            original_filenames=names,
        )
