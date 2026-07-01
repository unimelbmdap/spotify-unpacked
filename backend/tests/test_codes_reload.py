import base64

import pytest
from fastapi.testclient import TestClient

from app.deps import get_settings
from app.main import create_app


@pytest.fixture
def seed_file(tmp_path):
    p = tmp_path / "codes.csv"
    p.write_text(
        "# code,max_uses,label\nSEED-0001,1,pilot\nSEED-0002,2,\n", encoding="utf-8"
    )
    return p


@pytest.fixture
def client(monkeypatch, tmp_path, seed_file):
    monkeypatch.setenv("IP_HASH_SALT", "x" * 64)
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "hunter2hunter")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path/'t.db'}")
    monkeypatch.setenv("PARTICIPANT_CODES_FILE", str(seed_file))
    monkeypatch.setenv("RATE_LIMIT_VALIDATE", "1000/minute")
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


def test_startup_loads_seed_file(client):
    assert client.get("/api/codes/SEED-0001").json() == {"valid": True}
    assert client.get("/api/codes/seed-0002").json() == {"valid": True}


def test_reload_imports_new_and_updates_existing(client, admin_headers, seed_file):
    seed_file.write_text("SEED-0001,1,pilot\nSEED-0003,1,late add\n", encoding="utf-8")
    r = client.post("/api/admin/codes/reload", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["added"] == 1  # SEED-0003
    assert body["updated"] == 1  # SEED-0001
    assert client.get("/api/codes/SEED-0003").json() == {"valid": True}


def test_reload_requires_admin_and_csrf(client):
    assert client.post("/api/admin/codes/reload").status_code in (400, 401)


def test_empty_codes_file_env_does_not_crash_startup(monkeypatch, tmp_path):
    # An empty PARTICIPANT_CODES_FILE must disable seeding, not resolve to "."
    # (a directory) and crash startup.
    monkeypatch.setenv("IP_HASH_SALT", "x" * 64)
    monkeypatch.setenv("ADMIN_PASSWORD", "hunter2hunter")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path/'t.db'}")
    monkeypatch.setenv("PARTICIPANT_CODES_FILE", "")
    get_settings.cache_clear()
    from app import deps

    deps._engine_cache.clear()
    app = create_app()
    with TestClient(app) as c:
        assert c.get("/api/codes/UNKNOWN-CODE").json() == {"valid": False}
