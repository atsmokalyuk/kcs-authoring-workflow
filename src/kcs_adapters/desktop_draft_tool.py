"""Desktop kcs_draft_article orchestration."""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kcs_adapters import desktop_authoring_pipeline as _desktop_authoring_pipeline
from kcs_adapters import desktop_draft_arguments as _desktop_draft_arguments
from kcs_adapters import desktop_draft_batch as _desktop_draft_batch
from kcs_adapters import desktop_payload as _desktop_payload
from kcs_adapters import desktop_reuse_comparison as _desktop_reuse_comparison
from kcs_adapters import desktop_semantic_providers as _desktop_semantic_providers
from kcs_adapters.desktop_semantic_review import SemanticReviewError
from kcs_adapters.desktop_stdio_transport import McpArgumentError
from kcs_adapters.desktop_tool_names import (
    TOOL_CONFIRM_REUSE_COMPARISON,
    TOOL_DRAFT_ARTICLE,
    claude_desktop_tool_alias,
)
from kcs_adapters.desktop_workflow import (
    ApprovedSummaryPipelineStageError,
    DesktopDraftWorkflow,
    NoSemanticCandidatesError,
    OperatorSelectionExpiredError,
    OperatorSelectionInvalidError,
    OperatorSelectionUnavailableError,
    PendingDraftSelection,
    PendingReuseComparison,
    SemanticExtractionProviderUnavailableError,
    attach_pending_selection,
    finalize_author_result_with_bundle,
    remaining_operator_choice_status,
)
from kcs_adapters.desktop_workflow_results import (
    operator_selection_expired_result,
    operator_selection_unavailable_result,
    semantic_provider_unavailable_result,
    semantic_review_metadata_blocked_result,
    semantic_review_required_result,
)
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict

AuthoringCallable = Callable[[Mapping[str, Any]], JsonDict]

_LIKELY_KCS_MATERIAL_RE = re.compile(
    r"\b(?:"
    r"cause|customer|error|fail(?:ed|s|ure)?|fix(?:ed)?|issue|problem|"
    r"resolution|resolved|restart(?:ed)?|root\s+cause|symptoms?|ticket|"
    r"workaround"
    r")\b",
    re.I,
)
_DRAFT_ARTICLE_DESKTOP_TOOL_ALIAS = claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE)
_CONFIRM_REUSE_COMPARISON_DESKTOP_TOOL_ALIAS = claude_desktop_tool_alias(
    TOOL_CONFIRM_REUSE_COMPARISON
)
_CANDIDATE_FREE_COMPARISON_OUTCOMES = frozenset(
    {"need_more_evidence", "none_fit"}
)


@dataclass(frozen=True)
class _DraftArticlePrimaryCallShape:
    has_summary: bool
    has_selection_ref: bool
    has_selected_item_ref: bool
    has_selected_item_refs: bool
    has_operator_resolution_evidence: bool
    has_ticket_ref: bool

    @classmethod
    def from_arguments(
        cls,
        arguments: Mapping[str, Any],
    ) -> _DraftArticlePrimaryCallShape:
        return cls(
            has_summary=bool(arguments.get("approved_summary_text")),
            has_selection_ref=bool(arguments.get("operator_selection_ref")),
            has_selected_item_ref=bool(arguments.get("operator_selected_item_ref")),
            has_selected_item_refs="operator_selected_item_refs" in arguments,
            has_operator_resolution_evidence=(
                "operator_confirmed_resolution_steps" in arguments
            ),
            has_ticket_ref=bool(arguments.get("ticket_ref")),
        )

    @property
    def is_summary_authoring(self) -> bool:
        return (
            self.has_summary
            and not self.has_selection_ref
            and not self.has_selected_item_ref
            and not self.has_selected_item_refs
            and not self.has_operator_resolution_evidence
            and not self.has_ticket_ref
        )

    @property
    def is_ticket_ref_authoring(self) -> bool:
        return (
            self.has_ticket_ref
            and not self.has_summary
            and not self.has_selection_ref
            and not self.has_selected_item_ref
            and not self.has_selected_item_refs
            and not self.has_operator_resolution_evidence
        )

    @property
    def is_operator_selection_authoring(self) -> bool:
        return (
            self.has_selection_ref
            and self.has_selected_item_ref
            and not self.has_selected_item_refs
            and not self.has_summary
            and not self.has_ticket_ref
        )

    @property
    def is_operator_batch_authoring(self) -> bool:
        return (
            self.has_selection_ref
            and self.has_selected_item_refs
            and not self.has_selected_item_ref
            and not self.has_summary
            and not self.has_ticket_ref
        )


@dataclass(frozen=True)
class _ReuseComparisonReplay:
    comparison_ref: str
    outcome: str
    candidate_ref: str | None
    allowed_candidate_refs: frozenset[str]
    result: JsonDict
    expires_at: float


