from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path

from kcs_adapters.mcp_desktop import (
    CLAUDE_DESKTOP_TOOL_ALIASES,
    DESKTOP_OPERATOR_TOOLS,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_SOURCE = REPO_ROOT / "packaging" / "cowork" / "kcs-authoring"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_kcs_cowork_plugin.py"
EXPECTED_PLUGIN_FILES = {
    ".claude-plugin/plugin.json",
    ".mcp.json",
    "README.md",
    "skills/kcs-authoring-control/SKILL.md",
}


def _load_build_module():
    spec = importlib.util.spec_from_file_location(
        "build_kcs_cowork_plugin",
        BUILD_SCRIPT,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cowork_plugin_manifest_references_local_mcp_config() -> None:
    manifest = json.loads(
        (PLUGIN_SOURCE / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )

    assert manifest["name"] == "kcs-authoring"
    assert manifest["version"] == "0.1.0"
    assert manifest["mcpServers"] == "./.mcp.json"
    assert manifest["author"]["name"] == "KCS Authoring MVP"


def test_cowork_plugin_mcp_config_launches_kcs_desktop_server() -> None:
    text = (PLUGIN_SOURCE / ".mcp.json").read_text(encoding="utf-8")
    config = json.loads(text)
    server = config["mcpServers"]["kcs-authoring"]

    assert server["command"] == "uv"
    assert server["args"] == [
        "--directory",
        "${HOME}/kcs-authoring-mvp",
        "run",
        "kcs-desktop-mcp",
        "--tool-name-style",
        "claude_desktop_aliases",
    ]
    assert server["env"]["KCS_AUTHORING_MVP_REPO_ROOT"] == "${HOME}/kcs-authoring-mvp"
    assert server["env"]["KCS_AUTHORING_MVP_UV_COMMAND"] == "uv"
    assert "/Users/" not in text
    assert "token" not in text.casefold()
    assert "secret" not in text.casefold()


def test_cowork_plugin_skill_names_expected_tools_and_boundaries() -> None:
    text = (
        PLUGIN_SOURCE / "skills" / "kcs-authoring-control" / "SKILL.md"
    ).read_text(encoding="utf-8")
    expected_tool_names = {
        CLAUDE_DESKTOP_TOOL_ALIASES[tool_name]
        for tool_name in DESKTOP_OPERATOR_TOOLS
    }

    for tool_name in expected_tool_names:
        assert tool_name in text
    assert "kcs_validate_handoff_request" not in text
    assert "kcs_validate_draft_request" not in text
    for boundary in (
        "raw Zendesk payloads",
        "customer replies",
        "credentials",
        "auto_publish_allowed=false",
        "public_output_approved=false",
    ):
        assert boundary in text


def test_build_script_creates_plugin_archive(tmp_path: Path) -> None:
    module = _load_build_module()
    output = tmp_path / "kcs-authoring.plugin"

    built = module.build_plugin(source=PLUGIN_SOURCE, output=output)

    assert built == output
    assert output.is_file()
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert EXPECTED_PLUGIN_FILES.issubset(names)
        assert all(".venv" not in name for name in names)
        assert all("__pycache__" not in name for name in names)
        manifest = json.loads(
            archive.read(".claude-plugin/plugin.json").decode("utf-8")
        )
    assert manifest["name"] == "kcs-authoring"
