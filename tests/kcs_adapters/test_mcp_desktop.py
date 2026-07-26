from __future__ import annotations

import io
import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

import kcs_adapters
from kcs_adapters import (
    desktop_authoring_pipeline,
    desktop_semantic_candidates,
    desktop_semantic_review,
    desktop_tool_results,
    desktop_workflow,
    mcp_desktop,
)
from kcs_adapters.desktop_semantic_candidate_contract import (
    semantic_submission_correction,
)
from kcs_adapters.desktop_workflow import (
    ApprovedSummarySemanticExtractionProvider,
    FixtureSemanticExtractionProvider,
)
from kcs_adapters.mcp_desktop import (
    MCP_PROTOCOL_VERSION,
    TOOL_AUTHOR_APPROVED_SUMMARY,
    TOOL_AUTHOR_TICKET,
    TOOL_DRAFT_ARTICLE,
    TOOL_DRAFT_TICKET,
    TOOL_GET_POLICY_SUMMARY,
    TOOL_NAME_STYLE_CANONICAL,
    TOOL_PREPARE_SEMANTIC_REVIEW,
    TOOL_REGISTER_CLEAN_TICKET,
    TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
    TOOL_RUN_CONTRACT_SMOKE,
    TOOL_SUBMIT_SEMANTIC_REVIEW,
    TOOL_VALIDATE_DRAFT_RESPONSE,
    TOOL_VALIDATE_HANDOFF_REQUEST,
    TOOL_VALIDATE_HANDOFF_RESPONSE,
    KcsDesktopMcpAdapter,
    McpStdioTransport,
    McpToolResult,
    canonical_tool_name_from_claude_desktop_alias,
    claude_desktop_tool_alias,
    serve_stdio,
)
from kcs_core.claude_draft import (
    CLAUDE_DRAFT_RESPONSE_SCHEMA_VERSION,
    ClaudeDraftProviderErrorCode,
    ClaudeDraftStatus,
    build_claude_draft_request,
)
from kcs_core.claude_handoff import (
    CLAUDE_HANDOFF_RESPONSE_SCHEMA_VERSION,
    ClaudeHandoffProviderErrorCode,
    ClaudeHandoffProviderStatus,
    KcsClaudeHandoffRequestPacket,
)
from kcs_core.errors import ContractValidationError
from kcs_core.models import (
    ArticleType,
    DecisionStatus,
    ReadinessState,
    RecommendedAction,
)
from kcs_core.semantic_extraction import (
    CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION,
    SEMANTIC_ISSUE_PROPOSAL_SCHEMA_VERSION,
    KcsItemStatus,
    ProductRelation,
    Supportability,
    SupportabilityBasis,
    VisibilityHint,
)
from kcs_core.validation import EvidenceValidationResult


class _FakeSemanticExtractionProvider:
    def __init__(self, candidates: list[dict[str, object]]) -> None:
        self.candidates = candidates
        self.calls: list[str] = []

    def propose_candidates(self, context):
        self.calls.append(str(context.get("approved_summary_text", "")))
        return {
            "case_ref": "test-semantic-case-001",
            "extraction_source_ref": "test-semantic-run-001",
            "items": [self._semantic_item(candidate) for candidate in self.candidates],
            "schema_version": CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION,
            "source_refs": ["test-semantic-source-001"],
        }

    def _semantic_item(self, candidate: dict[str, object]) -> dict[str, object]:
        item_ref = str(candidate.get("item_ref") or "candidate-001")
        summary = str(
            candidate.get("title")
            or candidate.get("summary")
            or "Monitoring graphs show no data"
        )
        article_type = str(
            candidate.get("article_type") or ArticleType.TECHNICAL_SCR.value
        )
        environment = candidate.get("environment")
        if not isinstance(environment, dict):
            environment = {
                "applicable_to": ["Plesk for Linux"],
                "platform": "Plesk for Linux",
            }
        item: dict[str, object] = {
            "article_type_hint": article_type,
            "candidate_id": item_ref,
            "confirmed_facts": candidate.get(
                "confirmed_facts",
                ["The diagnostic summary references service.log and service.conf."],
            ),
            "environment": environment,
            "kcs_item_status": KcsItemStatus.CANDIDATE_ALLOWED.value,
            "product_relation": ProductRelation.PLESK_OWNED.value,
            "source_refs": [f"test-semantic-source-{item_ref}"],
            "summary": summary,
            "supportability": Supportability.SUPPORTED.value,
            "supportability_basis": SupportabilityBasis.NOT_CHECKED.value,
            "symptoms": candidate.get(
                "symptoms",
                ["Monitoring graphs show no data."],
            ),
            "visibility_hint": VisibilityHint.PUBLIC_CUSTOMER_SAFE.value,
        }
        for source_key, target_key in (
            ("supported_cause", "supported_cause"),
            (
                "supported_resolution_or_workaround",
                "supported_resolution_or_workaround",
            ),
            ("resolution_steps", "resolution_steps"),
            ("question", "question"),
            ("supported_answer", "supported_answer"),
        ):
            if source_key in candidate:
                item[target_key] = candidate[source_key]
        if article_type == ArticleType.TECHNICAL_SCR.value:
            item.setdefault(
                "supported_cause",
                "A required product-side package is missing.",
            )
            item.setdefault(
                "supported_resolution_or_workaround",
                "Confirm the package status, restart the service, and verify graphs.",
            )
            item.setdefault(
                "resolution_steps",
                [
                    "Run rpm -q product-side-package to confirm the package status.",
                    (
                        "Run systemctl restart product-service to restart the "
                        "related service."
                    ),
                    (
                        "Open the monitoring module page in the Plesk UI and "
                        "confirm graphs load."
                    ),
                ],
            )
        return item


def _handoff_request(**overrides: object) -> KcsClaudeHandoffRequestPacket:
    payload: dict[str, object] = {
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
        "schema_version": "kcs_claude_handoff_request_v1",
    }
    payload.update(overrides)
    return KcsClaudeHandoffRequestPacket.from_json_dict(payload)


def _handoff_response(
    request: KcsClaudeHandoffRequestPacket | None = None,
    **overrides: object,
) -> dict[str, object]:
    request = request or _handoff_request()
    payload: dict[str, object] = {
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
    payload.update(overrides)
    return payload


def _draft_response(**overrides: object) -> dict[str, object]:
    request = _draft_request()
    payload: dict[str, object] = {
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
        "reviewer_notes": ["Reviewer should verify the safe draft."],
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
    payload.update(overrides)
    return payload


def _draft_request():
    return build_claude_draft_request(_handoff_request(), draft_ref="draft-001")


def _request(method: str, params: object | None = None, request_id: object = 1):
    return {
        "id": request_id,
        "jsonrpc": "2.0",
        "method": method,
        "params": {} if params is None else params,
    }


def _initialized_transport(
    *,
    adapter: KcsDesktopMcpAdapter | None = None,
    tool_name_style: str = "claude_desktop_aliases",
) -> McpStdioTransport:
    transport = McpStdioTransport(adapter=adapter, tool_name_style=tool_name_style)
    response = transport.handle_message(
        _request("initialize", {"protocolVersion": MCP_PROTOCOL_VERSION})
    )
    assert response is not None
    assert response["result"]["protocolVersion"] == MCP_PROTOCOL_VERSION
    assert (
        transport.handle_message(
            {"jsonrpc": "2.0", "method": "notifications/initialized"}
        )
        is None
    )
    return transport


def _call_tool(
    transport: McpStdioTransport,
    name: str,
    arguments: object | None = None,
):
    return transport.handle_message(
        _request(
            "tools/call",
            {"arguments": {} if arguments is None else arguments, "name": name},
        )
    )


def _tool_text(response: Mapping[str, Any]) -> str:
    content = response.get("result", {}).get("content", [])
    assert isinstance(content, list)
    for item in content:
        assert isinstance(item, Mapping)
        if item.get("type") == "text":
            text = item.get("text")
            assert isinstance(text, str)
            return text
    raise AssertionError("missing text content")


def _tool_html_resource_text(response: Mapping[str, Any]) -> str:
    content = response.get("result", {}).get("content", [])
    assert isinstance(content, list)
    for item in content:
        assert isinstance(item, Mapping)
        if item.get("type") == "text":
            text = item.get("text")
            assert isinstance(text, str)
            if text.startswith("```html\n") and "\n```\n\n```json\n" in text:
                return text.split("```html\n", 1)[1].split("\n```\n\n```json\n", 1)[0]
    raise AssertionError("missing html text block")


def _call_author_approved_summary(arguments: object | None = None):
    return _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_AUTHOR_APPROVED_SUMMARY,
        arguments,
    )


def _assert_draft_article_call_shape_invalid(arguments: object) -> dict[str, object]:
    response = _call_tool(
        _initialized_transport(),
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        arguments,
    )

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "input_validation"
    assert structured["debug_code"] == "draft_article_call_shape_invalid"
    assert "reviewer_only_html" not in structured
    assert "zendesk_source_html" not in result_text
    return structured


def _approved_summary_args(**overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "applicable_to": ["Plesk Obsidian for Linux"],
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "candidate_id": "item-001",
        "confirmed_facts": [
            "The product module request completes but graphs show no data.",
            "The diagnostic summary references service.log and service.conf.",
        ],
        "environment": {
            "component": "Monitoring",
            "platform": "Linux",
            "product": "Plesk",
        },
        "resolution_steps": [
            "Run rpm -q product-side-package to confirm the package status.",
            "Run systemctl restart product-service to restart the related service.",
            "Open the monitoring module page in the Plesk UI and confirm graphs load.",
        ],
        "summary": "Product monitoring graphs show no data after module load.",
        "supported_cause": "A required product-side package is missing.",
        "supported_resolution_or_workaround": (
            "Install the missing package and restart the related service."
        ),
        "symptoms": ["Product monitoring graphs show no data."],
        "title": "Monitoring graphs show no data in Plesk",
    }
    item_override = overrides.pop("item", {})
    if isinstance(item_override, dict):
        item.update(item_override)
    payload: dict[str, object] = {
        "approved_summary_text": (
            "Approved sanitized summary: product monitoring graphs show no data. "
            "The summary references service.log and service.conf."
        ),
        "case_ref": "approved-summary-case-001",
        "item": item,
        "reuse_search_checked": True,
        "reuse_search_run_ref": "reuse-search-001",
    }
    payload.update(overrides)
    return payload


def _semantic_candidate(**overrides: object) -> dict[str, object]:
    candidate = dict(_approved_summary_args()["item"])
    candidate.pop("candidate_id", None)
    candidate.pop("summary", None)
    candidate["item_ref"] = "candidate-001"
    candidate["reason"] = "Monitoring graphs have no datapoints."
    candidate.update(overrides)
    return candidate


def _labeled_summary() -> str:
    return (
        "Title: Monitoring graphs show no data in Plesk\n"
        "Applicable To: Plesk for Linux\n"
        "Symptoms:\n"
        "- Monitoring graphs show no data.\n"
        "Confirmed facts:\n"
        "- The diagnostic summary references service.log and service.conf.\n"
        "Cause: A required product-side package is missing.\n"
        "Resolution steps:\n"
        "- Run rpm -q product-side-package to confirm the package status.\n"
        "- Run systemctl restart product-service to restart the related service.\n"
        "- Open the monitoring module page in the Plesk UI and confirm graphs load.\n"
    )


def _narrative_monitoring_summary() -> str:
    return (
        "Summary: Monitoring graphs show no data in Plesk.\n\n"
        "Investigation:\n"
        "1. Logs showed plugin-loading errors, but the datasource endpoint "
        "still returned metric names.\n"
        "2. A working reference server did not have the same ownership issue "
        "under /usr/local/psa/var/modules/monitoring/.\n"
        "3. Root cause was found in "
        "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf, an unowned "
        "configuration file. Its DataDir setting pointed collectd to write RRD "
        "metric files to a non-standard path that the Monitoring backend does "
        "not query.\n\n"
        "Resolution: The unowned collectd config file was backed up and "
        "removed from /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf, and "
        "the sw-collectd service was restarted. New metric data began writing "
        "to the expected location and Monitoring graphs started displaying "
        "data again. Older data may not appear, and graphs repopulate "
        "gradually as new metrics are collected.\n"
    )


def _compact_monitoring_summary() -> str:
    return (
        "Monitoring graphs show no data in Plesk. Root cause was found in "
        "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf, an unowned "
        "configuration file with a non-standard DataDir that the Monitoring "
        "backend does not query. The config file was backed up and removed, "
        "and the sw-collectd service was restarted."
    )


def _raw_monitoring_ticket_summary() -> str:
    return (
        "# Customer Ticket Content\n\n"
        "When loading the monitoring module in Plesk, none of the graphs show "
        "any data. Uninstalling and reinstalling the Monitoring extension did "
        "not resolve the issue.\n\n"
        "The datasource endpoint returned metric names, but no datapoints were "
        "returned for the graphs. A working reference server was compared with "
        "the affected server. Root cause was found in "
        "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf. This unowned "
        "collectd configuration file set DataDir to a non-standard path under "
        "/usr/local/psa/var/modules/monitoring/rrd that the Monitoring backend "
        "does not query.\n\n"
        "The config file was backed up and removed from "
        "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf, and the "
        "sw-collectd service was restarted. The Monitoring graphs started "
        "displaying data again. Older data may not appear; graphs repopulate "
        "gradually as new metrics are collected.\n\n"
        "-- {{PERSON_NAME_001}} Technical Support Engineer\n"
        "[{{SHELL_USERHOST_001}} ~]# rpm -qf "
        "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf\n"
        "file /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf is not owned "
        "by any package\n"
    )


def _raw_monitoring_ticket_without_explicit_fix_verbs() -> str:
    return (
        "# Customer Ticket Content\n\n"
        "When loading the monitoring module in Plesk, none of the graphs show "
        "any data. We have un-installed and re-installed the extension, and "
        "it still displays no data.\n\n"
        "The datasource endpoint returns metric names, but no datapoints are "
        "returned for the graphs. The affected server has "
        "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf with a DataDir "
        "value pointing under /usr/local/psa/var/modules/monitoring/rrd. "
        "That location is not queried by the Monitoring backend.\n\n"
        "After correcting the collectd configuration, the Monitoring graphs "
        "started displaying data again. The graphs repopulate gradually with "
        "newly collected metrics; older data from before the correction may "
        "not be visible.\n"
    )


def _multi_item_labeled_summary() -> str:
    return (
        "Item 1: Monitoring graphs show no data in Plesk\n"
        "Applicable To: Plesk for Linux\n"
        "Symptoms:\n"
        "- Monitoring graphs show no data.\n"
        "Confirmed facts:\n"
        "- The diagnostic summary references service.log and service.conf.\n"
        "Cause: A required product-side package is missing.\n"
        "Resolution steps:\n"
        "- Run rpm -q product-side-package to confirm the package status.\n"
        "- Run systemctl restart product-service to restart the related service.\n"
        "\n"
        "Item 2: Monitoring extension post-install fails\n"
        "Applicable To: Plesk for Linux\n"
        "Symptoms:\n"
        "- Monitoring extension post-install fails.\n"
        "Confirmed facts:\n"
        "- The module directory ownership is incorrect.\n"
        "Cause: The module directory is owned by root instead of psaadm.\n"
        "Resolution steps:\n"
        "- Run ls -ld /usr/local/psa/var/modules/monitoring/.\n"
        "- Reinstall the monitoring extension from Plesk Extensions.\n"
    )


def _windows_labeled_summary() -> str:
    return (
        "Title: Plesk scheduled task fails on Windows\n"
        "Applicable To: Plesk for Windows\n"
        "Symptoms:\n"
        "- A Plesk scheduled task fails on Windows.\n"
        "Confirmed facts:\n"
        "- The diagnostic summary references Windows service status.\n"
        "Cause: A required Plesk Windows service is stopped.\n"
        "Resolution steps:\n"
        "- Connect to the Plesk server via RDP.\n"
        "- Open the Windows Services screen and confirm the Plesk service status.\n"
        "- Run plesk repair installation to repair the supported installation.\n"
    )


def _howto_labeled_summary() -> str:
    return (
        "Title: How to restart a Plesk service on Linux\n"
        "Applicable To: Plesk for Linux\n"
        "Question: How to restart a Plesk service on Linux?\n"
        "Answer: Connect to the Plesk server via SSH and run "
        "systemctl restart product-service.\n"
    )


def _write_approved_ticket_summary(
    tmp_path,
    *,
    ticket_ref: str = "ticket-001",
    **overrides: object,
) -> None:
    payload = _approved_summary_args()
    payload["schema_version"] = "kcs_approved_ticket_summary_v1"
    payload["ticket_ref"] = ticket_ref
    payload.update(overrides)
    source_dir = tmp_path / "local-data" / "approved-summaries"
    source_dir.mkdir(parents=True)
    (source_dir / f"{ticket_ref}.json").write_text(
        json.dumps(payload, sort_keys=True),
        encoding="utf-8",
    )


def _write_clean_ticket_text(
    tmp_path,
    text: str,
    *,
    ticket_ref: str = "ticket-001",
) -> None:
    source_dir = tmp_path / "local-data" / "approved-summaries" / ticket_ref
    source_dir.mkdir(parents=True)
    (source_dir / "clean.ticket.txt").write_text(text, encoding="utf-8")


def test_initialize_lifecycle_and_capabilities_are_narrow() -> None:
    transport = McpStdioTransport()

    before_init = transport.handle_message(_request("tools/list"))
    initialize = transport.handle_message(
        _request("initialize", {"protocolVersion": MCP_PROTOCOL_VERSION})
    )
    before_initialized = transport.handle_message(_request("tools/list"))
    initialized = transport.handle_message(
        {"jsonrpc": "2.0", "method": "notifications/initialized"}
    )
    after_initialized = transport.handle_message(_request("tools/list"))

    assert before_init is not None
    assert before_init["error"]["code"] == -32002
    assert initialize is not None
    _assert_narrow_initialize_capabilities(initialize["result"])
    _assert_desktop_initialize_instructions(initialize["result"]["instructions"])
    assert "logging" not in initialize["result"]["capabilities"]
    assert before_initialized is not None
    assert before_initialized["error"]["code"] == -32002
    assert initialized is None
    assert after_initialized is not None
    assert "tools" in after_initialized["result"]


def _assert_narrow_initialize_capabilities(result: Mapping[str, Any]) -> None:
    assert result["capabilities"] == {
        "tools": {"listChanged": False},
        "resources": {"subscribe": False, "listChanged": False},
        "prompts": {"listChanged": False},
    }


def _assert_desktop_initialize_instructions(instructions: str) -> None:
    _assert_text_includes(
        instructions,
        (
            "kcs_draft_article",
            "kcs_register_clean_ticket",
            "approved_summary_text",
            "ticket_ref",
            "first call kcs_register_clean_ticket",
            "configured approved-summaries store",
            "Use only the listed KCS Authoring tools",
            "legacy instruction",
            "support_get_behavior_instructions",
            "Plesk Support Assistant Local",
            "Do not report Plesk Support Assistant Local as missing",
            "Claude Desktop file card is not a filesystem path",
            "do not inspect upload directories",
            "item/item_candidates",
            "kcs_prepare_semantic_review",
            "kcs_submit_semantic_review",
            "reuse_comparison_required",
            "kcs_confirm_reuse_comparison",
            "exactly one operator question",
            "do not normalize or strip it",
        ),
    )
    _assert_text_excludes(
        instructions,
        (
            "raw comments",
            "internal notes",
            "attachments",
            "draft an article",
            "validation tools only",
        ),
    )


def test_initialize_accepts_claude_desktop_capability_namespace() -> None:
    response = McpStdioTransport().handle_message(
        _request(
            "initialize",
            {
                "capabilities": {
                    "extensions": {
                        "io.modelcontextprotocol/ui": {
                            "mimeTypes": ["text/html;profile=mcp-app"]
                        }
                    }
                },
                "clientInfo": {"name": "claude-ai", "version": "0.1.0"},
                "protocolVersion": MCP_PROTOCOL_VERSION,
            },
            request_id=0,
        )
    )

    assert response is not None
    assert response["id"] == 0
    assert response["result"]["protocolVersion"] == MCP_PROTOCOL_VERSION


def test_initialize_rejects_unsupported_protocol_version_value_safely() -> None:
    response = McpStdioTransport().handle_message(
        _request("initialize", {"protocolVersion": "2024-11-05"})
    )

    assert response is not None
    assert response["error"]["code"] == -32602
    assert "2024-11-05" not in json.dumps(response)


@pytest.mark.parametrize(
    "request_id",
    [
        "person@example.com",
        "customer.example.net",
        "PLSK-12345678-1234",
        "/Users/alex/private",
        "token=SECRET",
    ],
)
def test_jsonrpc_rejects_private_request_id_without_echo(request_id: str) -> None:
    response = McpStdioTransport().handle_message(
        _request(
            "initialize",
            {"protocolVersion": MCP_PROTOCOL_VERSION},
            request_id=request_id,
        )
    )

    text = json.dumps(response, sort_keys=True)
    assert response is not None
    assert response["error"]["code"] == -32600
    assert response["id"] is None
    assert request_id not in text


def test_jsonrpc_rejects_unknown_top_level_private_field_without_echo() -> None:
    response = McpStdioTransport().handle_message(
        {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "ping",
            "params": {},
            "raw_ticket": "person@example.com",
        }
    )

    text = json.dumps(response, sort_keys=True)
    assert response is not None
    assert response["error"]["code"] == -32600
    assert response["id"] is None
    assert "person@example.com" not in text


def test_initialize_rejects_unknown_private_params_without_echo() -> None:
    private_value = "https://customer.example.net/private"

    response = McpStdioTransport().handle_message(
        _request(
            "initialize",
            {
                "attachment_url": private_value,
                "protocolVersion": MCP_PROTOCOL_VERSION,
            },
        )
    )

    text = json.dumps(response, sort_keys=True)
    assert response is not None
    assert response["error"]["code"] == -32602
    assert "customer.example.net" not in text


def test_initialize_rejects_private_capability_metadata_without_echo() -> None:
    private_value = "token=SECRET"

    response = McpStdioTransport().handle_message(
        _request(
            "initialize",
            {
                "capabilities": {"experimental": private_value},
                "protocolVersion": MCP_PROTOCOL_VERSION,
            },
        )
    )

    text = json.dumps(response, sort_keys=True)
    assert response is not None
    assert response["error"]["code"] == -32602
    assert "SECRET" not in text


@pytest.mark.parametrize(
    "method",
    [
        "ping",
        "tools/list",
        "resources/list",
        "resources/templates/list",
        "prompts/list",
    ],
)
def test_empty_param_methods_reject_raw_params_without_echo(method: str) -> None:
    transport = _initialized_transport()

    response = transport.handle_message(
        _request(method, {"raw_ticket": "person@example.com", "token": "SECRET"})
    )

    text = json.dumps(response, sort_keys=True)
    assert response is not None
    assert response["error"]["code"] == -32602
    assert "person@example.com" not in text
    assert "SECRET" not in text


def test_resources_prompts_and_resource_templates_empty() -> None:
    transport = _initialized_transport()

    resources = transport.handle_message(_request("resources/list"))
    prompts = transport.handle_message(_request("prompts/list"))
    templates = transport.handle_message(_request("resources/templates/list"))

    assert resources is not None
    assert resources["result"] == {"resources": []}
    assert prompts is not None
    assert prompts["result"] == {"prompts": []}
    assert templates is not None
    assert templates["result"] == {"resourceTemplates": []}


def test_tools_list_desktop_mode_exposes_aliases_only_with_safe_annotations() -> None:
    transport = _initialized_transport()

    response = transport.handle_message(_request("tools/list"))

    assert response is not None
    tools = response["result"]["tools"]
    tool_names = {tool["name"] for tool in tools}
    assert "kcs.validate_handoff_request" not in tool_names
    assert "kcs_validate_handoff_request" not in tool_names
    assert "kcs_validate_handoff_response" not in tool_names
    assert "kcs_validate_draft_request" not in tool_names
    assert "kcs_validate_draft_response" not in tool_names
    assert tool_names == {
        "kcs_register_clean_ticket",
        "kcs_draft_ticket",
        "kcs_draft_article",
        "kcs_confirm_reuse_comparison",
        "kcs_prepare_semantic_review",
        "kcs_submit_semantic_review",
        "support_get_behavior_instructions",
    }
    assert [tool["name"] for tool in tools][:3] == [
        "kcs_draft_ticket",
        "kcs_register_clean_ticket",
        "kcs_draft_article",
    ]
    assert len(tools) == 7
    for tool in tools:
        _assert_desktop_tool_contract(tool)

    tools_by_name = _tools_by_name(tools)
    _assert_register_clean_ticket_tool(tools_by_name["kcs_register_clean_ticket"])
    _assert_draft_article_tool(tools_by_name["kcs_draft_article"])
    _assert_confirm_reuse_comparison_tool(
        tools_by_name["kcs_confirm_reuse_comparison"]
    )
    _assert_prepare_semantic_review_tool(
        tools_by_name["kcs_prepare_semantic_review"]
    )
    _assert_submit_semantic_review_tool(
        tools_by_name["kcs_submit_semantic_review"]
    )
    _assert_draft_ticket_tool(tools_by_name["kcs_draft_ticket"])


def _tools_by_name(tools: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {tool["name"]: tool for tool in tools}


def _assert_desktop_tool_contract(tool: Mapping[str, Any]) -> None:
    assert tool["annotations"]["destructiveHint"] is False
    assert tool["annotations"]["openWorldHint"] is False
    assert "inputSchema" in tool
    assert "outputSchema" not in tool
    assert tool["inputSchema"]["additionalProperties"] is False


def _assert_schema_shape(
    schema: Mapping[str, Any],
    *,
    properties: set[str],
    required: list[str] | None = None,
) -> None:
    assert set(schema["properties"]) == properties
    if required is not None:
        assert schema["required"] == required


def _assert_tool_annotations(
    tool: Mapping[str, Any],
    *,
    read_only: bool,
    idempotent: bool,
) -> None:
    assert tool["annotations"]["readOnlyHint"] is read_only
    assert tool["annotations"]["idempotentHint"] is idempotent


def _assert_text_includes(value: str, terms: Sequence[str]) -> None:
    for term in terms:
        assert term in value


def _assert_text_excludes(value: str, terms: Sequence[str]) -> None:
    for term in terms:
        assert term not in value


def _assert_register_clean_ticket_tool(tool: Mapping[str, Any]) -> None:
    _assert_text_includes(
        tool["description"],
        (
            "sanitized ticket text is visible",
            "no ticket_ref exists",
            "clean_ticket_text",
            "next_arguments",
        ),
    )
    _assert_schema_shape(
        tool["inputSchema"],
        properties={"clean_ticket_text", "debug", "ticket_ref"},
        required=["clean_ticket_text"],
    )
    _assert_tool_annotations(tool, read_only=False, idempotent=False)


def _assert_draft_article_tool(tool: Mapping[str, Any]) -> None:
    _assert_text_includes(
        tool["description"],
        (
            "short approved_summary_text",
            "For `/draft <ticket_ref>`, use kcs_draft_ticket",
        ),
    )
    _assert_text_excludes(
        tool["description"],
        ("item object", "item_candidates only", "break-fix"),
    )
    schema = tool["inputSchema"]
    _assert_schema_shape(
        schema,
        properties={
            "approved_summary_text",
            "debug",
            "operator_confirmed_resolution_steps",
            "operator_selected_item_ref",
            "operator_selected_item_refs",
            "operator_selection_ref",
        },
    )
    summary_description = schema["properties"]["approved_summary_text"]["description"]
    _assert_text_includes(
        summary_description,
        (
            "Short inline sanitized text",
            "kcs_register_clean_ticket",
            "attachments",
        ),
    )
    _assert_text_excludes(summary_description, ("raw comments", "internal notes"))
    debug_description = schema["properties"]["debug"]["description"]
    _assert_text_includes(
        debug_description,
        ("explicit debug or smoke compatibility", "reviewer-only Zendesk HTML"),
    )
    for hidden_alias in (
        "auto_publish_allowed",
        "case_ref",
        "item",
        "item_candidates",
        "operator_choice_confirmed",
        "article_title",
        "commands",
        "diagnosis",
        "problem",
        "provider_calls",
        "reference_article_html",
        "reuse_search_checked",
        "solution",
        "steps",
        "ticket_ref",
    ):
        assert hidden_alias not in schema["properties"]
    _assert_tool_annotations(tool, read_only=False, idempotent=False)


def _assert_prepare_semantic_review_tool(tool: Mapping[str, Any]) -> None:
    _assert_text_includes(
        tool["description"],
        ("semantic_review_required", "bounded excerpts"),
    )
    schema = tool["inputSchema"]
    _assert_schema_shape(
        schema,
        properties={"semantic_review_ref"},
        required=["semantic_review_ref"],
    )
    assert "Opaque semantic-review ref" in schema["properties"][
        "semantic_review_ref"
    ]["description"]
    _assert_tool_annotations(tool, read_only=True, idempotent=True)


def _assert_confirm_reuse_comparison_tool(tool: Mapping[str, Any]) -> None:
    _assert_text_includes(
        tool["description"],
        (
            "operator-confirmed outcome",
            "Copy comparison_ref exactly",
            "Do not include ticket facts",
        ),
    )
    schema = tool["inputSchema"]
    _assert_schema_shape(
        schema,
        properties={"candidate_ref", "comparison_ref", "outcome"},
        required=["comparison_ref", "outcome"],
    )
    assert schema["properties"]["outcome"]["enum"] == [
        "reuse",
        "update",
        "none_fit",
        "need_more_evidence",
    ]
    _assert_tool_annotations(tool, read_only=False, idempotent=False)


def _assert_draft_ticket_tool(tool: Mapping[str, Any]) -> None:
    assert "Use immediately" in tool["description"]
    assert "/draft <ticket_ref>" in tool["description"]
    assert "only ticket_ref" in tool["description"]
    assert "do not normalize or strip it" in tool["description"]
    assert "Do not ask for an attachment" in tool["description"]
    schema = tool["inputSchema"]
    assert set(schema["properties"]) == {"debug", "ticket_ref"}
    assert schema["required"] == ["ticket_ref"]
    assert "Opaque clean-ticket ref" in schema["properties"]["ticket_ref"][
        "description"
    ]
    assert tool["annotations"]["readOnlyHint"] is False
    assert tool["annotations"]["idempotentHint"] is False


def _assert_submit_semantic_review_tool(tool: Mapping[str, Any]) -> None:
    assert "Submit semantic_issue_proposal_v1" in tool["description"]
    assert "candidate_semantic_extraction_v1" not in tool["description"]
    assert "No article draft" in tool["description"]
    schema = tool["inputSchema"]
    assert set(schema["properties"]) == {
        "semantic_issue_proposal",
        "semantic_review_ref",
    }
    assert schema["required"] == [
        "semantic_issue_proposal",
        "semantic_review_ref",
    ]
    proposal_schema = schema["properties"]["semantic_issue_proposal"]
    assert proposal_schema["type"] == "object"
    assert "prepared packet required_submit_shape" in proposal_schema["description"]
    assert "Python validates and projects" in proposal_schema["description"]
    assert "properties" not in proposal_schema
    assert tool["annotations"]["readOnlyHint"] is False
    assert tool["annotations"]["idempotentHint"] is False


def test_tools_list_internal_mode_keeps_output_schema() -> None:
    transport = _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL)

    response = transport.handle_message(_request("tools/list"))

    assert response is not None
    tools = response["result"]["tools"]
    assert tools
    for tool in tools:
        assert "outputSchema" in tool


def test_desktop_mode_rejects_low_level_validation_tools() -> None:
    response = _call_tool(
        _initialized_transport(),
        claude_desktop_tool_alias(TOOL_VALIDATE_HANDOFF_REQUEST),
        {"request": _handoff_request().to_json_dict()},
    )

    assert response is not None
    assert response["error"]["code"] == -32602


def test_unknown_desktop_alias_conversion_fails_closed() -> None:
    with pytest.raises(ValueError, match="Unknown Claude Desktop tool alias"):
        canonical_tool_name_from_claude_desktop_alias("unknown_alias")


def test_desktop_rejects_canonical_but_internal_accepts_it() -> None:
    desktop = _initialized_transport()
    internal = _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL)

    desktop_response = _call_tool(desktop, TOOL_GET_POLICY_SUMMARY)
    internal_response = _call_tool(internal, TOOL_GET_POLICY_SUMMARY)

    assert desktop_response is not None
    assert desktop_response["error"]["code"] == -32602
    assert internal_response is not None
    assert internal_response["result"]["isError"] is False
    assert internal_response["result"]["structuredContent"]["result_kind"] == (
        "policy_summary"
    )


