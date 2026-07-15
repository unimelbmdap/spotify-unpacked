from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession


def make_engine(database_url: str) -> AsyncEngine:
    engine = create_async_engine(database_url, echo=False, future=True)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine.sync_engine, "connect")
        def _set_sqlite_pragmas(dbapi_conn, _record):  # noqa: ANN001
            # WAL lets readers and writers proceed concurrently, so the backup's
            # `VACUUM INTO` read snapshot never blocks a donation commit (the
            # default rollback journal would). journal_mode is persisted in the
            # DB header; busy_timeout is per-connection, so both are set on every
            # connect. A NULL _record marks a genuinely new DBAPI connection.
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA busy_timeout=5000")
            cur.close()

    return engine


def session_maker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db(engine: AsyncEngine) -> None:
    # Import models so SQLModel.metadata sees them.
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
