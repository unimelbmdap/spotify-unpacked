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


def _files(tmp_path: Path, names: list[str]) -> list[UploadFile]:
    out = []
    for n in names:
        p = tmp_path / n
        p.write_text("{}", encoding="utf-8")
        out.append(UploadFile(filename=n, path=p, size=p.stat().st_size))
    return out


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
    files = _files(tmp_path, ["a.json", "b.json"])

    result = await perform_donation(
        session,
        mediaflux=client,
        namespace="/projects", collection_id=42,
        code=c.code,
        consent_version="v1.0",
        consent_accepted_at=datetime.now(timezone.utc),
        client_ip_hash="h",
        app_version="dev",
        files=files,
    )

    await session.commit()
    refreshed = await session.get(ParticipantCode, c.code)
    [donation] = (await session.exec(select(Donation))).all()

    assert refreshed.uses == 1
    assert donation.status == DonationStatus.complete
    assert donation.completed_at is not None
    assert len(client.created) == 2
    assert len(client.destroyed) == 0
    assert all(r.status == "ok" for r in result.results)
    assert result.donation_id == donation.id

    # Each create_asset call goes to the project namespace with a
    # disambiguator-prefixed asset name and the donations collection_id.
    assert [call["namespace"] for call in client.create_calls] == ["/projects", "/projects"]
    assert [call["collection_id"] for call in client.create_calls] == [42, 42]
    names = [call["name"] for call in client.create_calls]
    assert all(n.startswith(c.code + "__") and n.endswith(".json") for n in names)
    assert any(n.endswith("a.json") for n in names)
    assert any(n.endswith("b.json") for n in names)


@pytest.mark.asyncio
async def test_perform_donation_rolls_back_on_partial_failure(session, tmp_path):
    [c] = await generate_codes(session, count=1, max_uses=1)
    await session.commit()

    # Fail on the second create_asset call.
    client = StubMediafluxClient(fail_after=1)
    files = _files(tmp_path, ["a.json", "b.json"])

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
            files=files,
        )

    await session.commit()

    refreshed = await session.get(ParticipantCode, c.code)
    [donation] = (await session.exec(select(Donation))).all()

    # First asset was created then destroyed during rollback.
    assert client.destroyed == client.created
    # Use was not burned by a failed attempt.
    assert refreshed.uses == 0
    assert donation.status == DonationStatus.failed


@pytest.mark.asyncio
async def test_perform_donation_raises_when_code_unavailable(session, tmp_path):
    files = _files(tmp_path, ["a.json"])
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
            files=files,
        )