class DesktopDraftArticleTool:
    """Own the Desktop-visible kcs_draft_article state machine."""

    def __init__(
        self,
        *,
        draft_workflow: DesktopDraftWorkflow,
        reviewer_bundle_root: Path,
        schema_version: str,
        author_approved_summary: AuthoringCallable,
        author_ticket: AuthoringCallable,
    ) -> None:
        self._draft_workflow = draft_workflow
        self._reviewer_bundle_root = reviewer_bundle_root
        self._schema_version = schema_version
        self._author_approved_summary = author_approved_summary
        self._author_ticket = author_ticket
        self._last_reuse_comparison_replay: _ReuseComparisonReplay | None = None

    def draft_article(self, arguments: Mapping[str, Any]) -> JsonDict:
        try:
            primary_result = self._draft_article_primary_surface_result(arguments)
            result = (
                primary_result
                if primary_result is not None
                else _author_failure_result(
                    failure_stage="input_validation",
                    debug_code="draft_article_call_shape_invalid",
                    schema_version=self._schema_version,
                )
            )
        except (
            ContractValidationError,
            McpArgumentError,
            _desktop_draft_arguments.DraftArticleArgumentError,
        ):
            result = _author_failure_result(
                failure_stage="input_validation",
                debug_code="draft_article_args_invalid",
                schema_version=self._schema_version,
            )
        if result.get("result_kind") not in {
            "draft_article_batch",
            "reuse_comparison_blocked",
            "reuse_comparison_required",
        }:
            result["result_kind"] = "draft_article_authoring"
        return result

    def prepare_ticket_reuse_comparison(
        self,
        arguments: Mapping[str, Any],
    ) -> JsonDict:
        """Reach the ticket comparison gate through a write-incapable path."""

        try:
            return self._draft_article_from_primary_ticket_ref(
                arguments,
                comparison_only=True,
            )
        except (
            ContractValidationError,
            McpArgumentError,
            _desktop_draft_arguments.DraftArticleArgumentError,
        ):
            return _author_failure_result(
                failure_stage="input_validation",
                debug_code="draft_article_args_invalid",
                schema_version=self._schema_version,
            )

    def prepare_semantic_review(self, arguments: Mapping[str, Any]) -> JsonDict:
        """Return the bounded semantic-review packet for a pending ref."""

        return self._draft_workflow.prepared_semantic_review_packet(
            arguments.get("semantic_review_ref")
        )

    def submit_semantic_review(self, arguments: Mapping[str, Any]) -> JsonDict:
        """Validate semantic-review candidates and continue normal drafting."""

        submission = self._draft_workflow.submitted_semantic_review_candidates(
            semantic_review_ref=arguments.get("semantic_review_ref"),
            semantic_issue_proposal=arguments.get("semantic_issue_proposal"),
        )
        if isinstance(submission, dict):
            return submission
        (
            candidates,
            approved_summary_text,
            ticket_ref,
            approved_summary_source_kind,
            semantic_item_outcomes,
        ) = submission
        candidates = _desktop_draft_arguments.draft_article_candidates_with_refs(
            candidates
        )
        if not candidates:
            result = _author_failure_result(
                failure_stage="semantic_extraction",
                debug_code="semantic_review_submission_invalid",
                schema_version=self._schema_version,
            )
            result["semantic_item_outcomes"] = semantic_item_outcomes
            result["review_summary"]["semantic_item_outcomes"] = semantic_item_outcomes
            return result
        if len(candidates) > 1:
            result = self._split_required_selection_result(
                candidates,
                approved_summary_text=approved_summary_text,
                approved_summary_source_kind=approved_summary_source_kind,
                semantic_item_outcomes=semantic_item_outcomes,
                invalid_debug_code="semantic_review_submission_invalid",
            )
            result["approved_summary_source"] = "semantic_review"
            result["reviewer_bundle_written"] = False
            result["semantic_item_outcomes"] = semantic_item_outcomes
            result["review_summary"]["semantic_item_outcomes"] = semantic_item_outcomes
            result["ticket_ref"] = ticket_ref
            return result
        comparison = self._start_reuse_comparison(
            candidate=candidates[0],
            approved_summary_text=approved_summary_text,
            approved_summary_source_kind=approved_summary_source_kind,
            selected_item_refs=[str(candidates[0]["item_ref"])],
            current_index=0,
            selection_ref=None,
            debug=False,
        )
        if comparison is not None:
            comparison["approved_summary_source"] = "semantic_review"
            comparison["semantic_item_outcomes"] = semantic_item_outcomes
            comparison["ticket_ref"] = ticket_ref
            return comparison
        result = self._author_candidate(
            candidate=candidates[0],
            approved_summary_text=approved_summary_text,
            approved_summary_source_kind=approved_summary_source_kind,
            debug=False,
        )
        _attach_candidate_control_metadata(result, candidates[0])
        result["approved_summary_source"] = "semantic_review"
        result["result_kind"] = "draft_article_authoring"
        result["semantic_item_outcomes"] = semantic_item_outcomes
        result["ticket_ref"] = ticket_ref
        return result

    def confirm_reuse_comparison(
        self,
        arguments: Mapping[str, Any],
    ) -> JsonDict:
        """Apply one operator-confirmed comparison outcome."""

        replay = self._replayed_reuse_comparison(arguments)
        if replay is not None:
            return replay
        pending_before_submit = self._draft_workflow.pending_reuse_comparison
        if (
            pending_before_submit is not None
            and arguments.get("comparison_ref")
            != pending_before_submit.comparison_ref
        ):
            raise _desktop_reuse_comparison.ReuseComparisonInvalidError
        submission = self._draft_workflow.submitted_reuse_comparison(
            comparison_ref=arguments.get("comparison_ref"),
            outcome=arguments.get("outcome"),
            candidate_ref=arguments.get("candidate_ref"),
        )
        pending = submission.pending
        item_ref = pending.selected_item_refs[pending.current_index]
        if submission.outcome == "none_fit":
            result = self._author_candidate(
                candidate=_candidate_with_confirmed_reuse_search(
                    pending.issue_candidate,
                    search_run_ref=pending.evidence.search_run_ref,
                ),
                approved_summary_text=pending.approved_summary_text,
                approved_summary_source_kind=pending.approved_summary_source_kind,
                debug=pending.debug,
            )
            _attach_candidate_control_metadata(result, pending.issue_candidate)
            selection_outcome = _desktop_draft_batch.candidate_result_outcome(result)
        else:
            result = _desktop_reuse_comparison.reuse_comparison_terminal_result(
                submission,
                schema_version=self._schema_version,
            )
            selection_outcome = "completed_blocked"
        self._record_comparison_selection_outcome(
            pending,
            item_ref=item_ref,
            outcome=selection_outcome,
        )
        completed = [
            *pending.completed_outcomes,
            _comparison_outcome_ledger(
                item_ref=item_ref,
                comparison_outcome=submission.outcome,
                result=result,
            ),
        ]
        if (
            submission.outcome != "need_more_evidence"
            and selection_outcome != "workflow_stopped"
            and pending.current_index + 1 < len(pending.selected_item_refs)
        ):
            next_index = pending.current_index + 1
            next_ref = pending.selected_item_refs[next_index]
            next_candidate = self._draft_workflow.selected_candidate(
                selection_ref=pending.selection_ref,
                selected_item_ref=next_ref,
            )
            next_result = self._start_reuse_comparison(
                candidate=next_candidate,
                approved_summary_text=pending.approved_summary_text,
                approved_summary_source_kind=(
                    pending.approved_summary_source_kind
                ),
                selected_item_refs=list(pending.selected_item_refs),
                current_index=next_index,
                selection_ref=pending.selection_ref,
                debug=pending.debug,
                completed_outcomes=completed,
            )
            if next_result is not None:
                next_result["comparison_sequence_outcomes"] = completed
                return self._remember_reuse_comparison(
                    arguments=arguments,
                    pending=pending,
                    result=next_result,
                )
        result["comparison_sequence_outcomes"] = completed
        self._attach_remaining_selection_status(result)
        return self._remember_reuse_comparison(
            arguments=arguments,
            pending=pending,
            result=result,
        )

    def _replayed_reuse_comparison(
        self,
        arguments: Mapping[str, Any],
    ) -> JsonDict | None:
        replay = self._last_reuse_comparison_replay
        if replay is None or arguments.get("comparison_ref") != replay.comparison_ref:
            return None
        if time.monotonic() > replay.expires_at:
            self._last_reuse_comparison_replay = None
            return None
        outcome = arguments.get("outcome")
        candidate_ref = arguments.get("candidate_ref")
        if outcome != replay.outcome:
            raise _desktop_reuse_comparison.ReuseComparisonInvalidError
        if outcome in _CANDIDATE_FREE_COMPARISON_OUTCOMES:
            if (
                candidate_ref is not None
                and (
                    not isinstance(candidate_ref, str)
                    or candidate_ref not in replay.allowed_candidate_refs
                )
            ):
                raise _desktop_reuse_comparison.ReuseComparisonInvalidError
        elif candidate_ref != replay.candidate_ref:
            raise _desktop_reuse_comparison.ReuseComparisonInvalidError
        return deepcopy(replay.result)

    def _remember_reuse_comparison(
        self,
        *,
        arguments: Mapping[str, Any],
        pending: PendingReuseComparison,
        result: JsonDict,
    ) -> JsonDict:
        outcome = str(arguments.get("outcome") or "")
        requested_candidate_ref = arguments.get("candidate_ref")
        candidate_ref = (
            None
            if outcome in _CANDIDATE_FREE_COMPARISON_OUTCOMES
            else (
                requested_candidate_ref
                if isinstance(requested_candidate_ref, str)
                else None
            )
        )
        candidate_cards = _desktop_reuse_comparison.comparison_candidate_cards(
            pending.evidence.candidates
        )
        self._last_reuse_comparison_replay = _ReuseComparisonReplay(
            comparison_ref=pending.comparison_ref,
            outcome=outcome,
            candidate_ref=candidate_ref,
            allowed_candidate_refs=frozenset(
                str(card["candidate_ref"])
                for card in candidate_cards
                if isinstance(card.get("candidate_ref"), str)
            ),
            result=deepcopy(result),
            expires_at=pending.expires_at,
        )
        return result

    def _start_reuse_comparison(
        self,
        *,
        candidate: Mapping[str, object],
        approved_summary_text: str,
        approved_summary_source_kind: str | None,
        selected_item_refs: list[str],
        current_index: int,
        selection_ref: str | None,
        debug: bool,
        completed_outcomes: list[Mapping[str, object]] | None = None,
    ) -> JsonDict | None:
        if not self._draft_workflow.reuse_comparison_enabled:
            return None
        comparison = self._draft_workflow.start_pending_reuse_comparison(
            issue_candidate=candidate,
            approved_summary_text=approved_summary_text,
            approved_summary_source_kind=approved_summary_source_kind,
            selected_item_refs=selected_item_refs,
            current_index=current_index,
            selection_ref=selection_ref,
            debug=debug,
            completed_outcomes=completed_outcomes,
        )
        if isinstance(comparison, PendingReuseComparison):
            return _desktop_reuse_comparison.reuse_comparison_required_result(
                comparison,
                schema_version=self._schema_version,
                submit_tool=_CONFIRM_REUSE_COMPARISON_DESKTOP_TOOL_ALIAS,
            )
        return _desktop_reuse_comparison.reuse_comparison_blocked_result(
            comparison,
            schema_version=self._schema_version,
        )

    def _author_candidate(
        self,
        *,
        candidate: Mapping[str, Any],
        approved_summary_text: str,
        approved_summary_source_kind: str | None,
        debug: bool,
    ) -> JsonDict:
        return self._draft_article_primary_author_result(
            _desktop_draft_arguments.draft_article_authoring_args_from_candidate(
                approved_summary_text=approved_summary_text,
                candidate=_candidate_without_control_metadata(candidate),
                debug=debug,
                approved_summary_source_kind=approved_summary_source_kind,
            )
        )

    def _record_comparison_selection_outcome(
        self,
        pending: PendingReuseComparison,
        *,
        item_ref: str,
        outcome: str,
    ) -> None:
        if pending.selection_ref is None:
            return
        self._record_selected_candidate_outcome(item_ref, outcome)

    def _attach_remaining_selection_status(self, result: JsonDict) -> None:
        remaining = self._draft_workflow.pending_selection
        if remaining is None:
            return
        result.update(
            remaining_operator_choice_status(
                remaining,
                submit_tool=_DRAFT_ARTICLE_DESKTOP_TOOL_ALIAS,
            )
        )

    def _new_pending_draft_selection(
        self,
        item_candidates: list[JsonDict],
        *,
        approved_summary_text: str,
        approved_summary_source_kind: str | None = None,
        semantic_item_outcomes: list[JsonDict] | None = None,
    ) -> PendingDraftSelection:
        return self._draft_workflow.start_pending_selection(
            item_candidates,
            approved_summary_text=approved_summary_text,
            approved_summary_source_kind=approved_summary_source_kind,
            semantic_item_outcomes=semantic_item_outcomes,
        )

    def _draft_article_primary_surface_result(
        self,
        arguments: Mapping[str, Any],
    ) -> JsonDict | None:
        if not set(arguments).issubset(
            _desktop_draft_arguments.DRAFT_ARTICLE_DESKTOP_PRIMARY_ARGS
        ):
            return None
        call_shape = _DraftArticlePrimaryCallShape.from_arguments(arguments)
        if call_shape.is_summary_authoring:
            self._draft_workflow.clear_pending_semantic_review()
            return self._draft_article_from_primary_summary(arguments)
        if call_shape.is_ticket_ref_authoring:
            self._draft_workflow.clear_pending_semantic_review()
            return self._draft_article_from_primary_ticket_ref(arguments)
        if call_shape.is_operator_selection_authoring:
            self._draft_workflow.clear_pending_semantic_review()
            return self._draft_article_from_primary_selection(arguments)
        if call_shape.is_operator_batch_authoring:
            self._draft_workflow.clear_pending_semantic_review()
            return self._draft_article_from_primary_batch(arguments)
        return _author_failure_result(
            failure_stage="input_validation",
            debug_code="draft_article_call_shape_invalid",
            schema_version=self._schema_version,
        )

    def _draft_article_from_primary_summary(
        self,
        arguments: Mapping[str, Any],
        *,
        ticket_ref_for_semantic_review: str | None = None,
        semantic_source_kind: str | None = None,
        comparison_only: bool = False,
    ) -> JsonDict:
        approved_summary_text = _approved_summary_text_for_semantic_source(
            arguments,
            semantic_source_kind=semantic_source_kind,
        )
        try:
            candidates = _desktop_draft_arguments.draft_article_candidates_with_refs(
                self._draft_workflow.item_candidates_from_summary(
                    approved_summary_text,
                    source_kind=semantic_source_kind,
                )
            )
        except SemanticExtractionProviderUnavailableError:
            return semantic_provider_unavailable_result(
                schema_version=self._schema_version,
            )
        except NoSemanticCandidatesError:
            return self._semantic_review_or_no_candidates_result(
                approved_summary_text=approved_summary_text,
                ticket_ref=ticket_ref_for_semantic_review,
            )
        except (ContractValidationError, McpArgumentError, ValueError):
            return _author_failure_result(
                failure_stage="semantic_extraction",
                debug_code="semantic_extraction_output_invalid",
                schema_version=self._schema_version,
            )
        if not candidates:
            return self._semantic_review_or_no_candidates_result(
                approved_summary_text=approved_summary_text,
                ticket_ref=ticket_ref_for_semantic_review,
            )
        if len(candidates) > 1:
            return self._split_required_selection_result(
                candidates,
                approved_summary_text=approved_summary_text,
                approved_summary_source_kind=semantic_source_kind,
                invalid_debug_code="semantic_extraction_output_invalid",
            )
        comparison = self._start_reuse_comparison(
            candidate=candidates[0],
            approved_summary_text=approved_summary_text,
            approved_summary_source_kind=semantic_source_kind,
            selected_item_refs=[str(candidates[0]["item_ref"])],
            current_index=0,
            selection_ref=None,
            debug=arguments.get("debug") is True,
        )
        return self._comparison_or_author_result(
            comparison,
            candidate=candidates[0],
            approved_summary_text=approved_summary_text,
            approved_summary_source_kind=semantic_source_kind,
            debug=arguments.get("debug") is True,
            comparison_only=comparison_only,
        )

    def _comparison_or_author_result(
        self,
        comparison: JsonDict | None,
        *,
        candidate: Mapping[str, Any],
        approved_summary_text: str,
        approved_summary_source_kind: str | None,
        debug: bool,
        comparison_only: bool,
    ) -> JsonDict:
        if comparison is not None:
            return comparison
        if comparison_only:
            return _author_failure_result(
                failure_stage="reuse_comparison",
                debug_code="reuse_comparison_gate_unavailable",
                schema_version=self._schema_version,
            )
        result = self._author_candidate(
            candidate=candidate,
            approved_summary_text=approved_summary_text,
            approved_summary_source_kind=approved_summary_source_kind,
            debug=debug,
        )
        _attach_candidate_control_metadata(result, candidate)
        return result

    def _draft_article_from_primary_ticket_ref(
        self,
        arguments: Mapping[str, Any],
        *,
        comparison_only: bool = False,
    ) -> JsonDict:
        ticket_ref = _ticket_ref_from_arguments(arguments)
        try:
            approved_arguments = _ticket_author_arguments(arguments)
        except ApprovedSummaryPipelineStageError as exc:
            return _ticket_author_failure_result(
                ticket_ref=ticket_ref,
                failure_stage="input_validation",
                debug_code=exc.debug_code,
                schema_version=self._schema_version,
            )
        if _desktop_draft_arguments.has_structured_approved_summary_item_input(
            approved_arguments
        ):
            return self._structured_ticket_ref_result(
                arguments,
                approved_arguments=approved_arguments,
                ticket_ref=ticket_ref,
                comparison_only=comparison_only,
            )
        summary_arguments: JsonDict = {
            "approved_summary_text": approved_arguments["approved_summary_text"],
        }
        if arguments.get("debug") is True:
            summary_arguments["debug"] = True
        result = self._draft_article_from_primary_summary(
            summary_arguments,
            ticket_ref_for_semantic_review=ticket_ref,
            semantic_source_kind=(
                _desktop_semantic_providers.SEMANTIC_SOURCE_APPROVED_CLEAN_TICKET
            ),
            comparison_only=comparison_only,
        )
        result["approved_summary_source"] = "local_clean_ticket"
        result["ticket_ref"] = ticket_ref
        return result

    def _structured_ticket_ref_result(
        self,
        arguments: Mapping[str, Any],
        *,
        approved_arguments: Mapping[str, Any],
        ticket_ref: str,
        comparison_only: bool,
    ) -> JsonDict:
        item = _desktop_payload.approved_summary_optional_item_object(
            approved_arguments
        )
        if item is not None:
            comparison = self._structured_ticket_ref_comparison(
                arguments,
                approved_arguments=approved_arguments,
                item=item,
                ticket_ref=ticket_ref,
            )
            if comparison is not None:
                return comparison
        if comparison_only:
            return _ticket_author_failure_result(
                ticket_ref=ticket_ref,
                failure_stage="reuse_comparison",
                debug_code="reuse_comparison_gate_unavailable",
                schema_version=self._schema_version,
            )
        result = self._author_ticket(arguments)
        finalized = finalize_author_result_with_bundle(
            result,
            bundle_root=self._reviewer_bundle_root,
            include_reviewer_only_html=arguments.get("debug") is True,
            schema_version=self._schema_version,
        )
        finalized["approved_summary_source"] = "local_approved_summary"
        finalized["ticket_ref"] = ticket_ref
        return finalized

    def _structured_ticket_ref_comparison(
        self,
        arguments: Mapping[str, Any],
        *,
        approved_arguments: Mapping[str, Any],
        item: Mapping[str, Any],
        ticket_ref: str,
    ) -> JsonDict | None:
        candidate = dict(item)
        candidate.setdefault(
            "item_ref",
            str(candidate.get("candidate_id") or "candidate-001"),
        )
        comparison = self._start_reuse_comparison(
            candidate=candidate,
            approved_summary_text=str(
                approved_arguments.get("approved_summary_text") or ""
            ),
            approved_summary_source_kind=(
                _desktop_semantic_providers.SEMANTIC_SOURCE_APPROVED_CLEAN_TICKET
            ),
            selected_item_refs=[str(candidate["item_ref"])],
            current_index=0,
            selection_ref=None,
            debug=arguments.get("debug") is True,
        )
        if comparison is not None:
            comparison["approved_summary_source"] = "local_approved_summary"
            comparison["ticket_ref"] = ticket_ref
        return comparison

    def _semantic_review_or_no_candidates_result(
        self,
        *,
        approved_summary_text: str,
        ticket_ref: str | None,
    ) -> JsonDict:
        if ticket_ref and _likely_kcs_material(approved_summary_text):
            try:
                _desktop_authoring_pipeline.clean_ticket_semantic_review_metadata(
                    ticket_ref=ticket_ref,
                    approved_summary_text=approved_summary_text,
                )
            except ApprovedSummaryPipelineStageError as exc:
                return semantic_review_metadata_blocked_result(
                    debug_code=exc.debug_code,
                    schema_version=self._schema_version,
                )
            else:
                try:
                    pending_review = self._draft_workflow.start_pending_semantic_review(
                        approved_summary_text=approved_summary_text,
                        ticket_ref=ticket_ref,
                        source_kind=(
                            _desktop_semantic_providers.SEMANTIC_SOURCE_APPROVED_CLEAN_TICKET
                        ),
                    )
                except SemanticReviewError as exc:
                    return _author_failure_result(
                        failure_stage="semantic_extraction",
                        debug_code=exc.debug_code,
                        schema_version=self._schema_version,
                    )
                except ContractValidationError:
                    return _author_failure_result(
                        failure_stage="semantic_extraction",
                        debug_code="semantic_review_packet_invalid",
                        schema_version=self._schema_version,
                    )
                packet = pending_review.packet
                result = semantic_review_required_result(
                    schema_version=self._schema_version,
                    semantic_review_ref=pending_review.semantic_review_ref,
                )
                result["excerpt_count"] = packet["excerpt_count"]
                result["excerpt_total_bytes"] = packet["excerpt_total_bytes"]
                result["semantic_review_packet_sha256"] = packet[
                    "semantic_review_packet_sha256"
                ]
                return result
        return _author_failure_result(
            failure_stage="semantic_extraction",
            debug_code="semantic_extraction_no_candidates",
            schema_version=self._schema_version,
        )

    def _draft_article_from_primary_selection(
        self,
        arguments: Mapping[str, Any],
    ) -> JsonDict:
        pending_selection = self._draft_workflow.pending_selection
        if pending_selection is None:
            return operator_selection_unavailable_result(
                schema_version=self._schema_version,
            )
        selection_ref = arguments.get("operator_selection_ref")
        selected_item_ref = arguments.get("operator_selected_item_ref")
        try:
            candidate = self._draft_workflow.selected_candidate(
                selection_ref=selection_ref,
                selected_item_ref=selected_item_ref,
            )
        except OperatorSelectionExpiredError:
            return operator_selection_expired_result(
                schema_version=self._schema_version,
            )
        except OperatorSelectionUnavailableError:
            return operator_selection_unavailable_result(
                schema_version=self._schema_version,
            )
        except OperatorSelectionInvalidError:
            return _desktop_draft_arguments.draft_article_selection_error_result(
                arguments,
                pending_selection,
                schema_version=self._schema_version,
                submit_tool=_DRAFT_ARTICLE_DESKTOP_TOOL_ALIAS,
            )
        operator_steps, evidence_failure = self._operator_resolution_steps(
            arguments,
            selected_item_ref,
        )
        if evidence_failure is not None:
            return evidence_failure
        comparison = self._start_primary_selection_comparison(
            arguments=arguments,
            candidate=candidate,
            operator_steps=operator_steps,
            pending_selection=pending_selection,
            selected_item_ref=selected_item_ref,
            selection_ref=selection_ref,
        )
        if comparison is not None:
            return comparison
        result = self._draft_article_primary_author_result(
            _selected_candidate_authoring_arguments(
                pending_selection=pending_selection,
                candidate=candidate,
                debug=arguments.get("debug") is True,
                operator_confirmed_resolution_steps=operator_steps,
            )
        )
        _attach_candidate_control_metadata(result, candidate)
        result["semantic_item_outcomes"] = list(
            pending_selection.semantic_item_outcomes
        )
        outcome = _desktop_draft_batch.candidate_result_outcome(result)
        remaining_selection = self._record_selected_candidate_outcome(
            selected_item_ref,
            outcome,
        )
        _attach_operator_evidence_provenance(result, operator_steps)
        _attach_remaining_selection_after_outcome(
            result,
            outcome=outcome,
            remaining_selection=remaining_selection,
        )
        return result

    def _start_primary_selection_comparison(
        self,
        *,
        arguments: Mapping[str, Any],
        candidate: Mapping[str, Any],
        operator_steps: list[str] | None,
        pending_selection: PendingDraftSelection,
        selected_item_ref: object,
        selection_ref: object,
    ) -> JsonDict | None:
        if operator_steps is not None:
            return None
        if self._draft_workflow.selected_candidate_is_retryable(selected_item_ref):
            return None
        return self._start_reuse_comparison(
            candidate=candidate,
            approved_summary_text=pending_selection.approved_summary_text,
            approved_summary_source_kind=(
                pending_selection.approved_summary_source_kind
            ),
            selected_item_refs=[str(selected_item_ref)],
            current_index=0,
            selection_ref=str(selection_ref),
            debug=arguments.get("debug") is True,
        )

    def _operator_resolution_steps(
        self,
        arguments: Mapping[str, Any],
        selected_item_ref: object,
    ) -> tuple[list[str] | None, JsonDict | None]:
        candidate_is_retryable = self._draft_workflow.selected_candidate_is_retryable(
            selected_item_ref
        )
        if "operator_confirmed_resolution_steps" not in arguments:
            if candidate_is_retryable:
                return None, _operator_resolution_evidence_failure_result(
                    debug_code="operator_resolution_evidence_required",
                    schema_version=self._schema_version,
                )
            return None, None
        if not candidate_is_retryable:
            return None, _operator_resolution_evidence_failure_result(
                debug_code="operator_resolution_evidence_unavailable",
                schema_version=self._schema_version,
            )
        try:
            return (
                _desktop_draft_arguments.operator_confirmed_resolution_steps(
                    arguments.get("operator_confirmed_resolution_steps")
                ),
                None,
            )
        except _desktop_draft_arguments.DraftArticleArgumentError:
            return None, _operator_resolution_evidence_failure_result(
                debug_code="operator_resolution_evidence_invalid",
                schema_version=self._schema_version,
            )

    def _draft_article_from_primary_batch(
        self,
        arguments: Mapping[str, Any],
    ) -> JsonDict:
        pending_selection = self._draft_workflow.pending_selection
        if pending_selection is None:
            return _draft_batch_stopped_result(
                debug_code="operator_selection_invalid",
                failure_stage="operator_selection",
                schema_version=self._schema_version,
            )
        selected_item_refs, candidates, selection_failure = (
            self._validated_batch_selection(arguments)
        )
        if selection_failure is not None:
            return selection_failure
        if self._draft_workflow.reuse_comparison_enabled:
            return self._start_reuse_comparison(
                candidate=candidates[0],
                approved_summary_text=pending_selection.approved_summary_text,
                approved_summary_source_kind=(
                    pending_selection.approved_summary_source_kind
                ),
                selected_item_refs=selected_item_refs,
                current_index=0,
                selection_ref=str(arguments.get("operator_selection_ref")),
                debug=arguments.get("debug") is True,
            ) or _draft_batch_stopped_result(
                debug_code="reuse_comparison_unavailable",
                failure_stage="reuse_comparison",
                schema_version=self._schema_version,
            )

        candidate_labels = {
            item_ref: candidate["title"]
            for item_ref, candidate in zip(selected_item_refs, candidates, strict=True)
            if isinstance(candidate.get("title"), str) and candidate["title"]
        }
        candidate_outcomes: list[JsonDict] = []
        for index, (item_ref, candidate) in enumerate(
            zip(selected_item_refs, candidates, strict=True)
        ):
            try:
                result = self._draft_article_primary_author_result(
                    _selected_candidate_authoring_arguments(
                        pending_selection=pending_selection,
                        candidate=candidate,
                        debug=arguments.get("debug") is True,
                    )
                )
            except (
                ContractValidationError,
                McpArgumentError,
                _desktop_draft_arguments.DraftArticleArgumentError,
            ):
                result = _author_failure_result(
                    failure_stage="input_validation",
                    debug_code="draft_article_args_invalid",
                    schema_version=self._schema_version,
                )
            _attach_candidate_control_metadata(result, candidate)
            outcome = _desktop_draft_batch.candidate_result_outcome(result)
            candidate_outcomes.append(
                _desktop_draft_batch.candidate_outcome_ledger(
                    item_ref=item_ref,
                    outcome=outcome,
                    result=result,
                )
            )
            self._record_selected_candidate_outcome(item_ref, outcome)
            if outcome == "workflow_stopped":
                candidate_outcomes.extend(
                    _desktop_draft_batch.not_attempted_candidate_outcome(
                        remaining_item_ref
                    )
                    for remaining_item_ref in selected_item_refs[index + 1 :]
                )
                return _draft_batch_result(
                    batch_status="batch_stopped",
                    candidate_outcomes=candidate_outcomes,
                    failure_result=result,
                    pending_selection=self._draft_workflow.pending_selection,
                    schema_version=self._schema_version,
                    candidate_labels=candidate_labels,
                )
        return _draft_batch_result(
            batch_status=(
                "batch_completed"
                if all(
                    item["outcome"] == "completed_draft" for item in candidate_outcomes
                )
                else "batch_completed_with_blockers"
            ),
            candidate_outcomes=candidate_outcomes,
            failure_result=None,
            pending_selection=self._draft_workflow.pending_selection,
            schema_version=self._schema_version,
            candidate_labels=candidate_labels,
        )

    def _validated_batch_selection(
        self,
        arguments: Mapping[str, Any],
    ) -> tuple[list[str], list[JsonDict], JsonDict | None]:
        if "operator_confirmed_resolution_steps" in arguments:
            return (
                [],
                [],
                _draft_batch_stopped_result(
                    debug_code="operator_resolution_evidence_invalid",
                    failure_stage="operator_selection",
                    schema_version=self._schema_version,
                ),
            )
        selected_item_refs = arguments.get("operator_selected_item_refs")
        if not _desktop_draft_batch.valid_batch_item_refs(selected_item_refs):
            return (
                [],
                [],
                _draft_batch_stopped_result(
                    debug_code="operator_selection_invalid",
                    failure_stage="operator_selection",
                    schema_version=self._schema_version,
                ),
            )
        assert isinstance(selected_item_refs, list)
        if any(
            self._draft_workflow.selected_candidate_is_retryable(item_ref)
            for item_ref in selected_item_refs
        ):
            return (
                [],
                [],
                _draft_batch_stopped_result(
                    debug_code="operator_resolution_evidence_required",
                    failure_stage="operator_selection",
                    schema_version=self._schema_version,
                ),
            )
        try:
            candidates = [
                self._draft_workflow.selected_candidate(
                    selection_ref=arguments.get("operator_selection_ref"),
                    selected_item_ref=item_ref,
                )
                for item_ref in selected_item_refs
            ]
        except OperatorSelectionExpiredError:
            return (
                [],
                [],
                _draft_batch_stopped_result(
                    debug_code="operator_selection_expired",
                    failure_stage="operator_selection",
                    schema_version=self._schema_version,
                ),
            )
        except (OperatorSelectionInvalidError, OperatorSelectionUnavailableError):
            return (
                [],
                [],
                _draft_batch_stopped_result(
                    debug_code="operator_selection_invalid",
                    failure_stage="operator_selection",
                    schema_version=self._schema_version,
                ),
            )
        return selected_item_refs, candidates, None

    def _record_selected_candidate_outcome(
        self,
        selected_item_ref: object,
        outcome: str,
    ) -> PendingDraftSelection | None:
        if outcome == "completed_draft":
            return self._draft_workflow.mark_selected_candidate_drafted(
                selected_item_ref
            )
        if outcome == "blocked_retryable":
            return self._draft_workflow.mark_selected_candidate_retryable(
                selected_item_ref
            )
        if outcome == "completed_blocked":
            return self._draft_workflow.mark_selected_candidate_completed_blocked(
                selected_item_ref
            )
        return self._draft_workflow.pending_selection

    def _draft_article_primary_author_result(
        self,
        arguments: Mapping[str, Any],
    ) -> JsonDict:
        result = self._author_approved_summary(arguments)
        return finalize_author_result_with_bundle(
            result,
            bundle_root=self._reviewer_bundle_root,
            include_reviewer_only_html=arguments.get("debug") is True,
            schema_version=self._schema_version,
        )

    def _split_required_selection_result(
        self,
        candidates: list[JsonDict],
        *,
        approved_summary_text: str,
        approved_summary_source_kind: str | None,
        invalid_debug_code: str,
        semantic_item_outcomes: list[JsonDict] | None = None,
    ) -> JsonDict:
        result = _desktop_draft_arguments.draft_article_split_required_result(
            {"item_candidates": candidates},
            schema_version=self._schema_version,
        )
        if result is None:  # pragma: no cover - defensive invariant
            return _author_failure_result(
                failure_stage="semantic_extraction",
                debug_code=invalid_debug_code,
                schema_version=self._schema_version,
            )
        pending_selection = self._new_pending_draft_selection(
            candidates,
            approved_summary_text=approved_summary_text,
            approved_summary_source_kind=approved_summary_source_kind,
            semantic_item_outcomes=semantic_item_outcomes,
        )
        attach_pending_selection(
            result,
            pending_selection,
            submit_tool=_DRAFT_ARTICLE_DESKTOP_TOOL_ALIAS,
        )
        return result


