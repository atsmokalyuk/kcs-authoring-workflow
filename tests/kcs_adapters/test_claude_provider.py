from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

import kcs_adapters
from kcs_adapters.claude_provider import (
    CLAUDE_PROVIDER_ATTEMPT_SCHEMA_VERSION,
    CLAUDE_PROVIDER_CONFIG_SCHEMA_VERSION,
    CLAUDE_PROVIDER_PREFLIGHT_SCHEMA_VERSION,
    CLAUDE_PROVIDER_SMOKE_RESULT_SCHEMA_VERSION,
    ClaudeProviderConfig,
    ClaudeProviderSmokeErrorCode,
    ClaudeProviderSmokeResult,
    ClaudeProviderTransportMode,
    DirectHttpClaudeProviderClient,
    DirectHttpRuntimeConfig,
    FakeClaudeProviderClient,
    build_claude_provider_attempt_packet,
    build_claude_provider_preflight,
    run_claude_provider_smoke,
)
from kcs_core.claude_draft import (
    CLAUDE_DRAFT_RESPONSE_SCHEMA_VERSION,
    ClaudeDraftProviderErrorCode,
    ClaudeDraftStatus,
    KcsClaudeDraftRequestPacket,
    build_claude_draft_request,
)
from kcs_core.claude_handoff import (
    CLAUDE_HANDOFF_RESPONSE_SCHEMA_VERSION,
    ClaudeHandoffProviderErrorCode,
    ClaudeHandoffProviderStatus,
    KcsClaudeHandoffRequestPacket,
)
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import dump_json_dict
from kcs_core.models import (
    ArticleType,
    DecisionStatus,
    ReadinessState,
    RecommendedAction,
)


def _handoff_request(**overrides: object) -> KcsClaudeHandoffRequestPacket:
    payload: dict[str, object] = {
        "case_ref": "case-001",
        "handoff_purpose": "reviewer_assist_notes",
        "handoff_ref": "handoff-001",
        "item_ref": "item-001",
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
            "short_public_safe_summary": "Synthetic safe handoff context.",
            "status_codes": ["decision_status_decision_ready"],
            "title_hint": "Safe synthetic title",
            "warning_codes": [],
        },
        "operator_override": {
            "allowed_override_modes": [],
            "operator_override_allowed": False,
            "override_status": "not_requested",
        },
        "artifact_refs": {
            "reviewer_packet_ref": "",
            "reviewer_packet_sha256": "",
            "zendesk_source_ref": "",
            "zendesk_source_sha256": "",
        },
        "schema_version": "kcs_claude_handoff_request_v1",
    }
    payload.update(overrides)
    return KcsClaudeHandoffRequestPacket.from_json_dict(payload)


def _draft_request() -> KcsClaudeDraftRequestPacket:
    return build_claude_draft_request(_handoff_request(), draft_ref="draft-001")


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
        "reviewer_assist_notes": ["Reviewer should confirm the safe title."],
        "schema_version": CLAUDE_HANDOFF_RESPONSE_SCHEMA_VERSION,
        "structured_comments": {
            "comment_codes": ["title_review_suggested"],
            "needs_reviewer_attention": True,
        },
    }
    payload.update(overrides)
    return payload


def _draft_response(
    request: KcsClaudeDraftRequestPacket | None = None,
    **overrides: object,
) -> dict[str, object]:
    request = request or _draft_request()
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
        "reviewer_notes": ["Reviewer should confirm the safe draft."],
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


def _direct_config() -> ClaudeProviderConfig:
    return ClaudeProviderConfig(
        provider_profile="approved_provider",
        transport_mode=ClaudeProviderTransportMode.DIRECT_HTTP.value,
        model_ref="claude-sonnet-safe",
        endpoint_ref="approved-claude-endpoint",
        credentials_source_ref="approved-provider-auth",
    )


def _runtime_config() -> DirectHttpRuntimeConfig:
    return DirectHttpRuntimeConfig(
        endpoint_url="https://provider.invalid/kcs",
        api_key="runtime-auth-placeholder",
        model="claude-runtime-model",
    )


