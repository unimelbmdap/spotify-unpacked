import pytest
from fastapi.testclient import TestClient

from app.consent import load_consent_text
from app.deps import get_settings
from app.main import create_app


def test_load_consent_text_reads_file(tmp_path):
    (tmp_path / "v1.0.md").write_text("hello consent", encoding="utf-8")
    text = load_consent_text(tmp_path, "v1.0")
    assert text == "hello consent"


def test_load_consent_text_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_consent_text(tmp_path, "v9.9")


@pytest.fixture
def client(monkeypatch, tmp_path):
    (tmp_path / "v1.0.md").write_text("CONSENT BODY", encoding="utf-8")
    monkeypatch.setenv("IP_HASH_SALT", "x" * 64)
    monkeypatch.setenv("ADMIN_PASSWORD", "hunter2hunter")
    monkeypatch.setenv("CONSENT_DIR", str(tmp_path))
    monkeypatch.setenv("CONSENT_VERSION", "v1.0")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path/'t.db'}")
    get_settings.cache_clear()
    from app import deps
    deps._engine_cache.clear()
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_consent_endpoint_returns_version_and_text(client):
    r = client.get("/api/consent")
    assert r.status_code == 200
    assert r.json() == {"version": "v1.0", "text": "CONSENT BODY"}
