import asyncio
import json
from datetime import datetime, timezone


def _seed_donation(client, admin_headers) -> dict:
    """Insert a completed donation row directly via the live session maker.

    Used to populate `/api/admin/donations` for listing tests without going
    through the real donate flow (which lives in its own test module).
    """
    [code] = client.post("/api/admin/codes", headers=admin_headers, json={"count": 1}).json()
    from app.deps import _get_session_maker, get_settings
    from app.models import Donation, DonationStatus

    settings = get_settings()
    Session = _get_session_maker(settings)

    async def insert():
        async with Session() as s:
            s.add(
                Donation(
                    code=code["code"],
                    status=DonationStatus.stored,
                    submitted_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                    client_ip_hash="h",
                    consent_version="v1.0",
                    storage_path="/app/data/donations/donation_test__T__1.zip",
                    # Legacy field — kept on the model for back-compat; still
                    # exposed in the listing as `asset_ids`.
                    asset_ids_json=json.dumps(["A1", "A2"]),
                )
            )
            await s.commit()

    asyncio.run(insert())
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
    assert rows[0]["status"] == "stored"
    assert rows[0]["storage_path"].endswith(".zip")
    assert rows[0]["synced_at"] is None
    assert rows[0]["mediaflux_asset_id"] is None
    assert rows[0]["asset_ids"] == ["A1", "A2"]  # legacy field still surfaced


def test_list_donations_filter_by_code(client, admin_headers):
    _seed_donation(client, admin_headers)
    r = client.get("/api/admin/donations?code=does-not-exist", headers=admin_headers)
    assert r.status_code == 200
    assert r.json() == []
