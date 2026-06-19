"""Claude Desktop MCP stdio adapter for KCS validator/control tools."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from pathlib import Path
from typing import IO, Any

from kcs_adapters import desktop_payload as _desktop_payload
from kcs_adapters import desktop_ticket_ref as _desktop_ticket_ref
from kcs_adapters import desktop_workflow as _desktop_workflow
from kcs_adapters.desktop_reviewer_bundle import (
    DEFAULT_REVIEWER_BUNDLE_ROOT,
    reviewer_bundle_root_from_environment,
)
from kcs_adapters.desktop_workflow import (
    ApprovedSummaryExecution,
    ApprovedSummaryPipelineHooks,
    ApprovedSummaryPipelineStageError,
    DesktopDraftWorkflow,
    NoSemanticCandidatesError,
    OperatorSelectionExpiredError,
    OperatorSelectionInvalidError,
    OperatorSelectionUnavailableError,
    PendingDraftSelection,
    SemanticExtractionProviderUnavailableError,
    approved_summary_pipeline_status,
    attach_pending_selection,
    draft_author_failure_result,
    execute_approved_summary_pipeline,
    finalize_author_result_with_bundle,
    operator_selection_expired_result,
    operator_selection_unavailable_result,
    selection_error_result,
    semantic_provider_from_environment,
    semantic_provider_unavailable_result,
    split_required_result,
)
from kcs_core.claude_draft import (
    CLAUDE_DRAFT_REQUEST_SCHEMA_VERSION,
    CLAUDE_DRAFT_RESPONSE_SCHEMA_VERSION,
    ClaudeDraftProviderErrorCode,
    ClaudeDraftStatus,
    KcsClaudeDraftRequestPacket,
    build_claude_draft_request,
    validate_claude_draft_response,
)
from kcs_core.claude_handoff import (
    CLAUDE_HANDOFF_REQUEST_SCHEMA_VERSION,
    CLAUDE_HANDOFF_RESPONSE_SCHEMA_VERSION,
    ClaudeHandoffProviderErrorCode,
    ClaudeHandoffProviderStatus,
    KcsClaudeHandoffRequestPacket,
    validate_claude_handoff_response,
)
from kcs_core.decision import decide_kcs_action
from kcs_core.errors import ContractValidationError
from kcs_core.evidence_builder import (
    EvidenceBuildPolicy,
    build_evidence_packet_from_zendesk_export,
)
from kcs_core.json_payload import (
    JsonDict,
    JsonPayload,
    dumps_payload,
    require_json_object,
)
from kcs_core.models import (
    ArticleType,
    DecisionStatus,
    KcsActionDecisionPacket,
    KcsReviewerPacket,
    KcsValidationReportPacket,
    NormalizedTicketEvidencePacket,
    ReadinessState,
    RecommendedAction,
    ReuseSearchResultsPacket,
)
from kcs_core.readiness import build_validation_report
from kcs_core.renderer import render_reviewer_packet
from kcs_core.safety import InputClass, SafetyGateResult, validate_evidence_safety
from kcs_core.sanitizer import ensure_safe_sanitized_payload
from kcs_core.semantic_extraction import SemanticExtractionProvider
from kcs_core.validation import EvidenceValidationResult, validate_evidence_packet

_approved_summary_open_questions = _desktop_workflow.approved_summary_open_questions
_approved_summary_public_candidate = _desktop_workflow.approved_summary_public_candidate
_approved_summary_quality_gaps = _desktop_workflow.approved_summary_quality_gaps
_approved_summary_reuse_search_status = (
    _desktop_workflow.approved_summary_reuse_search_status
)
_approved_summary_reuse_was_checked = (
    _desktop_workflow.approved_summary_reuse_was_checked
)
_approved_summary_reviewer_only_draft = (
    _desktop_workflow.approved_summary_reviewer_only_draft
)
_approved_summary_reviewer_only_html = (
    _desktop_workflow.approved_summary_reviewer_only_html
)
_approved_summary_reviewer_only_preview = (
    _desktop_workflow.approved_summary_reviewer_only_preview
)
_approved_summary_reviewer_only_preview_text = (
    _desktop_workflow.approved_summary_reviewer_only_preview_text
)
_require_approved_summary_false_only_args = (
    _desktop_payload.require_approved_summary_false_only_args
)
_safe_candidate_list = _desktop_workflow.safe_candidate_list
_safe_candidate_string = _desktop_workflow.safe_candidate_string

MCP_PROTOCOL_VERSION = "2025-11-25"
MCP_SUPPORTED_PROTOCOL_VERSIONS = ("2025-06-18", MCP_PROTOCOL_VERSION)
MCP_DESKTOP_SERVER_NAME = "kcs-authoring-desktop-mcp"
MCP_DESKTOP_SERVER_VERSION = "0.1.0"
MCP_TOOL_RESULT_SCHEMA_VERSION = "kcs_mcp_tool_result_v1"

TOOL_NAME_STYLE_DESKTOP_ALIASES = "claude_desktop_aliases"
TOOL_NAME_STYLE_CANONICAL = "canonical"

TOOL_GET_POLICY_SUMMARY = "kcs.get_policy_summary"
TOOL_GET_MCP_READINESS = "kcs.get_mcp_readiness"
TOOL_VALIDATE_HANDOFF_REQUEST = "kcs.validate_handoff_request"
TOOL_VALIDATE_HANDOFF_RESPONSE = "kcs.validate_handoff_response"
TOOL_VALIDATE_DRAFT_REQUEST = "kcs.validate_draft_request"
TOOL_VALIDATE_DRAFT_RESPONSE = "kcs.validate_draft_response"
TOOL_RUN_CONTRACT_SMOKE = "kcs.run_contract_smoke"
TOOL_RUN_APPROVED_SUMMARY_PIPELINE = "kcs.run_approved_summary_pipeline"
TOOL_AUTHOR_APPROVED_SUMMARY = "kcs.author_approved_summary"
TOOL_AUTHOR_TICKET = "kcs.author_ticket"
TOOL_REGISTER_CLEAN_TICKET = "kcs.register_clean_ticket"
TOOL_DRAFT_ARTICLE = "kcs.draft_article"
TOOL_SUPPORT_GET_BEHAVIOR_INSTRUCTIONS = "support.get_behavior_instructions"
DESKTOP_OPERATOR_TOOLS = frozenset(
    {
        TOOL_REGISTER_CLEAN_TICKET,
        TOOL_DRAFT_ARTICLE,
        TOOL_SUPPORT_GET_BEHAVIOR_INSTRUCTIONS,
    }
)

CLAUDE_DESKTOP_TOOL_ALIASES = {
    TOOL_GET_POLICY_SUMMARY: "kcs_get_policy_summary",
    TOOL_GET_MCP_READINESS: "kcs_get_mcp_readiness",
    TOOL_VALIDATE_HANDOFF_REQUEST: "kcs_validate_handoff_request",
    TOOL_VALIDATE_HANDOFF_RESPONSE: "kcs_validate_handoff_response",
    TOOL_VALIDATE_DRAFT_REQUEST: "kcs_validate_draft_request",
    TOOL_VALIDATE_DRAFT_RESPONSE: "kcs_validate_draft_response",
    TOOL_RUN_CONTRACT_SMOKE: "kcs_run_contract_smoke",
    TOOL_RUN_APPROVED_SUMMARY_PIPELINE: "kcs_run_approved_summary_pipeline",
    TOOL_AUTHOR_APPROVED_SUMMARY: "kcs_author_approved_summary",
    TOOL_AUTHOR_TICKET: "kcs_author_ticket",
    TOOL_REGISTER_CLEAN_TICKET: "kcs_register_clean_ticket",
    TOOL_DRAFT_ARTICLE: "kcs_draft_article",
    TOOL_SUPPORT_GET_BEHAVIOR_INSTRUCTIONS: "support_get_behavior_instructions",
}
CANONICAL_TOOL_BY_CLAUDE_DESKTOP_ALIAS = {
    alias: canonical for canonical, alias in CLAUDE_DESKTOP_TOOL_ALIASES.items()
}

JSONRPC_VERSION = "2.0"
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
SERVER_NOT_INITIALIZED = -32002

_MAX_JSONRPC_LINE_BYTES = 96 * 1024
_MAX_TOOL_RESULT_BYTES = 32 * 1024
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
_DRAFT_ARTICLE_ARGS = frozenset(
    {
        "approved_summary_text",
        "auto_publish_allowed",
        "case_ref",
        "customer_replies",
        "debug",
        "item",
        "item_candidates",
        "network_calls",
        "operator_choice_confirmed",
        "operator_selected_item_ref",
        "operator_selection_ref",
        "provider_calls",
        "public_output_approved",
        "publishes",
        "ready_for_real_ticket_use",
        "reference_article",
        "reference_article_html",
        "reference_article_text",
        "reuse_search_checked",
        "reuse_search_run_ref",
        "ticket_ref",
        "writes_files",
    }
)
_DRAFT_ARTICLE_DESKTOP_PRIMARY_ARGS = frozenset(
    {
        "approved_summary_text",
        "debug",
        "operator_selected_item_ref",
        "operator_selection_ref",
        "ticket_ref",
    }
)
_DRAFT_ARTICLE_ITEM_CANDIDATE_FIELDS = frozenset(
    {
        "applicable_to",
        "article_type",
        "confirmed_facts",
        "environment",
        "item_ref",
        "question",
        "reason",
        "resolution_steps",
        "supported_answer",
        "supported_cause",
        "supported_resolution_or_workaround",
        "summary",
        "symptoms",
        "title",
    }
)
_DRAFT_ARTICLE_ITEM_METADATA_FIELDS = frozenset({"item_ref", "reason"})
_APPROVED_SUMMARY_PIPELINE_ARGS = _desktop_payload.APPROVED_SUMMARY_PIPELINE_ARGS
_APPROVED_SUMMARY_ITEM_FIELDS = _desktop_payload.APPROVED_SUMMARY_ITEM_FIELDS
_APPROVED_SUMMARY_ENVIRONMENT_FIELDS = (
    _desktop_payload.APPROVED_SUMMARY_ENVIRONMENT_FIELDS
)
_APPROVED_SUMMARY_NORMALIZED_ENVIRONMENT_FIELDS = (
    _desktop_payload.APPROVED_SUMMARY_NORMALIZED_ENVIRONMENT_FIELDS
)
_APPROVED_SUMMARY_TOP_LEVEL_ITEM_FIELDS = (
    _desktop_payload.APPROVED_SUMMARY_TOP_LEVEL_ITEM_FIELDS
)
_NO_ARGS = frozenset()
_EMPTY_PARAM_METHOD_RESULTS: Mapping[str, JsonDict] = {
    "ping": {},
    "resources/list": {"resources": []},
    "resources/templates/list": {"resourceTemplates": []},
    "prompts/list": {"prompts": []},
}
_RESULT_FORBIDDEN_FRAGMENTS = (
    "article_body",
    "attachment_url",
    "audio",
    "draft_artifact",
    "embedded_resource",
    "evidence_basis",
    "file://",
    "image",
    "internal_comment",
    "local_path",
    "raw_comment",
    "raw_ticket",
    "raw_validation_payload",
    "redaction_map",
    "resource_link",
    "reviewer_packet",
    "reviewer_only_draft_artifact",
    "zendesk_source_html",
)
_RESULT_FORBIDDEN_COMPACT_FRAGMENTS = (
    "articlebody",
    "attachmenturl",
    "draftartifact",
    "embeddedresource",
    "localpath",
    "rawvalidationpayload",
    "resourcelink",
    "revieweronlydraftartifact",
    "zendesksourcehtml",
)
_RESULT_FORBIDDEN_EXACT_KEYS = frozenset({"resource"})
_TOOL_RESULT_HTML_FIELDS = frozenset({"reviewer_only_html"})
_APPROVED_HTML_URL_REFS = {
    "https://support.plesk.com/hc/en-us/articles/"
    "12377512781975-How-to-connect-to-a-Plesk-server-via-SSH": "approved-ssh-kb-ref",
    (
        "https://support.plesk.com/hc/en-us/articles/"
        "12377247797271-How-to-connect-to-a-Plesk-server-via-RDP-with-available-"
        "credentials"
    ): "approved-rdp-kb-ref",
}
_HTML_URL_RE = re.compile(r"https?://[^\"'\\s<>]+", re.I)
_FORBIDDEN_TEXT_HTML_TAG_RE = re.compile(
    r"</\s*[a-z][a-z0-9:-]*\b|<\s*(?:a|br|div|h1|h2|h3|li|ol|p|pre|ul)\b",
    re.I,
)
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
class McpToolDescriptor:
    """MCP-compatible tool descriptor subset."""

    name: str
    description: str
    input_schema: JsonDict
    output_schema: JsonDict
    annotations: JsonDict


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
ApprovedSummaryPayloadArgumentError = (
    _desktop_payload.ApprovedSummaryPayloadArgumentError
)


DraftArticleSemanticExtractionProvider = SemanticExtractionProvider
_ApprovedSummaryExecution = ApprovedSummaryExecution


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
            tools = (
                _policy_summary_descriptor(),
                _readiness_descriptor(),
                _validate_handoff_request_descriptor(),
                _validate_handoff_response_descriptor(),
                _validate_draft_request_descriptor(),
                _validate_draft_response_descriptor(),
                _contract_smoke_descriptor(),
                _approved_summary_pipeline_descriptor(),
                _author_approved_summary_descriptor(),
                _author_ticket_descriptor(),
                _register_clean_ticket_descriptor(),
                _draft_article_descriptor(),
                _support_get_behavior_instructions_descriptor(),
            )
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
        except McpArgumentError:
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
        request = KcsClaudeHandoffRequestPacket.from_json_dict(arguments["request"])
        return _handoff_request_summary(request)

    def _validate_handoff_response(self, arguments: Mapping[str, Any]) -> JsonDict:
        _require_args(
            arguments,
            _REQUEST_RESPONSE_ARGS,
            required=_REQUEST_RESPONSE_ARGS,
        )
        request = KcsClaudeHandoffRequestPacket.from_json_dict(arguments["request"])
        response = validate_claude_handoff_response(
            arguments["response"],
            request=request,
        )
        return _handoff_response_summary(request, response)

    def _validate_draft_request(self, arguments: Mapping[str, Any]) -> JsonDict:
        _require_args(arguments, _REQUEST_ARG, required=_REQUEST_ARG)
        request = KcsClaudeDraftRequestPacket.from_json_dict(arguments["request"])
        return _draft_request_summary(request)

    def _validate_draft_response(self, arguments: Mapping[str, Any]) -> JsonDict:
        _require_args(
            arguments,
            _REQUEST_RESPONSE_ARGS,
            required=_REQUEST_RESPONSE_ARGS,
        )
        request = KcsClaudeDraftRequestPacket.from_json_dict(arguments["request"])
        response = validate_claude_draft_response(
            arguments["response"],
            request=request,
        )
        return _draft_response_summary(request, response)

    def _run_contract_smoke(self, arguments: Mapping[str, Any]) -> JsonDict:
        _require_args(arguments, _NO_ARGS, required=_NO_ARGS)
        handoff_request = _synthetic_handoff_request()
        handoff_response = validate_claude_handoff_response(
            _synthetic_handoff_response(handoff_request),
            request=handoff_request,
        )
        draft_request = build_claude_draft_request(
            handoff_request,
            draft_ref="draft-001",
        )
        draft_response = validate_claude_draft_response(
            _synthetic_draft_response(draft_request),
            request=draft_request,
        )
        checks = [
            _handoff_request_summary(handoff_request),
            _handoff_response_summary(handoff_request, handoff_response),
            _draft_request_summary(draft_request),
            _draft_response_summary(draft_request, draft_response),
        ]
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
            return _approved_summary_failure_result(
                failure_stage=exc.failure_stage,
                debug_code=exc.debug_code,
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
        except (ContractValidationError, McpArgumentError):
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
        draft_arguments = _draft_article_without_operator_selection_fields(
            draft_arguments
        )
        if _has_approved_summary_authoring_input(draft_arguments):
            return self._author_approved_summary(
                _draft_article_without_uploaded_ticket_ref(draft_arguments)
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
        if not set(arguments).issubset(_DRAFT_ARTICLE_DESKTOP_PRIMARY_ARGS):
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
            candidates = _draft_article_candidates_with_refs(
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
            result = _draft_article_split_required_result(
                {"item_candidates": candidates}
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
            _draft_article_authoring_args_from_candidate(
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
        if _has_structured_approved_summary_item_input(approved_arguments):
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
            return _draft_article_selection_error_result(arguments, pending_selection)
        return self._draft_article_primary_author_result(
            _draft_article_authoring_args_from_candidate(
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


def _draft_article_arguments(arguments: Mapping[str, Any]) -> Mapping[str, Any]:
    _require_args(arguments, _DRAFT_ARTICLE_ARGS, required=frozenset())
    _require_approved_summary_false_only_args(arguments)
    normalized = _draft_article_with_normalized_item(arguments)
    if "item_candidates" not in arguments:
        return normalized
    candidates = _draft_article_item_candidates(arguments["item_candidates"])
    normalized["item_candidates"] = candidates
    if len(candidates) == 1 and "item" not in normalized:
        candidate_item = {
            key: value
            for key, value in candidates[0].items()
            if key in _APPROVED_SUMMARY_ITEM_FIELDS
        }
        if candidate_item:
            normalized["item"] = candidate_item
    return normalized


def _draft_article_authoring_args_from_candidate(
    *,
    approved_summary_text: str,
    candidate: Mapping[str, Any],
    debug: bool,
) -> JsonDict:
    return _draft_article_with_normalized_item(
        {
            "approved_summary_text": approved_summary_text,
            "debug": debug,
            "item": dict(candidate),
        }
    )


def _draft_article_candidates_with_refs(
    candidates: list[JsonDict],
) -> list[JsonDict]:
    normalized: list[JsonDict] = []
    for index, candidate in enumerate(candidates, start=1):
        candidate_with_ref = dict(candidate)
        item_ref = candidate_with_ref.get("item_ref")
        if not isinstance(item_ref, str) or not item_ref:
            candidate_with_ref["item_ref"] = f"candidate-{index:03d}"
        normalized.append(candidate_with_ref)
    return normalized


def _draft_article_with_normalized_item(
    arguments: Mapping[str, Any],
) -> JsonDict:
    normalized = dict(arguments)
    if "item" not in normalized:
        return normalized
    item = dict(require_json_object(normalized["item"]))
    item_ref = item.pop("item_ref", None)
    for metadata_field in _DRAFT_ARTICLE_ITEM_METADATA_FIELDS - {"item_ref"}:
        item.pop(metadata_field, None)
    if (
        isinstance(item_ref, str)
        and item_ref
        and "candidate_id" not in item
    ):
        item["candidate_id"] = item_ref
    normalized["item"] = item
    return normalized


def _draft_article_without_operator_selection_fields(
    arguments: Mapping[str, Any],
) -> Mapping[str, Any]:
    return {
        key: value
        for key, value in arguments.items()
        if key
        not in {
            "operator_choice_confirmed",
            "operator_selected_item_ref",
            "operator_selection_ref",
            "item_candidates",
        }
    }


def _draft_article_without_uploaded_ticket_ref(
    arguments: Mapping[str, Any],
) -> Mapping[str, Any]:
    if "approved_summary_text" not in arguments or "ticket_ref" not in arguments:
        return arguments
    cleaned = dict(arguments)
    cleaned.pop("ticket_ref", None)
    return cleaned


def _draft_article_selection_error_result(
    arguments: Mapping[str, Any],
    pending_selection: PendingDraftSelection,
) -> JsonDict | None:
    return selection_error_result(
        arguments,
        pending_selection,
        schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
        submit_tool=claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
    )


def _draft_article_item_candidates(value: object) -> list[JsonDict]:
    if not isinstance(value, list):
        raise McpArgumentError("Invalid item candidates.")
    candidates: list[JsonDict] = []
    for candidate in value:
        if not isinstance(candidate, Mapping):
            raise McpArgumentError("Invalid item candidate.")
        if any(key not in _DRAFT_ARTICLE_ITEM_CANDIDATE_FIELDS for key in candidate):
            raise McpArgumentError("Unexpected item candidate field.")
        candidate_json = dict(candidate)
        ensure_safe_sanitized_payload(candidate_json)
        candidates.append(candidate_json)
    return candidates


def _draft_article_split_required_result(
    arguments: Mapping[str, Any],
) -> JsonDict | None:
    if _draft_article_has_confirmed_operator_selection(arguments):
        return None
    candidates = arguments.get("item_candidates")
    if not isinstance(candidates, list) or len(candidates) <= 1:
        return None
    return split_required_result(
        candidates,
        schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
    )


def _draft_article_has_confirmed_operator_selection(
    arguments: Mapping[str, Any],
) -> bool:
    return (
        arguments.get("operator_choice_confirmed") is True
        and isinstance(arguments.get("operator_selection_ref"), str)
        and isinstance(arguments.get("operator_selected_item_ref"), str)
    )


def _has_approved_summary_authoring_input(arguments: Mapping[str, Any]) -> bool:
    if "approved_summary_text" in arguments:
        return True
    if "item" in arguments:
        return True
    return any(key in arguments for key in _APPROVED_SUMMARY_TOP_LEVEL_ITEM_FIELDS)


def _has_structured_approved_summary_item_input(arguments: Mapping[str, Any]) -> bool:
    if "item" in arguments:
        return True
    return any(key in arguments for key in _APPROVED_SUMMARY_TOP_LEVEL_ITEM_FIELDS)


def _append_quality_gap(result: JsonDict, gap: JsonDict) -> None:
    quality_gaps = result.get("quality_gaps")
    if isinstance(quality_gaps, list):
        quality_gaps.append(gap)


def _execute_approved_summary_pipeline(
    arguments: Mapping[str, Any],
) -> _ApprovedSummaryExecution:
    return execute_approved_summary_pipeline(
        arguments,
        hooks=ApprovedSummaryPipelineHooks(
            build_payload=_checked_approved_summary_pipeline_payload,
            build_evidence=_build_approved_summary_evidence,
            validate_safety=_validate_approved_summary_safety,
            validate_evidence=_validate_approved_summary_evidence,
            decide=_decide_approved_summary_action,
            render=_render_approved_summary_reviewer_packet,
            build_readiness=_build_approved_summary_readiness,
            item_ref=_approved_summary_pipeline_item_ref,
            short_summary=_desktop_payload.approved_summary_short_summary,
            title=_desktop_payload.approved_summary_title,
        ),
    )


def _approved_summary_pipeline_item_ref(
    arguments: Mapping[str, Any],
    decision: KcsActionDecisionPacket,
) -> str:
    return decision.candidate_id or _desktop_payload.approved_summary_item_ref(
        arguments
    )


def _approved_summary_pipeline_status(
    execution: _ApprovedSummaryExecution,
) -> JsonDict:
    return approved_summary_pipeline_status(
        execution,
        schema_version=MCP_TOOL_RESULT_SCHEMA_VERSION,
        reuse_search_status=_approved_summary_reuse_search_status(
            execution.arguments
        ),
    )


def _approved_summary_author_result(
    execution: _ApprovedSummaryExecution,
) -> JsonDict:
    status = _approved_summary_pipeline_status(execution)
    draft = _approved_summary_reviewer_only_draft(execution)
    return {
        **status,
        "article_type": execution.decision.article_type,
        "atomic_item": _approved_summary_atomic_item(execution),
        "blockers": [],
        "draft_sections": draft,
        "open_questions": _approved_summary_open_questions(execution),
        "quality_gaps": _approved_summary_quality_gaps(execution, draft),
        "recommended_action": execution.decision.recommended_action,
        "result_kind": "approved_summary_authoring",
        "review_summary": _approved_summary_review_status(execution),
        "reviewer_only_html": _approved_summary_reviewer_only_html(execution),
        "reviewer_only_draft": draft,
        "reviewer_only_preview": _approved_summary_reviewer_only_preview(draft),
        "reviewer_only_preview_text": _approved_summary_reviewer_only_preview_text(
            draft
        ),
        "should_be_kcs_article": _approved_summary_should_be_article(execution),
    }


def _approved_summary_author_failure_result(
    *,
    failure_stage: str,
    debug_code: str,
) -> JsonDict:
    return draft_author_failure_result(
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
    result = _approved_summary_author_failure_result(
        failure_stage=failure_stage,
        debug_code=debug_code,
    )
    result["result_kind"] = "approved_ticket_authoring"
    result["ticket_ref"] = ticket_ref
    result["approved_summary_source"] = "local_approved_summary"
    if debug_code in {
        "approved_ticket_ref_invalid",
        "approved_ticket_summary_invalid",
        "approved_ticket_summary_not_found",
    }:
        result["automatic_item_retry_allowed"] = True
        result["manual_draft_allowed"] = False
        result["next_required_action"] = (
            "retry_with_approved_summary_text_from_attachment"
        )
        result["review_summary"] = {
            "draft_available": False,
            "next_required_action": (
                "retry_with_approved_summary_text_from_attachment"
            ),
            "reason": debug_code,
        }
    return result


def _approved_summary_should_be_article(
    execution: _ApprovedSummaryExecution,
) -> bool:
    return (
        execution.decision.status == DecisionStatus.DECISION_READY.value
        and execution.decision.recommended_action
        in {
            RecommendedAction.CREATE_CANDIDATE.value,
            RecommendedAction.UPDATE_EXISTING.value,
            RecommendedAction.FLAG_EXISTING.value,
        }
    )


def _approved_summary_atomic_item(
    execution: _ApprovedSummaryExecution,
) -> JsonDict:
    candidate = _approved_summary_public_candidate(execution.reviewer_packet)
    symptoms = _safe_candidate_list(candidate, "symptoms")
    return {
        "item_ref": execution.item_ref,
        "summary": _safe_candidate_string(candidate, "summary")
        or (symptoms[0] if symptoms else ""),
        "title": _safe_candidate_string(candidate, "title"),
    }


def _approved_summary_review_status(
    execution: _ApprovedSummaryExecution,
) -> JsonDict:
    return {
        "draft_request_ready": execution.draft_request_ready,
        "readiness_state": execution.readiness.state,
        "recommended_action": execution.decision.recommended_action,
        "review_required": execution.reviewer_packet.review_required,
    }


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
            "inputSchema": _desktop_input_schema(payload["input_schema"]),
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


def claude_desktop_tool_alias(tool_name: str) -> str:
    """Return the Claude Desktop-safe alias for a canonical tool name."""

    try:
        return CLAUDE_DESKTOP_TOOL_ALIASES[tool_name]
    except KeyError:
        raise ValueError("Tool has no Claude Desktop alias mapping.") from None


def canonical_tool_name_from_claude_desktop_alias(tool_name: str) -> str:
    """Return the canonical name for a Claude Desktop alias."""

    try:
        return CANONICAL_TOOL_BY_CLAUDE_DESKTOP_ALIAS[tool_name]
    except KeyError:
        raise ValueError("Unknown Claude Desktop tool alias.") from None


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


def _policy_summary_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_GET_POLICY_SUMMARY,
        description="Return KCS Desktop MCP safety and scope metadata.",
        input_schema=_object_schema(),
    )


def _readiness_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_GET_MCP_READINESS,
        description="Return KCS Desktop MCP readiness metadata and visible tools.",
        input_schema=_object_schema(),
    )


def _validate_handoff_request_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_VALIDATE_HANDOFF_REQUEST,
        description="Validate one KCS-9b handoff request packet.",
        input_schema=_object_schema(
            properties={"request": {"type": "object"}},
            required=["request"],
        ),
    )


def _validate_handoff_response_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_VALIDATE_HANDOFF_RESPONSE,
        description="Validate one KCS-9b handoff response against its request.",
        input_schema=_object_schema(
            properties={"request": {"type": "object"}, "response": {"type": "object"}},
            required=["request", "response"],
        ),
    )


def _validate_draft_request_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_VALIDATE_DRAFT_REQUEST,
        description="Validate one KCS-9c draft request packet.",
        input_schema=_object_schema(
            properties={"request": {"type": "object"}},
            required=["request"],
        ),
    )


def _validate_draft_response_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_VALIDATE_DRAFT_RESPONSE,
        description="Validate one KCS-9c draft response against its request.",
        input_schema=_object_schema(
            properties={"request": {"type": "object"}, "response": {"type": "object"}},
            required=["request", "response"],
        ),
    )


def _contract_smoke_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_RUN_CONTRACT_SMOKE,
        description="Run an in-memory synthetic KCS-9b/KCS-9c validation smoke.",
        input_schema=_object_schema(),
    )


def _approved_summary_pipeline_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
        description=(
            "Run the local KCS pipeline for one approved sanitized summary. "
            "Provide approved_summary_text. Optional structured item fields can "
            "be passed either as item or top-level fields; common aliases like "
            "problem, diagnosis, solution, commands, and secondary_finding are "
            "accepted. Explicit supported cause/resolution evidence is required "
            "before evidence-ready status. This MVP does not perform live reuse "
            "search; if reuse_search_checked is not provided, reuse search is "
            "marked skipped and drafting may continue. Set debug=true to receive "
            "value-safe failure_stage and debug_code. The tool returns compact "
            "status only."
        ),
        input_schema=_approved_summary_input_schema(),
    )


def _author_approved_summary_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_AUTHOR_APPROVED_SUMMARY,
        description=(
            "Author a reviewer-only KCS draft/status packet from one approved "
            "sanitized support summary. Requires explicit supported cause or "
            "answer evidence, explicit supported resolution or answer evidence, "
            "and a single atomic item. This MVP marks reuse search skipped when "
            "reuse_search_checked is not provided. Returns compact reviewer-only "
            "draft sections, reviewer_only_html for copy/paste, and deterministic "
            "quality-gap status; does not publish, write files, call a provider, "
            "or return full packet bodies."
        ),
        input_schema=_approved_summary_input_schema(),
    )


def _author_ticket_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_AUTHOR_TICKET,
        description=(
            "Author a reviewer-only KCS draft/status packet from one local "
            "approved sanitized ticket summary reference. Provide ticket_ref. "
            "The tool reads only configured approved summary files, "
            "returns reviewer_only_html for copy/paste, does not read Zendesk, "
            "and does not publish, write files, call a provider, or return raw "
            "packet bodies."
        ),
        input_schema=_approved_ticket_input_schema(),
    )


def _register_clean_ticket_descriptor() -> McpToolDescriptor:
    descriptor = _descriptor(
        name=TOOL_REGISTER_CLEAN_TICKET,
        description=(
            "Register one approved sanitized support-ticket transcript as a "
            "configured clean ticket file. Use this when Claude Desktop "
            "receives a draft-article request with an operator-provided "
            "sanitized attachment or long paste and no ticket_ref yet. This is "
            "the automatic first step for attachment-based drafting. Pass the "
            "complete visible sanitized transcript, even when long, in "
            "clean_ticket_text and optionally an opaque ticket_ref; do not pass "
            "uploaded filenames, "
            "local paths, Claude upload paths, item, item_candidates, aliases, "
            "or reference article bodies. A Claude Desktop file card is not a "
            "filesystem path: do not inspect upload directories, and use the "
            "visible file text as clean_ticket_text. The tool writes "
            "clean.ticket.txt under the configured approved-summaries store "
            "and returns exact next_arguments for kcs_draft_article."
        ),
        input_schema=_register_clean_ticket_input_schema(),
    )
    descriptor.annotations["idempotentHint"] = False
    descriptor.annotations["readOnlyHint"] = False
    return descriptor


def _draft_article_descriptor() -> McpToolDescriptor:
    descriptor = _descriptor(
        name=TOOL_DRAFT_ARTICLE,
        description=(
            "Primary KCS authoring tool for sanitized support-ticket article "
            "requests. Prefer ticket_ref when the cleaned ticket transcript "
            "has been saved by a trusted source under the configured "
            "approved-summaries store. For an operator-provided sanitized "
            "attachment or long paste with no ticket_ref, call "
            "kcs_register_clean_ticket first and then call this tool with the "
            "returned next_arguments. Use approved_summary_text only as a "
            "fallback for short inline sanitized text when clean-ticket "
            "registration is not needed. Do not summarize, redact labeled "
            "sections, or pass upload filenames, paths, item, item_candidates, "
            "aliases, or reference article bodies. A Claude Desktop file card "
            "is not a filesystem path; do not inspect upload directories or "
            "ask the operator to re-upload while visible file text is "
            "available. If no visible file text is available, report "
            "file_content_unavailable and do not draft manually. "
            "Python validates the input and owns semantic extraction, decision, "
            "rendering, and local bundle output. Successful results return "
            "reviewer-only Zendesk HTML plus compact status. If split_required "
            "is returned, call again with only operator_selection_ref and "
            "operator_selected_item_ref."
        ),
        input_schema=_draft_article_input_schema(),
    )
    descriptor.annotations["idempotentHint"] = False
    descriptor.annotations["readOnlyHint"] = False
    return descriptor


def _support_get_behavior_instructions_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_SUPPORT_GET_BEHAVIOR_INSTRUCTIONS,
        description=(
            "Compatibility helper for legacy Plesk Support behavior-instruction "
            "requests. Returns the minimal KCS Authoring route: use "
            "kcs_draft_article for sanitized ticket article drafting."
        ),
        input_schema=_object_schema(),
    )


def _approved_summary_input_schema() -> JsonDict:
    return _object_schema(
        properties={
            "applicable_to": {"type": ["array", "string"]},
            "approved_summary_text": {"type": "string"},
            "article_type": {"type": "string"},
            "article_title": {"type": "string"},
            "auto_publish_allowed": {"type": "boolean"},
            "candidate_id": {"type": "string"},
            "case_ref": {"type": "string"},
            "cause": {"type": "string"},
            "commands": {"type": ["array", "string"]},
            "confirmed_facts": {"type": ["array", "string"]},
            "customer_replies": {"type": "boolean"},
            "debug": {
                "type": "boolean",
                "description": (
                    "Use true only for explicit debug or smoke compatibility. "
                    "Successful Desktop draft results already include "
                    "reviewer-only Zendesk HTML and compact status."
                ),
            },
            "diagnosis": {"type": "string"},
            "environment": {"type": ["object", "string"]},
            "evidence": {"type": ["array", "string"]},
            "facts": {"type": ["array", "string"]},
            "fix": {"type": "string"},
            "item": {"type": "object"},
            "log_evidence": {"type": ["array", "string"]},
            "logs": {"type": ["array", "string"]},
            "notes": {"type": ["array", "string"]},
            "open_questions": {"type": ["array", "string"]},
            "problem": {"type": ["array", "string"]},
            "problem_statement": {"type": ["array", "string"]},
            "provider_calls": {"type": "boolean"},
            "public_output_approved": {"type": "boolean"},
            "publishes": {"type": "boolean"},
            "question": {"type": "string"},
            "ready_for_real_ticket_use": {"type": "boolean"},
            "reference_article": {"type": "string"},
            "reference_article_html": {"type": "string"},
            "reference_article_text": {"type": "string"},
            "reuse_search_checked": {"type": "boolean"},
            "reuse_search_run_ref": {"type": "string"},
            "resolution": {"type": "string"},
            "resolution_procedure": {"type": "string"},
            "root_cause": {"type": "string"},
            "root_cause_analysis": {"type": "string"},
            "resolution_steps": {"type": ["array", "string"]},
            "resolution_summary": {"type": "string"},
            "secondary_finding": {"type": ["array", "string"]},
            "secondary_findings": {"type": ["array", "string"]},
            "secondary_issue": {"type": ["array", "string"]},
            "secondary_issues": {"type": ["array", "string"]},
            "solution": {"type": "string"},
            "steps": {"type": ["array", "string"]},
            "supported_answer": {"type": "string"},
            "supported_cause": {"type": "string"},
            "supported_resolution_or_workaround": {"type": "string"},
            "symptom": {"type": "string"},
            "symptoms": {"type": ["array", "string"]},
            "title": {"type": "string"},
            "network_calls": {"type": "boolean"},
            "writes_files": {"type": "boolean"},
        },
        required=["approved_summary_text"],
    )


def _approved_ticket_input_schema() -> JsonDict:
    return _object_schema(
        properties={
            "auto_publish_allowed": {"type": "boolean"},
            "customer_replies": {"type": "boolean"},
            "debug": {"type": "boolean"},
            "network_calls": {"type": "boolean"},
            "provider_calls": {"type": "boolean"},
            "public_output_approved": {"type": "boolean"},
            "publishes": {"type": "boolean"},
            "ready_for_real_ticket_use": {"type": "boolean"},
            "reference_article": {"type": "string"},
            "reference_article_html": {"type": "string"},
            "reference_article_text": {"type": "string"},
            "ticket_ref": {"type": "string"},
            "writes_files": {"type": "boolean"},
        },
        required=["ticket_ref"],
    )


def _register_clean_ticket_input_schema() -> JsonDict:
    return _object_schema(
        properties={
            "clean_ticket_text": {
                "type": "string",
                "description": (
                    "Complete visible approved sanitized ticket transcript. "
                    "Do not summarize, condense, rewrite, redact labeled "
                    "sections, or omit visible symptoms, cause, resolution, "
                    "config paths, commands, services, platform facts, or other "
                    "sanitized evidence. Do not include tool-call XML, "
                    "parameter tags, or MCP argument markup inside this text."
                ),
            },
            "debug": {
                "type": "boolean",
                "description": "Use true only for explicit debug or smoke runs.",
            },
            "ticket_ref": {
                "type": "string",
                "description": (
                    "Optional opaque safe ref for the clean ticket file. Do not "
                    "pass filenames, absolute paths, Claude upload paths, or "
                    "arbitrary local paths."
                ),
            },
        },
        required=["clean_ticket_text"],
    )


def _draft_article_input_schema() -> JsonDict:
    return _object_schema(
        properties={
            "approved_summary_text": {
                "type": "string",
                "description": (
                    "Fallback for short inline sanitized support-ticket text "
                    "when clean-ticket registration is not needed. For "
                    "attachments, long pasted tickets, or any case where no "
                    "ticket_ref exists yet, call kcs_register_clean_ticket "
                    "first. If this field is used, pass the visible sanitized "
                    "text as-is. Do not summarize, condense, rewrite, redact "
                    "labeled sections, or omit symptoms, cause, resolution, "
                    "config paths, commands, services, platform facts, or other "
                    "visible evidence before calling the tool. Do not pass "
                    "uploaded filenames, local paths, or Claude upload paths."
                ),
            },
            "debug": {
                "type": "boolean",
                "description": (
                    "Use true only for explicit debug or smoke compatibility. "
                    "Successful Desktop draft results already include "
                    "reviewer-only Zendesk HTML and compact status."
                ),
            },
            "operator_selected_item_ref": {
                "type": "string",
                "description": (
                    "Opaque item ref selected by the operator from a previous "
                    "split-required result."
                ),
            },
            "operator_selection_ref": {
                "type": "string",
                "description": (
                    "Opaque selection ref returned by a previous split-required "
                    "result."
                ),
            },
            "ticket_ref": {
                "type": "string",
                "description": (
                    "Opaque ref for a configured cleaned ticket transcript. "
                    "Use only refs prepared by a trusted source under "
                    "local-data/approved-summaries; do not pass filenames, "
                    "absolute paths, Claude upload paths, or arbitrary local "
                    "paths."
                ),
            },
        }
    )


def _draft_article_item_schema() -> JsonDict:
    return _object_schema(
        properties={
            "applicable_to": {
                "type": ["array", "string"],
                "description": (
                    "Applicable product/platform values, for example Plesk for "
                    "Linux or Plesk for Windows. Include release/version only "
                    "when the approved summary supports it."
                ),
            },
            "article_type": {
                "type": "string",
                "enum": [ArticleType.TECHNICAL_SCR.value, ArticleType.HOWTO_QA.value],
                "description": "Canonical article type only.",
            },
            "confirmed_facts": {
                "type": ["array", "string"],
                "description": "Confirmed facts from the approved sanitized summary.",
            },
            "environment": _draft_article_environment_schema(),
            "resolution_steps": {
                "type": ["array", "string"],
                "description": (
                    "Executable reviewer-ready steps. Include concrete how-to "
                    "detail present in the summary: approved prerequisite links, "
                    "UI navigation, commands, paths, services, and verification. "
                    "Use safe backup or move-aside steps such as mv ... .bak "
                    "when cleanup is needed; do not pass rm -rf, delete, remove, "
                    "or destructive cleanup steps."
                ),
            },
            "supported_answer": {
                "type": "string",
                "description": "Required for howto_qa when applicable.",
            },
            "supported_cause": {
                "type": "string",
                "description": (
                    "Confirmed supported cause for technical_scr. Do not use "
                    "speculative wording such as likely, suspected, appears, "
                    "maybe, probably, unclear, or unknown."
                ),
            },
            "supported_resolution_or_workaround": {
                "type": "string",
                "description": "Supported resolution or workaround for technical_scr.",
            },
            "symptoms": {
                "type": ["array", "string"],
                "description": "Observed symptoms for technical_scr.",
            },
            "title": {"type": "string"},
        }
    )


def _draft_article_item_candidate_schema() -> JsonDict:
    schema = _draft_article_item_schema()
    schema["properties"] = {
        **schema["properties"],
        "item_ref": {"type": "string"},
        "reason": {
            "type": "string",
            "description": "Short reason why this is a separate semantic KCS item.",
        },
    }
    return schema


def _draft_article_environment_schema() -> JsonDict:
    return _object_schema(
        properties={
            "component": {"type": ["array", "string"]},
            "components": {"type": ["array", "string"]},
            "extension": {"type": "string"},
            "operating_system": {"type": "string"},
            "os": {"type": "string"},
            "platform": {"type": "string"},
            "product": {"type": "string"},
            "version": {"type": "string"},
        }
    )


def _descriptor(
    *,
    name: str,
    description: str,
    input_schema: JsonDict,
) -> McpToolDescriptor:
    return McpToolDescriptor(
        name=name,
        description=description,
        input_schema=input_schema,
        output_schema=_tool_output_schema(),
        annotations={
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
            "readOnlyHint": True,
        },
    )


def _object_schema(
    *,
    properties: Mapping[str, object] | None = None,
    required: list[str] | None = None,
) -> JsonDict:
    return {
        "additionalProperties": False,
        "properties": dict(properties or {}),
        "required": list(required or []),
        "type": "object",
    }


def _tool_output_schema() -> JsonDict:
    success = _object_schema(
        properties={key: {"type": "object"} for key in _SUCCESS_OUTPUT_KEYS},
        required=["ok", "result_kind", "schema_version"],
    )
    success["properties"] = _SUCCESS_OUTPUT_PROPERTIES
    error = _object_schema(
        properties={
            "error": {"type": "string"},
            "error_code": {"type": "string"},
            "ok": {"type": "boolean"},
        },
        required=["ok", "error", "error_code"],
    )
    return {"anyOf": [success, error]}


_SUCCESS_OUTPUT_PROPERTIES: JsonDict = {
    "auto_publish_allowed": {"type": "boolean"},
    "automatic_item_retry_allowed": {"type": "boolean"},
    "approved_summary_source": {"type": "string"},
    "article_type": {"type": "string"},
    "atomic_item": {"type": "object"},
    "blockers": {"type": "array"},
    "bundle_ref": {"type": "string"},
    "bundle_storage_hint": {"type": "string"},
    "bundle_storage_ref": {"type": "string"},
    "byte_length": {"type": "integer"},
    "case_ref": {"type": "string"},
    "checks": {"type": "array"},
    "clean_ticket_sha256": {"type": "string"},
    "clean_ticket_store_ref": {"type": "string"},
    "clean_ticket_storage_hint": {"type": "string"},
    "clean_ticket_storage_ref": {"type": "string"},
    "customer_replies": {"type": "boolean"},
    "debug_code": {"type": "string"},
    "draft_ref": {"type": "string"},
    "draft_generated": {"type": "boolean"},
    "draft_request_ready": {"type": "boolean"},
    "draft_sections": {"type": "object"},
    "evidence_valid": {"type": "boolean"},
    "draft_status": {"type": "string"},
    "failure_stage": {"type": "string"},
    "handoff_ref": {"type": "string"},
    "html_path": {"type": "string"},
    "html_sha256": {"type": "string"},
    "input_safety_ok": {"type": "boolean"},
    "item_candidates": {"type": "array"},
    "item_ref": {"type": "string"},
    "kcs_ready": {"type": "boolean"},
    "manual_draft_allowed": {"type": "boolean"},
    "manifest_path": {"type": "string"},
    "network_calls": {"type": "boolean"},
    "next_arguments": {"type": "object"},
    "next_required_action": {"type": "string"},
    "next_tool_name": {"type": "string"},
    "ok": {"type": "boolean"},
    "open_questions": {"type": "array"},
    "operator_choice_options": {"type": "array"},
    "operator_choice_confirmed": {"type": "boolean"},
    "operator_choice_request": {"type": "object"},
    "operator_prompt": {"type": "string"},
    "operator_prompt_style": {"type": "string"},
    "operator_selected_item_ref": {"type": "string"},
    "operator_selection_ref": {"type": "string"},
    "original_article_type": {"type": "string"},
    "original_decision_status": {"type": "string"},
    "original_readiness_state": {"type": "string"},
    "original_recommended_action": {"type": "string"},
    "prompts_exposed": {"type": "boolean"},
    "protocol_version": {"type": "string"},
    "provider_calls": {"type": "boolean"},
    "provider_error_code": {"type": "string"},
    "provider_status": {"type": "string"},
    "public_output_approved": {"type": "boolean"},
    "publishes": {"type": "boolean"},
    "pipeline_ok": {"type": "boolean"},
    "quality_gaps": {"type": "array"},
    "recommended_action": {"type": "string"},
    "ready_for_reviewer": {"type": "boolean"},
    "ready_for_real_ticket_use": {"type": "boolean"},
    "request_schema_version": {"type": "string"},
    "request_sha256": {"type": "string"},
    "resources_exposed": {"type": "boolean"},
    "response_schema_version": {"type": "string"},
    "response_sha256": {"type": "string"},
    "result_kind": {"type": "string"},
    "review_summary": {"type": "object"},
    "reviewer_only_html": {"type": "string"},
    "reviewer_only_draft": {"type": "object"},
    "reviewer_only_preview": {"type": "object"},
    "reviewer_only_preview_text": {"type": "string"},
    "reviewer_bundle_written": {"type": "boolean"},
    "reuse_search_run_ref": {"type": "string"},
    "reuse_search_status": {"type": "string"},
    "schema_version": {"type": "string"},
    "server_name": {"type": "string"},
    "server_version": {"type": "string"},
    "should_be_kcs_article": {"type": "boolean"},
    "smoke_ok": {"type": "boolean"},
    "tool_count": {"type": "integer"},
    "tools": {"type": "array"},
    "ticket_ref": {"type": "string"},
    "validation_ok": {"type": "boolean"},
    "writes_files": {"type": "boolean"},
}
_SUCCESS_OUTPUT_KEYS = frozenset(_SUCCESS_OUTPUT_PROPERTIES)


def _desktop_input_schema(input_schema: Mapping[str, Any]) -> JsonDict:
    schema = _safe_desktop_schema_fragment(input_schema)
    if not isinstance(schema, dict) or schema.get("type") != "object":
        return _object_schema()
    return schema


def _safe_desktop_schema_fragment(schema: object) -> JsonDict:
    if not isinstance(schema, Mapping):
        return {"type": "object"}

    result: JsonDict = {"type": _safe_schema_type(schema.get("type", "object"))}
    _copy_safe_schema_metadata(schema, result)
    _copy_safe_schema_children(schema, result)
    return result


def _safe_schema_type(value: object) -> object:
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    return "object"


def _copy_safe_schema_metadata(schema: Mapping[str, Any], result: JsonDict) -> None:
    description = schema.get("description")
    if isinstance(description, str):
        result["description"] = description[:500]

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and all(
        isinstance(item, str) for item in enum_values
    ):
        result["enum"] = list(enum_values)

    max_length = schema.get("maxLength")
    if isinstance(max_length, int):
        result["maxLength"] = max_length

    additional_properties = schema.get("additionalProperties")
    if isinstance(additional_properties, bool):
        result["additionalProperties"] = additional_properties

    required = schema.get("required")
    if isinstance(required, list) and all(isinstance(item, str) for item in required):
        result["required"] = list(required)


def _copy_safe_schema_children(schema: Mapping[str, Any], result: JsonDict) -> None:
    properties = schema.get("properties")
    if isinstance(properties, Mapping):
        result["properties"] = {
            name: _safe_desktop_schema_fragment(value)
            for name, value in properties.items()
            if isinstance(name, str)
        }

    items = schema.get("items")
    if isinstance(items, Mapping):
        result["items"] = _safe_desktop_schema_fragment(items)


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
    _validate_tool_structured_content(structured, descriptor.output_schema)
    content = _tool_result_content(structured)
    structured_content = _desktop_structured_content(
        descriptor=descriptor,
        structured=structured,
    )
    return {
        "content": content,
        "isError": not result.ok,
        "structuredContent": structured_content,
    }


def _tool_result_content(structured: Mapping[str, Any]) -> list[JsonDict]:
    return [{"text": _tool_result_text(structured), "type": "text"}]


def _reviewer_html_resource_uri(structured: Mapping[str, Any]) -> str:
    bundle_ref = structured.get("bundle_ref")
    item_ref = structured.get("item_ref")
    html_sha256 = structured.get("html_sha256")
    safe_bundle = bundle_ref if isinstance(bundle_ref, str) else "bundle"
    safe_item = item_ref if isinstance(item_ref, str) else "item"
    safe_hash = html_sha256 if isinstance(html_sha256, str) else "html"
    return f"kcs-reviewer-bundle://{safe_bundle}/{safe_item}/{safe_hash}.html"


def _tool_result_text(structured: Mapping[str, Any]) -> str:
    pre_draft_text = _pre_draft_tool_result_text(structured)
    if pre_draft_text is not None:
        return pre_draft_text
    debug_text = _debug_tool_result_text(structured)
    if debug_text is not None:
        return debug_text
    html = structured.get("reviewer_only_html")
    if (
        isinstance(html, str)
        and html
        and structured.get("result_kind")
        in {
            "approved_summary_authoring",
            "approved_ticket_authoring",
            "draft_article_authoring",
        }
    ):
        status = {
            "article_type": structured.get("article_type"),
            "auto_publish_allowed": structured.get("auto_publish_allowed"),
            "case_ref": structured.get("case_ref"),
            "debug_code": structured.get("debug_code"),
            "draft_request_ready": structured.get("draft_request_ready"),
            "draft_generated": structured.get("draft_generated"),
            "failure_stage": structured.get("failure_stage"),
            "html_path": structured.get("html_path"),
            "html_sha256": structured.get("html_sha256"),
            "bundle_storage_hint": structured.get("bundle_storage_hint"),
            "bundle_storage_ref": structured.get("bundle_storage_ref"),
            "item_ref": structured.get("item_ref"),
            "kcs_ready": structured.get("kcs_ready"),
            "manifest_path": structured.get("manifest_path"),
            "ok": structured.get("ok"),
            "pipeline_ok": structured.get("pipeline_ok"),
            "public_output_approved": structured.get("public_output_approved"),
            "ready_for_reviewer": structured.get("ready_for_reviewer"),
            "recommended_action": structured.get("recommended_action"),
            "result_kind": structured.get("result_kind"),
            "reuse_search_status": structured.get("reuse_search_status"),
            "reviewer_bundle_written": structured.get("reviewer_bundle_written"),
            "validation_ok": structured.get("validation_ok"),
        }
        return (
            "```html\n"
            f"{html}\n"
            "```\n\n"
            "```json\n"
            f"{_compact_json(status)}\n"
            "```"
        )
    if (
        structured.get("result_kind") == "draft_article_authoring"
        and structured.get("draft_generated") is True
        and isinstance(structured.get("html_path"), str)
    ):
        status = {
            "article_type": structured.get("article_type"),
            "auto_publish_allowed": structured.get("auto_publish_allowed"),
            "debug_code": structured.get("debug_code"),
            "draft_generated": structured.get("draft_generated"),
            "html_path": structured.get("html_path"),
            "bundle_storage_hint": structured.get("bundle_storage_hint"),
            "bundle_storage_ref": structured.get("bundle_storage_ref"),
            "item_ref": structured.get("item_ref"),
            "kcs_ready": structured.get("kcs_ready"),
            "manifest_path": structured.get("manifest_path"),
            "public_output_approved": structured.get("public_output_approved"),
            "ready_for_reviewer": structured.get("ready_for_reviewer"),
            "recommended_action": structured.get("recommended_action"),
            "reuse_search_status": structured.get("reuse_search_status"),
            "reviewer_bundle_written": structured.get("reviewer_bundle_written"),
        }
        return (
            "Reviewer-only KCS draft generated by the KCS Authoring tool. "
            "Zendesk HTML is saved on the operator's local machine in the "
            "reviewer bundle at html_path. When bundle_storage_hint is present, "
            "resolve html_path under that directory. Report the returned local "
            "bundle location and status only; do not claim the file is "
            "unavailable from this chat, do not inspect upload/sandbox paths, "
            "and do not offer a separate chat-authored article.\n\n"
            "Compact status:\n"
            "```json\n"
            f"{_compact_json(status)}\n"
            "```"
        )
    if (
        structured.get("result_kind") == "draft_article_authoring"
        and structured.get("recommended_action") == "split_required"
        and isinstance(structured.get("operator_choice_request"), Mapping)
    ):
        return _split_required_tool_result_text(structured)
    return _compact_json(structured)


def _pre_draft_tool_result_text(structured: Mapping[str, Any]) -> str | None:
    if structured.get("result_kind") == "clean_ticket_registered":
        status = {
            "clean_ticket_sha256": structured.get("clean_ticket_sha256"),
            "clean_ticket_store_ref": structured.get("clean_ticket_store_ref"),
            "clean_ticket_storage_hint": structured.get(
                "clean_ticket_storage_hint"
            ),
            "clean_ticket_storage_ref": structured.get("clean_ticket_storage_ref"),
            "next_arguments": structured.get("next_arguments"),
            "next_tool_name": structured.get("next_tool_name"),
            "ok": structured.get("ok"),
            "result_kind": structured.get("result_kind"),
            "ticket_ref": structured.get("ticket_ref"),
            "writes_files": structured.get("writes_files"),
        }
        return (
            "Clean ticket transcript registered. Continue by calling "
            "kcs_draft_article with next_arguments exactly as returned.\n\n"
            "Compact status:\n"
            "```json\n"
            f"{_compact_json(status)}\n"
            "```"
        )
    if structured.get("debug_code") == "clean_ticket_text_incomplete":
        status = {
            "debug_code": structured.get("debug_code"),
            "draft_available": False,
            "failure_stage": structured.get("failure_stage"),
            "next_required_action": "register_complete_visible_clean_ticket_text",
            "ok": structured.get("ok"),
            "result_kind": structured.get("result_kind"),
            "writes_files": structured.get("writes_files"),
        }
        return (
            "Clean ticket registration is blocked because the provided text "
            "appears to be an incomplete or truncated ticket excerpt. No clean "
            "ticket was saved and no article draft is available.\n\n"
            "Do not draft manually. Read the complete visible sanitized file "
            "text, then call kcs_register_clean_ticket again with the complete "
            "transcript.\n\n"
            "Compact status:\n"
            "```json\n"
            f"{_compact_json(status)}\n"
            "```"
        )
    if structured.get("debug_code") == "clean_ticket_text_invalid":
        status = {
            "debug_code": structured.get("debug_code"),
            "draft_available": False,
            "failure_stage": structured.get("failure_stage"),
            "next_required_action": "register_original_visible_clean_ticket_text",
            "ok": structured.get("ok"),
            "result_kind": structured.get("result_kind"),
            "writes_files": structured.get("writes_files"),
        }
        return (
            "Clean ticket registration is blocked because the provided text is "
            "not an acceptable clean ticket transcript. No clean ticket was "
            "saved and no article draft is available.\n\n"
            "Do not draft manually. Do not reconstruct, summarize, or invent "
            "missing ticket sections. Call kcs_register_clean_ticket again only "
            "with the original complete visible sanitized ticket text.\n\n"
            "Compact status:\n"
            "```json\n"
            f"{_compact_json(status)}\n"
            "```"
        )
    if structured.get("result_kind") == "behavior_instructions":
        return (
            "KCS Authoring behavior: for sanitized support-ticket article "
            "requests, use KCS Authoring:kcs_draft_article with ticket_ref "
            "when a cleaned ticket transcript already exists. If the user asks "
            "to draft an article from a sanitized attachment or long paste and "
            "no ticket_ref exists, first call kcs_register_clean_ticket, then "
            "call kcs_draft_article with the returned next_arguments. A Claude "
            "Desktop file card is not a filesystem path; use visible file text "
            "instead of inspecting upload directories. If no visible file text "
            "is available, report file_content_unavailable and do not draft "
            "manually. Use the tool-generated reviewer-only Zendesk HTML as "
            "the draft."
        )
    return None


def _debug_tool_result_text(structured: Mapping[str, Any]) -> str | None:
    if structured.get("debug_code") == "semantic_extraction_provider_unavailable":
        status = {
            "auto_publish_allowed": structured.get("auto_publish_allowed"),
            "debug_code": structured.get("debug_code"),
            "draft_available": False,
            "failure_stage": structured.get("failure_stage"),
            "manual_draft_allowed": structured.get("manual_draft_allowed"),
            "next_required_action": structured.get("next_required_action"),
            "recommended_action": structured.get("recommended_action"),
            "result_kind": structured.get("result_kind"),
            "should_be_kcs_article": structured.get("should_be_kcs_article"),
            "writes_files": structured.get("writes_files"),
        }
        return (
            "KCS article drafting is blocked by the KCS Authoring tool because "
            "the approved semantic extraction provider is not configured. No "
            "reviewer-only draft was generated.\n\n"
            "Compact status:\n"
            "```json\n"
            f"{_compact_json(status)}\n"
            "```"
        )
    if structured.get("debug_code") == "semantic_extraction_no_candidates":
        status = {
            "approved_summary_source": structured.get("approved_summary_source"),
            "auto_publish_allowed": structured.get("auto_publish_allowed"),
            "debug_code": structured.get("debug_code"),
            "draft_available": False,
            "failure_stage": structured.get("failure_stage"),
            "manual_draft_allowed": structured.get("manual_draft_allowed"),
            "next_required_action": (
                "register_complete_clean_ticket_with_final_evidence"
            ),
            "recommended_action": structured.get("recommended_action"),
            "result_kind": structured.get("result_kind"),
            "should_be_kcs_article": structured.get("should_be_kcs_article"),
            "ticket_ref": structured.get("ticket_ref"),
            "writes_files": structured.get("writes_files"),
        }
        return (
            "KCS article drafting is blocked by the KCS Authoring tool because "
            "Python did not find a complete semantic KCS item in the clean "
            "ticket text. No reviewer-only draft was generated.\n\n"
            "Do not draft manually. Register a complete sanitized clean ticket "
            "that includes the final symptom, supported cause, and resolution "
            "evidence, then call kcs_draft_article again with the returned "
            "ticket_ref.\n\n"
            "Compact status:\n"
            "```json\n"
            f"{_compact_json(status)}\n"
            "```"
        )
    return None


def _desktop_structured_content(
    *,
    descriptor: McpToolDescriptor,
    structured: Mapping[str, Any],
) -> JsonDict:
    compact = dict(structured)
    if descriptor.name == TOOL_DRAFT_ARTICLE:
        compact.pop("reviewer_only_html", None)
    return compact


def _split_required_tool_result_text(structured: Mapping[str, Any]) -> str:
    choice_request = structured.get("operator_choice_request")
    options = (
        choice_request.get("options")
        if isinstance(choice_request, Mapping)
        else None
    )
    option_lines: list[str] = []
    if isinstance(options, list):
        for index, option in enumerate(options, start=1):
            if not isinstance(option, Mapping):
                continue
            label = str(option.get("label") or option.get("value") or f"Option {index}")
            submit_arguments = option.get("submit_arguments")
            safe_submit_arguments = (
                submit_arguments if isinstance(submit_arguments, Mapping) else {}
            )
            option_lines.append(
                f"{index}. {label}\n"
                "   submit_arguments: "
                f"{_compact_json(safe_submit_arguments)}"
            )
    status = {
        "debug_code": structured.get("debug_code"),
        "draft_request_ready": structured.get("draft_request_ready"),
        "failure_stage": structured.get("failure_stage"),
        "manual_draft_allowed": structured.get("manual_draft_allowed"),
        "next_required_action": structured.get("next_required_action"),
        "operator_selection_ref": structured.get("operator_selection_ref"),
        "recommended_action": structured.get("recommended_action"),
        "result_kind": structured.get("result_kind"),
    }
    options_text = (
        "\n".join(option_lines) if option_lines else "No safe options returned."
    )
    return (
        "Multiple KCS article candidates were detected. Operator selection is "
        "required before drafting.\n\n"
        "Use a native single-choice popup if Claude Desktop provides one. If no "
        "popup is available, ask the operator to choose one option and call "
        "kcs_draft_article again with exactly that option's submit_arguments. "
        "Do not draft manually.\n\n"
        "Candidate options:\n"
        f"{options_text}\n\n"
        "Compact status:\n"
        "```json\n"
        f"{_compact_json(status)}\n"
        "```"
    )


def _validate_tool_structured_content(
    payload: Mapping[str, Any],
    output_schema: Mapping[str, Any],
) -> None:
    require_json_object(payload)
    ensure_safe_sanitized_payload(_tool_result_payload_for_generic_safety(payload))
    _ensure_no_forbidden_tool_result_payload(payload)
    if len(_compact_json(payload).encode("utf-8")) > _MAX_TOOL_RESULT_BYTES:
        raise ContractValidationError("MCP tool result is too large")
    if not _matches_schema(payload, output_schema):
        raise ContractValidationError("MCP tool result schema mismatch")


def _tool_result_payload_for_generic_safety(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            key: (
                _mask_approved_tool_html_urls(item)
                if key in _TOOL_RESULT_HTML_FIELDS and isinstance(item, str)
                else _tool_result_payload_for_generic_safety(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_tool_result_payload_for_generic_safety(item) for item in value]
    return value


def _mask_approved_tool_html_urls(value: str) -> str:
    masked = value
    for url, safe_ref in _APPROVED_HTML_URL_REFS.items():
        masked = masked.replace(url, safe_ref)
    return masked


def _matches_schema(payload: Mapping[str, Any], schema: Mapping[str, Any]) -> bool:
    any_of = schema.get("anyOf")
    if isinstance(any_of, list):
        return any(
            isinstance(option, Mapping) and _matches_schema(payload, option)
            for option in any_of
        )
    if schema.get("type") != "object":
        return False
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    if not isinstance(properties, Mapping) or not isinstance(required, list):
        return False
    if schema.get("additionalProperties") is False and any(
        key not in properties for key in payload
    ):
        return False
    if any(not isinstance(key, str) or key not in payload for key in required):
        return False
    return all(
        _value_matches_type(value, properties.get(key))
        for key, value in payload.items()
    )


def _value_matches_type(value: object, schema: object) -> bool:
    if not isinstance(schema, Mapping):
        return False
    schema_type = schema.get("type")
    if schema_type == "boolean":
        return isinstance(value, bool)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "array":
        return isinstance(value, list)
    if schema_type == "object":
        return isinstance(value, Mapping)
    return False


def _ensure_no_forbidden_tool_result_payload(
    value: object,
    *,
    current_key: str | None = None,
) -> None:
    if isinstance(value, Mapping):
        _ensure_no_forbidden_tool_result_mapping(value)
        return
    if isinstance(value, list):
        _ensure_no_forbidden_tool_result_list(value, current_key=current_key)
        return
    if isinstance(value, str):
        _ensure_no_forbidden_tool_result_string(value, current_key=current_key)


def _ensure_no_forbidden_tool_result_mapping(value: Mapping[object, object]) -> None:
    for key, item in value.items():
        if not isinstance(key, str):
            raise ContractValidationError("MCP tool result schema mismatch")
        _ensure_no_forbidden_tool_result_key(key)
        _ensure_no_forbidden_tool_result_payload(item, current_key=key)


def _ensure_no_forbidden_tool_result_list(
    value: list[object],
    *,
    current_key: str | None,
) -> None:
    for item in value:
        _ensure_no_forbidden_tool_result_payload(item, current_key=current_key)


def _ensure_no_forbidden_tool_result_string(
    value: str,
    *,
    current_key: str | None,
) -> None:
    if current_key in _TOOL_RESULT_HTML_FIELDS:
        _ensure_no_forbidden_tool_result_html(value)
        return
    _ensure_no_forbidden_tool_result_text(value)


def _ensure_no_forbidden_tool_result_html(value: str) -> None:
    normalized = value.casefold()
    compact = normalized.replace("_", "").replace("-", "")
    if any(fragment in normalized for fragment in _RESULT_FORBIDDEN_FRAGMENTS):
        raise ContractValidationError("MCP tool result contains unsafe value")
    if any(
        fragment in compact for fragment in _RESULT_FORBIDDEN_COMPACT_FRAGMENTS
    ):
        raise ContractValidationError("MCP tool result contains unsafe value")
    for url in _HTML_URL_RE.findall(value):
        if url not in _APPROVED_HTML_URL_REFS:
            raise ContractValidationError("MCP tool result contains unsafe value")


def _ensure_no_forbidden_tool_result_text(value: str) -> None:
    normalized = value.casefold()
    compact = normalized.replace("_", "").replace("-", "")
    if any(fragment in normalized for fragment in _RESULT_FORBIDDEN_FRAGMENTS):
        raise ContractValidationError("MCP tool result contains unsafe value")
    if any(
        fragment in compact for fragment in _RESULT_FORBIDDEN_COMPACT_FRAGMENTS
    ):
        raise ContractValidationError("MCP tool result contains unsafe value")
    if _FORBIDDEN_TEXT_HTML_TAG_RE.search(value):
        raise ContractValidationError("MCP tool result contains unsafe value")


def _ensure_no_forbidden_tool_result_key(value: str) -> None:
    normalized = value.casefold()
    if normalized in _RESULT_FORBIDDEN_EXACT_KEYS:
        raise ContractValidationError("MCP tool result contains unsafe value")
    _ensure_no_forbidden_tool_result_text(value)


def _tool_error(error_code: str) -> McpToolResult:
    return McpToolResult(
        ok=False,
        error="KCS MCP tool validation failed.",
        error_code=error_code,
    )


def _approved_summary_failure_result(
    *,
    failure_stage: str,
    debug_code: str,
) -> JsonDict:
    stage_order = {
        "input_validation": 0,
        "item_identification": 0,
        "operator_selection": 0,
        "semantic_extraction": 0,
        "evidence_builder": 1,
        "input_safety": 2,
        "evidence_validation": 3,
        "decision": 4,
        "renderer": 5,
        "readiness": 6,
        "draft_request_ready": 7,
    }
    failed_index = stage_order.get(failure_stage, len(stage_order))

    def stage_passed(stage: str) -> bool:
        return stage_order[stage] < failed_index

    return {
        "auto_publish_allowed": False,
        "case_ref": "approved-summary-case-001",
        "checks": [
            {"kind": "input_validation", "ok": stage_passed("input_validation")},
            {"kind": "evidence_builder", "ok": stage_passed("evidence_builder")},
            {"kind": "input_safety", "ok": stage_passed("input_safety")},
            {
                "kind": "evidence_validation",
                "ok": stage_passed("evidence_validation"),
            },
            {"kind": "decision", "ok": stage_passed("decision")},
            {"kind": "renderer", "ok": stage_passed("renderer")},
            {"kind": "readiness", "ok": stage_passed("readiness")},
            {
                "kind": "draft_request_ready",
                "ok": stage_passed("draft_request_ready"),
            },
        ],
        "debug_code": debug_code,
        "draft_request_ready": False,
        "evidence_valid": stage_passed("evidence_validation"),
        "failure_stage": failure_stage,
        "input_safety_ok": stage_passed("input_safety"),
        "network_calls": False,
        "ok": False,
        "original_article_type": ArticleType.NONE.value,
        "original_decision_status": DecisionStatus.BLOCKED.value,
        "original_readiness_state": ReadinessState.BLOCKED.value,
        "original_recommended_action": RecommendedAction.BLOCKED.value,
        "pipeline_ok": False,
        "provider_calls": False,
        "public_output_approved": False,
        "ready_for_real_ticket_use": False,
        "ready_for_reviewer": False,
        "result_kind": "approved_summary_pipeline",
        "schema_version": MCP_TOOL_RESULT_SCHEMA_VERSION,
        "validation_ok": False,
        "writes_files": False,
    }


def _checked_approved_summary_pipeline_payload(
    arguments: Mapping[str, Any],
) -> JsonDict:
    try:
        return _desktop_payload.approved_summary_pipeline_payload(arguments)
    except ApprovedSummaryInputError as exc:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="input_validation",
            debug_code=exc.debug_code,
        ) from None
    except ApprovedSummaryPayloadArgumentError:
        raise McpArgumentError("Invalid approved summary arguments.") from None
    except ContractValidationError:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="input_validation",
            debug_code="approved_summary_input_invalid",
        ) from None


def _approved_ticket_author_arguments(arguments: Mapping[str, Any]) -> JsonDict:
    try:
        return _desktop_ticket_ref.approved_ticket_author_arguments(arguments)
    except ApprovedSummaryInputError as exc:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="input_validation",
            debug_code=exc.debug_code,
        ) from None
    except (ContractValidationError, McpArgumentError):
        raise ApprovedSummaryPipelineStageError(
            failure_stage="input_validation",
            debug_code="approved_ticket_summary_invalid",
        ) from None


def _approved_ticket_ref_from_arguments(arguments: Mapping[str, Any]) -> str:
    return _desktop_ticket_ref.approved_ticket_ref_from_arguments(arguments)


def _build_approved_summary_evidence(
    arguments: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> NormalizedTicketEvidencePacket:
    try:
        return build_evidence_packet_from_zendesk_export(
            payload,
            case_ref=_desktop_payload.approved_summary_case_ref(arguments),
            policy=EvidenceBuildPolicy(
                input_class=InputClass.OPERATOR_SANITIZED_SUMMARY.value,
                assume_sanitized=True,
            ),
        )
    except ContractValidationError:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="evidence_builder",
            debug_code="approved_summary_evidence_build_failed",
        ) from None


def _validate_approved_summary_safety(
    evidence: NormalizedTicketEvidencePacket,
) -> SafetyGateResult:
    try:
        safety = validate_evidence_safety(evidence)
    except ContractValidationError:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="input_safety",
            debug_code="approved_summary_safety_failed",
        ) from None
    if not safety.ok:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="input_safety",
            debug_code="approved_summary_safety_blocked",
        )
    return safety


def _validate_approved_summary_evidence(
    evidence: NormalizedTicketEvidencePacket,
) -> EvidenceValidationResult:
    try:
        evidence_validation = validate_evidence_packet(evidence)
    except ContractValidationError:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="evidence_validation",
            debug_code="approved_summary_evidence_validation_failed",
        ) from None
    if not evidence_validation.ok:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="evidence_validation",
            debug_code="approved_summary_evidence_validation_blocked",
        )
    return evidence_validation


def _decide_approved_summary_action(
    arguments: Mapping[str, Any],
    evidence: NormalizedTicketEvidencePacket,
) -> KcsActionDecisionPacket:
    try:
        decision = decide_kcs_action(
            evidence, _approved_summary_reuse_results(arguments)
        )
    except ContractValidationError:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="decision",
            debug_code="approved_summary_decision_failed",
        ) from None
    if decision.status != DecisionStatus.DECISION_READY.value:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="decision",
            debug_code="approved_summary_decision_blocked",
        )
    return decision


def _render_approved_summary_reviewer_packet(
    evidence: NormalizedTicketEvidencePacket,
    decision: KcsActionDecisionPacket,
) -> KcsReviewerPacket:
    try:
        return render_reviewer_packet(evidence, decision)
    except ContractValidationError:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="renderer",
            debug_code="approved_summary_renderer_failed",
        ) from None


def _build_approved_summary_readiness(
    evidence: NormalizedTicketEvidencePacket,
    decision: KcsActionDecisionPacket,
    reviewer_packet: KcsReviewerPacket,
) -> KcsValidationReportPacket:
    try:
        readiness = build_validation_report(evidence, decision, reviewer_packet)
    except ContractValidationError:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="readiness",
            debug_code="approved_summary_readiness_failed",
        ) from None
    if not readiness.ready_for_reviewer:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="readiness",
            debug_code="approved_summary_readiness_blocked",
        )
    return readiness


def _approved_summary_reuse_results(
    arguments: Mapping[str, Any],
) -> ReuseSearchResultsPacket:
    reuse_checked = _approved_summary_reuse_was_checked(arguments)
    return ReuseSearchResultsPacket(
        search_run_ref=_approved_summary_reuse_search_run_ref(arguments),
        searched=True,
        search_source=(
            "operator_approved_summary"
            if reuse_checked
            else "operator_approved_summary_reuse_skipped"
        ),
        matches=[],
        blockers=[],
    )


def _approved_summary_reuse_search_run_ref(arguments: Mapping[str, Any]) -> str:
    value = arguments.get("reuse_search_run_ref")
    item = _desktop_payload.approved_summary_optional_item_object(arguments)
    if value is None and item is not None:
        value = item.get("reuse_search_run_ref")
    if isinstance(value, str) and value.strip():
        ensure_safe_sanitized_payload(value)
        return value.strip()
    return "operator-approved-summary-reuse-skipped"


def _empty_reuse_results() -> ReuseSearchResultsPacket:
    return ReuseSearchResultsPacket(
        search_run_ref="mcp-approved-summary-reuse-001",
        searched=True,
        search_source="mcp_approved_summary",
        matches=[],
        blockers=[],
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


def _handoff_request_summary(request: KcsClaudeHandoffRequestPacket) -> JsonDict:
    return {
        "auto_publish_allowed": False,
        "case_ref": request.case_ref,
        "handoff_ref": request.handoff_ref,
        "item_ref": request.item_ref,
        "ok": True,
        "original_article_type": request.original_article_type,
        "original_decision_status": request.original_decision_status,
        "original_readiness_state": request.original_readiness_state,
        "original_recommended_action": request.original_recommended_action,
        "public_output_approved": False,
        "request_schema_version": CLAUDE_HANDOFF_REQUEST_SCHEMA_VERSION,
        "request_sha256": _payload_sha256(request),
        "result_kind": "handoff_request_validation",
        "schema_version": MCP_TOOL_RESULT_SCHEMA_VERSION,
        "validation_ok": True,
    }


def _handoff_response_summary(
    request: KcsClaudeHandoffRequestPacket,
    response: JsonPayload,
) -> JsonDict:
    return {
        "auto_publish_allowed": False,
        "handoff_ref": request.handoff_ref,
        "ok": True,
        "provider_error_code": response.to_json_dict()["provider_error_code"],
        "provider_status": response.to_json_dict()["provider_status"],
        "public_output_approved": False,
        "response_schema_version": CLAUDE_HANDOFF_RESPONSE_SCHEMA_VERSION,
        "response_sha256": _payload_sha256(response),
        "result_kind": "handoff_response_validation",
        "schema_version": MCP_TOOL_RESULT_SCHEMA_VERSION,
        "validation_ok": True,
    }


def _draft_request_summary(request: KcsClaudeDraftRequestPacket) -> JsonDict:
    return {
        "auto_publish_allowed": False,
        "case_ref": request.case_ref,
        "draft_ref": request.draft_ref,
        "handoff_ref": request.handoff_ref,
        "item_ref": request.item_ref,
        "ok": True,
        "original_article_type": request.original_article_type,
        "original_decision_status": request.original_decision_status,
        "original_readiness_state": request.original_readiness_state,
        "original_recommended_action": request.original_recommended_action,
        "public_output_approved": False,
        "request_schema_version": CLAUDE_DRAFT_REQUEST_SCHEMA_VERSION,
        "request_sha256": _payload_sha256(request),
        "result_kind": "draft_request_validation",
        "schema_version": MCP_TOOL_RESULT_SCHEMA_VERSION,
        "validation_ok": True,
    }


def _draft_response_summary(
    request: KcsClaudeDraftRequestPacket,
    response: JsonPayload,
) -> JsonDict:
    payload = response.to_json_dict()
    return {
        "auto_publish_allowed": False,
        "draft_ref": request.draft_ref,
        "draft_status": payload["draft_status"],
        "handoff_ref": request.handoff_ref,
        "ok": True,
        "provider_error_code": payload["provider_error_code"],
        "public_output_approved": False,
        "response_schema_version": CLAUDE_DRAFT_RESPONSE_SCHEMA_VERSION,
        "response_sha256": _payload_sha256(response),
        "result_kind": "draft_response_validation",
        "schema_version": MCP_TOOL_RESULT_SCHEMA_VERSION,
        "validation_ok": True,
    }


def _synthetic_handoff_request() -> KcsClaudeHandoffRequestPacket:
    return KcsClaudeHandoffRequestPacket.from_json_dict(
        {
            "artifact_refs": {
                "reviewer_packet_ref": "",
                "reviewer_packet_sha256": "",
                "zendesk_source_ref": "",
                "zendesk_source_sha256": "",
            },
            "case_ref": "case-001",
            "handoff_purpose": "reviewer_assist_notes",
            "handoff_ref": "handoff-001",
            "item_ref": "item-001",
            "operator_override": {
                "allowed_override_modes": [],
                "operator_override_allowed": False,
                "override_status": "not_requested",
            },
            "original_article_type": ArticleType.TECHNICAL_SCR.value,
            "original_decision_status": DecisionStatus.DECISION_READY.value,
            "original_readiness_state": ReadinessState.READY_FOR_REVIEWER.value,
            "original_recommended_action": RecommendedAction.CREATE_CANDIDATE.value,
            "provider_profile": "fake_provider",
            "safe_context": {
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "blocker_codes": [],
                "reason_codes": [],
                "reviewer_only_reason_codes": [],
                "short_public_safe_summary": "Synthetic safe context.",
                "status_codes": ["decision_status_decision_ready"],
                "title_hint": "Safe synthetic title",
                "warning_codes": [],
            },
            "schema_version": CLAUDE_HANDOFF_REQUEST_SCHEMA_VERSION,
        }
    )


def _synthetic_handoff_response(
    request: KcsClaudeHandoffRequestPacket,
) -> JsonDict:
    return {
        "auto_publish_allowed": False,
        "contains_article_draft": False,
        "handoff_ref": request.handoff_ref,
        "original_article_type": request.original_article_type,
        "original_decision_status": request.original_decision_status,
        "original_readiness_state": request.original_readiness_state,
        "original_recommended_action": request.original_recommended_action,
        "provider_error_code": ClaudeHandoffProviderErrorCode.NONE.value,
        "provider_status": ClaudeHandoffProviderStatus.ACCEPTED.value,
        "public_output_approved": False,
        "reviewer_assist_notes": ["Reviewer should verify the safe summary."],
        "schema_version": CLAUDE_HANDOFF_RESPONSE_SCHEMA_VERSION,
        "structured_comments": {
            "comment_codes": ["reviewer_attention_requested"],
            "needs_reviewer_attention": True,
        },
    }


def _synthetic_draft_response(request: KcsClaudeDraftRequestPacket) -> JsonDict:
    return {
        "applicable_to": "Plesk for Linux",
        "article_type": request.original_article_type,
        "auto_publish_allowed": False,
        "draft_status": ClaudeDraftStatus.ACCEPTED.value,
        "handoff_ref": request.handoff_ref,
        "internal_only_content_present": False,
        "original_article_type": request.original_article_type,
        "original_decision_status": request.original_decision_status,
        "original_readiness_state": request.original_readiness_state,
        "original_recommended_action": request.original_recommended_action,
        "provider_error_code": ClaudeDraftProviderErrorCode.NONE.value,
        "public_output_approved": False,
        "reviewer_notes": ["Reviewer should verify the synthetic draft."],
        "schema_version": CLAUDE_DRAFT_RESPONSE_SCHEMA_VERSION,
        "sections": {
            "cause": "A supported product setting is disabled.",
            "resolution": "Enable the supported product setting in Plesk.",
            "symptoms": "A safe product task fails with a reusable error.",
        },
        "title": "Plesk task fails with a reusable error",
        "unsupported_claims_present": False,
        "zendesk_source_html": (
            "<h1>Plesk task fails with a reusable error</h1>"
            "<h2>Applicable to</h2><p>Plesk for Linux</p>"
            "<h2>Symptoms</h2><p>A safe product task fails.</p>"
            "<h2>Cause</h2><p>A supported product setting is disabled.</p>"
            "<h2>Resolution</h2><ol><li>Enable the setting.</li></ol>"
        ),
    }


def _payload_sha256(payload: JsonPayload) -> str:
    return sha256(dumps_payload(payload).encode("utf-8")).hexdigest()


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
