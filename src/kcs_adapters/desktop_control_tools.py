"""Control and validation tool handlers for the Desktop MCP adapter."""

from __future__ import annotations

from collections.abc import Sequence

from kcs_adapters import desktop_contract_smoke as _desktop_contract_smoke
from kcs_adapters import desktop_protocol as _desktop_protocol
from kcs_adapters.desktop_tool_descriptors import McpToolDescriptor
from kcs_adapters.desktop_tool_names import CLAUDE_DESKTOP_TOOL_ALIASES
from kcs_core.json_payload import JsonDict
from kcs_core.models import ArticleType


def policy_summary_result(
    *,
    schema_version: str,
    tool_count: int,
) -> JsonDict:
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
        "schema_version": schema_version,
        "tool_count": tool_count,
        "writes_files": False,
    }


def readiness_result(
    *,
    schema_version: str,
    tools: Sequence[McpToolDescriptor],
) -> JsonDict:
    return {
        "auto_publish_allowed": False,
        "ok": True,
        "prompts_exposed": False,
        "protocol_version": _desktop_protocol.MCP_PROTOCOL_VERSION,
        "public_output_approved": False,
        "ready_for_real_ticket_use": False,
        "resources_exposed": False,
        "result_kind": "mcp_readiness",
        "schema_version": schema_version,
        "server_name": _desktop_protocol.MCP_DESKTOP_SERVER_NAME,
        "server_version": _desktop_protocol.MCP_DESKTOP_SERVER_VERSION,
        "tool_count": len(tools),
        "tools": [CLAUDE_DESKTOP_TOOL_ALIASES[tool.name] for tool in tools],
    }


def validate_handoff_request_result(
    request: object,
    *,
    schema_version: str,
) -> JsonDict:
    return _desktop_contract_smoke.validate_handoff_request_payload(
        request,
        schema_version=schema_version,
    )


def validate_handoff_response_result(
    request: object,
    response: object,
    *,
    schema_version: str,
) -> JsonDict:
    return _desktop_contract_smoke.validate_handoff_response_payload(
        request,
        response,
        schema_version=schema_version,
    )


def validate_draft_request_result(
    request: object,
    *,
    schema_version: str,
) -> JsonDict:
    return _desktop_contract_smoke.validate_draft_request_payload(
        request,
        schema_version=schema_version,
    )


def validate_draft_response_result(
    request: object,
    response: object,
    *,
    schema_version: str,
) -> JsonDict:
    return _desktop_contract_smoke.validate_draft_response_payload(
        request,
        response,
        schema_version=schema_version,
    )


def contract_smoke_result(*, schema_version: str) -> JsonDict:
    checks = _desktop_contract_smoke.run_contract_smoke(
        schema_version=schema_version
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
        "schema_version": schema_version,
        "smoke_ok": True,
        "writes_files": False,
    }


__all__ = [
    "contract_smoke_result",
    "policy_summary_result",
    "readiness_result",
    "validate_draft_request_result",
    "validate_draft_response_result",
    "validate_handoff_request_result",
    "validate_handoff_response_result",
]
