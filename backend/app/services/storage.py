import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StoredBundle:
    """Result of storing a donation bundle on disk."""

    bundle_path: Path
    sidecar_path: Path


def store_bundle(
    *,
    source_zip: Path,
    asset_name: str,
    sidecar: dict[str, Any],
    target_dir: Path,
) -> StoredBundle:
    """Atomically place a donation bundle into the storage directory.

    Layout:
        <target_dir>/<asset_name>           # the zip
        <target_dir>/<asset_name>.json      # sibling sidecar of donor metadata

    "Atomically" = write to a temp name then `os.replace`, so partial writes
    (crash, OOM, container restart mid-write) never leave a half-written
    file visible to the sync job.

    Temp files are staged in a sibling `.tmp/` dir *outside* `target_dir`
    rather than inside it. The Mediaflux sync recursively watches
    `target_dir` and has no file-exclude flag, so a partial `.tmp` file
    inside it (even under a dot-subdir, which is still scanned) could be
    uploaded mid-write. Staging outside the watched tree, but on the same
    filesystem (a sibling of `target_dir`), keeps the final `os.replace`
    into `target_dir` atomic.

    Caller is responsible for ensuring `asset_name` is unique inside
    `target_dir` (the donations service already includes donation_id +
    timestamp in the name).
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = target_dir.parent / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    final_zip = target_dir / asset_name
    final_json = target_dir / f"{asset_name}.json"
    tmp_zip = tmp_dir / f".{asset_name}.tmp"
    tmp_json = tmp_dir / f".{asset_name}.json.tmp"

    try:
        # Copy then rename — keeps the original temp file intact in case
        # the donor's source zip lives on a different filesystem than the
        # target dir.
        shutil.copyfile(source_zip, tmp_zip)
        tmp_json.write_text(
            json.dumps(sidecar, sort_keys=True, indent=2), encoding="utf-8"
        )
        os.replace(tmp_zip, final_zip)
        os.replace(tmp_json, final_json)
    except Exception:
        for p in (tmp_zip, tmp_json):
            p.unlink(missing_ok=True)
        raise

    return StoredBundle(bundle_path=final_zip, sidecar_path=final_json)
