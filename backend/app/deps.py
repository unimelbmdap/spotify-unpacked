from collections.abc import AsyncIterator
from functools import lru_cache

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import Settings
from app.db import make_engine, session_maker
from app.security import check_basic_auth, hash_ip, require_admin_csrf_header


@lru_cache
def get_settings() -> Settings:
    return Settings()


_engine_cache: dict[str, async_sessionmaker[AsyncSession]] = {}


def _get_session_maker(settings: Settings) -> async_sessionmaker[AsyncSession]:
    if settings.database_url not in _engine_cache:
        _engine_cache[settings.database_url] = session_maker(make_engine(settings.database_url))
    return _engine_cache[settings.database_url]


async def get_db(
    settings: Settings = Depends(get_settings),
) -> AsyncIterator[AsyncSession]:
    Session = _get_session_maker(settings)
    async with Session() as s:
        yield s


def get_client_ip_hash(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> str:
    ip = request.client.host if request.client else "0.0.0.0"
    return hash_ip(ip, settings.ip_hash_salt)


def require_admin(
    request: Request,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    require_admin_csrf_header(dict(request.headers))
    if not check_basic_auth(authorization, settings.admin_username, settings.admin_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": 'Basic realm="admin"'},
        )


from app.mediaflux.client import MediafluxClient, StubMediafluxClient  # noqa: E402

_mediaflux_client: MediafluxClient | None = None


def get_mediaflux_client(settings: Settings = Depends(get_settings)) -> MediafluxClient:
    global _mediaflux_client
    if _mediaflux_client is not None:
        return _mediaflux_client
    if settings.mediaflux_client == "stub":
        _mediaflux_client = StubMediafluxClient()
    elif settings.mediaflux_client == "aterm":
        # AtermMediafluxClient is added in Task 21.
        from app.mediaflux.client import AtermMediafluxClient

        _mediaflux_client = AtermMediafluxClient(
            jar_path=settings.aterm_jar_path,
            host=settings.mediaflux_host,
            port=settings.mediaflux_port,
            token=settings.mediaflux_token,
        )
    else:  # pragma: no cover
        raise RuntimeError(f"Unknown MEDIAFLUX_CLIENT={settings.mediaflux_client}")
    return _mediaflux_client


def reset_mediaflux_client() -> None:
    """Test helper: clear the cached client."""
    global _mediaflux_client
    _mediaflux_client = None
