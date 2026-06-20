from __future__ import annotations

from collections.abc import Mapping

import pytest

from kcs_adapters import desktop_protocol, desktop_stdio_transport
from kcs_adapters.desktop_mcp_results import McpToolResult
from kcs_adapters.desktop_tool_descriptors import McpToolDescriptor, tool_descriptors
from kcs_adapters.desktop_tool_names import (
    DESKTOP_OPERATOR_TOOLS,
    TOOL_GET_POLICY_SUMMARY,
    TOOL_NAME_STYLE_CANONICAL,
)


class _FakeAdapter:
    def __init__(self, visible_tools: frozenset[str] | None = None) -> None:
        self._visible_tools = visible_tools

    def list_tools(self) -> tuple[McpToolDescriptor, ...]:
        tools = tool_descriptors()
        if self._visible_tools is None:
            return tools
        return tuple(tool for tool in tools if tool.name in self._visible_tools)

    def call_tool(
        self,
        name: str,
        arguments: Mapping[str, object] | None = None,
    ) -> McpToolResult:
        return McpToolResult(
            ok=True,
            result={
                "arguments_seen": dict(arguments or {}),
                "ok": True,
                "result_kind": "policy_summary",
                "schema_version": "kcs_mcp_tool_result_v1",
                "tool_name": name,
            },
        )


def _initialize(transport: desktop_stdio_transport.McpStdioTransport) -> None:
    response = transport.handle_message(
        {
            "id": "init",
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": desktop_protocol.MCP_PROTOCOL_VERSION},
        }
    )
    assert response is not None
    assert (
        response["result"]["protocolVersion"]
        == desktop_protocol.MCP_PROTOCOL_VERSION
    )
    assert (
        transport.handle_message(
            {"jsonrpc": "2.0", "method": "notifications/initialized"}
        )
        is None
    )


def test_stdio_transport_requires_factory_when_adapter_is_missing() -> None:
    with pytest.raises(ValueError, match="MCP adapter factory is required"):
        desktop_stdio_transport.McpStdioTransport()


def test_stdio_transport_factory_receives_desktop_visible_tools() -> None:
    calls: list[frozenset[str] | None] = []

    def factory(visible_tools: frozenset[str] | None) -> _FakeAdapter:
        calls.append(visible_tools)
        return _FakeAdapter(visible_tools)

    transport = desktop_stdio_transport.McpStdioTransport(adapter_factory=factory)
    _initialize(transport)
    response = transport.handle_message(
        {"id": "tools", "jsonrpc": "2.0", "method": "tools/list"}
    )

    assert calls == [DESKTOP_OPERATOR_TOOLS]
    assert response is not None
    assert {tool["name"] for tool in response["result"]["tools"]} == {
        "kcs_register_clean_ticket",
        "kcs_draft_article",
        "kcs_prepare_semantic_review",
        "kcs_submit_semantic_review",
        "support_get_behavior_instructions",
    }


def test_stdio_transport_canonical_mode_uses_all_tools_and_canonical_names() -> None:
    transport = desktop_stdio_transport.McpStdioTransport(
        adapter=_FakeAdapter(),
        tool_name_style=TOOL_NAME_STYLE_CANONICAL,
    )
    _initialize(transport)
    response = transport.handle_message(
        {"id": "tools", "jsonrpc": "2.0", "method": "tools/list"}
    )

    assert response is not None
    assert any(
        tool["name"] == TOOL_GET_POLICY_SUMMARY
        for tool in response["result"]["tools"]
    )
    assert all("outputSchema" in tool for tool in response["result"]["tools"])
