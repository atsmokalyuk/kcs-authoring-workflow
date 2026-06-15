"""Build the KCS Authoring MVP Claude Desktop MCPB package."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Iterable

BUNDLE_NAME = "kcs-authoring-mvp-validator-control"
BUNDLE_SOURCE = Path("packaging/claude-desktop") / BUNDLE_NAME
DEFAULT_OUTPUT = Path("dist") / f"{BUNDLE_NAME}.mcpb"
ALLOWED_BUNDLE_FILES = frozenset(
    {
        Path("manifest.json"),
        Path("server/index.js"),
        Path("README.md"),
    }
)
REQUIRED_FILES = (
    Path("manifest.json"),
    Path("server/index.js"),
    Path("README.md"),
)
FORBIDDEN_PARTS = {
    ".DS_Store",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "venv",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default=str(BUNDLE_SOURCE),
        help="MCPB source directory.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output .mcpb path.",
    )
    args = parser.parse_args(argv)

    source = Path(args.source)
    output = Path(args.output)
    build_mcpb(source=source, output=output)
    print(output)
    return 0


def build_mcpb(*, source: Path, output: Path) -> Path:
    """Create an MCPB zip archive from a validated bundle source directory."""

    source = source.resolve()
    output = output.resolve()
    _validate_source(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp_output = output.with_name(f".{output.name}.tmp")
    if tmp_output.exists():
        tmp_output.unlink()
    with zipfile.ZipFile(tmp_output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in _bundle_files(source):
            archive.write(path, path.relative_to(source).as_posix())
    tmp_output.replace(output)
    return output


def _validate_source(source: Path) -> None:
    if not source.is_dir():
        raise SystemExit(f"MCPB source directory not found: {source}")
    for required in REQUIRED_FILES:
        if not (source / required).is_file():
            raise SystemExit(f"MCPB source is missing {required.as_posix()}")
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("manifest_version") != "0.3":
        raise SystemExit("MCPB manifest_version must be 0.3")
    if manifest.get("name") != BUNDLE_NAME:
        raise SystemExit(f"MCPB manifest name must be {BUNDLE_NAME}")


def _bundle_files(source: Path) -> Iterable[Path]:
    discovered: set[Path] = set()
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if path.is_symlink():
            raise SystemExit(
                f"MCPB source must not contain symlinks: {relative.as_posix()}"
            )
        if path.is_dir():
            continue
        if any(part in FORBIDDEN_PARTS for part in relative.parts):
            continue
        discovered.add(relative)

    unexpected = discovered - ALLOWED_BUNDLE_FILES
    if unexpected:
        names = ", ".join(sorted(item.as_posix() for item in unexpected))
        raise SystemExit(f"MCPB source contains unexpected files: {names}")

    for relative in sorted(ALLOWED_BUNDLE_FILES):
        yield source / relative


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
