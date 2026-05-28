from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.mediaflux.client import AtermMediafluxClient
from app.mediaflux.exceptions import (
    MediafluxAssetCreateError,
    MediafluxAuthError,
    MediafluxTransportError,
)
from app.mediaflux.metadata import DonorMetadata


def _md(name="x.json") -> DonorMetadata:
    return DonorMetadata(
        donor_code="abc",
        consent_version="v1",
        consent_accepted_at=datetime.now(timezone.utc),
        submitted_at=datetime.now(timezone.utc),
        client_ip_hash="h",
        source_filename=name,
        app_version="dev",
    )


@pytest.fixture
def jar(tmp_path):
    j = tmp_path / "aterm.jar"
    j.write_bytes(b"")  # AtermMediafluxClient checks the path exists
    return j


@pytest.mark.asyncio
async def test_create_asset_invokes_aterm_and_parses_id(jar, tmp_path, monkeypatch):
    f = tmp_path / "x.json"
    f.write_bytes(b"{}")

    captured: dict = {}

    async def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return SimpleNamespace(returncode=0, stdout=b":id 12345\n", stderr=b"")

    monkeypatch.setattr("app.mediaflux.client.anyio_run_process", fake_run)

    client = AtermMediafluxClient(jar_path=jar, host="h", port=443, token="t")
    asset_id = await client.create_asset(
        f, namespace="/ns", name="x.json", metadata=_md(), collection_id=99
    )

    assert asset_id == "12345"
    joined = " ".join(captured["cmd"])
    assert "asset.create" in joined
    assert ":namespace /ns" in joined
    assert ":name x.json" in joined
    assert ":description donor_code=abc" in joined  # render_description output
    assert ":collection 99" in joined
    assert str(f) in joined
    # The legacy :meta block must NOT be sent (server may not have the schema).
    assert ":meta" not in joined


@pytest.mark.asyncio
async def test_create_asset_omits_collection_when_not_set(jar, tmp_path, monkeypatch):
    """When collection_id is None, no :collection arg is added."""
    f = tmp_path / "x.json"
    f.write_bytes(b"{}")
    captured: dict = {}

    async def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return SimpleNamespace(returncode=0, stdout=b":id 7\n", stderr=b"")

    monkeypatch.setattr("app.mediaflux.client.anyio_run_process", fake_run)
    client = AtermMediafluxClient(jar_path=jar, host="h", port=443, token="t")
    await client.create_asset(f, namespace="/ns", name="x.json", metadata=_md())
    assert ":collection" not in " ".join(captured["cmd"])


@pytest.mark.asyncio
async def test_create_asset_raises_auth_error_on_auth_failure(jar, tmp_path, monkeypatch):
    f = tmp_path / "x.json"
    f.write_bytes(b"{}")

    async def fake_run(cmd, **kw):
        return SimpleNamespace(
            returncode=1, stdout=b"", stderr=b"ERROR: authentication failed"
        )

    monkeypatch.setattr("app.mediaflux.client.anyio_run_process", fake_run)

    client = AtermMediafluxClient(jar_path=jar, host="h", port=443, token="t")
    with pytest.raises(MediafluxAuthError):
        await client.create_asset(f, namespace="/ns", name="x.json", metadata=_md())


@pytest.mark.asyncio
async def test_create_asset_raises_transport_on_network_error(jar, tmp_path, monkeypatch):
    f = tmp_path / "x.json"
    f.write_bytes(b"{}")

    async def fake_run(cmd, **kw):
        return SimpleNamespace(
            returncode=2, stdout=b"", stderr=b"java.net.ConnectException: refused"
        )

    monkeypatch.setattr("app.mediaflux.client.anyio_run_process", fake_run)

    client = AtermMediafluxClient(jar_path=jar, host="h", port=443, token="t")
    with pytest.raises(MediafluxTransportError):
        await client.create_asset(f, namespace="/ns", name="x.json", metadata=_md())


@pytest.mark.asyncio
async def test_create_asset_raises_generic_on_other_error(jar, tmp_path, monkeypatch):
    f = tmp_path / "x.json"
    f.write_bytes(b"{}")

    async def fake_run(cmd, **kw):
        return SimpleNamespace(returncode=3, stdout=b"", stderr=b"unknown problem")

    monkeypatch.setattr("app.mediaflux.client.anyio_run_process", fake_run)

    client = AtermMediafluxClient(jar_path=jar, host="h", port=443, token="t")
    with pytest.raises(MediafluxAssetCreateError):
        await client.create_asset(f, namespace="/ns", name="x.json", metadata=_md())


@pytest.mark.asyncio
async def test_destroy_asset_swallows_errors(jar, monkeypatch):
    async def fake_run(cmd, **kw):
        return SimpleNamespace(returncode=1, stdout=b"", stderr=b"oops")

    monkeypatch.setattr("app.mediaflux.client.anyio_run_process", fake_run)

    client = AtermMediafluxClient(jar_path=jar, host="h", port=443, token="t")
    # Should NOT raise.
    await client.destroy_asset("123")


@pytest.mark.asyncio
async def test_create_asset_missing_jar_raises(tmp_path):
    client = AtermMediafluxClient(
        jar_path=tmp_path / "missing.jar", host="h", port=443, token="t"
    )
    with pytest.raises(MediafluxTransportError):
        await client.create_asset(
            Path("/dev/null"), namespace="/ns", name="x.json", metadata=_md()
        )
