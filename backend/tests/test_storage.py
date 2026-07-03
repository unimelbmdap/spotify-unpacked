from pathlib import Path

from app.services.storage import store_bundle


def test_temp_files_are_staged_outside_target_dir(tmp_path, monkeypatch):
    """The sync watches target_dir; partial .tmp files must never appear there.

    We spy on os.replace to capture where each temp file was staged before the
    atomic rename into target_dir, and assert none were staged anywhere inside
    the recursively-watched donations tree (target/.tmp would still be scanned,
    so `!= target` is too weak).
    """
    import app.services.storage as storage

    src = tmp_path / "src.zip"
    src.write_bytes(b"PK\x03\x04 fake zip bytes")
    target = tmp_path / "donations"

    staged_parents = []
    real_replace = storage.os.replace

    def spy_replace(a, b):
        staged_parents.append(Path(a).parent)
        return real_replace(a, b)

    monkeypatch.setattr(storage.os, "replace", spy_replace)

    result = store_bundle(
        source_zip=src,
        asset_name="donation_X__20260101-000000__1.zip",
        sidecar={"donor_code": "X"},
        target_dir=target,
    )

    # os.replace ran for both zip + sidecar, and neither was staged inside the
    # watched donations tree.
    assert staged_parents, "expected os.replace to be called"
    assert all(not parent.is_relative_to(target) for parent in staged_parents)

    # end state: only the final files live in the watched dir, no dotfiles/.tmp
    names = sorted(p.name for p in target.iterdir())
    assert names == [
        "donation_X__20260101-000000__1.zip",
        "donation_X__20260101-000000__1.zip.json",
    ]
    assert result.bundle_path.exists() and result.sidecar_path.exists()
