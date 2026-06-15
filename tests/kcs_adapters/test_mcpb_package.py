from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from kcs_adapters.mcp_desktop import CLAUDE_DESKTOP_TOOL_ALIASES

REPO_ROOT = Path(__file__).resolve().parents[2]
MCPB_SOURCE = (
    REPO_ROOT
    / "packaging"
    / "claude-desktop"
    / "kcs-authoring-mvp-validator-control"
)
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_kcs_mcpb.py"
EXPECTED_BUNDLE_FILES = {
    "README.md",
    "manifest.json",
    "server/index.js",
}
NODE_COMMAND = shutil.which("node")


def _load_build_module():
    spec = importlib.util.spec_from_file_location("build_kcs_mcpb", BUILD_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _copy_mcpb_source(tmp_path: Path) -> Path:
    source = tmp_path / "bundle"
    shutil.copytree(MCPB_SOURCE, source)
    return source


def test_mcpb_manifest_exposes_desktop_alias_tools_only() -> None:
    manifest = json.loads((MCPB_SOURCE / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["manifest_version"] == "0.3"
    assert manifest["name"] == "kcs-authoring-mvp-validator-control"
    assert manifest["server"]["type"] == "node"
    assert manifest["server"]["entry_point"] == "server/index.js"
    assert manifest["server"]["mcp_config"]["command"] == "node"
    assert {tool["name"] for tool in manifest["tools"]} == set(
        CLAUDE_DESKTOP_TOOL_ALIASES.values()
    )
    assert all("." not in tool["name"] for tool in manifest["tools"])
    assert manifest["prompts_generated"] is False
    assert manifest["tools_generated"] is False


def test_mcpb_manifest_uses_user_config_without_secrets_or_paths() -> None:
    text = (MCPB_SOURCE / "manifest.json").read_text(encoding="utf-8")
    manifest = json.loads(text)

    assert "${user_config.repository_root}" in text
    assert "${user_config.uv_command}" in text
    assert "/Users/" not in text
    assert "api_key" not in text.casefold()
    assert "token" not in text.casefold()
    assert "secret" not in text.casefold()
    assert manifest["user_config"]["repository_root"]["type"] == "directory"
    assert manifest["user_config"]["repository_root"]["required"] is True
    assert manifest["user_config"]["uv_command"]["type"] == "string"


def test_mcpb_node_wrapper_launches_repo_local_stdio_server() -> None:
    text = (MCPB_SOURCE / "server" / "index.js").read_text(encoding="utf-8")

    assert "KCS_AUTHORING_MVP_REPO_ROOT" in text
    assert "KCS_AUTHORING_MVP_UV_COMMAND" in text
    assert 'name = "kcs-authoring-mvp"' in text
    assert "src\", \"kcs_adapters\", \"mcp_desktop.py" in text
    assert '"--project"' in text
    assert '"kcs-desktop-mcp"' in text
    assert '"claude_desktop_aliases"' in text
    assert "/Users/" not in text
    assert "plesk" not in text.casefold()
    assert "process.stdin.pipe(child.stdin)" in text
    assert "child.stdout" in text
    assert "USERPROFILE" in text
    assert "APPDATA" in text
    assert "TMPDIR" in text


def test_mcpb_node_wrapper_rejects_wrong_repo_root_without_spawn(
    tmp_path: Path,
) -> None:
    if NODE_COMMAND is None:
        pytest.skip("node is not installed")
    repo = tmp_path / "wrong-repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "not-kcs-authoring-mvp"\n',
        encoding="utf-8",
    )

    completed = subprocess.run(
        [NODE_COMMAND, str(MCPB_SOURCE / "server" / "index.js")],
        check=False,
        env={
            "KCS_AUTHORING_MVP_REPO_ROOT": str(repo),
            "KCS_AUTHORING_MVP_UV_COMMAND": "uv",
            "PATH": "",
        },
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert completed.returncode != 0
    assert "repository_root must point to the KCS Authoring MVP repository" in (
        completed.stderr
    )
    assert "not-kcs-authoring-mvp" not in completed.stderr


def test_mcpb_node_wrapper_rejects_uv_command_with_arguments() -> None:
    if NODE_COMMAND is None:
        pytest.skip("node is not installed")
    completed = subprocess.run(
        [NODE_COMMAND, str(MCPB_SOURCE / "server" / "index.js")],
        check=False,
        env={
            "KCS_AUTHORING_MVP_REPO_ROOT": str(REPO_ROOT),
            "KCS_AUTHORING_MVP_UV_COMMAND": "uv --project /private",
            "PATH": "",
        },
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert completed.returncode != 0
    assert "uv executable name or path without arguments" in completed.stderr
    assert "/private" not in completed.stderr


def test_build_script_creates_mcpb_archive(tmp_path: Path) -> None:
    module = _load_build_module()
    output = tmp_path / "kcs-authoring-mvp-validator-control.mcpb"

    built = module.build_mcpb(source=MCPB_SOURCE, output=output)

    assert built == output
    assert output.is_file()
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert names == EXPECTED_BUNDLE_FILES
        assert all(".venv" not in name for name in names)
        assert all("__pycache__" not in name for name in names)
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
    assert manifest["name"] == "kcs-authoring-mvp-validator-control"


def test_build_script_rejects_symlinked_files(tmp_path: Path) -> None:
    module = _load_build_module()
    source = _copy_mcpb_source(tmp_path)
    private_file = tmp_path / "private-token.txt"
    private_file.write_text("token=SECRET", encoding="utf-8")
    (source / "server" / "leak.txt").symlink_to(private_file)

    try:
        module.build_mcpb(source=source, output=tmp_path / "out.mcpb")
    except SystemExit as exc:
        assert "leak.txt" in str(exc)
        assert "SECRET" not in str(exc)
    else:  # pragma: no cover - failure path for assertion clarity
        raise AssertionError("expected symlinked MCPB source to fail closed")


def test_build_script_rejects_unexpected_extra_files(tmp_path: Path) -> None:
    module = _load_build_module()
    source = _copy_mcpb_source(tmp_path)
    (source / ".env").write_text("TOKEN=SECRET", encoding="utf-8")

    try:
        module.build_mcpb(source=source, output=tmp_path / "out.mcpb")
    except SystemExit as exc:
        assert ".env" in str(exc)
        assert "SECRET" not in str(exc)
    else:  # pragma: no cover - failure path for assertion clarity
        raise AssertionError("expected unexpected MCPB source file to fail closed")
