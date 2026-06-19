from __future__ import annotations

import pytest

from kcs_adapters import desktop_protocol
from kcs_adapters.desktop_mcp_results import (
    McpToolResult,
    mcp_tool_response,
    tool_error,
)
from kcs_adapters.desktop_tool_descriptors import tool_descriptors


def test_initialize_result_returns_fixed_protocol_payload() -> None:
    result = desktop_protocol.initialize_result(
        desktop_protocol.MCP_PROTOCOL_VERSION
    )

    assert result["protocolVersion"] == desktop_protocol.MCP_PROTOCOL_VERSION
    assert result["serverInfo"] == {
        "name": desktop_protocol.MCP_DESKTOP_SERVER_NAME,
        "version": desktop_protocol.MCP_DESKTOP_SERVER_VERSION,
    }
    assert result["capabilities"] == {
        "prompts": {"listChanged": False},
        "resources": {"listChanged": False, "subscribe": False},
        "tools": {"listChanged": False},
    }
    assert "kcs_register_clean_ticket" in result["instructions"]
    assert "kcs_draft_article" in result["instructions"]


def test_initialize_result_rejects_unsupported_protocol_version() -> None:
    with pytest.raises(ValueError, match="Unsupported protocol version"):
        desktop_protocol.initialize_result("2024-11-05")


def test_mcp_tool_response_builds_success_envelope() -> None:
    descriptor = tool_descriptors()[0]

    response = mcp_tool_response(
        descriptor=descriptor,
        result=McpToolResult(
            ok=True,
            result={
                "ok": True,
                "result_kind": "policy_summary",
                "schema_version": "kcs_mcp_tool_result_v1",
            },
        ),
    )

    assert response["isError"] is False
    assert response["structuredContent"]["ok"] is True
    assert response["content"][0]["type"] == "text"


def test_tool_error_builds_error_envelope() -> None:
    descriptor = tool_descriptors()[0]
    result = tool_error("tool_result_invalid")

    response = mcp_tool_response(descriptor=descriptor, result=result)

    assert result.ok is False
    assert result.error_code == "tool_result_invalid"
    assert response["isError"] is True
    assert response["structuredContent"]["error_code"] == "tool_result_invalid"
