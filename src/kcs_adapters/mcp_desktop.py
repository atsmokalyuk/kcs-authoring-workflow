"""Claude Desktop MCP stdio adapter for KCS validator/control tools."""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import IO, Any

from kcs_adapters import desktop_authoring_tools as _desktop_authoring_tools
from kcs_adapters import desktop_control_tools as _desktop_control_tools
from kcs_adapters import desktop_draft_arguments as _desktop_draft_arguments
from kcs_adapters import desktop_mcp_results as _desktop_mcp_results
from kcs_adapters import desktop_protocol as _desktop_protocol
from kcs_adapters import desktop_stdio_transport as _desktop_stdio_transport
from kcs_adapters.desktop_reviewer_bundle import (
    DEFAULT_REVIEWER_BUNDLE_ROOT,
    reviewer_bundle_root_from_environment,
)
from kcs_adapters.desktop_tool_descriptors import (
    McpToolDescriptor,
    tool_descriptors,
)
from kcs_adapters.desktop_tool_names import (
    CANONICAL_TOOL_BY_CLAUDE_DESKTOP_ALIAS,
    CLAUDE_DESKTOP_TOOL_ALIASES,
    DESKTOP_OPERATOR_TOOLS,
    TOOL_AUTHOR_APPROVED_SUMMARY,
    TOOL_AUTHOR_TICKET,
    TOOL_DRAFT_ARTICLE,
    TOOL_GET_MCP_READINESS,
    TOOL_GET_POLICY_SUMMARY,
    TOOL_NAME_STYLE_CANONICAL,
    TOOL_NAME_STYLE_DESKTOP_ALIASES,
    TOOL_REGISTER_CLEAN_TICKET,
    TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
    TOOL_RUN_CONTRACT_SMOKE,
    TOOL_SUPPORT_GET_BEHAVIOR_INSTRUCTIONS,
    TOOL_VALIDATE_DRAFT_REQUEST,
    TOOL_VALIDATE_DRAFT_RESPONSE,
    TOOL_VALIDATE_HANDOFF_REQUEST,
    TOOL_VALIDATE_HANDOFF_RESPONSE,
    canonical_tool_name_from_claude_desktop_alias,
    claude_desktop_tool_alias,
)
from kcs_adapters.desktop_workflow import (
    DesktopDraftWorkflow,
    semantic_provider_from_environment,
)
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict
from kcs_core.semantic_extraction import SemanticExtractionProvider

MCP_PROTOCOL_VERSION = _desktop_protocol.MCP_PROTOCOL_VERSION
MCP_SUPPORTED_PROTOCOL_VERSIONS = _desktop_protocol.MCP_SUPPORTED_PROTOCOL_VERSIONS
MCP_DESKTOP_SERVER_NAME = _desktop_protocol.MCP_DESKTOP_SERVER_NAME
MCP_DESKTOP_SERVER_VERSION = _desktop_protocol.MCP_DESKTOP_SERVER_VERSION
MCP_TOOL_RESULT_SCHEMA_VERSION = "kcs_mcp_tool_result_v1"

_REQUEST_ARG = frozenset({"request"})
_REQUEST_RESPONSE_ARGS = frozenset({"request", "response"})
_NO_ARGS = frozenset()
_DRAFT_SELECTION_TTL_SECONDS = 15 * 60
_REVIEWER_BUNDLE_ROOT = DEFAULT_REVIEWER_BUNDLE_ROOT
_DEFAULT_SEMANTIC_EXTRACTION_PROVIDER = object()


DraftArticleSemanticExtractionProvider = SemanticExtractionProvider
McpArgumentError = _desktop_stdio_transport.McpArgumentError
McpToolResult = _desktop_mcp_results.McpToolResult


