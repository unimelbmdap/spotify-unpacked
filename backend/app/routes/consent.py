from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings
from app.consent import load_consent_text
from app.deps import get_settings
from app.schemas import ConsentResponse

router = APIRouter(prefix="/api", tags=["consent"])


@router.get("/consent", response_model=ConsentResponse)
def consent(settings: Settings = Depends(get_settings)) -> ConsentResponse:
    try:
        text = load_consent_text(settings.consent_dir, settings.consent_version)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail="Consent text not found") from exc
    return ConsentResponse(version=settings.consent_version, text=text)
