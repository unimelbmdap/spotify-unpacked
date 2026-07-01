import re
from dataclasses import dataclass
from dataclasses import asdict as _dataclass_asdict
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import update
from sqlmodel.ext.asyncio.session import AsyncSession

from app.mediaflux.metadata import DonorMetadata
from app.models import CodeStatus, Donation, DonationStatus, ParticipantCode
from app.schemas import DonateResult, DonationResponse
from app.services.codes import normalise_code
from app.services.storage import store_bundle

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
    code = normalise_code(code)
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
    code = normalise_code(code)
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

    The fixed `donation_` prefix matters for the eventual sync to Mediaflux:
    secrets.token_urlsafe can emit codes starting with `-` or `_`, and
    aterm's Tcl-like shell parser treats `:name -anything…` as "qualifier
    followed by another qualifier" and bails with "missing value for
    qualifier". The prefix guarantees the asset name always starts with
    an alphanumeric.
    """
    stamp = ts.strftime("%Y%m%d-%H%M%S")
    return f"donation_{_safe_code_for_path(code)}__{stamp}__{donation_id}.zip"


def _sidecar_dict(md: DonorMetadata, original_filenames: list[str]) -> dict:
    """Sidecar JSON written next to each bundle. Self-contained so the
    sync job doesn't need to query the backend's SQLite to know what
    metadata to attach to the Mediaflux asset.
    """
    d = _dataclass_asdict(md)
    # ISO-8601 datetimes for portability.
    d["consent_accepted_at"] = md.consent_accepted_at.isoformat()
    d["submitted_at"] = md.submitted_at.isoformat()
    d["original_filenames"] = original_filenames
    return d


async def perform_donation(
    session: AsyncSession,
    *,
    storage_dir: Path,
    code: str,
    consent_version: str,
    consent_accepted_at: datetime,
    client_ip_hash: str,
    app_version: str,
    bundle: UploadFile,
    original_filenames: list[str],
) -> DonationResponse:
    """Execute a single donation transaction.

    The donate flow is now decoupled from Mediaflux: we just stash the
    zip on disk and record it in SQLite. A separate sync job (rclone /
    aterm script / whatever) is responsible for getting the bundle onto
    Mediaflux later, which is when `synced_at` and `mediaflux_asset_id`
    get populated.

    Steps:
      1. Atomic reservation of code use (rollback decrements on failure).
      2. Insert pending Donation row to obtain donation_id.
      3. Store the bundle + sidecar manifest on disk atomically.
      4. Mark the donation `stored` with the storage_path.
      5. On any failure: release the code, mark failed, re-raise.
    """
    code = normalise_code(code)
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
    try:
        stored = store_bundle(
            source_zip=bundle.path,
            asset_name=asset_name,
            sidecar=_sidecar_dict(md, original_filenames),
            target_dir=storage_dir,
        )
    except Exception:
        donation.status = DonationStatus.failed
        donation.completed_at = datetime.now(timezone.utc)
        session.add(donation)
        await _release_code(session, code=code)
        raise

    donation.status = DonationStatus.stored
    donation.completed_at = datetime.now(timezone.utc)
    donation.storage_path = str(stored.bundle_path)
    session.add(donation)

    # `asset_id` in the response now refers to the donation id (a stable
    # backend-side identifier) — there is no Mediaflux asset id yet. The
    # sync job will populate `Donation.mediaflux_asset_id` later.
    results = [
        DonateResult(filename=name, asset_id=str(donation.id), status="ok")
        for name in original_filenames
    ]
    return DonationResponse(donation_id=donation.id, results=results)