def _validated_summary(request_kind: str = "handoff") -> dict[str, object]:
    schema = (
        CLAUDE_HANDOFF_RESPONSE_SCHEMA_VERSION
        if request_kind == "handoff"
        else CLAUDE_DRAFT_RESPONSE_SCHEMA_VERSION
    )
    return {
        "provider_error_code": "none",
        "provider_status": "accepted",
        "response_kind": request_kind,
        "response_schema_version": schema,
        "response_sha256": "0" * 64,
        "validation_ok": True,
    }


def test_config_is_safe_serializable_and_preflight_keeps_runtime_secret_out() -> None:
    config = _direct_config()
    runtime = _runtime_config()
    preflight = build_claude_provider_preflight(config, runtime_config=runtime)
    config_payload = dump_json_dict(config)
    preflight_payload = dump_json_dict(preflight)

    assert config_payload["schema_version"] == CLAUDE_PROVIDER_CONFIG_SCHEMA_VERSION
    assert preflight_payload["schema_version"] == (
        CLAUDE_PROVIDER_PREFLIGHT_SCHEMA_VERSION
    )
    assert preflight_payload["ready_for_live_smoke"] is True
    assert preflight_payload["ready_for_real_ticket_use"] is False
    assert "provider.invalid" not in repr(config_payload)
    assert "runtime-auth-placeholder" not in repr(preflight_payload)
    assert "runtime-auth-placeholder" not in repr(runtime)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("endpoint_ref", "https://provider.example/kcs"),
        ("credentials_source_ref", "token=SECRET"),
        ("credentials_source_ref", "/path/to/token"),
        ("credentials_source_ref", "env:ANTHROPIC_API_KEY=secret"),
        ("credentials_source_ref", "ANTHROPIC_API_KEY"),
        ("model_ref", "claude model"),
    ],
)
def test_config_rejects_raw_runtime_or_secret_like_values(
    field: str,
    value: object,
) -> None:
    values = _direct_config().to_json_dict()
    values[field] = value

    with pytest.raises(ContractValidationError) as captured:
        ClaudeProviderConfig.from_json_dict(values)

    assert str(value) not in str(captured.value)


@pytest.mark.parametrize(
    "endpoint_url",
    [
        "https://user:pass@provider.invalid/kcs",
        "https://provider.invalid/kcs?token=SECRET",
        "https://provider.invalid/kcs#secret",
        "https://provider.invalid/kcs\nfoo",
        "https://provider.invalid/kcs\r\nx-extra: value",
        "https://provider.invalid/kcs\x00foo",
        "http://provider.invalid/kcs",
    ],
)
def test_runtime_config_rejects_unsafe_endpoint_url(endpoint_url: str) -> None:
    with pytest.raises(ContractValidationError):
        DirectHttpRuntimeConfig(
            endpoint_url=endpoint_url,
            api_key="runtime-auth-placeholder",
            model="claude-runtime-model",
        )


@pytest.mark.parametrize(
    "model",
    ["token=SECRET", "model with spaces", "/path/to/model"],
)
def test_runtime_config_rejects_unsafe_model_ref(model: str) -> None:
    with pytest.raises(ContractValidationError):
        DirectHttpRuntimeConfig(
            endpoint_url="https://provider.invalid/kcs",
            api_key="runtime-auth-placeholder",
            model=model,
        )


def test_runtime_config_rejects_header_injection_in_api_key() -> None:
    with pytest.raises(ContractValidationError):
        DirectHttpRuntimeConfig(
            endpoint_url="https://provider.invalid/kcs",
            api_key="runtime-auth-placeholder\nx-extra: value",
            model="claude-runtime-model",
        )


def test_direct_http_requires_approved_provider_profile() -> None:
    with pytest.raises(ContractValidationError):
        ClaudeProviderConfig(
            provider_profile="fake_provider",
            transport_mode=ClaudeProviderTransportMode.DIRECT_HTTP.value,
            model_ref="claude-sonnet-safe",
            endpoint_ref="approved-claude-endpoint",
            credentials_source_ref="approved-provider-auth",
        )


def test_fake_transport_requires_fake_provider_profile() -> None:
    with pytest.raises(ContractValidationError):
        ClaudeProviderConfig(
            provider_profile="approved_provider",
            transport_mode=ClaudeProviderTransportMode.FAKE_PROVIDER.value,
            model_ref="claude-sonnet-safe",
        )


