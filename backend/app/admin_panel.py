"""Browser admin panel (sqladmin) for managing the participant-code whitelist.

Mounted at ``/admin`` and separate from the JSON admin API under
``/api/admin``. Auth is a session login validated against the same
ADMIN_USERNAME/ADMIN_PASSWORD credentials; keep it behind the UoM-IP
allow-list at the reverse proxy just like the API.
"""

import hmac
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI
from sqladmin import Admin, ModelView, action
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.config import Settings
from app.deps import get_settings
from app.models import AuditEvent, Donation, ParticipantCode
from app.services.codes import _CODE_RE, load_codes_from_file, normalise_code


def authenticate_admin(username: str, password: str, settings: Settings) -> bool:
    """Constant-time check of a username/password pair against admin creds."""
    return hmac.compare_digest(username, settings.admin_username) and hmac.compare_digest(
        password, settings.admin_password
    )


def prepare_code_data(data: dict[str, Any], *, is_created: bool) -> dict[str, Any]:
    """Normalise + validate participant-code form data before it is saved.

    sqladmin writes straight to the table, bypassing the service layer, so we
    reapply the same rules here: trim + uppercase the code and enforce the
    format (on create AND edit, since the code is now editable), and fill
    server-managed fields on create. Raises ValueError on a malformed code so
    the bad row is never written.
    """
    if "code" in data and data["code"] is not None:
        data["code"] = normalise_code(str(data["code"]))
        if not _CODE_RE.fullmatch(data["code"]):
            raise ValueError("Code must be 5-32 characters of letters, digits, '-' or '_'.")
    if is_created:
        data.setdefault("uses", 0)
        data["created_at"] = datetime.now(timezone.utc)
    return data


class AdminAuth(AuthenticationBackend):
    def __init__(self, secret_key: str, settings: Settings) -> None:
        # SameSite=Strict so a logged-in admin's session cookie is not sent on
        # cross-site requests, mitigating CSRF on state-changing panel actions.
        super().__init__(secret_key=secret_key, same_site="strict")
        self._settings = settings

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = str(form.get("username", ""))
        password = str(form.get("password", ""))
        if authenticate_admin(username, password, self._settings):
            request.session.update({"admin": username})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return bool(request.session.get("admin"))


class ParticipantCodeAdmin(ModelView, model=ParticipantCode):
    name = "Participant Code"
    name_plural = "Participant Codes"
    icon = "fa-solid fa-ticket"
    column_list = [
        ParticipantCode.code,
        ParticipantCode.status,
        ParticipantCode.uses,
        ParticipantCode.max_uses,
        ParticipantCode.admin_label,
        ParticipantCode.created_at,
    ]
    column_searchable_list = [ParticipantCode.code, ParticipantCode.admin_label]
    column_sortable_list = [ParticipantCode.code, ParticipantCode.created_at, ParticipantCode.status]
    # `code` is a normal (unique) column now, so it shows and is editable.
    # `uses`/`created_at` are server-managed and deliberately left off the forms.
    form_create_rules = ["code", "status", "max_uses", "admin_label"]
    form_edit_rules = ["code", "status", "max_uses", "admin_label"]

    async def on_model_change(
        self, data: dict[str, Any], model: Any, is_created: bool, request: Request
    ) -> None:
        prepare_code_data(data, is_created=is_created)

    @action(
        name="reload_seed_file",
        label="Reload from seed file",
        confirmation_message="Re-import codes from the configured seed file?",
        add_in_detail=False,
        add_in_list=True,
    )
    async def reload_seed_file(self, request: Request) -> RedirectResponse:
        settings = get_settings()
        path = settings.participant_codes_file
        list_url = request.url_for("admin:list", identity=self.identity)
        if path is None or not path.is_file():
            return RedirectResponse(list_url)
        async with self.session_maker() as session:
            await load_codes_from_file(session, path)
            await session.commit()
        return RedirectResponse(list_url)


class _ReadOnlyView(ModelView):
    can_create = False
    can_edit = False
    can_delete = False
    can_view_details = True


class DonationAdmin(_ReadOnlyView, model=Donation):
    name = "Donation"
    name_plural = "Donations"
    icon = "fa-solid fa-box-archive"
    # synced_at / mediaflux_asset_id are intentionally omitted: v1 sync tracks
    # nothing in the DB, so they'd always render empty and mislead. status here
    # is the donation-write lifecycle (pending/stored/failed), not sync state.
    column_list = [
        Donation.id,
        Donation.code,
        Donation.status,
        Donation.submitted_at,
        Donation.storage_path,
    ]
    column_sortable_list = [Donation.id, Donation.submitted_at, Donation.status]


class AuditEventAdmin(_ReadOnlyView, model=AuditEvent):
    name = "Audit Event"
    name_plural = "Audit Events"
    icon = "fa-solid fa-list-check"
    column_list = [AuditEvent.id, AuditEvent.ts, AuditEvent.kind, AuditEvent.code]
    column_sortable_list = [AuditEvent.id, AuditEvent.ts, AuditEvent.kind]


def create_admin(app: FastAPI, engine: AsyncEngine, settings: Settings) -> Admin:
    """Mount the sqladmin panel on `app` and register the model views."""
    # Fall back to the IP-hash salt (already a required 32+ char secret) when a
    # dedicated session secret is not configured.
    secret = settings.admin_session_secret or settings.ip_hash_salt
    admin = Admin(
        app,
        engine,
        title="Donation Admin",
        authentication_backend=AdminAuth(secret_key=secret, settings=settings),
    )
    admin.add_view(ParticipantCodeAdmin)
    admin.add_view(DonationAdmin)
    admin.add_view(AuditEventAdmin)
    return admin
