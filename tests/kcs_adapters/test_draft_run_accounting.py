from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from kcs_adapters import desktop_tool_results
from kcs_adapters import draft_run_accounting as draft_run_accounting_module
from kcs_adapters.desktop_mcp_adapter import KcsDesktopMcpAdapter
from kcs_adapters.desktop_tool_names import (
    TOOL_CONFIRM_REUSE_COMPARISON,
    TOOL_DRAFT_ARTICLE,
    TOOL_DRAFT_TICKET,
    TOOL_PREPARE_SEMANTIC_REVIEW,
    TOOL_SUBMIT_SEMANTIC_REVIEW,
)
from kcs_adapters.draft_run_accounting import (
    DRAFT_RUN_ACCOUNTING_MODE_ENV,
    DRAFT_RUN_REPORT_DIR_ENV,
    DraftRunAccounting,
    DraftRunReport,
    LocalJsonDraftRunSink,
    draft_run_accounting_from_environment,
)

_CORRELATION = "a" * 64
_PRIVATE_CANARY = "PRIVATE-ticket-title.example/customer/314159"


class _CapturingSink:
    def __init__(self) -> None:
        self.reports: list[DraftRunReport] = []

    def checkpoint(self, report: DraftRunReport) -> None:
        self.reports.append(report)


class _FailingSink:
    def checkpoint(self, report: DraftRunReport) -> None:
        raise OSError("local sink unavailable")


def _accounting(sink: object) -> DraftRunAccounting:
    return DraftRunAccounting(
        sink,  # type: ignore[arg-type]
        correlation_factory=lambda: _CORRELATION,
    )


