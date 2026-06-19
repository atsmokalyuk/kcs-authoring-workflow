"""Claude Desktop MCP stdio adapter for KCS validator/control tools."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable, Mapping
from dataclasses import asdict, replace
from pathlib import Path
from typing import IO, Any

from kcs_adapters import desktop_authoring_pipeline as _desktop_authoring_pipeline
from kcs_adapters import desktop_contract_smoke as _desktop_contract_smoke
from kcs_adapters import desktop_draft_arguments as _desktop_draft_arguments
from kcs_adapters import desktop_jsonrpc as _desktop_jsonrpc
from kcs_adapters import desktop_mcp_results as _desktop_mcp_results
from kcs_adapters import desktop_payload as _desktop_payload
from kcs_adapters import desktop_protocol as _desktop_protocol
from kcs_adapters import desktop_ticket_ref as _desktop_ticket_ref
from kcs_adapters import desktop_tool_schemas as _desktop_tool_schemas
from kcs_adapters import desktop_workflow as _desktop_workflow
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
    ApprovedSummaryPipelineStageError,
    DesktopDraftWorkflow,
    NoSemanticCandidatesError,
    OperatorSelectionExpiredError,
    OperatorSelectionInvalidError,
    OperatorSelectionUnavailableError,
    PendingDraftSelection,
    SemanticExtractionProviderUnavailableError,
    attach_pending_selection,
    finalize_author_result_with_bundle,
    operator_selection_expired_result,
    operator_selection_unavailable_result,
    semantic_provider_from_environment,
    semantic_provider_unavailable_result,
)
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict
from kcs_core.models import ArticleType
from kcs_core.semantic_extraction import SemanticExtractionProvider

MCP_PROTOCOL_VERSION = _desktop_protocol.MCP_PROTOCOL_VERSION
MCP_SUPPORTED_PROTOCOL_VERSIONS = _desktop_protocol.MCP_SUPPORTED_PROTOCOL_VERSIONS
MCP_DESKTOP_SERVER_NAME = _desktop_protocol.MCP_DESKTOP_SERVER_NAME
MCP_DESKTOP_SERVER_VERSION = _desktop_protocol.MCP_DESKTOP_SERVER_VERSION
MCP_TOOL_RESULT_SCHEMA_VERSION = "kcs_mcp_tool_result_v1"

_REQUEST_ARG = frozenset({"request"})
_REQUEST_RESPONSE_ARGS = frozenset({"request", "response"})
_APPROVED_SUMMARY_FALSE_ONLY_ARGS = _desktop_payload.APPROVED_SUMMARY_FALSE_ONLY_ARGS
_NO_ARGS = frozenset()
_DRAFT_SELECTION_TTL_SECONDS = 15 * 60
_REVIEWER_BUNDLE_ROOT = DEFAULT_REVIEWER_BUNDLE_ROOT
_DEFAULT_SEMANTIC_EXTRACTION_PROVIDER = object()


class McpArgumentError(ValueError):
    """Tool argument shape error that maps to JSON-RPC invalid params."""


ApprovedSummaryInputError = _desktop_payload.ApprovedSummaryInputError


DraftArticleSemanticExtractionProvider = SemanticExtractionProvider
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
            TOOL_RUN_APPROVED_SUMMARY_PIPELINE: self._run_approved_summary_pipeline,
            TOOL_AUTHOR_APPROVED_SUMMARY: self._author_approved_summary,
            TOOL_AUTHOR_TICKET: self._author_ticket,
            TOOL_REGISTER_CLEAN_TICKET: self._register_clean_ticket,
            TOOL_DRAFT_ARTICLE: self._draft_article,
            TOOL_SUPPORT_GET_BEHAVIOR_INSTRUCTIONS: (
                self._support_get_behavior_instructions
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
        return {
            "auto_publish_allowed": False,
            "checks": [
                {
                    "canonical_values": [
                        ArticleType.TECHNICAL_SCR.value,
                        ArticleType.HOWTO_QA.value,
                    ],
                    "kind": "approved_summary_article_types",
                    "ok": True,
                }
            ],
            "customer_replies": False,
            "network_calls": False,
            "ok": True,
            "provider_calls": False,
            "publishes": False,
            "ready_for_real_ticket_use": False,
            "resources_exposed": False,
            "result_kind": "policy_summary",
            "schema_version": MCP_TOOL_RESULT_SCHEMA_VERSION,
            "tool_count": len(self.list_tools()),
            "writes_files": False,
        }

    def _get_readiness(self, arguments: Mapping[str, Any]) -> JsonDict:
        _require_args(arguments, _NO_ARGS, required=_NO_ARGS)
        return {
            "auto_publish_allowed": False,
            "ok": True,
            "prompts_exposed": False,
            "protocol_version": MCP_PROTOCOL_VERSION,
            "public_output_approved": False,
            "ready_for_real_ticket_use": False,
            "resources_exposed": False,
            "result_kind": "mcp_readiness",
            "schema_version": MCP_TOOL_RESULT_SCHEMA_VERSION,
            "server_name": MCP_DESKTOP_SERVER_NAME,
            "server_version": MCP_DESKTOP_SERVER_VERSION,
            "tool_count": len(self.list_tools()),
            "tools": [
                CLAUDE_DESKTOP_TOOL_ALIASES[tool.name] for tool in self.list_tools()
            ],
        }

    def _validate_handoff_request(self, arguments: Mapping[str, Any]) -> JsonDict:
        _require_args(arguments, _REQUEST_ARG, required=_REQUEST_ARG)
        return _desktop_contract_smoke.validate_handoff_request_payload(
            arguments["request"],
            schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
        )

    def _validate_handoff_response(self, arguments: Mapping[str, Any]) -> JsonDict:
        _require_args(
            arguments,
            _REQUEST_RESPONSE_ARGS,
            required=_REQUEST_RESPONSE_ARGS,
        )
        return _desktop_contract_smoke.validate_handoff_response_payload(
            arguments["request"],
            arguments["response"],
            schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
        )

    def _validate_draft_request(self, arguments: Mapping[str, Any]) -> JsonDict:
        _require_args(arguments, _REQUEST_ARG, required=_REQUEST_ARG)
        return _desktop_contract_smoke.validate_draft_request_payload(
            arguments["request"],
            schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
        )

    def _validate_draft_response(self, arguments: Mapping[str, Any]) -> JsonDict:
        _require_args(
            arguments,
            _REQUEST_RESPONSE_ARGS,
            required=_REQUEST_RESPONSE_ARGS,
        )
        return _desktop_contract_smoke.validate_draft_response_payload(
            arguments["request"],
            arguments["response"],
            schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
        )

    def _run_contract_smoke(self, arguments: Mapping[str, Any]) -> JsonDict:
        _require_args(arguments, _NO_ARGS, required=_NO_ARGS)
        checks = _desktop_contract_smoke.run_contract_smoke(
            schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION
        )
        return {
            "auto_publish_allowed": False,
            "checks": checks,
            "network_calls": False,
            "ok": True,
            "provider_calls": False,
            "public_output_approved": False,
            "ready_for_real_ticket_use": False,
            "result_kind": "contract_smoke",
            "schema_version": MCP_TOOL_RESULT_SCHEMA_VERSION,
            "smoke_ok": True,
            "writes_files": False,
        }

    def _run_approved_summary_pipeline(self, arguments: Mapping[str, Any]) -> JsonDict:
        try:
            execution = _execute_approved_summary_pipeline(arguments)
        except ApprovedSummaryPipelineStageError as exc:
            return _desktop_authoring_pipeline.pipeline_failure_result(
                failure_stage=exc.failure_stage,
                debug_code=exc.debug_code,
                schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
            )
        return _approved_summary_pipeline_status(execution)

    def _author_approved_summary(self, arguments: Mapping[str, Any]) -> JsonDict:
        try:
            execution = _execute_approved_summary_pipeline(arguments)
        except ApprovedSummaryPipelineStageError as exc:
            return _approved_summary_author_failure_result(
                failure_stage=exc.failure_stage,
                debug_code=exc.debug_code,
            )
        return _approved_summary_author_result(execution)

    def _author_ticket(self, arguments: Mapping[str, Any]) -> JsonDict:
        ticket_ref = _approved_ticket_ref_from_arguments(arguments)
        try:
            approved_arguments = _approved_ticket_author_arguments(arguments)
            execution = _execute_approved_summary_pipeline(approved_arguments)
        except ApprovedSummaryPipelineStageError as exc:
            return _approved_ticket_author_failure_result(
                ticket_ref=ticket_ref,
                failure_stage=exc.failure_stage,
                debug_code=exc.debug_code,
            )
        result = _approved_summary_author_result(execution)
        result["result_kind"] = "approved_ticket_authoring"
        result["ticket_ref"] = ticket_ref
        result["approved_summary_source"] = "local_approved_summary"
        return result

    def _register_clean_ticket(self, arguments: Mapping[str, Any]) -> JsonDict:
        try:
            return _desktop_ticket_ref.register_clean_ticket_arguments(arguments)
        except ApprovedSummaryInputError as exc:
            debug_code = exc.debug_code
        except ContractValidationError:
            debug_code = "clean_ticket_text_invalid"
        return {
            "auto_publish_allowed": False,
            "debug_code": debug_code,
            "failure_stage": "input_validation",
            "network_calls": False,
            "ok": False,
            "pipeline_ok": False,
            "public_output_approved": False,
            "ready_for_real_ticket_use": False,
            "result_kind": "clean_ticket_registration",
            "schema_version": MCP_TOOL_RESULT_SCHEMA_VERSION,
            "writes_files": False,
        }

    def _draft_article(self, arguments: Mapping[str, Any]) -> JsonDict:
        try:
            primary_result = self._draft_article_primary_surface_result(
                arguments
            )
            result = (
                primary_result
                if primary_result is not None
                else _approved_summary_author_failure_result(
                    failure_stage="input_validation",
                    debug_code="draft_article_call_shape_invalid",
                )
            )
        except (
            ContractValidationError,
            McpArgumentError,
            _desktop_draft_arguments.DraftArticleArgumentError,
        ):
            result = _approved_summary_author_failure_result(
                failure_stage="input_validation",
                debug_code="draft_article_args_invalid",
            )
        result["result_kind"] = "draft_article_authoring"
        return result

    def _draft_article_after_selection(
        self,
        draft_arguments: Mapping[str, Any],
    ) -> JsonDict:
        draft_arguments = (
            _desktop_draft_arguments.draft_article_without_operator_selection_fields(
                draft_arguments
            )
        )
        if _desktop_draft_arguments.has_approved_summary_authoring_input(
            draft_arguments
        ):
            return self._author_approved_summary(
                _desktop_draft_arguments.draft_article_without_uploaded_ticket_ref(
                    draft_arguments
                )
            )
        if "ticket_ref" in draft_arguments:
            return self._author_ticket(draft_arguments)
        return _approved_summary_author_failure_result(
            failure_stage="input_validation",
            debug_code="draft_article_input_missing",
        )

    def _new_pending_draft_selection(
        self,
        item_candidates: list[JsonDict],
        *,
        approved_summary_text: str,
    ) -> PendingDraftSelection:
        return self._draft_workflow.start_pending_selection(
            item_candidates,
            approved_summary_text=approved_summary_text,
        )

    def _draft_article_primary_surface_result(
        self,
        arguments: Mapping[str, Any],
    ) -> JsonDict | None:
        if not set(arguments).issubset(
            _desktop_draft_arguments.DRAFT_ARTICLE_DESKTOP_PRIMARY_ARGS
        ):
            return None
        has_summary = bool(arguments.get("approved_summary_text"))
        has_selection_ref = bool(arguments.get("operator_selection_ref"))
        has_selected_item_ref = bool(arguments.get("operator_selected_item_ref"))
        has_ticket_ref = bool(arguments.get("ticket_ref"))
        if (
            has_summary
            and not has_selection_ref
            and not has_selected_item_ref
            and not has_ticket_ref
        ):
            return self._draft_article_from_primary_summary(arguments)
        if (
            has_ticket_ref
            and not has_summary
            and not has_selection_ref
            and not has_selected_item_ref
        ):
            return self._draft_article_from_primary_ticket_ref(arguments)
        if (
            has_selection_ref
            and has_selected_item_ref
            and not has_summary
            and not has_ticket_ref
        ):
            return self._draft_article_from_primary_selection(arguments)
        return _approved_summary_author_failure_result(
            failure_stage="input_validation",
            debug_code="draft_article_call_shape_invalid",
        )

    def _draft_article_from_primary_summary(
        self,
        arguments: Mapping[str, Any],
    ) -> JsonDict:
        approved_summary_text = _desktop_payload.approved_summary_text_argument(
            arguments
        )
        try:
            candidates = _desktop_draft_arguments.draft_article_candidates_with_refs(
                self._draft_workflow.item_candidates_from_summary(
                    approved_summary_text
                )
            )
        except SemanticExtractionProviderUnavailableError:
            return semantic_provider_unavailable_result(
                schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
            )
        except NoSemanticCandidatesError:
            return _approved_summary_author_failure_result(
                failure_stage="semantic_extraction",
                debug_code="semantic_extraction_no_candidates",
            )
        except (ContractValidationError, McpArgumentError, ValueError):
            return _approved_summary_author_failure_result(
                failure_stage="semantic_extraction",
                debug_code="semantic_extraction_output_invalid",
            )
        if not candidates:
            return _approved_summary_author_failure_result(
                failure_stage="semantic_extraction",
                debug_code="semantic_extraction_no_candidates",
            )
        if len(candidates) > 1:
            result = _desktop_draft_arguments.draft_article_split_required_result(
                {"item_candidates": candidates},
                schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
            )
            if result is None:  # pragma: no cover - defensive invariant
                return _approved_summary_author_failure_result(
                    failure_stage="semantic_extraction",
                    debug_code="semantic_extraction_output_invalid",
                )
            pending_selection = self._new_pending_draft_selection(
                candidates,
                approved_summary_text=approved_summary_text,
            )
            attach_pending_selection(
                result,
                pending_selection,
                submit_tool=claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
            )
            return result
        return self._draft_article_primary_author_result(
            _desktop_draft_arguments.draft_article_authoring_args_from_candidate(
                approved_summary_text=approved_summary_text,
                candidate=candidates[0],
                debug=arguments.get("debug") is True,
            )
        )

    def _draft_article_from_primary_ticket_ref(
        self,
        arguments: Mapping[str, Any],
    ) -> JsonDict:
        ticket_ref = _approved_ticket_ref_from_arguments(arguments)
        try:
            approved_arguments = _approved_ticket_author_arguments(arguments)
        except ApprovedSummaryPipelineStageError as exc:
            return _approved_ticket_author_failure_result(
                ticket_ref=ticket_ref,
                failure_stage="input_validation",
                debug_code=exc.debug_code,
            )
        if _desktop_draft_arguments.has_structured_approved_summary_item_input(
            approved_arguments
        ):
            result = self._author_ticket(arguments)
            finalized = finalize_author_result_with_bundle(
                result,
                bundle_root=self._reviewer_bundle_root,
                include_reviewer_only_html=arguments.get("debug") is True,
                schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
            )
            finalized["approved_summary_source"] = "local_approved_summary"
            finalized["ticket_ref"] = ticket_ref
            return finalized
        summary_arguments: JsonDict = {
            "approved_summary_text": approved_arguments["approved_summary_text"],
        }
        if arguments.get("debug") is True:
            summary_arguments["debug"] = True
        result = self._draft_article_from_primary_summary(summary_arguments)
        result["approved_summary_source"] = "local_clean_ticket"
        result["ticket_ref"] = ticket_ref
        return result

    def _draft_article_from_primary_selection(
        self,
        arguments: Mapping[str, Any],
    ) -> JsonDict:
        pending_selection = self._draft_workflow.pending_selection
        if pending_selection is None:
            return operator_selection_unavailable_result(
                schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
            )
        selection_ref = arguments.get("operator_selection_ref")
        selected_item_ref = arguments.get("operator_selected_item_ref")
        try:
            candidate = self._draft_workflow.selected_candidate(
                selection_ref=selection_ref,
                selected_item_ref=selected_item_ref,
            )
        except OperatorSelectionExpiredError:
            return operator_selection_expired_result(
                schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
            )
        except OperatorSelectionUnavailableError:
            return operator_selection_unavailable_result(
                schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
            )
        except OperatorSelectionInvalidError:
            return _desktop_draft_arguments.draft_article_selection_error_result(
                arguments,
                pending_selection,
                schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
                submit_tool=claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
            )
        return self._draft_article_primary_author_result(
            _desktop_draft_arguments.draft_article_authoring_args_from_candidate(
                approved_summary_text=pending_selection.approved_summary_text,
                candidate=candidate,
                debug=arguments.get("debug") is True,
            )
        )

    def _draft_article_primary_author_result(
        self,
        arguments: Mapping[str, Any],
    ) -> JsonDict:
        result = self._author_approved_summary(arguments)
        return finalize_author_result_with_bundle(
            result,
            bundle_root=self._reviewer_bundle_root,
            include_reviewer_only_html=arguments.get("debug") is True,
            schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
        )

    def _support_get_behavior_instructions(
        self,
        arguments: Mapping[str, Any],
    ) -> JsonDict:
        _require_args(arguments, _NO_ARGS, required=frozenset())
        return {
            "auto_publish_allowed": False,
            "network_calls": False,
            "ok": True,
            "public_output_approved": False,
            "result_kind": "behavior_instructions",
            "schema_version": MCP_TOOL_RESULT_SCHEMA_VERSION,
            "should_be_kcs_article": True,
            "validation_ok": True,
            "writes_files": False,
        }


def _execute_approved_summary_pipeline(
    arguments: Mapping[str, Any],
) -> _desktop_workflow.ApprovedSummaryExecution:
    try:
        return _desktop_authoring_pipeline.execute_pipeline(arguments)
    except _desktop_authoring_pipeline.DesktopAuthoringArgumentError:
        raise McpArgumentError("Invalid approved summary arguments.") from None


def _approved_summary_pipeline_status(
    execution: _desktop_workflow.ApprovedSummaryExecution,
) -> JsonDict:
    return _desktop_authoring_pipeline.pipeline_status_result(
        execution,
        schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
    )


def _approved_summary_author_result(
    execution: _desktop_workflow.ApprovedSummaryExecution,
) -> JsonDict:
    return _desktop_authoring_pipeline.author_result(
        execution,
        schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
    )


def _approved_summary_author_failure_result(
    *,
    failure_stage: str,
    debug_code: str,
) -> JsonDict:
    return _desktop_authoring_pipeline.author_failure_result(
        failure_stage=failure_stage,
        debug_code=debug_code,
        schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
    )


def _approved_ticket_author_failure_result(
    *,
    ticket_ref: str,
    failure_stage: str,
    debug_code: str,
) -> JsonDict:
    return _desktop_authoring_pipeline.ticket_author_failure_result(
        ticket_ref=ticket_ref,
        failure_stage=failure_stage,
        debug_code=debug_code,
        schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
    )


class McpStdioTransport:
    """Line-delimited JSON-RPC stdio transport for Claude Desktop."""

    def __init__(
        self,
        *,
        adapter: KcsDesktopMcpAdapter | None = None,
        tool_name_style: str = TOOL_NAME_STYLE_DESKTOP_ALIASES,
    ) -> None:
        if tool_name_style not in {
            TOOL_NAME_STYLE_DESKTOP_ALIASES,
            TOOL_NAME_STYLE_CANONICAL,
        }:
            raise ValueError("Unsupported MCP tool name style.")
        visible_tools = (
            DESKTOP_OPERATOR_TOOLS
            if tool_name_style == TOOL_NAME_STYLE_DESKTOP_ALIASES
            else None
        )
        self._adapter = adapter or KcsDesktopMcpAdapter(visible_tools=visible_tools)
        self._tool_name_style = tool_name_style
        self._initialize_responded = False
        self._ready = False

    def handle_message(self, message: object) -> JsonDict | None:
        """Handle one JSON-RPC message."""

        parsed = _desktop_jsonrpc.parse_jsonrpc_message(message)
        if parsed.error_code is not None:
            if parsed.is_notification:
                return None
            return _desktop_jsonrpc.error_response(
                parsed.request_id,
                parsed.error_code,
                "Invalid JSON-RPC request.",
            )
        request_id = parsed.request_id
        method = parsed.method
        params = parsed.params
        is_notification = parsed.is_notification
        if is_notification:
            return self._handle_notification(method)
        if not self._ready and method not in {"initialize", "ping"}:
            return _desktop_jsonrpc.error_response(
                request_id,
                _desktop_jsonrpc.SERVER_NOT_INITIALIZED,
                "MCP transport is not initialized.",
            )

        result = self._handle_request(
            method=method,
            params=params,
            request_id=request_id,
        )
        if _desktop_jsonrpc.is_error_response(result):
            return result
        if result is _METHOD_NOT_FOUND:
            return _desktop_jsonrpc.error_response(
                request_id,
                _desktop_jsonrpc.METHOD_NOT_FOUND,
                "Unknown method.",
            )
        return {
            "jsonrpc": _desktop_jsonrpc.JSONRPC_VERSION,
            "id": request_id,
            "result": result,
        }

    def _handle_request(
        self,
        *,
        method: str,
        params: object,
        request_id: object,
    ) -> object:
        try:
            return self._dispatch(method=method, params=params)
        except McpArgumentError:
            return _desktop_jsonrpc.error_response(
                request_id,
                _desktop_jsonrpc.INVALID_PARAMS,
                "Invalid tool arguments.",
            )
        except ValueError:
            return _desktop_jsonrpc.error_response(
                request_id,
                _desktop_jsonrpc.INVALID_PARAMS,
                "Invalid params.",
            )
        except Exception:  # pragma: no cover - defensive transport boundary
            return _desktop_jsonrpc.error_response(
                request_id,
                _desktop_jsonrpc.INTERNAL_ERROR,
                "Internal transport error.",
            )

    def _handle_notification(self, method: str) -> JsonDict | None:
        if method == "notifications/initialized":
            if self._initialize_responded:
                self._ready = True
            return None
        return None

    def _dispatch(self, *, method: str, params: object) -> object:
        if method == "initialize":
            return self._initialize(params)
        if method in _desktop_jsonrpc.EMPTY_PARAM_METHOD_RESULTS:
            _desktop_jsonrpc.require_empty_params(params)
            return dict(_desktop_jsonrpc.EMPTY_PARAM_METHOD_RESULTS[method])
        if method == "tools/list":
            _desktop_jsonrpc.require_empty_params(params)
            return {
                "tools": [
                    self._tool_descriptor_payload(tool)
                    for tool in self._adapter.list_tools()
                ]
            }
        if method == "tools/call":
            return self._call_tool(params)
        return _METHOD_NOT_FOUND

    def _initialize(self, params: object) -> JsonDict:
        params_obj = _desktop_jsonrpc.require_initialize_params(params)
        protocol_version = params_obj.get("protocolVersion")
        result = _desktop_protocol.initialize_result(protocol_version)
        self._initialize_responded = True
        return result

    def _call_tool(self, params: object) -> JsonDict:
        params_obj = _desktop_jsonrpc.require_object_params(params)
        if any(key not in {"arguments", "name"} for key in params_obj):
            raise McpArgumentError("Unexpected tool call parameter.")
        name = params_obj.get("name")
        if not isinstance(name, str) or not name:
            raise McpArgumentError("Invalid tool name.")
        canonical_name = self._canonical_tool_name(name)
        available = {tool.name: tool for tool in self._adapter.list_tools()}
        descriptor = available.get(canonical_name)
        if descriptor is None:
            raise McpArgumentError("Unknown tool.")
        arguments = params_obj.get("arguments", {})
        if not isinstance(arguments, Mapping):
            raise McpArgumentError("Invalid tool arguments.")
        result = self._adapter.call_tool(canonical_name, arguments)
        try:
            return _mcp_tool_response(descriptor=descriptor, result=result)
        except ContractValidationError:
            return _mcp_tool_response(
                descriptor=descriptor,
                result=_tool_error("tool_result_invalid"),
            )

    def _tool_descriptor_payload(self, tool: McpToolDescriptor) -> JsonDict:
        external = replace(tool, name=self._external_tool_name(tool.name))
        payload = asdict(external)
        descriptor = {
            "annotations": payload["annotations"],
            "description": payload["description"],
            "inputSchema": _desktop_tool_schemas.desktop_input_schema(
                payload["input_schema"]
            ),
            "name": payload["name"],
        }
        if self._tool_name_style == TOOL_NAME_STYLE_CANONICAL:
            descriptor["outputSchema"] = payload["output_schema"]
        return descriptor

    def _external_tool_name(self, name: str) -> str:
        if self._tool_name_style == TOOL_NAME_STYLE_DESKTOP_ALIASES:
            return claude_desktop_tool_alias(name)
        return name

    def _canonical_tool_name(self, name: str) -> str:
        if self._tool_name_style == TOOL_NAME_STYLE_DESKTOP_ALIASES:
            return CANONICAL_TOOL_BY_CLAUDE_DESKTOP_ALIAS.get(name, name + "__invalid")
        return name


class _MethodNotFound:
    pass


_METHOD_NOT_FOUND = _MethodNotFound()


def serve_stdio(
    *,
    input_stream: Iterable[str | bytes] | None = None,
    output_stream: IO[str] | None = None,
    tool_name_style: str = TOOL_NAME_STYLE_DESKTOP_ALIASES,
) -> None:
    """Serve newline-delimited JSON-RPC over stdio-compatible streams."""

    transport = McpStdioTransport(tool_name_style=tool_name_style)
    input_stream = input_stream or sys.stdin
    output_stream = output_stream or sys.stdout
    for raw_line in input_stream:
        response = _desktop_jsonrpc.handle_stdio_line(transport, raw_line)
        if response is not None:
            output_stream.write(_desktop_jsonrpc.compact_json(response) + "\n")
            output_stream.flush()


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


def _approved_ticket_author_arguments(arguments: Mapping[str, Any]) -> JsonDict:
    try:
        return _desktop_authoring_pipeline.ticket_author_arguments(arguments)
    except _desktop_authoring_pipeline.DesktopAuthoringArgumentError:
        raise McpArgumentError("Invalid approved ticket arguments.") from None


def _approved_ticket_ref_from_arguments(arguments: Mapping[str, Any]) -> str:
    return _desktop_authoring_pipeline.ticket_ref_from_arguments(arguments)


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
