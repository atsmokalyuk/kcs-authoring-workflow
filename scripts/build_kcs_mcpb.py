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
STATIC_BUNDLE_FILES = frozenset(
    {
        Path("manifest.json"),
        Path("server/index.js"),
        Path("README.md"),
    }
)
ALLOWED_BUNDLE_FILES = STATIC_BUNDLE_FILES
REQUIRED_FILES = (
    Path("manifest.json"),
    Path("server/index.js"),
    Path("README.md"),
)
BUNDLED_PROJECT_ROOT = Path("python")
BUNDLED_PROJECT_FILES = (
    Path("pyproject.toml"),
    Path("README.md"),
)
BUNDLED_SOURCE_DIRS = (
    Path("src/kcs_adapters"),
    Path("src/kcs_core"),
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
    repo_root = _repo_root()
    output = output.resolve()
    _validate_source(source)
    _validate_bundled_project(repo_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp_output = output.with_name(f".{output.name}.tmp")
    if tmp_output.exists():
        tmp_output.unlink()
    with zipfile.ZipFile(tmp_output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in _bundle_files(source):
            archive.write(path, path.relative_to(source).as_posix())
        for path in _bundled_project_files(repo_root):
            archive.write(
                path,
                (BUNDLED_PROJECT_ROOT / path.relative_to(repo_root)).as_posix(),
            )
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

    unexpected = discovered - STATIC_BUNDLE_FILES
    if unexpected:
        names = ", ".join(sorted(item.as_posix() for item in unexpected))
        raise SystemExit(f"MCPB source contains unexpected files: {names}")

    for relative in sorted(STATIC_BUNDLE_FILES):
        yield source / relative


def _bundled_project_files(repo_root: Path) -> Iterable[Path]:
    for relative in BUNDLED_PROJECT_FILES:
        path = repo_root / relative
        if path.is_file():
            yield path
    for source_dir in BUNDLED_SOURCE_DIRS:
        root = repo_root / source_dir
        for path in sorted(root.rglob("*.py")):
            relative = path.relative_to(repo_root)
            if any(part in FORBIDDEN_PARTS for part in relative.parts):
                continue
            if path.is_symlink():
                raise SystemExit(
                    f"Bundled Python source must not contain symlinks: "
                    f"{relative.as_posix()}"
                )
            yield path


def expected_bundle_files() -> set[Path]:
    """Return the expected package member paths for the current checkout."""

    repo_root = _repo_root()
    return {
        *STATIC_BUNDLE_FILES,
        *(
            BUNDLED_PROJECT_ROOT / path.relative_to(repo_root)
            for path in _bundled_project_files(repo_root)
        ),
    }


def package_member_allowed(member: Path) -> bool:
    """Return whether a package member is allowed in an installed MCPB."""

    if member in STATIC_BUNDLE_FILES:
        return True
    if BUNDLED_PROJECT_ROOT not in member.parents:
        return False
    relative = member.relative_to(BUNDLED_PROJECT_ROOT)
    if any(part in FORBIDDEN_PARTS for part in relative.parts):
        return False
    if relative in BUNDLED_PROJECT_FILES:
        return True
    return (
        relative.suffix == ".py"
        and len(relative.parts) >= 3
        and Path(*relative.parts[:2]) in BUNDLED_SOURCE_DIRS
    )


def _validate_bundled_project(repo_root: Path) -> None:
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.is_file():
        raise SystemExit("Bundled Python project is missing pyproject.toml")
    text = pyproject.read_text(encoding="utf-8")
    if 'name = "kcs-authoring-mvp"' not in text:
        raise SystemExit("Bundled Python project has unexpected name")
    for source_dir in BUNDLED_SOURCE_DIRS:
        if not (repo_root / source_dir).is_dir():
            raise SystemExit(
                f"Bundled Python project is missing {source_dir.as_posix()}"
            )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
