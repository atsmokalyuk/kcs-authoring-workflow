from __future__ import annotations

import io
import json
import subprocess
import sys
from collections.abc import Mapping
from hashlib import sha256
from typing import Any

import pytest

import kcs_adapters
from kcs_adapters import desktop_authoring_pipeline, mcp_desktop
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
    assert initialize["result"]["capabilities"] == {
        "tools": {"listChanged": False},
        "resources": {"subscribe": False, "listChanged": False},
        "prompts": {"listChanged": False},
    }
    instructions = initialize["result"]["instructions"]
    assert "kcs_draft_article" in instructions
    assert "kcs_register_clean_ticket" in instructions
    assert "approved_summary_text" in instructions
    assert "ticket_ref" in instructions
    assert "first call kcs_register_clean_ticket" in instructions
    assert "configured approved-summaries store" in instructions
    assert "Use only the listed KCS Authoring tools" in instructions
    assert "legacy instruction" in instructions
    assert "support_get_behavior_instructions" in instructions
    assert "Plesk Support Assistant Local" in instructions
    assert "Do not report Plesk Support Assistant Local as missing" in instructions
    assert "Claude Desktop file card is not a filesystem path" in instructions
    assert "do not inspect upload directories" in instructions
    assert "item/item_candidates" in instructions
    assert "kcs_prepare_semantic_review" in instructions
    assert "kcs_submit_semantic_review" in instructions
    assert "raw comments" not in instructions
    assert "internal notes" not in instructions
    assert "attachments" not in instructions
    assert "draft an article" not in instructions
    assert "validation tools only" not in instructions
    assert "logging" not in initialize["result"]["capabilities"]
    assert before_initialized is not None
    assert before_initialized["error"]["code"] == -32002
    assert initialized is None
    assert after_initialized is not None
    assert "tools" in after_initialized["result"]


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
        "kcs_prepare_semantic_review",
        "kcs_submit_semantic_review",
        "support_get_behavior_instructions",
    }
    assert [tool["name"] for tool in tools][:3] == [
        "kcs_draft_ticket",
        "kcs_register_clean_ticket",
        "kcs_draft_article",
    ]
    assert len(tools) == 6
    for tool in tools:
        if tool["name"] == "kcs_register_clean_ticket":
            assert "sanitized ticket text is visible" in tool["description"]
            assert "no ticket_ref exists" in tool["description"]
            assert "clean_ticket_text" in tool["description"]
            assert "next_arguments" in tool["description"]
            schema = tool["inputSchema"]
            assert set(schema["properties"]) == {
                "clean_ticket_text",
                "debug",
                "ticket_ref",
            }
            assert schema["required"] == ["clean_ticket_text"]
            assert tool["annotations"]["readOnlyHint"] is False
            assert tool["annotations"]["idempotentHint"] is False
        elif tool["name"] == "kcs_draft_article":
            assert "short approved_summary_text" in tool["description"]
            assert "For `/draft <ticket_ref>`, use kcs_draft_ticket" in (
                tool["description"]
            )
            assert "item object" not in tool["description"]
            assert "item_candidates only" not in tool["description"]
            assert "break-fix" not in tool["description"]
            schema = tool["inputSchema"]
            assert set(schema["properties"]) == {
                "approved_summary_text",
                "debug",
                "operator_selected_item_ref",
                "operator_selection_ref",
            }
            assert "Short inline sanitized text" in schema["properties"][
                "approved_summary_text"
            ]["description"]
            assert "kcs_register_clean_ticket" in schema["properties"][
                "approved_summary_text"
            ]["description"]
            assert "raw comments" not in schema["properties"][
                "approved_summary_text"
            ]["description"]
            assert "internal notes" not in schema["properties"][
                "approved_summary_text"
            ]["description"]
            assert "attachments" in schema["properties"]["approved_summary_text"][
                "description"
            ]
            assert "explicit debug or smoke compatibility" in schema["properties"][
                "debug"
            ]["description"]
            assert "reviewer-only Zendesk HTML" in schema["properties"]["debug"][
                "description"
            ]
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
            assert tool["annotations"]["readOnlyHint"] is False
            assert tool["annotations"]["idempotentHint"] is False
        elif tool["name"] == "kcs_prepare_semantic_review":
            assert "semantic_review_required" in tool["description"]
            assert "bounded excerpts" in tool["description"]
            schema = tool["inputSchema"]
            assert set(schema["properties"]) == {"semantic_review_ref"}
            assert schema["required"] == ["semantic_review_ref"]
            assert "Opaque semantic-review ref" in schema["properties"][
                "semantic_review_ref"
            ]["description"]
            assert tool["annotations"]["readOnlyHint"] is True
            assert tool["annotations"]["idempotentHint"] is True
        assert tool["annotations"]["destructiveHint"] is False
        assert tool["annotations"]["openWorldHint"] is False
        assert "inputSchema" in tool
        assert "outputSchema" not in tool
        assert tool["inputSchema"]["additionalProperties"] is False
    _assert_submit_semantic_review_tool(
        next(tool for tool in tools if tool["name"] == "kcs_submit_semantic_review")
    )
    _assert_draft_ticket_tool(
        next(tool for tool in tools if tool["name"] == "kcs_draft_ticket")
    )


