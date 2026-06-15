"""Build the local KCS Authoring Claude/Cowork plugin package."""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Iterable

PLUGIN_NAME = "kcs-authoring"
PLUGIN_SOURCE = Path("packaging/cowork") / PLUGIN_NAME
DEFAULT_OUTPUT = Path("dist") / f"{PLUGIN_NAME}.plugin"
REQUIRED_FILES = (
    Path(".claude-plugin/plugin.json"),
    Path(".mcp.json"),
    Path("skills/kcs-authoring-control/SKILL.md"),
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
        default=str(PLUGIN_SOURCE),
        help="Plugin source directory.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output .plugin path.",
    )
    args = parser.parse_args(argv)

    source = Path(args.source)
    output = Path(args.output)
    build_plugin(source=source, output=output)
    print(output)
    return 0


def build_plugin(*, source: Path, output: Path) -> Path:
    """Create a Claude/Cowork plugin zip archive from a validated source dir."""

    source = source.resolve()
    output = output.resolve()
    _validate_source(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp_output = output.with_name(f".{output.name}.tmp")
    if tmp_output.exists():
        tmp_output.unlink()
    with zipfile.ZipFile(tmp_output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in _plugin_files(source):
            archive.write(path, path.relative_to(source).as_posix())
    tmp_output.replace(output)
    return output


def _validate_source(source: Path) -> None:
    if not source.is_dir():
        raise SystemExit(f"Plugin source directory not found: {source}")
    for required in REQUIRED_FILES:
        if not (source / required).is_file():
            raise SystemExit(f"Plugin source is missing {required.as_posix()}")
    _validate_manifest(source)
    _validate_mcp_config(source)


def _validate_manifest(source: Path) -> None:
    manifest = json.loads(
        (source / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    name = manifest.get("name")
    if name != PLUGIN_NAME:
        raise SystemExit(f"Plugin manifest name must be {PLUGIN_NAME}")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise SystemExit("Plugin manifest name must be kebab-case")
    if manifest.get("mcpServers") != "./.mcp.json":
        raise SystemExit("Plugin manifest must reference ./.mcp.json")


def _validate_mcp_config(source: Path) -> None:
    mcp_config = json.loads((source / ".mcp.json").read_text(encoding="utf-8"))
    servers = mcp_config.get("mcpServers")
    if not isinstance(servers, dict) or PLUGIN_NAME not in servers:
        raise SystemExit("Plugin MCP config must define kcs-authoring")
    server = servers[PLUGIN_NAME]
    if not isinstance(server, dict):
        raise SystemExit("Plugin MCP server config is invalid")
    if server.get("command") != "uv":
        raise SystemExit("Plugin MCP server must use uv")
    if "kcs-desktop-mcp" not in server.get("args", ()):
        raise SystemExit("Plugin MCP server must launch kcs-desktop-mcp")


def _plugin_files(source: Path) -> Iterable[Path]:
    for path in sorted(source.rglob("*")):
        if path.is_dir():
            continue
        relative = path.relative_to(source)
        if any(part in FORBIDDEN_PARTS for part in relative.parts):
            continue
        yield path


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
