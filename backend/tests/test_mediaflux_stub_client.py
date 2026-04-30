from datetime import datetime, timezone

import pytest

from app.mediaflux.client import StubMediafluxClient
from app.mediaflux.exceptions import MediafluxAssetCreateError
from app.mediaflux.metadata import DonorMetadata


def _md() -> DonorMetadata:
    return DonorMetadata(
        donor_code="abc",
        consent_version="v1",
        consent_accepted_at=datetime.now(timezone.utc),
        submitted_at=datetime.now(timezone.utc),
        client_ip_hash="h",
        source_filename="x.json",
        app_version="dev",
    )


@pytest.mark.asyncio
async def test_stub_returns_sequential_ids(tmp_path):
    f = tmp_path / "x.json"
    f.write_text("{}", encoding="utf-8")
    client = StubMediafluxClient()
    a = await client.create_asset(f, namespace="/ns", name="x.json", metadata=_md())
    b = await client.create_asset(f, namespace="/ns", name="x.json", metadata=_md())
    assert a != b
    assert client.created == [a, b]


@pytest.mark.asyncio
async def test_stub_destroy_removes_from_log(tmp_path):
    f = tmp_path / "x.json"
    f.write_text("{}", encoding="utf-8")
    client = StubMediafluxClient()
    a = await client.create_asset(f, namespace="/ns", name="x.json", metadata=_md())
    await client.destroy_asset(a)
    assert a in client.destroyed


@pytest.mark.asyncio
async def test_stub_can_be_configured_to_fail(tmp_path):
    f = tmp_path / "x.json"
    f.write_text("{}", encoding="utf-8")
    client = StubMediafluxClient(fail_after=1)
    await client.create_asset(f, namespace="/ns", name="x.json", metadata=_md())
    with pytest.raises(MediafluxAssetCreateError):
        await client.create_asset(f, namespace="/ns", name="x.json", metadata=_md())
