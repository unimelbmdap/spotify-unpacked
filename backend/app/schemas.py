import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Used by both the donate endpoint and the admin code generator.
EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_REGEX = re.compile(r"\+?\d[\d\s().-]{6,}\d")


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ConsentResponse(BaseModel):
    version: str
    text: str


class CodeCreateRequest(BaseModel):
    count: int = Field(ge=1, le=1000)
    max_uses: int = Field(default=1, ge=1)
    admin_label: str | None = Field(default=None, max_length=200)


class CodeUpdateRequest(BaseModel):
    status: Literal["active", "revoked"] | None = None
    max_uses: int | None = Field(default=None, ge=1)
    admin_label: str | None = Field(default=None, max_length=200)


class CodeResponse(BaseModel):
    code: str
    status: str
    max_uses: int
    uses: int
    created_at: datetime
    admin_label: str | None


class DonateResult(BaseModel):
    filename: str
    asset_id: str | None
    status: Literal["ok", "failed"]
    detail: str | None = None


class DonationResponse(BaseModel):
    donation_id: int
    results: list[DonateResult]


class AuditEventResponse(BaseModel):
    id: int
    ts: datetime
    kind: str
    code: str | None
    client_ip_hash: str | None
    detail_json: str | None


class DonationListItem(BaseModel):
    id: int
    code: str
    status: str
    submitted_at: datetime
    completed_at: datetime | None
    consent_version: str
    storage_path: str | None
    synced_at: datetime | None
    mediaflux_asset_id: str | None
    # Legacy: assets ids from the pre-decoupling design; nullable for back-compat.
    asset_ids: list[str]


@dataclass
class AdminLabelHints:
    """Soft validation for admin-label PII shapes — used by the admin UI as a warning, not a hard reject."""

    looks_like_pii: bool
    reasons: list[str] = field(default_factory=list)

    @classmethod
    def from_label(cls, label: str | None) -> "AdminLabelHints":
        if not label:
            return cls(looks_like_pii=False)
        reasons: list[str] = []
        if EMAIL_REGEX.search(label):
            reasons.append("looks like an email address")
        if PHONE_REGEX.search(label):
            reasons.append("looks like a phone number")
        return cls(looks_like_pii=bool(reasons), reasons=reasons)
