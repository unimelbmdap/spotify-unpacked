import pytest
from sqlmodel import select

from app.db import init_db, make_engine, session_maker
from app.models import AuditEvent
from app.services.audit import record_event


@pytest.mark.asyncio
async def test_record_event_writes_row(tmp_path):
    engine = make_engine(f"sqlite+aiosqlite:///{tmp_path/'t.db'}")
    await init_db(engine)
    Session = session_maker(engine)

    async with Session() as s:
        await record_event(
            s, kind="donate_reject", code="abc", client_ip_hash="h", detail={"reason": "bad-code"}
        )
        await s.commit()

    async with Session() as s:
        rows = (await s.exec(select(AuditEvent))).all()

    assert len(rows) == 1
    assert rows[0].kind == "donate_reject"
    assert rows[0].code == "abc"
    assert '"reason": "bad-code"' in rows[0].detail_json

    await engine.dispose()