def test_policy_summary_lists_canonical_approved_summary_article_types() -> None:
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_GET_POLICY_SUMMARY,
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    article_type_check = next(
        check
        for check in structured["checks"]
        if check["kind"] == "approved_summary_article_types"
    )
    assert article_type_check["canonical_values"] == [
        ArticleType.TECHNICAL_SCR.value,
        ArticleType.HOWTO_QA.value,
    ]
    assert "accepted_alias_examples" not in article_type_check


def test_unknown_notifications_do_not_echo_params_or_write_response() -> None:
    response = _initialized_transport().handle_message(
        {
            "jsonrpc": "2.0",
            "method": "notifications/unknown",
            "params": {"token": "SECRET"},
        }
    )

    assert response is None


def test_tools_call_notification_does_not_execute_tool() -> None:
    response = _initialized_transport().handle_message(
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "arguments": {},
                "name": claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
            },
        }
    )

    assert response is None


def test_validate_handoff_request_returns_compact_safe_summary() -> None:
    transport = _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL)

    response = _call_tool(
        transport,
        TOOL_VALIDATE_HANDOFF_REQUEST,
        {"request": _handoff_request().to_json_dict()},
    )

    assert response is not None
    result = response["result"]
    assert result["isError"] is False
    structured = result["structuredContent"]
    assert structured["result_kind"] == "handoff_request_validation"
    assert structured["validation_ok"] is True
    assert structured["auto_publish_allowed"] is False
    assert "safe_context" not in json.dumps(structured)


def test_validate_handoff_response_rejects_private_value_without_echo() -> None:
    transport = _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL)
    request = _handoff_request()
    response_payload = _handoff_response(
        request,
        reviewer_assist_notes=["Contact person@example.com."],
    )

    response = _call_tool(
        transport,
        TOOL_VALIDATE_HANDOFF_RESPONSE,
        {"request": request.to_json_dict(), "response": response_payload},
    )

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    assert response["result"]["isError"] is True
    assert response["result"]["structuredContent"]["error_code"] == "validation_failed"
    assert "person@example.com" not in result_text


def test_validate_draft_response_returns_no_html_body() -> None:
    transport = _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL)
    request = _draft_request()

    response = _call_tool(
        transport,
        TOOL_VALIDATE_DRAFT_RESPONSE,
        {"request": request.to_json_dict(), "response": _draft_response()},
    )

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    assert response["result"]["isError"] is False
    assert response["result"]["structuredContent"]["result_kind"] == (
        "draft_response_validation"
    )
    assert "zendesk_source_html" not in result_text
    assert "<h1>" not in result_text


@pytest.mark.parametrize(
    "patch",
    [
        {"auto_publish_allowed": True},
        {"public_output_approved": True},
        {"unsupported_claims_present": True},
    ],
)
def test_validate_draft_response_rejects_publish_or_invalid_provider_output(
    patch: dict[str, object],
) -> None:
    transport = _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL)
    request = _draft_request()

    response = _call_tool(
        transport,
        TOOL_VALIDATE_DRAFT_RESPONSE,
        {"request": request.to_json_dict(), "response": _draft_response(**patch)},
    )

    assert response is not None
    assert response["result"]["isError"] is True
    assert response["result"]["structuredContent"]["error_code"] == "validation_failed"


def test_run_approved_summary_pipeline_returns_compact_ready_status() -> None:
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
        _approved_summary_args(debug=True),
    )

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    assert response["result"]["isError"] is False
    structured = response["result"]["structuredContent"]
    _assert_approved_summary_pipeline_compact_ready(structured, result_text)


def test_run_approved_summary_pipeline_bounds_long_title_for_handoff() -> None:
    long_title = "A" * 161
    arguments = _approved_summary_args(item={"title": long_title})
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
        arguments,
    )
    execution = desktop_authoring_pipeline.execute_pipeline(arguments)

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["pipeline_ok"] is True
    assert structured["debug_code"] == "none"
    assert execution.handoff_request.safe_context["title_hint"] == "A" * 160
    assert execution.arguments["item"]["title"] == long_title


def _assert_approved_summary_pipeline_compact_ready(
    structured: Mapping[str, Any],
    result_text: str,
) -> None:
    expected_fields = {
        "result_kind": "approved_summary_pipeline",
        "pipeline_ok": True,
        "failure_stage": "none",
        "debug_code": "none",
        "input_safety_ok": True,
        "evidence_valid": True,
        "ready_for_reviewer": True,
        "draft_request_ready": True,
        "original_recommended_action": "create_candidate",
        "original_article_type": "technical_scr",
        "auto_publish_allowed": False,
        "public_output_approved": False,
        "provider_calls": False,
        "writes_files": False,
    }
    for field, expected_value in expected_fields.items():
        assert structured[field] == expected_value
    _assert_text_excludes(
        result_text,
        ("zendesk_source_html", "evidence_basis", "<h1>"),
    )


def test_run_approved_summary_pipeline_rejects_break_fix_article_type_alias() -> None:
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
        _approved_summary_args(item={"article_type": "break-fix"}, debug=True),
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "input_validation"
    assert structured["debug_code"] == "approved_summary_article_type_invalid"


def test_author_approved_summary_returns_reviewer_only_draft() -> None:
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_AUTHOR_APPROVED_SUMMARY,
        _approved_summary_args(
            article_type=ArticleType.TECHNICAL_SCR.value,
            reference_article_text=(
                "Applicable to\nPlesk for Linux\nSymptoms\nGraphs show no data\n"
                "Cause\nA required package is missing\nResolution\nInstall it"
            ),
        ),
    )

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    assert response["result"]["isError"] is False
    structured = response["result"]["structuredContent"]
    _assert_approved_summary_authoring_success(structured)
    assert (
        structured["atomic_item"]["title"]
        == "Monitoring graphs show no data in Plesk"
    )
    draft = structured["reviewer_only_draft"]
    assert structured["draft_sections"] == draft
    assert structured["reviewer_only_preview"] == draft
    preview_text = structured["reviewer_only_preview_text"]
    _assert_monitoring_reviewer_only_preview_text(preview_text)
    _assert_monitoring_reviewer_only_draft(draft)
    assert {"kind": "reference_section_coverage_ok", "severity": "info"} in (
        structured["quality_gaps"]
    )
    result_output = response["result"]["content"][0]["text"]
    html = structured["reviewer_only_html"]
    _assert_reviewer_only_result_output(result_output, html, preview_text)
    _assert_monitoring_reviewer_only_html(html)
    _assert_text_excludes(
        result_text,
        ("zendesk_source_html", "evidence_basis", "reviewer_packet"),
    )


def _assert_approved_summary_authoring_success(
    structured: Mapping[str, Any],
) -> None:
    assert structured["result_kind"] == "approved_summary_authoring"
    assert structured["pipeline_ok"] is True
    assert structured["should_be_kcs_article"] is True
    assert structured["article_type"] == ArticleType.TECHNICAL_SCR.value
    assert structured["recommended_action"] == RecommendedAction.CREATE_CANDIDATE.value
    assert structured["ready_for_reviewer"] is True
    assert structured["draft_request_ready"] is True
    assert structured["auto_publish_allowed"] is False
    assert structured["public_output_approved"] is False
    assert structured["provider_calls"] is False
    assert structured["writes_files"] is False


def _assert_monitoring_reviewer_only_preview_text(preview_text: str) -> None:
    assert preview_text.startswith("Title: Monitoring graphs show no data in Plesk")
    _assert_text_includes(
        preview_text,
        (
            "Applicable to:\n- Plesk for Linux",
            "Symptoms:\n1. Product monitoring graphs show no data.",
            "Cause:\nA required product-side package is missing.",
        ),
    )


def _assert_monitoring_reviewer_only_draft(draft: Mapping[str, Any]) -> None:
    assert draft["status"] == "reviewer_only"
    assert draft["title"] == "Monitoring graphs show no data in Plesk"
    assert draft["symptoms"] == ["Product monitoring graphs show no data."]
    assert draft["cause"] == "A required product-side package is missing."
    assert (
        draft["resolution"]
        == "Install the missing package and restart the related service."
    )


def _assert_reviewer_only_result_output(
    result_output: str,
    html: str,
    preview_text: str,
) -> None:
    assert result_output.startswith("```html\n")
    assert "```html\n" in result_output
    _assert_text_excludes(
        result_output,
        (
            "COPY THE FINAL RESPONSE BELOW VERBATIM",
            "Do not rewrite it into a Markdown article",
            "do not add follow-up wording",
            "Reviewer-only Zendesk HTML draft generated",
            "COPY THE FENCED HTML BLOCK",
            "Reviewer preview:",
            preview_text,
        ),
    )
    assert "\n```\n\n```json\n" in result_output
    assert html in result_output


def _assert_monitoring_reviewer_only_html(html: str) -> None:
    _assert_text_includes(
        html,
        (
            "<h1>Monitoring graphs show no data in Plesk</h1>",
            "<h2>Applicable to</h2>",
            "<h2>Symptoms</h2>",
            "<h2>Cause</h2>",
            "<h2>Resolution</h2>",
        ),
    )


def test_author_approved_summary_returns_cli_entry_point_in_html() -> None:
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_AUTHOR_APPROVED_SUMMARY,
        _approved_summary_args(
            item={
                "resolution_steps": [
                    "Run rpm -qf /etc/sw-collectd/conf.d/custom.conf.",
                    "Run systemctl restart sw-collectd.",
                ],
                "supported_cause": (
                    "A custom collectd configuration overrides the data path."
                ),
                "supported_resolution_or_workaround": (
                    "Disable the custom collectd configuration and restart "
                    "sw-collectd."
                ),
            },
        ),
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    draft = structured["reviewer_only_draft"]
    assert draft["resolution_steps"][0] == "Connect to the Plesk server via SSH."
    assert (
        '<li><a href="https://support.plesk.com/hc/en-us/articles/'
        '12377512781975-How-to-connect-to-a-Plesk-server-via-SSH">'
        "Connect to the Plesk server via SSH.</a></li>"
        in structured["reviewer_only_html"]
    )


def test_author_approved_summary_normalizes_plesk_applicable_to() -> None:
    arguments = _approved_summary_args()
    assert isinstance(arguments["item"], dict)
    arguments["item"].pop("applicable_to")
    arguments["item"]["environment"] = (
        "Plesk with Advanced Monitoring extension, "
        "Grafana with plesk-json-backend-datasource plugin, "
        "sw-collectd for metrics collection, RPM-based"
    )

    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_AUTHOR_APPROVED_SUMMARY,
        arguments,
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    html = structured["reviewer_only_html"]
    draft = structured["reviewer_only_draft"]
    assert draft["applicable_to"] == ["Plesk for Linux"]
    assert (
        "<h2>Applicable to</h2>\n"
        "<ul>\n"
        "  <li>Plesk for Linux</li>\n"
        "</ul>"
    ) in html
    assert (
        '<li><a href="https://support.plesk.com/hc/en-us/articles/'
        '12377512781975-How-to-connect-to-a-Plesk-server-via-SSH">'
        "Connect to the Plesk server via SSH.</a></li>"
        in html
    )


def test_author_approved_summary_accepts_json_string_applicable_to() -> None:
    arguments = _approved_summary_args()
    assert isinstance(arguments["item"], dict)
    arguments["item"]["applicable_to"] = (
        '["Plesk with Advanced Monitoring extension", '
        '"Grafana with plesk-json-backend-datasource plugin", '
        '"sw-collectd for metrics collection", "RPM-based"]'
    )
    arguments["item"]["environment"] = (
        '["Plesk with Advanced Monitoring extension", '
        '"Grafana with plesk-json-backend-datasource plugin", '
        '"sw-collectd for metrics collection", "RPM-based"]'
    )

    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_AUTHOR_APPROVED_SUMMARY,
        arguments,
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    html = structured["reviewer_only_html"]
    assert "<li>Plesk for Linux</li>" in html
    assert "[&quot;" not in html
    assert "&quot;" not in html
    assert (
        '12377512781975-How-to-connect-to-a-Plesk-server-via-SSH">'
        "Connect to the Plesk server via SSH.</a></li>"
        in html
    )


def test_author_approved_summary_skips_missing_reuse_search_for_mvp_draft() -> None:
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_AUTHOR_APPROVED_SUMMARY,
        _approved_summary_args(
            debug=True,
            reuse_search_checked=False,
            reuse_search_run_ref="",
        ),
    )

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    assert response["result"]["isError"] is False
    structured = response["result"]["structuredContent"]
    assert structured["result_kind"] == "approved_summary_authoring"
    assert structured["pipeline_ok"] is True
    assert structured["failure_stage"] == "none"
    assert structured["debug_code"] == "none"
    assert structured["reuse_search_status"] == "skipped"
    assert structured["should_be_kcs_article"] is True
    assert "reviewer_only_html" in structured
    assert {"kind": "reuse_search_skipped", "severity": "warning"} in structured[
        "quality_gaps"
    ]
    assert "possible_duplicate_not_checked" not in result_text


def test_author_approved_summary_accepts_fixed_false_policy_flags() -> None:
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_AUTHOR_APPROVED_SUMMARY,
        _approved_summary_args(
            auto_publish_allowed=False,
            customer_replies=False,
            network_calls=False,
            provider_calls=False,
            public_output_approved=False,
            publishes=False,
            ready_for_real_ticket_use=False,
            writes_files=False,
        ),
    )

    assert response is not None
    assert response["result"]["isError"] is False
    structured = response["result"]["structuredContent"]
    assert structured["result_kind"] == "approved_summary_authoring"
    assert structured["pipeline_ok"] is True
    assert structured["auto_publish_allowed"] is False
    assert structured["public_output_approved"] is False
    assert structured["provider_calls"] is False
    assert structured["writes_files"] is False


def test_author_approved_summary_rejects_true_policy_flag() -> None:
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_AUTHOR_APPROVED_SUMMARY,
        _approved_summary_args(auto_publish_allowed=True),
    )

    assert response is not None
    assert response["result"]["isError"] is False
    structured = response["result"]["structuredContent"]
    assert structured["result_kind"] == "approved_summary_authoring"
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "input_validation"
    assert structured["debug_code"] == "approved_summary_policy_flag_invalid"


def test_author_ticket_loads_local_approved_summary(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    _write_approved_ticket_summary(tmp_path)

    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_AUTHOR_TICKET,
        {"ticket_ref": "ticket-001", "debug": True},
    )

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    assert response["result"]["isError"] is False
    structured = response["result"]["structuredContent"]
    assert structured["result_kind"] == "approved_ticket_authoring"
    assert structured["ticket_ref"] == "ticket-001"
    assert structured["approved_summary_source"] == "local_approved_summary"
    assert structured["pipeline_ok"] is True
    assert structured["ready_for_reviewer"] is True
    assert structured["draft_request_ready"] is True
    assert structured["recommended_action"] == RecommendedAction.CREATE_CANDIDATE.value
    assert "<h1>Monitoring graphs show no data in Plesk</h1>" in structured[
        "reviewer_only_html"
    ]
    assert str(tmp_path) not in result_text
    assert "zendesk_source_html" not in result_text
    assert "evidence_basis" not in result_text


