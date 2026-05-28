from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db, make_engine
from app.deps import get_settings
from app.ratelimit import attach_limiter
from app.routes import admin, consent, donate, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine = make_engine(settings.database_url)
    await init_db(engine)
    await engine.dispose()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Mediaflux Donation Backend", version="0.1.0", lifespan=lifespan)
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Admin-Request"],
    )
    attach_limiter(app)
    app.include_router(health.router)
    app.include_router(consent.router)
    app.include_router(donate.router)
    app.include_router(admin.router)
    return app


app = create_app()
