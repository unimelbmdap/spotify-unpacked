import asyncio
import json
from datetime import datetime, timezone


def _seed_audit_event(client):
    """Insert one audit event directly via the live session maker.

    `client` isn't read here — its purpose is to set up the app + DB via the
    `client` fixture before this helper runs.
    """
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

    asyncio.run(insert())


def test_audit_returns_recent_events(client, admin_headers):
    _seed_audit_event(client)
    r = client.get("/api/admin/audit", headers=admin_headers)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["kind"] == "donate_reject"
    assert rows[0]["code"] == "abc"
