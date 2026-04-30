class MediafluxError(Exception):
    """Base class for Mediaflux client errors."""


class MediafluxAuthError(MediafluxError):
    """Token rejected or auth failed."""


class MediafluxQuotaExceeded(MediafluxError):
    """Project quota would be exceeded by this upload."""


class MediafluxTransportError(MediafluxError):
    """Network / transport-level failure talking to Mediaflux."""


class MediafluxAssetCreateError(MediafluxError):
    """`asset.create` failed for a non-auth, non-quota reason."""
