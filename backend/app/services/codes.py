import re
import secrets
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import CodeStatus, ParticipantCode
from app.services.code_seed import CodeSeedEntry, parse_seed_csv

CODE_BYTES = 8  # token_urlsafe(8) → 11 chars, ~64 bits entropy
CODE_REGEX = r"^[A-Za-z0-9_-]{6,32}$"
_CODE_RE = re.compile(CODE_REGEX)


def normalise_code(code: str) -> str:
    """Canonical form of a participant code: trimmed and uppercased.

    Applied everywhere codes are written or looked up so participants can
    type any case (`mdap-001` == `MDAP-001`).
    """
    return code.strip().upper()


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
            code=normalise_code(secrets.token_urlsafe(CODE_BYTES)),
            status=CodeStatus.active,
            max_uses=max_uses,
            uses=0,
            created_at=now,
            admin_label=admin_label,
        )
        session.add(c)
        codes.append(c)
    return codes


async def import_codes(
    session: AsyncSession, entries: list[CodeSeedEntry]
) -> dict[str, int]:
    """Upsert caller-supplied codes (from the seed file or a reload).

    Idempotent: new codes are inserted; codes that already exist have their
    ``max_uses``/``admin_label`` updated but keep their ``uses`` and
    ``status`` (so a revoked code stays revoked and usage is never reset).
    Entries whose code is malformed or whose ``max_uses`` < 1 are skipped.
    Caller commits. Returns ``{"added", "updated", "skipped"}``.
    """
    added = updated = skipped = 0
    now = datetime.now(timezone.utc)
    for entry in entries:
        nc = normalise_code(entry.code)
        if not _CODE_RE.fullmatch(nc) or entry.max_uses < 1:
            skipped += 1
            continue
        existing = await session.get(ParticipantCode, nc)
        if existing is None:
            session.add(
                ParticipantCode(
                    code=nc,
                    status=CodeStatus.active,
                    max_uses=entry.max_uses,
                    uses=0,
                    created_at=now,
                    admin_label=entry.admin_label,
                )
            )
            added += 1
        else:
            existing.max_uses = entry.max_uses
            if entry.admin_label is not None:
                existing.admin_label = entry.admin_label
            session.add(existing)
            updated += 1
    return {"added": added, "updated": updated, "skipped": skipped}


async def load_codes_from_file(
    session: AsyncSession, path: Path
) -> tuple[dict[str, int], list[str]]:
    """Read the seed CSV at `path`, upsert its codes, return (summary, errors).

    Shared by startup seeding and the admin reload endpoint. Caller commits.
    """
    text = path.read_text(encoding="utf-8")
    entries, errors = parse_seed_csv(text)
    summary = await import_codes(session, entries)
    return summary, errors


async def is_code_valid(session: AsyncSession, code: str) -> bool:
    """Read-only check that a code can currently be used to donate.

    True only when the code exists, is active, and has remaining uses. Does
    NOT reserve — the authoritative atomic reservation happens in
    ``donations.reserve_code`` at submit time.
    """
    obj = await session.get(ParticipantCode, normalise_code(code))
    return obj is not None and obj.status == CodeStatus.active and obj.uses < obj.max_uses


async def list_codes(session: AsyncSession) -> list[ParticipantCode]:
    return list((await session.exec(select(ParticipantCode))).all())


async def revoke_code(session: AsyncSession, *, code: str) -> ParticipantCode | None:
    obj = await session.get(ParticipantCode, normalise_code(code))
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
    obj = await session.get(ParticipantCode, normalise_code(code))
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