class KcsDesktopMcpAdapter:
    """Read-only validator/control tool facade for Claude Desktop."""

    def __init__(
        self,
        *,
        reviewer_bundle_root: Path | None = None,
        semantic_extraction_provider: DraftArticleSemanticExtractionProvider
        | None
        | object = _DEFAULT_SEMANTIC_EXTRACTION_PROVIDER,
        selection_ttl_seconds: float = _DRAFT_SELECTION_TTL_SECONDS,
        visible_tools: Iterable[str] | None = None,
    ) -> None:
        self._tools: tuple[McpToolDescriptor, ...] | None = None
        self._reviewer_bundle_root = (
            reviewer_bundle_root
            if reviewer_bundle_root is not None
            else reviewer_bundle_root_from_environment()
        )
        semantic_provider = (
            semantic_provider_from_environment()
            if semantic_extraction_provider is _DEFAULT_SEMANTIC_EXTRACTION_PROVIDER
            else semantic_extraction_provider
        )
        self._draft_workflow = DesktopDraftWorkflow(
            provider=semantic_provider,
            selection_ttl_seconds=selection_ttl_seconds,
        )
        self._authoring_tools = _desktop_authoring_tools.DesktopAuthoringTools(
            draft_workflow=self._draft_workflow,
            reviewer_bundle_root=self._reviewer_bundle_root,
            schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
        )
        self._visible_tools = frozenset(visible_tools) if visible_tools else None
        self._handlers: dict[
            str, Any
        ] = {
            TOOL_GET_POLICY_SUMMARY: self._get_policy_summary,
            TOOL_GET_MCP_READINESS: self._get_readiness,
            TOOL_VALIDATE_HANDOFF_REQUEST: self._validate_handoff_request,
            TOOL_VALIDATE_HANDOFF_RESPONSE: self._validate_handoff_response,
            TOOL_VALIDATE_DRAFT_REQUEST: self._validate_draft_request,
            TOOL_VALIDATE_DRAFT_RESPONSE: self._validate_draft_response,
            TOOL_RUN_CONTRACT_SMOKE: self._run_contract_smoke,
            TOOL_RUN_APPROVED_SUMMARY_PIPELINE: (
                self._authoring_tools.run_approved_summary_pipeline
            ),
            TOOL_AUTHOR_APPROVED_SUMMARY: (
                self._authoring_tools.author_approved_summary
            ),
            TOOL_AUTHOR_TICKET: self._authoring_tools.author_ticket,
            TOOL_REGISTER_CLEAN_TICKET: (
                self._authoring_tools.register_clean_ticket
            ),
            TOOL_DRAFT_ARTICLE: self._authoring_tools.draft_article,
            TOOL_SUPPORT_GET_BEHAVIOR_INSTRUCTIONS: (
                self._authoring_tools.support_get_behavior_instructions
            ),
        }

    def list_tools(self) -> tuple[McpToolDescriptor, ...]:
        """Return the fixed KCS-12 tool surface."""

        if self._tools is None:
            tools = tool_descriptors()
            if self._visible_tools is not None:
                tools = tuple(
                    tool for tool in tools if tool.name in self._visible_tools
                )
            self._tools = tools
        return self._tools

    def call_tool(
        self, name: str, arguments: Mapping[str, Any] | None = None
    ) -> McpToolResult:
        """Dispatch a known local MCP tool."""

        arguments = arguments or {}
        handler = self._handlers.get(name)
        if handler is None:
            return _tool_error("tool_unavailable")
        try:
            return McpToolResult(ok=True, result=handler(arguments))
        except (McpArgumentError, _desktop_draft_arguments.DraftArticleArgumentError):
            raise
        except ContractValidationError:
            return _tool_error("validation_failed")
        except Exception:  # pragma: no cover - defensive adapter boundary
            return _tool_error("tool_failed")

    def _get_policy_summary(self, arguments: Mapping[str, Any]) -> JsonDict:
        _require_args(arguments, _NO_ARGS, required=_NO_ARGS)
        return _desktop_control_tools.policy_summary_result(
            schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
            tool_count=len(self.list_tools()),
        )

    def _get_readiness(self, arguments: Mapping[str, Any]) -> JsonDict:
        _require_args(arguments, _NO_ARGS, required=_NO_ARGS)
        return _desktop_control_tools.readiness_result(
            schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
            tools=self.list_tools(),
        )

    def _validate_handoff_request(self, arguments: Mapping[str, Any]) -> JsonDict:
        _require_args(arguments, _REQUEST_ARG, required=_REQUEST_ARG)
        return _desktop_control_tools.validate_handoff_request_result(
            arguments["request"],
            schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
        )

    def _validate_handoff_response(self, arguments: Mapping[str, Any]) -> JsonDict:
        _require_args(
            arguments,
            _REQUEST_RESPONSE_ARGS,
            required=_REQUEST_RESPONSE_ARGS,
        )
        return _desktop_control_tools.validate_handoff_response_result(
            arguments["request"],
            arguments["response"],
            schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
        )

    def _validate_draft_request(self, arguments: Mapping[str, Any]) -> JsonDict:
        _require_args(arguments, _REQUEST_ARG, required=_REQUEST_ARG)
        return _desktop_control_tools.validate_draft_request_result(
            arguments["request"],
            schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
        )

    def _validate_draft_response(self, arguments: Mapping[str, Any]) -> JsonDict:
        _require_args(
            arguments,
            _REQUEST_RESPONSE_ARGS,
            required=_REQUEST_RESPONSE_ARGS,
        )
        return _desktop_control_tools.validate_draft_response_result(
            arguments["request"],
            arguments["response"],
            schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
        )

    def _run_contract_smoke(self, arguments: Mapping[str, Any]) -> JsonDict:
        _require_args(arguments, _NO_ARGS, required=_NO_ARGS)
        return _desktop_control_tools.contract_smoke_result(
            schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION
        )


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
                visible_tools=visible_tools
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
            visible_tools=visible_tools
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
_tool_error = _desktop_mcp_results.tool_error


def _require_args(
    arguments: Mapping[str, Any],
    allowed: frozenset[str],
    *,
    required: frozenset[str],
) -> None:
    if any(key not in allowed for key in arguments):
        raise McpArgumentError("Unexpected tool argument.")
    if any(key not in arguments for key in required):
        raise McpArgumentError("Missing tool argument.")

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
    "TOOL_DRAFT_ARTICLE",
    "TOOL_GET_MCP_READINESS",
    "TOOL_GET_POLICY_SUMMARY",
    "TOOL_NAME_STYLE_CANONICAL",
    "TOOL_NAME_STYLE_DESKTOP_ALIASES",
    "TOOL_RUN_APPROVED_SUMMARY_PIPELINE",
    "TOOL_RUN_CONTRACT_SMOKE",
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