def _selected_candidate_authoring_arguments(
    *,
    pending_selection: PendingDraftSelection,
    candidate: Mapping[str, Any],
    debug: bool,
    operator_confirmed_resolution_steps: list[str] | None = None,
) -> JsonDict:
    arguments = _desktop_draft_arguments.draft_article_authoring_args_from_candidate(
        approved_summary_text=pending_selection.approved_summary_text,
        candidate=_candidate_without_control_metadata(candidate),
        debug=debug,
        approved_summary_source_kind=(pending_selection.approved_summary_source_kind),
    )
    if operator_confirmed_resolution_steps is None:
        return arguments
    item = dict(arguments["item"])
    item["resolution_steps"] = list(operator_confirmed_resolution_steps)
    arguments["item"] = item
    arguments["_operator_resolution_evidence_provenance"] = (
        _desktop_draft_arguments.OPERATOR_RESOLUTION_EVIDENCE_PROVENANCE
    )
    return arguments


def _attach_remaining_selection_after_outcome(
    result: JsonDict,
    *,
    outcome: str,
    remaining_selection: PendingDraftSelection | None,
) -> None:
    if outcome == "workflow_stopped" or remaining_selection is None:
        return
    result.update(
        remaining_operator_choice_status(
            remaining_selection,
            submit_tool=_DRAFT_ARTICLE_DESKTOP_TOOL_ALIAS,
        )
    )