def test_author_ticket_resolves_existing_bare_numeric_alias(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    canonical_ref = "ticket-123456"
    _write_approved_ticket_summary(tmp_path, ticket_ref=canonical_ref)

    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_AUTHOR_TICKET,
        {"ticket_ref": "123456", "debug": True},
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["result_kind"] == "approved_ticket_authoring"
    assert structured["ticket_ref"] == canonical_ref
    assert structured["pipeline_ok"] is True


def test_author_ticket_missing_summary_file_is_controlled_failure(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))

    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_AUTHOR_TICKET,
        {"ticket_ref": "ticket-001", "debug": True},
    )

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    assert response["result"]["isError"] is False
    structured = response["result"]["structuredContent"]
    assert structured["result_kind"] == "approved_ticket_authoring"
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "input_validation"
    assert structured["debug_code"] == "approved_ticket_summary_not_found"
    assert str(tmp_path) not in result_text


def test_author_ticket_rejects_unsafe_ref_without_echo() -> None:
    unsafe_ref = "../private-token"

    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_AUTHOR_TICKET,
        {"ticket_ref": unsafe_ref, "debug": True},
    )

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    assert response["result"]["isError"] is False
    structured = response["result"]["structuredContent"]
    assert structured["result_kind"] == "approved_ticket_authoring"
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "input_validation"
    assert structured["debug_code"] == "approved_ticket_ref_invalid"
    assert unsafe_ref not in result_text


def test_draft_article_uses_ticket_ref_path(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    _write_approved_ticket_summary(tmp_path)
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles"
        )
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"ticket_ref": "ticket-001", "debug": True},
    )

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["draft_generated"] is True
    assert structured["ticket_ref"] == "ticket-001"
    assert structured["approved_summary_source"] == "local_approved_summary"
    assert structured["reviewer_bundle_written"] is True
    assert "reviewer_only_html" not in structured
    assert structured["html_path"].endswith("/reviewer_only.html")
    assert str(tmp_path) not in result_text


def test_draft_ticket_uses_same_ticket_ref_path(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    _write_approved_ticket_summary(tmp_path)
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles"
        )
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_TICKET),
        {"ticket_ref": "ticket-001"},
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["draft_generated"] is True
    assert structured["ticket_ref"] == "ticket-001"
    assert structured["reviewer_bundle_written"] is True
    assert "reviewer_only_html" not in structured


def test_draft_ticket_rejects_non_ref_arguments() -> None:
    response = _call_tool(
        _initialized_transport(),
        claude_desktop_tool_alias(TOOL_DRAFT_TICKET),
        {"ticket_ref": "ticket-001", "item": {"title": "bad"}},
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "input_validation"
    assert structured["debug_code"] == "draft_article_args_invalid"


def test_draft_article_uses_clean_ticket_ref_file(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    _write_clean_ticket_text(
        tmp_path,
        _raw_monitoring_ticket_summary(),
        ticket_ref="monitoring-001",
    )
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles"
        )
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"ticket_ref": "monitoring-001", "debug": True},
    )

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["draft_generated"] is True
    assert structured["pipeline_ok"] is False
    assert structured["recommended_action"] == "draft_only"
    assert structured["debug_code"] == "draft_only_reuse_search_missing"
    assert structured["ticket_ref"] == "monitoring-001"
    assert structured["approved_summary_source"] == "local_clean_ticket"
    assert structured["article_type"] == ArticleType.TECHNICAL_SCR.value
    assert structured["reviewer_bundle_written"] is True
    assert "reviewer_only_html" not in structured
    html_path = tmp_path / structured["html_path"]
    assert "Connect to the Plesk server via SSH" in html_path.read_text(
        encoding="utf-8"
    )
    assert str(tmp_path) not in result_text


def test_draft_article_blocks_ambiguous_long_clean_ticket_ref(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    noisy_transcript = "\n".join(
        [
            "Avatar",
            "{{PERSON_NAME_002}}",
            "To: Client",
            "Show more",
            "I am logged in and checking the issue.",
            "Internal",
            "[{{SHELL_USERHOST_001}} ~]# ps aux",
            "many sw-engine-fpm workers are running",
            "I found that the panel was receiving many external requests.",
            "I created and tested a dedicated Fail2Ban rule for this traffic:",
            "fail2ban-regex /var/log/plesk/httpsd_access_log "
            "/etc/fail2ban/filter.d/plesk-panel-flood.conf",
            "systemctl reload fail2ban",
            "systemctl restart sw-engine sw-cp-server",
            "Later the customer asked about SSH connectivity and blocked IPs.",
            "As per the SSH access, Plesk does not manage it.",
        ]
        * 55
    )
    _write_clean_ticket_text(
        tmp_path,
        "# Customer Ticket Content\n\n"
        "I think my server is on attack, I blocked some IP but I think I have "
        f"another thing.\n{noisy_transcript}\n",
        ticket_ref="ticket-ambiguous",
    )
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles"
        )
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"ticket_ref": "ticket-ambiguous", "debug": True},
    )

    assert response is not None
    response_text = json.dumps(response, sort_keys=True)
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["pipeline_ok"] is False
    assert structured["debug_code"] == "clean_ticket_metadata_missing"
    assert structured["workflow_state"] == "semantic_review_metadata_blocked"
    assert structured["next_required_action"] == "repair_clean_ticket_metadata"
    assert structured["ticket_ref"] == "ticket-ambiguous"
    assert structured["manual_draft_allowed"] is False
    assert structured["draft_generated"] is False
    assert structured["reviewer_bundle_written"] is False
    assert "reviewer_only_html" not in structured
    assert "Do not draft manually" in response_text


def test_draft_article_registered_ambiguous_ticket_requires_semantic_review(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    noisy_transcript = "\n".join(
        [
            "Customer Ticket Content",
            "The customer reports that a product task fails intermittently.",
            "The investigation mentions one possible cause, then another.",
            "A final resolution is likely present but scattered across notes.",
            "Support restarted one service and later discussed a different issue.",
        ]
        * 45
    )
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles"
        )
    )
    register_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_REGISTER_CLEAN_TICKET),
        {
            "clean_ticket_text": noisy_transcript,
            "ticket_ref": "ticket-ambiguous",
        },
    )
    assert register_response is not None

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"ticket_ref": "ticket-ambiguous", "debug": True},
    )

    assert response is not None
    response_text = json.dumps(response, sort_keys=True)
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    _assert_ambiguous_ticket_semantic_review_required(structured, response_text)


def _assert_ambiguous_ticket_semantic_review_required(
    structured: Mapping[str, Any],
    response_text: str,
) -> None:
    expected_fields = {
        "pipeline_ok": False,
        "recommended_action": "blocked",
        "workflow_state": "semantic_review_required",
        "debug_code": "semantic_identification_low_confidence",
        "failure_stage": "semantic_extraction",
        "next_tool": "kcs_prepare_semantic_review",
        "draft_generated": False,
        "reviewer_bundle_written": False,
        "manual_draft_allowed": False,
        "ticket_ref": "ticket-ambiguous",
    }
    for field, expected_value in expected_fields.items():
        assert structured[field] == expected_value
    assert structured["next_arguments"] == {
        "semantic_review_ref": structured["semantic_review_ref"]
    }
    assert structured["excerpt_count"] > 0
    from kcs_adapters.desktop_semantic_review import (
        SEMANTIC_REVIEW_MAX_TOTAL_BYTES,
    )

    assert structured["excerpt_total_bytes"] <= SEMANTIC_REVIEW_MAX_TOTAL_BYTES
    assert isinstance(structured["semantic_review_packet_sha256"], str)
    assert "reviewer_only_html" not in structured
    assert "Do not draft manually" in response_text


def test_prepare_semantic_review_returns_bounded_selected_excerpts(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    noisy_transcript = _ambiguous_semantic_review_ticket_text()
    draft, prepare_response = _prepared_semantic_review_response(
        tmp_path,
        noisy_transcript,
    )

    assert prepare_response is not None
    packet_text = json.dumps(prepare_response, sort_keys=True)
    packet = prepare_response["result"]["structuredContent"]
    _assert_semantic_review_packet_header(packet, draft)
    _assert_semantic_review_packet_bounds(packet)
    _assert_semantic_review_required_submit_shape(packet, draft)
    _assert_semantic_review_candidate_field_metadata(packet)
    result_text = prepare_response["result"]["content"][0]["text"]
    _assert_semantic_review_prompt_text(result_text)
    _assert_semantic_review_packet_safety(packet, packet_text, result_text)


def _ambiguous_semantic_review_ticket_text() -> str:
    filler = "\n".join(
        f"Filler diagnostic note {index} DO-NOT-RETURN-FULL-TICKET-SENTINEL"
        for index in range(80)
    )
    return "\n\n".join(
        [
            "Customer Ticket Content",
            "Customer reports that a safe product task fails with an error.",
            filler,
            "The investigation mentions one possible cause, then another.",
            (
                "Support restarted one service and later discussed a different "
                "issue, so semantic item identification needs review."
            ),
        ]
    )


def _prepared_semantic_review_response(
    tmp_path: Path,
    clean_ticket_text: str,
) -> tuple[Mapping[str, Any], Mapping[str, Any] | None]:
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles"
        )
    )
    _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_REGISTER_CLEAN_TICKET),
        {
            "clean_ticket_text": clean_ticket_text,
            "ticket_ref": "ticket-semantic-review",
        },
    )
    draft_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"ticket_ref": "ticket-semantic-review", "debug": True},
    )
    assert draft_response is not None
    draft = draft_response["result"]["structuredContent"]
    return draft, _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_PREPARE_SEMANTIC_REVIEW),
        {"semantic_review_ref": draft["semantic_review_ref"]},
    )


def _assert_semantic_review_packet_header(
    packet: Mapping[str, Any],
    draft: Mapping[str, Any],
) -> None:
    assert packet["result_kind"] == "semantic_review_packet"
    assert packet["schema_version"] == "kcs_semantic_review_packet_v1"
    assert packet["semantic_review_ref"] == draft["semantic_review_ref"]
    assert packet["submit_tool"] == "kcs_submit_semantic_review"
    assert packet["submit_arguments"] == {
        "semantic_review_ref": draft["semantic_review_ref"]
    }


def _assert_semantic_review_packet_bounds(packet: Mapping[str, Any]) -> None:
    from kcs_adapters.desktop_semantic_review import (
        SEMANTIC_REVIEW_MAX_EXCERPTS,
        SEMANTIC_REVIEW_MAX_TOTAL_BYTES,
    )

    assert 0 < packet["excerpt_count"] <= SEMANTIC_REVIEW_MAX_EXCERPTS
    assert packet["excerpt_total_bytes"] <= SEMANTIC_REVIEW_MAX_TOTAL_BYTES
    assert packet["selected_excerpts"]
    assert packet["allowed_source_refs"] == [
        excerpt["source_ref"] for excerpt in packet["selected_excerpts"]
    ]


def _assert_semantic_review_required_submit_shape(
    packet: Mapping[str, Any],
    draft: Mapping[str, Any],
) -> None:
    required_shape = packet["required_submit_shape"]
    assert set(required_shape) == {
        "semantic_issue_proposal",
        "semantic_review_ref",
    }
    assert required_shape["semantic_review_ref"] == draft["semantic_review_ref"]
    proposal_shape = required_shape["semantic_issue_proposal"]
    assert proposal_shape["case_ref"] == draft["semantic_review_ref"]
    assert proposal_shape["schema_version"] == "semantic_issue_proposal_v1"
    assert proposal_shape["issues"] == []
    assert proposal_shape["coverage_records"] == []


def _assert_semantic_review_candidate_field_metadata(
    packet: Mapping[str, Any],
) -> None:
    assert set(packet["proposal_field_contracts"]) == {"reason_code"}
    assert packet["proposal_shape_contracts"]["observation"] == {
        "source_refs": "non_empty_allowed_source_ref_list",
        "text": "exact_text_from_one_referenced_selected_excerpt_except_summary",
    }
    assert packet["issue_boundary_contract"]["issue_unit"] == (
        "coherent_separately_searchable_problem_or_question"
    )
    for retired_field in (
        "active_output_schema",
        "allowed_output_schema",
        "candidate_field_contracts",
        "runtime_default",
        "shadow_mode",
    ):
        assert retired_field not in packet


def _assert_semantic_review_prompt_text(result_text: str) -> None:
    _assert_text_includes(
        result_text,
        (
            "Call kcs_submit_semantic_review with this argument shape",
            "observation-only issue boundaries",
            "Do not choose an operator action",
            "Cover every allowed_source_ref",
            "Do not draft an article",
            "semantic_issue_proposal",
        ),
    )


def _assert_semantic_review_packet_safety(
    packet: Mapping[str, Any],
    packet_text: str,
    result_text: str,
) -> None:
    assert "Do not draft an article" in packet_text
    assert '"candidates"' not in json.dumps(packet["required_submit_shape"])
    assert "DO-NOT-RETURN-FULL-TICKET-SENTINEL" not in packet_text


def test_prepare_semantic_review_allows_public_support_email(
) -> None:
    from kcs_adapters.desktop_semantic_review import semantic_review_packet

    excerpts = [
        {
            "role": "reported_symptom",
            "source_ref": "excerpt-001",
            "text": (
                "Customer Success team (cs@plesk.com) is responsible for "
                "licensing questions, including my.plesk.com issues."
            ),
        }
    ]
    packet = semantic_review_packet(
        excerpts=excerpts,
        semantic_review_ref="semantic-review-public-contact",
    )

    assert packet["result_kind"] == "semantic_review_packet"
    assert packet["selected_excerpts"]
    assert any(
        "cs@plesk.com" in excerpt["text"]
        for excerpt in packet["selected_excerpts"]
    )


def test_prepare_semantic_review_advertises_observation_shape(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    draft, prepare_response = _prepared_semantic_review_response(
        tmp_path,
        _ambiguous_semantic_review_ticket_text(),
    )

    assert prepare_response is not None
    packet = prepare_response["result"]["structuredContent"]
    proposal_shape = packet["required_submit_shape"]["semantic_issue_proposal"]
    assert proposal_shape == {
        "case_ref": draft["semantic_review_ref"],
        "coverage_records": [],
        "extraction_source_ref": "semantic-proposal-submit-001",
        "issues": [],
        "schema_version": SEMANTIC_ISSUE_PROPOSAL_SCHEMA_VERSION,
        "source_refs": packet["allowed_source_refs"],
    }
    assert packet["proposal_shape_contracts"]["observation"] == {
        "source_refs": "non_empty_allowed_source_ref_list",
        "text": "exact_text_from_one_referenced_selected_excerpt_except_summary",
    }


def test_prepare_semantic_review_omits_numeric_ticket_ref_from_packet(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles"
        )
    )
    _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_REGISTER_CLEAN_TICKET),
        {
            "clean_ticket_text": (
                "Customer Ticket Content\n"
                "Customer reports that a product task fails with an error.\n"
                "The investigation mentions one possible cause, then another.\n"
                "Support restarted one service and later discussed another issue."
            ),
            "ticket_ref": "ticket-example-real-tone",
        },
    )
    draft_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"ticket_ref": "ticket-example-real-tone", "debug": True},
    )
    assert draft_response is not None
    draft = draft_response["result"]["structuredContent"]
    assert draft["workflow_state"] == "semantic_review_required"
    assert draft["ticket_ref"] == "ticket-example-real-tone"

    prepare_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_PREPARE_SEMANTIC_REVIEW),
        {"semantic_review_ref": draft["semantic_review_ref"]},
    )

    assert prepare_response is not None
    packet = prepare_response["result"]["structuredContent"]
    packet_text = json.dumps(packet, sort_keys=True)
    assert packet["case_ref"] == draft["semantic_review_ref"]
    assert "ticket_ref" not in packet
    assert "ticket-example-real-tone" not in packet_text


def test_prepare_semantic_review_is_one_shot(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles"
        )
    )
    _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_REGISTER_CLEAN_TICKET),
        {
            "clean_ticket_text": (
                "Customer Ticket Content\n"
                "Customer reports that a product task fails with an error.\n"
                "The investigation mentions one possible cause, then another.\n"
                "Support restarted one service and later discussed another issue."
            ),
            "ticket_ref": "ticket-semantic-review",
        },
    )
    draft_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"ticket_ref": "ticket-semantic-review", "debug": True},
    )
    assert draft_response is not None
    semantic_review_ref = draft_response["result"]["structuredContent"][
        "semantic_review_ref"
    ]

    first_prepare = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_PREPARE_SEMANTIC_REVIEW),
        {"semantic_review_ref": semantic_review_ref},
    )
    second_prepare = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_PREPARE_SEMANTIC_REVIEW),
        {"semantic_review_ref": semantic_review_ref},
    )

    assert first_prepare is not None
    assert first_prepare["result"]["structuredContent"]["result_kind"] == (
        "semantic_review_packet"
    )
    assert second_prepare is not None
    structured = second_prepare["result"]["structuredContent"]
    assert structured["workflow_state"] == "semantic_review_prepare_blocked"
    assert structured["debug_code"] == "semantic_review_unavailable"
    assert structured["manual_draft_allowed"] is False


def test_new_draft_call_clears_pending_semantic_review(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles"
        )
    )
    _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_REGISTER_CLEAN_TICKET),
        {
            "clean_ticket_text": (
                "Customer Ticket Content\n"
                "Customer reports that a product task fails with an error.\n"
                "The investigation mentions one possible cause, then another.\n"
                "Support restarted one service and later discussed another issue."
            ),
            "ticket_ref": "ticket-semantic-review-a",
        },
    )
    _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_REGISTER_CLEAN_TICKET),
        {
            "clean_ticket_text": (
                "Customer Ticket Content\n"
                "Customer reports that a different product task fails.\n"
                "The investigation mentions one possible cause, then another.\n"
                "Support restarted one service and later discussed another issue."
            ),
            "ticket_ref": "ticket-semantic-review-b",
        },
    )
    first_draft = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"ticket_ref": "ticket-semantic-review-a", "debug": True},
    )
    assert first_draft is not None
    old_ref = first_draft["result"]["structuredContent"]["semantic_review_ref"]

    second_draft = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"ticket_ref": "ticket-semantic-review-b", "debug": True},
    )
    assert second_draft is not None

    prepare_old = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_PREPARE_SEMANTIC_REVIEW),
        {"semantic_review_ref": old_ref},
    )

    assert prepare_old is not None
    structured = prepare_old["result"]["structuredContent"]
    assert structured["workflow_state"] == "semantic_review_prepare_blocked"
    assert structured["debug_code"] == "semantic_review_invalid"
    assert structured["manual_draft_allowed"] is False


def test_register_clean_ticket_clears_pending_semantic_review(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles"
        )
    )
    _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_REGISTER_CLEAN_TICKET),
        {
            "clean_ticket_text": (
                "Customer Ticket Content\n"
                "Customer reports that a product task fails with an error.\n"
                "The investigation mentions one possible cause, then another.\n"
                "Support restarted one service and later discussed another issue."
            ),
            "ticket_ref": "ticket-semantic-review-a",
        },
    )
    first_draft = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"ticket_ref": "ticket-semantic-review-a", "debug": True},
    )
    assert first_draft is not None
    old_ref = first_draft["result"]["structuredContent"]["semantic_review_ref"]

    _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_REGISTER_CLEAN_TICKET),
        {
            "clean_ticket_text": (
                "Customer Ticket Content\n"
                "Customer reports that a different product task fails.\n"
                "The investigation mentions one possible cause, then another.\n"
                "Support restarted one service and later discussed another issue."
            ),
            "ticket_ref": "ticket-semantic-review-b",
        },
    )
    prepare_old = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_PREPARE_SEMANTIC_REVIEW),
        {"semantic_review_ref": old_ref},
    )

    assert prepare_old is not None
    structured = prepare_old["result"]["structuredContent"]
    assert structured["workflow_state"] == "semantic_review_prepare_blocked"
    assert structured["debug_code"] == "semantic_review_unavailable"
    assert structured["manual_draft_allowed"] is False


def test_semantic_review_excerpts_use_utf8_byte_caps() -> None:
    from kcs_adapters.desktop_semantic_review import (
        SEMANTIC_REVIEW_MAX_EXCERPT_BYTES,
        SEMANTIC_REVIEW_MAX_TOTAL_BYTES,
        selected_semantic_review_excerpts,
    )

    excerpts = selected_semantic_review_excerpts(
        "Customer reports product issue. "
        + ("Ж" * 20_000)
        + "\n\nSupport restarted a service and the issue was resolved."
    )

    assert excerpts
    assert all(
        len(str(excerpt["text"]).encode("utf-8"))
        <= SEMANTIC_REVIEW_MAX_EXCERPT_BYTES
        for excerpt in excerpts
    )
    assert (
        sum(len(str(excerpt["text"]).encode("utf-8")) for excerpt in excerpts)
        <= SEMANTIC_REVIEW_MAX_TOTAL_BYTES
    )


def _semantic_review_text_with_middle_resolution_reference(
    url: str,
    *,
    reference_index: int = 2,
) -> str:
    segments: list[str] = []
    for index in range(5):
        segments.extend(
            [
                (
                    "Customer-reported symptom:\n"
                    f"Synthetic operation {index} fails with a reported error."
                ),
                (
                    "Confirmed cause:\n"
                    f"Support confirmed root cause {index} because a setting is wrong."
                ),
            ]
        )
        if index == reference_index:
            segments.append(
                "Supported resolution:\n"
                f"Followed the existing public support article {url} and "
                "resolved the issue."
            )
        else:
            segments.append(
                "Supported resolution:\n"
                f"Resolution {index} fixed the issue with a supported workaround; "
                "the solution was verified and the operation was resolved."
            )
    return "\n\n".join(segments)


def test_semantic_review_excerpts_preserve_public_resolution_reference() -> None:
    from kcs_adapters.desktop_semantic_review import (
        SEMANTIC_REVIEW_MAX_RANKED_EXCERPTS,
        selected_semantic_review_excerpts,
    )

    public_url = (
        "https://support.plesk.com/hc/en-us/articles/123456789"
    )
    excerpts = selected_semantic_review_excerpts(
        _semantic_review_text_with_middle_resolution_reference(public_url)
    )

    assert len(excerpts) == SEMANTIC_REVIEW_MAX_RANKED_EXCERPTS
    assert any(public_url in str(excerpt["text"]) for excerpt in excerpts)
    assert all(
        excerpt["source_ref"] == f"excerpt-{index:03d}"
        for index, excerpt in enumerate(excerpts, start=1)
    )


def test_semantic_review_excerpts_reserve_late_public_resolution_reference() -> None:
    from kcs_adapters.desktop_semantic_review import (
        SEMANTIC_REVIEW_MAX_RANKED_EXCERPTS,
        selected_semantic_review_excerpts,
    )

    public_url = "https://support.plesk.com/hc/en-us/articles/123456789"
    excerpts = selected_semantic_review_excerpts(
        _semantic_review_text_with_middle_resolution_reference(
            public_url,
            reference_index=4,
        )
    )

    assert len(excerpts) == SEMANTIC_REVIEW_MAX_RANKED_EXCERPTS
    assert any(public_url in str(excerpt["text"]) for excerpt in excerpts)


def test_semantic_review_excerpts_do_not_reserve_unapproved_reference() -> None:
    from kcs_adapters.desktop_semantic_review import (
        SEMANTIC_REVIEW_MAX_RANKED_EXCERPTS,
        selected_semantic_review_excerpts,
    )

    unapproved_url = "https://example.invalid/articles/123456789"
    excerpts = selected_semantic_review_excerpts(
        _semantic_review_text_with_middle_resolution_reference(unapproved_url)
    )

    assert len(excerpts) == SEMANTIC_REVIEW_MAX_RANKED_EXCERPTS
    assert all(unapproved_url not in str(excerpt["text"]) for excerpt in excerpts)


