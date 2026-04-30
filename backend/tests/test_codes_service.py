import pytest
from sqlmodel import select

from app.db import init_db, make_engine, session_maker
from app.models import CodeStatus, ParticipantCode
from app.services.codes import (
    generate_codes,
    list_codes,
    revoke_code,
    update_code,
)


@pytest.fixture
async def session(tmp_path):
    engine = make_engine(f"sqlite+aiosqlite:///{tmp_path/'t.db'}")
    await init_db(engine)
    Session = session_maker(engine)
    async with Session() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_generate_codes_creates_n_active_rows(session):
    codes = await generate_codes(session, count=5, max_uses=2, admin_label="cohort-1")
    await session.commit()

    assert len(codes) == 5
    assert len({c.code for c in codes}) == 5  # unique
    rows = (await session.exec(select(ParticipantCode))).all()
    assert all(r.status == CodeStatus.active and r.max_uses == 2 for r in rows)
    assert all(r.admin_label == "cohort-1" for r in rows)


@pytest.mark.asyncio
async def test_list_codes_returns_all(session):
    await generate_codes(session, count=3)
    await session.commit()
    rows = await list_codes(session)
    assert len(rows) == 3


@pytest.mark.asyncio
async def test_revoke_code_marks_revoked(session):
    [c] = await generate_codes(session, count=1)
    await session.commit()
    updated = await revoke_code(session, code=c.code)
    await session.commit()
    assert updated.status == CodeStatus.revoked


@pytest.mark.asyncio
async def test_revoke_unknown_code_returns_none(session):
    assert await revoke_code(session, code="nope") is None


@pytest.mark.asyncio
async def test_update_code_changes_max_uses_and_label(session):
    [c] = await generate_codes(session, count=1, max_uses=1, admin_label="initial")
    await session.commit()
    updated = await update_code(session, code=c.code, max_uses=3, admin_label="updated")
    await session.commit()
    assert updated.max_uses == 3 and updated.admin_label == "updated"
