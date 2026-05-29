import io

import pytest
from fastapi.testclient import TestClient

from app.deps import get_settings, reset_mediaflux_client
from app.main import create_app


@pytest.fixture
def admin_headers():
    import base64

    creds = base64.b64encode(b"admin:hunter2hunter").decode()
    return {"Authorization": f"Basic {creds}", "X-Admin-Request": "1"}


@pytest.fixture
def client(monkeypatch, tmp_path):
    (tmp_path / "v1.0.md").write_text("CONSENT", encoding="utf-8")
    monkeypatch.setenv("IP_HASH_SALT", "x" * 64)
    monkeypatch.setenv("ADMIN_PASSWORD", "hunter2hunter")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path/'t.db'}")
    monkeypatch.setenv("CONSENT_DIR", str(tmp_path))
    monkeypatch.setenv("CONSENT_VERSION", "v1.0")
    monkeypatch.setenv("MEDIAFLUX_CLIENT", "stub")
    monkeypatch.setenv("MAX_BYTES_PER_FILE", str(1024))
    monkeypatch.setenv("MAX_BYTES_PER_REQUEST", str(2048))
    monkeypatch.setenv("MAX_FILES_PER_REQUEST", str(3))
    monkeypatch.setenv("RATE_LIMIT_DONATE", "100/minute")
    get_settings.cache_clear()
    from app import deps
    deps._engine_cache.clear()
    reset_mediaflux_client()

    app = create_app()
    with TestClient(app) as c:
        yield c


def _new_code(client, admin_headers, max_uses=1):
    [c] = client.post(
        "/api/admin/codes", headers=admin_headers, json={"count": 1, "max_uses": max_uses}
    ).json()
    return c["code"]


def _form(code, *, files):
    fields = [
        ("participant_code", (None, code)),
        ("consent_version", (None, "v1.0")),
        ("consent_accepted", (None, "true")),
        ("app_version", (None, "test-build")),
    ]
    for name, content in files:
        fields.append(("files", (name, io.BytesIO(content), "application/json")))
    return fields


def test_happy_path_201(client, admin_headers):
    code = _new_code(client, admin_headers)
    r = client.post(
        "/api/donate",
        files=_form(code, files=[("a.json", b'{"x":1}'), ("b.json", b'{"y":2}')]),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["donation_id"] >= 1
    assert [x["status"] for x in body["results"]] == ["ok", "ok"]


def test_unknown_code_401(client):
    r = client.post(
        "/api/donate",
        files=_form("nope", files=[("a.json", b'{}')]),
    )
    assert r.status_code == 401


def test_missing_consent_returns_409(client, admin_headers):
    code = _new_code(client, admin_headers)
    fields = [
        ("participant_code", (None, code)),
        ("consent_version", (None, "v0.0")),  # wrong
        ("consent_accepted", (None, "true")),
        ("app_version", (None, "test-build")),
        ("files", ("a.json", io.BytesIO(b'{}'), "application/json")),
    ]
    r = client.post("/api/donate", files=fields)
    assert r.status_code == 409


def test_consent_not_accepted_returns_400(client, admin_headers):
    code = _new_code(client, admin_headers)
    fields = [
        ("participant_code", (None, code)),
        ("consent_version", (None, "v1.0")),
        ("consent_accepted", (None, "false")),
        ("app_version", (None, "test-build")),
        ("files", ("a.json", io.BytesIO(b'{}'), "application/json")),
    ]
    r = client.post("/api/donate", files=fields)
    assert r.status_code == 400


def test_too_many_files_returns_413(client, admin_headers):
    code = _new_code(client, admin_headers)
    files = [(f"{i}.json", b'{}') for i in range(4)]
    r = client.post("/api/donate", files=_form(code, files=files))
    assert r.status_code == 413


def test_oversize_file_returns_413(client, admin_headers):
    code = _new_code(client, admin_headers)
    big = b"x" * 2000
    r = client.post("/api/donate", files=_form(code, files=[("a.json", big)]))
    assert r.status_code == 413


def test_non_json_extension_returns_400(client, admin_headers):
    code = _new_code(client, admin_headers)
    r = client.post("/api/donate", files=_form(code, files=[("a.txt", b'hi')]))
    assert r.status_code == 400


def test_code_already_used_401_on_retry(client, admin_headers):
    code = _new_code(client, admin_headers, max_uses=1)
    r1 = client.post("/api/donate", files=_form(code, files=[("a.json", b'{}')]))
    assert r1.status_code == 201
    r2 = client.post("/api/donate", files=_form(code, files=[("a.json", b'{}')]))
    assert r2.status_code == 401


def test_mediaflux_failure_returns_502_and_does_not_burn_use(client, admin_headers):
    """Inject a Mediaflux failure on the (single) bundle upload.

    With the bundle-per-donation design there is only one create_asset call
    per donation, so we use fail_after=0 to make that call fail. The
    contract being verified is: server returns 502, code is not burned,
    retry with the same code succeeds.
    """
    from app.mediaflux.client import StubMediafluxClient

    code = _new_code(client, admin_headers, max_uses=1)
    # Replace the cached client with one that fails on the first call.
    from app import deps
    deps._mediaflux_client = StubMediafluxClient(fail_after=0)

    r = client.post(
        "/api/donate",
        files=_form(code, files=[("a.json", b'{}'), ("b.json", b'{}')]),
    )
    assert r.status_code == 502, r.text

    # Reset to a working client and retry — code use was not burned.
    deps._mediaflux_client = StubMediafluxClient()
    r2 = client.post(
        "/api/donate",
        files=_form(code, files=[("a.json", b'{}'), ("b.json", b'{}')]),
    )
    assert r2.status_code == 201
