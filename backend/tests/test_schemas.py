import pytest
from pydantic import ValidationError

from app.schemas import (
    AdminLabelHints,
    CodeCreateRequest,
    CodeResponse,
    DonateResult,
    DonationResponse,
)


def test_code_create_request_rejects_negative_max_uses():
    with pytest.raises(ValidationError):
        CodeCreateRequest(count=1, max_uses=0)


def test_code_create_request_rejects_huge_count():
    with pytest.raises(ValidationError):
        CodeCreateRequest(count=10_000)


def test_code_response_serialises():
    from datetime import datetime, timezone

    r = CodeResponse(
        code="abc",
        status="active",
        max_uses=1,
        uses=0,
        created_at=datetime.now(timezone.utc),
        admin_label=None,
    )
    assert r.code == "abc"


def test_admin_label_hint_warns_on_email_shape():
    hints = AdminLabelHints.from_label("contact alice@example.com about cohort 2")
    assert hints.looks_like_pii is True
    assert "email" in hints.reasons[0]


def test_admin_label_hint_clean_label():
    hints = AdminLabelHints.from_label("cohort 2 — wave A")
    assert hints.looks_like_pii is False


def test_donation_response_round_trip():
    resp = DonationResponse(
        donation_id=42,
        results=[DonateResult(filename="x.json", asset_id="123", status="ok")],
    )
    assert resp.donation_id == 42
