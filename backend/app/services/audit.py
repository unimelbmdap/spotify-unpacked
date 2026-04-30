import json
from datetime import datetime, timezone
from typing import Any

from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import AuditEvent


async def record_event(
    session: AsyncSession,
    *,
    kind: str,
    code: str | None = None,
    client_ip_hash: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    """Add an AuditEvent. Caller is responsible for committing."""
    session.add(
        AuditEvent(
            ts=datetime.now(timezone.utc),
            kind=kind,
            code=code,
            client_ip_hash=client_ip_hash,
            detail_json=json.dumps(detail, sort_keys=True) if detail else None,
        )
    )
