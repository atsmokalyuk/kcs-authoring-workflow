"""MCP tool descriptor builders for the KCS Desktop adapter."""

from __future__ import annotations

from dataclasses import dataclass

from kcs_adapters import desktop_tool_schemas as _desktop_tool_schemas
from kcs_adapters.desktop_protocol import SEMANTIC_CONTROL_GUIDANCE
from kcs_adapters.desktop_tool_names import (
    TOOL_AUTHOR_APPROVED_SUMMARY,
    TOOL_AUTHOR_TICKET,
    TOOL_CONFIRM_REUSE_COMPARISON,
    TOOL_DRAFT_ARTICLE,
    TOOL_DRAFT_TICKET,
    TOOL_GET_MCP_READINESS,
    TOOL_GET_POLICY_SUMMARY,
    TOOL_PREPARE_SEMANTIC_REVIEW,
    TOOL_REGISTER_CLEAN_TICKET,
    TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
    TOOL_RUN_CONTRACT_SMOKE,
    TOOL_SUBMIT_SEMANTIC_REVIEW,
    TOOL_SUPPORT_GET_BEHAVIOR_INSTRUCTIONS,
    TOOL_VALIDATE_DRAFT_REQUEST,
    TOOL_VALIDATE_DRAFT_RESPONSE,
    TOOL_VALIDATE_HANDOFF_REQUEST,
    TOOL_VALIDATE_HANDOFF_RESPONSE,
)
from kcs_core.json_payload import JsonDict


@dataclass(frozen=True)
class McpToolDescriptor:
    """MCP-compatible tool descriptor subset."""

    name: str
    description: str
    input_schema: JsonDict
    output_schema: JsonDict
    annotations: JsonDict


def tool_descriptors() -> tuple[McpToolDescriptor, ...]:
    return (
        _draft_ticket_descriptor(),
        _register_clean_ticket_descriptor(),
        _draft_article_descriptor(),
        _confirm_reuse_comparison_descriptor(),
        _prepare_semantic_review_descriptor(),
        _submit_semantic_review_descriptor(),
        _support_get_behavior_instructions_descriptor(),
        _policy_summary_descriptor(),
        _readiness_descriptor(),
        _validate_handoff_request_descriptor(),
        _validate_handoff_response_descriptor(),
        _validate_draft_request_descriptor(),
        _validate_draft_response_descriptor(),
        _contract_smoke_descriptor(),
        _approved_summary_pipeline_descriptor(),
        _author_approved_summary_descriptor(),
        _author_ticket_descriptor(),
    )


def _policy_summary_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_GET_POLICY_SUMMARY,
        description="Return KCS Desktop MCP safety and scope metadata.",
        input_schema=_desktop_tool_schemas.object_schema(),
    )


def _readiness_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_GET_MCP_READINESS,
        description="Return KCS Desktop MCP readiness metadata and visible tools.",
        input_schema=_desktop_tool_schemas.object_schema(),
    )


def _validate_handoff_request_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_VALIDATE_HANDOFF_REQUEST,
        description="Validate one KCS-9b handoff request packet.",
        input_schema=_desktop_tool_schemas.object_schema(
            properties={"request": {"type": "object"}},
            required=["request"],
        ),
    )


def _validate_handoff_response_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_VALIDATE_HANDOFF_RESPONSE,
        description="Validate one KCS-9b handoff response against its request.",
        input_schema=_desktop_tool_schemas.object_schema(
            properties={"request": {"type": "object"}, "response": {"type": "object"}},
            required=["request", "response"],
        ),
    )


def _validate_draft_request_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_VALIDATE_DRAFT_REQUEST,
        description="Validate one KCS-9c draft request packet.",
        input_schema=_desktop_tool_schemas.object_schema(
            properties={"request": {"type": "object"}},
            required=["request"],
        ),
    )


def _validate_draft_response_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_VALIDATE_DRAFT_RESPONSE,
        description="Validate one KCS-9c draft response against its request.",
        input_schema=_desktop_tool_schemas.object_schema(
            properties={"request": {"type": "object"}, "response": {"type": "object"}},
            required=["request", "response"],
        ),
    )


def _contract_smoke_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_RUN_CONTRACT_SMOKE,
        description="Run an in-memory synthetic KCS-9b/KCS-9c validation smoke.",
        input_schema=_desktop_tool_schemas.object_schema(),
    )


def _approved_summary_pipeline_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_RUN_APPROVED_SUMMARY_PIPELINE,
        description=(
            "Run the local KCS pipeline for one approved sanitized summary. "
            "Provide approved_summary_text. Optional structured item fields can "
            "be passed either as item or top-level fields; common aliases like "
            "problem, diagnosis, solution, commands, and secondary_finding are "
            "accepted. Explicit supported cause/resolution evidence is required "
            "before evidence-ready status. This MVP does not perform live reuse "
            "search; if reuse_search_checked is not provided, reuse search is "
            "marked skipped and drafting may continue. Set debug=true to receive "
            "value-safe failure_stage and debug_code. The tool returns compact "
            "status only."
        ),
        input_schema=_desktop_tool_schemas.approved_summary_input_schema(),
    )


