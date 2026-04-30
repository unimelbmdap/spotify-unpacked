import base64

import pytest
from fastapi.testclient import TestClient

from app.deps import get_settings
from app.main import create_app


@pytest.fixture
def admin_headers():
    creds = base64.b64encode(b"admin:hunter2hunter").decode()
    return {
        "Authorization": f"Basic {creds}",
        "X-Admin-Request": "1",
    }


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("IP_HASH_SALT", "x" * 64)
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "hunter2hunter")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path/'t.db'}")
    get_settings.cache_clear()
    from app import deps
    deps._engine_cache.clear()

    app = create_app()
    with TestClient(app) as c:
        yield c


def test_post_codes_creates_them(client, admin_headers):
    r = client.post(
        "/api/admin/codes",
        headers=admin_headers,
        json={"count": 3, "max_uses": 2, "admin_label": "cohort-A"},
    )
    assert r.status_code == 201
    body = r.json()
    assert len(body) == 3
    assert all(c["status"] == "active" for c in body)
    assert all(c["max_uses"] == 2 for c in body)


def test_get_codes_lists(client, admin_headers):
    client.post("/api/admin/codes", headers=admin_headers, json={"count": 2})
    r = client.get("/api/admin/codes", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_patch_code_revokes(client, admin_headers):
    [c] = client.post("/api/admin/codes", headers=admin_headers, json={"count": 1}).json()
    r = client.patch(
        f"/api/admin/codes/{c['code']}",
        headers=admin_headers,
        json={"status": "revoked"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "revoked"


def test_patch_unknown_code_returns_404(client, admin_headers):
    r = client.patch("/api/admin/codes/no-such", headers=admin_headers, json={"status": "revoked"})
    assert r.status_code == 404


def test_post_codes_without_csrf_header_is_400(client):
    creds = base64.b64encode(b"admin:hunter2hunter").decode()
    r = client.post(
        "/api/admin/codes",
        headers={"Authorization": f"Basic {creds}"},
        json={"count": 1},
    )
    assert r.status_code == 400


def test_post_codes_without_auth_is_401(client):
    r = client.post(
        "/api/admin/codes",
        headers={"X-Admin-Request": "1"},
        json={"count": 1},
    )
    assert r.status_code == 401
