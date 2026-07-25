from __future__ import annotations

from collections.abc import Mapping

import pytest

from kcs_adapters.desktop_mcp_adapter import KcsDesktopMcpAdapter, McpToolResult
from kcs_adapters.desktop_reuse_comparison import REUSE_COMPARISON_OUTCOMES
from kcs_adapters.desktop_semantic_providers import (
    FixtureSemanticExtractionProvider,
)
from kcs_adapters.desktop_tool_names import (
    TOOL_CONFIRM_REUSE_COMPARISON,
    TOOL_REGISTER_CLEAN_TICKET,
)
from kcs_adapters.operator_authoring_controller import (
    OperatorAuthoringController,
    OperatorAuthoringControllerError,
)
from kcs_core.reuse_comparison import (
    ReuseComparisonCandidate,
    ReuseComparisonEvidence,
    ReuseComparisonEvidenceRequest,
    ReuseComparisonExcerpt,
)


class _RecordingAdapter:
    def __init__(
        self,
        results: list[McpToolResult],
        *,
        reuse_comparison_enabled: bool = True,
    ) -> None:
        self.results = results
        self.reuse_comparison_enabled = reuse_comparison_enabled
        self.calls: list[tuple[str, Mapping[str, object]]] = []

    def call_tool(
        self,
        name: str,
        arguments: Mapping[str, object] | None = None,
    ) -> McpToolResult:
        self.calls.append((name, arguments or {}))
        return self.results.pop(0)

    def begin_operator_reuse_comparison(
        self,
        ticket_ref: str,
    ) -> McpToolResult:
        self.calls.append(
            ("begin_operator_reuse_comparison", {"ticket_ref": ticket_ref})
        )
        return self.results.pop(0)


class _FixtureComparisonProvider:
    def collect_comparison_evidence(
        self,
        request: ReuseComparisonEvidenceRequest,
    ) -> ReuseComparisonEvidence:
        assert request.symptoms
        public_url = (
            "https://support.plesk.com/hc/en-us/articles/"
            "123456-Example-monitoring-article"
        )
        excerpt = ReuseComparisonExcerpt(
            excerpt_ref="public-excerpt-123456",
            section_path="Resolution",
            citation=f"Example monitoring article — Resolution — {public_url}",
            text="Restart the monitoring service and verify that graphs load.",
            token_count=9,
        )
        candidate = ReuseComparisonCandidate(
            rank=1,
            source_doc_id="plesk-support://123456",
            source_type="support",
            title="Example monitoring article",
            public_url=public_url,
            article_status="active",
            updated_at="2026-07-01",
            origin="search_result",
            excerpts=(excerpt,),
        )
        return ReuseComparisonEvidence(
            searched=True,
            status="comparison_evidence_ready",
            search_run_ref="comparison-run-controller-001",
            explicit_reference_status="not_provided",
            candidates=(candidate,),
        )


def _comparison_required_result() -> dict[str, object]:
    return {
        "auto_publish_allowed": False,
        "comparison_candidates": [
            {
                "candidate_ref": "comparison-candidate-001",
                "excerpts": [],
                "public_url": (
                    "https://support.plesk.com/hc/en-us/articles/123456"
                ),
                "title": "Example article",
            }
        ],
        "comparison_outcomes": list(REUSE_COMPARISON_OUTCOMES),
        "comparison_ref": "reuse-comparison-001",
        "draft_generated": False,
        "ok": True,
        "result_kind": "reuse_comparison_required",
        "reviewer_bundle_written": False,
        "schema_version": "kcs_mcp_tool_result_v1",
        "writes_files": False,
    }


def test_begin_calls_draft_ticket_directly_without_model_routing() -> None:
    adapter = _RecordingAdapter(
        [McpToolResult(ok=True, result=_comparison_required_result())]
    )

    result = OperatorAuthoringController(adapter).begin("ticket-001")

    assert result["result_kind"] == "reuse_comparison_required"
    assert adapter.calls == [
        (
            "begin_operator_reuse_comparison",
            {"ticket_ref": "ticket-001"},
        )
    ]


def test_begin_fails_before_tool_call_when_gate_is_unavailable() -> None:
    adapter = _RecordingAdapter([], reuse_comparison_enabled=False)

    with pytest.raises(
        OperatorAuthoringControllerError,
        match="operator_entrypoint_gate_unavailable",
    ):
        OperatorAuthoringController(adapter).begin("ticket-001")

    assert adapter.calls == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("draft_generated", True),
        ("reviewer_bundle_written", True),
        ("writes_files", True),
        ("result_kind", "draft_article_authoring"),
    ],
)
def test_begin_fails_closed_for_prohibited_first_result(
    field: str,
    value: object,
) -> None:
    first = _comparison_required_result()
    first[field] = value
    adapter = _RecordingAdapter([McpToolResult(ok=True, result=first)])

    with pytest.raises(
        OperatorAuthoringControllerError,
        match="operator_entrypoint_invariant_violated",
    ):
        OperatorAuthoringController(adapter).begin("ticket-001")


