import pytest

from app.db import init_db, make_engine, session_maker
from app.models import CodeStatus, ParticipantCode
from app.services.code_seed import CodeSeedEntry
from app.services.codes import (
    import_codes,
    is_code_valid,
    normalise_code,
    get_by_code,
)
from app.services.donations import reserve_code


@pytest.fixture
async def session(tmp_path):
    engine = make_engine(f"sqlite+aiosqlite:///{tmp_path/'t.db'}")
    await init_db(engine)
    Session = session_maker(engine)
    async with Session() as s:
        yield s
    await engine.dispose()


def test_normalise_code_trims_and_uppercases():
    assert normalise_code("  mdap-2026-001 ") == "MDAP-2026-001"


@pytest.mark.asyncio
async def test_import_codes_inserts_new(session):
    summary = await import_codes(
        session,
        [
            CodeSeedEntry(code="mdap-2026-001", max_uses=1, admin_label="pilot"),
            CodeSeedEntry(code="MDAP-2026-002", max_uses=3),
        ],
    )
    await session.commit()
    assert summary == {"added": 2, "updated": 0, "skipped": 0}
    obj = await get_by_code(session, "MDAP-2026-001")
    assert obj is not None
    assert obj.status == CodeStatus.active
    assert obj.max_uses == 1
    assert obj.admin_label == "pilot"


@pytest.mark.asyncio
async def test_import_codes_idempotent_preserves_uses_and_status(session):
    await import_codes(session, [CodeSeedEntry(code="AAA-111", max_uses=2)])
    await session.commit()
    obj = await get_by_code(session, "AAA-111")
    obj.uses = 1
    obj.status = CodeStatus.revoked
    session.add(obj)
    await session.commit()

    # Re-import the same code (different case) with new max_uses/label.
    summary = await import_codes(
        session, [CodeSeedEntry(code="aaa-111", max_uses=5, admin_label="updated")]
    )
    await session.commit()
    assert summary == {"added": 0, "updated": 1, "skipped": 0}

    obj = await get_by_code(session, "AAA-111")
    assert obj.uses == 1  # preserved
    assert obj.status == CodeStatus.revoked  # preserved
    assert obj.max_uses == 5  # updated
    assert obj.admin_label == "updated"  # updated


@pytest.mark.asyncio
async def test_import_codes_skips_invalid_format(session):
    summary = await import_codes(
        session,
        [
            CodeSeedEntry(code="ok-code-1"),  # valid
            CodeSeedEntry(code="12345"),  # valid five-digit participant code
            CodeSeedEntry(code="no"),  # too short (< 5 chars)
            CodeSeedEntry(code="bad code!"),  # invalid chars
        ],
    )
    await session.commit()
    assert summary["added"] == 2
    assert summary["skipped"] == 2


@pytest.mark.asyncio
async def test_is_code_valid_true_for_active_unused(session):
    await import_codes(session, [CodeSeedEntry(code="LIVE-0001")])
    await session.commit()
    assert await is_code_valid(session, "live-0001") is True  # case-insensitive


@pytest.mark.asyncio
async def test_is_code_valid_false_for_unknown_revoked_exhausted(session):
    await import_codes(
        session,
        [CodeSeedEntry(code="REV-0001"), CodeSeedEntry(code="EXH-0001", max_uses=1)],
    )
    await session.commit()

    assert await is_code_valid(session, "UNKNOWN-1") is False

    obj = await get_by_code(session, "REV-0001")
    obj.status = CodeStatus.revoked
    session.add(obj)
    await session.commit()
    assert await is_code_valid(session, "REV-0001") is False

    assert await reserve_code(session, code="EXH-0001") is True
    await session.commit()
    assert await is_code_valid(session, "EXH-0001") is False


@pytest.mark.asyncio
async def test_reserve_code_is_case_insensitive(session):
    await import_codes(session, [CodeSeedEntry(code="CASE-0001", max_uses=1)])
    await session.commit()
    assert await reserve_code(session, code="case-0001") is True
    await session.commit()
