import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import Settings
from app.deps import get_db, get_settings, require_admin
from app.models import AuditEvent, CodeStatus, Donation
from app.schemas import (
    AuditEventResponse,
    CodeCreateRequest,
    CodeReloadResponse,
    CodeResponse,
    CodeUpdateRequest,
    DonationListItem,
)
from app.services import codes as codes_service

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _to_response(c) -> CodeResponse:
    return CodeResponse(
        code=c.code,
        status=c.status.value,
        max_uses=c.max_uses,
        uses=c.uses,
        created_at=c.created_at,
        admin_label=c.admin_label,
    )


@router.post("/codes", response_model=list[CodeResponse], status_code=status.HTTP_201_CREATED)
async def create_codes(req: CodeCreateRequest, db: AsyncSession = Depends(get_db)):
    new_codes = await codes_service.generate_codes(
        db, count=req.count, max_uses=req.max_uses, admin_label=req.admin_label
    )
    await db.commit()
    return [_to_response(c) for c in new_codes]


@router.post("/codes/reload", response_model=CodeReloadResponse)
async def reload_codes(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    path = settings.participant_codes_file
    if path is None or not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="No participant codes file configured or file missing",
        )
    summary, _errors = await codes_service.load_codes_from_file(db, path)
    await db.commit()
    return CodeReloadResponse(**summary)


@router.get("/codes", response_model=list[CodeResponse])
async def list_codes(db: AsyncSession = Depends(get_db)):
    rows = await codes_service.list_codes(db)
    return [_to_response(c) for c in rows]


@router.patch("/codes/{code}", response_model=CodeResponse)
async def patch_code(code: str, req: CodeUpdateRequest, db: AsyncSession = Depends(get_db)):
    from app.models import ParticipantCode

    code = codes_service.normalise_code(code)
    updated = None
    if req.status == "revoked":
        updated = await codes_service.revoke_code(db, code=code)
    if req.max_uses is not None or req.admin_label is not None:
        updated = await codes_service.update_code(
            db, code=code, max_uses=req.max_uses, admin_label=req.admin_label
        ) or updated
    if updated is None:
        # Either the code doesn't exist, or no fields were given.
        existing = await db.get(ParticipantCode, code)
        if existing is None:
            raise HTTPException(status_code=404, detail="Unknown code")
        updated = existing
    if req.status == "active" and updated.status == CodeStatus.revoked:
        # Allow re-activation.
        updated.status = CodeStatus.active
        db.add(updated)
    await db.commit()
    await db.refresh(updated)
    return _to_response(updated)


@router.get("/donations", response_model=list[DonationListItem])
async def list_donations(
    code: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Donation).order_by(Donation.submitted_at.desc())
    if code is not None:
        stmt = stmt.where(Donation.code == code)
    rows = (await db.exec(stmt)).all()
    return [
        DonationListItem(
            id=d.id,
            code=d.code,
            status=d.status.value,
            submitted_at=d.submitted_at,
            completed_at=d.completed_at,
            consent_version=d.consent_version,
            storage_path=d.storage_path,
            synced_at=d.synced_at,
            mediaflux_asset_id=d.mediaflux_asset_id,
            asset_ids=json.loads(d.asset_ids_json) if d.asset_ids_json else [],
        )
        for d in rows
    ]


@router.get("/audit", response_model=list[AuditEventResponse])
async def list_audit(
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    limit = max(1, min(limit, 1000))
    rows = (
        await db.exec(select(AuditEvent).order_by(AuditEvent.ts.desc()).limit(limit))
    ).all()
    return [
        AuditEventResponse(
            id=e.id,
            ts=e.ts,
            kind=e.kind,
            code=e.code,
            client_ip_hash=e.client_ip_hash,
            detail_json=e.detail_json,
        )
        for e in rows
    ]
