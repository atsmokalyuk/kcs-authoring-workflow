"""Desktop-owned KCS draft workflow support.

This module intentionally keeps semantic extraction behind the core
``SemanticExtractionProvider`` contract. The production Desktop default is a
bounded local approved-summary provider that extracts only explicit facts from
sanitized operator-approved text.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from kcs_adapters import desktop_operator_selection as _desktop_operator_selection
from kcs_adapters import desktop_reuse_comparison as _desktop_reuse_comparison
from kcs_adapters import desktop_reviewer_preview as _desktop_reviewer_preview
from kcs_adapters import desktop_semantic_providers as _desktop_semantic_providers
from kcs_adapters import desktop_workflow_results as _desktop_workflow_results
from kcs_adapters import desktop_workflow_status as _desktop_workflow_status
from kcs_adapters.desktop_draft_output import (
    compact_draft_result,
    quality_blocked_result,
    quality_blocker_gaps,
    reviewer_only_quality_debt_allowed,
    reviewer_only_quality_draft_result,
)
from kcs_adapters.desktop_reviewer_bundle import write_desktop_reviewer_bundle
from kcs_adapters.desktop_semantic_candidate_contract import (
    semantic_submission_correction,
    semantic_submission_correction_stage,
)
from kcs_adapters.desktop_semantic_candidates import (
    ProjectedIssueSet,
    desktop_candidate_set_from_semantic_issue_proposal,
    desktop_item_candidates_from_semantic_extraction,
    project_semantic_issue_proposals,
    semantic_projection_requires_terminal_review,
)
from kcs_adapters.desktop_semantic_review import (
    PendingSemanticReview,
    SemanticReviewError,
    new_pending_semantic_review,
    prepared_pending_semantic_review,
    semantic_issue_proposal_from_submission,
    semantic_review_excerpt_role_index,
)
from kcs_core.claude_handoff import (
    KcsClaudeHandoffRequestPacket,
    bounded_claude_handoff_title_hint,
    build_claude_handoff_request,
)
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict
from kcs_core.models import (
    KcsActionDecisionPacket,
    KcsReviewerPacket,
    KcsValidationReportPacket,
    NormalizedTicketEvidencePacket,
)
from kcs_core.reuse_comparison import (
    ReuseComparisonEvidence,
    ReuseComparisonEvidenceProvider,
)
from kcs_core.safety import SafetyGateResult
from kcs_core.sanitizer import (
    ensure_safe_sanitized_payload,
)
from kcs_core.semantic_extraction import SemanticExtractionProvider
from kcs_core.validation import EvidenceValidationResult

_LINUX_ENVIRONMENT_RE = re.compile(
    r"\b(?:apache|centos|cloudlinux|debian|httpd|linux|nginx|"
    r"red\s*hat|rhel|rpm|systemctl|ubuntu)\b|/(?:etc|usr|var)/",
    re.I,
)
_WINDOWS_ENVIRONMENT_RE = re.compile(
    r"\b(?:iis|rdp|windows|winrm|powershell)\b|[A-Za-z]:\\",
    re.I,
)
_PLATFORM_TYPE_BY_MATCH_FLAGS = {
    (False, True): "Linux",
    (True, False): "Windows",
}

SEMANTIC_PROVIDER_ENV = _desktop_semantic_providers.SEMANTIC_PROVIDER_ENV
SEMANTIC_PROVIDER_APPROVED_SUMMARY = (
    _desktop_semantic_providers.SEMANTIC_PROVIDER_APPROVED_SUMMARY
)
SEMANTIC_PROVIDER_FIXTURE = _desktop_semantic_providers.SEMANTIC_PROVIDER_FIXTURE
SEMANTIC_PROVIDER_APPROVED = _desktop_semantic_providers.SEMANTIC_PROVIDER_APPROVED
ApprovedSummarySemanticExtractionProvider = (
    _desktop_semantic_providers.ApprovedSummarySemanticExtractionProvider
)
FixtureSemanticExtractionProvider = (
    _desktop_semantic_providers.FixtureSemanticExtractionProvider
)
NoSemanticCandidatesError = _desktop_semantic_providers.NoSemanticCandidatesError
SemanticExtractionProviderUnavailableError = (
    _desktop_semantic_providers.SemanticExtractionProviderUnavailableError
)
UnavailableSemanticExtractionProvider = (
    _desktop_semantic_providers.UnavailableSemanticExtractionProvider
)
semantic_provider_from_environment = (
    _desktop_semantic_providers.semantic_provider_from_environment
)

PendingDraftSelection = _desktop_operator_selection.PendingDraftSelection
PendingReuseComparison = _desktop_reuse_comparison.PendingReuseComparison
ReuseComparisonExpiredError = _desktop_reuse_comparison.ReuseComparisonExpiredError
ReuseComparisonInvalidError = _desktop_reuse_comparison.ReuseComparisonInvalidError
ReuseComparisonSubmission = _desktop_reuse_comparison.ReuseComparisonSubmission
ReuseComparisonUnavailableError = (
    _desktop_reuse_comparison.ReuseComparisonUnavailableError
)
attach_pending_selection = _desktop_operator_selection.attach_pending_selection
new_pending_draft_selection = _desktop_operator_selection.new_pending_draft_selection
operator_choice_request = _desktop_operator_selection.operator_choice_request
operator_choice_submit_options = (
    _desktop_operator_selection.operator_choice_submit_options
)
operator_choice_review_summary = (
    _desktop_operator_selection.operator_choice_review_summary
)
selected_pending_candidate = _desktop_operator_selection.selected_pending_candidate
split_candidate_cards = _desktop_operator_selection.split_candidate_cards
pending_selection_after_draft = (
    _desktop_operator_selection.pending_selection_after_draft
)
pending_selection_after_completed_candidate = (
    _desktop_operator_selection.pending_selection_after_completed_candidate
)
pending_selection_after_retryable_blocker = (
    _desktop_operator_selection.pending_selection_after_retryable_blocker
)
remaining_operator_choice_status = (
    _desktop_operator_selection.remaining_operator_choice_status
)
draft_author_failure_result = _desktop_workflow_results.draft_author_failure_result
operator_selection_expired_result = (
    _desktop_workflow_results.operator_selection_expired_result
)
operator_selection_unavailable_result = (
    _desktop_workflow_results.operator_selection_unavailable_result
)
selection_error_result = _desktop_workflow_results.selection_error_result
semantic_provider_unavailable_result = (
    _desktop_workflow_results.semantic_provider_unavailable_result
)
split_required_result = _desktop_workflow_results.split_required_result
approved_summary_draft_request_ready = (
    _desktop_workflow_status.approved_summary_draft_request_ready
)
approved_summary_pipeline_status = (
    _desktop_workflow_status.approved_summary_pipeline_status
)
approved_summary_reuse_search_status = (
    _desktop_workflow_status.approved_summary_reuse_search_status
)
approved_summary_reuse_was_checked = (
    _desktop_workflow_status.approved_summary_reuse_was_checked
)
approved_summary_applicable_to = (
    _desktop_reviewer_preview.approved_summary_applicable_to
)
approved_summary_html_quality_gaps = (
    _desktop_reviewer_preview.approved_summary_html_quality_gaps
)
approved_summary_open_questions = (
    _desktop_reviewer_preview.approved_summary_open_questions
)
approved_summary_public_candidate = (
    _desktop_reviewer_preview.approved_summary_public_candidate
)
approved_summary_quality_gaps = _desktop_reviewer_preview.approved_summary_quality_gaps
approved_summary_reference_section_gaps = (
    _desktop_reviewer_preview.approved_summary_reference_section_gaps
)
approved_summary_reference_text = (
    _desktop_reviewer_preview.approved_summary_reference_text
)
approved_summary_reviewer_only_draft = (
    _desktop_reviewer_preview.approved_summary_reviewer_only_draft
)
approved_summary_reviewer_only_html = (
    _desktop_reviewer_preview.approved_summary_reviewer_only_html
)
approved_summary_reviewer_only_preview = (
    _desktop_reviewer_preview.approved_summary_reviewer_only_preview
)
approved_summary_reviewer_only_preview_text = (
    _desktop_reviewer_preview.approved_summary_reviewer_only_preview_text
)
approved_summary_source_candidate = (
    _desktop_reviewer_preview.approved_summary_source_candidate
)
numbered_or_bulleted_lines = _desktop_reviewer_preview.numbered_or_bulleted_lines
safe_candidate_list = _desktop_reviewer_preview.safe_candidate_list
safe_candidate_string = _desktop_reviewer_preview.safe_candidate_string


class OperatorSelectionUnavailableError(RuntimeError):
    """No pending operator selection exists."""


class OperatorSelectionExpiredError(RuntimeError):
    """Pending operator selection expired."""


class OperatorSelectionInvalidError(RuntimeError):
    """Operator selection refs do not match pending state."""


class SemanticReviewUnavailableError(RuntimeError):
    """No pending semantic-review state exists."""


class SemanticReviewExpiredError(RuntimeError):
    """Pending semantic-review state expired."""


class SemanticReviewInvalidError(RuntimeError):
    """Semantic-review refs do not match pending state."""


class SemanticReviewSubmissionInvalidError(RuntimeError):
    """Semantic-review submission did not pass validation."""

    def __init__(
        self,
        debug_code: str,
        *,
        correction: JsonDict | None,
        terminal_cause_debug_code: str | None = None,
    ) -> None:
        super().__init__("semantic review submission invalid")
        self.correction = correction
        self.debug_code = debug_code
        self.terminal_cause_debug_code = terminal_cause_debug_code


class SemanticReviewBoundaryAmbiguousError(RuntimeError):
    """A proposal has no safe candidate-selection or operator action path."""

    def __init__(self, projected: ProjectedIssueSet) -> None:
        super().__init__("semantic boundary remained ambiguous")
        self.projected = projected


_TERMINAL_SEMANTIC_SUBMISSION_DEBUG_CODES = frozenset(
    {
        "semantic_coverage_shape_invalid",
        "semantic_observation_shape_invalid",
        "semantic_issue_proposal_shape_invalid",
        "semantic_issue_submission_invalid",
        "semantic_ref_shape_invalid",
        "semantic_review_forbidden_field",
        "semantic_review_forbidden_html_or_markdown",
        "semantic_review_local_ref_blocked",
        "semantic_review_packet_unavailable",
        "semantic_review_submission_invalid",
        "semantic_review_unsafe_value_blocked",
        "semantic_source_refs_shape_invalid",
    }
)


def _semantic_correction_stage_allowed(
    used_stages: tuple[str, ...],
    next_stage: str | None,
) -> bool:
    return next_stage is not None and (
        not used_stages
        or (used_stages == ("structure",) and next_stage == "grounding")
    )


def _semantic_correction_for_error(
    debug_code: str,
    cause: Exception,
) -> tuple[JsonDict | None, str | None]:
    correction = semantic_submission_correction(debug_code)
    if (
        correction is not None
        and isinstance(cause, SemanticReviewError)
        and cause.field_paths
    ):
        correction["field_paths"] = list(cause.field_paths)
    return correction, semantic_submission_correction_stage(debug_code)


class ApprovedSummaryPipelineStageError(ContractValidationError):
    """Value-safe approved summary pipeline stage error."""

    def __init__(self, *, failure_stage: str, debug_code: str) -> None:
        super().__init__("approved summary pipeline stage failed")
        self.failure_stage = failure_stage
        self.debug_code = debug_code


@dataclass(frozen=True)
class ApprovedSummaryExecution:
    """Result of a completed approved-summary authoring pipeline run."""

    arguments: Mapping[str, Any]
    payload: JsonDict
    evidence: NormalizedTicketEvidencePacket
    safety: SafetyGateResult
    evidence_validation: EvidenceValidationResult
    decision: KcsActionDecisionPacket
    reviewer_packet: KcsReviewerPacket
    readiness: KcsValidationReportPacket
    handoff_request: KcsClaudeHandoffRequestPacket
    draft_request_ready: bool
    item_ref: str


@dataclass(frozen=True)
class ApprovedSummaryPipelineHooks:
    """Adapter-owned operations used by the Desktop workflow orchestration."""

    build_payload: Callable[[Mapping[str, Any]], JsonDict]
    build_evidence: Callable[
        [Mapping[str, Any], Mapping[str, Any]],
        NormalizedTicketEvidencePacket,
    ]
    validate_safety: Callable[[NormalizedTicketEvidencePacket], SafetyGateResult]
    validate_evidence: Callable[
        [NormalizedTicketEvidencePacket],
        EvidenceValidationResult,
    ]
    decide: Callable[
        [Mapping[str, Any], NormalizedTicketEvidencePacket],
        KcsActionDecisionPacket,
    ]
    render: Callable[
        [NormalizedTicketEvidencePacket, KcsActionDecisionPacket],
        KcsReviewerPacket,
    ]
    build_readiness: Callable[
        [
            NormalizedTicketEvidencePacket,
            KcsActionDecisionPacket,
            KcsReviewerPacket,
        ],
        KcsValidationReportPacket,
    ]
    item_ref: Callable[[Mapping[str, Any], KcsActionDecisionPacket], str]
    short_summary: Callable[[Mapping[str, Any]], str]
    title: Callable[[Mapping[str, Any]], str]


class DesktopDraftWorkflow:
    """Own Desktop draft provider calls and pending operator selection state."""

    def __init__(
        self,
        *,
        provider: SemanticExtractionProvider | None | object,
        selection_ttl_seconds: float,
        reuse_comparison_provider: ReuseComparisonEvidenceProvider | None = None,
    ) -> None:
        self._provider = provider
        self._selection_ttl_seconds = selection_ttl_seconds
        self._reuse_comparison_provider = reuse_comparison_provider
        self._pending_selection: PendingDraftSelection | None = None
        self._pending_reuse_comparison: PendingReuseComparison | None = None
        self._pending_semantic_review: PendingSemanticReview | None = None

    @property
    def pending_selection(self) -> PendingDraftSelection | None:
        """Return current pending selection state, if any."""

        return self._pending_selection

    def clear_pending_selection(self) -> None:
        """Clear pending selection state after accepted continuation."""

        self._pending_selection = None

    def clear_pending_semantic_review(self) -> None:
        """Clear pending semantic-review state after use or superseding flow."""

        self._pending_semantic_review = None

    @property
    def reuse_comparison_enabled(self) -> bool:
        """Return whether this workflow has an approved comparison provider."""

        return self._reuse_comparison_provider is not None

    @property
    def pending_reuse_comparison(self) -> PendingReuseComparison | None:
        """Return current pending reuse-comparison state, if any."""

        return self._pending_reuse_comparison

    def clear_pending_reuse_comparison(self) -> None:
        """Clear pending comparison after use or controlled restart."""

        self._pending_reuse_comparison = None

    def start_pending_reuse_comparison(
        self,
        *,
        issue_candidate: Mapping[str, object],
        approved_summary_text: str,
        approved_summary_source_kind: str | None,
        selected_item_refs: list[str],
        current_index: int,
        selection_ref: str | None,
        debug: bool,
        completed_outcomes: list[Mapping[str, object]] | None = None,
    ) -> PendingReuseComparison | ReuseComparisonEvidence:
        """Collect bounded evidence and retain it only when comparison is ready."""

        provider = self._reuse_comparison_provider
        if provider is None:
            raise ReuseComparisonUnavailableError
        result = _desktop_reuse_comparison.collect_pending_reuse_comparison(
            provider=provider,
            issue_candidate=issue_candidate,
            approved_summary_text=approved_summary_text,
            approved_summary_source_kind=approved_summary_source_kind,
            selected_item_refs=selected_item_refs,
            current_index=current_index,
            selection_ref=selection_ref,
            debug=debug,
            completed_outcomes=completed_outcomes or (),
            ttl_seconds=self._selection_ttl_seconds,
        )
        self._pending_reuse_comparison = (
            result if isinstance(result, PendingReuseComparison) else None
        )
        return result

    def submitted_reuse_comparison(
        self,
        *,
        comparison_ref: object,
        outcome: object,
        candidate_ref: object = None,
    ) -> ReuseComparisonSubmission:
        """Consume one pending comparison or fail closed and require restart."""

        pending = self._pending_reuse_comparison
        if pending is None:
            raise ReuseComparisonUnavailableError
        if time.monotonic() > pending.expires_at:
            self._pending_reuse_comparison = None
            raise ReuseComparisonExpiredError
        if pending.selection_ref is not None:
            try:
                self.selected_candidate(
                    selection_ref=pending.selection_ref,
                    selected_item_ref=(
                        pending.selected_item_refs[pending.current_index]
                    ),
                )
            except (
                OperatorSelectionExpiredError,
                OperatorSelectionInvalidError,
                OperatorSelectionUnavailableError,
            ):
                self._pending_reuse_comparison = None
                raise ReuseComparisonInvalidError from None
        try:
            submission = _desktop_reuse_comparison.validate_reuse_comparison_submit(
                pending,
                comparison_ref=comparison_ref,
                outcome=outcome,
                candidate_ref=candidate_ref,
            )
        except ReuseComparisonInvalidError:
            self._pending_reuse_comparison = None
            raise
        self._pending_reuse_comparison = None
        return submission

    @property
    def pending_semantic_review(self) -> PendingSemanticReview | None:
        """Return current pending semantic-review state, if any."""

        return self._pending_semantic_review

    def item_candidates_from_summary(
        self,
        approved_summary_text: str,
        *,
        source_kind: str | None = None,
    ) -> list[JsonDict]:
        """Call the semantic provider and return Desktop draft candidates."""

        provider = self._provider
        if provider is None:
            raise SemanticExtractionProviderUnavailableError
        provider_context = {
            "approved_summary_text": approved_summary_text,
            "request_kind": "desktop_draft_article",
        }
        if source_kind:
            provider_context["source_kind"] = source_kind
        if (
            provider_context.get("source_kind")
            != _desktop_semantic_providers.SEMANTIC_SOURCE_APPROVED_CLEAN_TICKET
        ):
            ensure_safe_sanitized_payload(provider_context)
        extraction = provider.propose_candidates(provider_context)
        return desktop_item_candidates_from_semantic_extraction(extraction)

    def start_pending_selection(
        self,
        item_candidates: list[JsonDict],
        *,
        approved_summary_text: str,
        approved_summary_source_kind: str | None = None,
        semantic_item_outcomes: list[JsonDict] | None = None,
    ) -> PendingDraftSelection:
        """Store split-required candidates for a deterministic second call."""

        self._pending_selection = new_pending_draft_selection(
            item_candidates,
            approved_summary_text=approved_summary_text,
            approved_summary_source_kind=approved_summary_source_kind,
            semantic_item_outcomes=semantic_item_outcomes,
            ttl_seconds=self._selection_ttl_seconds,
        )
        return self._pending_selection

    def start_pending_semantic_review(
        self,
        *,
        approved_summary_text: str,
        ticket_ref: str,
        source_kind: str | None = None,
    ) -> PendingSemanticReview:
        """Store a bounded semantic-review packet for a deterministic next call."""

        self._pending_semantic_review = new_pending_semantic_review(
            approved_summary_text=approved_summary_text,
            ticket_ref=ticket_ref,
            source_kind=source_kind,
            ttl_seconds=self._selection_ttl_seconds,
        )
        return self._pending_semantic_review

    def prepared_semantic_review_packet(self, semantic_review_ref: object) -> JsonDict:
        """Return a pending semantic-review packet or raise a controlled error."""

        pending = self._pending_semantic_review_for_ref(semantic_review_ref)
        if pending.packet_prepared:
            raise SemanticReviewUnavailableError
        self._pending_semantic_review = prepared_pending_semantic_review(pending)
        return dict(pending.packet)

    def submitted_semantic_review_candidates(
        self,
        *,
        semantic_review_ref: object,
        semantic_issue_proposal: object = None,
        operator_selection_ref: object = None,
    ) -> JsonDict | tuple[list[JsonDict], str, str, str | None, list[JsonDict]]:
        """Validate a semantic-review submit and return Desktop candidates."""

        pending, is_operator_amendment = (
            self._pending_semantic_review_for_submission(
                semantic_review_ref=semantic_review_ref,
                operator_selection_ref=operator_selection_ref,
            )
        )
        try:
            submission = self._semantic_submission_candidates(
                pending,
                semantic_issue_proposal=semantic_issue_proposal,
            )
        except SemanticReviewBoundaryAmbiguousError:
            raise
        except ContractValidationError as exc:
            self._raise_semantic_submission_invalid(
                pending,
                debug_code="semantic_review_submission_invalid",
                cause=exc,
            )
        except Exception as exc:
            debug_code = getattr(
                exc, "debug_code", "semantic_review_submission_invalid"
            )
            self._raise_semantic_submission_invalid(
                pending,
                debug_code=str(debug_code),
                cause=exc,
            )
        if isinstance(submission, dict):
            return submission
        candidates, semantic_item_outcomes = submission
        self._complete_semantic_review_submission(
            pending,
            candidate_count=len(candidates),
            is_operator_amendment=is_operator_amendment,
        )
        return (
            candidates,
            pending.approved_summary_text,
            pending.ticket_ref,
            pending.source_kind,
            semantic_item_outcomes,
        )

    def _pending_semantic_review_for_submission(
        self,
        *,
        semantic_review_ref: object,
        operator_selection_ref: object,
    ) -> tuple[PendingSemanticReview, bool]:
        pending = self._pending_semantic_review_for_submit(semantic_review_ref)
        if operator_selection_ref is not None:
            return (
                self._pending_semantic_review_for_operator_amendment(
                    pending,
                    operator_selection_ref=operator_selection_ref,
                ),
                True,
            )
        if pending.accepted_for_selection:
            raise SemanticReviewUnavailableError
        return pending, False

    def _complete_semantic_review_submission(
        self,
        pending: PendingSemanticReview,
        *,
        candidate_count: int,
        is_operator_amendment: bool,
    ) -> None:
        if is_operator_amendment:
            self._pending_semantic_review = None
            if candidate_count < 2:
                raise SemanticReviewSubmissionInvalidError(
                    "semantic_review_submission_invalid",
                    correction=None,
                )
            return
        self._pending_semantic_review = replace(
            pending,
            accepted_for_selection=True,
            failed_submit_attempts=0,
            used_correction_stages=(),
        )

    def _pending_semantic_review_for_operator_amendment(
        self,
        pending: PendingSemanticReview,
        *,
        operator_selection_ref: object,
    ) -> PendingSemanticReview:
        if not pending.accepted_for_selection:
            raise SemanticReviewInvalidError
        self._active_selection_for_semantic_amendment(operator_selection_ref)
        if pending.operator_amendment_started:
            return pending
        started = replace(
            pending,
            failed_submit_attempts=0,
            operator_amendment_started=True,
            used_correction_stages=(),
        )
        self._pending_semantic_review = started
        return started

    def _active_selection_for_semantic_amendment(
        self,
        operator_selection_ref: object,
    ) -> PendingDraftSelection:
        pending_selection = self._pending_selection
        if pending_selection is None or not isinstance(operator_selection_ref, str):
            raise SemanticReviewInvalidError
        if operator_selection_ref != pending_selection.selection_ref:
            raise SemanticReviewInvalidError
        if (
            pending_selection.selected_candidate_refs
            or pending_selection.retryable_candidate_refs
        ):
            raise SemanticReviewInvalidError
        return pending_selection

    def _semantic_submission_candidates(
        self,
        pending: PendingSemanticReview,
        *,
        semantic_issue_proposal: object,
    ) -> JsonDict | tuple[list[JsonDict], list[JsonDict]]:
        fallback_environment = _minimal_environment_from_text(
            pending.approved_summary_text
        )
        proposal = semantic_issue_proposal_from_submission(
            pending=pending,
            semantic_issue_proposal=semantic_issue_proposal,
        )
        projected = project_semantic_issue_proposals(
            proposal,
            semantic_review_excerpt_role_index(pending),
        )
        if semantic_projection_requires_terminal_review(projected):
            self._pending_semantic_review = None
            raise SemanticReviewBoundaryAmbiguousError(projected)
        return desktop_candidate_set_from_semantic_issue_proposal(
            proposal,
            projected,
            fallback_environment=fallback_environment,
        )

    def _raise_semantic_submission_invalid(
        self,
        pending: PendingSemanticReview,
        *,
        debug_code: str,
        cause: Exception,
    ) -> None:
        failed_submit_attempts = pending.failed_submit_attempts + 1
        correction, correction_stage = _semantic_correction_for_error(
            debug_code,
            cause,
        )
        if correction is None or not _semantic_correction_stage_allowed(
            pending.used_correction_stages,
            correction_stage,
        ):
            self._pending_semantic_review = None
            bounded_cause_debug_code = (
                debug_code
                if correction is not None
                or debug_code in _TERMINAL_SEMANTIC_SUBMISSION_DEBUG_CODES
                else "semantic_review_submission_invalid"
            )
            terminal_debug_code = (
                debug_code
                if correction is None
                and debug_code in _TERMINAL_SEMANTIC_SUBMISSION_DEBUG_CODES
                else "semantic_issue_submission_invalid"
            )
            raise SemanticReviewSubmissionInvalidError(
                terminal_debug_code,
                correction=None,
                terminal_cause_debug_code=(
                    bounded_cause_debug_code
                    if terminal_debug_code != bounded_cause_debug_code
                    else None
                ),
            ) from cause
        assert correction_stage is not None
        self._pending_semantic_review = replace(
            pending,
            failed_submit_attempts=failed_submit_attempts,
            used_correction_stages=(
                *pending.used_correction_stages,
                correction_stage,
            ),
        )
        correction["retry_allowed"] = True
        raise SemanticReviewSubmissionInvalidError(
            debug_code,
            correction=correction,
        ) from cause

    def _pending_semantic_review_for_submit(
        self,
        semantic_review_ref: object,
    ) -> PendingSemanticReview:
        pending = self._pending_semantic_review_for_ref(semantic_review_ref)
        if not pending.packet_prepared:
            raise SemanticReviewUnavailableError
        return pending

    def _pending_semantic_review_for_ref(
        self,
        semantic_review_ref: object,
    ) -> PendingSemanticReview:
        pending = self._pending_semantic_review
        if pending is None:
            raise SemanticReviewUnavailableError
        if not isinstance(semantic_review_ref, str):
            raise SemanticReviewInvalidError
        if semantic_review_ref != pending.semantic_review_ref:
            raise SemanticReviewInvalidError
        if pending.expires_at <= time.monotonic():
            self._pending_semantic_review = None
            raise SemanticReviewExpiredError
        return pending

    def selected_candidate(
        self,
        *,
        selection_ref: object,
        selected_item_ref: object,
    ) -> JsonDict:
        """Return a selected pending candidate without consuming the selection."""

        pending_selection = self._pending_selection
        if pending_selection is None:
            raise OperatorSelectionUnavailableError
        if pending_selection.expires_at <= time.monotonic():
            self._pending_selection = None
            raise OperatorSelectionExpiredError
        if (
            selection_ref != pending_selection.selection_ref
            or selected_item_ref not in pending_selection.candidate_refs
        ):
            raise OperatorSelectionInvalidError
        try:
            candidate = selected_pending_candidate(pending_selection, selected_item_ref)
        except ContractValidationError as exc:
            raise OperatorSelectionInvalidError from exc
        return candidate

    def mark_selected_candidate_drafted(
        self,
        selected_item_ref: object,
    ) -> PendingDraftSelection | None:
        """Mark one pending candidate as drafted and return remaining state."""

        pending_selection = self._pending_selection
        if pending_selection is None or not isinstance(selected_item_ref, str):
            self._pending_selection = None
            return None
        self._pending_selection = pending_selection_after_draft(
            pending_selection,
            selected_item_ref,
        )
        return self._pending_selection

    def mark_selected_candidate_completed_blocked(
        self,
        selected_item_ref: object,
    ) -> PendingDraftSelection | None:
        """Complete one terminally blocked candidate for the current run."""

        pending_selection = self._pending_selection
        if pending_selection is None or not isinstance(selected_item_ref, str):
            self._pending_selection = None
            return None
        self._pending_selection = pending_selection_after_completed_candidate(
            pending_selection,
            selected_item_ref,
        )
        return self._pending_selection

    def mark_selected_candidate_retryable(
        self,
        selected_item_ref: object,
    ) -> PendingDraftSelection | None:
        """Keep one selected candidate pending for bounded evidence retry."""

        pending_selection = self._pending_selection
        if pending_selection is None or not isinstance(selected_item_ref, str):
            return pending_selection
        self._pending_selection = pending_selection_after_retryable_blocker(
            pending_selection,
            selected_item_ref,
        )
        return self._pending_selection

    def selected_candidate_is_retryable(self, selected_item_ref: object) -> bool:
        """Return whether a pending candidate has a retryable blocker."""

        pending_selection = self._pending_selection
        return (
            pending_selection is not None
            and isinstance(selected_item_ref, str)
            and selected_item_ref in pending_selection.retryable_candidate_refs
        )


def _minimal_environment_from_text(text: str) -> JsonDict:
    """Infer only draft-level product/platform metadata from clean ticket text."""

    platform = _platform_type_from_text(text)
    if not platform:
        return {}
    return {
        "applicable_to": [f"Plesk for {platform}"],
        "platform": platform,
        "product": "Plesk",
    }


def _platform_type_from_text(text: str) -> str:
    return _PLATFORM_TYPE_BY_MATCH_FLAGS.get(_platform_match_flags(text), "")


def _platform_match_flags(text: str) -> tuple[bool, bool]:
    return (
        bool(_WINDOWS_ENVIRONMENT_RE.search(text)),
        bool(_LINUX_ENVIRONMENT_RE.search(text)),
    )


def execute_approved_summary_pipeline(
    arguments: Mapping[str, Any],
    *,
    hooks: ApprovedSummaryPipelineHooks,
) -> ApprovedSummaryExecution:
    """Run the Desktop approved-summary KCS pipeline through adapter hooks."""

    payload = hooks.build_payload(arguments)
    evidence = hooks.build_evidence(arguments, payload)
    safety = hooks.validate_safety(evidence)
    evidence_validation = hooks.validate_evidence(evidence)
    decision = hooks.decide(arguments, evidence)
    reviewer_packet = hooks.render(evidence, decision)
    readiness = hooks.build_readiness(evidence, decision, reviewer_packet)
    item_ref = hooks.item_ref(arguments, decision)
    handoff_request = build_claude_handoff_request(
        decision,
        readiness,
        handoff_ref=f"handoff-{item_ref}",
        safe_context={
            "short_public_safe_summary": hooks.short_summary(arguments),
            "title_hint": bounded_claude_handoff_title_hint(hooks.title(arguments)),
        },
    )
    draft_request_ready = approved_summary_draft_request_ready(
        handoff_request,
        item_ref,
        readiness,
    )
    return ApprovedSummaryExecution(
        arguments=arguments,
        payload=payload,
        evidence=evidence,
        safety=safety,
        evidence_validation=evidence_validation,
        decision=decision,
        reviewer_packet=reviewer_packet,
        readiness=readiness,
        handoff_request=handoff_request,
        draft_request_ready=draft_request_ready,
        item_ref=item_ref,
    )


def finalize_author_result_with_bundle(
    result: Mapping[str, Any],
    *,
    bundle_root: Path,
    include_reviewer_only_html: bool,
    schema_version: str,
) -> JsonDict:
    """Finalize an author result into compact Desktop draft output."""

    if not result.get("ready_for_reviewer"):
        compact = dict(result)
        compact.pop("reviewer_only_html", None)
        compact.pop("zendesk_source_html", None)
        compact["reviewer_bundle_written"] = False
        compact["writes_files"] = False
        return compact
    html = result.get("reviewer_only_html")
    if not isinstance(html, str) or not html:
        return draft_author_failure_result(
            failure_stage="renderer",
            debug_code="reviewer_bundle_html_missing",
            schema_version=schema_version,
        )
    quality_blockers = quality_blocker_gaps(result)
    if quality_blockers and not reviewer_only_quality_debt_allowed(
        quality_blockers
    ):
        return quality_blocked_result(
            result,
            quality_blockers,
            schema_version=schema_version,
        )
    bundle_result = (
        reviewer_only_quality_draft_result(result, quality_blockers)
        if quality_blockers
        else dict(result)
    )
    try:
        bundle = write_desktop_reviewer_bundle(
            root=bundle_root,
            result=bundle_result,
            reviewer_only_html=html,
        )
    except OSError:
        return draft_author_failure_result(
            failure_stage="renderer",
            debug_code="reviewer_bundle_write_failed",
            schema_version=schema_version,
        )
    return compact_draft_result(
        bundle_result,
        bundle,
        include_reviewer_only_html=include_reviewer_only_html,
        reviewer_only_html=html,
    )
