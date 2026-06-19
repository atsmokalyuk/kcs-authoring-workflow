"""Build and install the local KCS Authoring Claude Desktop MCPB extension."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import zipfile
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from types import ModuleType

SCRIPT_DIR = Path(__file__).resolve().parent
BUILD_SCRIPT = SCRIPT_DIR / "build_kcs_mcpb.py"


def _load_build_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("build_kcs_mcpb", BUILD_SCRIPT)
    if spec is None or spec.loader is None:
        raise SystemExit("MCPB build script could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_BUILD_MODULE = _load_build_module()
ALLOWED_BUNDLE_FILES = _BUILD_MODULE.ALLOWED_BUNDLE_FILES
DEFAULT_OUTPUT = _BUILD_MODULE.DEFAULT_OUTPUT
build_mcpb = _BUILD_MODULE.build_mcpb
expected_bundle_files = _BUILD_MODULE.expected_bundle_files
package_member_allowed = _BUILD_MODULE.package_member_allowed

BUNDLE_NAME = "kcs-authoring-mvp-validator-control"
BUNDLE_SOURCE = Path("packaging/claude-desktop") / BUNDLE_NAME
CLAUDE_EXTENSION_DIRNAME = (
    "local.mcpb.kcs-authoring-mvp.kcs-authoring-mvp-validator-control"
)
DEFAULT_CLAUDE_EXTENSIONS_ROOT = (
    Path.home() / "Library" / "Application Support" / "Claude" / "Claude Extensions"
)
DEFAULT_INSTALL_DIR = DEFAULT_CLAUDE_EXTENSIONS_ROOT / CLAUDE_EXTENSION_DIRNAME
DEFAULT_INSTALLATIONS_FILE = (
    DEFAULT_CLAUDE_EXTENSIONS_ROOT.parent / "extensions-installations.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default=str(BUNDLE_SOURCE),
        help="MCPB source directory.",
    )
    parser.add_argument(
        "--package",
        default=str(DEFAULT_OUTPUT),
        help="Built .mcpb package path.",
    )
    parser.add_argument(
        "--install-dir",
        default=str(DEFAULT_INSTALL_DIR),
        help="Claude Desktop extension install directory.",
    )
    parser.add_argument(
        "--installations-file",
        default=str(DEFAULT_INSTALLATIONS_FILE),
        help="Claude Desktop extensions-installations.json path.",
    )
    parser.add_argument(
        "--skip-registry-update",
        action="store_true",
        help="Install files only; do not update Claude Desktop registry cache.",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Install an existing package without rebuilding it first.",
    )
    args = parser.parse_args(argv)

    package = Path(args.package)
    if not args.skip_build:
        package = build_mcpb(source=Path(args.source), output=package)
    install_mcpb(
        package=package,
        install_dir=Path(args.install_dir),
        installations_file=Path(args.installations_file),
        update_registry=not args.skip_registry_update,
    )
    print(Path(args.install_dir))
    return 0


def install_mcpb(
    *,
    package: Path,
    install_dir: Path,
    installations_file: Path | None = None,
    update_registry: bool = True,
) -> Path:
    package = package.resolve()
    install_dir = install_dir.resolve()
    _validate_package(package)
    install_dir.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = install_dir.with_name(f".{install_dir.name}.tmp")
    backup_dir = install_dir.with_name(f".{install_dir.name}.bak")
    _remove_tree(tmp_dir)
    _remove_tree(backup_dir)

    with zipfile.ZipFile(package) as archive:
        archive.extractall(tmp_dir)

    if install_dir.exists():
        install_dir.replace(backup_dir)
    tmp_dir.replace(install_dir)
    _remove_tree(backup_dir)
    if update_registry:
        _update_installation_registry(
            package=package,
            install_dir=install_dir,
            installations_file=(
                installations_file.resolve()
                if installations_file is not None
                else install_dir.parent.parent / "extensions-installations.json"
            ),
        )
    return install_dir


def _validate_package(package: Path) -> None:
    if not package.is_file() or package.is_symlink():
        raise SystemExit(f"MCPB package not found: {package}")
    expected_names = {path.as_posix() for path in expected_bundle_files()}
    with zipfile.ZipFile(package) as archive:
        names = set(archive.namelist())
        if not expected_names.issubset(names):
            raise SystemExit("MCPB package contains unexpected files")
        if any(not package_member_allowed(Path(name)) for name in names):
            raise SystemExit("MCPB package contains unexpected files")
        for info in archive.infolist():
            path = Path(info.filename)
            if path.is_absolute() or ".." in path.parts:
                raise SystemExit("MCPB package contains unsafe paths")
            if _zip_member_is_symlink(info):
                raise SystemExit("MCPB package contains symlinks")


def _update_installation_registry(
    *,
    package: Path,
    install_dir: Path,
    installations_file: Path,
) -> None:
    manifest = _package_manifest(package)
    registry = _read_installation_registry(installations_file)
    extensions = registry.setdefault("extensions", {})
    if not isinstance(extensions, dict):
        raise SystemExit("Claude extensions registry has invalid extensions field")
    previous_entry = extensions.get(install_dir.name, {})
    if not isinstance(previous_entry, dict):
        previous_entry = {}
    extensions[install_dir.name] = {
        "id": install_dir.name,
        "version": str(manifest.get("version", "")),
        "hash": sha256(package.read_bytes()).hexdigest(),
        "installedAt": _utc_timestamp(),
        "manifest": manifest,
        "signatureInfo": previous_entry.get("signatureInfo", {"status": "unsigned"}),
        "source": previous_entry.get("source", "local"),
    }
    _write_installation_registry(installations_file, registry)


def _package_manifest(package: Path) -> dict[str, object]:
    with zipfile.ZipFile(package) as archive:
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
    if not isinstance(manifest, dict):
        raise SystemExit("MCPB manifest is invalid")
    return manifest


def _read_installation_registry(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"extensions": {}}
    registry = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(registry, dict):
        raise SystemExit("Claude extensions registry is invalid")
    return registry


def _write_installation_registry(path: Path, registry: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_name(
            f"{path.name}.codex-backup-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        )
        shutil.copy2(path, backup)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp_path.replace(path)


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _zip_member_is_symlink(info: zipfile.ZipInfo) -> bool:
    return (info.external_attr >> 16) & 0o170000 == 0o120000


def _remove_tree(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
