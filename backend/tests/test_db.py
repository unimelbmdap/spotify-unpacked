import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import init_db, make_engine, session_maker


@pytest.mark.asyncio
async def test_init_db_creates_tables(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path/'t.db'}"
    engine = make_engine(url)
    await init_db(engine)
    Session = session_maker(engine)
    async with Session() as s:
        assert isinstance(s, AsyncSession)
    await engine.dispose()
