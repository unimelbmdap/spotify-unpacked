import base64
import hashlib
import hmac

from fastapi import HTTPException


def hash_ip(ip: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()


def check_basic_auth(authorization_header: str | None, username: str, password: str) -> bool:
    if not authorization_header or not authorization_header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(authorization_header[6:].strip()).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return False
    if ":" not in decoded:
        return False
    user, _, pw = decoded.partition(":")
    return hmac.compare_digest(user, username) and hmac.compare_digest(pw, password)


def require_admin_csrf_header(headers: dict) -> None:
    """Raise 400 if the X-Admin-Request header is not present.

    Header keys are compared case-insensitively (FastAPI gives us a Headers object
    that already lowercases). For unit tests we accept a plain dict — normalise here.
    """
    normalised = {k.lower(): v for k, v in headers.items()}
    if normalised.get("x-admin-request") != "1":
        raise HTTPException(status_code=400, detail="Missing X-Admin-Request header")
