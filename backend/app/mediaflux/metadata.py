from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DonorMetadata:
    donor_code: str
    consent_version: str
    consent_accepted_at: datetime
    submitted_at: datetime
    client_ip_hash: str
    source_filename: str
    app_version: str


def _escape(value: str) -> str:
    """Strip characters that would break aterm's command-line quoting.

    aterm uses double-quoted strings inside service-call arguments. We disallow
    embedded quotes and control characters. This is defence-in-depth — caller
    code already sanitises filenames separately, but the metadata renderer must
    never trust its inputs.
    """
    bad = '"\r\n\t<>'
    return "".join(c for c in value if c not in bad)


def render_meta_argument(md: DonorMetadata) -> str:
    """Render a `:meta < :donation:donor < … > >` fragment for an aterm command.

    See the Mediaflux service documentation for the XML-like service-call syntax.
    NOTE: This requires the `donation:donor` document type to be registered
    on the server (a server-admin / RCS operation). It is currently UNUSED
    by the production code path — see `render_description` for the v1
    workaround that doesn't need a custom doc-type.
    """
    fields = [
        ("donor_code", md.donor_code),
        ("consent_version", md.consent_version),
        ("consent_accepted_at", md.consent_accepted_at.isoformat()),
        ("submitted_at", md.submitted_at.isoformat()),
        ("client_ip_hash", md.client_ip_hash),
        ("source_filename", md.source_filename),
        ("app_version", md.app_version),
    ]
    inner = " ".join(f':{name} "{_escape(value)}"' for name, value in fields)
    return f":meta < :donation:donor < {inner} > >"


def render_description(md: DonorMetadata) -> str:
    """Render the donor metadata as a semicolon-separated key=value string for
    use as the asset's free-text description field.

    This is the v1 fallback for projects that don't have a custom
    `donation:donor` document type registered. Plain key=value;key=value
    keeps things human-readable in Asset Finder and trivially parseable.
    Avoids `"`, `\\`, `$`, `[`, `{` so the value is safe inside an
    aterm-quoted string with no escaping needed.
    """
    pairs = [
        ("donor_code", md.donor_code),
        ("consent_version", md.consent_version),
        ("consent_accepted_at", md.consent_accepted_at.isoformat()),
        ("submitted_at", md.submitted_at.isoformat()),
        ("client_ip_hash", md.client_ip_hash),
        ("source_filename", md.source_filename),
        ("app_version", md.app_version),
    ]
    return ";".join(f"{k}={_escape(v)}" for k, v in pairs)