def _assert_draft_ticket_tool(tool: Mapping[str, Any]) -> None:
    assert "Use immediately" in tool["description"]
    assert "/draft <ticket_ref>" in tool["description"]
    assert "only ticket_ref" in tool["description"]
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
    assert "Submit candidate_semantic_extraction_v1" in tool["description"]
    assert "candidate_semantic_extraction_v1" in tool["description"]
    assert "No article draft" in tool["description"]
    schema = tool["inputSchema"]
    assert set(schema["properties"]) == {
        "candidate_semantic_extraction",
        "semantic_review_ref",
    }
    assert schema["required"] == [
        "semantic_review_ref",
        "candidate_semantic_extraction",
    ]
    extraction_schema = schema["properties"]["candidate_semantic_extraction"]
    assert extraction_schema["type"] == "object"
    assert "prepared packet required_submit_shape" in extraction_schema["description"]
    assert "Python validates" in extraction_schema["description"]
    assert "properties" not in extraction_schema
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
    assert structured["result_kind"] == "approved_summary_pipeline"
    assert structured["pipeline_ok"] is True
    assert structured["failure_stage"] == "none"
    assert structured["debug_code"] == "none"
    assert structured["input_safety_ok"] is True
    assert structured["evidence_valid"] is True
    assert structured["ready_for_reviewer"] is True
    assert structured["draft_request_ready"] is True
    assert structured["original_recommended_action"] == "create_candidate"
    assert structured["original_article_type"] == "technical_scr"
    assert structured["auto_publish_allowed"] is False
    assert structured["public_output_approved"] is False
    assert structured["provider_calls"] is False
    assert structured["writes_files"] is False
    assert "zendesk_source_html" not in result_text
    assert "evidence_basis" not in result_text
    assert "<h1>" not in result_text


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
    assert (
        structured["atomic_item"]["title"]
        == "Monitoring graphs show no data in Plesk"
    )
    draft = structured["reviewer_only_draft"]
    assert structured["draft_sections"] == draft
    assert structured["reviewer_only_preview"] == draft
    preview_text = structured["reviewer_only_preview_text"]
    assert preview_text.startswith("Title: Monitoring graphs show no data in Plesk")
    assert "Applicable to:\n- Plesk for Linux" in preview_text
    assert "Symptoms:\n1. Product monitoring graphs show no data." in preview_text
    assert "Cause:\nA required product-side package is missing." in preview_text
    assert draft["status"] == "reviewer_only"
    assert draft["title"] == "Monitoring graphs show no data in Plesk"
    assert draft["symptoms"] == ["Product monitoring graphs show no data."]
    assert draft["cause"] == "A required product-side package is missing."
    assert (
        draft["resolution"]
        == "Install the missing package and restart the related service."
    )
    assert structured["quality_gaps"] == [
        {"kind": "reference_section_coverage_ok", "severity": "info"}
    ]
    result_output = response["result"]["content"][0]["text"]
    assert result_output.startswith("```html\n")
    assert "```html\n" in result_output
    assert "COPY THE FINAL RESPONSE BELOW VERBATIM" not in result_output
    assert "Do not rewrite it into a Markdown article" not in result_output
    assert "do not add follow-up wording" not in result_output
    assert "Reviewer-only Zendesk HTML draft generated" not in result_output
    assert "COPY THE FENCED HTML BLOCK" not in result_output
    assert "\n```\n\n```json\n" in result_output
    assert "Reviewer preview:" not in result_output
    assert preview_text not in result_output
    html = structured["reviewer_only_html"]
    assert "<h1>Monitoring graphs show no data in Plesk</h1>" in html
    assert html in result_output
    assert "<h2>Applicable to</h2>" in html
    assert "<h2>Symptoms</h2>" in html
    assert "<h2>Cause</h2>" in html
    assert "<h2>Resolution</h2>" in html
    assert "zendesk_source_html" not in result_text
    assert "evidence_basis" not in result_text
    assert "reviewer_packet" not in result_text


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
    assert structured["pipeline_ok"] is False
    assert structured["recommended_action"] == "blocked"
    assert structured["workflow_state"] == "semantic_review_required"
    assert structured["debug_code"] == "semantic_identification_low_confidence"
    assert structured["failure_stage"] == "semantic_extraction"
    assert structured["next_tool"] == "kcs_prepare_semantic_review"
    assert structured["next_arguments"] == {
        "semantic_review_ref": structured["semantic_review_ref"]
    }
    assert structured["excerpt_count"] > 0
    from kcs_adapters.desktop_semantic_review import (
        SEMANTIC_REVIEW_MAX_TOTAL_BYTES,
    )

    assert structured["excerpt_total_bytes"] <= SEMANTIC_REVIEW_MAX_TOTAL_BYTES
    assert isinstance(structured["semantic_review_packet_sha256"], str)
    assert structured["draft_generated"] is False
    assert structured["reviewer_bundle_written"] is False
    assert structured["manual_draft_allowed"] is False
    assert structured["ticket_ref"] == "ticket-ambiguous"
    assert "reviewer_only_html" not in structured
    assert "Do not draft manually" in response_text


