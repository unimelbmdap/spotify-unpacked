import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import update
from sqlmodel.ext.asyncio.session import AsyncSession

from app.mediaflux.client import MediafluxClient
from app.mediaflux.metadata import DonorMetadata
from app.models import CodeStatus, Donation, DonationStatus, ParticipantCode
from app.schemas import DonateResult, DonationResponse

# Asset/path-friendly subset of the donor code for the namespace path.
_SAFE_CODE = re.compile(r"[^A-Za-z0-9_-]")


class CodeUnavailable(Exception):
    """Raised when the participant code is unknown, revoked, or exhausted."""


@dataclass(frozen=True)
class UploadFile:
    filename: str
    path: Path
    size: int


async def reserve_code(session: AsyncSession, *, code: str) -> bool:
    """Atomically increment uses if code is active and uses < max_uses.

    Returns True if the reservation succeeded, False otherwise. Caller commits.

    Uses an ORM bulk UPDATE with synchronize_session='evaluate' so that any
    ParticipantCode instance already in the identity map has its uses attribute
    updated in-memory — avoiding stale-read issues without triggering async I/O.
    """
    stmt = (
        update(ParticipantCode)
        .where(
            ParticipantCode.code == code,
            ParticipantCode.status == CodeStatus.active,
            ParticipantCode.uses < ParticipantCode.max_uses,
        )
        .values(uses=ParticipantCode.uses + 1)
        .execution_options(synchronize_session="evaluate")
    )
    result = await session.exec(stmt)  # type: ignore[call-overload]
    return result.rowcount == 1  # type: ignore[union-attr]


async def _release_code(session: AsyncSession, *, code: str) -> None:
    """Decrement uses by 1 for compensation on donation failure."""
    stmt = (
        update(ParticipantCode)
        .where(
            ParticipantCode.code == code,
            ParticipantCode.uses > 0,
        )
        .values(uses=ParticipantCode.uses - 1)
        .execution_options(synchronize_session="evaluate")
    )
    await session.exec(stmt)  # type: ignore[call-overload]


def _safe_code_for_path(code: str) -> str:
    return _SAFE_CODE.sub("_", code)


def _build_namespace(root: str, code: str, ts: datetime, donation_id: int) -> str:
    stamp = ts.strftime("%Y%m%d-%H%M%S")
    return f"{root.rstrip('/')}/{_safe_code_for_path(code)}_{stamp}_{donation_id}"


async def perform_donation(
    session: AsyncSession,
    *,
    mediaflux: MediafluxClient,
    namespace_root: str,
    code: str,
    consent_version: str,
    consent_accepted_at: datetime,
    client_ip_hash: str,
    app_version: str,
    files: list[UploadFile],
) -> DonationResponse:
    """Execute a single donation transaction with all-or-fail semantics.

    Steps:
      1. Atomic reservation of code use (rollback decrements on failure).
      2. Insert pending Donation row to obtain donation_id.
      3. Upload each file via mediaflux.create_asset.
      4. On any failure: destroy all created assets, mark donation failed,
         release the reservation. Re-raise the original exception.
      5. On full success: mark donation complete with asset ids, return response.
    """
    if not await reserve_code(session, code=code):
        raise CodeUnavailable(code)

    submitted_at = datetime.now(timezone.utc)
    donation = Donation(
        code=code,
        status=DonationStatus.pending,
        submitted_at=submitted_at,
        client_ip_hash=client_ip_hash,
        consent_version=consent_version,
    )
    session.add(donation)
    await session.flush()  # populate donation.id without committing yet
    assert donation.id is not None

    namespace = _build_namespace(namespace_root, code, submitted_at, donation.id)
    created_ids: list[str] = []
    results: list[DonateResult] = []
    try:
        for f in files:
            md = DonorMetadata(
                donor_code=code,
                consent_version=consent_version,
                consent_accepted_at=consent_accepted_at,
                submitted_at=submitted_at,
                client_ip_hash=client_ip_hash,
                source_filename=f.filename,
                app_version=app_version,
            )
            asset_id = await mediaflux.create_asset(
                f.path, namespace=namespace, name=f.filename, metadata=md
            )
            created_ids.append(asset_id)
            results.append(DonateResult(filename=f.filename, asset_id=asset_id, status="ok"))
    except Exception:
        # Rollback: destroy any partial assets, release the reservation, mark failed.
        for asset_id in created_ids:
            try:
                await mediaflux.destroy_asset(asset_id)
            except Exception:
                # Best-effort; orphan ids remain referenced via audit log if needed.
                pass
        donation.status = DonationStatus.failed
        donation.completed_at = datetime.now(timezone.utc)
        session.add(donation)
        await _release_code(session, code=code)
        raise

    donation.status = DonationStatus.complete
    donation.completed_at = datetime.now(timezone.utc)
    donation.asset_ids_json = json.dumps(created_ids)
    session.add(donation)

    return DonationResponse(donation_id=donation.id, results=results)
