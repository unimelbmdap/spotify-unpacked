import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import Settings
from app.consent import load_consent_text
from app.deps import (
    get_client_ip_hash,
    get_db,
    get_settings,
)
from app.ratelimit import donate_rate_limit
from app.schemas import DonationResponse
from app.services import audit
from app.services.codes import CODE_REGEX
from app.services.donations import (
    CodeUnavailable,
    UploadFile as ServiceUploadFile,
    perform_donation,
)

router = APIRouter(prefix="/api", tags=["donate"])

_CODE_RE = re.compile(CODE_REGEX)
_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9._-]")


def _sanitise_filename(name: str) -> str:
    name = name.strip().replace("\\", "/").split("/")[-1]
    return _FILENAME_SAFE.sub("_", name)[:200]


@router.post(
    "/donate",
    response_model=DonationResponse,
    status_code=status.HTTP_201_CREATED,
)
@donate_rate_limit()
async def donate(
    request: Request,
    participant_code: str = Form(...),
    consent_version: str = Form(...),
    consent_accepted: bool = Form(...),
    app_version: str = Form(...),
    files: list[UploadFile] = File(...),
    settings: Settings = Depends(get_settings),
    client_ip_hash: str = Depends(get_client_ip_hash),
    db: AsyncSession = Depends(get_db),
):
    # 1. Envelope checks (before reading file bytes).
    if not _CODE_RE.fullmatch(participant_code):
        await audit.record_event(
            db, kind="donate_reject", client_ip_hash=client_ip_hash,
            detail={"reason": "bad-code-format"},
        )
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid participant code")

    if not consent_accepted:
        raise HTTPException(status_code=400, detail="Consent must be accepted")

    if consent_version != settings.consent_version:
        raise HTTPException(status_code=409, detail="Consent version is out of date")

    if len(files) > settings.max_files_per_request:
        raise HTTPException(status_code=413, detail="Too many files in request")

    if any(not (f.filename or "").lower().endswith(".json") for f in files):
        raise HTTPException(status_code=400, detail="Only .json files are accepted")

    # Confirm consent text exists for the version (otherwise misconfigured).
    try:
        load_consent_text(settings.consent_dir, settings.consent_version)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail="Server consent text missing") from exc

    consent_accepted_at = datetime.now(timezone.utc)

    # 2. Stream files to disk with per-file/per-request size enforcement.
    streamed: list[tuple[str, Path, int]] = []  # (sanitised_name, path, size)
    total_bytes = 0
    chunk_size = 1024 * 1024
    with TemporaryDirectory(prefix="donate-") as tmpdir:
        tmp_root = Path(tmpdir)
        for idx, f in enumerate(files):
            name = _sanitise_filename(f.filename or f"file-{idx}.json")
            target = tmp_root / f"{idx:03d}_{name}"
            written = 0
            with target.open("wb") as out:
                while True:
                    chunk = await f.read(chunk_size)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > settings.max_bytes_per_file:
                        raise HTTPException(
                            status_code=413,
                            detail=f"File '{name}' exceeds per-file size limit",
                        )
                    total_bytes += len(chunk)
                    if total_bytes > settings.max_bytes_per_request:
                        raise HTTPException(
                            status_code=413,
                            detail="Request exceeds total size limit",
                        )
                    out.write(chunk)
            streamed.append((name, target, written))

        # 2b. Zip the streamed files into a single bundle so each donation
        # is one Mediaflux asset (one row in Asset Finder, atomic rollback).
        bundle_path = tmp_root / "bundle.zip"
        with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, src, _size in streamed:
                zf.write(src, arcname=name)
        bundle = ServiceUploadFile(
            filename="bundle.zip",
            path=bundle_path,
            size=bundle_path.stat().st_size,
        )
        original_filenames = [name for name, _, _ in streamed]

        # 3. Reserve + store bundle on disk + record (services.donations).
        # Mediaflux sync happens later via a separate offline job — keeps
        # the request path independent of Mediaflux availability.
        try:
            response = await perform_donation(
                db,
                storage_dir=settings.donations_storage_dir,
                code=participant_code,
                consent_version=consent_version,
                consent_accepted_at=consent_accepted_at,
                client_ip_hash=client_ip_hash,
                app_version=app_version,
                bundle=bundle,
                original_filenames=original_filenames,
            )
        except CodeUnavailable:
            await audit.record_event(
                db, kind="donate_reject", code=participant_code,
                client_ip_hash=client_ip_hash,
                detail={"reason": "code-unavailable"},
            )
            await db.commit()
            raise HTTPException(
                status_code=401, detail="Participant code is invalid or already used"
            )
        except OSError as exc:
            # Disk full, permission denied on storage_dir, etc.
            await audit.record_event(
                db, kind="donate_failed", code=participant_code,
                client_ip_hash=client_ip_hash,
                detail={"error": exc.__class__.__name__, "message": str(exc)},
            )
            await db.commit()
            raise HTTPException(
                status_code=502,
                detail="Could not store donation; your code has not been used. Please try again.",
            )

        await audit.record_event(
            db, kind="donate_ok", code=participant_code,
            client_ip_hash=client_ip_hash,
            detail={"donation_id": response.donation_id, "files": len(original_filenames)},
        )
        await db.commit()
        return response
