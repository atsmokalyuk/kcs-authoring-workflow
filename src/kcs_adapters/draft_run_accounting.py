"""Value-safe accounting for one model-mediated Desktop ``/draft`` run."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
import threading
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from queue import Empty, Full, Queue
from typing import Any, Protocol, cast

from kcs_adapters import desktop_tool_results as _desktop_tool_results
from kcs_adapters.desktop_tool_names import (
    TOOL_CONFIRM_REUSE_COMPARISON,
    TOOL_DRAFT_ARTICLE,
    TOOL_DRAFT_TICKET,
    TOOL_PREPARE_SEMANTIC_REVIEW,
    TOOL_SUBMIT_SEMANTIC_REVIEW,
)

DRAFT_RUN_REPORT_SCHEMA_VERSION = "kcs_draft_run_report_v1"
DRAFT_RUN_ACCOUNTING_MODE_ENV = "KCS_DRAFT_RUN_ACCOUNTING"
DRAFT_RUN_REPORT_DIR_ENV = "KCS_DRAFT_RUN_REPORT_DIR"
LOCAL_JSON_MODE = "local-json"
_BACKGROUND_QUEUE_SIZE = 32

_RELEVANT_TOOLS = frozenset(
    {
        TOOL_CONFIRM_REUSE_COMPARISON,
        TOOL_DRAFT_ARTICLE,
        TOOL_DRAFT_TICKET,
        TOOL_PREPARE_SEMANTIC_REVIEW,
        TOOL_SUBMIT_SEMANTIC_REVIEW,
    }
)
_STAGES = frozenset(
    {
        "draft.start",
        "item.drafting",
        "item.reuse_decision",
        "item.reuse_decision_and_next_search",
        "item.reuse_search_comparison",
        "operator.item_selection",
        "operator.item_selection_and_reuse_search",
        "semantic_review.correction",
        "semantic_review.prepare",
        "semantic_review.submit",
        "semantic_review.submit_and_reuse_search",
    }
)
_TERMINAL_OUTCOMES = frozenset(
    {
        "client_interruption",
        "completed",
        "host_quota_exhausted",
        "in_progress",
        "rag_failure",
        "tool_blocked",
        "tool_failure",
    }
)
_SUCCESS_CLASSIFICATIONS = frozenset(
    {"controlled_block", "success", "tool_failure", "validation_failure"}
)
_BATCH_OUTCOME_CATEGORIES = frozenset(
    {
        "batch_completed",
        "batch_stopped",
        "not_applicable",
        "sequential_completed",
        "sequential_in_progress",
    }
)
_ALLOWED_DEBUG_CODES = frozenset(
    {
        "approved_summary_resolution_steps_incomplete",
        "comparison_no_evidence",
        "comparison_provider_invalid_response",
        "comparison_provider_not_ready",
        "comparison_provider_unavailable",
        "draft_article_args_invalid",
        "draft_article_call_shape_invalid",
        "explicit_article_context_missing",
        "multiple_kcs_items_detected",
        "operator_resolution_evidence_invalid",
        "operator_resolution_evidence_required",
        "operator_resolution_evidence_unavailable",
        "operator_selection_expired",
        "operator_selection_invalid",
        "operator_selection_required",
        "reuse_comparison_expired",
        "reuse_comparison_gate_unavailable",
        "reuse_comparison_invalid",
        "reuse_comparison_provider_invalid",
        "reuse_comparison_provider_unavailable",
        "reuse_comparison_unavailable",
        "semantic_extraction_no_candidates",
        "semantic_extraction_output_invalid",
        "semantic_extraction_provider_unavailable",
        "semantic_identification_low_confidence",
        "semantic_issue_boundary_ambiguous",
        "semantic_review_expired",
        "semantic_review_invalid",
        "semantic_review_metadata_invalid",
        "semantic_review_packet_invalid",
        "semantic_review_submission_invalid",
        "semantic_review_unavailable",
        "tool_failed",
        "validation_failed",
    }
)
_CONTINUATION_ACTIONS = frozenset(
    {
        "continue_kcs_authoring_workflow",
        "operator_confirm_reuse_comparison",
        "operator_select_remaining_item",
        "operator_select_single_item",
        "prepare_semantic_review",
        "resubmit_pending_reuse_comparison",
        "retry_corrected_semantic_submission",
    }
)
_RAG_FAILURE_CODES = frozenset(
    {
        "reuse_comparison_gate_unavailable",
        "reuse_comparison_provider_invalid",
        "reuse_comparison_provider_unavailable",
        "reuse_comparison_unavailable",
    }
)


class DraftRunReportSink(Protocol):
    """Optional local checkpoint target."""

    def checkpoint(self, report: DraftRunReport) -> None: ...


@dataclass(frozen=True)
class DraftRunObservation:
    """One strictly projected tool transition."""

    sequence: int
    stage: str
    tool_name: str
    item_index: int | None
    duration_ms: int
    request_bytes: int
    result_bytes: int
    model_visible_bytes: int
    candidate_count: int
    selected_item_count: int
    excerpt_count: int
    attempted_item_count: int
    completed_item_count: int
    retryable_blocked_item_count: int
    workflow_stopped_item_count: int
    batch_outcome_category: str
    retry_count: int
    semantic_correction_count: int
    network_calls: bool | None
    rag_available: bool | None
    debug_code: str | None
    success_classification: str


@dataclass(frozen=True)
class DraftRunReport:
    """Closed-schema, content-free snapshot of one ``/draft`` run."""

    schema_version: str
    run_correlation_sha256: str
    terminal_outcome: str
    terminal_source: str
    transition_count: int
    selected_item_count: int
    attempted_item_count: int
    completed_item_count: int
    retryable_blocked_item_count: int
    workflow_stopped_item_count: int
    batch_outcome_category: str
    retry_count: int
    semantic_correction_count: int
    observed_duration_ms: int
    observations: tuple[DraftRunObservation, ...]

    def to_json_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["observations"] = [
            asdict(observation) for observation in self.observations
        ]
        return payload


class LocalJsonDraftRunSink:
    """Atomically checkpoint one safe JSON report per correlation hash."""

    def __init__(self, report_dir: Path) -> None:
        self._report_dir = report_dir

    def checkpoint(self, report: DraftRunReport) -> None:
        validate_draft_run_report(report)
        self._report_dir.mkdir(parents=True, exist_ok=True)
        destination = self._report_dir / (
            f"kcs-draft-run-{report.run_correlation_sha256}.json"
        )
        serialized = json.dumps(
            report.to_json_dict(),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                dir=self._report_dir,
                encoding="utf-8",
                delete=False,
            ) as temporary:
                temporary.write(serialized)
                temporary.write("\n")
                temporary_path = Path(temporary.name)
            temporary_path.replace(destination)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()


class _BackgroundDraftRunReportSink:
    """Keep local persistence latency outside the workflow call path."""

    def __init__(self, sink: DraftRunReportSink) -> None:
        self._sink = sink
        self._queue: Queue[DraftRunReport] = Queue(maxsize=_BACKGROUND_QUEUE_SIZE)
        self._worker = threading.Thread(
            target=self._run,
            name="kcs-draft-run-accounting",
            daemon=True,
        )
        self._worker.start()

    def checkpoint(self, report: DraftRunReport) -> None:
        try:
            self._queue.put_nowait(report)
            return
        except Full:
            pass
        self._drop_oldest_checkpoint()
        try:
            self._queue.put_nowait(report)
        except Full:
            return

    def _drop_oldest_checkpoint(self) -> None:
        try:
            self._queue.get_nowait()
        except Empty:
            return
        self._queue.task_done()

    def _run(self) -> None:
        while True:
            report = self._queue.get()
            try:
                self._sink.checkpoint(report)
            except Exception:
                pass
            finally:
                self._queue.task_done()


class DraftRunAccounting:
    """Project relevant MCP transitions and fail open at the sink boundary."""

    def __init__(
        self,
        sink: DraftRunReportSink,
        *,
        correlation_factory: Callable[[], str] | None = None,
    ) -> None:
        self._sink = sink
        self._correlation_factory = correlation_factory or _new_correlation_hash
        self._correlation_hash: str | None = None
        self._observations: list[DraftRunObservation] = []
        self._terminal_outcome = "in_progress"
        self._terminal_source = "mcp_boundary"
        self._retry_count = 0
        self._semantic_correction_count = 0
        self._selected_item_count = 0
        self._item_index = 0

    def observe_tool_call(
        self,
        *,
        tool_name: str,
        arguments: Mapping[str, Any],
        result_ok: bool,
        result: Mapping[str, Any] | None,
        error_code: str | None,
        duration_ms: int,
    ) -> None:
        if tool_name not in _RELEVANT_TOOLS:
            return
        self._ensure_active_run(tool_name, arguments)
        if self._correlation_hash is None:
            return
        self._record_active_call(
            tool_name=tool_name,
            arguments=arguments,
            result_ok=result_ok,
            result=result or {},
            error_code=error_code,
            duration_ms=duration_ms,
        )

    def _ensure_active_run(
        self,
        tool_name: str,
        arguments: Mapping[str, Any],
    ) -> None:
        if tool_name == TOOL_DRAFT_TICKET:
            self._interrupt_active_run()
            self._start_run()
            return
        if (
            self._correlation_hash is None
            and tool_name == TOOL_DRAFT_ARTICLE
            and "ticket_ref" in arguments
        ):
            self._start_run()

    def _record_active_call(
        self,
        *,
        tool_name: str,
        arguments: Mapping[str, Any],
        result_ok: bool,
        result: Mapping[str, Any],
        error_code: str | None,
        duration_ms: int,
    ) -> None:
        self._update_counters(tool_name, arguments, result)
        observation = self._observation(
            tool_name=tool_name,
            arguments=arguments,
            result_ok=result_ok,
            result=result,
            error_code=error_code,
            duration_ms=duration_ms,
        )
        self._observations.append(observation)
        terminal_outcome = _terminal_outcome(
            result_ok=result_ok,
            result=result,
            error_code=error_code,
        )
        if terminal_outcome is not None:
            self._terminal_outcome = terminal_outcome
        self._checkpoint()
        if terminal_outcome is not None:
            self._clear_run()

    def close_as_client_interruption(self) -> None:
        """Explicitly close an active run without guessing the host reason."""

        if self._correlation_hash is None:
            return
        self._terminal_outcome = "client_interruption"
        self._terminal_source = "operator_or_transport"
        self._checkpoint()
        self._clear_run()

    def _start_run(self) -> None:
        correlation_hash = self._correlation_factory()
        if not _is_sha256(correlation_hash):
            raise ValueError("draft run correlation must be SHA-256")
        self._correlation_hash = correlation_hash
        self._observations = []
        self._terminal_outcome = "in_progress"
        self._terminal_source = "mcp_boundary"
        self._retry_count = 0
        self._semantic_correction_count = 0
        self._selected_item_count = 0
        self._item_index = 0

    def _interrupt_active_run(self) -> None:
        if self._correlation_hash is not None:
            self.close_as_client_interruption()

    def _clear_run(self) -> None:
        self._correlation_hash = None
        self._observations = []

    def _update_counters(
        self,
        tool_name: str,
        arguments: Mapping[str, Any],
        result: Mapping[str, Any],
    ) -> None:
        selected_count = _selected_count(arguments, result)
        self._selected_item_count = max(self._selected_item_count, selected_count)
        if tool_name == TOOL_SUBMIT_SEMANTIC_REVIEW:
            if result.get("next_required_action") == (
                "retry_corrected_semantic_submission"
            ):
                self._semantic_correction_count += 1
                self._retry_count += 1
        if (
            tool_name == TOOL_CONFIRM_REUSE_COMPARISON
            and result.get("next_required_action")
            == "resubmit_pending_reuse_comparison"
        ):
            self._retry_count += 1
        if _starts_reuse_comparison(result) and self._item_index == 0:
            self._item_index = 1

    def _observation(
        self,
        *,
        tool_name: str,
        arguments: Mapping[str, Any],
        result_ok: bool,
        result: Mapping[str, Any],
        error_code: str | None,
        duration_ms: int,
    ) -> DraftRunObservation:
        stage = _stage(tool_name, arguments, result)
        item_stage = stage.startswith("item.") or "reuse_search" in stage
        item_index = self._item_index if item_stage else None
        observation = DraftRunObservation(
            sequence=len(self._observations) + 1,
            stage=stage,
            tool_name=tool_name,
            item_index=item_index or None,
            duration_ms=max(0, duration_ms),
            request_bytes=_json_size(arguments),
            result_bytes=_json_size(result),
            model_visible_bytes=_model_visible_size(result),
            candidate_count=_candidate_count(result),
            selected_item_count=_selected_count(arguments, result),
            excerpt_count=_excerpt_count(result),
            attempted_item_count=_outcome_count(result, "attempted"),
            completed_item_count=_completed_item_count(result),
            retryable_blocked_item_count=_outcome_count(result, "blocked_retryable"),
            workflow_stopped_item_count=_outcome_count(result, "workflow_stopped"),
            batch_outcome_category=_batch_outcome_category(result),
            retry_count=self._retry_count,
            semantic_correction_count=self._semantic_correction_count,
            network_calls=_optional_bool(result.get("network_calls")),
            rag_available=_rag_available(result),
            debug_code=_safe_debug_code(result.get("debug_code") or error_code),
            success_classification=_success_classification(
                result_ok=result_ok,
                result=result,
                error_code=error_code,
            ),
        )
        if tool_name == TOOL_CONFIRM_REUSE_COMPARISON and _starts_reuse_comparison(
            result
        ):
            self._item_index += 1
        return observation

    def _checkpoint(self) -> None:
        if self._correlation_hash is None:
            return
        report = DraftRunReport(
            schema_version=DRAFT_RUN_REPORT_SCHEMA_VERSION,
            run_correlation_sha256=self._correlation_hash,
            terminal_outcome=self._terminal_outcome,
            terminal_source=self._terminal_source,
            transition_count=len(self._observations),
            selected_item_count=self._selected_item_count,
            attempted_item_count=_max_observation_count(
                self._observations, "attempted_item_count"
            ),
            completed_item_count=_max_observation_count(
                self._observations, "completed_item_count"
            ),
            retryable_blocked_item_count=_max_observation_count(
                self._observations, "retryable_blocked_item_count"
            ),
            workflow_stopped_item_count=_max_observation_count(
                self._observations, "workflow_stopped_item_count"
            ),
            batch_outcome_category=_latest_batch_outcome(self._observations),
            retry_count=self._retry_count,
            semantic_correction_count=self._semantic_correction_count,
            observed_duration_ms=sum(
                observation.duration_ms for observation in self._observations
            ),
            observations=tuple(self._observations),
        )
        try:
            self._sink.checkpoint(report)
        except Exception:
            return


def draft_run_accounting_from_environment() -> DraftRunAccounting | None:
    """Build the optional local sink without making configuration fatal."""

    if os.environ.get(DRAFT_RUN_ACCOUNTING_MODE_ENV) != LOCAL_JSON_MODE:
        return None
    report_dir = os.environ.get(DRAFT_RUN_REPORT_DIR_ENV)
    if not report_dir:
        return None
    try:
        local_sink = LocalJsonDraftRunSink(Path(report_dir))
        return DraftRunAccounting(_BackgroundDraftRunReportSink(local_sink))
    except (OSError, ValueError):
        return None


def validate_draft_run_report(report: DraftRunReport) -> None:
    """Reject fields outside the closed in-process report model."""

    valid = all(
        (
            _valid_report_header(report),
            _valid_report_counts(report),
            _valid_report_sequence(report),
            all(_valid_observation(item) for item in report.observations),
        )
    )
    if not valid:
        raise ValueError("draft run report invalid")


def _valid_report_header(report: DraftRunReport) -> bool:
    return (
        report.schema_version == DRAFT_RUN_REPORT_SCHEMA_VERSION
        and _is_sha256(report.run_correlation_sha256)
        and report.terminal_outcome in _TERMINAL_OUTCOMES
        and report.terminal_source
        in {"desktop_log_classifier", "mcp_boundary", "operator_or_transport"}
        and report.transition_count == len(report.observations)
        and report.batch_outcome_category in _BATCH_OUTCOME_CATEGORIES
    )


def _valid_report_counts(report: DraftRunReport) -> bool:
    counts = (
        report.selected_item_count,
        report.attempted_item_count,
        report.completed_item_count,
        report.retryable_blocked_item_count,
        report.workflow_stopped_item_count,
        report.retry_count,
        report.semantic_correction_count,
        report.observed_duration_ms,
    )
    return all(_is_non_negative_int(value) for value in counts)


def _valid_report_sequence(report: DraftRunReport) -> bool:
    expected_sequence = list(range(1, report.transition_count + 1))
    actual_sequence = [item.sequence for item in report.observations]
    measured_duration = sum(item.duration_ms for item in report.observations)
    return (
        actual_sequence == expected_sequence
        and report.observed_duration_ms == measured_duration
    )


def _valid_observation(observation: DraftRunObservation) -> bool:
    counts = (
        observation.sequence,
        observation.duration_ms,
        observation.request_bytes,
        observation.result_bytes,
        observation.model_visible_bytes,
        observation.candidate_count,
        observation.selected_item_count,
        observation.excerpt_count,
        observation.attempted_item_count,
        observation.completed_item_count,
        observation.retryable_blocked_item_count,
        observation.workflow_stopped_item_count,
        observation.retry_count,
        observation.semantic_correction_count,
    )
    return all(
        (
            _valid_observation_identity(observation),
            all(_is_non_negative_int(value) for value in counts),
            _valid_observation_optional_fields(observation),
        )
    )


def _valid_observation_identity(observation: DraftRunObservation) -> bool:
    return (
        observation.sequence >= 1
        and observation.stage in _STAGES
        and observation.tool_name in _RELEVANT_TOOLS
        and (observation.item_index is None or 1 <= observation.item_index <= 100)
        and observation.batch_outcome_category in _BATCH_OUTCOME_CATEGORIES
        and observation.success_classification in _SUCCESS_CLASSIFICATIONS
    )


def _valid_observation_optional_fields(
    observation: DraftRunObservation,
) -> bool:
    return all(
        (
            (
                observation.network_calls is None
                or isinstance(observation.network_calls, bool)
            ),
            (
                observation.rag_available is None
                or isinstance(observation.rag_available, bool)
            ),
            (
                observation.debug_code is None
                or observation.debug_code in _ALLOWED_DEBUG_CODES
                or observation.debug_code == "unclassified"
            ),
        )
    )


def _stage(
    tool_name: str,
    arguments: Mapping[str, Any],
    result: Mapping[str, Any],
) -> str:
    fixed_stages = {
        TOOL_DRAFT_TICKET: "draft.start",
        TOOL_PREPARE_SEMANTIC_REVIEW: "semantic_review.prepare",
    }
    fixed_stage = fixed_stages.get(tool_name)
    if fixed_stage is not None:
        return fixed_stage
    if tool_name == TOOL_SUBMIT_SEMANTIC_REVIEW:
        return _semantic_submit_stage(result)
    if tool_name == TOOL_CONFIRM_REUSE_COMPARISON:
        return _reuse_submit_stage(result)
    return _draft_article_stage(arguments, result)


def _semantic_submit_stage(result: Mapping[str, Any]) -> str:
    if result.get("next_required_action") == "retry_corrected_semantic_submission":
        return "semantic_review.correction"
    if _starts_reuse_comparison(result):
        return "semantic_review.submit_and_reuse_search"
    return "semantic_review.submit"


def _reuse_submit_stage(result: Mapping[str, Any]) -> str:
    if _starts_reuse_comparison(result):
        return "item.reuse_decision_and_next_search"
    return "item.reuse_decision"


def _draft_article_stage(
    arguments: Mapping[str, Any],
    result: Mapping[str, Any],
) -> str:
    if _starts_reuse_comparison(result):
        if _selected_count(arguments, result):
            return "operator.item_selection_and_reuse_search"
        return "item.reuse_search_comparison"
    if _selected_count(arguments, result):
        return "operator.item_selection"
    if result.get("draft_generated") is True:
        return "item.drafting"
    return "draft.start"


def _terminal_outcome(
    *,
    result_ok: bool,
    result: Mapping[str, Any],
    error_code: str | None,
) -> str | None:
    if not result_ok:
        return "tool_failure"
    if _is_rag_failure(result, error_code):
        return "rag_failure"
    if _has_continuation(result):
        return None
    return _terminal_without_continuation(result)


def _is_rag_failure(
    result: Mapping[str, Any],
    error_code: str | None,
) -> bool:
    debug_code = result.get("debug_code") or error_code
    return (
        debug_code in _RAG_FAILURE_CODES
        or result.get("result_kind") == "reuse_comparison_blocked"
    )


def _has_continuation(result: Mapping[str, Any]) -> bool:
    next_action = result.get("next_required_action")
    return isinstance(next_action, str) and next_action in _CONTINUATION_ACTIONS


def _terminal_without_continuation(
    result: Mapping[str, Any],
) -> str | None:
    if result.get("result_kind") == "draft_article_batch":
        return (
            "completed"
            if result.get("batch_status") == "batch_completed"
            else ("tool_blocked")
        )
    if (
        result.get("draft_generated") is True
        or result.get("result_kind") == "reuse_comparison_completed"
    ):
        return "completed"
    if result.get("ok") is False:
        return "tool_blocked"
    return None


def _success_classification(
    *,
    result_ok: bool,
    result: Mapping[str, Any],
    error_code: str | None,
) -> str:
    if not result_ok:
        return "tool_failure"
    if error_code == "validation_failed":
        return "validation_failure"
    if result.get("ok") is False:
        return "controlled_block"
    return "success"


def _selected_count(
    arguments: Mapping[str, Any],
    result: Mapping[str, Any],
) -> int:
    selected_refs = arguments.get("operator_selected_item_refs")
    if isinstance(selected_refs, list):
        return len(selected_refs)
    if arguments.get("operator_choice_confirmed") is True or (
        "operator_selected_item_ref" in arguments
    ):
        return 1
    result_count = result.get("selected_count")
    return result_count if _is_non_negative_int(result_count) else 0


def _candidate_count(result: Mapping[str, Any]) -> int:
    counts = [
        _list_count(result.get(key))
        for key in (
            "comparison_candidates",
            "item_candidates",
            "remaining_item_candidates",
            "retryable_item_candidates",
        )
    ]
    return max(counts, default=0)


def _excerpt_count(result: Mapping[str, Any]) -> int:
    direct_count = _list_count(result.get("selected_excerpts"))
    candidates = result.get("comparison_candidates")
    if not isinstance(candidates, list):
        return direct_count
    nested_count = sum(
        max(
            _list_count(candidate.get("excerpts")),
            _list_count(candidate.get("public_excerpts")),
        )
        for candidate in candidates
        if isinstance(candidate, Mapping)
    )
    return direct_count + nested_count


def _outcome_count(result: Mapping[str, Any], outcome: str) -> int:
    explicit_fields = {
        "attempted": "attempted_count",
        "blocked_retryable": "retryable_blocked_count",
        "workflow_stopped": "workflow_stopped_count",
    }
    explicit = result.get(explicit_fields[outcome])
    if _is_non_negative_int(explicit):
        return cast(int, explicit)
    return sum(
        item.get("attempted") is True
        if outcome == "attempted"
        else item.get("outcome") == outcome
        for item in _outcome_ledgers(result)
    )


def _completed_item_count(result: Mapping[str, Any]) -> int:
    explicit = result.get("completed_count")
    if _is_non_negative_int(explicit):
        return cast(int, explicit)
    return sum(
        item.get("outcome") in {"completed_blocked", "completed_draft"}
        for item in _outcome_ledgers(result)
    )


def _outcome_ledgers(result: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    for key in ("candidate_outcomes", "comparison_sequence_outcomes"):
        value = result.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, Mapping)]
    return []


def _batch_outcome_category(result: Mapping[str, Any]) -> str:
    batch_status = result.get("batch_status")
    if batch_status in {"batch_completed", "batch_stopped"}:
        return cast(str, batch_status)
    ledgers = _outcome_ledgers(result)
    if not ledgers:
        return "not_applicable"
    if _starts_reuse_comparison(result):
        return "sequential_in_progress"
    return "sequential_completed"


def _max_observation_count(
    observations: list[DraftRunObservation],
    field: str,
) -> int:
    return max(
        (cast(int, getattr(observation, field)) for observation in observations),
        default=0,
    )


def _latest_batch_outcome(
    observations: list[DraftRunObservation],
) -> str:
    outcomes = [
        item.batch_outcome_category
        for item in observations
        if item.batch_outcome_category != "not_applicable"
    ]
    return outcomes[-1] if outcomes else "not_applicable"


def _starts_reuse_comparison(result: Mapping[str, Any]) -> bool:
    return result.get("result_kind") == "reuse_comparison_required"


def _rag_available(result: Mapping[str, Any]) -> bool | None:
    result_kind = result.get("result_kind")
    if result_kind == "reuse_comparison_required":
        return True
    if result_kind == "reuse_comparison_blocked":
        return False
    return None


def _safe_debug_code(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and value in _ALLOWED_DEBUG_CODES:
        return value
    return "unclassified"


def _json_size(value: object) -> int:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError):
        return 0
    return len(encoded)


def _model_visible_size(result: Mapping[str, Any]) -> int:
    try:
        content = _desktop_tool_results.tool_result_content(result)
    except (TypeError, ValueError):
        return 0
    return _json_size(content)


def _list_count(value: object) -> int:
    return len(value) if isinstance(value, list) else 0


def _optional_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _is_non_negative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _new_correlation_hash() -> str:
    return hashlib.sha256(secrets.token_bytes(32)).hexdigest()


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


__all__ = [
    "DRAFT_RUN_ACCOUNTING_MODE_ENV",
    "DRAFT_RUN_REPORT_DIR_ENV",
    "DRAFT_RUN_REPORT_SCHEMA_VERSION",
    "DraftRunAccounting",
    "DraftRunObservation",
    "DraftRunReport",
    "DraftRunReportSink",
    "LOCAL_JSON_MODE",
    "LocalJsonDraftRunSink",
    "draft_run_accounting_from_environment",
    "validate_draft_run_report",
]
