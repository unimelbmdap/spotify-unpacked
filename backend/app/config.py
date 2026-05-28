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

    # Consent
    consent_version: str = "v1.0"
    consent_dir: Path = Path("./consent")

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

    # Upload limits
    max_files_per_request: int = 10
    max_bytes_per_file: int = 50 * 1024 * 1024
    max_bytes_per_request: int = 200 * 1024 * 1024
    rate_limit_donate: str = "5/minute"

    @field_validator("ip_hash_salt")
    @classmethod
    def salt_is_hex_like(cls, v: str) -> str:
        if any(c.isspace() for c in v):
            raise ValueError("IP_HASH_SALT must not contain whitespace")
        return v

    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.app_allowed_origins.split(",") if o.strip()]