def _candidate_without_control_metadata(
    candidate: Mapping[str, Any],
) -> JsonDict:
    authoring_candidate = dict(candidate)
    authoring_candidate.pop("candidate_origin", None)
    return authoring_candidate


def _candidate_with_confirmed_reuse_search(
    candidate: Mapping[str, Any],
    *,
    search_run_ref: str,
) -> JsonDict:
    confirmed = _candidate_without_public_article_delegation(candidate)
    confirmed["reuse_search_checked"] = True
    confirmed["reuse_search_run_ref"] = search_run_ref
    return confirmed


def _candidate_without_public_article_delegation(
    candidate: Mapping[str, Any],
) -> JsonDict:
    confirmed = dict(candidate)
    for key in ("supported_answer", "supported_resolution_or_workaround"):
        value = confirmed.get(key)
        if isinstance(value, str) and _desktop_reuse_comparison.has_public_article_url(
            value
        ):
            confirmed.pop(key)
    steps = confirmed.get("resolution_steps")
    if isinstance(steps, list):
        confirmed["resolution_steps"] = [
            step
            for step in steps
            if not (
                isinstance(step, str)
                and _desktop_reuse_comparison.has_public_article_url(step)
            )
        ]
    elif isinstance(steps, str) and _desktop_reuse_comparison.has_public_article_url(
        steps
    ):
        confirmed.pop("resolution_steps")
    return confirmed


