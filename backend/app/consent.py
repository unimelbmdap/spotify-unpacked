from pathlib import Path


def load_consent_text(consent_dir: Path, version: str) -> str:
    p = consent_dir / f"{version}.md"
    return p.read_text(encoding="utf-8")
