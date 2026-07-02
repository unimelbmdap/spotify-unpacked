from dataclasses import dataclass


@dataclass(frozen=True)
class CodeSeedEntry:
    """One row from the participant-code seed file.

    `code` is stored as read here; normalisation (trim + uppercase) happens
    in `codes.import_codes` so the seed format stays forgiving.
    """

    code: str
    max_uses: int = 10  # default is a generous safeguard, not a one-shot lock
    admin_label: str | None = None


def parse_seed_csv(text: str) -> tuple[list[CodeSeedEntry], list[str]]:
    """Parse the whitelist seed file into entries plus a list of error strings.

    Format (one code per line): ``code,max_uses,label``
      - ``max_uses`` (default 10) and ``label`` are optional.
      - Lines starting with ``#`` and blank lines are ignored.
      - A label may itself contain commas (everything after the second comma).
      - A malformed line (empty code, non-integer max_uses) is skipped and
        reported in the returned errors list rather than raising.
    """
    entries: list[CodeSeedEntry] = []
    errors: list[str] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # maxsplit=2 keeps any commas inside the label intact.
        parts = line.split(",", 2)
        code = parts[0].strip()
        if not code:
            errors.append(f"line {lineno}: empty code")
            continue

        max_uses = 10
        if len(parts) >= 2 and parts[1].strip() != "":
            raw_max = parts[1].strip()
            try:
                max_uses = int(raw_max)
            except ValueError:
                errors.append(f"line {lineno}: max_uses '{raw_max}' is not an integer")
                continue

        admin_label: str | None = None
        if len(parts) >= 3:
            label = parts[2].strip()
            admin_label = label or None

        entries.append(CodeSeedEntry(code=code, max_uses=max_uses, admin_label=admin_label))
    return entries, errors
