from abc import ABC, abstractmethod
from itertools import count
from pathlib import Path

from app.mediaflux.exceptions import MediafluxAssetCreateError
from app.mediaflux.metadata import DonorMetadata


class MediafluxClient(ABC):
    @abstractmethod
    async def create_asset(
        self,
        file_path: Path,
        *,
        namespace: str,
        name: str,
        metadata: DonorMetadata,
    ) -> str:
        """Create an asset, return its Mediaflux id."""

    @abstractmethod
    async def destroy_asset(self, asset_id: str) -> None:
        """Best-effort destroy. Implementations should log + swallow on failure."""


class StubMediafluxClient(MediafluxClient):
    """In-process stub for tests and local Docker dev (no real Mediaflux required)."""

    def __init__(self, *, fail_after: int | None = None) -> None:
        self._next_id = count(start=1000)
        self.created: list[str] = []
        self.destroyed: list[str] = []
        self._calls = 0
        self._fail_after = fail_after

    async def create_asset(
        self,
        file_path: Path,
        *,
        namespace: str,
        name: str,
        metadata: DonorMetadata,
    ) -> str:
        self._calls += 1
        if self._fail_after is not None and self._calls > self._fail_after:
            raise MediafluxAssetCreateError(f"stub failure on call {self._calls}")
        if not file_path.exists():
            raise MediafluxAssetCreateError(f"missing file: {file_path}")
        asset_id = str(next(self._next_id))
        self.created.append(asset_id)
        return asset_id

    async def destroy_asset(self, asset_id: str) -> None:
        self.destroyed.append(asset_id)