def test_confirm_calls_existing_submit_tool_in_same_adapter() -> None:
    adapter = _RecordingAdapter(
        [
            McpToolResult(ok=True, result=_comparison_required_result()),
            McpToolResult(
                ok=True,
                result={
                    "comparison_outcome": "reuse",
                    "draft_generated": False,
                    "ok": True,
                    "result_kind": "reuse_comparison_completed",
                    "reviewer_bundle_written": False,
                    "schema_version": "kcs_mcp_tool_result_v1",
                    "writes_files": False,
                },
            )
        ]
    )
    controller = OperatorAuthoringController(adapter)
    comparison = controller.begin("ticket-001")

    result = controller.confirm(
        comparison_ref=str(comparison["comparison_ref"]),
        outcome="reuse",
        candidate_ref="comparison-candidate-001",
    )

    assert result["comparison_outcome"] == "reuse"
    assert adapter.calls[1:] == [
        (
            TOOL_CONFIRM_REUSE_COMPARISON,
            {
                "candidate_ref": "comparison-candidate-001",
                "comparison_ref": "reuse-comparison-001",
                "outcome": "reuse",
            },
        )
    ]


@pytest.mark.parametrize("outcome", ["reuse", "update", "need_more_evidence"])
def test_confirm_fails_closed_if_no_draft_outcome_writes(
    outcome: str,
) -> None:
    adapter = _RecordingAdapter(
        [
            McpToolResult(ok=True, result=_comparison_required_result()),
            McpToolResult(
                ok=True,
                result={
                    "auto_publish_allowed": False,
                    "comparison_outcome": outcome,
                    "draft_generated": True,
                    "ok": True,
                    "public_output_approved": False,
                    "publishes": False,
                    "result_kind": "draft_article_authoring",
                    "reviewer_bundle_written": True,
                    "schema_version": "kcs_mcp_tool_result_v1",
                    "writes_files": True,
                },
            )
        ]
    )
    controller = OperatorAuthoringController(adapter)
    comparison = controller.begin("ticket-001")

    with pytest.raises(
        OperatorAuthoringControllerError,
        match="operator_entrypoint_confirmation_failed",
    ):
        controller.confirm(
            comparison_ref=str(comparison["comparison_ref"]),
            outcome=outcome,
            candidate_ref=(
                "comparison-candidate-001"
                if outcome in {"reuse", "update"}
                else None
            ),
        )


def test_submit_failure_packet_is_not_a_successful_confirmation() -> None:
    adapter = _RecordingAdapter(
        [
            McpToolResult(ok=True, result=_comparison_required_result()),
            McpToolResult(
                ok=True,
                result={
                    "debug_code": "reuse_comparison_expired",
                    "draft_generated": False,
                    "ok": False,
                    "result_kind": "reuse_comparison_submit_failed",
                    "reviewer_bundle_written": False,
                    "schema_version": "kcs_mcp_tool_result_v1",
                    "writes_files": False,
                },
            ),
        ]
    )
    controller = OperatorAuthoringController(adapter)
    comparison = controller.begin("ticket-001")

    with pytest.raises(
        OperatorAuthoringControllerError,
        match="operator_entrypoint_confirmation_failed",
    ):
        controller.confirm(
            comparison_ref=str(comparison["comparison_ref"]),
            outcome="need_more_evidence",
        )


