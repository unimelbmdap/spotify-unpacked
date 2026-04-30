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


def _seed_donation(client, admin_headers) -> dict:
    [code] = client.post("/api/admin/codes", headers=admin_headers, json={"count": 1}).json()
    import asyncio
    from app.deps import _get_session_maker, get_settings
    from app.models import Donation, DonationStatus

    settings = get_settings()
    Session = _get_session_maker(settings)

    async def insert():
        async with Session() as s:
            s.add(
                Donation(
                    code=code["code"],
                    status=DonationStatus.complete,
                    submitted_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                    client_ip_hash="h",
                    consent_version="v1.0",
                    asset_ids_json=json.dumps(["A1", "A2"]),
                )
            )
            await s.commit()

    asyncio.get_event_loop().run_until_complete(insert())
    return code


def test_list_donations_empty(client, admin_headers):
    r = client.get("/api/admin/donations", headers=admin_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_list_donations_returns_inserted(client, admin_headers):
    code = _seed_donation(client, admin_headers)
    r = client.get("/api/admin/donations", headers=admin_headers)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["code"] == code["code"]
    assert rows[0]["asset_ids"] == ["A1", "A2"]


def test_list_donations_filter_by_code(client, admin_headers):
    _seed_donation(client, admin_headers)
    r = client.get("/api/admin/donations?code=does-not-exist", headers=admin_headers)
    assert r.status_code == 200
    assert r.json() == []
