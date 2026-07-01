import pytest
from fastapi.testclient import TestClient

from app.admin_panel import authenticate_admin, prepare_code_data
from app.config import Settings
from app.deps import get_settings
from app.main import create_app


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        ip_hash_salt="x" * 64,
        admin_username="admin",
        admin_password="hunter2hunter",
    )


def test_authenticate_admin_accepts_correct_and_rejects_wrong():
    s = _settings()
    assert authenticate_admin("admin", "hunter2hunter", s) is True
    assert authenticate_admin("admin", "nope", s) is False
    assert authenticate_admin("root", "hunter2hunter", s) is False


def test_prepare_code_data_normalises_and_defaults_on_create():
    data = prepare_code_data({"code": " mdap-2026-9 ", "max_uses": 2}, is_created=True)
    assert data["code"] == "MDAP-2026-9"
    assert data["uses"] == 0
    assert data["created_at"] is not None


def test_prepare_code_data_rejects_malformed_code():
    with pytest.raises(ValueError):
        prepare_code_data({"code": "no"}, is_created=True)


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("IP_HASH_SALT", "x" * 64)
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "hunter2hunter")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path/'t.db'}")
    monkeypatch.delenv("PARTICIPANT_CODES_FILE", raising=False)
    get_settings.cache_clear()
    from app import deps

    deps._engine_cache.clear()
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_admin_login_page_is_mounted(client):
    assert client.get("/admin/login").status_code == 200


def test_admin_index_requires_auth(client):
    r = client.get("/admin", follow_redirects=False)
    assert r.status_code in (302, 307)


def test_admin_session_cookie_is_samesite_strict(client):
    # SameSite=Strict blocks cross-site GETs from carrying the admin session,
    # mitigating CSRF on the panel's state-changing actions.
    r = client.post(
        "/admin/login",
        data={"username": "admin", "password": "hunter2hunter"},
        follow_redirects=False,
    )
    assert "samesite=strict" in r.headers.get("set-cookie", "").lower()