@pytest.mark.parametrize("outcome", ["reuse", "update", "need_more_evidence"])
def test_real_controller_terminal_outcomes_do_not_create_draft(
    outcome: str,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    bundle_root = tmp_path / "local-data" / "reviewer-bundles"
    adapter = KcsDesktopMcpAdapter(
        reviewer_bundle_root=bundle_root,
        semantic_extraction_provider=FixtureSemanticExtractionProvider(),
        reuse_comparison_provider=_FixtureComparisonProvider(),
    )
    registered = adapter.call_tool(
        TOOL_REGISTER_CLEAN_TICKET,
        {
            "clean_ticket_text": (
                "Customer Ticket Content\n"
                "Title: Monitoring graphs show no data\n"
                "Applicable To: Plesk for Linux\n"
                "Symptoms:\n"
                "- Monitoring graphs show no data.\n"
                "Cause:\n"
                "- The monitoring service is inactive.\n"
                "Resolution:\n"
                "- Restart the monitoring service and verify the graphs."
            ),
            "ticket_ref": "controller-ticket-001",
        },
    )
    assert registered.ok is True
    controller = OperatorAuthoringController(adapter)

    comparison = controller.begin("controller-ticket-001")

    assert comparison["result_kind"] == "reuse_comparison_required"
    assert comparison["draft_generated"] is False
    assert not bundle_root.exists()

    candidate_ref = (
        "comparison-candidate-001" if outcome in {"reuse", "update"} else None
    )
    final = controller.confirm(
        comparison_ref=str(comparison["comparison_ref"]),
        outcome=outcome,
        candidate_ref=candidate_ref,
    )

    assert final["comparison_outcome"] == outcome
    assert final["draft_generated"] is False
    assert final["reviewer_bundle_written"] is False
    assert not bundle_root.exists()


def test_real_controller_allows_none_fit_authoring_only_after_confirmation(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    bundle_root = tmp_path / "local-data" / "reviewer-bundles"
    adapter = KcsDesktopMcpAdapter(
        reviewer_bundle_root=bundle_root,
        semantic_extraction_provider=FixtureSemanticExtractionProvider(),
        reuse_comparison_provider=_FixtureComparisonProvider(),
    )
    registered = adapter.call_tool(
        TOOL_REGISTER_CLEAN_TICKET,
        {
            "clean_ticket_text": (
                "Customer Ticket Content\n"
                "Title: Monitoring graphs show no data\n"
                "Applicable To: Plesk for Linux\n"
                "Symptoms: Monitoring graphs show no data.\n"
                "Cause: The monitoring service is inactive.\n"
                "Resolution: Restart the monitoring service and verify the graphs."
            ),
            "ticket_ref": "controller-ticket-none-fit",
        },
    )
    assert registered.ok is True
    controller = OperatorAuthoringController(adapter)
    comparison = controller.begin("controller-ticket-none-fit")

    assert comparison["draft_generated"] is False
    assert not bundle_root.exists()

    final = controller.confirm(
        comparison_ref=str(comparison["comparison_ref"]),
        outcome="none_fit",
    )

    assert final["draft_generated"] is True
    assert final["reviewer_bundle_written"] is True
    assert bundle_root.is_dir()


def test_controller_rejects_replayed_confirmation_before_adapter_call(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    adapter = KcsDesktopMcpAdapter(
        reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles",
        semantic_extraction_provider=FixtureSemanticExtractionProvider(),
        reuse_comparison_provider=_FixtureComparisonProvider(),
    )
    registered = adapter.call_tool(
        TOOL_REGISTER_CLEAN_TICKET,
        {
            "clean_ticket_text": (
                "Customer Ticket Content\n"
                "Title: Monitoring graphs show no data\n"
                "Applicable To: Plesk for Linux\n"
                "Symptoms: Monitoring graphs show no data.\n"
                "Cause: The monitoring service is inactive.\n"
                "Resolution: Restart the monitoring service and verify the graphs."
            ),
            "ticket_ref": "controller-ticket-replay",
        },
    )
    assert registered.ok is True
    controller = OperatorAuthoringController(adapter)
    comparison = controller.begin("controller-ticket-replay")
    arguments = {
        "comparison_ref": str(comparison["comparison_ref"]),
        "outcome": "need_more_evidence",
    }

    first = controller.confirm(**arguments)

    assert first["comparison_outcome"] == "need_more_evidence"
    with pytest.raises(
        OperatorAuthoringControllerError,
        match="operator_entrypoint_session_unavailable",
    ):
        controller.confirm(**arguments)


def test_controller_rejects_confirmation_without_its_own_begin() -> None:
    adapter = _RecordingAdapter([])

    with pytest.raises(
        OperatorAuthoringControllerError,
        match="operator_entrypoint_session_unavailable",
    ):
        OperatorAuthoringController(adapter).confirm(
            comparison_ref="reuse-comparison-001",
            outcome="need_more_evidence",
        )

    assert adapter.calls == []


def test_invalid_candidate_consumes_controller_session() -> None:
    adapter = _RecordingAdapter(
        [McpToolResult(ok=True, result=_comparison_required_result())]
    )
    controller = OperatorAuthoringController(adapter)
    comparison = controller.begin("ticket-001")

    with pytest.raises(
        OperatorAuthoringControllerError,
        match="operator_entrypoint_confirmation_invalid",
    ):
        controller.confirm(
            comparison_ref=str(comparison["comparison_ref"]),
            outcome="reuse",
            candidate_ref="comparison-candidate-999",
        )
    with pytest.raises(
        OperatorAuthoringControllerError,
        match="operator_entrypoint_session_unavailable",
    ):
        controller.confirm(
            comparison_ref=str(comparison["comparison_ref"]),
            outcome="reuse",
            candidate_ref="comparison-candidate-001",
        )


def test_invalid_outcome_consumes_controller_session() -> None:
    adapter = _RecordingAdapter(
        [McpToolResult(ok=True, result=_comparison_required_result())]
    )
    controller = OperatorAuthoringController(adapter)
    comparison = controller.begin("ticket-001")

    with pytest.raises(
        OperatorAuthoringControllerError,
        match="operator_entrypoint_outcome_invalid",
    ):
        controller.confirm(
            comparison_ref=str(comparison["comparison_ref"]),
            outcome="draft_anyway",
        )
    with pytest.raises(
        OperatorAuthoringControllerError,
        match="operator_entrypoint_session_unavailable",
    ):
        controller.confirm(
            comparison_ref=str(comparison["comparison_ref"]),
            outcome="need_more_evidence",
        )

    assert len(adapter.calls) == 1