def test_unrelated_public_reference_does_not_change_excerpt_selection() -> None:
    from kcs_adapters.desktop_semantic_review import (
        SEMANTIC_REVIEW_MAX_RANKED_EXCERPTS,
        selected_semantic_review_excerpts,
    )

    public_url = "https://support.plesk.com/hc/en-us/articles/123456789"
    baseline_text = _semantic_review_text_with_middle_resolution_reference(
        "https://example.invalid/articles/123456789"
    )
    text = baseline_text.replace(
        "Synthetic operation 4 fails with a reported error.",
        (
            "Synthetic operation 4 fails with a reported error. "
            f"An unrelated note mentions {public_url}."
        ),
    )

    baseline = selected_semantic_review_excerpts(baseline_text)
    excerpts = selected_semantic_review_excerpts(text)

    assert len(excerpts) == SEMANTIC_REVIEW_MAX_RANKED_EXCERPTS
    assert [excerpt["role"] for excerpt in excerpts] == [
        excerpt["role"] for excerpt in baseline
    ]
    assert [
        str(excerpt["text"]).replace(
            f" An unrelated note mentions {public_url}.",
            "",
        )
        for excerpt in excerpts
    ] == [str(excerpt["text"]) for excerpt in baseline]


def test_semantic_review_excerpts_keep_customer_howto_questions() -> None:
    from kcs_adapters.desktop_semantic_review import (
        selected_semantic_review_excerpts,
    )

    excerpts = selected_semantic_review_excerpts(
        "\n\n".join(
            [
                (
                    "Customer asks how to create an account to manage a "
                    "licence when my.plesk.com returns an email error."
                ),
                (
                    "Customer reports a command syntax issue for disabling "
                    "Nextcloud maintenance mode. They tried occ commands but "
                    "both do not work."
                ),
                (
                    "Customer also asks: We have a problem with the PHP "
                    "OPcache module that is not available. How can we activate "
                    "it or modify it? The answer explains checking the domain "
                    "PHP Settings and Performance Settings."
                ),
                (
                    "Support resolved the command issue by running occ with "
                    "the correct Plesk PHP binary from the Nextcloud directory."
                ),
            ]
        )
    )

    excerpt_text = "\n".join(str(excerpt["text"]) for excerpt in excerpts)
    assert "OPcache module" in excerpt_text
    assert "How can we activate it or modify it" in excerpt_text
    question_excerpt = next(
        excerpt for excerpt in excerpts if "OPcache module" in str(excerpt["text"])
    )
    assert question_excerpt["role"] == "unclassified_evidence"


def test_semantic_review_excerpts_keep_flattened_labeled_answer_and_internal_note(
) -> None:
    from kcs_adapters.desktop_semantic_review import (
        selected_semantic_review_excerpts,
    )

    excerpts = selected_semantic_review_excerpts(
        "\n".join(
            [
                "Customer-reported symptom:",
                "A governed operation fails.",
                "Confirmed cause:",
                "A required setting is disabled.",
                "Supported resolution:",
                "Enable the setting and verify the operation.",
                "Customer question:",
                "How can a maintenance task be performed?",
                "Supported answer:",
                "Run the approved maintenance operation.",
                "Internal workflow note:",
                "This content records internal routing only.",
            ]
        )
    )

    assert [(excerpt["role"], excerpt["text"]) for excerpt in excerpts] == [
        (
            "unclassified_evidence",
            "Customer-reported symptom:\nA governed operation fails.",
        ),
        (
            "unclassified_evidence",
            "Confirmed cause:\nA required setting is disabled.",
        ),
        (
            "unclassified_evidence",
            "Supported resolution:\nEnable the setting and verify the operation.",
        ),
        (
            "unclassified_evidence",
            "Customer question:\nHow can a maintenance task be performed?",
        ),
        (
            "unclassified_evidence",
            "Supported answer:\nRun the approved maintenance operation.",
        ),
        (
            "internal_workflow_note",
            "Internal workflow note:\nThis content records internal routing only.",
        ),
    ]


def test_semantic_review_role_index_keeps_atomic_model_neutral_evidence() -> None:
    pending = desktop_semantic_review.new_pending_semantic_review(
        approved_summary_text="\n\n".join(
            [
                (
                    "Issue 1 — customer-reported symptom: A product task shows "
                    "no result. Confirmed cause: A required component is missing. "
                    "Supported resolution: Run product-service restart and confirm "
                    "that the task succeeds."
                ),
                (
                    "Issue 2 — customer-reported symptom: A second product task "
                    "fails with an error. Confirmed cause: A product directory has "
                    "incorrect ownership. Supported resolution: Back up the "
                    "directory, restore ownership, and confirm successful output."
                ),
            ]
        ),
        source_kind="local_clean_ticket",
        ticket_ref="ticket-role-index-synthetic",
        ttl_seconds=60,
    )

    excerpts = pending.packet["selected_excerpts"]
    assert isinstance(excerpts, list)
    role_index = desktop_semantic_review.semantic_review_excerpt_role_index(pending)

    assert [
        role_index[excerpt["source_ref"]]["roles"] for excerpt in excerpts
    ] == [
        ["unclassified_evidence"],
        ["unclassified_evidence"],
        ["unclassified_evidence"],
        ["unclassified_evidence"],
        ["unclassified_evidence"],
        ["unclassified_evidence"],
    ]
    source_refs = [excerpt["source_ref"] for excerpt in excerpts]

    def observation(text: str, source_ref: str) -> dict[str, object]:
        return {"source_refs": [source_ref], "text": text}

    issues = []
    for index, offset in enumerate(range(0, len(source_refs), 3), start=1):
        symptom_ref, cause_ref, resolution_ref = source_refs[offset : offset + 3]
        issues.append(
            {
                "answer_evidence": [],
                "cause_evidence": [
                    observation("A supported cause is recorded.", cause_ref)
                ],
                "context_evidence": [],
                "error_evidence": [],
                "issue_ref": f"issue-{index:03d}",
                "question": None,
                "resolution_evidence": [
                    observation("A supported resolution is recorded.", resolution_ref)
                ],
                "summary": observation(
                    f"Synthetic product issue {index}", symptom_ref
                ),
                "symptoms": [
                    observation("A product task fails.", symptom_ref)
                ],
                "verification_evidence": [],
            }
        )
    projected = desktop_semantic_candidates.project_semantic_issue_proposals(
        {
            "case_ref": pending.semantic_review_ref,
            "coverage_records": [],
            "extraction_source_ref": "semantic-proposal-role-index-synthetic",
            "issues": issues,
            "schema_version": SEMANTIC_ISSUE_PROPOSAL_SCHEMA_VERSION,
            "source_refs": source_refs,
        },
        role_index,
    )

    assert projected.blocked_proposals == ()
    assert projected.unassigned_evidence == ()
    assert projected.selectable_issue_refs == ("issue-001", "issue-002")


def _prepared_issue_proposal_packet(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    with_environment: bool = False,
) -> tuple[McpStdioTransport, str, Mapping[str, Any]]:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles"
        )
    )
    _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_REGISTER_CLEAN_TICKET),
        {
            "clean_ticket_text": "\n".join(
                (
                    [
                        "Environment: Plesk for Linux",
                    ]
                    if with_environment
                    else []
                )
                + [
                    "Customer Ticket Content",
                    "The customer reports that a synthetic operation fails.",
                    "The investigation mentions one possible cause, then another.",
                    "A final resolution is present but scattered across notes.",
                    (
                        "Support ran systemctl restart synthetic-service and "
                        "verified the service status."
                    ),
                ]
                * 45
            ),
            "ticket_ref": "ticket-semantic-proposal-runtime",
        },
    )
    draft_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"ticket_ref": "ticket-semantic-proposal-runtime", "debug": True},
    )
    assert draft_response is not None
    semantic_review_ref = draft_response["result"]["structuredContent"][
        "semantic_review_ref"
    ]
    prepare_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_PREPARE_SEMANTIC_REVIEW),
        {"semantic_review_ref": semantic_review_ref},
    )
    assert prepare_response is not None
    packet = prepare_response["result"]["structuredContent"]
    assert packet["required_submit_shape"]["semantic_issue_proposal"][
        "schema_version"
    ] == SEMANTIC_ISSUE_PROPOSAL_SCHEMA_VERSION
    assert "active_output_schema" not in packet
    assert "runtime_default" not in packet
    assert "shadow_mode" not in packet
    assert "do not omit explicit resolution steps" in packet["task"]
    return transport, semantic_review_ref, packet


def _selected_excerpt_text(
    packet: Mapping[str, Any],
    source_ref: str,
) -> str:
    excerpts = packet["selected_excerpts"]
    assert isinstance(excerpts, list)
    for excerpt in excerpts:
        assert isinstance(excerpt, dict)
        if excerpt["source_ref"] == source_ref:
            text = excerpt["text"]
            assert isinstance(text, str)
            return text
    raise AssertionError("selected excerpt unavailable")


def _source_ref_containing(
    packet: Mapping[str, Any],
    needle: str,
) -> str:
    excerpts = packet["selected_excerpts"]
    assert isinstance(excerpts, list)
    for excerpt in excerpts:
        assert isinstance(excerpt, dict)
        text = excerpt["text"]
        if isinstance(text, str) and needle in text:
            source_ref = excerpt["source_ref"]
            assert isinstance(source_ref, str)
            return source_ref
    raise AssertionError("selected excerpt text unavailable")


@pytest.mark.parametrize("json_encoded_transport", [False, True])
def test_validated_semantic_proposal_reaches_operator_selection(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    json_encoded_transport: bool,
) -> None:
    transport, semantic_review_ref, packet = _prepared_issue_proposal_packet(
        tmp_path, monkeypatch
    )
    tools_response = transport.handle_message(_request("tools/list"))
    assert tools_response is not None
    submit_tool = _tools_by_name(tools_response["result"]["tools"])[
        "kcs_submit_semantic_review"
    ]
    assert set(submit_tool["inputSchema"]["properties"]) == {
        "semantic_issue_proposal",
        "semantic_review_ref",
    }
    assert submit_tool["inputSchema"]["required"] == [
        "semantic_issue_proposal",
        "semantic_review_ref",
    ]
    source_refs = packet["allowed_source_refs"]
    assert isinstance(source_refs, list)

    assert len(source_refs) >= 2

    def observation(
        text: str,
        refs: list[str] = source_refs,
    ) -> dict[str, object]:
        return {"source_refs": refs, "text": text}

    def issue(
        issue_ref: str,
        summary: str,
        identity_refs: list[str],
    ) -> dict[str, object]:
        identity_observations = [
            observation(
                _selected_excerpt_text(packet, identity_ref),
                [identity_ref],
            )
            for identity_ref in identity_refs
        ]
        return {
            "cause_evidence": identity_observations,
            "error_evidence": [
                observation(
                    _selected_excerpt_text(packet, source_refs[0]),
                    [source_refs[0]],
                )
            ],
            "issue_ref": issue_ref,
            "resolution_evidence": identity_observations,
            "summary": summary,
            "symptoms": [
                observation(
                    _selected_excerpt_text(packet, source_refs[0]),
                    [source_refs[0]],
                )
            ],
        }

    proposal = {
        "case_ref": semantic_review_ref,
        "coverage_records": [],
        "extraction_source_ref": "semantic-proposal-selection-001",
        "issues": [
            issue(
                "issue-001",
                "Synthetic operation one returns no result",
                [source_refs[0]],
            ),
            issue(
                "issue-002",
                "Synthetic operation two returns no result",
                source_refs[1:],
            ),
        ],
        "schema_version": SEMANTIC_ISSUE_PROPOSAL_SCHEMA_VERSION,
        "source_refs": source_refs,
    }
    submitted_proposal: object = (
        json.dumps(proposal) if json_encoded_transport else proposal
    )
    submit_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "semantic_issue_proposal": submitted_proposal,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert submit_response is not None
    structured = submit_response["result"]["structuredContent"]
    assert submit_response["result"]["isError"] is False
    assert structured["recommended_action"] == "split_required", structured
    assert structured["operator_prompt_style"] == "native_choice_popup"
    assert structured["operator_choice_request"]["prose_only_choice_allowed"] is False
    assert [item["item_ref"] for item in structured["item_candidates"]] == [
        "issue-001",
        "issue-002",
    ]
    all_option = structured["operator_choice_request"]["options"][-1]
    assert all_option == {
        "label": "All candidates",
        "submit_arguments": {
            "operator_selected_item_refs": ["issue-001", "issue-002"],
            "operator_selection_ref": structured["operator_selection_ref"],
        },
        "value": "all",
    }
    assert "operator_all_submit_arguments" not in structured
    assert "all_submit_arguments" not in structured["operator_choice_request"]

    batch_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        all_option["submit_arguments"],
    )

    assert batch_response is not None
    batch = batch_response["result"]["structuredContent"]
    assert batch_response["result"]["isError"] is False
    assert batch["result_kind"] == "draft_article_batch"
    assert batch.get("debug_code") != "draft_article_args_invalid"
    assert [outcome["item_ref"] for outcome in batch["candidate_outcomes"]] == [
        "issue-001",
        "issue-002",
    ]
    assert all(outcome["attempted"] is True for outcome in batch["candidate_outcomes"])


def _unassigned_proposal(
    packet: Mapping[str, Any],
    semantic_review_ref: str,
) -> dict[str, object]:
    source_refs = list(packet["allowed_source_refs"])
    symptom_ref = _source_ref_containing(packet, "customer reports")
    cause_ref = _source_ref_containing(packet, "possible cause")
    resolution_ref = _source_ref_containing(packet, "systemctl restart")
    assigned_refs = [symptom_ref, cause_ref, resolution_ref]
    unassigned_refs = [ref for ref in source_refs if ref not in assigned_refs]

    def observation(text: str, source_ref: str) -> dict[str, object]:
        return {"source_refs": [source_ref], "text": text}

    return {
        "case_ref": semantic_review_ref,
        "coverage_records": [
            {
                "coverage_ref": "coverage-001",
                "duplicate_of_source_ref": None,
                "reason_code": "ticket_metadata",
                "source_refs": unassigned_refs,
            }
        ],
        "extraction_source_ref": "semantic-proposal-boundary-001",
        "issues": [
            {
                "answer_evidence": [],
                "cause_evidence": [
                    observation(
                        _selected_excerpt_text(packet, cause_ref),
                        cause_ref,
                    )
                ],
                "context_evidence": [],
                "error_evidence": [
                    observation(
                        _selected_excerpt_text(packet, symptom_ref),
                        symptom_ref,
                    )
                ],
                "issue_ref": "issue-001",
                "question": None,
                "resolution_evidence": [
                    observation(
                        _selected_excerpt_text(packet, resolution_ref),
                        resolution_ref,
                    )
                ],
                "summary": {
                    "source_refs": assigned_refs,
                    "text": "A synthetic operation returns no result",
                },
                "symptoms": [
                    observation(
                        _selected_excerpt_text(packet, symptom_ref),
                        symptom_ref,
                    )
                ],
                "verification_evidence": [],
            }
        ],
        "schema_version": SEMANTIC_ISSUE_PROPOSAL_SCHEMA_VERSION,
        "source_refs": source_refs,
    }


def _two_issue_proposal(
    packet: Mapping[str, Any],
    semantic_review_ref: str,
) -> dict[str, object]:
    source_refs = list(packet["allowed_source_refs"])
    exact_text = _selected_excerpt_text(packet, source_refs[0])

    def observation(text: str) -> dict[str, object]:
        return {"source_refs": source_refs, "text": text}

    def issue(issue_ref: str, summary: str) -> dict[str, object]:
        return {
            "answer_evidence": [],
            "cause_evidence": [observation(exact_text)],
            "context_evidence": [],
            "error_evidence": [observation(exact_text)],
            "issue_ref": issue_ref,
            "question": None,
            "resolution_evidence": [observation(exact_text)],
            "summary": observation(summary),
            "symptoms": [observation(exact_text)],
            "verification_evidence": [],
        }

    return {
        "case_ref": semantic_review_ref,
        "coverage_records": [],
        "extraction_source_ref": "semantic-proposal-overlap-001",
        "issues": [
            issue("issue-001", "Synthetic operation one returns no result"),
            issue("issue-002", "Synthetic operation two returns no result"),
        ],
        "schema_version": SEMANTIC_ISSUE_PROPOSAL_SCHEMA_VERSION,
        "source_refs": source_refs,
    }


