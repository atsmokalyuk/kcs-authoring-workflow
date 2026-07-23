"""Claude Desktop MCP stdio entrypoint for KCS validator/control tools."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from typing import IO

from kcs_adapters import desktop_mcp_adapter as _desktop_mcp_adapter
from kcs_adapters import desktop_mcp_results as _desktop_mcp_results
from kcs_adapters import desktop_protocol as _desktop_protocol
from kcs_adapters import desktop_stdio_transport as _desktop_stdio_transport
from kcs_adapters.desktop_tool_descriptors import McpToolDescriptor
from kcs_adapters.desktop_tool_names import (
    CANONICAL_TOOL_BY_CLAUDE_DESKTOP_ALIAS,
    CLAUDE_DESKTOP_TOOL_ALIASES,
    DESKTOP_OPERATOR_TOOLS,
    TOOL_AUTHOR_APPROVED_SUMMARY,
    TOOL_AUTHOR_TICKET,
    TOOL_CONFIRM_REUSE_COMPARISON,
    TOOL_DRAFT_ARTICLE,
    TOOL_DRAFT_TICKET,
    TOOL_GET_MCP_READINESS,
    TOOL_GET_POLICY_SUMMARY,
    TOOL_NAME_STYLE_CANONICAL,
    TOOL_NAME_STYLE_DESKTOP_ALIASES,
    TOOL_PREPARE_SEMANTIC_REVIEW,
    TOOL_REGISTER_CLEAN_TICKET,
    TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
    TOOL_RUN_CONTRACT_SMOKE,
    TOOL_SUBMIT_SEMANTIC_REVIEW,
    TOOL_SUPPORT_GET_BEHAVIOR_INSTRUCTIONS,
    TOOL_VALIDATE_DRAFT_REQUEST,
    TOOL_VALIDATE_DRAFT_RESPONSE,
    TOOL_VALIDATE_HANDOFF_REQUEST,
    TOOL_VALIDATE_HANDOFF_RESPONSE,
    canonical_tool_name_from_claude_desktop_alias,
    claude_desktop_tool_alias,
)
from kcs_adapters.local_public_rag import LocalPublicRagAdapter

MCP_PROTOCOL_VERSION = _desktop_protocol.MCP_PROTOCOL_VERSION
MCP_SUPPORTED_PROTOCOL_VERSIONS = _desktop_protocol.MCP_SUPPORTED_PROTOCOL_VERSIONS
MCP_DESKTOP_SERVER_NAME = _desktop_protocol.MCP_DESKTOP_SERVER_NAME
MCP_DESKTOP_SERVER_VERSION = _desktop_protocol.MCP_DESKTOP_SERVER_VERSION
MCP_TOOL_RESULT_SCHEMA_VERSION = (
    _desktop_mcp_adapter.MCP_TOOL_RESULT_SCHEMA_VERSION
)

DraftArticleSemanticExtractionProvider = (
    _desktop_mcp_adapter.DraftArticleSemanticExtractionProvider
)
KcsDesktopMcpAdapter = _desktop_mcp_adapter.KcsDesktopMcpAdapter
McpArgumentError = _desktop_mcp_adapter.McpArgumentError
McpToolResult = _desktop_mcp_adapter.McpToolResult


class McpStdioTransport(_desktop_stdio_transport.McpStdioTransport):
    """Compatibility wrapper that wires the local Desktop adapter factory."""

    def __init__(
        self,
        *,
        adapter: KcsDesktopMcpAdapter | None = None,
        tool_name_style: str = TOOL_NAME_STYLE_DESKTOP_ALIASES,
    ) -> None:
        super().__init__(
            adapter=adapter,
            adapter_factory=lambda visible_tools: KcsDesktopMcpAdapter(
                visible_tools=visible_tools,
                reuse_comparison_provider=LocalPublicRagAdapter(),
            ),
            tool_name_style=tool_name_style,
        )


def serve_stdio(
    *,
    input_stream: Iterable[str | bytes] | None = None,
    output_stream: IO[str] | None = None,
    tool_name_style: str = TOOL_NAME_STYLE_DESKTOP_ALIASES,
) -> None:
    """Serve newline-delimited JSON-RPC over stdio-compatible streams."""

    _desktop_stdio_transport.serve_stdio(
        adapter_factory=lambda visible_tools: KcsDesktopMcpAdapter(
            visible_tools=visible_tools,
            reuse_comparison_provider=LocalPublicRagAdapter(),
        ),
        input_stream=input_stream,
        output_stream=output_stream,
        tool_name_style=tool_name_style,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the KCS Claude Desktop MCP stdio adapter."
    )
    parser.add_argument(
        "--tool-name-style",
        choices=(TOOL_NAME_STYLE_DESKTOP_ALIASES, TOOL_NAME_STYLE_CANONICAL),
        default=TOOL_NAME_STYLE_DESKTOP_ALIASES,
        help=(
            "Expose Claude Desktop underscore aliases by default; canonical "
            "style is internal/test only."
        ),
    )
    args = parser.parse_args(argv)
    serve_stdio(tool_name_style=args.tool_name_style)
    return 0


_mcp_tool_response = _desktop_mcp_results.mcp_tool_response


__all__ = [
    "CANONICAL_TOOL_BY_CLAUDE_DESKTOP_ALIAS",
    "CLAUDE_DESKTOP_TOOL_ALIASES",
    "DESKTOP_OPERATOR_TOOLS",
    "MCP_DESKTOP_SERVER_NAME",
    "MCP_DESKTOP_SERVER_VERSION",
    "MCP_PROTOCOL_VERSION",
    "MCP_TOOL_RESULT_SCHEMA_VERSION",
    "DraftArticleSemanticExtractionProvider",
    "McpArgumentError",
    "McpStdioTransport",
    "McpToolDescriptor",
    "McpToolResult",
    "KcsDesktopMcpAdapter",
    "TOOL_AUTHOR_APPROVED_SUMMARY",
    "TOOL_AUTHOR_TICKET",
    "TOOL_CONFIRM_REUSE_COMPARISON",
    "TOOL_DRAFT_ARTICLE",
    "TOOL_DRAFT_TICKET",
    "TOOL_GET_MCP_READINESS",
    "TOOL_GET_POLICY_SUMMARY",
    "TOOL_NAME_STYLE_CANONICAL",
    "TOOL_NAME_STYLE_DESKTOP_ALIASES",
    "TOOL_PREPARE_SEMANTIC_REVIEW",
    "TOOL_REGISTER_CLEAN_TICKET",
    "TOOL_RUN_APPROVED_SUMMARY_PIPELINE",
    "TOOL_RUN_CONTRACT_SMOKE",
    "TOOL_SUPPORT_GET_BEHAVIOR_INSTRUCTIONS",
    "TOOL_SUBMIT_SEMANTIC_REVIEW",
    "TOOL_VALIDATE_DRAFT_REQUEST",
    "TOOL_VALIDATE_DRAFT_RESPONSE",
    "TOOL_VALIDATE_HANDOFF_REQUEST",
    "TOOL_VALIDATE_HANDOFF_RESPONSE",
    "canonical_tool_name_from_claude_desktop_alias",
    "claude_desktop_tool_alias",
    "main",
    "serve_stdio",
]


if __name__ == "__main__":
    raise SystemExit(main())
