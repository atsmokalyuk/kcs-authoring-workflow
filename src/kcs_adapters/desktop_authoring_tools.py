"""Desktop authoring tool handlers for the MCP adapter."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from kcs_adapters import desktop_authoring_pipeline as _desktop_authoring_pipeline
from kcs_adapters import desktop_draft_tool as _desktop_draft_tool
from kcs_adapters import desktop_payload as _desktop_payload
from kcs_adapters import desktop_reuse_comparison as _desktop_reuse_comparison
from kcs_adapters import desktop_ticket_ref as _desktop_ticket_ref
from kcs_adapters import desktop_workflow_results as _desktop_workflow_results
from kcs_adapters.desktop_stdio_transport import McpArgumentError
from kcs_adapters.desktop_workflow import (
    ApprovedSummaryPipelineStageError,
    DesktopDraftWorkflow,
    ReuseComparisonExpiredError,
    ReuseComparisonInvalidError,
    ReuseComparisonUnavailableError,
    SemanticReviewBoundaryAmbiguousError,
    SemanticReviewExpiredError,
    SemanticReviewInvalidError,
    SemanticReviewSubmissionInvalidError,
    SemanticReviewUnavailableError,
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
        self._schema_version = schema_version
        self._draft_workflow = draft_workflow
        self._draft_article_tool = _desktop_draft_tool.DesktopDraftArticleTool(
            draft_workflow=draft_workflow,
            reviewer_bundle_root=reviewer_bundle_root,
            schema_version=schema_version,
            author_approved_summary=self.author_approved_summary,
            author_ticket=self.author_ticket,
        )

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
        self._draft_workflow.clear_pending_semantic_review()
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
        return self._draft_article_tool.draft_article(arguments)

    def draft_ticket(self, arguments: Mapping[str, Any]) -> JsonDict:
        try:
            _require_args(
                arguments,
                frozenset({"debug", "ticket_ref"}),
                required=frozenset({"ticket_ref"}),
            )
        except McpArgumentError:
            return {
                "auto_publish_allowed": False,
                "debug_code": "draft_article_args_invalid",
                "draft_generated": False,
                "failure_stage": "input_validation",
                "manual_draft_allowed": False,
                "network_calls": False,
                "ok": False,
                "pipeline_ok": False,
                "public_output_approved": False,
                "ready_for_real_ticket_use": False,
                "result_kind": "draft_article_authoring",
                "reviewer_bundle_written": False,
                "schema_version": self._schema_version,
                "validation_ok": False,
                "writes_files": False,
            }
        draft_arguments = {"ticket_ref": arguments["ticket_ref"]}
        if "debug" in arguments:
            draft_arguments["debug"] = arguments["debug"]
        return self._draft_article_tool.draft_article(draft_arguments)

    def prepare_ticket_reuse_comparison(
        self,
        arguments: Mapping[str, Any],
    ) -> JsonDict:
        """Start ticket comparison without exposing an authoring-capable path."""

        try:
            _require_args(
                arguments,
                frozenset({"ticket_ref"}),
                required=frozenset({"ticket_ref"}),
            )
        except McpArgumentError:
            return {
                "auto_publish_allowed": False,
                "debug_code": "draft_article_args_invalid",
                "draft_generated": False,
                "failure_stage": "input_validation",
                "manual_draft_allowed": False,
                "network_calls": False,
                "ok": False,
                "pipeline_ok": False,
                "public_output_approved": False,
                "ready_for_real_ticket_use": False,
                "result_kind": "draft_article_authoring",
                "reviewer_bundle_written": False,
                "schema_version": self._schema_version,
                "validation_ok": False,
                "writes_files": False,
            }
        return self._draft_article_tool.prepare_ticket_reuse_comparison(arguments)

    def confirm_reuse_comparison(
        self,
        arguments: Mapping[str, Any],
    ) -> JsonDict:
        try:
            _require_args(
                arguments,
                frozenset({"candidate_ref", "comparison_ref", "outcome"}),
                required=frozenset({"comparison_ref", "outcome"}),
            )
            return self._draft_article_tool.confirm_reuse_comparison(arguments)
        except ReuseComparisonExpiredError:
            debug_code = "reuse_comparison_expired"
        except ReuseComparisonUnavailableError:
            debug_code = "reuse_comparison_unavailable"
        except ReuseComparisonInvalidError:
            debug_code = "reuse_comparison_invalid"
        except McpArgumentError:
            self._draft_workflow.clear_pending_reuse_comparison()
            debug_code = "reuse_comparison_invalid"
        return _desktop_reuse_comparison.reuse_comparison_submit_failure_result(
            debug_code=debug_code,
            schema_version=self._schema_version,
        )

    def prepare_semantic_review(self, arguments: Mapping[str, Any]) -> JsonDict:
        try:
            _require_args(
                arguments,
                frozenset({"semantic_review_ref"}),
                required=frozenset({"semantic_review_ref"}),
            )
            return self._draft_article_tool.prepare_semantic_review(arguments)
        except SemanticReviewExpiredError:
            debug_code = "semantic_review_expired"
        except SemanticReviewUnavailableError:
            debug_code = "semantic_review_unavailable"
        except SemanticReviewInvalidError:
            debug_code = "semantic_review_invalid"
        except McpArgumentError:
            debug_code = "semantic_review_invalid"
        return _desktop_workflow_results.semantic_review_prepare_failure_result(
            debug_code=debug_code,
            schema_version=self._schema_version,
        )

    def submit_semantic_review(self, arguments: Mapping[str, Any]) -> JsonDict:
        correction: JsonDict | None = None
        terminal_cause_debug_code: str | None = None
        try:
            _require_semantic_submit_args(arguments)
            return self._draft_article_tool.submit_semantic_review(arguments)
        except SemanticReviewBoundaryAmbiguousError as exc:
            return _desktop_workflow_results.semantic_review_boundary_terminal_result(
                projected=exc.projected,
                schema_version=self._schema_version,
            )
        except SemanticReviewExpiredError:
            debug_code = "semantic_review_expired"
        except SemanticReviewUnavailableError:
            debug_code = "semantic_review_unavailable"
        except SemanticReviewInvalidError:
            debug_code = "semantic_review_invalid"
        except SemanticReviewSubmissionInvalidError as exc:
            correction = exc.correction
            debug_code = exc.debug_code
            terminal_cause_debug_code = exc.terminal_cause_debug_code
        except (ContractValidationError, McpArgumentError) as exc:
            _terminalize_invalid_semantic_submit_shape(
                self._draft_workflow,
                exc,
            )
            debug_code = "semantic_review_submission_invalid"
        return _desktop_workflow_results.semantic_review_submit_failure_result(
            correction=correction,
            debug_code=debug_code,
            schema_version=self._schema_version,
            terminal_cause_debug_code=terminal_cause_debug_code,
        )

    def support_get_behavior_instructions(
        self,
        arguments: Mapping[str, Any],
    ) -> JsonDict:
        _require_args(arguments, frozenset(), required=frozenset())
        return {
            "auto_publish_allowed": False,
            "manual_draft_allowed": False,
            "network_calls": False,
            "next_required_action": "continue_kcs_authoring_workflow",
            "ok": True,
            "public_output_approved": False,
            "result_kind": "behavior_instructions",
            "schema_version": self._schema_version,
            "should_be_kcs_article": True,
            "validation_ok": True,
            "writes_files": False,
        }


def _require_semantic_submit_args(arguments: Mapping[str, Any]) -> None:
    _require_args(
        arguments,
        frozenset({"semantic_issue_proposal", "semantic_review_ref"}),
        required=frozenset({"semantic_issue_proposal", "semantic_review_ref"}),
    )


def _terminalize_invalid_semantic_submit_shape(
    draft_workflow: DesktopDraftWorkflow,
    error: Exception,
) -> None:
    if isinstance(error, McpArgumentError):
        draft_workflow.clear_pending_semantic_review()


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
