from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class CodeStatus(str, Enum):
    active = "active"
    revoked = "revoked"


class DonationStatus(str, Enum):
    pending = "pending"
    complete = "complete"
    failed = "failed"


class ParticipantCode(SQLModel, table=True):
    __tablename__ = "participant_codes"

    code: str = Field(primary_key=True)
    status: CodeStatus = Field(default=CodeStatus.active)
    max_uses: int = Field(default=1)
    uses: int = Field(default=0)
    created_at: datetime
    admin_label: str | None = Field(default=None)  # MUST NOT contain PII


class Donation(SQLModel, table=True):
    __tablename__ = "donations"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(foreign_key="participant_codes.code", index=True)
    status: DonationStatus = Field(default=DonationStatus.pending)
    submitted_at: datetime
    completed_at: datetime | None = Field(default=None)
    client_ip_hash: str
    consent_version: str
    asset_ids_json: str | None = Field(default=None)


class AuditEvent(SQLModel, table=True):
    __tablename__ = "audit_events"

    id: int | None = Field(default=None, primary_key=True)
    ts: datetime
    kind: str = Field(index=True)
    code: str | None = Field(default=None, index=True)
    client_ip_hash: str | None = Field(default=None)
    detail_json: str | None = Field(default=None)