def _attach_candidate_control_metadata(
    result: JsonDict,
    candidate: Mapping[str, Any],
) -> None:
    article_type = candidate.get("article_type")
    if (
        isinstance(article_type, str)
        and article_type
        and result.get("article_type") in {None, "none"}
    ):
        result["article_type"] = article_type
    candidate_origin = candidate.get("candidate_origin")
    if isinstance(candidate_origin, str) and candidate_origin:
        result["candidate_origin"] = candidate_origin


def _attach_operator_evidence_provenance(
    result: JsonDict,
    operator_confirmed_resolution_steps: list[str] | None,
) -> None:
    if operator_confirmed_resolution_steps is not None:
        result["operator_evidence_provenance"] = (
            _desktop_draft_arguments.OPERATOR_RESOLUTION_EVIDENCE_PROVENANCE
        )


def _comparison_outcome_ledger(
    *,
    item_ref: str,
    comparison_outcome: str,
    result: Mapping[str, Any],
) -> JsonDict:
    ledger: JsonDict = {
        "comparison_outcome": comparison_outcome,
        "draft_generated": result.get("draft_generated") is True,
        "item_ref": item_ref,
        "recommended_action": str(result.get("recommended_action") or ""),
        "reviewer_bundle_written": result.get("reviewer_bundle_written") is True,
    }
    bundle_ref = result.get("bundle_ref")
    if isinstance(bundle_ref, str) and bundle_ref:
        ledger["bundle_ref"] = bundle_ref
    for key in ("manifest_path", "html_path"):
        artifact_path = result.get(key)
        if isinstance(artifact_path, str) and artifact_path:
            ledger[key] = artifact_path
    return ledger


