import base64

import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from app.deps import get_settings, require_admin


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("IP_HASH_SALT", "x" * 64)
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "hunter2hunter")
    get_settings.cache_clear()  # clear lru_cache between tests

    app = FastAPI()

    @app.get("/admin-only")
    def admin_only(_: None = Depends(require_admin)):
        return {"ok": True}

    return app


def test_admin_endpoint_rejects_no_creds(app):
    with TestClient(app) as c:
        r = c.get("/admin-only", headers={"X-Admin-Request": "1"})
    assert r.status_code == 401


def test_admin_endpoint_rejects_wrong_password(app):
    creds = base64.b64encode(b"admin:wrong").decode()
    with TestClient(app) as c:
        r = c.get(
            "/admin-only",
            headers={"Authorization": f"Basic {creds}", "X-Admin-Request": "1"},
        )
    assert r.status_code == 401


def test_admin_endpoint_rejects_missing_csrf_header(app):
    creds = base64.b64encode(b"admin:hunter2hunter").decode()
    with TestClient(app) as c:
        r = c.get("/admin-only", headers={"Authorization": f"Basic {creds}"})
    assert r.status_code == 400


def test_admin_endpoint_accepts_correct_creds_and_header(app):
    creds = base64.b64encode(b"admin:hunter2hunter").decode()
    with TestClient(app) as c:
        r = c.get(
            "/admin-only",
            headers={"Authorization": f"Basic {creds}", "X-Admin-Request": "1"},
        )
    assert r.status_code == 200 and r.json() == {"ok": True}
