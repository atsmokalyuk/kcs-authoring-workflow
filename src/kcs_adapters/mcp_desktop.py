"""Claude Desktop MCP stdio adapter for KCS validator/control tools."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from pathlib import Path
from typing import IO, Any

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
    build_claude_handoff_request,
    validate_claude_handoff_response,
)
from kcs_core.decision import decide_kcs_action
from kcs_core.errors import ContractValidationError
from kcs_core.evidence_builder import (
    APPROVED_EVIDENCE_EXPORT_SCHEMA_VERSION,
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
from kcs_core.safety import (
    EvidenceVisibility,
    InputClass,
    SafetyGateResult,
    validate_evidence_safety,
)
from kcs_core.sanitizer import ensure_safe_sanitized_payload
from kcs_core.validation import EvidenceValidationResult, validate_evidence_packet

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
TOOL_DRAFT_ARTICLE = "kcs.draft_article"
DESKTOP_OPERATOR_TOOLS = frozenset(
    {
        TOOL_DRAFT_ARTICLE,
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
    TOOL_DRAFT_ARTICLE: "kcs_draft_article",
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
_SAFE_APPROVED_TICKET_REF_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}")
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
_APPROVED_SUMMARY_FALSE_ONLY_ARGS = frozenset(
    {
        "auto_publish_allowed",
        "customer_replies",
        "network_calls",
        "provider_calls",
        "public_output_approved",
        "publishes",
        "ready_for_real_ticket_use",
        "writes_files",
    }
)
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
_DRAFT_ARTICLE_ITEM_CANDIDATE_FIELDS = frozenset(
    {
        "applicable_to",
        "article_type",
        "confirmed_facts",
        "environment",
        "item_ref",
        "reason",
        "resolution_steps",
        "supported_answer",
        "supported_cause",
        "supported_resolution_or_workaround",
        "symptoms",
        "title",
    }
)
_APPROVED_SUMMARY_PIPELINE_ARGS = frozenset(
    {
        "applicable_to",
        "approved_summary_text",
        "article_type",
        "article_title",
        "auto_publish_allowed",
        "candidate_id",
        "cause",
        "case_ref",
        "commands",
        "confirmed_facts",
        "customer_replies",
        "debug",
        "diagnosis",
        "environment",
        "evidence",
        "facts",
        "fix",
        "item",
        "log_evidence",
        "logs",
        "notes",
        "open_questions",
        "problem",
        "problem_statement",
        "provider_calls",
        "public_output_approved",
        "publishes",
        "question",
        "ready_for_real_ticket_use",
        "reuse_search_checked",
        "reuse_search_run_ref",
        "reference_article",
        "reference_article_text",
        "reference_article_html",
        "resolution",
        "resolution_procedure",
        "root_cause",
        "root_cause_analysis",
        "resolution_steps",
        "resolution_summary",
        "secondary_finding",
        "secondary_findings",
        "secondary_issue",
        "secondary_issues",
        "solution",
        "summary",
        "steps",
        "supported_answer",
        "supported_cause",
        "supported_resolution_or_workaround",
        "symptom",
        "symptoms",
        "title",
        "network_calls",
        "writes_files",
    }
)
_APPROVED_TICKET_ARGS = frozenset(
    {
        "debug",
        "reference_article",
        "reference_article_html",
        "reference_article_text",
        "reuse_search_checked",
        "reuse_search_run_ref",
        "ticket_ref",
        *_APPROVED_SUMMARY_FALSE_ONLY_ARGS,
    }
)
_APPROVED_TICKET_FILE_KEYS = frozenset(
    {
        "approved_summary_text",
        "case_ref",
        "item",
        "reference_article",
        "reference_article_html",
        "reference_article_text",
        "reuse_search_checked",
        "reuse_search_run_ref",
        "schema_version",
        "ticket_ref",
    }
)
_APPROVED_TICKET_FILE_SCHEMA_VERSION = "kcs_approved_ticket_summary_v1"
_APPROVED_TICKET_SUMMARY_DIR = Path("local-data") / "approved-summaries"
_MAX_APPROVED_TICKET_FILE_BYTES = 64 * 1024
_APPROVED_SUMMARY_ITEM_FIELDS = frozenset(
    {
        "answer_steps",
        "applicable_to",
        "article_type",
        "article_title",
        "candidate_id",
        "cause",
        "commands",
        "confirmed_facts",
        "diagnosis",
        "environment",
        "evidence",
        "facts",
        "fix",
        "log_evidence",
        "logs",
        "notes",
        "open_questions",
        "problem",
        "problem_statement",
        "question",
        "reuse_search_checked",
        "reuse_search_run_ref",
        "resolution",
        "resolution_procedure",
        "resolution_steps",
        "resolution_summary",
        "root_cause",
        "root_cause_analysis",
        "secondary_finding",
        "secondary_findings",
        "secondary_issue",
        "secondary_issues",
        "solution",
        "summary",
        "steps",
        "supported_answer",
        "supported_cause",
        "supported_resolution_or_workaround",
        "symptom",
        "symptoms",
        "title",
    }
)
_APPROVED_SUMMARY_ENVIRONMENT_FIELDS = frozenset(
    {
        "component",
        "components",
        "extension",
        "operating_system",
        "os",
        "platform",
        "product",
        "version",
    }
)
_APPROVED_SUMMARY_NORMALIZED_ENVIRONMENT_FIELDS = frozenset(
    {"component", "platform", "product", "version"}
)
_APPROVED_SUMMARY_TOP_LEVEL_ITEM_FIELDS = frozenset(
    _APPROVED_SUMMARY_PIPELINE_ARGS
    - {
        "approved_summary_text",
        "case_ref",
        "debug",
        "item",
        *_APPROVED_SUMMARY_FALSE_ONLY_ARGS,
        "reference_article",
        "reference_article_html",
        "reference_article_text",
    }
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


class ApprovedSummaryInputError(ContractValidationError):
    """Value-safe approved summary input error with a compact debug code."""

    def __init__(self, debug_code: str) -> None:
        super().__init__("approved summary input invalid")
        self.debug_code = debug_code


class ApprovedSummaryPipelineStageError(ContractValidationError):
    """Value-safe approved summary pipeline stage error."""

    def __init__(self, *, failure_stage: str, debug_code: str) -> None:
        super().__init__("approved summary pipeline stage failed")
        self.failure_stage = failure_stage
        self.debug_code = debug_code


@dataclass(frozen=True)
class _ApprovedSummaryExecution:
    arguments: Mapping[str, Any]
    payload: JsonDict
    evidence: NormalizedTicketEvidencePacket
    safety: SafetyGateResult
    evidence_validation: EvidenceValidationResult
    decision: KcsActionDecisionPacket
    reviewer_packet: KcsReviewerPacket
    readiness: KcsValidationReportPacket
    handoff_request: KcsClaudeHandoffRequestPacket
    draft_request_ready: bool
    item_ref: str


class KcsDesktopMcpAdapter:
    """Read-only validator/control tool facade for Claude Desktop."""

    def __init__(self, *, visible_tools: Iterable[str] | None = None) -> None:
        self._tools: tuple[McpToolDescriptor, ...] | None = None
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
            TOOL_DRAFT_ARTICLE: self._draft_article,
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
                _draft_article_descriptor(),
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
        """Dispatch a known read-only tool."""

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

    def _draft_article(self, arguments: Mapping[str, Any]) -> JsonDict:
        try:
            draft_arguments = _draft_article_arguments(arguments)
            split_result = _draft_article_split_required_result(draft_arguments)
            if split_result is not None:
                result = split_result
            elif "ticket_ref" in draft_arguments:
                result = self._author_ticket(draft_arguments)
            elif _has_approved_summary_authoring_input(draft_arguments):
                result = self._author_approved_summary(draft_arguments)
            else:
                result = _approved_summary_author_failure_result(
                    failure_stage="input_validation",
                    debug_code="draft_article_input_missing",
                )
        except (ContractValidationError, McpArgumentError):
            result = _approved_summary_author_failure_result(
                failure_stage="input_validation",
                debug_code="draft_article_args_invalid",
            )
        result["result_kind"] = "draft_article_authoring"
        return result


def _draft_article_arguments(arguments: Mapping[str, Any]) -> Mapping[str, Any]:
    _require_args(arguments, _DRAFT_ARTICLE_ARGS, required=frozenset())
    _require_approved_summary_false_only_args(arguments)
    if "item_candidates" not in arguments:
        return arguments
    candidates = _draft_article_item_candidates(arguments["item_candidates"])
    normalized = dict(arguments)
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
    candidates = arguments.get("item_candidates")
    if not isinstance(candidates, list) or len(candidates) <= 1:
        return None
    result = _approved_summary_author_failure_result(
        failure_stage="item_identification",
        debug_code="multiple_kcs_items_detected",
    )
    result["item_candidates"] = _draft_article_split_candidate_cards(candidates)
    result["automatic_item_retry_allowed"] = False
    result["manual_draft_allowed"] = False
    result["next_required_action"] = "operator_select_single_item"
    result["recommended_action"] = "split_required"
    result["review_summary"] = {
        "draft_available": False,
        "next_required_action": "operator_select_single_item",
        "reason": "multiple_kcs_items_detected",
    }
    return result


def _draft_article_split_candidate_cards(
    candidates: list[JsonDict],
) -> list[JsonDict]:
    cards: list[JsonDict] = []
    for index, candidate in enumerate(candidates, start=1):
        item_ref = candidate.get("item_ref")
        title = candidate.get("title")
        card: JsonDict = {
            "item_ref": (
                item_ref if isinstance(item_ref, str) and item_ref else f"item-{index}"
            ),
            "title": _safe_split_candidate_text(title, fallback=f"Item {index}"),
        }
        article_type = candidate.get("article_type")
        if isinstance(article_type, str) and article_type:
            card["article_type"] = article_type
        ensure_safe_sanitized_payload(card)
        cards.append(card)
    return cards


def _safe_split_candidate_text(value: object, *, fallback: str) -> str:
    if not isinstance(value, str):
        return fallback
    text = _approved_summary_snippet(value, max_length=140)
    if not text:
        return fallback
    try:
        ensure_safe_sanitized_payload(text)
    except ContractValidationError:
        return fallback
    return text


def _has_approved_summary_authoring_input(arguments: Mapping[str, Any]) -> bool:
    if "approved_summary_text" in arguments:
        return True
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
    payload = _checked_approved_summary_pipeline_payload(arguments)
    evidence = _build_approved_summary_evidence(arguments, payload)
    safety = _validate_approved_summary_safety(evidence)
    evidence_validation = _validate_approved_summary_evidence(evidence)
    decision = _decide_approved_summary_action(arguments, evidence)
    reviewer_packet = _render_approved_summary_reviewer_packet(evidence, decision)
    readiness = _build_approved_summary_readiness(evidence, decision, reviewer_packet)
    item_ref = decision.candidate_id or _approved_summary_item_ref(arguments)
    handoff_request = build_claude_handoff_request(
        decision,
        readiness,
        handoff_ref=f"handoff-{item_ref}",
        safe_context={
            "short_public_safe_summary": _approved_summary_short_summary(arguments),
            "title_hint": _approved_summary_title(arguments),
        },
    )
    draft_request_ready = _approved_summary_draft_request_ready(
        handoff_request, item_ref, readiness
    )
    return _ApprovedSummaryExecution(
        arguments=arguments,
        payload=payload,
        evidence=evidence,
        safety=safety,
        evidence_validation=evidence_validation,
        decision=decision,
        reviewer_packet=reviewer_packet,
        readiness=readiness,
        handoff_request=handoff_request,
        draft_request_ready=draft_request_ready,
        item_ref=item_ref,
    )


def _approved_summary_draft_request_ready(
    handoff_request: KcsClaudeHandoffRequestPacket,
    item_ref: str,
    readiness: KcsValidationReportPacket,
) -> bool:
    if not readiness.ready_for_reviewer:
        return False
    try:
        build_claude_draft_request(handoff_request, draft_ref=f"draft-{item_ref}")
    except ContractValidationError:
        return False
    return True


def _approved_summary_pipeline_status(
    execution: _ApprovedSummaryExecution,
) -> JsonDict:
    decision = execution.decision
    readiness = execution.readiness
    safety = execution.safety
    evidence_validation = execution.evidence_validation
    return {
        "auto_publish_allowed": False,
        "case_ref": execution.evidence.case_ref,
        "checks": [
            {"kind": "input_validation", "ok": True},
            {"kind": "evidence_builder", "ok": True},
            {"kind": "input_safety", "ok": safety.ok},
            {"kind": "evidence_validation", "ok": evidence_validation.ok},
            {
                "kind": "decision",
                "ok": decision.status == DecisionStatus.DECISION_READY.value,
            },
            {"kind": "renderer", "ok": True},
            {"kind": "readiness", "ok": readiness.ready_for_reviewer},
            {"kind": "draft_request_ready", "ok": execution.draft_request_ready},
        ],
        "debug_code": "none",
        "draft_request_ready": execution.draft_request_ready,
        "evidence_valid": evidence_validation.ok,
        "failure_stage": "none",
        "handoff_ref": execution.handoff_request.handoff_ref,
        "input_safety_ok": safety.ok,
        "item_ref": execution.item_ref,
        "network_calls": False,
        "ok": safety.ok and readiness.ready_for_reviewer,
        "original_article_type": decision.article_type,
        "original_decision_status": decision.status,
        "original_readiness_state": readiness.state,
        "original_recommended_action": decision.recommended_action,
        "pipeline_ok": safety.ok and readiness.ready_for_reviewer,
        "provider_calls": False,
        "public_output_approved": False,
        "ready_for_real_ticket_use": False,
        "ready_for_reviewer": readiness.ready_for_reviewer,
        "result_kind": "approved_summary_pipeline",
        "reuse_search_status": _approved_summary_reuse_search_status(
            execution.arguments
        ),
        "schema_version": MCP_TOOL_RESULT_SCHEMA_VERSION,
        "validation_ok": evidence_validation.ok,
        "writes_files": False,
    }


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
    return {
        **_approved_summary_failure_result(
            failure_stage=failure_stage,
            debug_code=debug_code,
        ),
        "article_type": "none",
        "atomic_item": {},
        "blockers": [debug_code],
        "open_questions": [],
        "quality_gaps": [],
        "recommended_action": "blocked",
        "result_kind": "approved_summary_authoring",
        "review_summary": {
            "draft_available": False,
            "reason": debug_code,
        },
        "should_be_kcs_article": False,
    }


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


def _approved_summary_reviewer_only_draft(
    execution: _ApprovedSummaryExecution,
) -> JsonDict:
    candidate = _approved_summary_public_candidate(execution.reviewer_packet)
    source_candidate = _approved_summary_source_candidate(execution)
    resolution_steps = _safe_candidate_list(candidate, "resolution_steps")
    return {
        "applicable_to": _approved_summary_applicable_to(candidate),
        "cause": _safe_candidate_string(candidate, "cause"),
        "resolution": _safe_candidate_string(
            source_candidate, "supported_resolution_or_workaround"
        )
        or _safe_candidate_string(source_candidate, "supported_answer")
        or _safe_candidate_string(candidate, "resolution")
        or " ".join(resolution_steps),
        "resolution_steps": resolution_steps,
        "status": "reviewer_only",
        "symptoms": _safe_candidate_list(candidate, "symptoms"),
        "title": _safe_candidate_string(candidate, "title"),
    }


def _approved_summary_reviewer_only_html(
    execution: _ApprovedSummaryExecution,
) -> str:
    html = execution.reviewer_packet.zendesk_source_html
    if not isinstance(html, str):
        return ""
    return html


def _approved_summary_reviewer_only_preview(draft: Mapping[str, Any]) -> JsonDict:
    return {
        "applicable_to": _safe_candidate_list(draft, "applicable_to"),
        "cause": _safe_candidate_string(draft, "cause"),
        "resolution": _safe_candidate_string(draft, "resolution"),
        "resolution_steps": _safe_candidate_list(draft, "resolution_steps"),
        "status": _safe_candidate_string(draft, "status"),
        "symptoms": _safe_candidate_list(draft, "symptoms"),
        "title": _safe_candidate_string(draft, "title"),
    }


def _approved_summary_reviewer_only_preview_text(
    draft: Mapping[str, Any],
) -> str:
    preview = _approved_summary_reviewer_only_preview(draft)
    lines = [
        f"Title: {preview['title']}",
        f"Status: {preview['status']}",
        "",
        "Applicable to:",
        *_numbered_or_bulleted_lines(preview["applicable_to"], bullet="-"),
        "",
        "Symptoms:",
        *_numbered_or_bulleted_lines(preview["symptoms"], bullet="1."),
        "",
        "Cause:",
        str(preview["cause"]),
        "",
        "Resolution:",
        str(preview["resolution"]),
        "",
        "Resolution steps:",
        *_numbered_or_bulleted_lines(preview["resolution_steps"], bullet="1."),
    ]
    return "\n".join(line for line in lines if line is not None).strip()


def _numbered_or_bulleted_lines(values: object, *, bullet: str) -> list[str]:
    if not isinstance(values, list) or not values:
        return ["-"]
    if bullet == "1.":
        return [f"{index}. {value}" for index, value in enumerate(values, start=1)]
    return [f"{bullet} {value}" for value in values]


def _approved_summary_quality_gaps(
    execution: _ApprovedSummaryExecution,
    draft: Mapping[str, Any],
) -> list[JsonDict]:
    gaps: list[JsonDict] = []
    if not _safe_candidate_list(draft, "applicable_to"):
        gaps.append({"kind": "missing_applicable_to", "severity": "blocker"})
    if not _safe_candidate_list(draft, "symptoms"):
        gaps.append({"kind": "missing_symptoms", "severity": "blocker"})
    if not _safe_candidate_string(draft, "cause"):
        gaps.append({"kind": "missing_cause", "severity": "blocker"})
    if not _safe_candidate_string(draft, "resolution"):
        gaps.append({"kind": "missing_resolution", "severity": "blocker"})
    reference_text = _approved_summary_reference_text(execution.arguments)
    if reference_text is None:
        gaps.append({"kind": "reference_not_provided", "severity": "info"})
    else:
        gaps.extend(_approved_summary_reference_section_gaps(reference_text, draft))
    if not _approved_summary_reuse_was_checked(execution.arguments):
        gaps.append({"kind": "reuse_search_skipped", "severity": "warning"})
    return gaps


def _approved_summary_reference_text(arguments: Mapping[str, Any]) -> str | None:
    reference_keys = (
        "reference_article",
        "reference_article_text",
        "reference_article_html",
    )
    for key in reference_keys:
        value = arguments.get(key)
        if isinstance(value, str) and value.strip():
            ensure_safe_sanitized_payload(value)
            return value.strip()
    return None


def _approved_summary_reference_section_gaps(
    reference_text: str,
    draft: Mapping[str, Any],
) -> list[JsonDict]:
    gaps: list[JsonDict] = []
    reference = reference_text.casefold()
    section_checks = (
        (
            "applicable_to",
            "applicable to",
            _safe_candidate_list(draft, "applicable_to"),
        ),
        ("symptoms", "symptoms", _safe_candidate_list(draft, "symptoms")),
        ("cause", "cause", [_safe_candidate_string(draft, "cause")]),
        ("resolution", "resolution", [_safe_candidate_string(draft, "resolution")]),
    )
    for kind, marker, values in section_checks:
        if marker in reference and not any(values):
            gaps.append(
                {
                    "kind": f"reference_section_missing_{kind}",
                    "severity": "warning",
                }
            )
    if not gaps:
        gaps.append({"kind": "reference_section_coverage_ok", "severity": "info"})
    return gaps


def _approved_summary_open_questions(
    execution: _ApprovedSummaryExecution,
) -> list[str]:
    candidate = _approved_summary_public_candidate(execution.reviewer_packet)
    return _safe_candidate_list(candidate, "open_questions")


def _approved_summary_public_candidate(packet: KcsReviewerPacket) -> JsonDict:
    candidate = packet.public_article_candidate
    if not isinstance(candidate, Mapping):
        return {}
    return dict(candidate)


def _approved_summary_applicable_to(candidate: Mapping[str, Any]) -> list[str]:
    values = _safe_candidate_list(candidate, "applicable_to")
    return [
        value
        for value in values
        if not value.casefold().startswith("approved-summary-")
    ]


def _approved_summary_source_candidate(
    execution: _ApprovedSummaryExecution,
) -> JsonDict:
    candidates = execution.payload.get("issue_candidates")
    if not isinstance(candidates, list) or not candidates:
        return {}
    candidate = candidates[0]
    if not isinstance(candidate, Mapping):
        return {}
    return dict(candidate)


def _safe_candidate_string(candidate: Mapping[str, Any], key: str) -> str:
    value = candidate.get(key)
    if isinstance(value, str):
        return value
    return ""


def _safe_candidate_list(candidate: Mapping[str, Any], key: str) -> list[str]:
    value = candidate.get(key)
    if isinstance(value, str) and value:
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item]
    return []


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
                "KCS Authoring MCP server for approved sanitized KCS article "
                "workflows. For any request like 'draft an article', "
                "'draft me an article', 'write an article', or 'create a KB "
                "article', or equivalent non-English requests such as "
                "'напиши статью' or 'me escreva um artigo' with an approved "
                "sanitized support-ticket summary "
                "attachment or local ticket_ref, call kcs_draft_article "
                "immediately. Do not ask what kind of article to draft; the "
                "default is a reviewer-only KCS knowledge base article. Do "
                "not ask what language to use; default article language is "
                "English unless the operator explicitly requests another "
                "language. Do "
                "not ask the operator to choose between reuse search and "
                "manual drafting before the first tool call; call the tool "
                "and show its controlled status. If "
                "the tool succeeds, show reviewer_only_html as one fenced "
                "html block and then compact status. Do not draft manually "
                "when the tool fails. Do not send raw Zendesk data, internal "
                "notes, attachments, customer replies, or credentials."
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
            "The tool reads only repository-local approved summary JSON files, "
            "returns reviewer_only_html for copy/paste, does not read Zendesk, "
            "and does not publish, write files, call a provider, or return raw "
            "packet bodies."
        ),
        input_schema=_approved_ticket_input_schema(),
    )


def _draft_article_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_DRAFT_ARTICLE,
        description=(
            "Primary operator tool for any approved sanitized support-ticket "
            "article request, including 'draft an article', 'draft me an "
            "article', 'write an article', 'create a KB article', or 'draft "
            "article for ticket', including equivalent non-English requests "
            "such as 'напиши статью' or 'me escreva um artigo'. Do not ask "
            "what kind of article; default to "
            "a reviewer-only KCS knowledge base article. Do not ask what "
            "language to use; default to English unless the operator "
            "explicitly requests another language. Provide either "
            "ticket_ref for a local approved sanitized summary file, or "
            "approved_summary_text plus one structured item object from a "
            "chat attachment/paste. If the ticket contains more than one "
            "semantic KCS item, pass item_candidates instead of combining "
            "items; the tool will return split_required. For single-item "
            "chat attachment/paste input, extract and pass item.title, "
            "item.symptoms, item.confirmed_facts, item.environment or "
            "item.applicable_to, item.supported_cause, "
            "item.supported_resolution_or_workaround, and executable "
            "item.resolution_steps. Resolution steps must include the "
            "how-to detail present in the ticket, such as UI navigation, "
            "commands, file paths, service names, verification actions, or "
            "approved prerequisite links; do not pass high-level steps that "
            "require the reviewer to search for how to apply them. Do not pass "
            "a partial one-line summary as "
            "a draft request; the tool will fail closed instead of producing "
            "placeholder or thin HTML. Do not ask what kind of article and "
            "do not invent reuse/search status. If reuse/search proof is not "
            "provided, this MVP marks reuse search as skipped and continues "
            "with reviewer-only drafting. If article_type is "
            "provided, use only technical_scr or howto_qa. The tool returns "
            "reviewer_only_html plus reviewer-only draft/status output when "
            "validation passes and never publishes, "
            "writes files, reads Zendesk, calls a provider, or replies to "
            "customers."
        ),
        input_schema=_draft_article_input_schema(),
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
            "debug": {"type": "boolean"},
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


def _draft_article_input_schema() -> JsonDict:
    return _object_schema(
        properties={
            "approved_summary_text": {
                "type": "string",
                "description": (
                    "Approved sanitized support-ticket summary text. Do not pass "
                    "raw Zendesk payloads, raw comments, internal notes, or "
                    "attachments."
                ),
            },
            "auto_publish_allowed": {"type": "boolean"},
            "case_ref": {"type": "string"},
            "customer_replies": {"type": "boolean"},
            "debug": {"type": "boolean"},
            "item": _draft_article_item_schema(),
            "item_candidates": {
                "type": "array",
                "description": (
                    "Use when the approved summary appears to contain multiple "
                    "semantic KCS items. Do not combine multiple issues into one "
                    "article."
                ),
                "items": _draft_article_item_candidate_schema(),
            },
            "network_calls": {"type": "boolean"},
            "provider_calls": {"type": "boolean"},
            "public_output_approved": {"type": "boolean"},
            "publishes": {"type": "boolean"},
            "ready_for_real_ticket_use": {"type": "boolean"},
            "reference_article": {"type": "string"},
            "reference_article_html": {"type": "string"},
            "reference_article_text": {"type": "string"},
            "reuse_search_checked": {"type": "boolean"},
            "reuse_search_run_ref": {"type": "string"},
            "ticket_ref": {"type": "string"},
            "writes_files": {"type": "boolean"},
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
                    "UI navigation, commands, paths, services, and verification."
                ),
            },
            "supported_answer": {
                "type": "string",
                "description": "Required for howto_qa when applicable.",
            },
            "supported_cause": {
                "type": "string",
                "description": "Supported cause for technical_scr.",
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
    "case_ref": {"type": "string"},
    "checks": {"type": "array"},
    "customer_replies": {"type": "boolean"},
    "debug_code": {"type": "string"},
    "draft_ref": {"type": "string"},
    "draft_request_ready": {"type": "boolean"},
    "draft_sections": {"type": "object"},
    "evidence_valid": {"type": "boolean"},
    "draft_status": {"type": "string"},
    "failure_stage": {"type": "string"},
    "handoff_ref": {"type": "string"},
    "input_safety_ok": {"type": "boolean"},
    "item_candidates": {"type": "array"},
    "item_ref": {"type": "string"},
    "manual_draft_allowed": {"type": "boolean"},
    "network_calls": {"type": "boolean"},
    "next_required_action": {"type": "string"},
    "ok": {"type": "boolean"},
    "open_questions": {"type": "array"},
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
    text = _tool_result_text(structured)
    return {
        "content": [{"text": text, "type": "text"}],
        "isError": not result.ok,
        "structuredContent": structured,
    }


def _tool_result_text(structured: Mapping[str, Any]) -> str:
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
        preview_text = structured.get("reviewer_only_preview_text")
        status = {
            "article_type": structured.get("article_type"),
            "auto_publish_allowed": structured.get("auto_publish_allowed"),
            "case_ref": structured.get("case_ref"),
            "debug_code": structured.get("debug_code"),
            "draft_request_ready": structured.get("draft_request_ready"),
            "failure_stage": structured.get("failure_stage"),
            "item_ref": structured.get("item_ref"),
            "ok": structured.get("ok"),
            "pipeline_ok": structured.get("pipeline_ok"),
            "public_output_approved": structured.get("public_output_approved"),
            "ready_for_reviewer": structured.get("ready_for_reviewer"),
            "recommended_action": structured.get("recommended_action"),
            "result_kind": structured.get("result_kind"),
            "validation_ok": structured.get("validation_ok"),
        }
        return (
            "COPY THE FENCED HTML BLOCK BELOW VERBATIM IN THE FINAL ANSWER. "
            "Do not rewrite it, summarize it, convert it to Markdown, change "
            "section names, change the article type, or change Applicable to.\n\n"
            "Reviewer-only Zendesk HTML:\n"
            "```html\n"
            f"{html}\n"
            "```\n\n"
            "Reviewer preview for the tool panel only. Do not copy this "
            "preview into the final answer:\n"
            f"{preview_text if isinstance(preview_text, str) else ''}\n\n"
            "Compact status:\n"
            f"{_compact_json(status)}"
        )
    return _compact_json(structured)


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
    if "<h1" in normalized or "<p" in normalized or "</" in normalized:
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
        return _approved_summary_pipeline_payload(arguments)
    except ApprovedSummaryInputError as exc:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="input_validation",
            debug_code=exc.debug_code,
        ) from None
    except ContractValidationError:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="input_validation",
            debug_code="approved_summary_input_invalid",
        ) from None


def _approved_ticket_author_arguments(arguments: Mapping[str, Any]) -> JsonDict:
    try:
        _require_args(
            arguments,
            _APPROVED_TICKET_ARGS,
            required=frozenset({"ticket_ref"}),
        )
        _require_approved_summary_false_only_args(arguments)
        ticket_ref = _checked_approved_ticket_ref(arguments["ticket_ref"])
        file_payload = _approved_ticket_file_payload(ticket_ref)
        merged = _approved_ticket_merged_arguments(
            ticket_ref=ticket_ref,
            file_payload=file_payload,
            arguments=arguments,
        )
        _require_approved_summary_false_only_args(merged)
        return merged
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
    try:
        return _checked_approved_ticket_ref(arguments.get("ticket_ref"))
    except (ApprovedSummaryInputError, ContractValidationError):
        return "invalid-ticket-ref"


def _checked_approved_ticket_ref(value: object) -> str:
    if not isinstance(value, str) or not _SAFE_APPROVED_TICKET_REF_RE.fullmatch(value):
        raise ApprovedSummaryInputError("approved_ticket_ref_invalid")
    ensure_safe_sanitized_payload(value)
    return value


def _approved_ticket_file_payload(ticket_ref: str) -> JsonDict:
    path = _approved_ticket_summary_path(ticket_ref)
    payload = _read_approved_ticket_file_payload(path)
    _validate_approved_ticket_file_payload(payload, ticket_ref=ticket_ref)
    return payload


def _read_approved_ticket_file_payload(path: Path) -> JsonDict:
    try:
        if not path.is_file() or path.is_symlink():
            raise ApprovedSummaryInputError("approved_ticket_summary_not_found")
        if path.stat().st_size > _MAX_APPROVED_TICKET_FILE_BYTES:
            raise ApprovedSummaryInputError("approved_ticket_summary_invalid")
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle, parse_constant=_reject_json_constant)
    except ApprovedSummaryInputError:
        raise
    except (OSError, json.JSONDecodeError, ValueError):
        raise ApprovedSummaryInputError("approved_ticket_summary_invalid") from None
    if not isinstance(payload, dict):
        raise ApprovedSummaryInputError("approved_ticket_summary_invalid")
    return payload


def _validate_approved_ticket_file_payload(
    payload: Mapping[str, Any],
    *,
    ticket_ref: str,
) -> None:
    if any(key not in _APPROVED_TICKET_FILE_KEYS for key in payload):
        raise ApprovedSummaryInputError("approved_ticket_summary_invalid")
    ensure_safe_sanitized_payload(payload)
    if payload.get("schema_version") != _APPROVED_TICKET_FILE_SCHEMA_VERSION:
        raise ApprovedSummaryInputError("approved_ticket_summary_invalid")
    if payload.get("ticket_ref") != ticket_ref:
        raise ApprovedSummaryInputError("approved_ticket_summary_invalid")


def _approved_ticket_summary_path(ticket_ref: str) -> Path:
    root = _approved_ticket_repo_root()
    return root / _APPROVED_TICKET_SUMMARY_DIR / f"{ticket_ref}.json"


def _approved_ticket_repo_root() -> Path:
    value = os.environ.get("KCS_AUTHORING_MVP_REPO_ROOT")
    root = Path(value) if value else Path.cwd()
    return root.resolve(strict=False)


def _approved_ticket_merged_arguments(
    *,
    ticket_ref: str,
    file_payload: Mapping[str, Any],
    arguments: Mapping[str, Any],
) -> JsonDict:
    merged: JsonDict = {
        key: value
        for key, value in file_payload.items()
        if key not in {"schema_version", "ticket_ref"}
    }
    merged.setdefault("case_ref", f"approved-ticket-{ticket_ref}")
    for key in (
        "debug",
        "reference_article",
        "reference_article_html",
        "reference_article_text",
        "reuse_search_checked",
        "reuse_search_run_ref",
        *_APPROVED_SUMMARY_FALSE_ONLY_ARGS,
    ):
        if key in arguments:
            merged[key] = arguments[key]
    return merged


def _build_approved_summary_evidence(
    arguments: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> NormalizedTicketEvidencePacket:
    try:
        return build_evidence_packet_from_zendesk_export(
            payload,
            case_ref=_approved_summary_case_ref(arguments),
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


def _approved_summary_pipeline_payload(arguments: Mapping[str, Any]) -> JsonDict:
    _require_approved_summary_args(arguments)
    approved_summary_text = _approved_summary_text_argument(arguments)
    item = _approved_summary_checked_item(arguments, approved_summary_text)
    article_type = _approved_summary_checked_article_type(item)
    candidate_id = _approved_summary_checked_item_ref(arguments)
    environment = _approved_summary_checked_environment(item)
    resolution_steps = _approved_summary_optional_string_list(
        item, "resolution_steps"
    )
    _require_approved_summary_authoring_fields(
        article_type=article_type,
        environment=environment,
        resolution_steps=resolution_steps,
    )
    candidate: JsonDict = {
        "article_type": article_type,
        "atomic": True,
        "candidate_id": candidate_id,
        "confirmed_facts": _approved_summary_required_string_list(
            item, "confirmed_facts"
        ),
        "customer_reported": True,
        "kcs_applicable": True,
        "public_solution_safe": True,
        "resolution_state": "solved",
        "resolution_steps": resolution_steps,
        "source_refs": [f"approved-summary-source-{candidate_id}"],
        "summary": _approved_summary_required_string(item, "summary"),
        "symptoms": _approved_summary_required_string_list(item, "symptoms"),
        "title": _approved_summary_required_string(item, "title"),
    }
    optional_string_fields = (
        "question",
        "supported_answer",
        "supported_cause",
        "supported_resolution_or_workaround",
    )
    for field_name in optional_string_fields:
        value = _approved_summary_optional_string(item, field_name)
        if value is not None:
            candidate[field_name] = value
    optional_list_fields = ("answer_steps", "applicable_to", "open_questions")
    for field_name in optional_list_fields:
        values = _approved_summary_optional_string_list(item, field_name)
        if values:
            candidate[field_name] = values
    if environment:
        candidate["environment"] = environment
    return {
        "confirmed_facts": candidate["confirmed_facts"],
        "environment": environment,
        "input_class": InputClass.OPERATOR_SANITIZED_SUMMARY.value,
        "issue_candidates": [candidate],
        "open_questions": _approved_summary_optional_string_list(
            item, "open_questions"
        ),
        "sanitizer_report": {},
        "schema_version": APPROVED_EVIDENCE_EXPORT_SCHEMA_VERSION,
        "source_refs": ["approved-summary-source-001"],
        "supported_cause": candidate.get("supported_cause"),
        "supported_resolution_or_workaround": candidate.get(
            "supported_resolution_or_workaround"
        )
        or candidate.get("supported_answer"),
        "symptoms": candidate["symptoms"],
        "visibility_summary": {
            "classes": [EvidenceVisibility.PUBLIC_CUSTOMER_SAFE.value]
        },
    }


def _require_approved_summary_args(arguments: Mapping[str, Any]) -> None:
    try:
        _require_args(
            arguments,
            _APPROVED_SUMMARY_PIPELINE_ARGS,
            required=frozenset(),
        )
        _require_approved_summary_false_only_args(arguments)
    except McpArgumentError:
        raise ApprovedSummaryInputError("approved_summary_args_invalid") from None


def _require_approved_summary_false_only_args(arguments: Mapping[str, Any]) -> None:
    for key in _APPROVED_SUMMARY_FALSE_ONLY_ARGS:
        if key in arguments and arguments[key] is not False:
            raise ApprovedSummaryInputError("approved_summary_policy_flag_invalid")


def _approved_summary_text_argument(arguments: Mapping[str, Any]) -> str:
    value = arguments.get("approved_summary_text")
    if isinstance(value, str) and value.strip():
        try:
            ensure_safe_sanitized_payload(value)
        except ContractValidationError:
            raise ApprovedSummaryInputError(
                "approved_summary_text_invalid"
            ) from None
        return value.strip()
    if value is not None:
        raise ApprovedSummaryInputError("approved_summary_text_invalid") from None
    text = _approved_summary_text_from_structured_arguments(arguments)
    if text:
        return text
    raise ApprovedSummaryInputError("approved_summary_text_invalid") from None


def _approved_summary_checked_item(
    arguments: Mapping[str, Any],
    approved_summary_text: str,
) -> JsonDict:
    try:
        return _approved_summary_item(arguments, approved_summary_text)
    except McpArgumentError:
        raise
    except ContractValidationError:
        raise ApprovedSummaryInputError("approved_summary_item_invalid") from None


def _approved_summary_checked_article_type(item: Mapping[str, Any]) -> str:
    try:
        return _approved_summary_article_type(item)
    except ContractValidationError:
        raise ApprovedSummaryInputError(
            "approved_summary_article_type_invalid"
        ) from None


def _approved_summary_checked_item_ref(arguments: Mapping[str, Any]) -> str:
    try:
        return _approved_summary_item_ref(arguments)
    except ContractValidationError:
        raise ApprovedSummaryInputError("approved_summary_item_ref_invalid") from None


def _approved_summary_checked_environment(item: Mapping[str, Any]) -> JsonDict:
    try:
        return _approved_summary_environment(item)
    except McpArgumentError:
        raise
    except ContractValidationError:
        raise ApprovedSummaryInputError(
            "approved_summary_environment_invalid"
        ) from None


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


def _approved_summary_reuse_was_checked(arguments: Mapping[str, Any]) -> bool:
    item = _approved_summary_optional_item_object(arguments)
    reuse_checked = arguments.get("reuse_search_checked")
    if reuse_checked is None and item is not None:
        reuse_checked = item.get("reuse_search_checked")
    return reuse_checked is True


def _approved_summary_reuse_search_status(arguments: Mapping[str, Any]) -> str:
    return "checked" if _approved_summary_reuse_was_checked(arguments) else "skipped"


def _approved_summary_reuse_search_run_ref(arguments: Mapping[str, Any]) -> str:
    value = arguments.get("reuse_search_run_ref")
    item = _approved_summary_optional_item_object(arguments)
    if value is None and item is not None:
        value = item.get("reuse_search_run_ref")
    if isinstance(value, str) and value.strip():
        ensure_safe_sanitized_payload(value)
        return value.strip()
    return "operator-approved-summary-reuse-skipped"


def _approved_summary_optional_item_object(
    arguments: Mapping[str, Any],
) -> JsonDict | None:
    if "item" not in arguments:
        return None
    return require_json_object(arguments["item"])


def _approved_summary_case_ref(arguments: Mapping[str, Any]) -> str:
    value = arguments.get("case_ref")
    if isinstance(value, str) and value.strip():
        try:
            ensure_safe_sanitized_payload(value)
        except ContractValidationError:
            raise ApprovedSummaryInputError(
                "approved_summary_case_ref_invalid"
            ) from None
        return _opaque_approved_summary_case_ref(value)
    return "approved-summary-case-001"


def _opaque_approved_summary_case_ref(value: str) -> str:
    digest = sha256(value.strip().encode("utf-8")).hexdigest()[:12]
    return f"approved-summary-case-{digest}"


def _approved_summary_item_ref(arguments: Mapping[str, Any]) -> str:
    item = _approved_summary_item(
        arguments,
        _approved_summary_text_argument(arguments),
    )
    value = item.get("candidate_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "item-001"


def _approved_summary_title(arguments: Mapping[str, Any]) -> str:
    item = _approved_summary_item(
        arguments,
        _approved_summary_text_argument(arguments),
    )
    return _required_string(item, "title")


def _approved_summary_short_summary(arguments: Mapping[str, Any]) -> str:
    item = _approved_summary_item(
        arguments,
        _approved_summary_text_argument(arguments),
    )
    return _required_string(item, "summary")


def _approved_summary_item(
    arguments: Mapping[str, Any],
    approved_summary_text: str,
) -> JsonDict:
    if "item" in arguments:
        item = require_json_object(arguments["item"])
        if any(key not in _APPROVED_SUMMARY_ITEM_FIELDS for key in item):
            raise McpArgumentError("Unexpected approved summary item field.")
        ensure_safe_sanitized_payload(item)
        return _apply_approved_summary_item_defaults(
            _normalize_approved_summary_item(dict(item)),
            approved_summary_text,
        )

    item: JsonDict = {}
    for key in sorted(_APPROVED_SUMMARY_TOP_LEVEL_ITEM_FIELDS):
        if key in arguments:
            item[key] = arguments[key]
    item = _normalize_approved_summary_item(item)
    return _apply_approved_summary_item_defaults(item, approved_summary_text)


def _apply_approved_summary_item_defaults(
    item: JsonDict,
    approved_summary_text: str,
) -> JsonDict:
    summary = _approved_summary_snippet(approved_summary_text, max_length=500)
    item.setdefault("article_type", ArticleType.TECHNICAL_SCR.value)
    item.setdefault("summary", summary)
    if "environment" not in item and "applicable_to" in item:
        item["environment"] = item["applicable_to"]
    item.setdefault(
        "applicable_to",
        _approved_summary_applicable_to_from_environment(item.get("environment"))
        or ["Approved sanitized support context"],
    )
    _promote_resolution_steps_to_supported_resolution(item)
    ensure_safe_sanitized_payload(item)
    return item


def _promote_resolution_steps_to_supported_resolution(item: JsonDict) -> None:
    if "supported_resolution_or_workaround" in item or "supported_answer" in item:
        return
    resolution_steps = _optional_string_list(item, "resolution_steps")
    if resolution_steps:
        item["supported_resolution_or_workaround"] = " ".join(resolution_steps)


def _normalize_approved_summary_item(item: JsonDict) -> JsonDict:
    _move_item_alias(item, "article_title", "title")
    _move_item_alias(item, "symptom", "symptoms")
    _move_item_alias(item, "problem", "symptoms")
    _move_item_alias(item, "problem_statement", "symptoms")
    _move_item_alias(item, "evidence", "confirmed_facts")
    _move_item_alias(item, "facts", "confirmed_facts")
    _move_item_alias(item, "log_evidence", "confirmed_facts")
    _move_item_alias(item, "logs", "confirmed_facts")
    _move_item_alias(item, "notes", "confirmed_facts")
    _move_item_alias(item, "secondary_finding", "confirmed_facts")
    _move_item_alias(item, "secondary_findings", "confirmed_facts")
    _move_item_alias(item, "secondary_issue", "confirmed_facts")
    _move_item_alias(item, "secondary_issues", "confirmed_facts")
    _move_item_alias(item, "root_cause", "supported_cause")
    _move_item_alias(item, "root_cause_analysis", "supported_cause")
    _move_item_alias(item, "cause", "supported_cause")
    _move_item_alias(item, "diagnosis", "supported_cause")
    _move_item_alias(item, "resolution_summary", "supported_resolution_or_workaround")
    _move_item_alias(item, "resolution", "supported_resolution_or_workaround")
    _move_item_alias(item, "resolution_procedure", "supported_resolution_or_workaround")
    _move_item_alias(item, "solution", "supported_resolution_or_workaround")
    _move_item_alias(item, "fix", "supported_resolution_or_workaround")
    _move_item_alias(item, "steps", "resolution_steps")
    _move_item_alias(item, "commands", "resolution_steps")
    return item


def _move_item_alias(item: JsonDict, alias: str, canonical: str) -> None:
    value = item.pop(alias, None)
    if value is not None and canonical not in item:
        item[canonical] = value


def _approved_summary_text_from_structured_arguments(
    arguments: Mapping[str, Any],
) -> str:
    item = _approved_summary_structured_item_for_text(arguments)
    if not item:
        return ""
    fragments: list[str] = []
    for key in (
        "title",
        "symptoms",
        "confirmed_facts",
        "supported_cause",
        "supported_resolution_or_workaround",
        "resolution_steps",
        "environment",
        "applicable_to",
    ):
        fragments.extend(_approved_summary_text_fragments(item.get(key)))
    text = " ".join(fragment for fragment in fragments if fragment).strip()
    ensure_safe_sanitized_payload(text)
    return _approved_summary_snippet(text, max_length=900) if text else ""


def _approved_summary_structured_item_for_text(
    arguments: Mapping[str, Any],
) -> JsonDict:
    if "item" in arguments:
        item = require_json_object(arguments["item"])
        if any(key not in _APPROVED_SUMMARY_ITEM_FIELDS for key in item):
            raise ApprovedSummaryInputError("approved_summary_item_invalid")
        return _normalize_approved_summary_item(dict(item))
    item: JsonDict = {}
    for key in sorted(_APPROVED_SUMMARY_TOP_LEVEL_ITEM_FIELDS):
        if key in arguments:
            item[key] = arguments[key]
    return _normalize_approved_summary_item(item)


def _approved_summary_text_fragments(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, Mapping):
        fragments: list[str] = []
        for item in value.values():
            fragments.extend(_approved_summary_text_fragments(item))
        return fragments
    if isinstance(value, list | tuple):
        fragments: list[str] = []
        for item in value:
            fragments.extend(_approved_summary_text_fragments(item))
        return fragments
    return []


def _approved_summary_article_type(item: Mapping[str, Any]) -> str:
    value = _required_string(item, "article_type")
    try:
        article_type = ArticleType(value)
    except ValueError:
        raise ContractValidationError("approved summary article_type invalid") from None
    if article_type == ArticleType.NONE:
        raise ContractValidationError("approved summary article_type invalid")
    return article_type.value


def _approved_summary_environment(item: Mapping[str, Any]) -> JsonDict:
    value = item.get("environment")
    if value is None:
        return {}
    if isinstance(value, str):
        ensure_safe_sanitized_payload(value)
        return {"platform": _approved_summary_snippet(value, max_length=180)}
    if isinstance(value, list | tuple):
        return _approved_summary_environment_from_labels(value)
    environment = require_json_object(value)
    if any(key not in _APPROVED_SUMMARY_ENVIRONMENT_FIELDS for key in environment):
        raise McpArgumentError("Unexpected approved summary environment field.")
    ensure_safe_sanitized_payload(environment)
    normalized = dict(environment)
    component_values = _approved_summary_environment_values(
        normalized.pop("component", None)
    )
    component_values.extend(
        _approved_summary_environment_values(normalized.pop("components", None))
    )
    component_values.extend(
        _approved_summary_environment_values(normalized.pop("extension", None))
    )
    if component_values:
        normalized["component"] = " / ".join(component_values)
    platform_alias = normalized.pop("os", None) or normalized.pop(
        "operating_system", None
    )
    if platform_alias is not None and "platform" not in normalized:
        normalized["platform"] = platform_alias
    return {
        key: value
        for key, value in normalized.items()
        if key in _APPROVED_SUMMARY_NORMALIZED_ENVIRONMENT_FIELDS
    }


def _approved_summary_environment_from_labels(value: object) -> JsonDict:
    labels = _approved_summary_environment_label_values(value)
    if not labels:
        raise McpArgumentError("Unexpected approved summary environment field.")
    return {"platform": _approved_summary_snippet(" / ".join(labels), max_length=180)}


def _require_approved_summary_authoring_fields(
    *,
    article_type: str,
    environment: Mapping[str, Any],
    resolution_steps: list[str],
) -> None:
    if not environment:
        raise ApprovedSummaryInputError("approved_summary_environment_required")
    if article_type == ArticleType.TECHNICAL_SCR.value and not resolution_steps:
        raise ApprovedSummaryInputError("approved_summary_resolution_steps_required")
    if article_type == ArticleType.TECHNICAL_SCR.value:
        _require_executable_resolution_steps(resolution_steps)


def _require_executable_resolution_steps(resolution_steps: list[str]) -> None:
    executable_steps = sum(
        1 for step in resolution_steps if _RESOLUTION_EXECUTABLE_DETAIL_RE.search(step)
    )
    detailed_steps = sum(
        1 for step in resolution_steps if _resolution_step_has_executable_detail(step)
    )
    if len(resolution_steps) <= 2:
        minimum_detailed_steps = len(resolution_steps)
    else:
        minimum_detailed_steps = max(2, (len(resolution_steps) + 1) // 2)
    if executable_steps < 1 or detailed_steps < minimum_detailed_steps:
        raise ApprovedSummaryInputError("approved_summary_resolution_steps_incomplete")


def _resolution_step_has_executable_detail(step: str) -> bool:
    return bool(
        _RESOLUTION_EXECUTABLE_DETAIL_RE.search(step)
        or _RESOLUTION_INFORMATIONAL_DETAIL_RE.search(step)
    )


def _approved_summary_applicable_to_from_environment(value: object) -> list[str]:
    values = _approved_summary_environment_label_values(value)
    seen: set[str] = set()
    result: list[str] = []
    for item in values:
        label = _approved_summary_snippet(item, max_length=120)
        key = label.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(label)
    return result[:8]


def _approved_summary_environment_label_values(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        ensure_safe_sanitized_payload(value)
        return _split_approved_summary_environment_text(value)
    if isinstance(value, Mapping):
        labels: list[str] = []
        for key in (
            "product",
            "component",
            "components",
            "extension",
            "platform",
            "os",
            "operating_system",
            "version",
        ):
            labels.extend(_approved_summary_environment_label_values(value.get(key)))
        return labels
    if isinstance(value, list | tuple):
        labels: list[str] = []
        for item in value:
            labels.extend(_approved_summary_environment_label_values(item))
        return labels
    return []


def _split_approved_summary_environment_text(value: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"[;,]", value) if part.strip()]
    return parts or [value.strip()]


def _approved_summary_environment_values(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        if not value.strip():
            raise McpArgumentError("Unexpected approved summary environment field.")
        ensure_safe_sanitized_payload(value)
        return [value.strip()]
    if not isinstance(value, list):
        raise McpArgumentError("Unexpected approved summary environment field.")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise McpArgumentError("Unexpected approved summary environment field.")
        ensure_safe_sanitized_payload(item)
        result.append(item.strip())
    return result


def _approved_summary_default_title(summary: str) -> str:
    sentence = summary.split(".", 1)[0].strip()
    if not sentence:
        sentence = "Approved sanitized KCS candidate"
    return _approved_summary_snippet(sentence, max_length=140)


def _approved_summary_snippet(value: str, *, max_length: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 1].rstrip(" ,.;:") + "."


def _approved_summary_required_string(item: Mapping[str, Any], key: str) -> str:
    try:
        return _required_string(item, key)
    except ContractValidationError:
        raise ApprovedSummaryInputError("approved_summary_content_invalid") from None


def _approved_summary_optional_string(
    item: Mapping[str, Any], key: str
) -> str | None:
    try:
        return _optional_string(item, key)
    except ContractValidationError:
        raise ApprovedSummaryInputError("approved_summary_content_invalid") from None


def _approved_summary_required_string_list(
    item: Mapping[str, Any], key: str
) -> list[str]:
    try:
        return _required_string_list(item, key)
    except ContractValidationError:
        raise ApprovedSummaryInputError("approved_summary_content_invalid") from None


def _approved_summary_optional_string_list(
    item: Mapping[str, Any], key: str
) -> list[str]:
    try:
        return _optional_string_list(item, key)
    except ContractValidationError:
        raise ApprovedSummaryInputError("approved_summary_content_invalid") from None


def _required_string(item: Mapping[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError("approved summary field invalid")
    ensure_safe_sanitized_payload(value)
    return value.strip()


def _required_argument_string(arguments: Mapping[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError("approved summary argument invalid")
    ensure_safe_sanitized_payload(value)
    return value.strip()


def _optional_string(item: Mapping[str, Any], key: str) -> str | None:
    value = item.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError("approved summary field invalid")
    ensure_safe_sanitized_payload(value)
    return value.strip()


def _required_string_list(item: Mapping[str, Any], key: str) -> list[str]:
    values = _optional_string_list(item, key)
    if not values:
        raise ContractValidationError("approved summary field invalid")
    return values


def _optional_string_list(item: Mapping[str, Any], key: str) -> list[str]:
    value = item.get(key)
    if value is None:
        return []
    if isinstance(value, str):
        return _string_list_from_scalar(value)
    if not isinstance(value, list):
        raise ContractValidationError("approved summary field invalid")
    result: list[str] = []
    for entry in value:
        if not isinstance(entry, str) or not entry.strip():
            raise ContractValidationError("approved summary field invalid")
        ensure_safe_sanitized_payload(entry)
        result.append(entry.strip())
    return result


def _string_list_from_scalar(value: str) -> list[str]:
    if not value.strip():
        raise ContractValidationError("approved summary field invalid")
    values = _string_or_json_string_list(value)
    for entry in values:
        ensure_safe_sanitized_payload(entry)
    return values


def _string_or_json_string_list(value: str) -> list[str]:
    stripped = value.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        try:
            parsed = json.loads(stripped)
        except ValueError:
            parsed = None
        if isinstance(parsed, list) and all(
            isinstance(entry, str) and entry.strip() for entry in parsed
        ):
            return [entry.strip() for entry in parsed]
    return [stripped]


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