def test_direct_http_preflight_requires_safe_endpoint_and_credential_refs() -> None:
    config = ClaudeProviderConfig(
        provider_profile="approved_provider",
        transport_mode=ClaudeProviderTransportMode.DIRECT_HTTP.value,
        model_ref="claude-sonnet-safe",
        endpoint_ref="",
        credentials_source_ref="",
    )

    report = build_claude_provider_preflight(
        config,
        runtime_config=_runtime_config(),
    )

    assert report.transport_supported is True
    assert report.ready_for_live_smoke is False
    assert "endpoint_ref_missing" in report.failed_checks
    assert "credentials_source_ref_missing" in report.failed_checks


@pytest.mark.parametrize(
    "transport_mode",
    [
        ClaudeProviderTransportMode.INTERNAL_SERVICE.value,
        ClaudeProviderTransportMode.MCP_CLIENT.value,
    ],
)
def test_future_transports_are_not_ready_in_kcs_11(transport_mode: str) -> None:
    config = ClaudeProviderConfig(transport_mode=transport_mode)
    report = build_claude_provider_preflight(config)

    assert report.transport_supported is False
    assert report.ready_for_live_smoke is False
    assert report.ready_for_real_ticket_use is False
    assert "transport_not_supported" in report.failed_checks


def test_attempt_packets_derive_handoff_and_draft_schema_without_raw_payload() -> None:
    config = ClaudeProviderConfig()
    handoff_attempt = build_claude_provider_attempt_packet(_handoff_request(), config)
    draft_attempt = build_claude_provider_attempt_packet(_draft_request(), config)

    assert handoff_attempt.schema_version == CLAUDE_PROVIDER_ATTEMPT_SCHEMA_VERSION
    assert handoff_attempt.request_kind == "handoff"
    assert handoff_attempt.request_schema_version == "kcs_claude_handoff_request_v1"
    assert draft_attempt.request_kind == "draft"
    assert draft_attempt.request_schema_version == "kcs_claude_draft_request_v1"
    assert draft_attempt.ready_for_real_ticket_use is False
    assert draft_attempt.raw_context_included is False
    assert "Synthetic safe handoff context" not in repr(draft_attempt.to_json_dict())


def test_attempt_builder_rejects_unsupported_request_object() -> None:
    with pytest.raises(ContractValidationError):
        build_claude_provider_attempt_packet(object(), ClaudeProviderConfig())  # type: ignore[arg-type]


def test_fake_provider_smoke_validates_handoff_response() -> None:
    request = _handoff_request()
    result = run_claude_provider_smoke(
        request,
        client=FakeClaudeProviderClient(handoff_response=_handoff_response(request)),
        config=ClaudeProviderConfig(),
    )
    payload = dump_json_dict(result)

    assert payload["schema_version"] == CLAUDE_PROVIDER_SMOKE_RESULT_SCHEMA_VERSION
    assert payload["provider_called"] is True
    assert payload["response_valid"] is True
    assert payload["provider_error_code"] == "none"
    assert payload["ready_for_real_ticket_use"] is False
    assert payload["auto_publish_allowed"] is False
    assert payload["public_output_approved"] is False
    assert payload["validated_response"]["response_kind"] == "handoff"


def test_fake_provider_smoke_validates_draft_without_carrying_html_body() -> None:
    request = _draft_request()
    result = run_claude_provider_smoke(
        request,
        client=FakeClaudeProviderClient(draft_response=_draft_response(request)),
        config=ClaudeProviderConfig(),
    )
    payload = dump_json_dict(result)

    assert payload["response_valid"] is True
    assert payload["validated_response"]["response_kind"] == "draft"
    assert payload["validated_response"]["response_sha256"]
    assert "zendesk_source_html" not in repr(payload)
    assert "Plesk task fails with a reusable error" not in repr(payload)


