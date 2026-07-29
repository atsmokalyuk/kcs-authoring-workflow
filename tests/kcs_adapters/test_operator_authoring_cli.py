from __future__ import annotations

import io
import sys
from collections.abc import Mapping

import pytest

from kcs_adapters import operator_authoring_cli
from kcs_adapters.desktop_mcp_adapter import McpToolResult
from kcs_adapters.desktop_reuse_comparison import REUSE_COMPARISON_OUTCOMES
from kcs_adapters.operator_authoring_cli import run_interactive, run_preflight
from kcs_adapters.operator_authoring_controller import (
    OperatorAuthoringController,
)


class _RecordingAdapter:
    reuse_comparison_enabled = True

    def __init__(
        self,
        final: Mapping[str, object],
        *,
        first: Mapping[str, object] | None = None,
    ) -> None:
        self.first = dict(first) if first is not None else _comparison()
        self.final = dict(final)
        self.calls: list[tuple[str, Mapping[str, object]]] = []

    def call_tool(
        self,
        name: str,
        arguments: Mapping[str, object] | None = None,
    ) -> McpToolResult:
        self.calls.append((name, arguments or {}))
        return McpToolResult(ok=True, result=dict(self.final))

    def begin_operator_reuse_comparison(
        self,
        ticket_ref: str,
    ) -> McpToolResult:
        self.calls.append(
            ("begin_operator_reuse_comparison", {"ticket_ref": ticket_ref})
        )
        return McpToolResult(ok=True, result=self.first)


class _OrderCheckingInput(io.StringIO):
    def __init__(self, value: str, output: io.StringIO) -> None:
        super().__init__(value)
        self.output = output

    def readline(self, *args, **kwargs) -> str:
        rendered = self.output.getvalue()
        assert "Reusable article candidates:" in rendered
        assert "Choose outcome:" in rendered
        return super().readline(*args, **kwargs)


