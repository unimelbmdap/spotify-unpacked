"""Bundle and report file naming.

The backend names each donation bundle
`donation_<code>__<YYYYMMDD-HHMMSS>__<id>.zip` (see
backend/app/services/donations.py::_build_bundle_name) and writes a sidecar
`<bundle>.json` beside it. Report artefacts reuse the bundle stem and append
the generator version so that regenerating at a new version never overwrites.
"""

import re
from dataclasses import dataclass
from pathlib import Path

# Anchored on the two double-underscore separators, not on the year, so it
# keeps working past 2026 and on any code the backend's _safe_code_for_path
# can produce ([A-Za-z0-9_-]).
_BUNDLE_RE = re.compile(
    r"^donation_(?P<code>[A-Za-z0-9_-]+?)__(?P<stamp>\d{8}-\d{6})__(?P<donation_id>\d+)\.zip$"
)

REPORT_SUFFIX = ".pdf"
COMPANION_SUFFIX = ".json"
FAILED_SUFFIX = ".failed.json"
CLAIM_SUFFIX = ".lock"


@dataclass(frozen=True)
class BundleName:
    code: str
    stamp: str
    donation_id: int
    stem: str  # bundle filename without .zip

    @property
    def zip_name(self) -> str:
        return f"{self.stem}.zip"

    @property
    def sidecar_name(self) -> str:
        return f"{self.stem}.zip.json"

    def versioned_stem(self, version: int) -> str:
        return f"{self.stem}__{version_tag(version)}"

    def report_name(self, version: int) -> str:
        return self.versioned_stem(version) + REPORT_SUFFIX

    def companion_name(self, version: int) -> str:
        return self.versioned_stem(version) + COMPANION_SUFFIX

    def failed_name(self, version: int) -> str:
        return self.versioned_stem(version) + FAILED_SUFFIX

    def claim_name(self, version: int) -> str:
        return self.versioned_stem(version) + CLAIM_SUFFIX

    def report_glob_any_version(self) -> str:
        return f"{self.stem}__v[0-9][0-9]*{REPORT_SUFFIX}"


def version_tag(version: int) -> str:
    """'v01', 'v02', ... zero-padded to two digits so listings sort."""
    return f"v{version:02d}"


def parse_bundle_name(path: Path | str) -> BundleName | None:
    """BundleName for a bundle path, or None if the filename is not a bundle."""
    name = Path(path).name
    match = _BUNDLE_RE.match(name)
    if not match:
        return None
    return BundleName(
        code=match.group("code"),
        stamp=match.group("stamp"),
        donation_id=int(match.group("donation_id")),
        stem=name[: -len(".zip")],
    )
