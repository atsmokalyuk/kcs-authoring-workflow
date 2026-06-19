"""Claude Desktop MCP stdio adapter for KCS validator/control tools."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import IO, Any

from kcs_adapters import desktop_authoring_pipeline as _desktop_authoring_pipeline
from kcs_adapters import desktop_contract_smoke as _desktop_contract_smoke
from kcs_adapters import desktop_draft_arguments as _desktop_draft_arguments
from kcs_adapters import desktop_payload as _desktop_payload
from kcs_adapters import desktop_ticket_ref as _desktop_ticket_ref
from kcs_adapters import desktop_tool_results as _desktop_tool_results
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
from kcs_core.sanitizer import ensure_safe_sanitized_payload
from kcs_core.semantic_extraction import SemanticExtractionProvider

MCP_PROTOCOL_VERSION = "2025-11-25"
MCP_SUPPORTED_PROTOCOL_VERSIONS = ("2025-06-18", MCP_PROTOCOL_VERSION)
MCP_DESKTOP_SERVER_NAME = "kcs-authoring-desktop-mcp"
MCP_DESKTOP_SERVER_VERSION = "0.1.0"
MCP_TOOL_RESULT_SCHEMA_VERSION = "kcs_mcp_tool_result_v1"

JSONRPC_VERSION = "2.0"
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
SERVER_NOT_INITIALIZED = -32002

_MAX_JSONRPC_LINE_BYTES = 96 * 1024
_SAFE_REQUEST_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,80}")
_RESOLUTION_EXECUTABLE_DETAIL_RE = re.compile(
    r"(?:"
    r"https?://|"
    r"/[A-Za-z0-9._~:/%+\-]+|"
    r"\b(?:"
    r"awk|cat|chmod|chown|cp|curl|find|grep|head|journalctl|"
    r"ls|mkdir|mv|plesk|rm|rpm|sed|service|stat|systemctl|tail|test"
    r")\b(?:\s+[A-Za-z0-9_./:+%=-]+)+|"
    r"\b(?:click|open|select|browse|navigate)\b.*\b(?:menu|page|screen|tab|ui)\b|"
    r"\b(?:connect|log in|login)\b.*\b(?:plesk|rdp|server|ssh)\b|"
    r"\b(?:check|confirm|verify)\b.*\b(?:"
    r"data|directory|graphs?|log|metrics?|ownership|path|permissions?|"
    r"service|status"
    r")\b"
    r")",
    re.I,
)
_RESOLUTION_INFORMATIONAL_DETAIL_RE = re.compile(
    r"\b(?:advise|inform|note|warn)\b|"
    r"\b(?:historical|older|previous)\s+data\b|"
    r"\b(?:will|may)\s+not\s+(?:appear|backfill|be\s+visible)\b|"
    r"\b(?:repopulate|populate)\s+gradually\b",
    re.I,
)
_RESOLUTION_DESTRUCTIVE_STEP_RE = re.compile(
    r"\brm\s+(?:-[A-Za-z]*r[A-Za-z]*f[A-Za-z]*|"
    r"-[A-Za-z]*f[A-Za-z]*r[A-Za-z]*|-[A-Za-z]*r[A-Za-z]*\s+-[A-Za-z]*f[A-Za-z]*)\s+/",
    re.I,
)
_SUPPORTED_CAUSE_UNCERTAIN_RE = re.compile(
    r"\b(?:appears?|likely|maybe|possibly|probably|seems?|suspected|unclear|unknown)\b",
    re.I,
)
_JSONRPC_ALLOWED_KEYS = frozenset({"id", "jsonrpc", "method", "params"})
_INITIALIZE_PARAM_KEYS = frozenset({"capabilities", "clientInfo", "protocolVersion"})
_INITIALIZE_FORBIDDEN_TEXT_FRAGMENTS = (
    "/users/",
    "api_key",
    "apikey",
    "attachment_url",
    "attachmenturl",
    "authorization",
    "bearer ",
    "internal_comment",
    "internalcomment",
    "raw_ticket",
    "rawticket",
    "secret=",
    "token=",
)
_REQUEST_ARG = frozenset({"request"})
_REQUEST_RESPONSE_ARGS = frozenset({"request", "response"})
_APPROVED_SUMMARY_FALSE_ONLY_ARGS = _desktop_payload.APPROVED_SUMMARY_FALSE_ONLY_ARGS
_NO_ARGS = frozenset()
_EMPTY_PARAM_METHOD_RESULTS: Mapping[str, JsonDict] = {
    "ping": {},
    "resources/list": {"resources": []},
    "resources/templates/list": {"resourceTemplates": []},
    "prompts/list": {"prompts": []},
}
_DRAFT_SELECTION_TTL_SECONDS = 15 * 60
_REVIEWER_BUNDLE_ROOT = DEFAULT_REVIEWER_BUNDLE_ROOT
_DEFAULT_SEMANTIC_EXTRACTION_PROVIDER = object()


@dataclass(frozen=True)
class _ParsedJsonRpcMessage:
    request_id: object
    method: str
    params: object
    is_notification: bool
    error_code: int | None = None


@dataclass(frozen=True)
class McpToolResult:
    """Safe adapter tool result."""

    ok: bool
    result: JsonDict | None = None
    error: str | None = None
    error_code: str | None = None


class McpArgumentError(ValueError):
    """Tool argument shape error that maps to JSON-RPC invalid params."""


ApprovedSummaryInputError = _desktop_payload.ApprovedSummaryInputError


DraftArticleSemanticExtractionProvider = SemanticExtractionProvider


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

        parsed = _parse_jsonrpc_message(message)
        if parsed.error_code is not None:
            if parsed.is_notification:
                return None
            return _error_response(
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
            return _error_response(
                request_id,
                SERVER_NOT_INITIALIZED,
                "MCP transport is not initialized.",
            )

        result = self._handle_request(
            method=method,
            params=params,
            request_id=request_id,
        )
        if _is_error_response(result):
            return result
        if result is _METHOD_NOT_FOUND:
            return _error_response(request_id, METHOD_NOT_FOUND, "Unknown method.")
        return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}

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
            return _error_response(
                request_id,
                INVALID_PARAMS,
                "Invalid tool arguments.",
            )
        except ValueError:
            return _error_response(request_id, INVALID_PARAMS, "Invalid params.")
        except Exception:  # pragma: no cover - defensive transport boundary
            return _error_response(
                request_id,
                INTERNAL_ERROR,
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
        if method in _EMPTY_PARAM_METHOD_RESULTS:
            _require_empty_params(params)
            return dict(_EMPTY_PARAM_METHOD_RESULTS[method])
        if method == "tools/list":
            _require_empty_params(params)
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
        params_obj = _require_initialize_params(params)
        protocol_version = params_obj.get("protocolVersion")
        if protocol_version not in MCP_SUPPORTED_PROTOCOL_VERSIONS:
            raise ValueError("Unsupported protocol version.")
        self._initialize_responded = True
        return {
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False},
            },
            "instructions": (
                "KCS Authoring MCP server. For sanitized support-ticket article "
                "requests, call kcs_draft_article. Prefer ticket_ref when a "
                "trusted source has saved the cleaned ticket transcript under "
                "the configured approved-summaries store. If no ref "
                "exists for an operator-provided sanitized attachment or paste, "
                "first call kcs_register_clean_ticket with the complete visible "
                "sanitized transcript, then call kcs_draft_article with the "
                "returned next_arguments. For short pasted sanitized text, "
                "kcs_draft_article may use approved_summary_text directly. Do "
                "not summarize or redact labeled sections before either tool "
                "call. A Claude Desktop file card is not a filesystem path: "
                "do not inspect upload directories, do not pass upload "
                "filenames or paths, and do not ask the operator to re-upload "
                "while visible text is available. If no visible file text is "
                "available, report file_content_unavailable and do not draft "
                "manually. Do not pass item, item_candidates, or aliases. "
                "Python validates the input and owns semantic extraction, "
                "decision, rendering, and local bundle output. The default "
                "Desktop workflow does not require Claude CLI/Code or an API "
                "key. Successful draft results include reviewer-only Zendesk "
                "HTML and compact status."
            ),
            "protocolVersion": protocol_version,
            "serverInfo": {
                "name": MCP_DESKTOP_SERVER_NAME,
                "version": MCP_DESKTOP_SERVER_VERSION,
            },
        }

    def _call_tool(self, params: object) -> JsonDict:
        params_obj = _require_object_params(params)
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
        response = _handle_stdio_line(transport, raw_line)
        if response is not None:
            output_stream.write(_compact_json(response) + "\n")
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


def _handle_stdio_line(
    transport: McpStdioTransport,
    raw_line: str | bytes,
) -> JsonDict | None:
    try:
        line = _decode_stdio_line(raw_line)
        if len(line.encode("utf-8")) > _MAX_JSONRPC_LINE_BYTES:
            return _error_response(None, PARSE_ERROR, "Parse error.")
        if not line.strip():
            return None
        message = json.loads(line, parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return _error_response(None, PARSE_ERROR, "Parse error.")
    return transport.handle_message(message)


def _decode_stdio_line(raw_line: str | bytes) -> str:
    if isinstance(raw_line, bytes):
        return raw_line.decode("utf-8")
    return raw_line


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"Invalid JSON constant: {value}")


def _mcp_tool_response(
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


def _tool_error(error_code: str) -> McpToolResult:
    return McpToolResult(
        ok=False,
        error="KCS MCP tool validation failed.",
        error_code=error_code,
    )


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


def _require_object_params(params: object) -> JsonDict:
    if params is None:
        return {}
    if not isinstance(params, dict):
        raise ValueError("JSON-RPC params must be an object.")
    return params


def _require_empty_params(params: object) -> None:
    params_obj = _require_object_params(params)
    if params_obj:
        raise ValueError("JSON-RPC params must be empty.")


def _require_initialize_params(params: object) -> JsonDict:
    params_obj = _require_object_params(params)
    if any(key not in _INITIALIZE_PARAM_KEYS for key in params_obj):
        raise ValueError("Invalid initialize params.")
    _ensure_safe_initialize_metadata(params_obj)
    return params_obj


def _ensure_safe_initialize_metadata(value: object) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("Invalid initialize params.")
            _ensure_no_initialize_private_marker(key)
            _ensure_safe_initialize_metadata(item)
        return
    if isinstance(value, list):
        for item in value:
            _ensure_safe_initialize_metadata(item)
        return
    _ensure_safe_initialize_scalar(value)


def _ensure_safe_initialize_scalar(value: object) -> None:
    if value is None or isinstance(value, bool | int):
        return
    if isinstance(value, str):
        _ensure_no_initialize_private_marker(value)
        return
    if isinstance(value, float) and math.isfinite(value):
        return
    raise ValueError("Invalid initialize params.")


def _ensure_no_initialize_private_marker(value: str) -> None:
    normalized = value.casefold()
    if "@" in normalized or "://" in normalized:
        raise ValueError("Invalid initialize params.")
    if any(fragment in normalized for fragment in _INITIALIZE_FORBIDDEN_TEXT_FRAGMENTS):
        raise ValueError("Invalid initialize params.")


def _compact_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, allow_nan=False, separators=(",", ":"))


def _is_supported_request_id(request_id: object) -> bool:
    if isinstance(request_id, bool):
        return False
    if isinstance(request_id, int):
        return True
    if isinstance(request_id, str):
        if not _SAFE_REQUEST_ID_RE.fullmatch(request_id):
            return False
        try:
            ensure_safe_sanitized_payload(request_id)
        except ContractValidationError:
            return False
        return True
    return False


def _parse_jsonrpc_message(message: object) -> _ParsedJsonRpcMessage:
    if not isinstance(message, dict):
        return _ParsedJsonRpcMessage(None, "", {}, False, INVALID_REQUEST)
    if any(key not in _JSONRPC_ALLOWED_KEYS for key in message):
        return _ParsedJsonRpcMessage(None, "", {}, False, INVALID_REQUEST)
    request_id = message.get("id")
    is_notification = "id" not in message
    if "id" in message and not _is_supported_request_id(request_id):
        return _ParsedJsonRpcMessage(None, "", {}, False, INVALID_REQUEST)
    method = message.get("method")
    if message.get("jsonrpc") != JSONRPC_VERSION or not isinstance(method, str):
        return _ParsedJsonRpcMessage(
            request_id,
            "",
            {},
            is_notification,
            INVALID_REQUEST,
        )
    return _ParsedJsonRpcMessage(
        request_id,
        method,
        message.get("params", {}),
        is_notification,
    )


def _is_error_response(value: object) -> bool:
    return (
        isinstance(value, dict)
        and "error" in value
        and value.get("jsonrpc") == "2.0"
    )


def _error_response(request_id: object, code: int, message: str) -> JsonDict:
    return {
        "error": {"code": code, "message": message},
        "id": request_id,
        "jsonrpc": JSONRPC_VERSION,
    }


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
