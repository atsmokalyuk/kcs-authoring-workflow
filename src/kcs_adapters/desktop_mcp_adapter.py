"""Desktop MCP adapter facade and dispatch table."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from kcs_adapters import desktop_authoring_tools as _desktop_authoring_tools
from kcs_adapters import desktop_control_tools as _desktop_control_tools
from kcs_adapters import desktop_draft_arguments as _desktop_draft_arguments
from kcs_adapters import desktop_mcp_results as _desktop_mcp_results
from kcs_adapters import desktop_stdio_transport as _desktop_stdio_transport
from kcs_adapters.desktop_reviewer_bundle import reviewer_bundle_root_from_environment
from kcs_adapters.desktop_tool_descriptors import (
    McpToolDescriptor,
    tool_descriptors,
)
from kcs_adapters.desktop_tool_names import (
    TOOL_AUTHOR_APPROVED_SUMMARY,
    TOOL_AUTHOR_TICKET,
    TOOL_DRAFT_ARTICLE,
    TOOL_GET_MCP_READINESS,
    TOOL_GET_POLICY_SUMMARY,
    TOOL_REGISTER_CLEAN_TICKET,
    TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
    TOOL_RUN_CONTRACT_SMOKE,
    TOOL_SUPPORT_GET_BEHAVIOR_INSTRUCTIONS,
    TOOL_VALIDATE_DRAFT_REQUEST,
    TOOL_VALIDATE_DRAFT_RESPONSE,
    TOOL_VALIDATE_HANDOFF_REQUEST,
    TOOL_VALIDATE_HANDOFF_RESPONSE,
)
from kcs_adapters.desktop_workflow import (
    DesktopDraftWorkflow,
    semantic_provider_from_environment,
)
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict
from kcs_core.semantic_extraction import SemanticExtractionProvider

MCP_TOOL_RESULT_SCHEMA_VERSION = "kcs_mcp_tool_result_v1"

_REQUEST_ARG = frozenset({"request"})
_REQUEST_RESPONSE_ARGS = frozenset({"request", "response"})
_NO_ARGS = frozenset()
_DRAFT_SELECTION_TTL_SECONDS = 15 * 60
_DEFAULT_SEMANTIC_EXTRACTION_PROVIDER = object()

DraftArticleSemanticExtractionProvider = SemanticExtractionProvider
McpArgumentError = _desktop_stdio_transport.McpArgumentError
McpToolResult = _desktop_mcp_results.McpToolResult


class KcsDesktopMcpAdapter:
    """Validator/control/authoring tool facade for Claude Desktop."""

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
        self._handlers: dict[str, Any] = {
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
            return _desktop_mcp_results.tool_error("tool_unavailable")
        try:
            return McpToolResult(ok=True, result=handler(arguments))
        except (McpArgumentError, _desktop_draft_arguments.DraftArticleArgumentError):
            raise
        except ContractValidationError:
            return _desktop_mcp_results.tool_error("validation_failed")
        except Exception:  # pragma: no cover - defensive adapter boundary
            return _desktop_mcp_results.tool_error("tool_failed")

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
    "DraftArticleSemanticExtractionProvider",
    "KcsDesktopMcpAdapter",
    "MCP_TOOL_RESULT_SCHEMA_VERSION",
    "McpArgumentError",
    "McpToolResult",
]
