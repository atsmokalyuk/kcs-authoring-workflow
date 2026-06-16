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
    ReadinessState,
    RecommendedAction,
    ReuseSearchResultsPacket,
)
from kcs_core.readiness import build_validation_report
from kcs_core.renderer import render_reviewer_packet
from kcs_core.safety import EvidenceVisibility, InputClass, validate_evidence_safety
from kcs_core.sanitizer import ensure_safe_sanitized_payload
from kcs_core.validation import validate_evidence_packet

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

CLAUDE_DESKTOP_TOOL_ALIASES = {
    TOOL_GET_POLICY_SUMMARY: "kcs_get_policy_summary",
    TOOL_GET_MCP_READINESS: "kcs_get_mcp_readiness",
    TOOL_VALIDATE_HANDOFF_REQUEST: "kcs_validate_handoff_request",
    TOOL_VALIDATE_HANDOFF_RESPONSE: "kcs_validate_handoff_response",
    TOOL_VALIDATE_DRAFT_REQUEST: "kcs_validate_draft_request",
    TOOL_VALIDATE_DRAFT_RESPONSE: "kcs_validate_draft_response",
    TOOL_RUN_CONTRACT_SMOKE: "kcs_run_contract_smoke",
    TOOL_RUN_APPROVED_SUMMARY_PIPELINE: "kcs_run_approved_summary_pipeline",
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
_APPROVED_SUMMARY_PIPELINE_ARGS = frozenset(
    {"approved_summary_text", "case_ref", "item"}
)
_APPROVED_SUMMARY_ITEM_FIELDS = frozenset(
    {
        "answer_steps",
        "applicable_to",
        "article_type",
        "candidate_id",
        "confirmed_facts",
        "environment",
        "open_questions",
        "question",
        "resolution_steps",
        "summary",
        "supported_answer",
        "supported_cause",
        "supported_resolution_or_workaround",
        "symptoms",
        "title",
    }
)
_APPROVED_SUMMARY_ENVIRONMENT_FIELDS = frozenset(
    {"component", "platform", "product", "version"}
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


class KcsDesktopMcpAdapter:
    """Read-only validator/control tool facade for Claude Desktop."""

    def __init__(self) -> None:
        self._tools: tuple[McpToolDescriptor, ...] | None = None
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
        }

    def list_tools(self) -> tuple[McpToolDescriptor, ...]:
        """Return the fixed KCS-12 tool surface."""

        if self._tools is None:
            self._tools = (
                _policy_summary_descriptor(),
                _readiness_descriptor(),
                _validate_handoff_request_descriptor(),
                _validate_handoff_response_descriptor(),
                _validate_draft_request_descriptor(),
                _validate_draft_response_descriptor(),
                _contract_smoke_descriptor(),
                _approved_summary_pipeline_descriptor(),
            )
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
        payload = _approved_summary_pipeline_payload(arguments)
        evidence = build_evidence_packet_from_zendesk_export(
            payload,
            case_ref=_approved_summary_case_ref(arguments),
            policy=EvidenceBuildPolicy(
                input_class=InputClass.OPERATOR_SANITIZED_SUMMARY.value,
                assume_sanitized=True,
            ),
        )
        safety = validate_evidence_safety(evidence)
        evidence_validation = validate_evidence_packet(evidence)
        decision = decide_kcs_action(evidence, _empty_reuse_results())
        reviewer_packet = render_reviewer_packet(evidence, decision)
        readiness = build_validation_report(evidence, decision, reviewer_packet)
        item_ref = decision.candidate_id or _approved_summary_item_ref(arguments)
        handoff_ref = f"handoff-{item_ref}"
        handoff_request = build_claude_handoff_request(
            decision,
            readiness,
            handoff_ref=handoff_ref,
            safe_context={
                "short_public_safe_summary": _approved_summary_short_summary(
                    arguments
                ),
                "title_hint": _approved_summary_title(arguments),
            },
        )
        draft_request_ready = False
        if readiness.ready_for_reviewer:
            try:
                build_claude_draft_request(
                    handoff_request,
                    draft_ref=f"draft-{item_ref}",
                )
                draft_request_ready = True
            except ContractValidationError:
                draft_request_ready = False
        return {
            "auto_publish_allowed": False,
            "case_ref": evidence.case_ref,
            "checks": [
                {"kind": "input_safety", "ok": safety.ok},
                {"kind": "evidence_validation", "ok": evidence_validation.ok},
                {
                    "kind": "decision",
                    "ok": decision.status == DecisionStatus.DECISION_READY.value,
                },
                {"kind": "readiness", "ok": readiness.ready_for_reviewer},
                {"kind": "draft_request_ready", "ok": draft_request_ready},
            ],
            "draft_request_ready": draft_request_ready,
            "evidence_valid": evidence_validation.ok,
            "handoff_ref": handoff_request.handoff_ref,
            "input_safety_ok": safety.ok,
            "item_ref": item_ref,
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
            "schema_version": MCP_TOOL_RESULT_SCHEMA_VERSION,
            "validation_ok": evidence_validation.ok,
            "writes_files": False,
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
        self._adapter = adapter or KcsDesktopMcpAdapter()
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
                "KCS Authoring validator/control MCP server. Exposes compact "
                "read-only validation tools only. Do not send raw Zendesk data, "
                "internal notes, attachments, customer replies, or credentials."
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
        return _mcp_tool_response(descriptor=descriptor, result=result)

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
            "Provide approved_summary_text plus item fields: title, article_type, "
            "symptoms, confirmed_facts, supported_cause, "
            "supported_resolution_or_workaround, resolution_steps, applicable_to, "
            "and environment. The tool returns compact status only."
        ),
        input_schema=_object_schema(
            properties={
                "approved_summary_text": {"type": "string"},
                "case_ref": {"type": "string"},
                "item": {"type": "object"},
            },
            required=["approved_summary_text", "item"],
        ),
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
    "case_ref": {"type": "string"},
    "checks": {"type": "array"},
    "customer_replies": {"type": "boolean"},
    "draft_ref": {"type": "string"},
    "draft_request_ready": {"type": "boolean"},
    "evidence_valid": {"type": "boolean"},
    "draft_status": {"type": "string"},
    "handoff_ref": {"type": "string"},
    "input_safety_ok": {"type": "boolean"},
    "item_ref": {"type": "string"},
    "network_calls": {"type": "boolean"},
    "ok": {"type": "boolean"},
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
    "ready_for_reviewer": {"type": "boolean"},
    "ready_for_real_ticket_use": {"type": "boolean"},
    "request_schema_version": {"type": "string"},
    "request_sha256": {"type": "string"},
    "resources_exposed": {"type": "boolean"},
    "response_schema_version": {"type": "string"},
    "response_sha256": {"type": "string"},
    "result_kind": {"type": "string"},
    "schema_version": {"type": "string"},
    "server_name": {"type": "string"},
    "server_version": {"type": "string"},
    "smoke_ok": {"type": "boolean"},
    "tool_count": {"type": "integer"},
    "tools": {"type": "array"},
    "validation_ok": {"type": "boolean"},
    "writes_files": {"type": "boolean"},
}
_SUCCESS_OUTPUT_KEYS = frozenset(_SUCCESS_OUTPUT_PROPERTIES)


