"""Generator version.

Bump when the rendered output changes in a way that warrants new reports for
future donations. Existing reports are never regenerated automatically: the
version is part of every output filename, and the worker treats a bundle as
done once a report at any version exists (see worker.scan).
"""

GENERATOR_VERSION = 1

# Layout of the companion JSON written beside each PDF (companion.py). Bump
# independently of GENERATOR_VERSION when keys are added, removed or renamed.
COMPANION_SCHEMA = 1