def test_prepare_semantic_review_returns_bounded_selected_excerpts(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    filler = "\n".join(
        f"Filler diagnostic note {index} DO-NOT-RETURN-FULL-TICKET-SENTINEL"
        for index in range(80)
    )
    noisy_transcript = "\n\n".join(
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
    transport = _initialized_transport(
        adapter=KcsDesktopMcpAdapter(
            reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles"
        )
    )
    _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_REGISTER_CLEAN_TICKET),
        {
            "clean_ticket_text": noisy_transcript,
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

    prepare_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_PREPARE_SEMANTIC_REVIEW),
        {"semantic_review_ref": draft["semantic_review_ref"]},
    )

    assert prepare_response is not None
    packet_text = json.dumps(prepare_response, sort_keys=True)
    packet = prepare_response["result"]["structuredContent"]
    assert packet["result_kind"] == "semantic_review_packet"
    assert packet["schema_version"] == "kcs_semantic_review_packet_v1"
    assert packet["semantic_review_ref"] == draft["semantic_review_ref"]
    assert packet["allowed_output_schema"] == "candidate_semantic_extraction_v1"
    assert packet["submit_tool"] == "kcs_submit_semantic_review"
    assert packet["submit_arguments"] == {
        "semantic_review_ref": draft["semantic_review_ref"]
    }
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
    required_shape = packet["required_submit_shape"]
    assert set(required_shape) == {
        "candidate_semantic_extraction",
        "semantic_review_ref",
    }
    assert required_shape["semantic_review_ref"] == draft["semantic_review_ref"]
    extraction_shape = required_shape["candidate_semantic_extraction"]
    assert extraction_shape["case_ref"] == draft["semantic_review_ref"]
    assert extraction_shape["schema_version"] == "candidate_semantic_extraction_v1"
    assert "items" in extraction_shape
    assert "candidates" not in extraction_shape
    shape_item = extraction_shape["items"][0]
    assert isinstance(shape_item["symptoms"][0], str)
    assert isinstance(shape_item["confirmed_facts"][0], str)
    assert isinstance(shape_item["resolution_steps"][0], str)
    assert packet["candidate_plain_string_array_fields"] == [
        "source_refs",
        "symptoms",
        "confirmed_facts",
        "resolution_steps",
        "open_questions",
    ]
    assert packet["candidate_item_field_names"]
    assert packet["candidate_environment_field_names"] == [
        "applicable_to",
        "platform",
        "product",
    ]
    assert "Return every separately searchable KCS item candidate" in packet[
        "candidate_count_policy"
    ]
    assert "Do not choose the first candidate yourself" in packet[
        "candidate_count_policy"
    ]
    assert packet["resolution_step_requirements"]
    result_text = prepare_response["result"]["content"][0]["text"]
    assert "Call kcs_submit_semantic_review with this exact argument shape" in (
        result_text
    )
    assert "choose a candidate yourself" in result_text
    assert "submit all of those candidates together in the items array" in (
        result_text
    )
    assert "candidate array key must be items" in result_text
    assert "resolution_steps must be standalone and executable" in result_text
    assert "arrays of plain strings only" in result_text
    assert "{order, action}" in result_text
    assert "Do not draft an article" in packet_text
    assert "Do not copy local workstation paths" in result_text
    assert "Sanitized server configuration or log paths may be included" in result_text
    assert '"candidates"' not in json.dumps(packet["required_submit_shape"])
    assert "DO-NOT-RETURN-FULL-TICKET-SENTINEL" not in packet_text


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
            "ticket_ref": "ticket-96016087",
        },
    )
    draft_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {"ticket_ref": "ticket-96016087", "debug": True},
    )
    assert draft_response is not None
    draft = draft_response["result"]["structuredContent"]
    assert draft["workflow_state"] == "semantic_review_required"
    assert draft["ticket_ref"] == "ticket-96016087"

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
    assert "ticket-96016087" not in packet_text


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


def _semantic_review_extraction(
    packet: Mapping[str, Any],
    *,
    item_count: int = 1,
    source_ref: str | None = None,
    resolution_text: str = "Restart the affected service and confirm success.",
) -> dict[str, object]:
    source_refs = [source_ref or packet["allowed_source_refs"][0]]
    items: list[dict[str, object]] = []
    for index in range(item_count):
        candidate_id = f"candidate-{index + 1:03d}"
        items.append(
            {
                "article_type_hint": ArticleType.TECHNICAL_SCR.value,
                "candidate_id": candidate_id,
                "confirmed_facts": [
                    "The clean ticket contains confirmed failure evidence."
                ],
                "environment": {
                    "applicable_to": ["Plesk for Linux"],
                    "platform": "Plesk for Linux",
                },
                "kcs_item_status": KcsItemStatus.CANDIDATE_ALLOWED.value,
                "product_relation": ProductRelation.PLESK_OWNED.value,
                "resolution_steps": [
                    "Connect to the Plesk server via SSH.",
                    "Run systemctl restart sw-cp-server.",
                    "Open Plesk and confirm the task completes successfully.",
                ],
                "source_refs": source_refs,
                "summary": f"Plesk task fails with an error {index + 1}",
                "supportability": Supportability.SUPPORTED.value,
                "supportability_basis": SupportabilityBasis.NOT_CHECKED.value,
                "supported_cause": "A Plesk service issue caused the failure.",
                "supported_resolution_or_workaround": resolution_text,
                "symptoms": ["A product task fails with an error."],
                "visibility_hint": VisibilityHint.PUBLIC_CUSTOMER_SAFE.value,
            }
        )
    return {
        "case_ref": packet["case_ref"],
        "extraction_source_ref": "semantic-review-submit-001",
        "items": items,
        "schema_version": CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION,
        "source_refs": source_refs,
    }