def _desktop_input_schema(input_schema: Mapping[str, Any]) -> JsonDict:
    properties = input_schema.get("properties", {})
    if not isinstance(properties, Mapping):
        properties = {}
    required = input_schema.get("required", [])
    if not isinstance(required, list) or not all(
        isinstance(item, str) for item in required
    ):
        required = []
    safe_properties: JsonDict = {}
    for name, schema in properties.items():
        if isinstance(name, str) and isinstance(schema, Mapping):
            safe_properties[name] = {"type": schema.get("type", "object")}
    return _object_schema(properties=safe_properties, required=required)


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
    text = _compact_json(structured)
    return {
        "content": [{"text": text, "type": "text"}],
        "isError": not result.ok,
        "structuredContent": structured,
    }


def _validate_tool_structured_content(
    payload: Mapping[str, Any],
    output_schema: Mapping[str, Any],
) -> None:
    require_json_object(payload)
    ensure_safe_sanitized_payload(payload)
    _ensure_no_forbidden_tool_result_payload(payload)
    if len(_compact_json(payload).encode("utf-8")) > _MAX_TOOL_RESULT_BYTES:
        raise ContractValidationError("MCP tool result is too large")
    if not _matches_schema(payload, output_schema):
        raise ContractValidationError("MCP tool result schema mismatch")


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


