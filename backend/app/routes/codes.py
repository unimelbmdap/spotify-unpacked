from fastapi import APIRouter, Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from app.deps import get_db
from app.ratelimit import validate_rate_limit
from app.schemas import CodeValidateRequest, CodeValidationResponse
from app.services.codes import is_code_valid

router = APIRouter(prefix="/api", tags=["codes"])


@router.post("/codes/validate", response_model=CodeValidationResponse)
@validate_rate_limit()
async def validate_code(
    request: Request,
    body: CodeValidateRequest,
    db: AsyncSession = Depends(get_db),
) -> CodeValidationResponse:
    """Public up-front check that a participant code can currently be used.

    Read-only convenience for the donate page; the authoritative reservation
    still happens at submit time. Takes the code in the POST body (not the URL)
    to keep codes out of access logs and browser history. Returns a plain
    ``{"valid": false}`` for unknown/revoked/exhausted/malformed codes alike
    (no enumeration signal).
    """
    return CodeValidationResponse(valid=await is_code_valid(db, body.code))