def test_report_projects_only_counts_codes_and_durations() -> None:
    sink = _CapturingSink()
    accounting = _accounting(sink)

    accounting.observe_tool_call(
        tool_name=TOOL_DRAFT_TICKET,
        arguments={"ticket_ref": f"ticket-{_PRIVATE_CANARY}"},
        result_ok=True,
        result={
            "debug_code": "semantic_identification_low_confidence",
            "next_required_action": "prepare_semantic_review",
            "ok": False,
        },
        error_code=None,
        duration_ms=11,
    )
    accounting.observe_tool_call(
        tool_name=TOOL_PREPARE_SEMANTIC_REVIEW,
        arguments={"semantic_review_ref": _PRIVATE_CANARY},
        result_ok=True,
        result={"ok": True, "packet": _PRIVATE_CANARY},
        error_code=None,
        duration_ms=12,
    )
    accounting.observe_tool_call(
        tool_name=TOOL_SUBMIT_SEMANTIC_REVIEW,
        arguments={"semantic_issue_proposal": _PRIVATE_CANARY},
        result_ok=True,
        result={
            "debug_code": "semantic_review_submission_invalid",
            "next_required_action": "retry_corrected_semantic_submission",
            "ok": False,
        },
        error_code=None,
        duration_ms=13,
    )
    accounting.observe_tool_call(
        tool_name=TOOL_DRAFT_ARTICLE,
        arguments={
            "operator_choice_confirmed": True,
            "operator_selected_item_refs": [_PRIVATE_CANARY],
        },
        result_ok=True,
        result={
            "comparison_candidates": [
                {
                    "title": _PRIVATE_CANARY,
                    "excerpts": [_PRIVATE_CANARY],
                }
            ],
            "network_calls": True,
            "next_required_action": "operator_confirm_reuse_comparison",
            "ok": True,
            "result_kind": "reuse_comparison_required",
        },
        error_code=None,
        duration_ms=17,
    )
    accounting.observe_tool_call(
        tool_name=TOOL_CONFIRM_REUSE_COMPARISON,
        arguments={"comparison_ref": _PRIVATE_CANARY, "outcome": "none_fit"},
        result_ok=True,
        result={
            "comparison_outcome": "none_fit",
            "ok": True,
            "result_kind": "reuse_comparison_completed",
        },
        error_code=None,
        duration_ms=19,
    )

    report = sink.reports[-1]
    assert report.terminal_outcome == "completed"
    assert report.transition_count == 5
    assert report.retry_count == 1
    assert report.semantic_correction_count == 1
    assert report.observed_duration_ms == 72
    assert [item.stage for item in report.observations] == [
        "draft.start",
        "semantic_review.prepare",
        "semantic_review.correction",
        "operator.item_selection_and_reuse_search",
        "item.reuse_decision",
    ]
    assert report.observations[3].candidate_count == 1
    assert report.observations[3].excerpt_count == 1
    assert report.observations[3].selected_item_count == 1
    assert report.observations[3].rag_available is True
    projected_content = desktop_tool_results.tool_result_content(
        {
            "comparison_candidates": [
                {
                    "title": _PRIVATE_CANARY,
                    "excerpts": [_PRIVATE_CANARY],
                }
            ],
            "network_calls": True,
            "next_required_action": "operator_confirm_reuse_comparison",
            "ok": True,
            "result_kind": "reuse_comparison_required",
        }
    )
    assert report.observations[3].model_visible_bytes == len(
        json.dumps(
            projected_content,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )
    assert (
        report.observations[3].model_visible_bytes
        != report.observations[3].result_bytes
    )
    serialized = json.dumps(report.to_json_dict(), sort_keys=True)
    assert _PRIVATE_CANARY not in serialized
    for forbidden_field in (
        "arguments",
        "input",
        "output",
        "packet",
        "result",
        "ticket_ref",
    ):
        assert f'"{forbidden_field}"' not in serialized


def test_unknown_debug_code_is_collapsed() -> None:
    sink = _CapturingSink()
    accounting = _accounting(sink)

    accounting.observe_tool_call(
        tool_name=TOOL_DRAFT_TICKET,
        arguments={"ticket_ref": "opaque"},
        result_ok=True,
        result={
            "debug_code": _PRIVATE_CANARY,
            "next_required_action": "prepare_semantic_review",
            "ok": False,
        },
        error_code=None,
        duration_ms=1,
    )

    assert sink.reports[-1].observations[0].debug_code == "unclassified"
    assert _PRIVATE_CANARY not in json.dumps(sink.reports[-1].to_json_dict())


def test_batch_outcome_counts_are_projected_without_item_ledgers() -> None:
    sink = _CapturingSink()
    accounting = _accounting(sink)
    accounting.observe_tool_call(
        tool_name=TOOL_DRAFT_TICKET,
        arguments={"ticket_ref": "opaque"},
        result_ok=True,
        result={
            "next_required_action": "operator_select_single_item",
            "ok": False,
        },
        error_code=None,
        duration_ms=1,
    )

    accounting.observe_tool_call(
        tool_name=TOOL_DRAFT_ARTICLE,
        arguments={
            "operator_selected_item_refs": [
                f"{_PRIVATE_CANARY}-1",
                f"{_PRIVATE_CANARY}-2",
            ]
        },
        result_ok=True,
        result={
            "attempted_count": 2,
            "batch_status": "batch_completed",
            "candidate_outcomes": [
                {
                    "item_ref": f"{_PRIVATE_CANARY}-1",
                    "outcome": "completed_draft",
                },
                {
                    "item_ref": f"{_PRIVATE_CANARY}-2",
                    "outcome": "blocked_retryable",
                },
            ],
            "completed_count": 1,
            "ok": True,
            "result_kind": "draft_article_batch",
            "retryable_blocked_count": 1,
            "selected_count": 2,
            "workflow_stopped_count": 0,
        },
        error_code=None,
        duration_ms=5,
    )

    report = sink.reports[-1]
    assert report.terminal_outcome == "completed"
    assert report.batch_outcome_category == "batch_completed"
    assert report.selected_item_count == 2
    assert report.attempted_item_count == 2
    assert report.completed_item_count == 1
    assert report.retryable_blocked_item_count == 1
    assert report.workflow_stopped_item_count == 0
    assert _PRIVATE_CANARY not in json.dumps(report.to_json_dict())


def test_semantic_submit_marks_reuse_search_at_the_same_existing_seam() -> None:
    sink = _CapturingSink()
    accounting = _accounting(sink)
    accounting.observe_tool_call(
        tool_name=TOOL_DRAFT_TICKET,
        arguments={"ticket_ref": "opaque"},
        result_ok=True,
        result={
            "next_required_action": "prepare_semantic_review",
            "ok": False,
        },
        error_code=None,
        duration_ms=1,
    )

    accounting.observe_tool_call(
        tool_name=TOOL_SUBMIT_SEMANTIC_REVIEW,
        arguments={"semantic_issue_proposal": "opaque"},
        result_ok=True,
        result={
            "comparison_candidates": [],
            "next_required_action": "operator_confirm_reuse_comparison",
            "ok": True,
            "result_kind": "reuse_comparison_required",
        },
        error_code=None,
        duration_ms=2,
    )

    observation = sink.reports[-1].observations[-1]
    assert observation.stage == "semantic_review.submit_and_reuse_search"
    assert observation.item_index == 1
    assert observation.rag_available is True


def test_new_draft_closes_previous_run_as_client_interruption() -> None:
    correlations = iter(("a" * 64, "b" * 64))
    sink = _CapturingSink()
    accounting = DraftRunAccounting(
        sink,
        correlation_factory=lambda: next(correlations),
    )
    continuation = {
        "next_required_action": "prepare_semantic_review",
        "ok": False,
    }

    accounting.observe_tool_call(
        tool_name=TOOL_DRAFT_TICKET,
        arguments={"ticket_ref": "first"},
        result_ok=True,
        result=continuation,
        error_code=None,
        duration_ms=1,
    )
    accounting.observe_tool_call(
        tool_name=TOOL_DRAFT_TICKET,
        arguments={"ticket_ref": "second"},
        result_ok=True,
        result=continuation,
        error_code=None,
        duration_ms=2,
    )

    interrupted = [
        report
        for report in sink.reports
        if report.terminal_outcome == "client_interruption"
    ]
    assert len(interrupted) == 1
    assert interrupted[0].run_correlation_sha256 == "a" * 64
    assert sink.reports[-1].run_correlation_sha256 == "b" * 64
    assert sink.reports[-1].terminal_outcome == "in_progress"


def test_local_json_sink_writes_only_safe_hash_named_report(tmp_path: Path) -> None:
    accounting = _accounting(LocalJsonDraftRunSink(tmp_path))

    accounting.observe_tool_call(
        tool_name=TOOL_DRAFT_TICKET,
        arguments={"ticket_ref": _PRIVATE_CANARY},
        result_ok=True,
        result={
            "next_required_action": "prepare_semantic_review",
            "ok": False,
        },
        error_code=None,
        duration_ms=4,
    )

    paths = list(tmp_path.iterdir())
    assert [path.name for path in paths] == [f"kcs-draft-run-{_CORRELATION}.json"]
    text = paths[0].read_text(encoding="utf-8")
    assert _PRIVATE_CANARY not in text
    assert json.loads(text)["terminal_outcome"] == "in_progress"


def test_background_sink_does_not_wait_for_slow_persistence() -> None:
    capture = _CapturingSink()
    accounting = _accounting(capture)
    accounting.observe_tool_call(
        tool_name=TOOL_DRAFT_TICKET,
        arguments={"ticket_ref": "opaque"},
        result_ok=True,
        result={
            "next_required_action": "prepare_semantic_review",
            "ok": False,
        },
        error_code=None,
        duration_ms=1,
    )
    report = capture.reports[-1]
    started = threading.Event()
    release = threading.Event()

    class _SlowSink:
        def checkpoint(self, report: DraftRunReport) -> None:
            started.set()
            release.wait(timeout=1)

    sink = draft_run_accounting_module._BackgroundDraftRunReportSink(_SlowSink())
    started_at = time.monotonic()
    sink.checkpoint(report)

    assert time.monotonic() - started_at < 0.1
    assert started.wait(timeout=1)
    release.set()


def test_failing_sink_does_not_change_desktop_tool_result() -> None:
    control = KcsDesktopMcpAdapter(semantic_extraction_provider=None)
    observed = KcsDesktopMcpAdapter(
        semantic_extraction_provider=None,
        draft_run_accounting=_accounting(_FailingSink()),
    )

    expected = control.call_tool(TOOL_DRAFT_TICKET, {})
    actual = observed.call_tool(TOOL_DRAFT_TICKET, {})

    assert actual == expected


def test_environment_factory_is_disabled_unless_mode_and_directory_are_set(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(DRAFT_RUN_ACCOUNTING_MODE_ENV, raising=False)
    monkeypatch.delenv(DRAFT_RUN_REPORT_DIR_ENV, raising=False)
    assert draft_run_accounting_from_environment() is None

    monkeypatch.setenv(DRAFT_RUN_ACCOUNTING_MODE_ENV, "local-json")
    assert draft_run_accounting_from_environment() is None

    monkeypatch.setenv(DRAFT_RUN_REPORT_DIR_ENV, str(tmp_path))
    accounting = draft_run_accounting_from_environment()
    assert isinstance(accounting, DraftRunAccounting)
    accounting.observe_tool_call(
        tool_name=TOOL_DRAFT_TICKET,
        arguments={"ticket_ref": _PRIVATE_CANARY},
        result_ok=True,
        result={
            "next_required_action": "prepare_semantic_review",
            "ok": False,
        },
        error_code=None,
        duration_ms=1,
    )
    deadline = time.monotonic() + 1
    while not list(tmp_path.iterdir()) and time.monotonic() < deadline:
        time.sleep(0.01)
    reports = list(tmp_path.iterdir())
    assert len(reports) == 1
    assert _PRIVATE_CANARY not in reports[0].read_text(encoding="utf-8")
