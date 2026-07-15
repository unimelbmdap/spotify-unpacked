from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # HTTP
    app_allowed_origins: str = "http://localhost:5173"

    # Database
    database_url: str = "sqlite+aiosqlite:///./donations.db"

    # Privacy
    ip_hash_salt: str = Field(min_length=32)

    # Admin
    admin_username: str = "admin"
    admin_password: str = Field(min_length=8)
    # Secret for signing the /admin panel session cookie. Falls back to
    # IP_HASH_SALT when empty; set explicitly in production.
    admin_session_secret: str = ""

    # Consent
    consent_version: str = "v1.0"
    consent_dir: Path = Path("./consent")

    # Local storage for donation bundles.
    # Each donation lands here as `donation_<code>__<ts>__<id>.zip` plus a
    # sibling `.json` sidecar with the donor metadata. The directory is
    # mounted onto the host via docker-compose so the eventual sync job
    # (rclone / aterm script / whatever) can read it without going through
    # the FastAPI process.
    donations_storage_dir: Path = Path("./data/donations")

    # Mediaflux
    mediaflux_client: Literal["stub", "aterm"] = "stub"
    # Namespace assets are created in. The MDAP project is a *collection asset*
    # rather than a writable namespace, so this is normally the project's
    # parent namespace (e.g. "/projects") and grouping happens via
    # `mediaflux_collection_id` instead.
    mediaflux_namespace: str = "/projects"
    # Optional asset id of a Mediaflux collection. When set, every created
    # asset is added as a member of that collection — this is how we group
    # donations under a "donations" folder in Asset Finder without needing
    # to create sub-namespaces (which require server-admin privileges).
    mediaflux_collection_id: int | None = None
    mediaflux_host: str = "mediaflux.researchsoftware.unimelb.edu.au"
    mediaflux_port: int = 443
    mediaflux_token: str = ""
    aterm_jar_path: Path = Path("/opt/mediaflux/aterm.jar")

    # Participant-code whitelist seed file (CSV: `code,max_uses,label`).
    # Loaded/upserted into the participant_codes table at startup and via
    # POST /api/admin/codes/reload. Sits on the ./data volume so admins can
    # edit it on the host. Set to None to disable file-based seeding.
    participant_codes_file: Path | None = Path("./data/participant_codes.csv")

    # Upload limits
    max_files_per_request: int = 10
    max_bytes_per_file: int = 50 * 1024 * 1024
    max_bytes_per_request: int = 200 * 1024 * 1024
    rate_limit_donate: str = "5/minute"
    # Rate limit for the public code-validation endpoint. Kept stricter than
    # donate to blunt code-guessing since the endpoint reveals validity.
    rate_limit_validate: str = "20/minute"

    # Database backup
    # A scheduled `VACUUM INTO` snapshot of the SQLite DB. Snapshots are
    # timestamped and land in backup_dir; keeping backup_dir inside
    # donations_storage_dir (the default) means the existing mflux-sync loop
    # mirrors them to Mediaflux with no extra wiring. The temp file is written
    # to the DB's own parent dir (outside the synced tree) and atomically
    # renamed in, so the uploader never sees a partial file.
    backup_enabled: bool = True
    backup_interval_hours: float = Field(default=24.0, gt=0, allow_inf_nan=False)
    backup_dir: Path = Path("./data/donations/_db-backups")
    # Local snapshots to keep (0 = keep all). Older ones are pruned after each
    # successful backup so they can't fill the volume; this only affects the
    # local copy, since mflux-sync is upload-only and never deletes from
    # Mediaflux, where the full history is retained.
    backup_retention: int = Field(default=30, ge=0)

    @field_validator("participant_codes_file", mode="before")
    @classmethod
    def blank_codes_file_is_none(cls, v: object) -> object:
        # An empty/whitespace env value disables seeding; otherwise it would
        # coerce to Path(".") (a directory) and crash the startup loader.
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return v

    @field_validator("ip_hash_salt")
    @classmethod
    def salt_is_hex_like(cls, v: str) -> str:
        if any(c.isspace() for c in v):
            raise ValueError("IP_HASH_SALT must not contain whitespace")
        return v

    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.app_allowed_origins.split(",") if o.strip()]