def _prepared_semantic_review_packet(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    clean_ticket_text: str | None = None,
):
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
                clean_ticket_text
                or "Customer Ticket Content\n"
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
    prepare_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_PREPARE_SEMANTIC_REVIEW),
        {"semantic_review_ref": semantic_review_ref},
    )
    assert prepare_response is not None
    return (
        transport,
        semantic_review_ref,
        prepare_response["result"]["structuredContent"],
    )


def test_submit_semantic_review_single_candidate_continues_to_draft(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": _semantic_review_extraction(packet),
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    response_text = json.dumps(response, sort_keys=True)
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["approved_summary_source"] == "semantic_review"
    assert structured["ticket_ref"] == "ticket-semantic-review"
    assert structured["draft_generated"] is True
    assert structured["reviewer_bundle_written"] is True
    assert "reviewer_only_html" not in structured
    assert "candidate_semantic_extraction" not in response_text


def test_submit_semantic_review_uses_clean_ticket_minimal_environment(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path,
        monkeypatch,
        clean_ticket_text=(
            "Customer Ticket Content\n"
            "Plesk for Linux server reports that a product task fails.\n"
            "The investigation mentions /etc/httpd/conf.d/example.conf and "
            "systemctl status httpd on a Linux host.\n"
            "Support restarted one service and confirmed the issue resolved."
        ),
    )
    extraction = _semantic_review_extraction(packet)
    extraction["items"][0]["environment"] = {}

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": extraction,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["debug_code"] == "draft_only_reuse_search_missing"
    assert structured["draft_generated"] is True
    assert structured["reviewer_bundle_written"] is True


def test_submit_semantic_review_accepts_firewall_resolution_actions(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )
    extraction = _semantic_review_extraction(packet)
    extraction["items"][0]["summary"] = (
        "High CPU load caused by HTTP flood traffic to the Plesk Panel"
    )
    extraction["items"][0]["resolution_steps"] = [
        "Connect to the Plesk server via SSH.",
        (
            "Confirm with a reviewer whether the custom Fail2Ban mitigation "
            "should be public or internal before KCS handoff."
        ),
        (
            "Run iptables-save to back up firewall rules before applying "
            "traffic mitigation."
        ),
        "Run fail2ban-client reload after adding the panel flood jail.",
        "Run iptables -I INPUT -p tcp --dport 8880 -j DROP.",
        "Verify CPU status and confirm port 8880 flood traffic is no longer processed.",
    ]
    extraction["items"][0]["supported_resolution_or_workaround"] = (
        "Reload the Fail2Ban jail, block the abusive panel HTTP traffic on "
        "port 8880, and verify CPU usage drops."
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": extraction,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["debug_code"] == "draft_only_reuse_search_missing"
    assert structured["draft_generated"] is True
    assert structured["reviewer_bundle_written"] is True


def test_submit_semantic_review_accepts_ticket_supported_risky_action_without_rollback(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )
    extraction = _semantic_review_extraction(packet)
    extraction["items"][0]["summary"] = (
        "High CPU load caused by HTTP flood traffic to the Plesk Panel"
    )
    extraction["items"][0]["resolution_steps"] = [
        "Connect to the Plesk server via SSH.",
        "Run iptables -I INPUT -p tcp --dport 8880 -j DROP.",
        "Verify CPU status and confirm port 8880 flood traffic is no longer processed.",
    ]
    extraction["items"][0]["supported_resolution_or_workaround"] = (
        "Block the abusive panel HTTP traffic on port 8880 and verify CPU "
        "usage drops."
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": extraction,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["debug_code"] == "draft_only_reuse_search_missing"
    assert structured["draft_generated"] is True
    assert structured["reviewer_bundle_written"] is True
    assert "risky_visible_step_without_warning_or_backup" not in structured["blockers"]


def test_submit_semantic_review_blocks_vague_technical_resolution_actions(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )
    extraction = _semantic_review_extraction(packet)
    extraction["items"][0]["summary"] = (
        "High CPU load caused by HTTP flood traffic to the Plesk Panel"
    )
    extraction["items"][0]["resolution_steps"] = [
        "Connect to the Plesk server via SSH.",
        (
            "Create a custom Fail2Ban filter at "
            "/etc/fail2ban/filter.d/panel-flood.conf matching repeated "
            "requests."
        ),
        "Create a custom jail for the panel flood traffic.",
        "Block the flood traffic on the affected port.",
    ]
    extraction["items"][0]["supported_resolution_or_workaround"] = (
        "Create a custom Fail2Ban filter and jail, then block the abusive "
        "traffic."
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": extraction,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["debug_code"] == "reviewer_html_quality_blocked"
    assert structured["draft_generated"] is False
    assert structured["manual_draft_allowed"] is False
    assert structured["reviewer_bundle_written"] is False
    assert "resolution_action_missing_implementation_detail" in structured["blockers"]


def test_submit_semantic_review_multiple_candidates_returns_split_required(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": _semantic_review_extraction(
                packet,
                item_count=2,
            ),
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["recommended_action"] == "split_required"
    assert structured["approved_summary_source"] == "semantic_review"
    assert structured["ticket_ref"] == "ticket-semantic-review"
    assert structured["manual_draft_allowed"] is False
    assert structured["reviewer_bundle_written"] is False
    assert "operator_selection_ref" in structured
    assert "operator_choice_request" in structured
    text = response["result"]["content"][0]["text"]
    assert text.startswith("Multiple KCS article candidates were detected.")
    assert "Do not answer with a prose-only candidate list." in text
    assert (
        "kcs_draft_article with exactly the selected option's submit_arguments"
        in text
    )
    assert "submit_arguments" in text


def test_submit_semantic_review_selected_split_candidate_continues_to_draft(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )

    split_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": _semantic_review_extraction(
                packet,
                item_count=2,
            ),
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert split_response is not None
    split = split_response["result"]["structuredContent"]
    assert split["recommended_action"] == "split_required"
    assert split["operator_selection_ref"].startswith("operator-selection-")

    selected_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {
            "operator_selected_item_ref": "candidate-001",
            "operator_selection_ref": split["operator_selection_ref"],
        },
    )

    assert selected_response is not None
    structured = selected_response["result"]["structuredContent"]
    assert selected_response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["draft_generated"] is True
    assert structured["item_ref"] == "candidate-001"
    assert structured["reviewer_bundle_written"] is True


def test_submit_semantic_review_first_of_three_keeps_valid_remaining_choice(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )

    split_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": _semantic_review_extraction(
                packet,
                item_count=3,
            ),
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert split_response is not None
    split = split_response["result"]["structuredContent"]
    selected_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
        {
            "operator_selected_item_ref": "candidate-001",
            "operator_selection_ref": split["operator_selection_ref"],
        },
    )

    assert selected_response is not None
    assert selected_response["result"]["isError"] is False
    structured = selected_response["result"]["structuredContent"]
    assert structured["draft_generated"] is True
    assert structured["item_ref"] == "candidate-001"
    assert structured["remaining_selection_ref"] == split["operator_selection_ref"]
    assert len(structured["remaining_item_candidates"]) == 2
    assert "remaining_operator_choice_request" in structured
    assert "next_arguments" not in structured


