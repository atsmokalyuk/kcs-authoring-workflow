"""MCP tool result envelopes for the Desktop adapter transport."""

from __future__ import annotations

from dataclasses import dataclass

from kcs_adapters import desktop_tool_results as _desktop_tool_results
from kcs_adapters.desktop_tool_descriptors import McpToolDescriptor
from kcs_adapters.desktop_tool_names import TOOL_DRAFT_ARTICLE
from kcs_core.json_payload import JsonDict


@dataclass(frozen=True)
class McpToolResult:
    """Safe adapter tool result."""

    ok: bool
    result: JsonDict | None = None
    error: str | None = None
    error_code: str | None = None


def mcp_tool_response(
    *,
    descriptor: McpToolDescriptor,
    result: McpToolResult,
) -> JsonDict:
    structured = (
        result.result
        if result.ok and result.result is not None
        else {
            "error": result.error or "KCS MCP tool failed.",
            "error_code": result.error_code or "tool_error",
            "ok": False,
        }
    )
    _desktop_tool_results.validate_tool_structured_content(
        structured,
        descriptor.output_schema,
    )
    content = _desktop_tool_results.tool_result_content(structured)
    structured_content = _desktop_tool_results.desktop_structured_content(
        draft_tool_name=TOOL_DRAFT_ARTICLE,
        descriptor_name=descriptor.name,
        structured=structured,
    )
    return {
        "content": content,
        "isError": not result.ok,
        "structuredContent": structured_content,
    }


def tool_error(error_code: str) -> McpToolResult:
    return McpToolResult(
        ok=False,
        error="KCS MCP tool validation failed.",
        error_code=error_code,
    )


__all__ = [
    "McpToolResult",
    "mcp_tool_response",
    "tool_error",
]
