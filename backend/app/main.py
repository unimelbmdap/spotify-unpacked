from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db, make_engine
from app.deps import get_settings
from app.routes import admin, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine = make_engine(settings.database_url)
    await init_db(engine)
    await engine.dispose()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Mediaflux Donation Backend", version="0.1.0", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(admin.router)
    return app


app = create_app()
