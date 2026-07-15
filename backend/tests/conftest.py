import base64
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.deps import get_settings
from app.main import create_app


@pytest.fixture(autouse=True)
def _disable_db_backups(monkeypatch):
    """Keep the scheduled backup loop from writing snapshots during tests.

    Autouse so it also covers modules that define their own `client` fixture.
    The backup service functions are still exercised directly in test_backup.py.
    """
    monkeypatch.setenv("BACKUP_ENABLED", "false")


@pytest.fixture
def client(monkeypatch, tmp_path) -> Iterator[TestClient]:
    """Default app client.

    Sets the env vars Settings requires for validation, points the DB at a
    per-test tempfile, and resets cached state so each test gets a fresh app
    backed by its own SQLite. Tests that need extra env vars (e.g. CONSENT_DIR
    for `/api/consent`) override this fixture in their own module.
    """
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


@pytest.fixture
def admin_headers() -> dict[str, str]:
    """HTTP headers for an authenticated admin call (basic auth + CSRF marker)."""
    creds = base64.b64encode(b"admin:hunter2hunter").decode()
    return {
        "Authorization": f"Basic {creds}",
        "X-Admin-Request": "1",
    }
