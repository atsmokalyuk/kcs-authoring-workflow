"""Desktop kcs_draft_article orchestration."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from kcs_adapters import desktop_authoring_pipeline as _desktop_authoring_pipeline
from kcs_adapters import desktop_draft_arguments as _desktop_draft_arguments
from kcs_adapters import desktop_payload as _desktop_payload
from kcs_adapters.desktop_semantic_review import SemanticReviewError
from kcs_adapters.desktop_stdio_transport import McpArgumentError
from kcs_adapters.desktop_tool_names import (
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
    SemanticExtractionProviderUnavailableError,
    attach_pending_selection,
    finalize_author_result_with_bundle,
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

    def draft_article(self, arguments: Mapping[str, Any]) -> JsonDict:
        try:
            primary_result = self._draft_article_primary_surface_result(
                arguments
            )
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
        result["result_kind"] = "draft_article_authoring"
        return result

    def prepare_semantic_review(self, arguments: Mapping[str, Any]) -> JsonDict:
        """Return the bounded semantic-review packet for a pending ref."""

        return self._draft_workflow.prepared_semantic_review_packet(
            arguments.get("semantic_review_ref")
        )

    def _new_pending_draft_selection(
        self,
        item_candidates: list[JsonDict],
        *,
        approved_summary_text: str,
    ) -> PendingDraftSelection:
        return self._draft_workflow.start_pending_selection(
            item_candidates,
            approved_summary_text=approved_summary_text,
        )

    def _draft_article_primary_surface_result(
        self,
        arguments: Mapping[str, Any],
    ) -> JsonDict | None:
        if not set(arguments).issubset(
            _desktop_draft_arguments.DRAFT_ARTICLE_DESKTOP_PRIMARY_ARGS
        ):
            return None
        has_summary = bool(arguments.get("approved_summary_text"))
        has_selection_ref = bool(arguments.get("operator_selection_ref"))
        has_selected_item_ref = bool(arguments.get("operator_selected_item_ref"))
        has_ticket_ref = bool(arguments.get("ticket_ref"))
        if (
            has_summary
            and not has_selection_ref
            and not has_selected_item_ref
            and not has_ticket_ref
        ):
            self._draft_workflow.clear_pending_semantic_review()
            return self._draft_article_from_primary_summary(arguments)
        if (
            has_ticket_ref
            and not has_summary
            and not has_selection_ref
            and not has_selected_item_ref
        ):
            self._draft_workflow.clear_pending_semantic_review()
            return self._draft_article_from_primary_ticket_ref(arguments)
        if (
            has_selection_ref
            and has_selected_item_ref
            and not has_summary
            and not has_ticket_ref
        ):
            self._draft_workflow.clear_pending_semantic_review()
            return self._draft_article_from_primary_selection(arguments)
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
    ) -> JsonDict:
        approved_summary_text = _desktop_payload.approved_summary_text_argument(
            arguments
        )
        try:
            candidates = _desktop_draft_arguments.draft_article_candidates_with_refs(
                self._draft_workflow.item_candidates_from_summary(
                    approved_summary_text
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
            result = _desktop_draft_arguments.draft_article_split_required_result(
                {"item_candidates": candidates},
                schema_version=self._schema_version,
            )
            if result is None:  # pragma: no cover - defensive invariant
                return _author_failure_result(
                    failure_stage="semantic_extraction",
                    debug_code="semantic_extraction_output_invalid",
                    schema_version=self._schema_version,
                )
            pending_selection = self._new_pending_draft_selection(
                candidates,
                approved_summary_text=approved_summary_text,
            )
            attach_pending_selection(
                result,
                pending_selection,
                submit_tool=claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
            )
            return result
        return self._draft_article_primary_author_result(
            _desktop_draft_arguments.draft_article_authoring_args_from_candidate(
                approved_summary_text=approved_summary_text,
                candidate=candidates[0],
                debug=arguments.get("debug") is True,
            )
        )

    def _draft_article_from_primary_ticket_ref(
        self,
        arguments: Mapping[str, Any],
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
        summary_arguments: JsonDict = {
            "approved_summary_text": approved_arguments["approved_summary_text"],
        }
        if arguments.get("debug") is True:
            summary_arguments["debug"] = True
        result = self._draft_article_from_primary_summary(
            summary_arguments,
            ticket_ref_for_semantic_review=ticket_ref,
        )
        result["approved_summary_source"] = "local_clean_ticket"
        result["ticket_ref"] = ticket_ref
        return result

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
                    pending_review = (
                        self._draft_workflow.start_pending_semantic_review(
                            approved_summary_text=approved_summary_text,
                            ticket_ref=ticket_ref,
                        )
                    )
                except SemanticReviewError as exc:
                    return _author_failure_result(
                        failure_stage="semantic_extraction",
                        debug_code=exc.debug_code,
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
                submit_tool=claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE),
            )
        return self._draft_article_primary_author_result(
            _desktop_draft_arguments.draft_article_authoring_args_from_candidate(
                approved_summary_text=pending_selection.approved_summary_text,
                candidate=candidate,
                debug=arguments.get("debug") is True,
            )
        )

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


def _likely_kcs_material(text: str) -> bool:
    return len(text.encode("utf-8")) >= 120 and bool(
        _LIKELY_KCS_MATERIAL_RE.search(text)
    )


__all__ = [
    "AuthoringCallable",
    "DesktopDraftArticleTool",
]