def _ensure_no_forbidden_tool_result_payload(value: object) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ContractValidationError("MCP tool result schema mismatch")
            _ensure_no_forbidden_tool_result_key(key)
            _ensure_no_forbidden_tool_result_payload(item)
        return
    if isinstance(value, list):
        for item in value:
            _ensure_no_forbidden_tool_result_payload(item)
        return
    if isinstance(value, str):
        _ensure_no_forbidden_tool_result_text(value)


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


def _approved_summary_pipeline_payload(arguments: Mapping[str, Any]) -> JsonDict:
    _require_args(
        arguments,
        _APPROVED_SUMMARY_PIPELINE_ARGS,
        required=frozenset({"approved_summary_text", "item"}),
    )
    _required_argument_string(arguments, "approved_summary_text")
    item = require_json_object(arguments["item"])
    if any(key not in _APPROVED_SUMMARY_ITEM_FIELDS for key in item):
        raise McpArgumentError("Unexpected approved summary item field.")
    ensure_safe_sanitized_payload(item)
    article_type = _approved_summary_article_type(item)
    candidate_id = _approved_summary_item_ref(arguments)
    environment = _approved_summary_environment(item)
    candidate: JsonDict = {
        "article_type": article_type,
        "atomic": True,
        "candidate_id": candidate_id,
        "confirmed_facts": _required_string_list(item, "confirmed_facts"),
        "customer_reported": True,
        "kcs_applicable": True,
        "public_solution_safe": True,
        "resolution_state": "solved",
        "resolution_steps": _optional_string_list(item, "resolution_steps"),
        "reuse_search_status": "checked",
        "source_refs": [f"approved-summary-source-{candidate_id}"],
        "summary": _required_string(item, "summary"),
        "symptoms": _required_string_list(item, "symptoms"),
        "title": _required_string(item, "title"),
    }
    optional_string_fields = (
        "question",
        "supported_answer",
        "supported_cause",
        "supported_resolution_or_workaround",
    )
    for field_name in optional_string_fields:
        value = _optional_string(item, field_name)
        if value is not None:
            candidate[field_name] = value
    optional_list_fields = ("answer_steps", "applicable_to", "open_questions")
    for field_name in optional_list_fields:
        values = _optional_string_list(item, field_name)
        if values:
            candidate[field_name] = values
    if environment:
        candidate["environment"] = environment
    return {
        "confirmed_facts": candidate["confirmed_facts"],
        "environment": environment
        or {
            "component": "product-component",
            "platform": "supported-platform",
            "product": "supported-product",
        },
        "input_class": InputClass.OPERATOR_SANITIZED_SUMMARY.value,
        "issue_candidates": [candidate],
        "open_questions": _optional_string_list(item, "open_questions"),
        "sanitizer_report": None,
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


def _approved_summary_case_ref(arguments: Mapping[str, Any]) -> str:
    value = arguments.get("case_ref")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "approved-summary-case-001"


def _approved_summary_item_ref(arguments: Mapping[str, Any]) -> str:
    item = require_json_object(arguments["item"])
    value = item.get("candidate_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "item-001"


def _approved_summary_title(arguments: Mapping[str, Any]) -> str:
    item = require_json_object(arguments["item"])
    return _required_string(item, "title")


def _approved_summary_short_summary(arguments: Mapping[str, Any]) -> str:
    item = require_json_object(arguments["item"])
    return _required_string(item, "summary")


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
    environment = require_json_object(value)
    if any(key not in _APPROVED_SUMMARY_ENVIRONMENT_FIELDS for key in environment):
        raise McpArgumentError("Unexpected approved summary environment field.")
    ensure_safe_sanitized_payload(environment)
    return dict(environment)


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
    if not isinstance(value, list):
        raise ContractValidationError("approved summary field invalid")
    result: list[str] = []
    for entry in value:
        if not isinstance(entry, str) or not entry.strip():
            raise ContractValidationError("approved summary field invalid")
        ensure_safe_sanitized_payload(entry)
        result.append(entry.strip())
    return result


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
