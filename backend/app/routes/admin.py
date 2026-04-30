from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.deps import get_db, require_admin
from app.models import CodeStatus
from app.schemas import (
    CodeCreateRequest,
    CodeResponse,
    CodeUpdateRequest,
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


@router.get("/codes", response_model=list[CodeResponse])
async def list_codes(db: AsyncSession = Depends(get_db)):
    rows = await codes_service.list_codes(db)
    return [_to_response(c) for c in rows]


@router.patch("/codes/{code}", response_model=CodeResponse)
async def patch_code(code: str, req: CodeUpdateRequest, db: AsyncSession = Depends(get_db)):
    from app.models import ParticipantCode

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
