import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.deps import get_settings
from app.ratelimit import attach_limiter, donate_rate_limit


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("IP_HASH_SALT", "x" * 64)
    monkeypatch.setenv("ADMIN_PASSWORD", "hunter2hunter")
    monkeypatch.setenv("RATE_LIMIT_DONATE", "2/minute")
    get_settings.cache_clear()

    app = FastAPI()
    attach_limiter(app)

    @app.post("/x")
    @donate_rate_limit()
    def x(request: Request):
        return {"ok": True}

    return app


def test_rate_limit_blocks_after_n_requests(app):
    with TestClient(app) as c:
        assert c.post("/x").status_code == 200
        assert c.post("/x").status_code == 200
        assert c.post("/x").status_code == 429
