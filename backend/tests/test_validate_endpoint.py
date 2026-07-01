import base64

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.deps import get_settings
from app.main import create_app
from app.ratelimit import attach_limiter, validate_rate_limit


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("IP_HASH_SALT", "x" * 64)
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "hunter2hunter")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path/'t.db'}")
    monkeypatch.setenv("RATE_LIMIT_VALIDATE", "1000/minute")
    monkeypatch.delenv("PARTICIPANT_CODES_FILE", raising=False)
    get_settings.cache_clear()
    from app import deps

    deps._engine_cache.clear()
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_headers():
    creds = base64.b64encode(b"admin:hunter2hunter").decode()
    return {"Authorization": f"Basic {creds}", "X-Admin-Request": "1"}


def _make_code(client, admin_headers, max_uses=1):
    [c] = client.post(
        "/api/admin/codes", headers=admin_headers, json={"count": 1, "max_uses": max_uses}
    ).json()
    return c["code"]


def test_valid_active_code_returns_true(client, admin_headers):
    code = _make_code(client, admin_headers)
    r = client.post("/api/codes/validate", json={"code": code})
    assert r.status_code == 200
    assert r.json() == {"valid": True}


def test_unknown_code_returns_false(client):
    assert client.post("/api/codes/validate", json={"code": "UNKNOWN-CODE-1"}).json() == {"valid": False}


def test_revoked_code_returns_false(client, admin_headers):
    code = _make_code(client, admin_headers)
    client.patch(f"/api/admin/codes/{code}", headers=admin_headers, json={"status": "revoked"})
    assert client.post("/api/codes/validate", json={"code": code}).json() == {"valid": False}


def test_validation_is_case_insensitive(client, admin_headers):
    code = _make_code(client, admin_headers)
    assert client.post("/api/codes/validate", json={"code": code.lower()}).json() == {"valid": True}


def test_malformed_code_returns_false_not_error(client):
    r = client.post("/api/codes/validate", json={"code": "ab"})  # too short
    assert r.status_code == 200
    assert r.json() == {"valid": False}


def test_validate_endpoint_is_rate_limited(monkeypatch):
    monkeypatch.setenv("IP_HASH_SALT", "x" * 64)
    monkeypatch.setenv("ADMIN_PASSWORD", "hunter2hunter")
    monkeypatch.setenv("RATE_LIMIT_VALIDATE", "2/minute")
    get_settings.cache_clear()

    app = FastAPI()
    attach_limiter(app)

    @app.get("/v")
    @validate_rate_limit()
    def v(request: Request):
        return {"ok": True}

    with TestClient(app) as c:
        assert c.get("/v").status_code == 200
        assert c.get("/v").status_code == 200
        assert c.get("/v").status_code == 429
