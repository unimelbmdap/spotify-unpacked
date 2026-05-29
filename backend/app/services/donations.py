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


def _build_bundle_name(code: str, ts: datetime, donation_id: int) -> str:
    """Compose a unique, prefix-sortable asset name for one donation bundle.

    Format: `donation_<code>__<YYYYMMDD-HHMMSS>__<donation_id>.zip` — sorts
    chronologically by donor and is trivially parseable later.

    The fixed `donation_` prefix matters: secrets.token_urlsafe can emit
    codes starting with `-` or `_`, and aterm's Tcl-like shell parser
    treats `:name -anything…` as "qualifier followed by another
    qualifier" and bails with "missing value for qualifier". The prefix
    guarantees the asset name always starts with an alphanumeric.
    """
    stamp = ts.strftime("%Y%m%d-%H%M%S")
    return f"donation_{_safe_code_for_path(code)}__{stamp}__{donation_id}.zip"


async def perform_donation(
    session: AsyncSession,
    *,
    mediaflux: MediafluxClient,
    namespace: str,
    code: str,
    consent_version: str,
    consent_accepted_at: datetime,
    client_ip_hash: str,
    app_version: str,
    bundle: UploadFile,
    original_filenames: list[str],
    collection_id: int | None = None,
) -> DonationResponse:
    """Execute a single donation transaction with all-or-fail semantics.

    The caller passes ONE bundle file (the route layer zips the donor's
    files together so each donation becomes a single Mediaflux asset).

    Steps:
      1. Atomic reservation of code use (rollback decrements on failure).
      2. Insert pending Donation row to obtain donation_id.
      3. Upload the bundle via mediaflux.create_asset — the asset is placed
         in `namespace` with a disambiguator-prefixed name and added as
         a member of `collection_id` if set.
      4. On failure: destroy the asset (best-effort), mark donation failed,
         release the reservation. Re-raise the original exception.
      5. On success: mark donation complete with the asset id, return.
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

    asset_name = _build_bundle_name(code, submitted_at, donation.id)
    md = DonorMetadata(
        donor_code=code,
        consent_version=consent_version,
        consent_accepted_at=consent_accepted_at,
        submitted_at=submitted_at,
        client_ip_hash=client_ip_hash,
        source_filename=",".join(original_filenames),
        app_version=app_version,
    )
    created_ids: list[str] = []
    try:
        asset_id = await mediaflux.create_asset(
            bundle.path,
            namespace=namespace,
            name=asset_name,
            metadata=md,
            collection_id=collection_id,
        )
        created_ids.append(asset_id)
        results = [
            DonateResult(filename=name, asset_id=asset_id, status="ok")
            for name in original_filenames
        ]
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
