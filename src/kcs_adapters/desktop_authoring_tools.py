"""Desktop authoring tool handlers for the MCP adapter."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from kcs_adapters import desktop_authoring_pipeline as _desktop_authoring_pipeline
from kcs_adapters import desktop_draft_arguments as _desktop_draft_arguments
from kcs_adapters import desktop_payload as _desktop_payload
from kcs_adapters import desktop_ticket_ref as _desktop_ticket_ref
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
    operator_selection_expired_result,
    operator_selection_unavailable_result,
    semantic_provider_unavailable_result,
)
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict

ApprovedSummaryInputError = _desktop_payload.ApprovedSummaryInputError


class DesktopAuthoringTools:
    """Own Desktop authoring/register/draft tool handlers."""

    def __init__(
        self,
        *,
        draft_workflow: DesktopDraftWorkflow,
        reviewer_bundle_root: Path,
        schema_version: str,
    ) -> None:
        self._draft_workflow = draft_workflow
        self._reviewer_bundle_root = reviewer_bundle_root
        self._schema_version = schema_version

    def run_approved_summary_pipeline(
        self,
        arguments: Mapping[str, Any],
    ) -> JsonDict:
        try:
            execution = _execute_approved_summary_pipeline(arguments)
        except ApprovedSummaryPipelineStageError as exc:
            return _desktop_authoring_pipeline.pipeline_failure_result(
                failure_stage=exc.failure_stage,
                debug_code=exc.debug_code,
                schema_version=self._schema_version,
            )
        return _approved_summary_pipeline_status(
            execution,
            schema_version=self._schema_version,
        )

    def author_approved_summary(
        self,
        arguments: Mapping[str, Any],
    ) -> JsonDict:
        try:
            execution = _execute_approved_summary_pipeline(arguments)
        except ApprovedSummaryPipelineStageError as exc:
            return _approved_summary_author_failure_result(
                failure_stage=exc.failure_stage,
                debug_code=exc.debug_code,
                schema_version=self._schema_version,
            )
        return _approved_summary_author_result(
            execution,
            schema_version=self._schema_version,
        )

    def author_ticket(self, arguments: Mapping[str, Any]) -> JsonDict:
        ticket_ref = _approved_ticket_ref_from_arguments(arguments)
        try:
            approved_arguments = _approved_ticket_author_arguments(arguments)
            execution = _execute_approved_summary_pipeline(approved_arguments)
        except ApprovedSummaryPipelineStageError as exc:
            return _approved_ticket_author_failure_result(
                ticket_ref=ticket_ref,
                failure_stage=exc.failure_stage,
                debug_code=exc.debug_code,
                schema_version=self._schema_version,
            )
        result = _approved_summary_author_result(
            execution,
            schema_version=self._schema_version,
        )
        result["result_kind"] = "approved_ticket_authoring"
        result["ticket_ref"] = ticket_ref
        result["approved_summary_source"] = "local_approved_summary"
        return result

    def register_clean_ticket(self, arguments: Mapping[str, Any]) -> JsonDict:
        try:
            return _desktop_ticket_ref.register_clean_ticket_arguments(arguments)
        except ApprovedSummaryInputError as exc:
            debug_code = exc.debug_code
        except ContractValidationError:
            debug_code = "clean_ticket_text_invalid"
        return {
            "auto_publish_allowed": False,
            "debug_code": debug_code,
            "failure_stage": "input_validation",
            "network_calls": False,
            "ok": False,
            "pipeline_ok": False,
            "public_output_approved": False,
            "ready_for_real_ticket_use": False,
            "result_kind": "clean_ticket_registration",
            "schema_version": self._schema_version,
            "writes_files": False,
        }

    def draft_article(self, arguments: Mapping[str, Any]) -> JsonDict:
        try:
            primary_result = self._draft_article_primary_surface_result(
                arguments
            )
            result = (
                primary_result
                if primary_result is not None
                else _approved_summary_author_failure_result(
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
            result = _approved_summary_author_failure_result(
                failure_stage="input_validation",
                debug_code="draft_article_args_invalid",
                schema_version=self._schema_version,
            )
        result["result_kind"] = "draft_article_authoring"
        return result

    def support_get_behavior_instructions(
        self,
        arguments: Mapping[str, Any],
    ) -> JsonDict:
        _require_args(arguments, frozenset(), required=frozenset())
        return {
            "auto_publish_allowed": False,
            "network_calls": False,
            "ok": True,
            "public_output_approved": False,
            "result_kind": "behavior_instructions",
            "schema_version": self._schema_version,
            "should_be_kcs_article": True,
            "validation_ok": True,
            "writes_files": False,
        }

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
            return self._draft_article_from_primary_summary(arguments)
        if (
            has_ticket_ref
            and not has_summary
            and not has_selection_ref
            and not has_selected_item_ref
        ):
            return self._draft_article_from_primary_ticket_ref(arguments)
        if (
            has_selection_ref
            and has_selected_item_ref
            and not has_summary
            and not has_ticket_ref
        ):
            return self._draft_article_from_primary_selection(arguments)
        return _approved_summary_author_failure_result(
            failure_stage="input_validation",
            debug_code="draft_article_call_shape_invalid",
            schema_version=self._schema_version,
        )

    def _draft_article_from_primary_summary(
        self,
        arguments: Mapping[str, Any],
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
            return _approved_summary_author_failure_result(
                failure_stage="semantic_extraction",
                debug_code="semantic_extraction_no_candidates",
                schema_version=self._schema_version,
            )
        except (ContractValidationError, McpArgumentError, ValueError):
            return _approved_summary_author_failure_result(
                failure_stage="semantic_extraction",
                debug_code="semantic_extraction_output_invalid",
                schema_version=self._schema_version,
            )
        if not candidates:
            return _approved_summary_author_failure_result(
                failure_stage="semantic_extraction",
                debug_code="semantic_extraction_no_candidates",
                schema_version=self._schema_version,
            )
        if len(candidates) > 1:
            result = _desktop_draft_arguments.draft_article_split_required_result(
                {"item_candidates": candidates},
                schema_version=self._schema_version,
            )
            if result is None:  # pragma: no cover - defensive invariant
                return _approved_summary_author_failure_result(
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
        ticket_ref = _approved_ticket_ref_from_arguments(arguments)
        try:
            approved_arguments = _approved_ticket_author_arguments(arguments)
        except ApprovedSummaryPipelineStageError as exc:
            return _approved_ticket_author_failure_result(
                ticket_ref=ticket_ref,
                failure_stage="input_validation",
                debug_code=exc.debug_code,
                schema_version=self._schema_version,
            )
        if _desktop_draft_arguments.has_structured_approved_summary_item_input(
            approved_arguments
        ):
            result = self.author_ticket(arguments)
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
        result = self._draft_article_from_primary_summary(summary_arguments)
        result["approved_summary_source"] = "local_clean_ticket"
        result["ticket_ref"] = ticket_ref
        return result

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
        result = self.author_approved_summary(arguments)
        return finalize_author_result_with_bundle(
            result,
            bundle_root=self._reviewer_bundle_root,
            include_reviewer_only_html=arguments.get("debug") is True,
            schema_version=self._schema_version,
        )


def _execute_approved_summary_pipeline(
    arguments: Mapping[str, Any],
) -> Any:
    try:
        return _desktop_authoring_pipeline.execute_pipeline(arguments)
    except _desktop_authoring_pipeline.DesktopAuthoringArgumentError:
        raise McpArgumentError("Invalid approved summary arguments.") from None


def _approved_summary_pipeline_status(
    execution: Any,
    *,
    schema_version: str,
) -> JsonDict:
    return _desktop_authoring_pipeline.pipeline_status_result(
        execution,
        schema_version=schema_version,
    )


def _approved_summary_author_result(
    execution: Any,
    *,
    schema_version: str,
) -> JsonDict:
    return _desktop_authoring_pipeline.author_result(
        execution,
        schema_version=schema_version,
    )


def _approved_summary_author_failure_result(
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


def _approved_ticket_author_failure_result(
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


def _approved_ticket_author_arguments(arguments: Mapping[str, Any]) -> JsonDict:
    try:
        return _desktop_authoring_pipeline.ticket_author_arguments(arguments)
    except _desktop_authoring_pipeline.DesktopAuthoringArgumentError:
        raise McpArgumentError("Invalid approved ticket arguments.") from None


def _approved_ticket_ref_from_arguments(arguments: Mapping[str, Any]) -> str:
    return _desktop_authoring_pipeline.ticket_ref_from_arguments(arguments)


def _require_args(
    arguments: Mapping[str, Any],
    allowed: frozenset[str],
    *,
    required: frozenset[str],
) -> None:
    if any(key not in allowed for key in arguments):
        raise McpArgumentError("Unexpected tool argument.")
    if any(key not in arguments for key in required):
        raise McpArgumentError("Missing tool argument.")


__all__ = [
    "DesktopAuthoringTools",
]
