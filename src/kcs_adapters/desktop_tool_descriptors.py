"""MCP tool descriptor builders for the KCS Desktop adapter."""

from __future__ import annotations

from dataclasses import dataclass

from kcs_adapters import desktop_tool_schemas as _desktop_tool_schemas
from kcs_adapters.desktop_tool_names import (
    TOOL_AUTHOR_APPROVED_SUMMARY,
    TOOL_AUTHOR_TICKET,
    TOOL_DRAFT_ARTICLE,
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
        _register_clean_ticket_descriptor(),
        _draft_article_descriptor(),
        _prepare_semantic_review_descriptor(),
        _submit_semantic_review_descriptor(),
        _support_get_behavior_instructions_descriptor(),
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
            "Register one approved sanitized support-ticket transcript as a "
            "configured clean ticket file. Use this when Claude Desktop "
            "receives a draft-article request with an operator-provided "
            "sanitized attachment or long paste and no ticket_ref yet. This is "
            "the automatic first step for attachment-based drafting. Pass the "
            "complete visible sanitized transcript, even when long, in "
            "clean_ticket_text and optionally an opaque ticket_ref; do not pass "
            "uploaded filenames, "
            "local paths, Claude upload paths, item, item_candidates, aliases, "
            "or reference article bodies. A Claude Desktop file card is not a "
            "filesystem path: do not inspect upload directories, and use the "
            "visible file text as clean_ticket_text. The tool writes "
            "clean.ticket.txt under the configured approved-summaries store "
            "and returns exact next_arguments for kcs_draft_article."
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
            "Primary KCS authoring tool for sanitized support-ticket article "
            "requests. Prefer ticket_ref when the cleaned ticket transcript "
            "has been saved by a trusted source under the configured "
            "approved-summaries store. For an operator-provided sanitized "
            "attachment or long paste with no ticket_ref, call "
            "kcs_register_clean_ticket first and then call this tool with the "
            "returned next_arguments. Use approved_summary_text only as a "
            "fallback for short inline sanitized text when clean-ticket "
            "registration is not needed. Do not summarize, redact labeled "
            "sections, or pass upload filenames, paths, item, item_candidates, "
            "aliases, or reference article bodies. A Claude Desktop file card "
            "is not a filesystem path; do not inspect upload directories or "
            "ask the operator to re-upload while visible file text is "
            "available. If no visible file text is available, report "
            "file_content_unavailable and do not draft manually. "
            "Python validates the input and owns semantic extraction, decision, "
            "rendering, and local bundle output. Successful results return "
            "compact status plus local reviewer bundle refs; reviewer-only "
            "Zendesk HTML is written to the local bundle and returned inline "
            "only when debug=true is used for explicit smoke/debug "
            "compatibility. If split_required is returned, call again with "
            "only operator_selection_ref and operator_selected_item_ref."
        ),
        input_schema=_desktop_tool_schemas.draft_article_input_schema(),
    )
    descriptor.annotations["idempotentHint"] = False
    descriptor.annotations["readOnlyHint"] = False
    return descriptor


def _prepare_semantic_review_descriptor() -> McpToolDescriptor:
    return _descriptor(
        name=TOOL_PREPARE_SEMANTIC_REVIEW,
        description=(
            "Return a bounded Claude-visible semantic-review packet for one "
            "pending clean-ticket semantic review. Call this only with the "
            "semantic_review_ref returned by kcs_draft_article. The packet "
            "contains selected excerpts only, not the full ticket. Use it to "
            "identify atomic KCS item candidates in candidate_semantic_extraction_v1 "
            "format only. Do not draft an article, choose a KCS action, return "
            "HTML, or submit item/item_candidates payloads through "
            "kcs_draft_article."
        ),
        input_schema=_desktop_tool_schemas.prepare_semantic_review_input_schema(),
    )


def _submit_semantic_review_descriptor() -> McpToolDescriptor:
    descriptor = _descriptor(
        name=TOOL_SUBMIT_SEMANTIC_REVIEW,
        description=(
            "Submit Claude-proposed semantic item identification for a prepared "
            "semantic review. Accepts only candidate_semantic_extraction_v1 "
            "grounded in the selected_excerpts source refs returned by "
            "kcs_prepare_semantic_review. Do not submit article drafts, HTML, "
            "recommended_action, item, item_candidates, raw ticket text, local "
            "paths, or publication flags. Python validates the extraction, then "
            "continues the normal draft or split-required pipeline."
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
            "Compatibility helper for legacy Plesk Support behavior-instruction "
            "requests. Returns the minimal KCS Authoring route: use "
            "kcs_draft_article for sanitized ticket article drafting."
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
