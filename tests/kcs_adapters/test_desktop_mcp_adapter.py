from __future__ import annotations

import pytest

from kcs_adapters import desktop_mcp_adapter, mcp_desktop
from kcs_adapters.desktop_mcp_adapter import KcsDesktopMcpAdapter
from kcs_adapters.desktop_stdio_transport import McpArgumentError
from kcs_adapters.desktop_tool_names import (
    TOOL_GET_MCP_READINESS,
    TOOL_GET_POLICY_SUMMARY,
)


def test_adapter_filters_visible_tools() -> None:
    adapter = KcsDesktopMcpAdapter(visible_tools={TOOL_GET_POLICY_SUMMARY})

    assert [tool.name for tool in adapter.list_tools()] == [
        TOOL_GET_POLICY_SUMMARY
    ]


def test_mcp_desktop_reexports_adapter_contract() -> None:
    assert mcp_desktop.KcsDesktopMcpAdapter is KcsDesktopMcpAdapter
    assert (
        mcp_desktop.MCP_TOOL_RESULT_SCHEMA_VERSION
        == desktop_mcp_adapter.MCP_TOOL_RESULT_SCHEMA_VERSION
    )
    assert mcp_desktop.McpToolResult is desktop_mcp_adapter.McpToolResult


def test_adapter_dispatches_known_tool() -> None:
    result = KcsDesktopMcpAdapter().call_tool(TOOL_GET_POLICY_SUMMARY, {})

    assert result.ok is True
    assert result.result["ok"] is True
    assert result.result["result_kind"] == "policy_summary"


def test_adapter_returns_controlled_unknown_tool_error() -> None:
    result = KcsDesktopMcpAdapter().call_tool("missing.tool", {})

    assert result.ok is False
    assert result.error_code == "tool_unavailable"


def test_adapter_validates_control_tool_arguments() -> None:
    adapter = KcsDesktopMcpAdapter()

    with pytest.raises(McpArgumentError):
        adapter.call_tool(TOOL_GET_MCP_READINESS, {"unexpected": True})
