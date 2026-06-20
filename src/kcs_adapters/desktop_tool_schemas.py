"""Claude Desktop MCP tool input/output schema helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kcs_core.json_payload import JsonDict
from kcs_core.models import ArticleType


def approved_summary_input_schema() -> JsonDict:
    return object_schema(
        properties={
            "applicable_to": {"type": ["array", "string"]},
            "approved_summary_text": {"type": "string"},
            "article_type": {"type": "string"},
            "article_title": {"type": "string"},
            "auto_publish_allowed": {"type": "boolean"},
            "candidate_id": {"type": "string"},
            "case_ref": {"type": "string"},
            "cause": {"type": "string"},
            "commands": {"type": ["array", "string"]},
            "confirmed_facts": {"type": ["array", "string"]},
            "customer_replies": {"type": "boolean"},
            "debug": {
                "type": "boolean",
                "description": (
                    "Use true only for explicit debug or smoke compatibility. "
                    "Default Desktop draft results return compact status and "
                    "local bundle refs; debug may include bounded inline "
                    "reviewer-only Zendesk HTML."
                ),
            },
            "diagnosis": {"type": "string"},
            "environment": {"type": ["object", "string"]},
            "evidence": {"type": ["array", "string"]},
            "facts": {"type": ["array", "string"]},
            "fix": {"type": "string"},
            "item": {"type": "object"},
            "log_evidence": {"type": ["array", "string"]},
            "logs": {"type": ["array", "string"]},
            "notes": {"type": ["array", "string"]},
            "open_questions": {"type": ["array", "string"]},
            "problem": {"type": ["array", "string"]},
            "problem_statement": {"type": ["array", "string"]},
            "provider_calls": {"type": "boolean"},
            "public_output_approved": {"type": "boolean"},
            "publishes": {"type": "boolean"},
            "question": {"type": "string"},
            "ready_for_real_ticket_use": {"type": "boolean"},
            "reference_article": {"type": "string"},
            "reference_article_html": {"type": "string"},
            "reference_article_text": {"type": "string"},
            "reuse_search_checked": {"type": "boolean"},
            "reuse_search_run_ref": {"type": "string"},
            "resolution": {"type": "string"},
            "resolution_procedure": {"type": "string"},
            "root_cause": {"type": "string"},
            "root_cause_analysis": {"type": "string"},
            "resolution_steps": {"type": ["array", "string"]},
            "resolution_summary": {"type": "string"},
            "secondary_finding": {"type": ["array", "string"]},
            "secondary_findings": {"type": ["array", "string"]},
            "secondary_issue": {"type": ["array", "string"]},
            "secondary_issues": {"type": ["array", "string"]},
            "solution": {"type": "string"},
            "steps": {"type": ["array", "string"]},
            "supported_answer": {"type": "string"},
            "supported_cause": {"type": "string"},
            "supported_resolution_or_workaround": {"type": "string"},
            "symptom": {"type": "string"},
            "symptoms": {"type": ["array", "string"]},
            "title": {"type": "string"},
            "network_calls": {"type": "boolean"},
            "writes_files": {"type": "boolean"},
        },
        required=["approved_summary_text"],
    )


def approved_ticket_input_schema() -> JsonDict:
    return object_schema(
        properties={
            "auto_publish_allowed": {"type": "boolean"},
            "customer_replies": {"type": "boolean"},
            "debug": {"type": "boolean"},
            "network_calls": {"type": "boolean"},
            "provider_calls": {"type": "boolean"},
            "public_output_approved": {"type": "boolean"},
            "publishes": {"type": "boolean"},
            "ready_for_real_ticket_use": {"type": "boolean"},
            "reference_article": {"type": "string"},
            "reference_article_html": {"type": "string"},
            "reference_article_text": {"type": "string"},
            "ticket_ref": {"type": "string"},
            "writes_files": {"type": "boolean"},
        },
        required=["ticket_ref"],
    )


def register_clean_ticket_input_schema() -> JsonDict:
    return object_schema(
        properties={
            "clean_ticket_text": {
                "type": "string",
                "description": (
                    "Complete visible approved sanitized ticket transcript. "
                    "Do not summarize, condense, rewrite, redact labeled "
                    "sections, or omit visible symptoms, cause, resolution, "
                    "config paths, commands, services, platform facts, or other "
                    "sanitized evidence. Do not include tool-call XML, "
                    "parameter tags, or MCP argument markup inside this text."
                ),
            },
            "debug": {
                "type": "boolean",
                "description": "Use true only for explicit debug or smoke runs.",
            },
            "ticket_ref": {
                "type": "string",
                "description": (
                    "Optional opaque safe ref for the clean ticket file. Do not "
                    "pass filenames, absolute paths, Claude upload paths, or "
                    "arbitrary local paths."
                ),
            },
        },
        required=["clean_ticket_text"],
    )


def draft_article_input_schema() -> JsonDict:
    return object_schema(
        properties={
            "approved_summary_text": {
                "type": "string",
                "description": (
                    "Fallback for short inline sanitized support-ticket text "
                    "when clean-ticket registration is not needed. For "
                    "attachments, long pasted tickets, or any case where no "
                    "ticket_ref exists yet, call kcs_register_clean_ticket "
                    "first. If this field is used, pass the visible sanitized "
                    "text as-is. Do not summarize, condense, rewrite, redact "
                    "labeled sections, or omit symptoms, cause, resolution, "
                    "config paths, commands, services, platform facts, or other "
                    "visible evidence before calling the tool. Do not pass "
                    "uploaded filenames, local paths, or Claude upload paths."
                ),
            },
            "debug": {
                "type": "boolean",
                "description": (
                    "Use true only for explicit debug or smoke compatibility. "
                    "Default Desktop draft results return compact status and "
                    "local bundle refs; debug may include bounded inline "
                    "reviewer-only Zendesk HTML."
                ),
            },
            "operator_selected_item_ref": {
                "type": "string",
                "description": (
                    "Opaque item ref selected by the operator from a previous "
                    "split-required result."
                ),
            },
            "operator_selection_ref": {
                "type": "string",
                "description": (
                    "Opaque selection ref returned by a previous split-required "
                    "result."
                ),
            },
            "ticket_ref": {
                "type": "string",
                "description": (
                    "Opaque ref for a configured cleaned ticket transcript. "
                    "Use only refs prepared by a trusted source under "
                    "local-data/approved-summaries; do not pass filenames, "
                    "absolute paths, Claude upload paths, or arbitrary local "
                    "paths."
                ),
            },
        }
    )


def draft_article_item_schema() -> JsonDict:
    return object_schema(
        properties={
            "applicable_to": {
                "type": ["array", "string"],
                "description": (
                    "Applicable product/platform values, for example Plesk for "
                    "Linux or Plesk for Windows. Include release/version only "
                    "when the approved summary supports it."
                ),
            },
            "article_type": {
                "type": "string",
                "enum": [ArticleType.TECHNICAL_SCR.value, ArticleType.HOWTO_QA.value],
                "description": "Canonical article type only.",
            },
            "confirmed_facts": {
                "type": ["array", "string"],
                "description": "Confirmed facts from the approved sanitized summary.",
            },
            "environment": draft_article_environment_schema(),
            "resolution_steps": {
                "type": ["array", "string"],
                "description": (
                    "Executable reviewer-ready steps. Include concrete how-to "
                    "detail present in the summary: approved prerequisite links, "
                    "UI navigation, commands, paths, services, and verification. "
                    "Use safe backup or move-aside steps such as mv ... .bak "
                    "when cleanup is needed; do not pass rm -rf, delete, remove, "
                    "or destructive cleanup steps."
                ),
            },
            "supported_answer": {
                "type": "string",
                "description": "Required for howto_qa when applicable.",
            },
            "supported_cause": {
                "type": "string",
                "description": (
                    "Confirmed supported cause for technical_scr. Do not use "
                    "speculative wording such as likely, suspected, appears, "
                    "maybe, probably, unclear, or unknown."
                ),
            },
            "supported_resolution_or_workaround": {
                "type": "string",
                "description": "Supported resolution or workaround for technical_scr.",
            },
            "symptoms": {
                "type": ["array", "string"],
                "description": "Observed symptoms for technical_scr.",
            },
            "title": {"type": "string"},
        }
    )


def draft_article_item_candidate_schema() -> JsonDict:
    schema = draft_article_item_schema()
    schema["properties"] = {
        **schema["properties"],
        "item_ref": {"type": "string"},
        "reason": {
            "type": "string",
            "description": "Short reason why this is a separate semantic KCS item.",
        },
    }
    return schema


def draft_article_environment_schema() -> JsonDict:
    return object_schema(
        properties={
            "component": {"type": ["array", "string"]},
            "components": {"type": ["array", "string"]},
            "extension": {"type": "string"},
            "operating_system": {"type": "string"},
            "os": {"type": "string"},
            "platform": {"type": "string"},
            "product": {"type": "string"},
            "version": {"type": "string"},
        }
    )


def object_schema(
    *,
    properties: Mapping[str, object] | None = None,
    required: list[str] | None = None,
) -> JsonDict:
    return {
        "additionalProperties": False,
        "properties": dict(properties or {}),
        "required": list(required or []),
        "type": "object",
    }


def tool_output_schema() -> JsonDict:
    success = object_schema(
        properties={key: {"type": "object"} for key in _SUCCESS_OUTPUT_KEYS},
        required=["ok", "result_kind", "schema_version"],
    )
    success["properties"] = _SUCCESS_OUTPUT_PROPERTIES
    error = object_schema(
        properties={
            "error": {"type": "string"},
            "error_code": {"type": "string"},
            "ok": {"type": "boolean"},
        },
        required=["ok", "error", "error_code"],
    )
    return {"anyOf": [success, error]}


_SUCCESS_OUTPUT_PROPERTIES: JsonDict = {
    "auto_publish_allowed": {"type": "boolean"},
    "automatic_item_retry_allowed": {"type": "boolean"},
    "approved_summary_source": {"type": "string"},
    "article_type": {"type": "string"},
    "atomic_item": {"type": "object"},
    "blockers": {"type": "array"},
    "bundle_ref": {"type": "string"},
    "bundle_storage_hint": {"type": "string"},
    "bundle_storage_ref": {"type": "string"},
    "byte_length": {"type": "integer"},
    "case_ref": {"type": "string"},
    "checks": {"type": "array"},
    "clean_ticket_sha256": {"type": "string"},
    "clean_ticket_store_ref": {"type": "string"},
    "clean_ticket_storage_hint": {"type": "string"},
    "clean_ticket_storage_ref": {"type": "string"},
    "customer_replies": {"type": "boolean"},
    "debug_code": {"type": "string"},
    "draft_ref": {"type": "string"},
    "draft_generated": {"type": "boolean"},
    "draft_request_ready": {"type": "boolean"},
    "draft_sections": {"type": "object"},
    "evidence_valid": {"type": "boolean"},
    "draft_status": {"type": "string"},
    "failure_stage": {"type": "string"},
    "handoff_ref": {"type": "string"},
    "html_path": {"type": "string"},
    "html_sha256": {"type": "string"},
    "input_safety_ok": {"type": "boolean"},
    "item_candidates": {"type": "array"},
    "item_ref": {"type": "string"},
    "kcs_ready": {"type": "boolean"},
    "manual_draft_allowed": {"type": "boolean"},
    "manifest_path": {"type": "string"},
    "network_calls": {"type": "boolean"},
    "next_arguments": {"type": "object"},
    "next_required_action": {"type": "string"},
    "next_tool": {"type": "string"},
    "next_tool_name": {"type": "string"},
    "ok": {"type": "boolean"},
    "open_questions": {"type": "array"},
    "operator_choice_options": {"type": "array"},
    "operator_choice_confirmed": {"type": "boolean"},
    "operator_choice_request": {"type": "object"},
    "operator_prompt": {"type": "string"},
    "operator_prompt_style": {"type": "string"},
    "operator_selected_item_ref": {"type": "string"},
    "operator_selection_ref": {"type": "string"},
    "original_article_type": {"type": "string"},
    "original_decision_status": {"type": "string"},
    "original_readiness_state": {"type": "string"},
    "original_recommended_action": {"type": "string"},
    "prompts_exposed": {"type": "boolean"},
    "protocol_version": {"type": "string"},
    "provider_calls": {"type": "boolean"},
    "provider_error_code": {"type": "string"},
    "provider_status": {"type": "string"},
    "public_output_approved": {"type": "boolean"},
    "publishes": {"type": "boolean"},
    "pipeline_ok": {"type": "boolean"},
    "quality_gaps": {"type": "array"},
    "recommended_action": {"type": "string"},
    "ready_for_reviewer": {"type": "boolean"},
    "ready_for_real_ticket_use": {"type": "boolean"},
    "request_schema_version": {"type": "string"},
    "request_sha256": {"type": "string"},
    "resources_exposed": {"type": "boolean"},
    "response_schema_version": {"type": "string"},
    "response_sha256": {"type": "string"},
    "result_kind": {"type": "string"},
    "review_summary": {"type": "object"},
    "reviewer_only_html": {"type": "string"},
    "reviewer_only_draft": {"type": "object"},
    "reviewer_only_preview": {"type": "object"},
    "reviewer_only_preview_text": {"type": "string"},
    "reviewer_bundle_written": {"type": "boolean"},
    "reuse_search_run_ref": {"type": "string"},
    "reuse_search_status": {"type": "string"},
    "schema_version": {"type": "string"},
    "server_name": {"type": "string"},
    "server_version": {"type": "string"},
    "should_be_kcs_article": {"type": "boolean"},
    "semantic_review_ref": {"type": "string"},
    "smoke_ok": {"type": "boolean"},
    "tool_count": {"type": "integer"},
    "tools": {"type": "array"},
    "ticket_ref": {"type": "string"},
    "validation_ok": {"type": "boolean"},
    "workflow_state": {"type": "string"},
    "writes_files": {"type": "boolean"},
}
_SUCCESS_OUTPUT_KEYS = frozenset(_SUCCESS_OUTPUT_PROPERTIES)


def desktop_input_schema(input_schema: Mapping[str, Any]) -> JsonDict:
    schema = safe_desktop_schema_fragment(input_schema)
    if not isinstance(schema, dict) or schema.get("type") != "object":
        return object_schema()
    return schema


def safe_desktop_schema_fragment(schema: object) -> JsonDict:
    if not isinstance(schema, Mapping):
        return {"type": "object"}

    result: JsonDict = {"type": _safe_schema_type(schema.get("type", "object"))}
    _copy_safe_schema_metadata(schema, result)
    _copy_safe_schema_children(schema, result)
    return result


def _safe_schema_type(value: object) -> object:
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    return "object"


def _copy_safe_schema_metadata(schema: Mapping[str, Any], result: JsonDict) -> None:
    description = schema.get("description")
    if isinstance(description, str):
        result["description"] = description[:500]

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and all(
        isinstance(item, str) for item in enum_values
    ):
        result["enum"] = list(enum_values)

    max_length = schema.get("maxLength")
    if isinstance(max_length, int):
        result["maxLength"] = max_length

    additional_properties = schema.get("additionalProperties")
    if isinstance(additional_properties, bool):
        result["additionalProperties"] = additional_properties

    required = schema.get("required")
    if isinstance(required, list) and all(isinstance(item, str) for item in required):
        result["required"] = list(required)


def _copy_safe_schema_children(schema: Mapping[str, Any], result: JsonDict) -> None:
    properties = schema.get("properties")
    if isinstance(properties, Mapping):
        result["properties"] = {
            name: safe_desktop_schema_fragment(value)
            for name, value in properties.items()
            if isinstance(name, str)
        }

    items = schema.get("items")
    if isinstance(items, Mapping):
        result["items"] = safe_desktop_schema_fragment(items)


__all__ = [
    "approved_summary_input_schema",
    "approved_ticket_input_schema",
    "desktop_input_schema",
    "draft_article_environment_schema",
    "draft_article_input_schema",
    "draft_article_item_candidate_schema",
    "draft_article_item_schema",
    "object_schema",
    "register_clean_ticket_input_schema",
    "safe_desktop_schema_fragment",
    "tool_output_schema",
]
