import secrets
from datetime import datetime, timezone

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import CodeStatus, ParticipantCode

CODE_BYTES = 8  # token_urlsafe(8) → 11 chars, ~64 bits entropy
CODE_REGEX = r"^[A-Za-z0-9_-]{6,32}$"


async def generate_codes(
    session: AsyncSession,
    *,
    count: int,
    max_uses: int = 1,
    admin_label: str | None = None,
) -> list[ParticipantCode]:
    if count < 1 or count > 1000:
        raise ValueError("count must be between 1 and 1000")
    if max_uses < 1:
        raise ValueError("max_uses must be >= 1")

    now = datetime.now(timezone.utc)
    codes: list[ParticipantCode] = []
    for _ in range(count):
        c = ParticipantCode(
            code=secrets.token_urlsafe(CODE_BYTES),
            status=CodeStatus.active,
            max_uses=max_uses,
            uses=0,
            created_at=now,
            admin_label=admin_label,
        )
        session.add(c)
        codes.append(c)
    return codes


async def list_codes(session: AsyncSession) -> list[ParticipantCode]:
    return list((await session.exec(select(ParticipantCode))).all())


async def revoke_code(session: AsyncSession, *, code: str) -> ParticipantCode | None:
    obj = await session.get(ParticipantCode, code)
    if obj is None:
        return None
    obj.status = CodeStatus.revoked
    session.add(obj)
    return obj


async def update_code(
    session: AsyncSession,
    *,
    code: str,
    max_uses: int | None = None,
    admin_label: str | None = None,
) -> ParticipantCode | None:
    obj = await session.get(ParticipantCode, code)
    if obj is None:
        return None
    if max_uses is not None:
        if max_uses < 1:
            raise ValueError("max_uses must be >= 1")
        obj.max_uses = max_uses
    if admin_label is not None:
        obj.admin_label = admin_label
    session.add(obj)
    return obj
