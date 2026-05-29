import logging
import re
from abc import ABC, abstractmethod
from itertools import count
from pathlib import Path

from anyio import fail_after
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
        collection_id: int | None = None,
    ) -> str:
        """Create an asset, return its Mediaflux id.

        If `collection_id` is provided, the new asset is added as a member
        of that Mediaflux collection (in addition to living in the given
        namespace). This is how donations end up grouped under the MDAP
        project's "donations" sub-collection without needing per-donation
        sub-namespaces.
        """

    @abstractmethod
    async def destroy_asset(self, asset_id: str) -> None:
        """Best-effort destroy. Implementations should log + swallow on failure."""


class StubMediafluxClient(MediafluxClient):
    """In-process stub for tests and local Docker dev (no real Mediaflux required)."""

    def __init__(self, *, fail_after: int | None = None) -> None:
        self._next_id = count(start=1000)
        self.created: list[str] = []
        self.destroyed: list[str] = []
        # Per-call audit logs the consumer-facing tests can assert on.
        self.create_calls: list[dict] = []
        self._calls = 0
        self._fail_after = fail_after

    async def create_asset(
        self,
        file_path: Path,
        *,
        namespace: str,
        name: str,
        metadata: DonorMetadata,
        collection_id: int | None = None,
    ) -> str:
        self._calls += 1
        if self._fail_after is not None and self._calls > self._fail_after:
            raise MediafluxAssetCreateError(f"stub failure on call {self._calls}")
        if not file_path.exists():
            raise MediafluxAssetCreateError(f"missing file: {file_path}")
        asset_id = str(next(self._next_id))
        self.created.append(asset_id)
        self.create_calls.append(
            {
                "namespace": namespace,
                "name": name,
                "collection_id": collection_id,
                "metadata": metadata,
            }
        )
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
        # aterm's nogui mode reads connection config from JVM -D properties,
        # NOT from --server=… CLI flags (those get interpreted as Tcl commands
        # by the inner shell and error with "invalid command name").
        #
        # Secure-identity tokens live in a special pseudo-domain called
        # "token"; auth uses domain=token + user=<token-string> (the same
        # pattern documented for SFTP/SMB). No password — the token IS
        # the credential.
        return [
            self.java_executable,
            f"-Dmf.host={self.host}",
            f"-Dmf.port={self.port}",
            "-Dmf.transport=https",
            "-Dmf.domain=token",
            f"-Dmf.user={self.token}",
            f"-Dmf.password={self.token}",
            "-jar",
            str(self.jar_path),
            "nogui",
        ]

    async def _run(self, args: list[str]) -> str:
        if not self.jar_path.exists():
            raise MediafluxTransportError(f"aterm jar not found at {self.jar_path}")
        cmd = self._base_cmd() + args
        log_cmd = " ".join(c if "--token=" not in c else "--token=***" for c in cmd)
        log.info("running aterm: %s", log_cmd)
        # anyio.run_process has no `timeout` kwarg; wrap in fail_after instead.
        try:
            with fail_after(self.timeout_seconds):
                result = await anyio_run_process(cmd, check=False)
        except TimeoutError as exc:
            raise MediafluxTransportError(
                f"aterm timed out after {self.timeout_seconds}s"
            ) from exc
        except Exception as exc:  # network / spawn failure inside anyio
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
        collection_id: int | None = None,
    ) -> str:
        from app.mediaflux.metadata import render_description

        # We store donor metadata in the asset description as
        # `key=value;key=value` rather than as a typed metadata document.
        # The proper-doc-type path needs a server-admin-registered
        # `donation:donor` schema; until that's available this works
        # without elevated permissions and stays human-readable in
        # Asset Finder. See render_description() for the encoding.
        description = render_description(metadata)
        # `:pid <collection-asset-id>` makes the new asset a MEMBER of that
        # collection. (`:collection true|false` is a different arg that
        # marks whether the new asset is itself a collection — not what
        # we want.)
        # When :pid is given, Mediaflux places the new asset in the same
        # namespace as the parent collection — so we must NOT also pass
        # :namespace, or the server does a separate write-permission
        # check on that namespace (which a project-scoped token won't
        # pass for, e.g., /projects).
        args: list[str] = [
            "asset.create",
            ":name", name,
            ":description", description,
            ":in", f"file:{file_path}",
        ]
        if collection_id is not None:
            args.extend([":pid", str(collection_id)])
        else:
            args.extend([":namespace", namespace])
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