@pytest.mark.parametrize(
    "response",
    [
        {"auto_publish_allowed": True},
        "<html>not json</html>",
        b'["not", "object"]',
        b'{"schema_version": NaN}',
        b'{"error": "token=SECRET person@example.com"}',
    ],
)
def test_direct_http_invalid_provider_response_is_safe(response: object) -> None:
    request = _handoff_request()
    transport = _FakeHttpTransport(response=response)
    client = DirectHttpClaudeProviderClient(
        config=_direct_config(),
        runtime_config=_runtime_config(),
        transport=transport,
    )

    result = run_claude_provider_smoke(
        request,
        client=client,
        config=_direct_config(),
    )

    assert result.provider_called is True
    assert result.response_valid is False
    assert result.provider_error_code == (
        ClaudeProviderSmokeErrorCode.PROVIDER_RESPONSE_INVALID.value
    )
    assert "SECRET" not in repr(result.to_json_dict())
    assert "person@example.com" not in repr(result.to_json_dict())


def test_direct_http_oversized_response_is_rejected_safely() -> None:
    request = _handoff_request()
    transport = _FakeHttpTransport(response=b'{"text":"' + b"a" * 70000 + b'"}')
    client = DirectHttpClaudeProviderClient(
        config=_direct_config(),
        runtime_config=_runtime_config(),
        transport=transport,
    )

    result = run_claude_provider_smoke(
        request,
        client=client,
        config=_direct_config(),
    )

    assert result.provider_called is True
    assert result.response_valid is False
    assert result.provider_error_code == "provider_response_invalid"
    assert "aaaaaaaa" not in repr(result.to_json_dict())


def test_direct_http_transport_payload_is_bounded_wrapper_plus_request() -> None:
    request = _handoff_request()
    transport = _FakeHttpTransport(response=_handoff_response(request))
    client = DirectHttpClaudeProviderClient(
        config=_direct_config(),
        runtime_config=_runtime_config(),
        transport=transport,
    )

    result = run_claude_provider_smoke(
        request,
        client=client,
        config=_direct_config(),
    )

    assert result.response_valid is True
    assert transport.calls == 1
    assert set(transport.payload) == {
        "instruction",
        "request",
        "request_kind",
        "schema_version",
    }
    assert transport.payload["request"] == request.to_json_dict()
    assert "custom_prompt" not in repr(transport.payload)
    assert "evidence_basis" not in repr(transport.payload)
    assert transport.timeout_seconds == _direct_config().timeout_seconds


def test_direct_http_transport_exception_is_safe_provider_failed() -> None:
    client = DirectHttpClaudeProviderClient(
        config=_direct_config(),
        runtime_config=_runtime_config(),
        transport=_FailingHttpTransport(),
    )

    result = run_claude_provider_smoke(
        _handoff_request(),
        client=client,
        config=_direct_config(),
    )

    assert result.provider_called is True
    assert result.response_valid is False
    assert result.provider_error_code == "provider_failed"
    assert "provider.invalid" not in repr(result.to_json_dict())
    assert "SECRET" not in repr(result.to_json_dict())


def test_direct_http_method_request_kind_mismatch_fails_before_transport_call() -> None:
    transport = _FakeHttpTransport(response=_draft_response())
    client = DirectHttpClaudeProviderClient(
        config=_direct_config(),
        runtime_config=_runtime_config(),
        transport=transport,
    )

    with pytest.raises(ContractValidationError):
        client.submit_draft(_handoff_request())  # type: ignore[arg-type]

    assert transport.calls == 0


def test_direct_http_handoff_method_rejects_draft_request_before_call() -> None:
    transport = _FakeHttpTransport(response=_handoff_response())
    client = DirectHttpClaudeProviderClient(
        config=_direct_config(),
        runtime_config=_runtime_config(),
        transport=transport,
    )

    with pytest.raises(ContractValidationError):
        client.submit_handoff(_draft_request())  # type: ignore[arg-type]

    assert transport.calls == 0


def test_provider_exception_returns_safe_failed_smoke_result() -> None:
    class FailingClient:
        @property
        def transport_mode(self) -> str:
            return ClaudeProviderTransportMode.FAKE_PROVIDER.value

        def submit_handoff(self, request: KcsClaudeHandoffRequestPacket) -> object:
            raise RuntimeError("token=SECRET https://provider.invalid/private")

        def submit_draft(self, request: KcsClaudeDraftRequestPacket) -> object:
            raise AssertionError("not used")

    result = run_claude_provider_smoke(
        _handoff_request(),
        client=FailingClient(),
        config=ClaudeProviderConfig(),
    )

    assert result.provider_called is True
    assert result.response_valid is False
    assert result.provider_error_code == "provider_failed"
    assert result.raw_error_echoed is False
    assert "SECRET" not in repr(result.to_json_dict())
    assert "provider.invalid" not in repr(result.to_json_dict())


