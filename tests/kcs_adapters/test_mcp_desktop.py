from __future__ import annotations

import io
import json

import pytest

import kcs_adapters
from kcs_adapters import mcp_desktop
from kcs_adapters.mcp_desktop import (
    MCP_PROTOCOL_VERSION,
    TOOL_GET_POLICY_SUMMARY,
    TOOL_NAME_STYLE_CANONICAL,
    TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
    TOOL_RUN_CONTRACT_SMOKE,
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
    tool_name_style: str = "claude_desktop_aliases",
) -> McpStdioTransport:
    transport = McpStdioTransport(tool_name_style=tool_name_style)
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
            "Install the missing product-side package.",
            "Restart the related product service.",
            "Reload the module page.",
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
    }
    payload.update(overrides)
    return payload


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
    assert "kcs_validate_handoff_request" in tool_names
    assert "kcs_run_contract_smoke" in tool_names
    assert "kcs_run_approved_summary_pipeline" in tool_names
    for tool in tools:
        assert tool["annotations"]["readOnlyHint"] is True
        assert tool["annotations"]["destructiveHint"] is False
        assert tool["annotations"]["idempotentHint"] is True
        assert tool["annotations"]["openWorldHint"] is False
        assert "inputSchema" in tool
        assert "outputSchema" not in tool
        assert tool["inputSchema"]["additionalProperties"] is False


def test_tools_list_internal_mode_keeps_output_schema() -> None:
    transport = _initialized_transport(tool_name_style=TOOL_NAME_STYLE_CANONICAL)

    response = transport.handle_message(_request("tools/list"))

    assert response is not None
    tools = response["result"]["tools"]
    assert tools
    for tool in tools:
        assert "outputSchema" in tool


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
                "name": claude_desktop_tool_alias(TOOL_RUN_CONTRACT_SMOKE),
            },
        }
    )

    assert response is None


def test_validate_handoff_request_returns_compact_safe_summary() -> None:
    transport = _initialized_transport()

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_VALIDATE_HANDOFF_REQUEST),
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
    transport = _initialized_transport()
    request = _handoff_request()
    response_payload = _handoff_response(
        request,
        reviewer_assist_notes=["Contact person@example.com."],
    )

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_VALIDATE_HANDOFF_RESPONSE),
        {"request": request.to_json_dict(), "response": response_payload},
    )

    assert response is not None
    result_text = json.dumps(response, sort_keys=True)
    assert response["result"]["isError"] is True
    assert response["result"]["structuredContent"]["error_code"] == "validation_failed"
    assert "person@example.com" not in result_text


def test_validate_draft_response_returns_no_html_body() -> None:
    transport = _initialized_transport()
    request = _draft_request()

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_VALIDATE_DRAFT_RESPONSE),
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
    transport = _initialized_transport()
    request = _draft_request()

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_VALIDATE_DRAFT_RESPONSE),
        {"request": request.to_json_dict(), "response": _draft_response(**patch)},
    )

    assert response is not None
    assert response["result"]["isError"] is True
    assert response["result"]["structuredContent"]["error_code"] == "validation_failed"


def test_run_approved_summary_pipeline_returns_compact_ready_status() -> None:
    response = _call_tool(
        _initialized_transport(),
        claude_desktop_tool_alias(TOOL_RUN_APPROVED_SUMMARY_PIPELINE),
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


def test_run_approved_summary_pipeline_rejects_unknown_item_field() -> None:
    response = _call_tool(
        _initialized_transport(),
        claude_desktop_tool_alias(TOOL_RUN_APPROVED_SUMMARY_PIPELINE),
        _approved_summary_args(item={"raw_ticket": "safe-looking value"}),
    )

    assert response is not None
    assert response["error"]["code"] == -32602
    assert "raw_ticket" not in json.dumps(response)


def test_run_approved_summary_pipeline_rejects_private_value_without_echo() -> None:
    response = _call_tool(
        _initialized_transport(),
        claude_desktop_tool_alias(TOOL_RUN_APPROVED_SUMMARY_PIPELINE),
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
    assert structured["debug_code"] == "approved_summary_input_invalid"
    assert "person@example.com" not in text


def test_run_approved_summary_pipeline_rejects_non_string_summary_text() -> None:
    response = _call_tool(
        _initialized_transport(),
        claude_desktop_tool_alias(TOOL_RUN_APPROVED_SUMMARY_PIPELINE),
        _approved_summary_args(approved_summary_text=["not", "a", "summary"]),
    )

    assert response is not None
    assert response["result"]["isError"] is False
    structured = response["result"]["structuredContent"]
    assert structured["pipeline_ok"] is False
    assert structured["failure_stage"] == "input_validation"
    assert structured["debug_code"] == "approved_summary_input_invalid"


def test_run_approved_summary_pipeline_reports_evidence_builder_stage() -> None:
    response = _call_tool(
        _initialized_transport(),
        claude_desktop_tool_alias(TOOL_RUN_APPROVED_SUMMARY_PIPELINE),
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


def test_unknown_tool_argument_is_json_rpc_error_not_tool_result() -> None:
    response = _call_tool(
        _initialized_transport(),
        claude_desktop_tool_alias(TOOL_VALIDATE_HANDOFF_REQUEST),
        {
            "raw_note": "safe-looking value",
            "request": _handoff_request().to_json_dict(),
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
        _initialized_transport(),
        claude_desktop_tool_alias(TOOL_RUN_CONTRACT_SMOKE),
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
        _initialized_transport(),
        claude_desktop_tool_alias(TOOL_RUN_CONTRACT_SMOKE),
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
                "name": claude_desktop_tool_alias(TOOL_GET_POLICY_SUMMARY),
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
    transport = _initialized_transport()

    response = _call_tool(
        transport,
        claude_desktop_tool_alias(TOOL_GET_POLICY_SUMMARY),
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
    assert (
        kcs_adapters.TOOL_RUN_APPROVED_SUMMARY_PIPELINE
        == TOOL_RUN_APPROVED_SUMMARY_PIPELINE
    )
    assert kcs_adapters.TOOL_VALIDATE_DRAFT_RESPONSE == TOOL_VALIDATE_DRAFT_RESPONSE
