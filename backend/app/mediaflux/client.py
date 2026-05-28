import logging
import re
from abc import ABC, abstractmethod
from itertools import count
from pathlib import Path

from anyio import run_process as anyio_run_process

from app.mediaflux.exceptions import (
    MediafluxAssetCreateError,
    MediafluxAuthError,
    MediafluxTransportError,
)
from app.mediaflux.metadata import DonorMetadata

log = logging.getLogger(__name__)

_ASSET_ID_RE = re.compile(r":id\s+(\d+)")


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


class AtermMediafluxClient(MediafluxClient):
    """Mediaflux client backed by the Java `aterm` CLI invoked via anyio.run_process.

    The Java jar is downloaded into the Docker image at /opt/mediaflux/aterm.jar
    (see the Dockerfile in Task 22).
    """

    def __init__(
        self,
        *,
        jar_path: Path,
        host: str,
        port: int,
        token: str,
        timeout_seconds: int = 600,
        java_executable: str = "java",
    ) -> None:
        self.jar_path = jar_path
        self.host = host
        self.port = port
        self.token = token
        self.timeout_seconds = timeout_seconds
        self.java_executable = java_executable

    def _base_cmd(self) -> list[str]:
        return [
            self.java_executable,
            "-jar",
            str(self.jar_path),
            "nogui",
            f"--server={self.host}",
            f"--port={self.port}",
            "--encrypt",
            f"--token={self.token}",
        ]

    async def _run(self, args: list[str]) -> str:
        if not self.jar_path.exists():
            raise MediafluxTransportError(f"aterm jar not found at {self.jar_path}")
        cmd = self._base_cmd() + args
        log_cmd = " ".join(c if "--token=" not in c else "--token=***" for c in cmd)
        log.info("running aterm: %s", log_cmd)
        try:
            result = await anyio_run_process(cmd, timeout=self.timeout_seconds, check=False)
        except Exception as exc:  # network failure inside anyio
            raise MediafluxTransportError(str(exc)) from exc
        if result.returncode != 0:
            stderr = (result.stderr or b"").decode("utf-8", errors="replace")
            if "authentication" in stderr.lower() or "unauthor" in stderr.lower():
                raise MediafluxAuthError(stderr.strip())
            if "ConnectException" in stderr or "UnknownHost" in stderr or "refused" in stderr:
                raise MediafluxTransportError(stderr.strip())
            raise MediafluxAssetCreateError(stderr.strip() or "aterm failed")
        return (result.stdout or b"").decode("utf-8", errors="replace")

    async def create_asset(
        self,
        file_path: Path,
        *,
        namespace: str,
        name: str,
        metadata,
    ) -> str:
        from app.mediaflux.metadata import render_meta_argument

        meta_arg = render_meta_argument(metadata)
        args = [
            "asset.create",
            ":namespace", namespace,
            ":name", name,
            ":in", f"file:{file_path}",
        ]
        # The :meta < … > argument is multi-token; pass it pre-tokenised by
        # splitting on whitespace. _escape() in metadata.py prevents injection.
        args.extend(meta_arg.split())
        out = await self._run(args)
        m = _ASSET_ID_RE.search(out)
        if not m:
            raise MediafluxAssetCreateError(f"could not parse asset id from: {out!r}")
        return m.group(1)

    async def destroy_asset(self, asset_id: str) -> None:
        try:
            await self._run(["asset.destroy", ":id", asset_id])
        except Exception as exc:  # destroy is best-effort
            log.warning("asset.destroy failed for %s: %s", asset_id, exc)