def test_smoke_rejects_client_transport_mismatch() -> None:
    result = run_claude_provider_smoke(
        _handoff_request(),
        client=FakeClaudeProviderClient(handoff_response=_handoff_response()),
        config=_direct_config(),
    )

    assert result.provider_called is False
    assert result.response_valid is False
    assert result.provider_error_code == "transport_not_supported"


def test_smoke_result_rejects_valid_response_without_validated_summary() -> None:
    with pytest.raises(ContractValidationError):
        ClaudeProviderSmokeResult(
            request_kind="handoff",
            provider_called=False,
            response_valid=True,
            provider_status="accepted",
            provider_error_code="none",
            validated_response={},
        )


def test_smoke_result_rejects_response_kind_mismatch() -> None:
    with pytest.raises(ContractValidationError):
        ClaudeProviderSmokeResult(
            request_kind="handoff",
            provider_called=True,
            response_valid=True,
            provider_status="accepted",
            provider_error_code="none",
            validated_response=_validated_summary("draft"),
        )


def test_smoke_result_rejects_invalid_response_with_none_error_code() -> None:
    with pytest.raises(ContractValidationError):
        ClaudeProviderSmokeResult(
            request_kind="handoff",
            provider_called=True,
            response_valid=False,
            provider_status="failed",
            provider_error_code="none",
            validated_response={},
        )


def test_smoke_result_rejects_failed_response_with_validated_summary() -> None:
    with pytest.raises(ContractValidationError):
        ClaudeProviderSmokeResult(
            request_kind="handoff",
            provider_called=True,
            response_valid=False,
            provider_status="failed",
            provider_error_code="provider_response_invalid",
            validated_response=_validated_summary(),
        )


def test_provider_output_cannot_set_publish_flags_or_action_authority() -> None:
    request = _handoff_request()
    response = _handoff_response(
        request,
        auto_publish_allowed=True,
        reviewer_assist_notes=["Provider recommends flag_existing."],
    )

    result = run_claude_provider_smoke(
        request,
        client=FakeClaudeProviderClient(handoff_response=response),
        config=ClaudeProviderConfig(),
    )

    assert result.response_valid is False
    assert result.provider_error_code == "provider_response_invalid"
    assert result.auto_publish_allowed is False
    assert result.public_output_approved is False


def test_adapter_package_exports_include_kcs_11_api() -> None:
    assert kcs_adapters.ClaudeProviderConfig is ClaudeProviderConfig
    assert kcs_adapters.FakeClaudeProviderClient is FakeClaudeProviderClient
    assert (
        kcs_adapters.DirectHttpClaudeProviderClient
        is DirectHttpClaudeProviderClient
    )
    assert (
        kcs_adapters.build_claude_provider_preflight
        is build_claude_provider_preflight
    )
    assert kcs_adapters.run_claude_provider_smoke is run_claude_provider_smoke


def test_no_mcp_runtime_client_is_implemented_in_kcs_11() -> None:
    assert not hasattr(kcs_adapters, "McpClaudeProviderClient")


class _FakeHttpTransport:
    def __init__(self, *, response: object) -> None:
        self.response = response
        self.calls = 0
        self.payload: Mapping[str, object] = {}
        self.timeout_seconds = 0

    def post_json(
        self,
        *,
        endpoint_url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, object],
        timeout_seconds: int,
        max_response_bytes: int,
    ) -> Mapping[str, Any] | bytes | str:
        self.calls += 1
        self.payload = payload
        self.timeout_seconds = timeout_seconds
        assert endpoint_url == "https://provider.invalid/kcs"
        assert headers["authorization"].startswith("Bearer ")
        if isinstance(self.response, Mapping | bytes | str):
            return self.response
        return self.response  # type: ignore[return-value]


class _FailingHttpTransport:
    def post_json(
        self,
        *,
        endpoint_url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, object],
        timeout_seconds: int,
        max_response_bytes: int,
    ) -> Mapping[str, Any] | bytes | str:
        raise RuntimeError("SECRET from https://provider.invalid/private")
