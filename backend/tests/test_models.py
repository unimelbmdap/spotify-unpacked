from datetime import datetime, timezone

import pytest
from sqlmodel import select

from app.db import init_db, make_engine, session_maker
from app.models import (
    AuditEvent,
    CodeStatus,
    Donation,
    DonationStatus,
    ParticipantCode,
)


@pytest.mark.asyncio
async def test_can_persist_each_model(tmp_path):
    engine = make_engine(f"sqlite+aiosqlite:///{tmp_path/'t.db'}")
    await init_db(engine)
    Session = session_maker(engine)

    async with Session() as s:
        s.add(
            ParticipantCode(
                code="abc",
                status=CodeStatus.active,
                max_uses=1,
                created_at=datetime.now(timezone.utc),
            )
        )
        s.add(
            Donation(
                code="abc",
                status=DonationStatus.pending,
                submitted_at=datetime.now(timezone.utc),
                client_ip_hash="hash",
                consent_version="v1.0",
            )
        )
        s.add(
            AuditEvent(
                ts=datetime.now(timezone.utc),
                kind="donate_ok",
                code="abc",
                client_ip_hash="hash",
            )
        )
        await s.commit()

    async with Session() as s:
        codes = (await s.execute(select(ParticipantCode))).scalars().all()
        donations = (await s.execute(select(Donation))).scalars().all()
        events = (await s.execute(select(AuditEvent))).scalars().all()

    assert len(codes) == 1 and codes[0].code == "abc"
    assert len(donations) == 1 and donations[0].status == DonationStatus.pending
    assert len(events) == 1 and events[0].kind == "donate_ok"

    await engine.dispose()