def test_unassigned_evidence_is_preserved_without_operator_checkpoint(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_issue_proposal_packet(
        tmp_path, monkeypatch
    )
    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "semantic_issue_proposal": _unassigned_proposal(
                packet, semantic_review_ref
            ),
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    continued = response["result"]["structuredContent"]
    assert continued["result_kind"] == "draft_article_authoring"
    assert continued["approved_summary_source"] == "semantic_review"
    assert continued.get("workflow_state") != (
        "semantic_review_boundary_choice_required"
    )
    assert continued.get("next_required_action") != (
        "operator_resolve_semantic_boundary"
    )
    assert any(
        outcome["outcome"] == "unassigned_evidence"
        for outcome in continued["semantic_item_outcomes"]
    )


def test_grouped_semantic_summary_longer_than_title_bound_still_drafts(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_issue_proposal_packet(
        tmp_path,
        monkeypatch,
        with_environment=True,
    )
    proposal = _unassigned_proposal(packet, semantic_review_ref)
    issues = proposal["issues"]
    assert isinstance(issues, list)
    issue = issues[0]
    assert isinstance(issue, dict)
    summary = issue["summary"]
    assert isinstance(summary, dict)
    summary["text"] = (
        "A synthetic operation returns no result after a configuration change "
        "and reports several related symptoms while the confirmed component "
        "state and supported recovery procedure remain part of one searchable "
        "technical issue."
    )
    assert len(summary["text"]) > 180
    resolution_ref = _source_ref_containing(packet, "systemctl restart")
    issue["resolution_evidence"] = [
        {
            "source_refs": [resolution_ref],
            "text": _selected_excerpt_text(packet, resolution_ref),
        }
    ]

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "semantic_issue_proposal": proposal,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    drafted = response["result"]["structuredContent"]
    assert drafted.get("debug_code") != "approved_summary_renderer_bounds_failed"
    assert drafted["draft_generated"] is True, drafted


def test_unassigned_evidence_flows_directly_to_native_candidate_selection(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_issue_proposal_packet(
        tmp_path, monkeypatch
    )
    source_refs = list(packet["allowed_source_refs"])
    assigned_refs = source_refs[:-1]

    def observation(text: str, refs: list[str]) -> dict[str, object]:
        return {"source_refs": refs, "text": text}

    def issue(issue_ref: str, summary: str, identity_ref: str) -> dict[str, object]:
        return {
            "answer_evidence": [],
            "cause_evidence": [
                observation(
                    _selected_excerpt_text(packet, identity_ref),
                    [identity_ref],
                )
            ],
            "context_evidence": [],
            "error_evidence": [
                observation(
                    _selected_excerpt_text(packet, assigned_refs[0]),
                    [assigned_refs[0]],
                )
            ],
            "issue_ref": issue_ref,
            "question": None,
            "resolution_evidence": [
                observation(
                    _selected_excerpt_text(packet, identity_ref),
                    [identity_ref],
                )
            ],
            "summary": observation(summary, assigned_refs),
            "symptoms": [
                observation(
                    _selected_excerpt_text(packet, assigned_refs[0]),
                    [assigned_refs[0]],
                )
            ],
            "verification_evidence": [],
        }

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "semantic_issue_proposal": {
                "case_ref": semantic_review_ref,
                "coverage_records": [
                    {
                        "coverage_ref": "coverage-001",
                        "duplicate_of_source_ref": None,
                        "reason_code": "ticket_metadata",
                        "source_refs": [source_refs[-1]],
                    }
                ],
                "extraction_source_ref": "semantic-proposal-unassigned-selection-001",
                "issues": [
                    issue(
                        "issue-001",
                        "Synthetic operation one returns no result",
                        source_refs[0],
                    ),
                    issue(
                        "issue-002",
                        "Synthetic operation two returns no result",
                        source_refs[-2],
                    ),
                ],
                "schema_version": SEMANTIC_ISSUE_PROPOSAL_SCHEMA_VERSION,
                "source_refs": source_refs,
            },
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    selection = response["result"]["structuredContent"]
    assert selection["recommended_action"] == "split_required"
    assert [item["item_ref"] for item in selection["item_candidates"]] == [
        "issue-001",
        "issue-002",
    ]
    assert any(
        outcome["outcome"] == "unassigned_evidence"
        for outcome in selection["semantic_item_outcomes"]
    )
    assert selection.get("workflow_state") != (
        "semantic_review_boundary_choice_required"
    )


def test_unassigned_evidence_and_shared_refs_flow_to_selection(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_issue_proposal_packet(
        tmp_path, monkeypatch
    )
    proposal = _unassigned_proposal(packet, semantic_review_ref)
    issues = proposal["issues"]
    assert isinstance(issues, list)
    first_issue = issues[0]
    assert isinstance(first_issue, dict)
    second_issue = dict(first_issue)
    second_issue["issue_ref"] = "issue-002"
    second_issue["summary"] = dict(first_issue["summary"])
    second_issue["summary"]["text"] = "A second synthetic operation fails"
    issues.append(second_issue)

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "semantic_issue_proposal": proposal,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    selection = response["result"]["structuredContent"]
    assert selection["recommended_action"] == "split_required"
    assert [item["item_ref"] for item in selection["item_candidates"]] == [
        "issue-001",
        "issue-002",
    ]
    assert all(
        "boundary_state" not in outcome and "boundary_provenance" not in outcome
        for outcome in selection["semantic_item_outcomes"]
        if outcome["item_ref"].startswith("issue-")
    )
    assert any(
        outcome["outcome"] == "unassigned_evidence"
        for outcome in selection["semantic_item_outcomes"]
    )


def test_shared_identity_refs_flow_to_mandatory_selection(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_issue_proposal_packet(
        tmp_path, monkeypatch
    )
    proposal = _two_issue_proposal(packet, semantic_review_ref)

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "semantic_issue_proposal": proposal,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    selection = response["result"]["structuredContent"]
    assert selection["recommended_action"] == "split_required"
    assert [item["item_ref"] for item in selection["item_candidates"]] == [
        "issue-001",
        "issue-002",
    ]
    assert all(
        "boundary_state" not in outcome and "boundary_provenance" not in outcome
        for outcome in selection["semantic_item_outcomes"]
    )


@pytest.mark.parametrize("missing_field", ["cause_evidence", "resolution_evidence"])
def test_incomplete_technical_identity_is_immediately_terminal(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    missing_field: str,
) -> None:
    transport, semantic_review_ref, packet = _prepared_issue_proposal_packet(
        tmp_path, monkeypatch
    )
    source_refs = list(packet["allowed_source_refs"])
    exact_text = _selected_excerpt_text(packet, source_refs[0])

    def observation(text: str) -> dict[str, object]:
        return {"source_refs": source_refs, "text": text}

    issue = {
        "answer_evidence": [],
        "cause_evidence": [observation(exact_text)],
        "context_evidence": [],
        "error_evidence": [observation(exact_text)],
        "issue_ref": "issue-001",
        "question": None,
        "resolution_evidence": [observation(exact_text)],
        "summary": observation("A synthetic operation returns no result"),
        "symptoms": [observation(exact_text)],
        "verification_evidence": [],
    }
    issue[missing_field] = []
    proposal = {
        "case_ref": semantic_review_ref,
        "coverage_records": [],
        "extraction_source_ref": "semantic-proposal-incomplete-identity",
        "issues": [issue],
        "schema_version": SEMANTIC_ISSUE_PROPOSAL_SCHEMA_VERSION,
        "source_refs": source_refs,
    }

    first = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "semantic_issue_proposal": proposal,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert first is not None
    terminal = first["result"]["structuredContent"]
    assert terminal["debug_code"] == "semantic_issue_boundary_ambiguous"
    assert terminal["workflow_state"] == "semantic_review_boundary_terminal"
    assert terminal["next_required_action"] == (
        "operator_review_semantic_boundary_blocker"
    )
    assert terminal["boundary_blocker_codes"] == ["evidence_shape_invalid"]
    assert terminal["boundary_blocker_count"] == 1
    assert terminal["review_summary"]["boundary_blocker_codes"] == [
        "evidence_shape_invalid"
    ]
    assert terminal["review_summary"]["boundary_blocker_count"] == 1
    assert terminal["draft_generated"] is False
    assert terminal["reviewer_bundle_written"] is False
    terminal_text = first["result"]["content"][0]["text"]
    assert "evidence_shape_invalid" in terminal_text


def test_incomplete_issue_does_not_hide_complete_candidates(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_issue_proposal_packet(
        tmp_path, monkeypatch
    )
    proposal = _two_issue_proposal(packet, semantic_review_ref)
    issues = proposal["issues"]
    assert isinstance(issues, list)
    incomplete = deepcopy(issues[0])
    incomplete["issue_ref"] = "issue-003"
    incomplete["resolution_evidence"] = []
    incomplete["summary"] = {
        "source_refs": list(packet["allowed_source_refs"]),
        "text": "Synthetic operation three has incomplete resolution evidence",
    }
    issues.append(incomplete)

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "semantic_issue_proposal": proposal,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    selection = response["result"]["structuredContent"]
    assert selection["recommended_action"] == "split_required"
    assert [item["item_ref"] for item in selection["item_candidates"]] == [
        "issue-001",
        "issue-002",
    ]
    outcomes = {
        outcome["item_ref"]: outcome for outcome in selection["semantic_item_outcomes"]
    }
    assert outcomes["issue-003"]["kcs_item_status"] == (
        "blocked_need_more_evidence"
    )
    assert outcomes["issue-003"]["outcome"] == "blocked_need_more_evidence"
    assert selection.get("workflow_state") != "semantic_review_boundary_terminal"


def test_symptomless_issue_cannot_reach_authoring_or_hide_complete_candidates(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_issue_proposal_packet(
        tmp_path, monkeypatch
    )
    proposal = _two_issue_proposal(packet, semantic_review_ref)
    issues = proposal["issues"]
    assert isinstance(issues, list)
    incomplete = deepcopy(issues[0])
    incomplete["issue_ref"] = "issue-003"
    incomplete["symptoms"] = []
    incomplete["error_evidence"] = []
    incomplete["summary"] = {
        "source_refs": list(packet["allowed_source_refs"]),
        "text": "A synthetic issue has no symptom evidence",
    }
    issues.append(incomplete)

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "semantic_issue_proposal": proposal,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    selection = response["result"]["structuredContent"]
    assert selection["recommended_action"] == "split_required"
    assert [item["item_ref"] for item in selection["item_candidates"]] == [
        "issue-001",
        "issue-002",
    ]
    outcomes = {
        outcome["item_ref"]: outcome for outcome in selection["semantic_item_outcomes"]
    }
    assert outcomes["issue-003"]["kcs_item_status"] == (
        "blocked_need_more_evidence"
    )
    assert outcomes["issue-003"]["outcome"] == "blocked_need_more_evidence"
    assert selection.get("workflow_state") != "semantic_review_boundary_terminal"


def test_incomplete_issue_does_not_hide_single_complete_candidate(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_issue_proposal_packet(
        tmp_path, monkeypatch
    )
    proposal = _two_issue_proposal(packet, semantic_review_ref)
    issues = proposal["issues"]
    assert isinstance(issues, list)
    incomplete = issues[1]
    assert isinstance(incomplete, dict)
    incomplete["resolution_evidence"] = []

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "semantic_issue_proposal": proposal,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    continued = response["result"]["structuredContent"]
    assert continued["result_kind"] == "draft_article_authoring"
    assert continued["approved_summary_source"] == "semantic_review"
    assert continued.get("workflow_state") != "semantic_review_boundary_terminal"
    outcomes = {
        outcome["item_ref"]: outcome for outcome in continued["semantic_item_outcomes"]
    }
    assert outcomes["issue-002"]["kcs_item_status"] == (
        "blocked_need_more_evidence"
    )
    assert outcomes["issue-002"]["outcome"] == "blocked_need_more_evidence"


def test_schema_correction_budget_is_independent_and_bounded(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_issue_proposal_packet(
        tmp_path, monkeypatch
    )
    proposal = _unassigned_proposal(packet, semantic_review_ref)
    coverage_records = proposal["coverage_records"]
    assert isinstance(coverage_records, list)
    coverage_record = coverage_records[0]
    assert isinstance(coverage_record, dict)
    coverage_record["reason_code"] = "model_selected_reason"
    arguments = {
        "semantic_issue_proposal": proposal,
        "semantic_review_ref": semantic_review_ref,
    }

    first = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        arguments,
    )
    assert first is not None
    first_result = first["result"]["structuredContent"]
    assert first_result["debug_code"] == "semantic_coverage_reason_invalid"
    assert first_result["semantic_submission_correction"]["retry_allowed"] is True

    second = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        arguments,
    )
    assert second is not None
    second_result = second["result"]["structuredContent"]
    assert second_result["debug_code"] == "semantic_issue_submission_invalid"
    assert "semantic_submission_correction" not in second_result
    assert second_result["reviewer_bundle_written"] is False


def test_exhausted_semantic_correction_preserves_bounded_terminal_cause(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_issue_proposal_packet(
        tmp_path, monkeypatch
    )
    proposal = _unassigned_proposal(packet, semantic_review_ref)
    coverage_records = proposal["coverage_records"]
    assert isinstance(coverage_records, list)
    coverage_record = coverage_records[0]
    assert isinstance(coverage_record, dict)
    coverage_record["reason_code"] = "model_selected_reason"

    first = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "semantic_issue_proposal": proposal,
            "semantic_review_ref": semantic_review_ref,
        },
    )
    assert first is not None
    assert first["result"]["structuredContent"]["debug_code"] == (
        "semantic_coverage_reason_invalid"
    )

    coverage_record["reason_code"] = "administrative_or_duplicate"
    source_refs = proposal["source_refs"]
    assert isinstance(source_refs, list)
    source_refs.append("excerpt-not-prepared")
    second = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "semantic_issue_proposal": proposal,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert second is not None
    second_result = second["result"]["structuredContent"]
    assert second_result["debug_code"] == "semantic_issue_submission_invalid"
    assert second_result["terminal_cause_debug_code"] == (
        "semantic_issue_top_level_source_refs_mismatch"
    )
    assert "semantic_submission_correction" not in second_result
    assert second_result.get("next_required_action") is None
    assert second_result["reviewer_bundle_written"] is False
    second_text = second["result"]["content"][0]["text"]
    assert "semantic_issue_top_level_source_refs_mismatch" in second_text
    assert "No bounded correction is available" in second_text


@pytest.mark.parametrize(
    ("invalid_shape", "expected_debug_code", "expected_field"),
    [
        (
            "case_ref",
            "semantic_issue_case_ref_mismatch",
            "case_ref",
        ),
        (
            "coverage",
            "semantic_issue_coverage_incomplete",
            "source_coverage",
        ),
        (
            "source_refs",
            "semantic_issue_top_level_source_refs_mismatch",
            "source_refs",
        ),
        (
            "issues",
            "semantic_issue_candidate_limit_exceeded",
            "issues",
        ),
    ],
)
def test_submit_shape_correction_is_single_use_and_bounded(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_shape: str,
    expected_debug_code: str,
    expected_field: str,
) -> None:
    transport, semantic_review_ref, packet = _prepared_issue_proposal_packet(
        tmp_path, monkeypatch
    )
    proposal = _unassigned_proposal(packet, semantic_review_ref)
    if invalid_shape == "case_ref":
        proposal["case_ref"] = "semantic-review-other-001"
    elif invalid_shape == "coverage":
        proposal["coverage_records"] = []
    elif invalid_shape == "source_refs":
        source_refs = proposal["source_refs"]
        assert isinstance(source_refs, list)
        source_refs.append("excerpt-extra")
    else:
        issues = proposal["issues"]
        assert isinstance(issues, list)
        issue = issues[0]
        assert isinstance(issue, dict)
        proposal["issues"] = [
            {**issue, "issue_ref": f"issue-{index:03d}"}
            for index in range(1, 7)
        ]
    arguments = {
        "semantic_issue_proposal": proposal,
        "semantic_review_ref": semantic_review_ref,
    }

    first = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        arguments,
    )

    assert first is not None
    first_result = first["result"]["structuredContent"]
    assert first_result["debug_code"] == expected_debug_code
    assert first_result["workflow_state"] == "semantic_review_submit_blocked"
    assert first_result["semantic_submission_correction"] == {
        **semantic_submission_correction(expected_debug_code),
        "retry_allowed": True,
    }
    assert first_result["semantic_submission_correction"]["field_name"] == (
        expected_field
    )
    assert first_result["next_required_action"] == (
        "retry_corrected_semantic_submission"
    )
    first_text = first["result"]["content"][0]["text"]
    assert "Submit shape correction" in first_text
    assert "Retry kcs_submit_semantic_review once" in first_text

    second = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        arguments,
    )

    assert second is not None
    second_result = second["result"]["structuredContent"]
    assert second_result["debug_code"] == "semantic_issue_submission_invalid"
    assert "semantic_submission_correction" not in second_result
    assert "next_required_action" not in second_result
    assert second_result["draft_generated"] is False
    assert second_result["reviewer_bundle_written"] is False


def test_retired_candidate_extraction_submit_shape_fails_closed(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_issue_proposal_packet(
        tmp_path, monkeypatch
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": {
                "case_ref": semantic_review_ref,
                "items": [],
                "schema_version": CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION,
                "source_refs": packet["allowed_source_refs"],
            },
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["workflow_state"] == "semantic_review_submit_blocked"
    assert structured["debug_code"] == "semantic_review_submission_invalid"
    assert structured["draft_generated"] is False
    assert structured["reviewer_bundle_written"] is False
    assert structured["manual_draft_allowed"] is False

    same_ref_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "semantic_issue_proposal": _unassigned_proposal(
                packet, semantic_review_ref
            ),
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert same_ref_response is not None
    same_ref = same_ref_response["result"]["structuredContent"]
    assert same_ref["workflow_state"] == "semantic_review_submit_blocked"
    assert same_ref["debug_code"] == "semantic_review_unavailable"
    assert "semantic_submission_correction" not in same_ref
    assert same_ref["draft_generated"] is False
    assert same_ref["reviewer_bundle_written"] is False


def test_semantic_issue_proposal_rejects_article_markdown_without_drafting(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_issue_proposal_packet(
        tmp_path, monkeypatch
    )
    proposal = _unassigned_proposal(packet, semantic_review_ref)
    proposal["article_markdown"] = "# Draft article"

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "semantic_issue_proposal": proposal,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["workflow_state"] == "semantic_review_submit_blocked"
    assert structured["debug_code"] == (
        "semantic_review_forbidden_html_or_markdown"
    )
    assert structured["draft_generated"] is False
    assert structured["reviewer_bundle_written"] is False
    assert structured["manual_draft_allowed"] is False
    assert "# Draft article" not in json.dumps(response, sort_keys=True)


def test_terminal_local_ref_blocker_does_not_instruct_retry(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_issue_proposal_packet(
        tmp_path, monkeypatch
    )
    proposal = _unassigned_proposal(packet, semantic_review_ref)
    issues = proposal["issues"]
    assert isinstance(issues, list)
    issue = issues[0]
    assert isinstance(issue, dict)
    summary = issue["summary"]
    assert isinstance(summary, dict)
    summary["text"] = "Synthetic issue references /private/tmp/reviewer.html."

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "semantic_issue_proposal": proposal,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["debug_code"] == "semantic_review_local_ref_blocked"
    assert "semantic_submission_correction" not in structured
    assert "next_required_action" not in structured
    result_text = response["result"]["content"][0]["text"]
    assert "No bounded correction is available; stop" in result_text
    assert "Submit shape correction" not in result_text


def test_terminal_semantic_shape_blocker_preserves_value_safe_reason(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_issue_proposal_packet(
        tmp_path, monkeypatch
    )
    proposal = _unassigned_proposal(packet, semantic_review_ref)
    issues = proposal["issues"]
    assert isinstance(issues, list)
    duplicate = dict(issues[0])
    issues.append(duplicate)

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "semantic_issue_proposal": proposal,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["debug_code"] == "semantic_issue_proposal_shape_invalid"
    assert structured["workflow_state"] == "semantic_review_submit_blocked"
    assert "semantic_submission_correction" not in structured
    assert structured["draft_generated"] is False
    assert structured["reviewer_bundle_written"] is False


@pytest.mark.parametrize(
    ("invalid_kind", "expected_debug_code"),
    [
        ("unsafe_value", "semantic_review_unsafe_value_blocked"),
        ("unsafe_ref", "semantic_ref_shape_invalid"),
    ],
)
def test_terminal_semantic_validation_classes_are_operator_visible(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_kind: str,
    expected_debug_code: str,
) -> None:
    transport, semantic_review_ref, packet = _prepared_issue_proposal_packet(
        tmp_path, monkeypatch
    )
    proposal = _unassigned_proposal(packet, semantic_review_ref)
    issues = proposal["issues"]
    assert isinstance(issues, list)
    issue = issues[0]
    assert isinstance(issue, dict)
    if invalid_kind == "unsafe_value":
        summary = issue["summary"]
        assert isinstance(summary, dict)
        summary["text"] = "A synthetic issue affects private.example.test."
    else:
        issue["issue_ref"] = "issue/unsafe"

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "semantic_issue_proposal": proposal,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["debug_code"] == expected_debug_code
    assert "semantic_submission_correction" not in structured
    assert structured["draft_generated"] is False
    assert structured["reviewer_bundle_written"] is False


def test_observation_shape_gets_one_bounded_correction_and_can_retry(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_issue_proposal_packet(
        tmp_path, monkeypatch
    )
    proposal = _unassigned_proposal(packet, semantic_review_ref)
    issues = proposal["issues"]
    assert isinstance(issues, list)
    issue = issues[0]
    assert isinstance(issue, dict)
    valid_summary = issue["summary"]
    assert isinstance(valid_summary, dict)
    valid_resolution_evidence = issue["resolution_evidence"]
    issue["summary"] = {**valid_summary, "unexpected": "field"}
    issue["resolution_evidence"] = "not-an-observation-list"
    arguments = {
        "semantic_issue_proposal": proposal,
        "semantic_review_ref": semantic_review_ref,
    }

    first = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        arguments,
    )

    assert first is not None
    blocked = first["result"]["structuredContent"]
    assert blocked["debug_code"] == "semantic_observation_shape_invalid"
    assert blocked["semantic_submission_correction"] == {
        **semantic_submission_correction("semantic_observation_shape_invalid"),
        "field_paths": [
            "issues[0].summary",
            "issues[0].resolution_evidence",
        ],
        "retry_allowed": True,
    }
    assert blocked["semantic_submission_correction"]["field_name"] == (
        "observation_fields"
    )
    correction_text = first["result"]["content"][0]["text"]
    assert "issues[0].summary" in correction_text
    assert "issues[0].resolution_evidence" in correction_text
    assert blocked["draft_generated"] is False
    assert blocked["reviewer_bundle_written"] is False

    issue["summary"] = valid_summary
    issue["resolution_evidence"] = valid_resolution_evidence
    second = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        arguments,
    )

    assert second is not None
    continued = second["result"]["structuredContent"]
    assert continued.get("debug_code") != "semantic_issue_submission_invalid"
    assert "semantic_submission_correction" not in continued


def test_paraphrased_observation_gets_one_exact_copy_correction(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_issue_proposal_packet(
        tmp_path,
        monkeypatch,
    )
    proposal = _unassigned_proposal(packet, semantic_review_ref)
    issues = proposal["issues"]
    assert isinstance(issues, list)
    issue = issues[0]
    assert isinstance(issue, dict)
    symptoms = issue["symptoms"]
    assert isinstance(symptoms, list)
    symptom = symptoms[0]
    assert isinstance(symptom, dict)
    exact_text = symptom["text"]
    symptom["text"] = "The synthetic operation did not work."
    arguments = {
        "semantic_issue_proposal": proposal,
        "semantic_review_ref": semantic_review_ref,
    }

    first = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        arguments,
    )

    assert first is not None
    blocked = first["result"]["structuredContent"]
    assert blocked["debug_code"] == "semantic_observation_text_not_extractive"
    assert blocked["semantic_submission_correction"] == {
        **semantic_submission_correction("semantic_observation_text_not_extractive"),
        "retry_allowed": True,
    }
    assert blocked["draft_generated"] is False
    assert blocked["reviewer_bundle_written"] is False
    assert "The synthetic operation did not work." not in json.dumps(blocked)

    symptom["text"] = exact_text
    second = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        arguments,
    )

    assert second is not None
    continued = second["result"]["structuredContent"]
    assert continued.get("debug_code") != "semantic_issue_submission_invalid"
    assert "semantic_submission_correction" not in continued


def test_terminal_semantic_blocker_rejects_unregistered_debug_code(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_issue_proposal_packet(
        tmp_path, monkeypatch
    )

    def raise_unregistered_debug_code(**_kwargs: object) -> None:
        error = RuntimeError("semantic submission failed")
        error.debug_code = "proposal-value-must-not-escape"  # type: ignore[attr-defined]
        raise error

    monkeypatch.setattr(
        desktop_workflow,
        "semantic_issue_proposal_from_submission",
        raise_unregistered_debug_code,
    )
    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "semantic_issue_proposal": _unassigned_proposal(
                packet,
                semantic_review_ref,
            ),
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["debug_code"] == "semantic_issue_submission_invalid"
    assert "proposal-value-must-not-escape" not in json.dumps(response, sort_keys=True)
    assert structured["draft_generated"] is False


def test_prepare_semantic_review_rejects_missing_state() -> None:
    transport = _initialized_transport()

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_PREPARE_SEMANTIC_REVIEW),
        {"semantic_review_ref": "semantic-review-missing"},
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["pipeline_ok"] is False
    assert structured["workflow_state"] == "semantic_review_prepare_blocked"
    assert structured["debug_code"] == "semantic_review_unavailable"
    assert structured["manual_draft_allowed"] is False
    assert structured["reviewer_bundle_written"] is False


def test_prepare_semantic_review_rejects_expired_state(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles",
            selection_ttl_seconds=-1,
        )
    )
    _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_REGISTER_CLEAN_TICKET),
        {
            "clean_ticket_text": (
                "Customer Ticket Content\n"
                "The customer reports that a product task fails.\n"
                "The investigation mentions one possible cause, then another.\n"
                "Support restarted one service and later discussed another issue."
            ),
            "ticket_ref": "ticket-semantic-review",
        },
    )
    draft_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"ticket_ref": "ticket-semantic-review", "debug": True},
    )
    assert draft_response is not None

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_PREPARE_SEMANTIC_REVIEW),
        {
            "semantic_review_ref": draft_response["result"]["structuredContent"][
                "semantic_review_ref"
            ]
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["workflow_state"] == "semantic_review_prepare_blocked"
    assert structured["debug_code"] == "semantic_review_expired"


def test_register_clean_ticket_then_draft_article_from_ref(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles"
        )
    )

    register_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_REGISTER_CLEAN_TICKET),
        {
            "clean_ticket_text": _raw_monitoring_ticket_summary(),
            "ticket_ref": "monitoring-001",
        },
    )

    assert register_response is not None
    registered = register_response["result"]["structuredContent"]
    register_text = json.dumps(register_response, sort_keys=True)
    assert register_response["result"]["isError"] is False
    assert registered["result_kind"] == "clean_ticket_registered"
    assert registered["ticket_ref"] == "monitoring-001"
    assert registered["next_arguments"] == {"ticket_ref": "monitoring-001"}
    assert "clean_ticket_text" not in register_text

    draft_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        registered["next_arguments"],
    )

    assert draft_response is not None
    draft = draft_response["result"]["structuredContent"]
    assert draft["result_kind"] == "draft_article_authoring"
    assert draft["draft_generated"] is True
    assert draft["ticket_ref"] == "monitoring-001"
    assert draft["approved_summary_source"] == "local_clean_ticket"
    assert draft["reviewer_bundle_written"] is True


