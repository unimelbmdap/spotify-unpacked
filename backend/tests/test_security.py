import pytest

from app.security import check_basic_auth, hash_ip, require_admin_csrf_header


def test_hash_ip_is_deterministic_with_same_salt():
    assert hash_ip("203.0.113.4", salt="abc") == hash_ip("203.0.113.4", salt="abc")


def test_hash_ip_changes_with_salt():
    assert hash_ip("203.0.113.4", salt="abc") != hash_ip("203.0.113.4", salt="xyz")


def test_check_basic_auth_accepts_correct_credentials():
    import base64

    creds = base64.b64encode(b"admin:hunter2hunter").decode()
    assert check_basic_auth(f"Basic {creds}", "admin", "hunter2hunter") is True


def test_check_basic_auth_rejects_wrong_password():
    import base64

    creds = base64.b64encode(b"admin:wrong").decode()
    assert check_basic_auth(f"Basic {creds}", "admin", "hunter2hunter") is False


def test_check_basic_auth_rejects_missing_header():
    assert check_basic_auth(None, "admin", "x") is False


def test_check_basic_auth_rejects_garbage():
    assert check_basic_auth("Bearer foo", "admin", "x") is False


def test_csrf_header_accepts_when_present():
    require_admin_csrf_header({"x-admin-request": "1"})  # no raise


def test_csrf_header_rejects_when_missing():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as ei:
        require_admin_csrf_header({})
    assert ei.value.status_code == 400