def _comparison() -> dict[str, object]:
    return {
        "auto_publish_allowed": False,
        "accepted_ticket_facts": ["Monitoring graphs show no data."],
        "comparison_candidates": [
            {
                "candidate_ref": "comparison-candidate-001",
                "excerpts": [
                    {
                        "section_path": "Resolution",
                        "text": "Restart the monitoring service.",
                    }
                ],
                "public_url": (
                    "https://support.plesk.com/hc/en-us/articles/123456"
                ),
                "title": "Example monitoring article",
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


def test_cli_shows_comparison_before_reading_operator_outcome() -> None:
    adapter = _RecordingAdapter(
        {
            "comparison_outcome": "need_more_evidence",
            "draft_generated": False,
            "ok": True,
            "result_kind": "reuse_comparison_completed",
            "reviewer_bundle_written": False,
            "schema_version": "kcs_mcp_tool_result_v1",
            "writes_files": False,
        }
    )
    output = io.StringIO()

    status = run_interactive(
        controller=OperatorAuthoringController(adapter),
        ticket_ref="ticket-001",
        input_stream=_OrderCheckingInput("4\n", output),
        output_stream=output,
    )

    assert status == 0
    assert "Recorded outcome: need_more_evidence. No draft was generated." in (
        output.getvalue()
    )
    assert adapter.calls[1][1] == {
        "comparison_ref": "reuse-comparison-001",
        "outcome": "need_more_evidence",
    }


def test_cli_requires_displayed_candidate_for_reuse() -> None:
    adapter = _RecordingAdapter(
        {
            "comparison_outcome": "reuse",
            "draft_generated": False,
            "ok": True,
            "result_kind": "reuse_comparison_completed",
            "reviewer_bundle_written": False,
            "schema_version": "kcs_mcp_tool_result_v1",
            "writes_files": False,
        }
    )
    output = io.StringIO()

    status = run_interactive(
        controller=OperatorAuthoringController(adapter),
        ticket_ref="ticket-001",
        input_stream=io.StringIO("1\n1\n"),
        output_stream=output,
    )

    assert status == 0
    assert "Choose article: 1-1" in output.getvalue()
    assert adapter.calls[1][1] == {
        "candidate_ref": "comparison-candidate-001",
        "comparison_ref": "reuse-comparison-001",
        "outcome": "reuse",
    }


def test_none_fit_submits_once_only_after_menu_selection() -> None:
    adapter = _RecordingAdapter(
        {
            "auto_publish_allowed": False,
            "comparison_outcome": "none_fit",
            "comparison_sequence_outcomes": [
                {"comparison_outcome": "none_fit"}
            ],
            "draft_generated": True,
            "ok": True,
            "public_output_approved": False,
            "ready_for_real_ticket_use": False,
            "result_kind": "approved_summary_authoring",
            "schema_version": "kcs_mcp_tool_result_v1",
        }
    )
    output = io.StringIO()

    status = run_interactive(
        controller=OperatorAuthoringController(adapter),
        ticket_ref="ticket-001",
        input_stream=io.StringIO("3\n"),
        output_stream=output,
    )

    assert status == 0
    assert len(adapter.calls) == 2
    assert adapter.calls[1][1] == {
        "comparison_ref": "reuse-comparison-001",
        "outcome": "none_fit",
    }
    assert "Reviewer draft created." in output.getvalue()


def test_cli_fails_closed_after_three_invalid_choices() -> None:
    adapter = _RecordingAdapter({})
    output = io.StringIO()

    status = run_interactive(
        controller=OperatorAuthoringController(adapter),
        ticket_ref="ticket-001",
        input_stream=io.StringIO("bad\nstill-bad\nnope\n"),
        output_stream=output,
    )

    assert status == 2
    assert len(adapter.calls) == 1
    assert "Blocked: operator_entrypoint_outcome_not_confirmed" in (
        output.getvalue()
    )


def test_cli_compacts_long_multiline_public_excerpt() -> None:
    comparison = _comparison()
    candidates = comparison["comparison_candidates"]
    assert isinstance(candidates, list)
    candidate = candidates[0]
    assert isinstance(candidate, dict)
    excerpts = candidate["excerpts"]
    assert isinstance(excerpts, list)
    excerpts[0]["text"] = f"Relevant start\n\n{'navigation-noise ' * 80}hidden-tail"
    adapter = _RecordingAdapter(
        {
            "comparison_outcome": "need_more_evidence",
            "draft_generated": False,
            "ok": True,
            "result_kind": "reuse_comparison_completed",
            "reviewer_bundle_written": False,
            "schema_version": "kcs_mcp_tool_result_v1",
            "writes_files": False,
        },
        first=comparison,
    )
    output = io.StringIO()

    status = run_interactive(
        controller=OperatorAuthoringController(adapter),
        ticket_ref="ticket-001",
        input_stream=io.StringIO("4\n"),
        output_stream=output,
    )

    rendered = output.getvalue()
    assert status == 0
    assert "Relevant start navigation-noise" in rendered
    assert "hidden-tail" not in rendered
    assert "…" in rendered


def test_cli_bounds_facts_and_omits_unapproved_candidate_metadata() -> None:
    comparison = _comparison()
    comparison["accepted_ticket_facts"] = [
        f"Confirmed symptom\n\n{'fact-detail ' * 80}hidden-fact-tail"
    ]
    candidates = comparison["comparison_candidates"]
    assert isinstance(candidates, list)
    candidate = candidates[0]
    assert isinstance(candidate, dict)
    candidate["provider_query"] = "must-not-render"
    candidate["runtime_chunk_id"] = "private-chunk-001"
    adapter = _RecordingAdapter(
        {
            "comparison_outcome": "need_more_evidence",
            "draft_generated": False,
            "ok": True,
            "result_kind": "reuse_comparison_completed",
            "reviewer_bundle_written": False,
            "schema_version": "kcs_mcp_tool_result_v1",
            "writes_files": False,
        },
        first=comparison,
    )
    output = io.StringIO()

    status = run_interactive(
        controller=OperatorAuthoringController(adapter),
        ticket_ref="ticket-001",
        input_stream=io.StringIO("4\n"),
        output_stream=output,
    )

    rendered = output.getvalue()
    assert status == 0
    assert "Confirmed symptom fact-detail" in rendered
    assert "hidden-fact-tail" not in rendered
    assert "must-not-render" not in rendered
    assert "private-chunk-001" not in rendered
    assert "…" in rendered


def test_cli_removes_terminal_control_sequences_from_fact_display() -> None:
    comparison = _comparison()
    comparison["accepted_ticket_facts"] = [
        "Monitoring \x1b[31mgraphs\x1b[0m show no data."
    ]
    adapter = _RecordingAdapter(
        {
            "comparison_outcome": "need_more_evidence",
            "draft_generated": False,
            "ok": True,
            "result_kind": "reuse_comparison_completed",
            "reviewer_bundle_written": False,
            "schema_version": "kcs_mcp_tool_result_v1",
            "writes_files": False,
        },
        first=comparison,
    )
    output = io.StringIO()

    status = run_interactive(
        controller=OperatorAuthoringController(adapter),
        ticket_ref="ticket-001",
        input_stream=io.StringIO("4\n"),
        output_stream=output,
    )

    assert status == 0
    assert "\x1b" not in output.getvalue()


def test_main_rejects_non_tty_before_constructing_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stdin = io.StringIO("3\n")
    stdout = io.StringIO()
    stderr = io.StringIO()
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", stderr)

    def unexpected_controller() -> OperatorAuthoringController:
        raise AssertionError("adapter must not be constructed")

    monkeypatch.setattr(
        operator_authoring_cli,
        "production_controller",
        unexpected_controller,
    )

    status = operator_authoring_cli.main(["ticket-001"])

    assert status == 2
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == (
        "Blocked: operator_entrypoint_interactive_tty_required\n"
    )


def test_preflight_shows_comparison_without_submit() -> None:
    adapter = _RecordingAdapter({})
    output = io.StringIO()

    status = run_preflight(
        controller=OperatorAuthoringController(adapter),
        ticket_ref="ticket-001",
        output_stream=output,
    )

    assert status == 0
    assert len(adapter.calls) == 1
    assert "Reusable article candidates:" in output.getvalue()
    assert "Preflight complete. No outcome was submitted." in output.getvalue()