def test_submit_semantic_review_rejects_unknown_source_ref(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": _semantic_review_extraction(
                packet,
                source_ref="excerpt-999",
            ),
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["workflow_state"] == "semantic_review_submit_blocked"
    assert structured["debug_code"] == "semantic_review_source_refs_invalid"
    assert structured["draft_generated"] is False
    assert structured["manual_draft_allowed"] is False
    assert structured["reviewer_bundle_written"] is False
    assert "reviewer_only_html" not in structured


def test_submit_semantic_review_rejects_article_draft_content(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": _semantic_review_extraction(
                packet,
                resolution_text="<h1>Article draft</h1>",
            ),
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["workflow_state"] == "semantic_review_submit_blocked"
    assert structured["debug_code"] == "semantic_review_forbidden_html_or_markdown"
    assert structured["draft_generated"] is False
    assert structured["manual_draft_allowed"] is False


def test_submit_semantic_review_rejects_broad_item_payload(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": _semantic_review_extraction(packet),
            "item": {"title": "not allowed"},
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["workflow_state"] == "semantic_review_submit_blocked"
    assert structured["debug_code"] == "semantic_review_submission_invalid"
    assert structured["draft_generated"] is False
    assert structured["manual_draft_allowed"] is False


def test_submit_semantic_review_rejects_structured_resolution_step_objects(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )
    extraction = _semantic_review_extraction(packet)
    extraction["items"][0]["resolution_steps"] = [
        {
            "action": "Restart Plesk panel services.",
            "order": 1,
        }
    ]

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": extraction,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    result = response["result"]
    structured = result["structuredContent"]
    assert structured["workflow_state"] == "semantic_review_submit_blocked"
    assert (
        structured["debug_code"]
        == "semantic_review_plain_string_arrays_required"
    )
    assert structured["draft_generated"] is False
    assert structured["manual_draft_allowed"] is False
    text = result["content"][0]["text"]
    assert "arrays of plain strings only" in text
    assert "{order, action}" in text
    assert "Restart Plesk panel services" not in text


def test_submit_semantic_review_rejects_too_many_candidates(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": _semantic_review_extraction(
                packet,
                item_count=6,
            ),
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["workflow_state"] == "semantic_review_submit_blocked"
    assert structured["debug_code"] == "semantic_review_too_many_candidates"
    assert structured["draft_generated"] is False
    assert structured["manual_draft_allowed"] is False


def test_submit_semantic_review_rejects_local_path_values(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )
    extraction = _semantic_review_extraction(packet)
    extraction["items"][0]["confirmed_facts"] = [
        "The local reviewer file is /Users/operator/private/ticket.txt"
    ]

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": extraction,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["workflow_state"] == "semantic_review_submit_blocked"
    assert structured["debug_code"] == "semantic_review_local_ref_blocked"
    assert structured["draft_generated"] is False
    assert structured["manual_draft_allowed"] is False


def test_submit_semantic_review_rejects_claude_extra_environment_path(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )
    extraction = _semantic_review_extraction(packet)
    extraction["items"][0]["environment"] = {
        "applicable_to": ["Plesk for Linux"],
        "log_file": "/var/log/plesk/httpsd_access_log",
        "services_affected": ["sw-engine-fpm", "sw-cp-server"],
    }

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": extraction,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    result = response["result"]
    structured = result["structuredContent"]
    assert structured["workflow_state"] == "semantic_review_submit_blocked"
    assert structured["debug_code"] == "semantic_review_submission_invalid"
    assert structured["draft_generated"] is False
    assert structured["manual_draft_allowed"] is False
    text = result["content"][0]["text"]
    assert "Do not restart or retry the same ticket_ref automatically" in text
    assert "semantic_review_metadata_blocked" in text
    assert "Re-register only when" in text


def test_submit_semantic_review_allows_corrected_retry_after_environment_error(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )
    extraction = _semantic_review_extraction(packet)
    extraction["items"][0]["environment"] = {
        "applicable_to": ["Plesk for Linux"],
        "platform": "Linux with IPv6",
        "product": "Plesk",
    }

    first_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": extraction,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert first_response is not None
    first_result = first_response["result"]
    first_structured = first_result["structuredContent"]
    assert first_structured["workflow_state"] == "semantic_review_submit_blocked"
    assert first_structured["debug_code"] == "semantic_review_environment_invalid"
    assert first_structured["draft_generated"] is False
    assert first_structured["manual_draft_allowed"] is False
    first_text = first_result["content"][0]["text"]
    assert "retry kcs_submit_semantic_review at most once with the same" in first_text
    assert "platform 'Linux'" in first_text

    extraction["items"][0]["environment"] = {
        "applicable_to": ["Plesk for Linux"],
        "platform": "Linux",
        "product": "Plesk",
    }
    second_response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": extraction,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert second_response is not None
    second_structured = second_response["result"]["structuredContent"]
    assert second_structured["result_kind"] == "draft_article_authoring"
    assert second_structured["debug_code"] == "draft_only_reuse_search_missing"
    assert second_structured["draft_generated"] is True
    assert second_structured["reviewer_bundle_written"] is True


def test_submit_semantic_review_accepts_scalar_applicable_to(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )
    extraction = _semantic_review_extraction(packet)
    extraction["items"][0]["environment"] = {
        "applicable_to": "Plesk for Linux",
        "platform": "Linux",
        "product": "Plesk",
    }

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": extraction,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["debug_code"] == "draft_only_reuse_search_missing"
    assert structured["draft_generated"] is True
    assert structured["reviewer_bundle_written"] is True


def test_submit_semantic_review_accepts_server_absolute_paths(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )
    extraction = _semantic_review_extraction(packet)
    extraction["items"][0]["resolution_steps"].insert(
        1,
        (
            "Run sed -i 's/enabled = false/enabled = true/' "
            "/etc/product/service.conf to enable the product service "
            "configuration."
        ),
    )
    extraction["items"][0]["resolution_steps"].insert(
        2,
        (
            "Run systemctl restart product-service after updating "
            "/etc/product/service.conf."
        ),
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": extraction,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["debug_code"] == "draft_only_reuse_search_missing"
    assert structured["draft_generated"] is True
    assert structured["reviewer_bundle_written"] is True


def test_semantic_review_submit_sanitizer_accepts_public_support_article_url() -> None:
    from kcs_adapters.desktop_semantic_review import (
        _ensure_no_forbidden_submit_values,
    )

    _ensure_no_forbidden_submit_values(
        {
            "confirmed_facts": [
                (
                    "The clean ticket cites "
                    "https://support.plesk.com/hc/en-us/articles/115001678209 "
                    "as related public support evidence."
                )
            ]
        }
    )


def test_submit_semantic_review_treats_explicit_support_article_as_reuse_match(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )
    extraction = _semantic_review_extraction(
        packet,
        resolution_text=(
            "Open the existing Plesk knowledge base article for the known issue "
            "at https://support.plesk.com/hc/en-us/articles/115001678209 and "
            "apply the documented fix."
        ),
    )
    extraction["items"][0]["resolution_steps"] = [
        "Connect to the Plesk server via SSH.",
        (
            "Open the existing Plesk knowledge base article for the known issue "
            "at https://support.plesk.com/hc/en-us/articles/115001678209 and "
            "apply the documented fix."
        ),
        "Run plesk repair web and confirm the Apache configuration is valid.",
    ]

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": extraction,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["draft_generated"] is True
    assert structured["recommended_action"] == "flag_existing"
    assert structured["reuse_search_status"] == "checked"
    assert structured["selected_reuse_match"]["match_ref"] == "kb-115001678209"
    assert structured["existing_article_review"]["action"] == "flag_existing"
    assert structured["existing_article_review"]["match_ref"] == "kb-115001678209"
    existing_review = structured["existing_article_review"]
    assert existing_review["do_not_create_duplicate"] is True
    suggested_change = existing_review["suggested_change"]
    assert "cause_to_check_or_add" not in suggested_change
    assert "resolution_steps_to_check_or_add" not in suggested_change
    assert suggested_change["symptoms_to_check_or_add"]
    assert suggested_change["resolution_coverage_to_verify"] == [
        "Connect to the Plesk server via SSH.",
        "Run plesk repair web and confirm the Apache configuration is valid.",
    ]
    omitted_steps = suggested_change["omitted_duplicate_resolution_steps"]
    assert len(omitted_steps) == 1
    assert "115001678209" in omitted_steps[0]


def test_submit_semantic_review_rejects_windows_local_path_values(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )
    extraction = _semantic_review_extraction(packet)
    extraction["items"][0]["confirmed_facts"] = [
        "The local reviewer file is C:\\Users\\operator\\ticket.txt."
    ]

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": extraction,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["workflow_state"] == "semantic_review_submit_blocked"
    assert structured["debug_code"] == "semantic_review_local_ref_blocked"
    assert structured["draft_generated"] is False
    assert structured["manual_draft_allowed"] is False


def test_submit_semantic_review_accepts_config_placeholders(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )
    extraction = _semantic_review_extraction(packet)
    extraction["items"][0]["resolution_steps"].insert(
        1,
        (
            "Create a filter rule with failregex = ^<HOST> .* GET / HTTP/1.1 "
            "and retry issuing the certificate with -d <domain>."
        ),
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": extraction,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["debug_code"] == "draft_only_reuse_search_missing"
    assert structured["draft_generated"] is True
    assert structured["reviewer_bundle_written"] is True


def test_submit_semantic_review_accepts_config_text_path_comment(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )
    extraction = _semantic_review_extraction(packet)
    extraction["items"][0]["resolution_steps"].insert(
        1,
        (
            "Create the product configuration: CONFIG_TEXT:\n"
            "# /etc/product/service.conf\n"
            "[product-service]\n"
            "enabled = true"
        ),
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": extraction,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["debug_code"] == "draft_only_reuse_search_missing"
    assert structured["draft_generated"] is True
    assert structured["reviewer_bundle_written"] is True


def test_submit_semantic_review_accepts_shell_prompt_commands(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )
    extraction = _semantic_review_extraction(packet)
    extraction["items"][0]["resolution_steps"].insert(
        1,
        "Run the command shown in the ticket: # plesk repair web.",
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": extraction,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["debug_code"] == "draft_only_reuse_search_missing"
    assert structured["draft_generated"] is True
    assert structured["reviewer_bundle_written"] is True


def test_submit_semantic_review_rejects_html_tags(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )
    extraction = _semantic_review_extraction(packet)
    extraction["items"][0]["confirmed_facts"] = [
        "The semantic candidate contains <script>alert(1)</script>."
    ]

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": extraction,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["workflow_state"] == "semantic_review_submit_blocked"
    assert structured["debug_code"] == "semantic_review_forbidden_html_or_markdown"
    assert structured["draft_generated"] is False
    assert structured["manual_draft_allowed"] is False


def test_submit_semantic_review_rejects_single_segment_unix_absolute_path(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )
    extraction = _semantic_review_extraction(packet)
    extraction["items"][0]["confirmed_facts"] = [
        "The local scratch directory is /tmp."
    ]

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": extraction,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["workflow_state"] == "semantic_review_submit_blocked"
    assert structured["debug_code"] == "semantic_review_local_ref_blocked"
    assert structured["draft_generated"] is False
    assert structured["manual_draft_allowed"] is False


def test_submit_semantic_review_rejects_html_article_tags(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )
    extraction = _semantic_review_extraction(
        packet,
        resolution_text="<table><tr><td>Article draft</td></tr></table>",
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": extraction,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["workflow_state"] == "semantic_review_submit_blocked"
    assert structured["debug_code"] == "semantic_review_forbidden_html_or_markdown"
    assert structured["draft_generated"] is False
    assert structured["manual_draft_allowed"] is False


def test_submit_semantic_review_rejects_oversized_payload(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport, semantic_review_ref, packet = _prepared_semantic_review_packet(
        tmp_path, monkeypatch
    )
    extraction = _semantic_review_extraction(packet)
    extraction["items"][0]["confirmed_facts"] = [
        f"Confirmed fact {index} with bounded text." for index in range(2_500)
    ]

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_SUBMIT_SEMANTIC_REVIEW),
        {
            "candidate_semantic_extraction": extraction,
            "semantic_review_ref": semantic_review_ref,
        },
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["workflow_state"] == "semantic_review_submit_blocked"
    assert structured["debug_code"] == "semantic_review_submission_too_large"
    assert structured["draft_generated"] is False
    assert structured["manual_draft_allowed"] is False


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
            "case_ref": "96024747",
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
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["draft_generated"] is True
    assert structured["debug_code"] == "draft_only_reuse_search_missing"
    assert structured["article_type"] == ArticleType.TECHNICAL_SCR.value
    assert structured["html_path"].startswith("local-data/reviewer-bundles/")
    assert structured["kcs_ready"] is False
    assert structured["recommended_action"] == "draft_only"
    assert structured["reuse_search_status"] == "skipped"
    assert structured["writes_files"] is True
    assert "reviewer_only_html" not in structured
    html_path = bundle_root / structured["bundle_ref"] / "candidate-001" / (
        "reviewer_only.html"
    )
    html = html_path.read_text(encoding="utf-8")
    result_output = _tool_text(response)
    assert "<h2>Resolution</h2>" in html
    assert not result_output.startswith("```html\n")
    assert "Reviewer-only KCS draft generated" in result_output
    assert "Do not rewrite it into a Markdown article" not in result_output
    assert "COPY THE FINAL RESPONSE BELOW VERBATIM" not in result_output
    assert "do not claim the file is unavailable from this chat" in result_output
    assert "do not offer a separate chat-authored article" in result_output
    assert "html_path" in result_output


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
    assert "<h2>Cause</h2>" in html
    assert (
        "The collectd configuration file "
        "<code>/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf</code> "
        "pointed Monitoring metric data to a location that the Plesk Monitoring "
        "backend does not query."
    ) in html
    assert "PERSON_NAME" not in html
    assert "SHELL_USERHOST" not in html
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
    assert split["debug_code"] == "multiple_kcs_items_detected"
    assert split["recommended_action"] == "split_required"
    assert split["operator_prompt_style"] == "native_choice_popup"
    assert split["operator_selection_ref"].startswith("operator-selection-")
    assert split["operator_choice_request"]["mode"] == "single_select"
    assert split["operator_choice_request"]["prose_only_choice_allowed"] is False
    assert split["operator_choice_request"]["manual_draft_allowed"] is False
    assert split["operator_choice_request"]["automatic_item_retry_allowed"] is False
    assert split["operator_choice_request"]["submit_tool"] == "kcs_draft_article"
    assert split["operator_choice_request"]["options"][0]["submit_arguments"] == {
        "operator_selected_item_ref": "candidate-001",
        "operator_selection_ref": split["operator_selection_ref"],
    }
    assert split["item_candidates"] == [
            {
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "item_ref": "candidate-001",
                "title": (
                    "Monitoring graphs show no data in Plesk due to custom "
                    "collectd RRD data directory"
                ),
            },
        {
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "item_ref": "candidate-002",
            "title": "Monitoring extension post-install fails",
        },
    ]
    assert "reviewer_only_html" not in split

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
    assert provider.calls == [
        (
            "Approved sanitized summary: one issue affects monitoring graphs "
            "and another independent issue affects extension installation."
        )
    ]
    assert response["result"]["isError"] is False
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "item_identification"
    assert structured["debug_code"] == "multiple_kcs_items_detected"
    assert structured["recommended_action"] == "split_required"
    assert structured["operator_prompt_style"] == "native_choice_popup"
    assert structured["operator_selection_ref"].startswith("operator-selection-")
    assert structured["operator_choice_options"] == structured["item_candidates"]
    assert structured["operator_choice_request"]["mode"] == "single_select"
    assert structured["operator_choice_request"]["submit_tool"] == "kcs_draft_article"
    assert structured["operator_choice_request"]["options"][1]["submit_arguments"] == {
        "operator_selected_item_ref": "candidate-002",
        "operator_selection_ref": structured["operator_selection_ref"],
    }
    assert structured["item_candidates"] == [
        {
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "item_ref": "candidate-001",
            "title": "Monitoring graphs show no data",
        },
        {
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "item_ref": "candidate-002",
            "title": "Monitoring extension post-install fails",
        },
    ]
    assert "reviewer_only_html" not in structured


def test_draft_article_primary_selection_uses_pending_provider_candidate(
    tmp_path,
) -> None:
    bundle_root = tmp_path / "local-data" / "reviewer-bundles"
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
    assert structured["result_kind"] == "draft_article_authoring"
    assert structured["draft_generated"] is True
    assert structured["pipeline_ok"] is False
    assert structured["debug_code"] == "draft_only_reuse_search_missing"
    assert structured["item_ref"] == "candidate-001"
    assert structured["kcs_ready"] is False
    assert structured["ready_for_reviewer"] is False
    assert structured["recommended_action"] == "draft_only"
    assert structured["reuse_search_status"] == "skipped"
    assert structured["reviewer_bundle_written"] is True
    assert structured["html_path"].startswith("local-data/reviewer-bundles/")
    assert structured["manifest_path"].startswith("local-data/reviewer-bundles/")
    assert structured["remaining_selection_ref"] == split["operator_selection_ref"]
    assert structured["remaining_item_candidates"] == [
        {
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "item_ref": "candidate-002",
            "title": "Monitoring extension post-install fails",
        }
    ]
    assert structured["next_tool"] == "kcs_draft_article"
    assert structured["next_arguments"] == {
        "operator_selected_item_ref": "candidate-002",
        "operator_selection_ref": split["operator_selection_ref"],
    }
    assert "reviewer_only_html" not in structured
    html_path = bundle_root / structured["bundle_ref"] / "candidate-001" / (
        "reviewer_only.html"
    )
    manifest_path = bundle_root / structured["bundle_ref"] / "manifest.json"
    assert html_path.is_file()
    assert "<h2>Resolution</h2>" in html_path.read_text(encoding="utf-8")
    assert manifest_path.is_file()
    assert sha256(html_path.read_bytes()).hexdigest() == structured["html_sha256"]

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


def test_draft_article_primary_quality_blocker_does_not_write_bundle(
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
    assert structured["debug_code"] == "reviewer_html_quality_blocked"
    assert structured["draft_generated"] is False
    assert structured["reviewer_bundle_written"] is False
    assert structured["writes_files"] is False
    assert "reviewer_only_html" not in structured
    assert "html_path" not in structured
    assert "cause_contains_resolution_action" in structured["blockers"]
    assert not list(bundle_root.glob("**/*"))


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
