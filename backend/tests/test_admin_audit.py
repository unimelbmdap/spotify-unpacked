import base64
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.deps import get_settings
from app.main import create_app


@pytest.fixture
def admin_headers():
    creds = base64.b64encode(b"admin:hunter2hunter").decode()
    return {"Authorization": f"Basic {creds}", "X-Admin-Request": "1"}


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("IP_HASH_SALT", "x" * 64)
    monkeypatch.setenv("ADMIN_PASSWORD", "hunter2hunter")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path/'t.db'}")
    get_settings.cache_clear()
    from app import deps
    deps._engine_cache.clear()
    app = create_app()
    with TestClient(app) as c:
        yield c


def _seed_audit_event(client):
    import asyncio

    from app.deps import _get_session_maker, get_settings
    from app.models import AuditEvent

    settings = get_settings()
    Session = _get_session_maker(settings)

    async def insert():
        async with Session() as s:
            s.add(
                AuditEvent(
                    ts=datetime.now(timezone.utc),
                    kind="donate_reject",
                    code="abc",
                    client_ip_hash="h",
                    detail_json=json.dumps({"reason": "bad-code"}),
                )
            )
            await s.commit()

    asyncio.get_event_loop().run_until_complete(insert())


def test_audit_returns_recent_events(client, admin_headers):
    _seed_audit_event(client)
    r = client.get("/api/admin/audit", headers=admin_headers)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["kind"] == "donate_reject"
    assert rows[0]["code"] == "abc"