def test_register_clean_ticket_rejects_truncated_visible_text(tmp_path) -> None:
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles"
        )
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_REGISTER_CLEAN_TICKET),
        {
            "clean_ticket_text": (
                "Customer Ticket Content\n"
                "Plesk Monitoring graphs show no data.\n"
                "With grafana debug enabled:\n"
                "[debug output truncated]\n"
            ),
            "ticket_ref": "monitoring-001",
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    result_output = response["result"]["content"][0]["text"]
    result_text = json.dumps(response, sort_keys=True)
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "clean_ticket_registration"
    assert structured["debug_code"] == "clean_ticket_text_incomplete"
    assert structured["writes_files"] is False
    assert "Clean ticket registration is blocked" in result_output
    assert "Do not draft manually" in result_output
    assert "debug output truncated" not in result_text


def test_register_clean_ticket_rejects_invalid_visible_text_without_retry_drafting(
    tmp_path,
) -> None:
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles"
        )
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_REGISTER_CLEAN_TICKET),
        {
            "clean_ticket_text": (
                "Customer Ticket Content\n"
                "Plesk Monitoring graphs show no data.\n"
                "Contact person@example.com for details.\n"
            ),
            "ticket_ref": "monitoring-001",
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    result_output = response["result"]["content"][0]["text"]
    result_text = json.dumps(response, sort_keys=True)
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "clean_ticket_registration"
    assert structured["debug_code"] == "clean_ticket_text_invalid"
    assert structured["writes_files"] is False
    assert "Do not draft manually" in result_output
    assert "Do not reconstruct, summarize, or invent" in result_output
    assert "person@example.com" not in result_text


def test_register_clean_ticket_rejects_embedded_tool_argument_markup(
    tmp_path,
) -> None:
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles"
        )
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_REGISTER_CLEAN_TICKET),
        {
            "clean_ticket_text": (
                "Customer Ticket Content\n"
                "Plesk Monitoring graphs show no data.\n"
                '<parameter name="ticket_ref">'
                "monitoring-graphs-no-data-rrd-path\n"
                "Resolution: disable config and restart the service.\n"
            ),
            "ticket_ref": "monitoring-001",
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    result_output = response["result"]["content"][0]["text"]
    result_text = json.dumps(response, sort_keys=True)
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "clean_ticket_registration"
    assert structured["debug_code"] == "clean_ticket_text_invalid"
    assert structured["writes_files"] is False
    assert "Do not draft manually" in result_output
    assert "parameter" not in result_text
    assert "monitoring-graphs-no-data-rrd-path" not in result_text


def test_draft_article_upload_path_ticket_ref_returns_retry_instruction() -> None:
    uploaded_path = "/mnt/user-data/uploads/sanitized_ticket_for_test.txt"

    response = _call_tool(
        _initialized_transport(),
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"ticket_ref": uploaded_path, "debug": True},
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    result_text = json.dumps(structured, sort_keys=True)
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "input_validation"
    assert structured["debug_code"] == "approved_ticket_ref_invalid"
    assert uploaded_path not in result_text


def test_draft_article_prefers_summary_text_over_ticket_ref() -> None:
    _assert_draft_article_call_shape_invalid(
        {
            **_approved_summary_args(debug=True),
            "ticket_ref": "ticket-001",
        },
    )
    result_text = json.dumps(
        _assert_draft_article_call_shape_invalid(
            {
                **_approved_summary_args(debug=True),
                "ticket_ref": "/mnt/user-data/uploads/sanitized_ticket_for_test.txt",
            }
        ),
        sort_keys=True,
    )
    assert "/mnt/user-data/uploads" not in result_text


def test_draft_article_uses_chat_summary_path() -> None:
    response = _call_author_approved_summary(_approved_summary_args(debug=True))

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "approved_summary_authoring"
    assert structured["pipeline_ok"] is True
    assert structured["ready_for_reviewer"] is True
    assert "reviewer_only_draft" in structured
    assert (
        '12377512781975-How-to-connect-to-a-Plesk-server-via-SSH">'
        "Connect to the Plesk server via SSH.</a></li>"
        in structured["reviewer_only_html"]
    )


def test_draft_article_rejects_top_level_structured_alias_fields() -> None:
    response = _call_tool(
        _initialized_transport(),
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {
            "applicable_to": [
                "Plesk with Advanced/360 Monitoring extension",
                "sw-collectd statistics collector",
            ],
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "case_ref": "example-simple",
            "confirmed_facts": [
                "The diagnostic summary references grafana.log.",
                "The collectd configuration file is not owned by any package.",
            ],
            "resolution_steps": [
                "Run rpm -qf /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf.",
                (
                    "Run cp -a /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf "
                    "/root/monitoring-case-backup/."
                ),
                (
                    "Run mv /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf "
                    "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf.disabled."
                ),
                "Run systemctl restart sw-collectd.",
                "Confirm new graph data appears.",
            ],
            "supported_cause": (
                "A leftover collectd configuration overrides the RRD data path."
            ),
            "supported_resolution_or_workaround": (
                "Disable the override and restart sw-collectd."
            ),
            "symptoms": [
                "Monitoring graphs show no data.",
                "The datasource lists metric names but returns no datapoints.",
            ],
            "title": (
                "Monitoring graphs show no data due to leftover collectd RRD "
                "path override"
            ),
        },
    )

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "input_validation"
    assert structured["debug_code"] == "draft_article_call_shape_invalid"
    assert "reviewer_only_html" not in structured
    assert "02rrdtool-monitoring.conf" not in result_text


def test_draft_article_skips_missing_reuse_search_for_mvp_draft() -> None:
    arguments = _approved_summary_args(debug=True)
    arguments.pop("reuse_search_checked")
    arguments.pop("reuse_search_run_ref")

    response = _call_author_approved_summary(arguments)

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "approved_summary_authoring"
    assert structured["pipeline_ok"] is True
    assert structured["failure_stage"] == "none"
    assert structured["debug_code"] == "none"
    assert structured["reuse_search_status"] == "skipped"
    assert structured["ready_for_reviewer"] is True
    assert structured["draft_request_ready"] is True
    assert "reviewer_only_html" in structured
    assert {"kind": "reuse_search_skipped", "severity": "warning"} in structured[
        "quality_gaps"
    ]


def test_draft_article_promotes_explicit_resolution_steps() -> None:
    arguments = _approved_summary_args(debug=True)
    assert isinstance(arguments["item"], dict)
    del arguments["item"]["supported_resolution_or_workaround"]

    response = _call_author_approved_summary(arguments)

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "approved_summary_authoring"
    assert structured["pipeline_ok"] is True
    assert structured["ready_for_reviewer"] is True
    assert "reviewer_only_html" in structured
    assert (
        '12377512781975-How-to-connect-to-a-Plesk-server-via-SSH">'
        "Connect to the Plesk server via SSH.</a></li>"
        in structured["reviewer_only_html"]
    )


def test_draft_article_accepts_common_admin_resolution_commands() -> None:
    arguments = _approved_summary_args(debug=True)
    assert isinstance(arguments["item"], dict)
    arguments["item"]["resolution_steps"] = [
        "Connect to the Plesk server via SSH.",
        "Run ls -ld /usr/local/psa/var/modules/monitoring/.",
        (
            "Run cat /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf "
            "to review the DataDir setting."
        ),
        (
            "Run chown psaadm:psaadm "
            "/usr/local/psa/var/modules/monitoring/."
        ),
        "Run chmod 0750 /usr/local/psa/var/modules/monitoring/.",
        "Run systemctl restart sw-collectd.",
        "Confirm Monitoring graphs show new data in the Plesk UI.",
    ]

    response = _call_author_approved_summary(arguments)

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "approved_summary_authoring"
    assert structured["pipeline_ok"] is True
    assert structured["ready_for_reviewer"] is True
    assert "reviewer_only_html" in structured
    assert (
        "<p>Review the <code>DataDir</code> setting:</p>\n"
        "      <p><code># cat "
        "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf</code></p>"
        in structured["reviewer_only_html"]
    )


def test_draft_article_accepts_mixed_concrete_resolution_procedure() -> None:
    arguments = _approved_summary_args(debug=True)
    assert isinstance(arguments["item"], dict)
    arguments["item"]["resolution_steps"] = [
        "Connect to the Plesk server via SSH.",
        (
            "Run rpm -qf /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf "
            "to confirm the file is not owned by a package."
        ),
        (
            "Run cat /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf "
            "to review the DataDir setting."
        ),
        "Move the conflicting file out of the active conf.d directory.",
        "Run systemctl restart sw-collectd.",
        "Confirm Monitoring graphs show new data in the Plesk UI.",
        (
            "Advise that historical data collected before the fix may not be "
            "visible because graphs repopulate gradually."
        ),
    ]

    response = _call_author_approved_summary(arguments)

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "approved_summary_authoring"
    assert structured["pipeline_ok"] is True
    assert structured["ready_for_reviewer"] is True
    assert "reviewer_only_html" in structured


def test_draft_article_accepts_final_informational_resolution_note() -> None:
    arguments = _approved_summary_args(debug=True)
    assert isinstance(arguments["item"], dict)
    arguments["item"]["resolution_steps"] = [
        "Connect to the Plesk server via SSH.",
        (
            "Run rpm -qf "
            "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf."
        ),
        (
            "Run cat /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf "
            "to review the DataDir setting."
        ),
        (
            "Run mv /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf "
            "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf.disabled."
        ),
        "Run systemctl restart sw-collectd.",
        "Confirm Monitoring graphs show new data in the Plesk UI.",
        (
            "Advise that historical data collected before the fix may not be "
            "visible because graphs repopulate gradually."
        ),
    ]

    response = _call_author_approved_summary(arguments)

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "approved_summary_authoring"
    assert structured["pipeline_ok"] is True
    assert structured["ready_for_reviewer"] is True
    assert "reviewer_only_html" in structured


def test_draft_article_accepts_angle_bracket_config_block_text() -> None:
    arguments = _approved_summary_args(debug=True)
    assert isinstance(arguments["item"], dict)
    arguments["item"]["resolution_steps"] = [
        (
            "Confirm the file contains a <Plugin rrdtool> block setting "
            "DataDir to a non-default path."
        ),
        "Run systemctl restart sw-collectd.",
    ]

    response = _call_author_approved_summary(arguments)

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "approved_summary_authoring"
    assert structured["pipeline_ok"] is True
    assert "tool_result_invalid" not in result_text
    assert (
        "Confirm the file contains a &lt;Plugin rrdtool&gt; block"
        in structured["reviewer_only_html"]
    )


def test_draft_article_requires_ticket_ref_or_summary() -> None:
    response = _call_tool(
        _initialized_transport(),
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"debug": True},
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "input_validation"
    assert structured["debug_code"] == "draft_article_call_shape_invalid"


def test_draft_article_primary_summary_blocks_when_provider_missing() -> None:
    response = _call_tool(
        _initialized_transport(
            adapter=KcsDesktopMcpAdapter(
                semantic_extraction_provider=None,
                visible_tools={TOOL_DRAFT_ARTICLE},
            )
        ),
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {
            "approved_summary_text": (
                "Approved sanitized summary: Monitoring graphs show no data."
            ),
            "debug": True,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "semantic_extraction"
    assert structured["debug_code"] == "semantic_extraction_provider_unavailable"
    assert structured["next_required_action"] == (
        "configure_semantic_extraction_provider"
    )
    assert structured["provider_calls"] is False
    assert "reviewer_only_html" not in structured
    result_output = response["result"]["content"][0]["text"]
    assert result_output.startswith("KCS article drafting is blocked")
    assert "approved semantic extraction provider is not configured" in result_output
    assert "do not write a fallback article" not in result_output
    assert "do not infer item/item_candidates" not in result_output


def test_draft_article_primary_summary_without_labels_has_no_candidates() -> None:
    response = _call_tool(
        _initialized_transport(
            adapter=KcsDesktopMcpAdapter(
                semantic_extraction_provider=FixtureSemanticExtractionProvider(),
                visible_tools={TOOL_DRAFT_ARTICLE},
            )
        ),
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {
            "approved_summary_text": (
                "Approved sanitized summary: Monitoring graphs show no data."
            ),
            "debug": True,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "semantic_extraction"
    assert structured["debug_code"] == "semantic_extraction_no_candidates"
    assert "reviewer_only_html" not in structured
    result_output = response["result"]["content"][0]["text"]
    assert result_output.startswith("KCS article drafting is blocked")
    assert "complete semantic KCS item" in result_output
    assert "Do not draft manually" in result_output
    assert "final symptom, supported cause, and resolution evidence" in result_output


def test_draft_article_primary_summary_rejects_embedded_tool_argument_markup() -> None:
    response = _call_tool(
        _initialized_transport(
            adapter=KcsDesktopMcpAdapter(
                semantic_extraction_provider=FixtureSemanticExtractionProvider(),
                visible_tools={TOOL_DRAFT_ARTICLE},
            )
        ),
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {
            "approved_summary_text": (
                "Customer Ticket Content\n"
                "Plesk Monitoring graphs show no data.\n"
                '<parameter name="debug">false'
            ),
            "debug": True,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    result_text = json.dumps(response, sort_keys=True)
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "input_validation"
    assert structured["debug_code"] == "draft_article_args_invalid"
    assert structured["writes_files"] is False
    assert "parameter" not in result_text


def test_draft_article_primary_fixture_provider_writes_bundle(tmp_path) -> None:
    bundle_root = tmp_path / "local-data" / "reviewer-bundles"
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=bundle_root,
            semantic_extraction_provider=FixtureSemanticExtractionProvider(),
            visible_tools={TOOL_DRAFT_ARTICLE},
        )
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"approved_summary_text": _labeled_summary()},
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    _assert_fixture_provider_bundle_draft_result(structured)
    _assert_fixture_provider_bundle_artifacts(response, bundle_root, structured)


def _assert_fixture_provider_bundle_draft_result(
    structured: Mapping[str, Any],
) -> None:
    expected_fields = {
        "result_kind": "draft_article_authoring",
        "draft_generated": True,
        "debug_code": "draft_only_reuse_search_missing",
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "kcs_ready": False,
        "recommended_action": "draft_only",
        "reuse_search_status": "skipped",
        "writes_files": True,
    }
    for field, expected_value in expected_fields.items():
        assert structured[field] == expected_value
    assert structured["html_path"].startswith("local-data/reviewer-bundles/")
    assert "reviewer_only_html" not in structured


def _assert_fixture_provider_bundle_artifacts(
    response: Mapping[str, Any],
    bundle_root: Path,
    structured: Mapping[str, Any],
) -> None:
    html_path = bundle_root / structured["bundle_ref"] / "candidate-001" / (
        "reviewer_only.html"
    )
    html = html_path.read_text(encoding="utf-8")
    result_output = _tool_text(response)
    assert "<h2>Resolution</h2>" in html
    assert not result_output.startswith("```html\n")
    _assert_text_includes(
        result_output,
        (
            "Reviewer-only KCS draft generated",
            "do not claim the file is unavailable from this chat",
            "do not offer a separate chat-authored article",
            "html_path",
        ),
    )
    _assert_text_excludes(
        result_output,
        (
            "Do not rewrite it into a Markdown article",
            "COPY THE FINAL RESPONSE BELOW VERBATIM",
        ),
    )


def test_draft_article_primary_fixture_provider_supports_narrative_summary(
    tmp_path,
) -> None:
    bundle_root = tmp_path / "local-data" / "reviewer-bundles"
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=bundle_root,
            semantic_extraction_provider=FixtureSemanticExtractionProvider(),
            visible_tools={TOOL_DRAFT_ARTICLE},
        )
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"approved_summary_text": _narrative_monitoring_summary(), "debug": True},
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["draft_generated"] is True
    assert structured["debug_code"] == "draft_only_reuse_search_missing"
    assert structured["article_type"] == ArticleType.TECHNICAL_SCR.value
    assert structured["reuse_search_status"] == "skipped"
    assert structured["kcs_ready"] is False
    blocker_gap_kinds = {
        gap["kind"]
        for gap in structured["quality_gaps"]
        if gap.get("severity") == "blocker"
    }
    assert blocker_gap_kinds == set()
    html = _tool_html_resource_text(response)
    assert "<li>Plesk for Linux</li>" in html
    assert (
        '12377512781975-How-to-connect-to-a-Plesk-server-via-SSH">'
        "Connect to the Plesk server via SSH.</a></li>"
    ) in html
    assert "systemctl restart sw-collectd" in html
    html_path = bundle_root / structured["bundle_ref"] / "candidate-001" / (
        "reviewer_only.html"
    )
    assert html_path.read_text(encoding="utf-8") in html


def test_draft_article_primary_fixture_provider_supports_compact_summary(
    tmp_path,
) -> None:
    bundle_root = tmp_path / "local-data" / "reviewer-bundles"
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=bundle_root,
            semantic_extraction_provider=FixtureSemanticExtractionProvider(),
            visible_tools={TOOL_DRAFT_ARTICLE},
        )
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"approved_summary_text": _compact_monitoring_summary(), "debug": True},
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["draft_generated"] is True
    assert structured["debug_code"] == "draft_only_reuse_search_missing"
    assert structured["article_type"] == ArticleType.TECHNICAL_SCR.value
    html = _tool_html_resource_text(response)
    assert "<li>Plesk for Linux</li>" in html
    assert "systemctl restart sw-collectd" in html
    assert "Monitoring graphs show no data" in html


def test_draft_article_primary_fixture_provider_supports_raw_ticket_summary(
    tmp_path,
) -> None:
    bundle_root = tmp_path / "local-data" / "reviewer-bundles"
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=bundle_root,
            semantic_extraction_provider=FixtureSemanticExtractionProvider(),
            visible_tools={TOOL_DRAFT_ARTICLE},
        )
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"approved_summary_text": _raw_monitoring_ticket_summary(), "debug": True},
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    _assert_raw_ticket_fixture_provider_draft_result(structured)
    html = _tool_html_resource_text(response)
    _assert_raw_ticket_fixture_provider_html(html)


def _assert_raw_ticket_fixture_provider_draft_result(
    structured: Mapping[str, Any],
) -> None:
    expected_fields = {
        "result_kind": "draft_article_authoring",
        "draft_generated": True,
        "debug_code": "draft_only_reuse_search_missing",
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "reuse_search_status": "skipped",
        "kcs_ready": False,
    }
    for field, expected_value in expected_fields.items():
        assert structured[field] == expected_value
    blocker_gap_kinds = {
        gap["kind"]
        for gap in structured["quality_gaps"]
        if gap.get("severity") == "blocker"
    }
    assert blocker_gap_kinds == set()


def _assert_raw_ticket_fixture_provider_html(html: str) -> None:
    _assert_text_includes(
        html,
        (
            "<li>Plesk for Linux</li>",
            "<h2>Cause</h2>",
            (
                "The collectd configuration file "
                "<code>/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf</code> "
                "pointed Monitoring metric data to a location that the Plesk "
                "Monitoring backend does not query."
            ),
            (
                '12377512781975-How-to-connect-to-a-Plesk-server-via-SSH">'
                "Connect to the Plesk server via SSH.</a></li>"
            ),
            (
                "<p>Back up the custom collectd configuration file:</p>\n"
                "      <p><code># cp -a "
                "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf "
                "/root/monitoring-case-backup/</code></p>"
            ),
            (
                "<p>Disable the custom collectd configuration file:</p>\n"
                "      <p><code># mv "
                "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf "
                "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf.disabled"
                "</code></p>"
            ),
            "systemctl restart sw-collectd",
        ),
    )
    _assert_text_excludes(html, ("PERSON_NAME", "SHELL_USERHOST"))


def test_draft_article_primary_local_provider_uses_final_fix_not_diagnostics(
    tmp_path,
) -> None:
    bundle_root = tmp_path / "local-data" / "reviewer-bundles"
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=bundle_root,
            semantic_extraction_provider=ApprovedSummarySemanticExtractionProvider(),
            visible_tools={TOOL_DRAFT_ARTICLE},
        )
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {
            "approved_summary_text": (
                "# Customer Ticket Content\n\n"
                "When loading the monitoring module in Plesk, none of the graphs "
                "show any data.\n"
                "logger=example level=error msg=\"plugin process exited\" "
                "plugin=/var/lib/grafana/plugins/plesk-json-backend-datasource/"
                "dist/bin error=\"signal: terminated\"\n"
                "[root@server modules]# ls -ld /var/lib/grafana/\n"
                "drwxrwxr-x 3 root root 18 Jun 17 2021 "
                "plesk-json-backend-datasource grafana:grafana 750 Disabled\n"
                "Test server\n"
                "file /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf is not "
                "owned by any package\n"
                "DataDir \"/usr/local/psa/var/modules/monitoring/rrd\"\n"
                "Root cause: leftover/custom unowned collectd override caused "
                "RRD files to be written to a path that Monitoring backend does "
                "not query correctly.\n"
                "I backed up and disabled the incorrect configuration file "
                "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf, restarted "
                "the statistics collector, and confirmed that new metric data "
                "is now being written to the expected location. The Monitoring "
                "graphs have started displaying data again.\n"
                "systemctl restart sw-collectd\n"
            ),
            "debug": True,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["debug_code"] == "draft_only_reuse_search_missing"
    assert structured["draft_generated"] is True
    html = _tool_html_resource_text(response)
    assert (
        "<h1>Monitoring graphs show no data in Plesk: custom unowned "
        "collectd configuration file</h1>"
    ) in html
    assert "Plesk Monitoring graphs show no data." in html
    assert "02rrdtool-monitoring.conf" in html
    assert (
        "<p>Restart <code>sw-collectd</code>:</p>\n"
        "      <p><code># systemctl restart sw-collectd</code></p>"
        in html
    )
    assert "Connect to the Plesk server via SSH" in html
    assert "plugin process exited" not in html
    assert "drwxrwxr-x" not in html
    assert "Test server" not in html
    assert "ls -ld" not in html


def test_draft_article_primary_fixture_provider_supports_live_raw_ticket_shape(
    tmp_path,
) -> None:
    bundle_root = tmp_path / "local-data" / "reviewer-bundles"
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=bundle_root,
            semantic_extraction_provider=FixtureSemanticExtractionProvider(),
            visible_tools={TOOL_DRAFT_ARTICLE},
        )
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {
            "approved_summary_text": (
                _raw_monitoring_ticket_without_explicit_fix_verbs()
            ),
            "debug": True,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["debug_code"] == "draft_only_reuse_search_missing"
    assert structured["draft_generated"] is True
    assert structured["article_type"] == ArticleType.TECHNICAL_SCR.value
    assert structured["reuse_search_status"] == "skipped"
    assert structured["kcs_ready"] is False
    html = _tool_html_resource_text(response)
    assert "<li>Plesk for Linux</li>" in html
    assert (
        '12377512781975-How-to-connect-to-a-Plesk-server-via-SSH">'
        "Connect to the Plesk server via SSH.</a></li>"
    ) in html
    assert (
        "<p>Back up the custom collectd configuration file:</p>\n"
        "      <p><code># cp -a "
        "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf "
        "/root/monitoring-case-backup/</code></p>"
    ) in html
    assert (
        "<p>Disable the custom collectd configuration file:</p>\n"
        "      <p><code># mv "
        "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf "
        "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf.disabled</code></p>"
    ) in html
    assert "systemctl restart sw-collectd" in html


def test_draft_article_primary_debug_includes_reviewer_only_html(tmp_path) -> None:
    bundle_root = tmp_path / "local-data" / "reviewer-bundles"
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=bundle_root,
            semantic_extraction_provider=FixtureSemanticExtractionProvider(),
            visible_tools={TOOL_DRAFT_ARTICLE},
        )
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"approved_summary_text": _labeled_summary(), "debug": True},
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["draft_generated"] is True
    assert "reviewer_only_html" not in structured
    html = _tool_html_resource_text(response)
    assert "<h2>Resolution</h2>" in html
    assert (
        '12377512781975-How-to-connect-to-a-Plesk-server-via-SSH">'
        "Connect to the Plesk server via SSH.</a></li>"
    ) in html
    html_path = bundle_root / structured["bundle_ref"] / "candidate-001" / (
        "reviewer_only.html"
    )
    assert html_path.read_text(encoding="utf-8") in html


def test_draft_article_primary_debug_links_windows_rdp_step(tmp_path) -> None:
    bundle_root = tmp_path / "local-data" / "reviewer-bundles"
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=bundle_root,
            semantic_extraction_provider=FixtureSemanticExtractionProvider(),
            visible_tools={TOOL_DRAFT_ARTICLE},
        )
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"approved_summary_text": _windows_labeled_summary(), "debug": True},
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["draft_generated"] is True
    assert "reviewer_only_html" not in structured
    html = _tool_html_resource_text(response)
    assert "<li>Plesk for Windows</li>" in html
    assert (
        '12377247797271-How-to-connect-to-a-Plesk-server-via-RDP-with-'
        'available-credentials">Connect to the Plesk server via RDP.</a></li>'
    ) in html


def test_draft_article_primary_fixture_provider_supports_howto_qa(tmp_path) -> None:
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles",
            semantic_extraction_provider=FixtureSemanticExtractionProvider(),
            visible_tools={TOOL_DRAFT_ARTICLE},
        )
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"approved_summary_text": _howto_labeled_summary(), "debug": True},
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["draft_generated"] is True
    assert structured["article_type"] == ArticleType.HOWTO_QA.value
    assert structured["debug_code"] == "draft_only_reuse_search_missing"
    assert "reviewer_only_html" not in structured
    html = _tool_html_resource_text(response)
    assert "<h2>Question</h2>" in html
    assert "<h2>Answer</h2>" in html
    assert "break-fix" not in json.dumps(structured, sort_keys=True)


def test_draft_article_primary_fixture_provider_splits_items(tmp_path) -> None:
    bundle_root = tmp_path / "local-data" / "reviewer-bundles"
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=bundle_root,
            semantic_extraction_provider=FixtureSemanticExtractionProvider(),
            visible_tools={TOOL_DRAFT_ARTICLE},
        )
    )

    split_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"approved_summary_text": _multi_item_labeled_summary()},
    )

    assert split_response is not None
    split = split_response["result"]["structuredContent"]
    assert split_response["result"]["isError"] is False
    _assert_fixture_provider_split_required(split)

    selected_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {
            "debug": True,
            "operator_selected_item_ref": "candidate-002",
            "operator_selection_ref": split["operator_selection_ref"],
        },
    )

    assert selected_response is not None
    structured = selected_response["result"]["structuredContent"]
    assert selected_response["result"]["isError"] is False
    _assert_fixture_provider_selected_candidate_draft(selected_response, structured)


def test_draft_article_primary_native_all_option_executes_exact_batch(
    tmp_path,
) -> None:
    bundle_root = tmp_path / "local-data" / "reviewer-bundles"
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=bundle_root,
            semantic_extraction_provider=FixtureSemanticExtractionProvider(),
            visible_tools={TOOL_DRAFT_ARTICLE},
        )
    )
    split_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"approved_summary_text": _multi_item_labeled_summary()},
    )

    assert split_response is not None
    split = split_response["result"]["structuredContent"]
    all_option = split["operator_choice_request"]["options"][-1]
    assert all_option == {
        "label": "All candidates",
        "submit_arguments": {
            "operator_selected_item_refs": ["candidate-001", "candidate-002"],
            "operator_selection_ref": split["operator_selection_ref"],
        },
        "value": "all",
    }
    assert "operator_all_submit_arguments" not in split
    assert "all_submit_arguments" not in split["operator_choice_request"]

    batch_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        all_option["submit_arguments"],
    )

    assert batch_response is not None
    structured = batch_response["result"]["structuredContent"]
    assert structured["result_kind"] == "draft_article_batch"
    assert structured.get("debug_code") != "draft_article_args_invalid"
    assert [
        outcome["item_ref"] for outcome in structured["candidate_outcomes"]
    ] == ["candidate-001", "candidate-002"]


