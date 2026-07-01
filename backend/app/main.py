import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.admin_panel import create_admin
from app.db import init_db, make_engine, session_maker
from app.deps import get_settings
from app.ratelimit import attach_limiter
from app.routes import admin, codes, consent, donate, health
from app.services.codes import load_codes_from_file

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine = make_engine(settings.database_url)
    await init_db(engine)

    # Seed the participant-code whitelist from the configured file, if present.
    path = settings.participant_codes_file
    if path is not None and path.is_file():
        Session = session_maker(engine)
        async with Session() as s:
            summary, errors = await load_codes_from_file(s, path)
            await s.commit()
        logger.info(
            "participant codes seeded from %s: %s (errors=%d)", path, summary, len(errors)
        )

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
    app.include_router(codes.router)
    app.include_router(donate.router)
    app.include_router(admin.router)

    # Browser admin panel at /admin (separate from the /api/admin JSON API).
    create_admin(app, make_engine(settings.database_url), settings)
    return app


app = create_app()
