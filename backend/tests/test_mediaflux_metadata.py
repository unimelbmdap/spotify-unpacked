from datetime import datetime, timezone

from app.mediaflux.metadata import DonorMetadata, render_meta_argument


def test_render_meta_includes_all_fields():
    md = DonorMetadata(
        donor_code="abc123",
        consent_version="v1.0",
        consent_accepted_at=datetime(2026, 4, 30, 10, 0, tzinfo=timezone.utc),
        submitted_at=datetime(2026, 4, 30, 10, 5, tzinfo=timezone.utc),
        client_ip_hash="deadbeef",
        source_filename="StreamingHistory.json",
        app_version="abc123sha",
    )
    rendered = render_meta_argument(md)
    assert ":meta < :donation:donor <" in rendered
    assert ":donor_code \"abc123\"" in rendered
    assert ":consent_version \"v1.0\"" in rendered
    assert ":source_filename \"StreamingHistory.json\"" in rendered
    assert ":app_version \"abc123sha\"" in rendered
    assert "2026-04-30T10:00:00+00:00" in rendered


def test_render_meta_escapes_quotes_in_filename():
    md = DonorMetadata(
        donor_code="abc",
        consent_version="v1",
        consent_accepted_at=datetime(2026, 4, 30, tzinfo=timezone.utc),
        submitted_at=datetime(2026, 4, 30, tzinfo=timezone.utc),
        client_ip_hash="h",
        source_filename='evil"name.json',
        app_version="x",
    )
    rendered = render_meta_argument(md)
    assert 'evil"name.json' not in rendered  # the raw quote must be escaped/stripped
    assert "evil" in rendered  # but the rest of the name survives
