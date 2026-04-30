import asyncio

import pytest

from app.db import init_db, make_engine, session_maker
from app.services.codes import generate_codes
from app.services.donations import reserve_code


@pytest.mark.asyncio
async def test_concurrent_reservations_respect_max_uses(tmp_path):
    engine = make_engine(f"sqlite+aiosqlite:///{tmp_path/'t.db'}")
    await init_db(engine)
    Session = session_maker(engine)

    async with Session() as s:
        [c] = await generate_codes(s, count=1, max_uses=3)
        await s.commit()
        code = c.code

    async def attempt() -> bool:
        async with Session() as s:
            ok = await reserve_code(s, code=code)
            await s.commit()
            return ok

    # Fire 20 concurrent attempts; only 3 should win.
    outcomes = await asyncio.gather(*(attempt() for _ in range(20)))
    wins = sum(outcomes)
    assert wins == 3

    await engine.dispose()