def _assert_fixture_provider_split_required(split: Mapping[str, Any]) -> None:
    assert split["debug_code"] == "multiple_kcs_items_detected"
    assert split["recommended_action"] == "split_required"
    assert split["operator_prompt_style"] == "native_choice_popup"
    assert split["operator_selection_ref"].startswith("operator-selection-")
    assert split["operator_choice_request"]["mode"] == "single_or_batch_select"
    assert split["operator_choice_request"]["prose_only_choice_allowed"] is False
    assert split["operator_choice_request"]["manual_draft_allowed"] is False
    assert split["operator_choice_request"]["automatic_item_retry_allowed"] is False
    assert split["operator_choice_request"]["submit_tool"] == "kcs_draft_article"
    assert split["operator_choice_request"]["options"][0]["submit_arguments"] == {
        "operator_selected_item_ref": "candidate-001",
        "operator_selection_ref": split["operator_selection_ref"],
    }
    assert split["operator_choice_submit_options"] == split[
        "operator_choice_request"
    ]["options"]
    assert "operator_all_submit_arguments" not in split
    assert "all_submit_arguments" not in split["operator_choice_request"]
    assert split["item_candidates"] == [
        {
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "candidate_origin": "customer_reported",
            "item_ref": "candidate-001",
            "title": (
                "Monitoring graphs show no data in Plesk due to custom "
                "collectd RRD data directory"
            ),
        },
        {
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "candidate_origin": "customer_reported",
            "item_ref": "candidate-002",
            "title": "Monitoring extension post-install fails",
        },
    ]
    assert "reviewer_only_html" not in split


def _assert_fixture_provider_selected_candidate_draft(
    selected_response: Mapping[str, Any],
    structured: Mapping[str, Any],
) -> None:
    assert structured["draft_generated"] is True
    assert structured["item_ref"] == "candidate-002"
    assert "reviewer_only_html" not in structured
    assert "Monitoring extension post-install fails" in _tool_html_resource_text(
        selected_response
    )


def test_draft_article_primary_summary_uses_provider_for_split_required() -> None:
    provider = _FakeSemanticExtractionProvider(
        [
            _semantic_candidate(
                item_ref="candidate-001",
                reason="Monitoring graphs have no datapoints.",
                title="Monitoring graphs show no data",
            ),
            _semantic_candidate(
                item_ref="candidate-002",
                reason="Extension post-install fails with permissions.",
                title="Monitoring extension post-install fails",
            ),
        ]
    )
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            semantic_extraction_provider=provider,
            visible_tools={TOOL_DRAFT_ARTICLE},
        )
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {
            "approved_summary_text": (
                "Approved sanitized summary: one issue affects monitoring graphs "
                "and another independent issue affects extension installation."
            ),
            "debug": True,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    _assert_provider_called_once_for_split_required(provider)
    _assert_primary_provider_split_required(structured)


def _assert_provider_called_once_for_split_required(
    provider: _FakeSemanticExtractionProvider,
) -> None:
    assert provider.calls == [
        (
            "Approved sanitized summary: one issue affects monitoring graphs "
            "and another independent issue affects extension installation."
        )
    ]


def _assert_primary_provider_split_required(structured: Mapping[str, Any]) -> None:
    expected_fields = {
        "result_kind": "draft_article_authoring",
        "pipeline_ok": False,
        "failure_stage": "item_identification",
        "debug_code": "multiple_kcs_items_detected",
        "recommended_action": "split_required",
        "operator_prompt_style": "native_choice_popup",
    }
    for field, expected_value in expected_fields.items():
        assert structured[field] == expected_value
    assert structured["operator_selection_ref"].startswith("operator-selection-")
    assert structured["operator_choice_options"] == structured[
        "operator_choice_request"
    ]["options"]
    assert (
        structured["operator_choice_request"]["mode"]
        == "single_or_batch_select"
    )
    assert structured["operator_choice_request"]["submit_tool"] == "kcs_draft_article"
    assert structured["operator_choice_request"]["options"][1]["submit_arguments"] == {
        "operator_selected_item_ref": "candidate-002",
        "operator_selection_ref": structured["operator_selection_ref"],
    }
    assert structured["operator_choice_submit_options"] == structured[
        "operator_choice_request"
    ]["options"]
    assert "operator_all_submit_arguments" not in structured
    assert "all_submit_arguments" not in structured["operator_choice_request"]
    assert structured["item_candidates"] == [
        {
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "candidate_origin": "customer_reported",
            "item_ref": "candidate-001",
            "title": "Monitoring graphs show no data",
        },
        {
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "candidate_origin": "customer_reported",
            "item_ref": "candidate-002",
            "title": "Monitoring extension post-install fails",
        },
    ]
    assert "reviewer_only_html" not in structured


def test_draft_article_primary_selection_uses_pending_provider_candidate(
    tmp_path,
) -> None:
    bundle_root = tmp_path / "local-data" / "reviewer-bundles"
    provider = _two_item_monitoring_provider()
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=bundle_root,
            semantic_extraction_provider=provider,
            visible_tools={TOOL_DRAFT_ARTICLE},
        )
    )
    split_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {
            "approved_summary_text": (
                "Approved sanitized summary: one issue affects monitoring graphs "
                "and another independent issue affects extension installation."
            )
        },
    )
    assert split_response is not None
    split = split_response["result"]["structuredContent"]

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {
            "operator_selected_item_ref": "candidate-001",
            "operator_selection_ref": split["operator_selection_ref"],
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    _assert_first_selected_provider_candidate_draft(structured, split)
    assert "reviewer_only_html" not in structured
    _assert_first_selected_provider_candidate_bundle(bundle_root, structured)

    second_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {
            "operator_selected_item_ref": "candidate-002",
            "operator_selection_ref": split["operator_selection_ref"],
        },
    )

    assert second_response is not None
    second = second_response["result"]["structuredContent"]
    assert second_response["result"]["isError"] is False
    _assert_second_selected_provider_candidate_bundle(bundle_root, second)


def _two_item_monitoring_provider() -> _FakeSemanticExtractionProvider:
    return _FakeSemanticExtractionProvider(
        [
            _semantic_candidate(
                item_ref="candidate-001",
                reason="Monitoring graphs have no datapoints.",
                title="Monitoring graphs show no data",
            ),
            _semantic_candidate(
                item_ref="candidate-002",
                reason="Extension post-install fails with permissions.",
                title="Monitoring extension post-install fails",
            ),
        ]
    )


def _assert_first_selected_provider_candidate_draft(
    structured: Mapping[str, Any],
    split: Mapping[str, Any],
) -> None:
    expected_fields = {
        "result_kind": "draft_article_authoring",
        "draft_generated": True,
        "pipeline_ok": False,
        "debug_code": "draft_only_reuse_search_missing",
        "item_ref": "candidate-001",
        "kcs_ready": False,
        "ready_for_reviewer": False,
        "recommended_action": "draft_only",
        "reuse_search_status": "skipped",
        "reviewer_bundle_written": True,
    }
    for field, expected_value in expected_fields.items():
        assert structured[field] == expected_value
    assert structured["html_path"].startswith("local-data/reviewer-bundles/")
    assert structured["manifest_path"].startswith("local-data/reviewer-bundles/")
    assert structured["remaining_selection_ref"] == split["operator_selection_ref"]
    assert structured["remaining_item_candidates"] == [
        {
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "candidate_origin": "customer_reported",
            "item_ref": "candidate-002",
            "title": "Monitoring extension post-install fails",
        }
    ]
    assert structured["next_tool"] == "kcs_draft_article"
    assert structured["next_arguments"] == {
        "operator_selected_item_ref": "candidate-002",
        "operator_selection_ref": split["operator_selection_ref"],
    }


def _assert_first_selected_provider_candidate_bundle(
    bundle_root: Path,
    structured: Mapping[str, Any],
) -> None:
    html_path = bundle_root / structured["bundle_ref"] / "candidate-001" / (
        "reviewer_only.html"
    )
    manifest_path = bundle_root / structured["bundle_ref"] / "manifest.json"
    assert html_path.is_file()
    assert "<h2>Resolution</h2>" in html_path.read_text(encoding="utf-8")
    assert manifest_path.is_file()
    assert sha256(html_path.read_bytes()).hexdigest() == structured["html_sha256"]


def _assert_second_selected_provider_candidate_bundle(
    bundle_root: Path,
    second: Mapping[str, Any],
) -> None:
    assert second["draft_generated"] is True
    assert second["item_ref"] == "candidate-002"
    assert "remaining_selection_ref" not in second
    second_html_path = bundle_root / second["bundle_ref"] / "candidate-002" / (
        "reviewer_only.html"
    )
    assert second_html_path.is_file()
    assert "Monitoring extension post-install fails" in second_html_path.read_text(
        encoding="utf-8",
    )


def test_draft_article_primary_summary_continues_for_single_candidate(tmp_path) -> None:
    bundle_root = tmp_path / "local-data" / "reviewer-bundles"
    provider = _FakeSemanticExtractionProvider(
        [
            _semantic_candidate(
                item_ref="candidate-001",
                title="Monitoring graphs show no data",
            )
        ]
    )
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=bundle_root,
            semantic_extraction_provider=provider,
            visible_tools={TOOL_DRAFT_ARTICLE},
        )
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {
            "approved_summary_text": (
                "Approved sanitized summary: product monitoring graphs show no data. "
                "The summary references service.log and service.conf."
            )
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["draft_generated"] is True
    assert structured["pipeline_ok"] is False
    assert structured["debug_code"] == "draft_only_reuse_search_missing"
    assert structured["item_ref"] == "candidate-001"
    assert structured["reuse_search_status"] == "skipped"
    assert structured["kcs_ready"] is False
    assert structured["ready_for_reviewer"] is False
    assert structured["reviewer_bundle_written"] is True
    assert "reviewer_only_html" not in structured
    html_path = (
        bundle_root
        / structured["bundle_ref"]
        / "candidate-001"
        / "reviewer_only.html"
    )
    assert html_path.is_file()
    assert "<h2>Resolution</h2>" in html_path.read_text(encoding="utf-8")


def test_draft_article_primary_reviewable_quality_debt_writes_local_bundle(
    tmp_path,
) -> None:
    bundle_root = tmp_path / "local-data" / "reviewer-bundles"
    provider = _FakeSemanticExtractionProvider(
        [
            _semantic_candidate(
                item_ref="candidate-001",
                supported_cause=(
                    "Run systemctl restart sw-collectd to restore Monitoring "
                    "graphs."
                ),
                title="Monitoring graphs show no data",
            )
        ]
    )
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=bundle_root,
            semantic_extraction_provider=provider,
            visible_tools={TOOL_DRAFT_ARTICLE},
        )
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {
            "approved_summary_text": (
                "Approved sanitized summary: product monitoring graphs show no data."
            ),
            "debug": True,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["pipeline_ok"] is False
    assert structured["debug_code"] == "draft_only_quality_gaps"
    assert structured["draft_generated"] is True
    assert structured["reviewer_bundle_written"] is True
    assert structured["writes_files"] is True
    assert structured["kcs_ready"] is False
    assert structured["ready_for_reviewer"] is False
    assert structured["public_output_approved"] is False
    assert "reviewer_only_html" not in structured
    assert "html_path" in structured
    assert "cause_contains_resolution_action" in structured["blockers"]
    assert len(list(bundle_root.glob("run-*/candidate-001/reviewer_only.html"))) == 1


def test_draft_article_primary_selection_expires_pending_choice() -> None:
    provider = _FakeSemanticExtractionProvider(
        [
            _semantic_candidate(item_ref="candidate-001"),
            _semantic_candidate(item_ref="candidate-002", title="Second issue"),
        ]
    )
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            semantic_extraction_provider=provider,
            selection_ttl_seconds=0,
            visible_tools={TOOL_DRAFT_ARTICLE},
        )
    )
    split_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"approved_summary_text": "Approved sanitized summary: two issues."},
    )
    assert split_response is not None
    split = split_response["result"]["structuredContent"]

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {
            "operator_selected_item_ref": "candidate-001",
            "operator_selection_ref": split["operator_selection_ref"],
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "operator_selection"
    assert structured["debug_code"] == "operator_selection_expired"
    assert structured["next_required_action"] == "restart_with_approved_summary_text"
    assert "reviewer_only_html" not in structured


def test_draft_article_primary_provider_output_invalid_is_controlled() -> None:
    provider = _FakeSemanticExtractionProvider(
        [
            _semantic_candidate(
                item_ref="candidate-001",
                title="Private person@example.com must not echo",
            )
        ]
    )
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            semantic_extraction_provider=provider,
            visible_tools={TOOL_DRAFT_ARTICLE},
        )
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"approved_summary_text": "Approved sanitized summary: safe input."},
    )

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "semantic_extraction"
    assert structured["debug_code"] == "semantic_extraction_output_invalid"
    assert "person@example.com" not in result_text
    assert "reviewer_only_html" not in structured


def test_draft_article_primary_selection_without_state_is_controlled() -> None:
    response = _call_tool(
        _initialized_transport(),
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {
            "debug": True,
            "operator_selected_item_ref": "candidate-001",
            "operator_selection_ref": "selection-opaque",
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "operator_selection"
    assert structured["debug_code"] == "operator_selection_invalid"
    assert structured["next_required_action"] == "restart_with_approved_summary_text"
    assert "reviewer_only_html" not in structured


def test_draft_article_primary_rejects_mixed_call_shape() -> None:
    response = _call_tool(
        _initialized_transport(),
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {
            "approved_summary_text": "Approved sanitized summary.",
            "operator_selected_item_ref": "candidate-001",
            "operator_selection_ref": "selection-opaque",
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "input_validation"
    assert structured["debug_code"] == "draft_article_call_shape_invalid"
    assert "reviewer_only_html" not in structured


@pytest.mark.parametrize(
    "arguments",
    [
        {"debug": True, "operator_selection_ref": "selection-opaque"},
        {"debug": True, "operator_selected_item_ref": "candidate-001"},
    ],
)
def test_draft_article_primary_rejects_partial_selection_shape(
    arguments: dict[str, object],
) -> None:
    response = _call_tool(
        _initialized_transport(),
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        arguments,
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "input_validation"
    assert structured["debug_code"] == "draft_article_call_shape_invalid"
    assert "reviewer_only_html" not in structured


def test_draft_article_returns_split_required_for_multiple_item_candidates() -> None:
    structured = _assert_draft_article_call_shape_invalid(
        {
            "approved_summary_text": (
                "Approved sanitized summary: one issue affects monitoring graphs "
                "and another independent issue affects extension installation."
            ),
            "debug": True,
            "item_candidates": [
                {
                    "item_ref": "candidate-001",
                    "reason": "Monitoring graphs have no datapoints.",
                    "title": "Monitoring graphs show no data",
                },
                {
                    "item_ref": "candidate-002",
                    "reason": "Extension post-install fails with permissions.",
                    "title": "Monitoring extension post-install fails",
                },
            ],
            "reuse_search_checked": True,
            "reuse_search_run_ref": "reuse-search-001",
        },
    )

    assert "operator_selection_ref" not in structured
    assert "item_candidates" not in structured


def test_draft_article_blocks_single_item_retry_until_operator_selects() -> None:
    structured = _assert_draft_article_call_shape_invalid(
        {
            "approved_summary_text": (
                "Approved sanitized summary: one issue affects monitoring graphs "
                "and another independent issue affects extension installation."
            ),
            "item_candidates": [
                {
                    "item_ref": "candidate-001",
                    "reason": "Monitoring graphs have no datapoints.",
                    "title": "Monitoring graphs show no data",
                },
                {
                    "item_ref": "candidate-002",
                    "reason": "Extension post-install fails with permissions.",
                    "title": "Monitoring extension post-install fails",
                },
            ],
        },
    )
    assert "operator_selection_ref" not in structured


def test_draft_article_allows_single_item_after_operator_selection() -> None:
    _assert_draft_article_call_shape_invalid(
        {
            "approved_summary_text": (
                "Approved sanitized summary: one issue affects monitoring graphs "
                "and another independent issue affects extension installation."
            ),
            "item_candidates": [
                {
                    "item_ref": "candidate-001",
                    "reason": "Monitoring graphs have no datapoints.",
                    "title": "Monitoring graphs show no data",
                },
                {
                    "item_ref": "candidate-002",
                    "reason": "Extension post-install fails with permissions.",
                    "title": "Monitoring extension post-install fails",
                },
            ],
        },
    )


def test_draft_article_accepts_selected_item_with_repeated_candidates() -> None:
    item_candidates = [
        {
            "item_ref": "candidate-001",
            "reason": "Monitoring graphs have no datapoints.",
            "title": "Monitoring graphs show no data",
        },
        {
            "item_ref": "candidate-002",
            "reason": "Extension post-install fails with permissions.",
            "title": "Monitoring extension post-install fails",
        },
    ]
    _assert_draft_article_call_shape_invalid(
        {
            "approved_summary_text": (
                "Approved sanitized summary: one issue affects monitoring graphs "
                "and another independent issue affects extension installation."
            ),
            "item_candidates": item_candidates,
        },
    )


def test_draft_article_rejects_unknown_fields_after_item_metadata_cleanup() -> None:
    arguments = _approved_summary_args(debug=True)
    assert isinstance(arguments["item"], dict)
    arguments["item"]["item_ref"] = "candidate-001"
    arguments["item"]["reason"] = "Copied candidate card metadata."
    arguments["item"]["unexpected_candidate_field"] = "must still fail"

    _assert_draft_article_call_shape_invalid(arguments)


def test_draft_article_accepts_environment_applicable_to_alias() -> None:
    arguments = _approved_summary_args(debug=True)
    assert isinstance(arguments["item"], dict)
    arguments["item"]["applicable_to"] = "Plesk for Linux"
    arguments["item"]["environment"] = {
        "applicable_to": "Plesk for Linux",
        "component": "Advanced Monitoring",
        "product": "Plesk",
    }

    response = _call_author_approved_summary(arguments)

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "approved_summary_authoring"
    assert structured["pipeline_ok"] is True
    assert structured["debug_code"] == "none"
    assert structured["ready_for_reviewer"] is True
    assert "<li>Plesk for Linux</li>" in structured["reviewer_only_html"]


def test_draft_article_accepts_structured_item_without_top_level_summary() -> None:
    arguments = _approved_summary_args(debug=True)
    arguments.pop("approved_summary_text")

    response = _call_author_approved_summary(arguments)

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "approved_summary_authoring"
    assert structured["pipeline_ok"] is True
    assert structured["debug_code"] == "none"
    assert "reviewer_only_html" in structured


def test_draft_article_accepts_safe_backup_filename_resolution_step() -> None:
    response = _call_author_approved_summary(
        _approved_summary_args(
            approved_summary_text=(
                "Approved sanitized summary: extension post-install fails because "
                "a module directory is owned by root:root instead of psaadm:psaadm. "
                "The supported workaround is to move the directory aside as "
                "monitoring.bak, reinstall the extension, and confirm ownership."
            ),
            item={
                "confirmed_facts": [
                    (
                        "/usr/local/psa/var/modules/monitoring/ is owned by "
                        "root:root instead of psaadm:psaadm."
                    ),
                    "A comparison server has the directory owned by psaadm:psaadm.",
                ],
                "resolution_steps": [
                    (
                        "Run ls -ld /usr/local/psa/var/modules/monitoring/ "
                        "to confirm the owner is root:root."
                    ),
                    (
                        "Move the directory aside before reinstalling: mv "
                        "/usr/local/psa/var/modules/monitoring/ "
                        "/usr/local/psa/var/modules/monitoring.bak"
                    ),
                    "Reinstall the monitoring extension from Plesk Extensions.",
                    (
                        "Run ls -ld /usr/local/psa/var/modules/monitoring/ "
                        "again and confirm psaadm:psaadm ownership."
                    ),
                ],
                "supported_cause": (
                    "The module directory is owned by root instead of psaadm, "
                    "so post-install cannot write into it."
                ),
                "supported_resolution_or_workaround": (
                    "Move the incorrectly owned directory aside and reinstall "
                    "the extension so the directory is recreated with correct "
                    "ownership."
                ),
                "symptoms": [
                    "Monitoring extension post-install fails with Permission denied.",
                ],
                "title": (
                    "Monitoring extension post-install fails due to wrong "
                    "directory ownership"
                ),
            },
        ),
    )

    assert response is not None
    assert response["result"]["isError"] is False
    structured = response["result"]["structuredContent"]
    assert structured["pipeline_ok"] is True
    assert structured["debug_code"] == "none"
    assert "reviewer_only_html" in structured
    assert "monitoring.bak" in structured["reviewer_only_html"]


def test_draft_article_split_required_returns_compact_candidate_cards() -> None:
    structured = _assert_draft_article_call_shape_invalid(
        {
            "approved_summary_text": (
                "Approved sanitized summary: one issue affects monitoring graphs "
                "and another independent issue affects extension installation."
            ),
            "item_candidates": [
                {
                    "article_type": ArticleType.TECHNICAL_SCR.value,
                    "confirmed_facts": [
                        "The candidate references service.log.",
                        "The candidate references application.ini.",
                    ],
                    "item_ref": "candidate-001",
                    "reason": "Monitoring graphs have no datapoints.",
                    "resolution_steps": [
                        (
                            "Run rpm -qf "
                            "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf."
                        ),
                        (
                            "Run mv /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf "
                            "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf.disabled."
                        ),
                        "Run systemctl restart sw-collectd.",
                    ],
                    "supported_cause": (
                        "A leftover collector config redirects metric data."
                    ),
                    "supported_resolution_or_workaround": (
                        "Disable the override and restart the collector."
                    ),
                    "symptoms": [
                        "Monitoring graphs show no data.",
                    ],
                    "title": "Monitoring graphs show no data",
                },
                {
                    "article_type": ArticleType.TECHNICAL_SCR.value,
                    "confirmed_facts": [
                        "The candidate references post-install.php.",
                    ],
                    "item_ref": "candidate-002",
                    "reason": "Extension post-install fails with permissions.",
                    "resolution_steps": [
                        (
                            "Confirm /usr/local/psa/var/modules/monitoring/ "
                            "ownership."
                        ),
                        "Reinstall the monitoring extension.",
                    ],
                    "supported_cause": (
                        "A module directory has incorrect ownership."
                    ),
                    "supported_resolution_or_workaround": (
                        "Recreate the directory with correct ownership."
                    ),
                    "symptoms": [
                        "Monitoring extension post-install fails.",
                    ],
                    "title": "Monitoring extension post-install fails",
                },
            ],
            "reuse_search_checked": True,
            "reuse_search_run_ref": "reuse-search-001",
        },
    )

    text = json.dumps(structured, sort_keys=True)
    assert "item_candidates" not in structured
    assert "resolution_steps" not in text
    assert "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf" not in text
    assert "/usr/local/psa/var/modules/monitoring/" not in text
    assert "tool_result_invalid" not in text


def test_draft_article_split_required_omits_unsafe_candidate_reason() -> None:
    structured = _assert_draft_article_call_shape_invalid(
        {
            "approved_summary_text": (
                "Approved sanitized summary: one issue affects monitoring graphs "
                "and another independent issue affects extension installation."
            ),
            "item_candidates": [
                {
                    "item_ref": "candidate-001",
                    "reason": (
                        "The candidate references "
                        "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf."
                    ),
                    "title": "Monitoring graphs show no data",
                },
                {
                    "item_ref": "candidate-002",
                    "reason": "Extension post-install fails with permissions.",
                    "title": "Monitoring extension post-install fails",
                },
            ],
            "reuse_search_checked": True,
            "reuse_search_run_ref": "reuse-search-001",
        },
    )

    text = json.dumps(structured, sort_keys=True)
    assert "item_candidates" not in structured
    assert "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf" not in text
    assert "tool_result_invalid" not in text


def test_run_approved_summary_pipeline_skips_missing_reuse_search_for_mvp() -> None:
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
        _approved_summary_args(
            debug=True,
            reuse_search_checked=False,
            reuse_search_run_ref="",
        ),
    )

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    assert response["result"]["isError"] is False
    structured = response["result"]["structuredContent"]
    assert structured["pipeline_ok"] is True
    assert structured["failure_stage"] == "none"
    assert structured["debug_code"] == "none"
    assert structured["reuse_search_status"] == "skipped"
    assert structured["input_safety_ok"] is True
    assert structured["evidence_valid"] is True
    assert structured["ready_for_reviewer"] is True
    assert structured["draft_request_ready"] is True
    assert "possible_duplicate_not_checked" not in result_text


def test_run_approved_summary_pipeline_blocks_summary_only_without_evidence() -> None:
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
        {
            "approved_summary_text": (
                "Approved sanitized summary: a supported product module loads "
                "but graphs show no data. The diagnostic summary references "
                "setup.php, service.log, application.ini, worker-process.pid, "
                "service.conf, 02component-feature.conf, settings.yaml, "
                "metadata.json, /etc/vendor-agent/conf.d/02component-feature.conf, "
                "and /usr/local/product/var/modules/component/rrd. The supported "
                "cause and resolution are present in the approved summary."
            ),
            "debug": True,
            "environment": (
                "Supported Linux platform; product module; service collector; "
                "embedded dashboard component"
            ),
        },
    )

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    assert response["result"]["isError"] is False
    structured = response["result"]["structuredContent"]
    assert structured["result_kind"] == "approved_summary_pipeline"
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "input_validation"
    assert structured["debug_code"] == "approved_summary_resolution_steps_required"
    assert structured["input_safety_ok"] is False
    assert structured["evidence_valid"] is False
    assert structured["draft_request_ready"] is False
    assert structured["provider_calls"] is False
    assert structured["writes_files"] is False
    assert "zendesk_source_html" not in result_text
    assert "evidence_basis" not in result_text


def test_draft_article_rejects_missing_environment_without_placeholder_html() -> None:
    arguments = _approved_summary_args(debug=True)
    assert isinstance(arguments["item"], dict)
    arguments["item"].pop("environment")
    arguments["item"].pop("applicable_to")

    response = _call_author_approved_summary(arguments)

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "approved_summary_authoring"
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "input_validation"
    assert structured["debug_code"] == "approved_summary_environment_required"
    assert "reviewer_only_html" not in structured
    assert "approved-summary-product" not in result_text
    assert "approved-summary-platform" not in result_text
    assert "approved-summary-component" not in result_text


def test_terminal_authoring_result_keeps_outcomes_diagnostic() -> None:
    result = {
        "auto_publish_allowed": False,
        "blockers": ["approved_summary_environment_required"],
        "debug_code": "approved_summary_environment_required",
        "failure_stage": "input_validation",
        "manual_draft_allowed": False,
        "ok": False,
        "pipeline_ok": False,
        "public_output_approved": False,
        "quality_gaps": [],
        "ready_for_reviewer": False,
        "recommended_action": "blocked",
        "result_kind": "draft_article_authoring",
        "reviewer_bundle_written": False,
        "semantic_item_outcomes": [
            {
                "item_ref": "candidate-allowed",
                "kcs_item_status": "candidate_allowed",
                "outcome": "draft_candidate",
            },
            {
                "item_ref": "candidate-blocked",
                "kcs_item_status": "blocked_need_more_evidence",
                "outcome": "blocked_need_more_evidence",
            },
        ],
    }

    text = desktop_tool_results.tool_result_text(result)

    assert "terminal blocked state" in text
    assert "No operator selection or further tool action was returned" in text
    assert "semantic_item_outcomes" in text
    assert "diagnostic ledger only" in text
    assert "Do not ask the operator to select an item" in text
    assert "candidate-allowed" not in text
    assert "candidate-blocked" not in text
    assert '"debug_code":"approved_summary_environment_required"' in text


def test_draft_article_returns_controlled_result_for_bad_environment() -> None:
    arguments = _approved_summary_args(debug=True)
    assert isinstance(arguments["item"], dict)
    arguments["item"]["environment"] = {"unsupported": "Plesk for Linux"}

    _assert_draft_article_call_shape_invalid(arguments)


def test_draft_article_rejects_scr_without_resolution_steps() -> None:
    arguments = _approved_summary_args(debug=True)
    assert isinstance(arguments["item"], dict)
    arguments["item"].pop("resolution_steps")

    response = _call_author_approved_summary(arguments)

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "approved_summary_authoring"
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "input_validation"
    assert (
        structured["debug_code"]
        == "approved_summary_resolution_steps_required"
    )
    assert "reviewer_only_html" not in structured


def test_draft_article_rejects_non_executable_resolution_steps() -> None:
    arguments = _approved_summary_args(debug=True)
    assert isinstance(arguments["item"], dict)
    arguments["item"]["resolution_steps"] = [
        "Back up and disable the rogue collectd config file.",
        "Restart the collector.",
    ]

    response = _call_author_approved_summary(arguments)

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "approved_summary_authoring"
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "input_validation"
    assert (
        structured["debug_code"]
        == "approved_summary_resolution_steps_incomplete"
    )
    assert (
        structured["next_required_action"]
        == "add_operator_confirmed_resolution_detail"
    )
    assert structured["operator_resolution_detail_policy"] == {
        "accepted_detail_examples": [
            "exact executable procedure and verification used in the ticket",
            "exact procedure confirmed by the operator",
            "explicit customer-confirmed procedure and outcome",
        ],
        "can_retry_after_operator_evidence": True,
        "do_not_invent_resolution_procedure": True,
        "reason": (
            "Resolution evidence does not contain enough concrete procedure "
            "detail for a standalone KCS draft."
        ),
    }
    result_text = response["result"]["content"][0]["text"]
    assert "add_operator_confirmed_resolution_detail" in result_text
    assert "do_not_invent_resolution_procedure" in result_text
    assert "reviewer_only_html" not in structured


def test_draft_article_rejects_speculative_supported_cause() -> None:
    arguments = _approved_summary_args(debug=True)
    assert isinstance(arguments["item"], dict)
    arguments["item"]["supported_cause"] = (
        "The directory was likely left over from a failed installation."
    )

    response = _call_author_approved_summary(arguments)

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "approved_summary_authoring"
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "input_validation"
    assert structured["debug_code"] == "approved_summary_supported_cause_uncertain"
    assert "reviewer_only_html" not in structured


def test_draft_article_rejects_destructive_resolution_step() -> None:
    arguments = _approved_summary_args(debug=True)
    assert isinstance(arguments["item"], dict)
    arguments["item"]["resolution_steps"] = [
        "Connect to the Plesk server via SSH.",
        "Run ls -ld /usr/local/psa/var/modules/monitoring/.",
        "Run rm -rf /usr/local/psa/var/modules/monitoring/.",
        "Reinstall the extension from the Plesk UI.",
    ]

    response = _call_author_approved_summary(arguments)

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "approved_summary_authoring"
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "input_validation"
    assert structured["debug_code"] == "approved_summary_resolution_step_destructive"
    assert "reviewer_only_html" not in structured
    assert "rm -rf" not in result_text


def test_run_approved_summary_pipeline_accepts_top_level_chat_item_fields() -> None:
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
        {
            "approved_summary_text": (
                "Approved sanitized summary: supported product monitoring graphs "
                "show no data. The root cause is a leftover unowned collector "
                "configuration file overriding the data directory. The supported "
                "fix is to disable the override file, restart the collector, and "
                "wait for new metric data."
            ),
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "confirmed_facts": (
                "The diagnostic summary references service.log and service.conf."
            ),
            "debug": True,
            "environment": {
                "components": ["monitoring component", "data source"],
                "extension": "monitoring extension",
                "os": "supported Linux platform",
                "product": "supported product",
            },
            "resolution_steps": (
                "Run mv /etc/product/conf.d/override.conf "
                "/etc/product/conf.d/override.conf.disabled. Run systemctl "
                "restart product-collector. Confirm new graph data."
            ),
            "reuse_search_checked": True,
            "reuse_search_run_ref": "reuse-search-001",
            "supported_cause": (
                "A leftover unowned collector configuration file overrides the "
                "data directory."
            ),
            "supported_resolution_or_workaround": (
                "Disable the override file and restart the collector."
            ),
            "symptoms": "Product monitoring graphs show no data.",
            "title": "Product monitoring graphs show no data",
        },
    )

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    assert response["result"]["isError"] is False
    structured = response["result"]["structuredContent"]
    assert structured["pipeline_ok"] is True
    assert structured["failure_stage"] == "none"
    assert structured["input_safety_ok"] is True
    assert structured["evidence_valid"] is True
    assert structured["ready_for_reviewer"] is True
    assert structured["draft_request_ready"] is True
    assert "zendesk_source_html" not in result_text
    assert "evidence_basis" not in result_text


def test_run_approved_summary_pipeline_accepts_chat_item_alias_fields() -> None:
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
        {
            "approved_summary_text": (
                "Approved sanitized summary: monitoring graphs show no data. "
                "The confirmed cause is a leftover collector configuration "
                "override. The supported fix is to disable the override file, "
                "restart the collector, and verify new graph data."
            ),
            "debug": True,
            "item": {
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "environment": {
                    "components": ["collector", "dashboard data source"],
                    "extension": "monitoring extension",
                    "os": "supported Linux platform",
                    "product": "supported product",
                },
                "evidence": "The sanitized diagnostic summary confirms the override.",
                "resolution_summary": "Disable the override and restart the collector.",
                "reuse_search_checked": True,
                "reuse_search_run_ref": "reuse-search-001",
                "root_cause": (
                    "A leftover collector override writes data to the wrong path."
                ),
                "steps": (
                    "Disable the override, restart the collector, and verify graphs."
                ),
                "symptom": "Monitoring graphs show no data.",
                "title": "Monitoring graphs show no data",
            },
        },
    )

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    assert response["result"]["isError"] is False
    structured = response["result"]["structuredContent"]
    assert structured["pipeline_ok"] is True
    assert structured["failure_stage"] == "none"
    assert structured["input_safety_ok"] is True
    assert structured["evidence_valid"] is True
    assert structured["ready_for_reviewer"] is True
    assert "zendesk_source_html" not in result_text
    assert "evidence_basis" not in result_text


def test_run_approved_summary_pipeline_accepts_common_chat_alias_fields() -> None:
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
        {
            "approved_summary_text": (
                "Approved sanitized summary: product monitoring graphs show no "
                "data. A diagnostic configuration override writes metric data "
                "to a nonstandard path. The supported solution disables the "
                "override and restarts the collector."
            ),
            "article_title": "Product monitoring graphs show no data",
            "commands": [
                "Run rpm -qf /etc/product/conf.d/override.conf.",
                (
                    "Run mv /etc/product/conf.d/override.conf "
                    "/etc/product/conf.d/override.conf.disabled."
                ),
                "Run systemctl restart product-collector.",
            ],
            "debug": True,
            "diagnosis": (
                "A leftover collector override writes metrics to the wrong "
                "location."
            ),
            "environment": {
                "component": "monitoring component / collector",
                "platform": "supported Linux platform",
                "product": "supported product",
            },
            "log_evidence": [
                "The diagnostic summary references service.log.",
                "The diagnostic summary references application.ini.",
            ],
            "problem": "Product monitoring graphs show no data.",
            "reuse_search_checked": True,
            "reuse_search_run_ref": "reuse-search-001",
            "secondary_issues": (
                "A module directory ownership mismatch can cause reinstall "
                "failure."
            ),
            "solution": (
                "Disable the stale override file and restart the collector."
            ),
        },
    )

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    assert response["result"]["isError"] is False
    structured = response["result"]["structuredContent"]
    assert structured["pipeline_ok"] is True
    assert structured["failure_stage"] == "none"
    assert structured["input_safety_ok"] is True
    assert structured["evidence_valid"] is True
    assert structured["ready_for_reviewer"] is True
    assert structured["draft_request_ready"] is True
    assert "zendesk_source_html" not in result_text
    assert "evidence_basis" not in result_text


