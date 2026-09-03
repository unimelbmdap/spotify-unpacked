"""Command line entry points.

    python -m donation_reports run [--once] [--force] [--only CODE]
    python -m donation_reports render BUNDLE.zip --out DIR [--variant streaming-only]
    python -m donation_reports render-one BUNDLE.zip OUT_DIR --version N --assets-dir DIR
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from donation_reports import fonts
from donation_reports.companion import build_companion
from donation_reports.loader import build_streaming_frame, load_bundle, streaming_only
from donation_reports.naming import BundleName, parse_bundle_name
from donation_reports.stats import DonorStats
from donation_reports.version import GENERATOR_VERSION
from donation_reports.worker import WorkerConfig, run_forever, run_once

logger = logging.getLogger("donation_reports")


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )


def render_bundle(zip_path: Path, out_dir: Path, *, version: int, assets_dir: Path,
                  variant: str | None = None, name: BundleName | None = None) -> tuple[Path, Path]:
    """Load, compute, and write `<stem>__vNN.json` then `<stem>__vNN.pdf` into out_dir."""
    from donation_reports.render import RenderContext, generate_donor_pdf

    fonts.configure(assets_dir)
    name = name or parse_bundle_name(zip_path) or BundleName(
        code=zip_path.stem, stamp="", donation_id=0, stem=zip_path.stem
    )
    streaming_raw, library, playlists = load_bundle(zip_path)
    if variant == "streaming-only":
        library, playlists = streaming_only(library, playlists)
    donor = DonorStats(name.code, build_streaming_frame(streaming_raw), library, playlists)

    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"__{variant}" if variant else ""
    companion_path = out_dir / (name.versioned_stem(version) + suffix + ".json")
    report_path = out_dir / (name.versioned_stem(version) + suffix + ".pdf")
    companion_path.write_text(
        json.dumps(build_companion(donor, name, version=version), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    generate_donor_pdf(donor, report_path, RenderContext(version=version, assets_dir=assets_dir))
    return companion_path, report_path


def _cmd_run(args: argparse.Namespace) -> int:
    cfg = WorkerConfig.from_env()
    if args.once:
        summary = run_once(cfg, force=args.force, only=args.only)
        return 0 if summary.failed == 0 else 1
    if args.force or args.only:
        print("--force/--only require --once", file=sys.stderr)
        return 2
    run_forever(cfg)
    return 0


def _cmd_render(args: argparse.Namespace) -> int:
    assets_dir = Path(args.assets_dir) if args.assets_dir else WorkerConfig.from_env().assets_dir
    companion, report = render_bundle(
        Path(args.bundle), Path(args.out), version=GENERATOR_VERSION, assets_dir=assets_dir,
        variant=args.variant,
    )
    print(f"wrote {companion}\nwrote {report}")
    return 0


def _cmd_render_one(args: argparse.Namespace) -> int:
    """Child process used by the worker. Last stderr line on failure is `Error: message`."""
    try:
        render_bundle(Path(args.bundle), Path(args.out_dir), version=args.version,
                      assets_dir=Path(args.assets_dir))
        return 0
    except Exception as exc:  # noqa: BLE001 - reported to the parent via exit code + stderr
        logger.exception("render-one failed")
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="donation_reports")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="scan the donations directory and render pending reports")
    run.add_argument("--once", action="store_true", help="one cycle, then exit")
    run.add_argument("--force", action="store_true",
                     help="ignore older-version reports and failure markers (never overwrites)")
    run.add_argument("--only", metavar="CODE", help="restrict to one participant code")
    run.set_defaults(func=_cmd_run)

    render = sub.add_parser("render", help="render one bundle to a directory (local inspection)")
    render.add_argument("bundle")
    render.add_argument("--out", required=True)
    render.add_argument("--variant", choices=["streaming-only"])
    render.add_argument("--assets-dir")
    render.set_defaults(func=_cmd_render)

    one = sub.add_parser("render-one", help="internal: worker child process")
    one.add_argument("bundle")
    one.add_argument("out_dir")
    one.add_argument("--version", type=int, required=True)
    one.add_argument("--assets-dir", required=True)
    one.set_defaults(func=_cmd_render_one)
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_logging()
    args = build_parser().parse_args(argv)
    return args.func(args)
