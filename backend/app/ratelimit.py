from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from app.deps import get_settings

limiter = Limiter(key_func=get_remote_address)


def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests, slow down."},
    )


def attach_limiter(app: FastAPI) -> None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)


def donate_rate_limit() -> Callable[..., Any]:
    """Decorator that applies the configured donate rate limit."""
    return limiter.limit(lambda: get_settings().rate_limit_donate)


def validate_rate_limit() -> Callable[..., Any]:
    """Decorator that applies the configured code-validation rate limit."""
    return limiter.limit(lambda: get_settings().rate_limit_validate)