def _draft_batch_result(
    *,
    batch_status: str,
    candidate_outcomes: list[JsonDict],
    failure_result: Mapping[str, Any] | None,
    pending_selection: PendingDraftSelection | None,
    schema_version: str,
    candidate_labels: Mapping[str, str] | None = None,
) -> JsonDict:
    remaining_status: JsonDict | None = None
    semantic_item_outcomes: list[JsonDict] | None = None
    if pending_selection is not None and batch_status != "batch_stopped":
        semantic_item_outcomes = list(pending_selection.semantic_item_outcomes)
        remaining_status = remaining_operator_choice_status(
            pending_selection,
            submit_tool=_DRAFT_ARTICLE_DESKTOP_TOOL_ALIAS,
        )
    return _desktop_draft_batch.batch_result(
        batch_status=batch_status,
        candidate_outcomes=candidate_outcomes,
        failure_result=failure_result,
        remaining_status=remaining_status,
        schema_version=schema_version,
        candidate_labels=candidate_labels,
        semantic_item_outcomes=semantic_item_outcomes,
    )


def _draft_batch_stopped_result(
    *,
    debug_code: str,
    failure_stage: str,
    schema_version: str,
) -> JsonDict:
    failure = _author_failure_result(
        failure_stage=failure_stage,
        debug_code=debug_code,
        schema_version=schema_version,
    )
    return _draft_batch_result(
        batch_status="batch_stopped",
        candidate_outcomes=[],
        failure_result=failure,
        pending_selection=None,
        schema_version=schema_version,
    )