def _author_approved_summary_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_AUTHOR_APPROVED_SUMMARY,
        description=(
            "Author a reviewer-only KCS draft/status packet from one approved "
            "sanitized support summary. Requires explicit supported cause or "
            "answer evidence, explicit supported resolution or answer evidence, "
            "and a single atomic item. This MVP marks reuse search skipped when "
            "reuse_search_checked is not provided. Returns compact reviewer-only "
            "draft sections, reviewer_only_html for copy/paste, and deterministic "
            "quality-gap status; does not publish, write files, call a provider, "
            "or return full packet bodies."
        ),
        input_schema=_desktop_tool_schemas.approved_summary_input_schema(),
    )


def _author_ticket_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_AUTHOR_TICKET,
        description=(
            "Author a reviewer-only KCS draft/status packet from one local "
            "approved sanitized ticket summary reference. Provide ticket_ref. "
            "The tool reads only configured approved summary files, "
            "returns reviewer_only_html for copy/paste, does not read Zendesk, "
            "and does not publish, write files, call a provider, or return raw "
            "packet bodies."
        ),
        input_schema=_desktop_tool_schemas.approved_ticket_input_schema(),
    )


def _register_clean_ticket_descriptor() -> McpToolDescriptor:
    descriptor = _descriptor(
        name=TOOL_REGISTER_CLEAN_TICKET,
        description=(
            "Use only when sanitized ticket text is visible and no ticket_ref "
            "exists. Stores clean_ticket_text and returns next_arguments."
        ),
        input_schema=_desktop_tool_schemas.register_clean_ticket_input_schema(),
    )
    descriptor.annotations["idempotentHint"] = False
    descriptor.annotations["readOnlyHint"] = False
    return descriptor


def _draft_article_descriptor() -> McpToolDescriptor:
    descriptor = _descriptor(
        name=TOOL_DRAFT_ARTICLE,
        description=(
            "Use only for short approved_summary_text, one operator-selected "
            "candidate, or one ordered operator-selected candidate batch. "
            "Operator-confirmed resolution steps are accepted only for a "
            "singular candidate already returned as retryable. For `/draft "
            "<ticket_ref>`, use kcs_draft_ticket."
        ),
        input_schema=_desktop_tool_schemas.draft_article_input_schema(),
    )
    descriptor.annotations["idempotentHint"] = False
    descriptor.annotations["readOnlyHint"] = False
    return descriptor


def _draft_ticket_descriptor() -> McpToolDescriptor:
    descriptor = _descriptor(
        name=TOOL_DRAFT_TICKET,
        description=(
            "Use immediately for `/draft <ticket_ref>`. Call with only "
            "ticket_ref and optional debug. Copy the ref exactly, including "
            "any `ticket-` prefix; do not normalize or strip it. Do not ask "
            "for an attachment."
        ),
        input_schema=_desktop_tool_schemas.draft_ticket_input_schema(),
    )
    descriptor.annotations["idempotentHint"] = False
    descriptor.annotations["readOnlyHint"] = False
    return descriptor


def _confirm_reuse_comparison_descriptor() -> McpToolDescriptor:
    descriptor = _descriptor(
        name=TOOL_CONFIRM_REUSE_COMPARISON,
        description=(
            "Submit only the operator-confirmed outcome for the pending public "
            "article comparison. Copy comparison_ref exactly. For reuse or "
            "update also copy one displayed candidate_ref. Do not include "
            "ticket facts, excerpts, URLs, recommendations, or free-form text."
        ),
        input_schema=(
            _desktop_tool_schemas.confirm_reuse_comparison_input_schema()
        ),
    )
    descriptor.annotations["idempotentHint"] = False
    descriptor.annotations["readOnlyHint"] = False
    return descriptor


def _prepare_semantic_review_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_PREPARE_SEMANTIC_REVIEW,
        description=(
            "Call only after semantic_review_required. Returns bounded "
            "excerpts and submit instructions for item identification. "
            "If several separately searchable issues are visible, submit all "
            "candidate items; Python handles operator selection."
        ),
        input_schema=_desktop_tool_schemas.prepare_semantic_review_input_schema(),
    )


def _submit_semantic_review_descriptor() -> McpToolDescriptor:
    descriptor = _descriptor(
        name=TOOL_SUBMIT_SEMANTIC_REVIEW,
        description=(
            "Submit semantic_issue_proposal_v1 from the prepared packet. "
            "Propose all separately searchable issue boundaries and explicit "
            "coverage records visible in the packet. Do not choose operator or "
            "KCS actions. No article draft, HTML, legacy candidate fields, item, "
            "item_candidates, or raw ticket text. "
            f"{SEMANTIC_CONTROL_GUIDANCE}"
        ),
        input_schema=_desktop_tool_schemas.submit_semantic_review_input_schema(),
    )
    descriptor.annotations["idempotentHint"] = False
    descriptor.annotations["readOnlyHint"] = False
    return descriptor


def _support_get_behavior_instructions_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_SUPPORT_GET_BEHAVIOR_INSTRUCTIONS,
        description=(
            "Legacy compatibility helper. If called, use the returned route "
            "and immediately continue /draft with kcs_draft_ticket or the "
            "returned next tool. Do not report this helper as unavailable."
        ),
        input_schema=_desktop_tool_schemas.object_schema(),
    )


def _descriptor(
    *,
    name: str,
    description: str,
    input_schema: JsonDict,
) -> McpToolDescriptor:
    return McpToolDescriptor(
        name=name,
        description=description,
        input_schema=input_schema,
        output_schema=_desktop_tool_schemas.tool_output_schema(),
        annotations={
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
            "readOnlyHint": True,
        },
    )


__all__ = [
    "McpToolDescriptor",
    "tool_descriptors",
]