def test_run_approved_summary_pipeline_accepts_chat_secondary_finding() -> None:
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
        {
            "approved_summary_text": (
                "Approved sanitized summary: product monitoring graphs show no "
                "data after extension reinstall. A leftover unowned collector "
                "configuration file overrides the metric data directory. The "
                "diagnostic summary references /var/www/vhosts, "
                "/usr/local/product/var/modules/monitoring/, "
                "/etc/vendor-agent/conf.d/02component-feature.conf, service.log, "
                "post-install.php, root:root ownership, and service restart. "
                "Historical data written to the wrong path is not backfilled."
            ),
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "confirmed_facts": [
                "The collector override file is not owned by any package.",
                "The override changes the metric data directory.",
            ],
            "debug": True,
            "environment": {
                "component": "collector / dashboard / data source",
                "os": "supported Linux RPM platform",
                "product": "supported product monitoring",
            },
            "resolution_steps": [
                "Run rpm -qf /etc/vendor-agent/conf.d/02component-feature.conf.",
                (
                    "Run cp -a /etc/vendor-agent/conf.d/02component-feature.conf "
                    "/root/monitoring-case-backup/."
                ),
                (
                    "Run mv /etc/vendor-agent/conf.d/02component-feature.conf "
                    "/etc/vendor-agent/conf.d/02component-feature.conf.disabled."
                ),
                "Run systemctl restart product-collector.",
                "Confirm new graph data appears.",
            ],
            "reuse_search_checked": True,
            "reuse_search_run_ref": "reuse-search-001",
            "secondary_finding": (
                "If the monitoring module directory is owned by root:root "
                "instead of service-user:service-user, reinstall can fail with "
                "Permission denied."
            ),
            "supported_cause": (
                "A leftover collector configuration file writes metric data to "
                "a nonstandard path."
            ),
            "supported_resolution_or_workaround": (
                "Disable the override, restart the collector, and verify new "
                "graph data."
            ),
            "symptoms": "Product monitoring graphs show no data.",
            "title": "Product monitoring graphs show no data",
        },
    )

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    assert response["result"]["isError"] is False
    structured = response["result"]["structuredContent"]
    assert structured["pipeline_ok"] is True
    assert structured["failure_stage"] == "none"
    assert structured["input_safety_ok"] is True
    assert structured["evidence_valid"] is True
    assert structured["ready_for_reviewer"] is True
    assert structured["draft_request_ready"] is True
    assert "zendesk_source_html" not in result_text
    assert "evidence_basis" not in result_text


def test_run_approved_summary_pipeline_rejects_unknown_item_field() -> None:
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
        _approved_summary_args(item={"raw_ticket": "safe-looking value"}),
    )

    assert response is not None
    assert response["error"]["code"] == -32602
    assert "raw_ticket" not in json.dumps(response)


def test_run_approved_summary_pipeline_rejects_private_value_without_echo() -> None:
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
        _approved_summary_args(
            approved_summary_text="Contact person@example.com for details."
        ),
    )

    text = json.dumps(response, sort_keys=True)
    assert response is not None
    assert response["result"]["isError"] is False
    structured = response["result"]["structuredContent"]
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "input_validation"
    assert structured["debug_code"] == "approved_summary_text_invalid"
    assert "person@example.com" not in text


def test_run_approved_summary_pipeline_rejects_non_string_summary_text() -> None:
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
        _approved_summary_args(approved_summary_text=["not", "a", "summary"]),
    )

    assert response is not None
    assert response["result"]["isError"] is False
    structured = response["result"]["structuredContent"]
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "input_validation"
    assert structured["debug_code"] == "approved_summary_text_invalid"


def test_run_approved_summary_pipeline_reports_evidence_builder_stage() -> None:
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
        _approved_summary_args(case_ref="person@example.com"),
    )

    text = json.dumps(response, sort_keys=True)
    assert response is not None
    assert response["result"]["isError"] is False
    structured = response["result"]["structuredContent"]
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "evidence_builder"
    assert structured["debug_code"] == "approved_summary_evidence_build_failed"
    assert "person@example.com" not in text


def test_run_approved_summary_pipeline_reports_candidate_local_safety_block() -> None:
    private_value = "2606:4700:4700::1111"
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
        _approved_summary_args(item={"symptoms": [private_value]}),
    )

    text = json.dumps(response, sort_keys=True)
    assert response is not None
    assert response["result"]["isError"] is False
    structured = response["result"]["structuredContent"]
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "input_safety"
    assert structured["debug_code"] == "approved_summary_safety_blocked"
    assert private_value not in text


def test_run_approved_summary_pipeline_reports_evidence_validation_stage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_validate_evidence_packet(_packet: object) -> EvidenceValidationResult:
        return EvidenceValidationResult(
            ok=False,
            blockers=("missing_supported_resolution",),
        )

    monkeypatch.setattr(
        desktop_authoring_pipeline,
        "validate_evidence_packet",
        fake_validate_evidence_packet,
    )

    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
        _approved_summary_args(debug=True),
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "evidence_validation"
    assert (
        structured["debug_code"]
        == "approved_summary_evidence_validation_blocked"
    )
    assert structured["input_safety_ok"] is True
    assert structured["evidence_valid"] is False
    checks = {check["kind"]: check["ok"] for check in structured["checks"]}
    assert checks["input_validation"] is True
    assert checks["evidence_builder"] is True
    assert checks["input_safety"] is True
    assert checks["evidence_validation"] is False


def test_run_approved_summary_pipeline_reports_renderer_stage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_render_reviewer_packet(*_args: object, **_kwargs: object) -> object:
        raise ContractValidationError("synthetic renderer failure")

    monkeypatch.setattr(
        desktop_authoring_pipeline,
        "render_reviewer_packet",
        fake_render_reviewer_packet,
    )

    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
        _approved_summary_args(debug=True),
    )

    text = json.dumps(response, sort_keys=True)
    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "renderer"
    assert structured["debug_code"] == "approved_summary_renderer_failed"
    assert "synthetic renderer failure" not in text
    checks = {check["kind"]: check["ok"] for check in structured["checks"]}
    assert checks["decision"] is True
    assert checks["renderer"] is False


def test_run_approved_summary_pipeline_classifies_renderer_safety_stage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_render_reviewer_packet(*_args: object, **_kwargs: object) -> object:
        raise ContractValidationError("public article candidate contains unsafe value")

    monkeypatch.setattr(
        desktop_authoring_pipeline,
        "render_reviewer_packet",
        fake_render_reviewer_packet,
    )

    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
        _approved_summary_args(debug=True),
    )

    text = json.dumps(response, sort_keys=True)
    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "renderer"
    assert structured["debug_code"] == "approved_summary_renderer_safety_failed"
    assert "public article candidate contains unsafe value" not in text
    checks = {check["kind"]: check["ok"] for check in structured["checks"]}
    assert checks["decision"] is True
    assert checks["renderer"] is False


def test_unknown_tool_argument_is_json_rpc_error_not_tool_result() -> None:
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_GET_POLICY_SUMMARY,
        {
            "raw_note": "safe-looking value",
        },
    )

    assert response is not None
    assert response["error"]["code"] == -32602
    assert "raw_note" not in json.dumps(response)


def test_contract_smoke_uses_in_memory_safe_packets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_open(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("contract smoke must not read files")

    monkeypatch.setattr("builtins.open", fail_open)
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_RUN_CONTRACT_SMOKE,
        {},
    )

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    assert response["result"]["isError"] is False
    structured = response["result"]["structuredContent"]
    assert structured["smoke_ok"] is True
    assert structured["provider_calls"] is False
    assert structured["network_calls"] is False
    assert "/Users/" not in result_text
    assert "zendesk_source_html" not in result_text


def test_contract_smoke_rejects_arguments() -> None:
    response = _call_tool(
        _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL),
        TOOL_RUN_CONTRACT_SMOKE,
        {"case_ref": "case-001"},
    )

    assert response is not None
    assert response["error"]["code"] == -32602


def test_tools_call_rejects_unknown_raw_params_without_echo() -> None:
    response = _initialized_transport().handle_message(
        _request(
            "tools/call",
            {
                "arguments": {},
                "name": claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
                "raw_ticket": "person@example.com",
            },
        )
    )

    text = json.dumps(response, sort_keys=True)
    assert response is not None
    assert response["error"]["code"] == -32602
    assert "person@example.com" not in text


def test_tool_result_builder_rejects_forbidden_output_surfaces() -> None:
    descriptor = KcsDesktopMcpAdapter().list_tools()[0]

    with pytest.raises(ContractValidationError):
        mcp_desktop._mcp_tool_response(  # noqa: SLF001
            descriptor=descriptor,
            result=McpToolResult(
                ok=True,
                result={
                    "ok": True,
                    "result_kind": "bad",
                    "schema_version": "kcs_mcp_tool_result_v1",
                    "zendesk_source_html": "<p>Unsafe body</p>",
                },
            ),
        )


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "attachment_url",
        "attachmentUrl",
        "audio",
        "draft_artifact",
        "draftArtifact",
        "embedded_resource",
        "embeddedResource",
        "image",
        "local_path",
        "localPath",
        "raw_validation_payload",
        "rawValidationPayload",
        "resource",
        "resource_link",
        "resourceLink",
        "reviewer_only_draft_artifact",
        "reviewerOnlyDraftArtifact",
    ],
)
def test_tool_result_builder_rejects_nested_forbidden_surfaces(
    forbidden_key: str,
) -> None:
    descriptor = KcsDesktopMcpAdapter().list_tools()[0]

    with pytest.raises(ContractValidationError):
        mcp_desktop._mcp_tool_response(  # noqa: SLF001
            descriptor=descriptor,
            result=McpToolResult(
                ok=True,
                result={
                    "checks": [{forbidden_key: "safe-ref"}],
                    "ok": True,
                    "result_kind": "policy_summary",
                    "schema_version": "kcs_mcp_tool_result_v1",
                },
            ),
        )


def test_tool_result_text_matches_compact_structured_content_json() -> None:
    transport = _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL)

    response = _call_tool(
        transport,
        TOOL_GET_POLICY_SUMMARY,
        {},
    )

    assert response is not None
    result = response["result"]
    text = result["content"][0]["text"]
    assert result["content"] == [{"text": text, "type": "text"}]
    assert json.loads(text) == result["structuredContent"]
    assert "resource_link" not in json.dumps(result)
    assert '"resource"' not in json.dumps(result)
    assert "file://" not in json.dumps(result)


@pytest.mark.parametrize(
    "line",
    [
        "{not-json}\n",
        '{"jsonrpc":"2.0","id":1,"method":"ping","params":{"x":NaN}}\n',
        '[{"jsonrpc":"2.0","id":1,"method":"ping"}]\n',
    ],
)
def test_stdio_framing_rejects_malformed_or_non_object_messages(line: str) -> None:
    output = io.StringIO()

    serve_stdio(input_stream=[line], output_stream=output)

    payload = json.loads(output.getvalue())
    assert payload["error"]["code"] in {-32700, -32600}
    assert "NaN" not in output.getvalue()


def test_stdio_framing_rejects_oversized_lines_and_invalid_utf8() -> None:
    output = io.StringIO()

    serve_stdio(input_stream=[" " * (96 * 1024 + 1), b"\xff\n"], output_stream=output)

    lines = [json.loads(line) for line in output.getvalue().splitlines()]
    assert [line["error"]["code"] for line in lines] == [-32700, -32700]


def test_root_exports_include_mcp_desktop_api() -> None:
    assert kcs_adapters.KcsDesktopMcpAdapter is KcsDesktopMcpAdapter
    assert kcs_adapters.McpStdioTransport is McpStdioTransport
    assert kcs_adapters.TOOL_DRAFT_ARTICLE == TOOL_DRAFT_ARTICLE
    assert kcs_adapters.TOOL_AUTHOR_TICKET == TOOL_AUTHOR_TICKET
    assert kcs_adapters.TOOL_REGISTER_CLEAN_TICKET == TOOL_REGISTER_CLEAN_TICKET
    assert (
        kcs_adapters.TOOL_RUN_APPROVED_SUMMARY_PIPELINE
        == TOOL_RUN_APPROVED_SUMMARY_PIPELINE
    )
    assert kcs_adapters.TOOL_VALIDATE_DRAFT_RESPONSE == TOOL_VALIDATE_DRAFT_RESPONSE


def test_mcp_desktop_module_help_runs_without_import_order_warning() -> None:
    completed = subprocess.run(
        [sys.executable, "-W", "error", "-m", "kcs_adapters.mcp_desktop", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "Run the KCS Claude Desktop MCP stdio adapter." in completed.stdout
    assert "RuntimeWarning" not in completed.stderr