def _operator_resolution_evidence_failure_result(
    *,
    debug_code: str,
    schema_version: str,
) -> JsonDict:
    result = _author_failure_result(
        failure_stage="operator_selection",
        debug_code=debug_code,
        schema_version=schema_version,
    )
    result["manual_draft_allowed"] = False
    result["next_required_action"] = (
        "submit_bounded_operator_confirmed_resolution_steps"
        if debug_code
        in {
            "operator_resolution_evidence_invalid",
            "operator_resolution_evidence_required",
        }
        else "select_retryable_candidate_before_submitting_resolution_steps"
    )
    return result


def _author_failure_result(
    *,
    failure_stage: str,
    debug_code: str,
    schema_version: str,
) -> JsonDict:
    return _desktop_authoring_pipeline.author_failure_result(
        failure_stage=failure_stage,
        debug_code=debug_code,
        schema_version=schema_version,
    )


def _ticket_author_failure_result(
    *,
    ticket_ref: str,
    failure_stage: str,
    debug_code: str,
    schema_version: str,
) -> JsonDict:
    return _desktop_authoring_pipeline.ticket_author_failure_result(
        ticket_ref=ticket_ref,
        failure_stage=failure_stage,
        debug_code=debug_code,
        schema_version=schema_version,
    )


def _ticket_author_arguments(arguments: Mapping[str, Any]) -> JsonDict:
    try:
        return _desktop_authoring_pipeline.ticket_author_arguments(arguments)
    except _desktop_authoring_pipeline.DesktopAuthoringArgumentError:
        raise McpArgumentError("Invalid approved ticket arguments.") from None


def _ticket_ref_from_arguments(arguments: Mapping[str, Any]) -> str:
    return _desktop_authoring_pipeline.ticket_ref_from_arguments(arguments)


def _approved_summary_text_for_semantic_source(
    arguments: Mapping[str, Any],
    *,
    semantic_source_kind: str | None,
) -> str:
    if (
        semantic_source_kind
        == _desktop_semantic_providers.SEMANTIC_SOURCE_APPROVED_CLEAN_TICKET
    ):
        return str(arguments.get("approved_summary_text", "")).strip()
    return _desktop_payload.approved_summary_text_argument(arguments)


def _likely_kcs_material(text: str) -> bool:
    return len(text.encode("utf-8")) >= 120 and bool(
        _LIKELY_KCS_MATERIAL_RE.search(text)
    )


__all__ = [
    "AuthoringCallable",
    "DesktopDraftArticleTool",
]
