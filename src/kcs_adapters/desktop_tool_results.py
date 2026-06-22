"""Claude Desktop MCP tool-result formatting and output-boundary checks."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict, require_json_object
from kcs_core.sanitizer import ensure_safe_sanitized_payload

MAX_TOOL_RESULT_BYTES = 256 * 1024

_RESULT_FORBIDDEN_FRAGMENTS = (
    "article_body",
    "attachment_url",
    "audio",
    "draft_artifact",
    "embedded_resource",
    "evidence_basis",
    "file://",
    "image",
    "internal_comment",
    "local_path",
    "raw_comment",
    "raw_ticket",
    "raw_validation_payload",
    "redaction_map",
    "resource_link",
    "reviewer_packet",
    "reviewer_only_draft_artifact",
    "zendesk_source_html",
)
_RESULT_FORBIDDEN_COMPACT_FRAGMENTS = (
    "articlebody",
    "attachmenturl",
    "draftartifact",
    "embeddedresource",
    "localpath",
    "rawvalidationpayload",
    "resourcelink",
    "revieweronlydraftartifact",
    "zendesksourcehtml",
)
_RESULT_FORBIDDEN_EXACT_KEYS = frozenset({"resource"})
_TOOL_RESULT_HTML_FIELDS = frozenset({"reviewer_only_html"})
_APPROVED_HTML_URL_REFS = {
    "https://support.plesk.com/hc/en-us/articles/"
    "12377512781975-How-to-connect-to-a-Plesk-server-via-SSH": "approved-ssh-kb-ref",
    (
        "https://support.plesk.com/hc/en-us/articles/"
        "12377247797271-How-to-connect-to-a-Plesk-server-via-RDP-with-available-"
        "credentials"
    ): "approved-rdp-kb-ref",
}
_HTML_URL_RE = re.compile(r"https?://[^\"'\\s<>]+", re.I)
_FORBIDDEN_TEXT_HTML_TAG_RE = re.compile(
    r"</\s*[a-z][a-z0-9:-]*\b|<\s*(?:a|br|div|h1|h2|h3|li|ol|p|pre|ul)\b",
    re.I,
)
_SAFE_LOCAL_REF_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,120}")
_TOOL_RESULT_LOCAL_REF_FIELDS = frozenset({"case_ref", "ticket_ref"})


def tool_result_content(structured: Mapping[str, Any]) -> list[JsonDict]:
    return [{"text": tool_result_text(structured), "type": "text"}]


def tool_result_text(structured: Mapping[str, Any]) -> str:
    pre_draft_text = _pre_draft_tool_result_text(structured)
    if pre_draft_text is not None:
        return pre_draft_text
    debug_text = _debug_tool_result_text(structured)
    if debug_text is not None:
        return debug_text
    html = structured.get("reviewer_only_html")
    if (
        isinstance(html, str)
        and html
        and structured.get("result_kind")
        in {
            "approved_summary_authoring",
            "approved_ticket_authoring",
            "draft_article_authoring",
        }
    ):
        status = {
            "article_type": structured.get("article_type"),
            "auto_publish_allowed": structured.get("auto_publish_allowed"),
            "case_ref": structured.get("case_ref"),
            "debug_code": structured.get("debug_code"),
            "draft_request_ready": structured.get("draft_request_ready"),
            "draft_generated": structured.get("draft_generated"),
            "existing_article_review": structured.get("existing_article_review"),
            "failure_stage": structured.get("failure_stage"),
            "html_path": structured.get("html_path"),
            "html_sha256": structured.get("html_sha256"),
            "bundle_storage_hint": structured.get("bundle_storage_hint"),
            "bundle_storage_ref": structured.get("bundle_storage_ref"),
            "item_ref": structured.get("item_ref"),
            "kcs_ready": structured.get("kcs_ready"),
            "manifest_path": structured.get("manifest_path"),
            "ok": structured.get("ok"),
            "pipeline_ok": structured.get("pipeline_ok"),
            "public_output_approved": structured.get("public_output_approved"),
            "ready_for_reviewer": structured.get("ready_for_reviewer"),
            "recommended_action": structured.get("recommended_action"),
            "result_kind": structured.get("result_kind"),
            "reuse_search_status": structured.get("reuse_search_status"),
            "reviewer_bundle_written": structured.get("reviewer_bundle_written"),
            "selected_reuse_match": structured.get("selected_reuse_match"),
            "validation_ok": structured.get("validation_ok"),
        }
        return (
            "```html\n"
            f"{html}\n"
            "```\n\n"
            "```json\n"
            f"{_compact_json(status)}\n"
            "```"
        )
    if (
        structured.get("result_kind") == "draft_article_authoring"
        and structured.get("draft_generated") is True
        and isinstance(structured.get("html_path"), str)
    ):
        status = {
            "article_type": structured.get("article_type"),
            "auto_publish_allowed": structured.get("auto_publish_allowed"),
            "debug_code": structured.get("debug_code"),
            "draft_generated": structured.get("draft_generated"),
            "existing_article_review": structured.get("existing_article_review"),
            "html_path": structured.get("html_path"),
            "bundle_storage_hint": structured.get("bundle_storage_hint"),
            "bundle_storage_ref": structured.get("bundle_storage_ref"),
            "item_ref": structured.get("item_ref"),
            "kcs_ready": structured.get("kcs_ready"),
            "manifest_path": structured.get("manifest_path"),
            "public_output_approved": structured.get("public_output_approved"),
            "ready_for_reviewer": structured.get("ready_for_reviewer"),
            "recommended_action": structured.get("recommended_action"),
            "reuse_search_status": structured.get("reuse_search_status"),
            "reviewer_bundle_written": structured.get("reviewer_bundle_written"),
            "selected_reuse_match": structured.get("selected_reuse_match"),
        }
        if structured.get("existing_article_review"):
            return (
                "Reviewer-only KCS existing-article review bundle generated by "
                "the KCS Authoring tool. This is not a duplicate new article: "
                "use existing_article_review to update or flag the matched "
                "article. Zendesk HTML is saved on the operator's local machine "
                "in the reviewer bundle at html_path.\n\n"
                "Compact status:\n"
                "```json\n"
                f"{_compact_json(status)}\n"
                "```"
            )
        return (
            "Reviewer-only KCS draft generated by the KCS Authoring tool. "
            "Zendesk HTML is saved on the operator's local machine in the "
            "reviewer bundle at html_path. When bundle_storage_hint is present, "
            "resolve html_path under that directory. Report the returned local "
            "bundle location and status only; do not claim the file is "
            "unavailable from this chat, do not inspect upload/sandbox paths, "
            "and do not offer a separate chat-authored article.\n\n"
            "Compact status:\n"
            "```json\n"
            f"{_compact_json(status)}\n"
            "```"
        )
    if (
        structured.get("recommended_action") == "split_required"
        and isinstance(structured.get("operator_choice_request"), Mapping)
    ):
        return _split_required_tool_result_text(structured)
    return _compact_json(structured)


def desktop_structured_content(
    *,
    draft_tool_name: str,
    descriptor_name: str,
    structured: Mapping[str, Any],
) -> JsonDict:
    compact = dict(structured)
    if descriptor_name == draft_tool_name:
        compact.pop("reviewer_only_html", None)
    return compact


def validate_tool_structured_content(
    payload: Mapping[str, Any],
    output_schema: Mapping[str, Any],
) -> None:
    require_json_object(payload)
    ensure_safe_sanitized_payload(_tool_result_payload_for_generic_safety(payload))
    _ensure_no_forbidden_tool_result_payload(payload)
    if len(_compact_json(payload).encode("utf-8")) > MAX_TOOL_RESULT_BYTES:
        raise ContractValidationError("MCP tool result is too large")
    if not _matches_schema(payload, output_schema):
        raise ContractValidationError("MCP tool result schema mismatch")


def _pre_draft_tool_result_text(structured: Mapping[str, Any]) -> str | None:
    if structured.get("result_kind") == "clean_ticket_registered":
        status = {
            "clean_ticket_sha256": structured.get("clean_ticket_sha256"),
            "clean_ticket_store_ref": structured.get("clean_ticket_store_ref"),
            "clean_ticket_storage_hint": structured.get(
                "clean_ticket_storage_hint"
            ),
            "clean_ticket_storage_ref": structured.get("clean_ticket_storage_ref"),
            "next_arguments": structured.get("next_arguments"),
            "next_tool_name": structured.get("next_tool_name"),
            "ok": structured.get("ok"),
            "result_kind": structured.get("result_kind"),
            "ticket_ref": structured.get("ticket_ref"),
            "writes_files": structured.get("writes_files"),
        }
        return (
            "Clean ticket transcript registered. Continue by calling "
            "kcs_draft_article with next_arguments exactly as returned.\n\n"
            "Compact status:\n"
            "```json\n"
            f"{_compact_json(status)}\n"
            "```"
        )
    if structured.get("result_kind") == "semantic_review_packet":
        required_submit_shape = structured.get("required_submit_shape")
        return (
            "Semantic review packet prepared by the KCS Authoring tool. "
            "Identify atomic KCS item candidates only. Do not draft an article, "
            "choose a KCS action, choose a candidate yourself, produce HTML, or "
            "use item/item_candidates payloads. If selected_excerpts contain "
            "more than one separately searchable KCS issue, submit all of those "
            "candidates together in the items array; Python will return the "
            "operator choice request. Use only the selected_excerpts and cite "
            "only allowed_source_refs in candidate_semantic_extraction_v1 "
            "output. Do not copy raw transcript text, raw command output, local "
            "workstation paths, or reviewer-bundle paths into the submission. "
            "Sanitized server configuration and log paths are allowed only when "
            "needed for standalone evidence. Do not add extra fields such as "
            "candidates, commands, log_file, service_names, or services_affected. "
            "The candidate array key must be items.\n\n"
            "For technical_scr candidates, resolution_steps must be standalone "
            "and executable. Include command names with arguments, service "
            "names, ports, rule names, and verification targets when present in "
            "selected_excerpts. Avoid vague steps such as 'create a rule' or "
            "'block the traffic' unless the concrete action detail is included. "
            "If the excerpts give only the resolution outcome or a high-level "
            "resolution description without the exact executable procedure "
            "needed to apply and verify it, do not invent the missing detail; "
            "submit only supported evidence and let Python return a "
            "resolution-steps blocker. That blocker may be resolved later only "
            "with operator-confirmed resolution detail.\n\n"
            "Call kcs_submit_semantic_review with this exact argument shape:\n"
            "```json\n"
            f"{_compact_json(required_submit_shape)}\n"
            "```\n\n"
            "Packet:\n"
            "```json\n"
            f"{_compact_json(structured)}\n"
            "```"
        )
    if structured.get("debug_code") == "clean_ticket_text_incomplete":
        status = {
            "debug_code": structured.get("debug_code"),
            "draft_available": False,
            "failure_stage": structured.get("failure_stage"),
            "next_required_action": "register_complete_visible_clean_ticket_text",
            "ok": structured.get("ok"),
            "result_kind": structured.get("result_kind"),
            "writes_files": structured.get("writes_files"),
        }
        return (
            "Clean ticket registration is blocked because the provided text "
            "appears to be an incomplete or truncated ticket excerpt. No clean "
            "ticket was saved and no article draft is available.\n\n"
            "Do not draft manually. Read the complete visible sanitized file "
            "text, then call kcs_register_clean_ticket again with the complete "
            "transcript.\n\n"
            "Compact status:\n"
            "```json\n"
            f"{_compact_json(status)}\n"
            "```"
        )
    if structured.get("debug_code") == "clean_ticket_text_invalid":
        status = {
            "debug_code": structured.get("debug_code"),
            "draft_available": False,
            "failure_stage": structured.get("failure_stage"),
            "next_required_action": "register_original_visible_clean_ticket_text",
            "ok": structured.get("ok"),
            "result_kind": structured.get("result_kind"),
            "writes_files": structured.get("writes_files"),
        }
        return (
            "Clean ticket registration is blocked because the provided text is "
            "not an acceptable clean ticket transcript. No clean ticket was "
            "saved and no article draft is available.\n\n"
            "Do not draft manually. Do not reconstruct, summarize, or invent "
            "missing ticket sections. Call kcs_register_clean_ticket again only "
            "with the original complete visible sanitized ticket text.\n\n"
            "Compact status:\n"
            "```json\n"
            f"{_compact_json(status)}\n"
            "```"
        )
    if structured.get("result_kind") == "behavior_instructions":
        return (
            "KCS Authoring behavior: for sanitized support-ticket article "
            "requests, use KCS Authoring:kcs_draft_ticket with ticket_ref "
            "when a cleaned ticket transcript already exists. If the user asks "
            "to draft an article from a sanitized attachment or long paste and "
            "no ticket_ref exists, first call kcs_register_clean_ticket, then "
            "call the returned next tool with next_arguments exactly. A Claude "
            "Desktop file card is not a filesystem path; use visible file text "
            "instead of inspecting upload directories. If no visible file text "
            "is available, report file_content_unavailable and do not draft "
            "manually. Do not stop after this helper; immediately continue the "
            "KCS Authoring workflow."
        )
    return None


def _debug_tool_result_text(structured: Mapping[str, Any]) -> str | None:
    if structured.get("debug_code") in {
        "approved_ticket_summary_invalid",
        "approved_ticket_summary_not_found",
    }:
        return _approved_ticket_blocked_tool_result_text(structured)
    if structured.get("debug_code") == "semantic_extraction_provider_unavailable":
        status = {
            "auto_publish_allowed": structured.get("auto_publish_allowed"),
            "debug_code": structured.get("debug_code"),
            "draft_available": False,
            "failure_stage": structured.get("failure_stage"),
            "manual_draft_allowed": structured.get("manual_draft_allowed"),
            "next_required_action": structured.get("next_required_action"),
            "recommended_action": structured.get("recommended_action"),
            "result_kind": structured.get("result_kind"),
            "should_be_kcs_article": structured.get("should_be_kcs_article"),
            "writes_files": structured.get("writes_files"),
        }
        return (
            "KCS article drafting is blocked by the KCS Authoring tool because "
            "the approved semantic extraction provider is not configured. No "
            "reviewer-only draft was generated.\n\n"
            "Compact status:\n"
            "```json\n"
            f"{_compact_json(status)}\n"
            "```"
        )
    if structured.get("workflow_state") == "semantic_review_required":
        return _semantic_review_required_tool_result_text(structured)
    if structured.get("workflow_state") == "semantic_review_metadata_blocked":
        status = {
            "approved_summary_source": structured.get("approved_summary_source"),
            "auto_publish_allowed": structured.get("auto_publish_allowed"),
            "debug_code": structured.get("debug_code"),
            "draft_generated": structured.get("draft_generated"),
            "failure_stage": structured.get("failure_stage"),
            "manual_draft_allowed": structured.get("manual_draft_allowed"),
            "next_required_action": structured.get("next_required_action"),
            "operator_resolution_detail_policy": structured.get(
                "operator_resolution_detail_policy"
            ),
            "public_output_approved": structured.get("public_output_approved"),
            "recommended_action": structured.get("recommended_action"),
            "result_kind": structured.get("result_kind"),
            "reviewer_bundle_written": structured.get("reviewer_bundle_written"),
            "ticket_ref": structured.get("ticket_ref"),
            "workflow_state": structured.get("workflow_state"),
            "writes_files": structured.get("writes_files"),
        }
        return (
            "KCS article drafting is blocked by the KCS Authoring tool because "
            "the clean-ticket metadata required for semantic review is missing, "
            "disabled, or no longer matches the clean ticket file. No "
            "reviewer-only draft was generated.\n\n"
            "Do not draft manually. Repair or re-register the clean ticket, then "
            "run the KCS draft workflow again.\n\n"
            "Compact status:\n"
            "```json\n"
            f"{_compact_json(status)}\n"
            "```"
        )
    if structured.get("workflow_state") in {
        "semantic_review_prepare_blocked",
        "semantic_review_submit_blocked",
    }:
        return _semantic_review_blocked_tool_result_text(structured)
    authoring_failure_text = _authoring_failure_debug_tool_result_text(structured)
    if authoring_failure_text is not None:
        return authoring_failure_text
    return None


def _authoring_failure_debug_tool_result_text(
    structured: Mapping[str, Any],
) -> str | None:
    if structured.get("debug_code") == "semantic_extraction_no_candidates":
        status = {
            "approved_summary_source": structured.get("approved_summary_source"),
            "auto_publish_allowed": structured.get("auto_publish_allowed"),
            "debug_code": structured.get("debug_code"),
            "draft_available": False,
            "failure_stage": structured.get("failure_stage"),
            "manual_draft_allowed": structured.get("manual_draft_allowed"),
            "next_required_action": (
                "register_complete_clean_ticket_with_final_evidence"
            ),
            "recommended_action": structured.get("recommended_action"),
            "result_kind": structured.get("result_kind"),
            "should_be_kcs_article": structured.get("should_be_kcs_article"),
            "ticket_ref": structured.get("ticket_ref"),
            "writes_files": structured.get("writes_files"),
        }
        return (
            "KCS article drafting is blocked by the KCS Authoring tool because "
            "Python did not find a complete semantic KCS item in the clean "
            "ticket text. No reviewer-only draft was generated.\n\n"
            "Do not draft manually. Register a complete sanitized clean ticket "
            "that includes the final symptom, supported cause, and resolution "
            "evidence, then call kcs_draft_article again with the returned "
            "ticket_ref.\n\n"
            "Compact status:\n"
            "```json\n"
            f"{_compact_json(status)}\n"
            "```"
        )
    if (
        structured.get("debug_code")
        in {
            "approved_summary_evidence_build_failed",
            "approved_summary_validation_failed",
            "approved_summary_renderer_failed",
            "approved_summary_renderer_bounds_failed",
        }
        and structured.get("draft_generated") is not True
    ):
        status = {
            "auto_publish_allowed": structured.get("auto_publish_allowed"),
            "debug_code": structured.get("debug_code"),
            "draft_generated": structured.get("draft_generated"),
            "failure_stage": structured.get("failure_stage"),
            "manual_draft_allowed": structured.get("manual_draft_allowed"),
            "next_required_action": structured.get("next_required_action"),
            "public_output_approved": structured.get("public_output_approved"),
            "recommended_action": structured.get("recommended_action"),
            "result_kind": structured.get("result_kind"),
            "reviewer_bundle_written": structured.get("reviewer_bundle_written"),
            "ticket_ref": structured.get("ticket_ref"),
            "validation_ok": structured.get("validation_ok"),
            "writes_files": structured.get("writes_files"),
        }
        return (
            "KCS article drafting is blocked by the KCS Authoring tool. No "
            "reviewer-only draft was generated.\n\n"
            "Do not draft manually. Do not invent recovery choices or ask the "
            "operator to choose a narrower candidate. If next_required_action "
            "or next_tool is absent in the compact status, stop and report the "
            "debug_code/failure_stage for tool-side review. If debug_code is "
            "approved_summary_resolution_steps_incomplete, treat the blocker as "
            "valid when the ticket gives only the resolution outcome or a "
            "high-level resolution description without the exact executable "
            "procedure needed to apply and verify it. The operator may provide "
            "operator-confirmed resolution detail and rerun the workflow; do "
            "not infer the missing procedure yourself.\n\n"
            "Compact status:\n"
            "```json\n"
            f"{_compact_json(status)}\n"
            "```"
        )
    return None


def _approved_ticket_blocked_tool_result_text(
    structured: Mapping[str, Any],
) -> str:
    status = {
        "auto_publish_allowed": structured.get("auto_publish_allowed"),
        "debug_code": structured.get("debug_code"),
        "draft_available": False,
        "failure_stage": structured.get("failure_stage"),
        "manual_draft_allowed": structured.get("manual_draft_allowed"),
        "next_required_action": structured.get("next_required_action"),
        "recommended_action": structured.get("recommended_action"),
        "result_kind": structured.get("result_kind"),
        "should_be_kcs_article": structured.get("should_be_kcs_article"),
        "ticket_ref": structured.get("ticket_ref"),
        "writes_files": structured.get("writes_files"),
    }
    if structured.get("debug_code") == "approved_ticket_summary_not_found":
        explanation = (
            "the ticket_ref was not found in the configured clean ticket store"
        )
        next_step = (
            "Check that the external cleanup form wrote the prepared clean "
            "ticket under the configured store, then call "
            "kcs_draft_article again with the same ticket_ref."
        )
    else:
        explanation = (
            "the clean ticket file was found but rejected by input/safety "
            "validation"
        )
        next_step = (
            "Re-run the local cleanup/preparation step for this ticket_ref "
            "or inspect the clean-ticket privacy scan result, then call "
            "kcs_draft_article again. Do not paste the transcript into chat "
            "unless the operator explicitly chooses that path."
        )
    return (
        "KCS article drafting is blocked by the KCS Authoring tool because "
        f"{explanation}. No reviewer-only draft was generated.\n\n"
        "Do not draft manually.\n\n"
        f"{next_step}\n\n"
        "Compact status:\n"
        "```json\n"
        f"{_compact_json(status)}\n"
        "```"
    )


def _semantic_review_blocked_tool_result_text(
    structured: Mapping[str, Any],
) -> str:
    plain_string_hint = ""
    if structured.get("debug_code") == "semantic_review_plain_string_arrays_required":
        plain_string_hint = (
            "\n\nSubmit shape correction: symptoms, confirmed_facts, "
            "resolution_steps, source_refs, and open_questions must be arrays "
            "of plain strings only. Preserve resolution order by array order; "
            "do not submit objects such as {order, action}, {text}, or nested "
            "step structures."
        )
    if structured.get("debug_code") == "semantic_review_environment_invalid":
        plain_string_hint = (
            "\n\nSubmit shape correction: environment must contain only "
            "normalized product/platform metadata. Use product 'Plesk'; use "
            "platform 'Linux', 'Windows', 'Plesk for Linux', or "
            "'Plesk for Windows'; use applicable_to values 'Plesk for Linux' "
            "or 'Plesk for Windows'. Put IPv4, IPv6, ports, services, and log "
            "paths in confirmed_facts or resolution_steps when excerpt-grounded."
        )
    if structured.get("debug_code") in {
        "semantic_review_forbidden_field",
        "semantic_review_forbidden_html_or_markdown",
        "semantic_review_local_ref_blocked",
    }:
        plain_string_hint = (
            "\n\nSubmit shape correction: remove forbidden article/payload "
            "content from the semantic extraction. Submit only "
            "candidate_semantic_extraction_v1 fields from the prepared packet; "
            "do not include HTML, Markdown article headings, local paths, "
            "reviewer files, item/item_candidates, recommended_action, or "
            "publication flags."
        )
    status = {
        "auto_publish_allowed": structured.get("auto_publish_allowed"),
        "debug_code": structured.get("debug_code"),
        "draft_generated": structured.get("draft_generated"),
        "failure_stage": structured.get("failure_stage"),
        "manual_draft_allowed": structured.get("manual_draft_allowed"),
        "next_required_action": structured.get("next_required_action"),
        "public_output_approved": structured.get("public_output_approved"),
        "recommended_action": structured.get("recommended_action"),
        "result_kind": structured.get("result_kind"),
        "reviewer_bundle_written": structured.get("reviewer_bundle_written"),
        "workflow_state": structured.get("workflow_state"),
        "writes_files": structured.get("writes_files"),
    }
    return (
        "KCS semantic review is blocked by the KCS Authoring tool. No "
        "reviewer-only draft was generated.\n\n"
        "Do not draft manually. Do not ask the operator to choose a recovery "
        "strategy. If the blocker includes a submit shape correction, retry "
        "kcs_submit_semantic_review at most once with the same "
        "semantic_review_ref and a corrected candidate_semantic_extraction. If "
        "there is no submit shape correction, stop and report the compact "
        "status. Do not restart or retry the same ticket_ref automatically "
        "unless the compact status explicitly asks for a restart. Re-register "
        "only when workflow_state is semantic_review_metadata_blocked.\n\n"
        f"{plain_string_hint}\n\n"
        "Compact status:\n"
        "```json\n"
        f"{_compact_json(status)}\n"
        "```"
    )


def _semantic_review_required_tool_result_text(
    structured: Mapping[str, Any],
) -> str:
    status = {
        "approved_summary_source": structured.get("approved_summary_source"),
        "auto_publish_allowed": structured.get("auto_publish_allowed"),
        "debug_code": structured.get("debug_code"),
        "draft_generated": structured.get("draft_generated"),
        "failure_stage": structured.get("failure_stage"),
        "manual_draft_allowed": structured.get("manual_draft_allowed"),
        "next_arguments": structured.get("next_arguments"),
        "next_required_action": structured.get("next_required_action"),
        "next_tool": structured.get("next_tool"),
        "public_output_approved": structured.get("public_output_approved"),
        "recommended_action": structured.get("recommended_action"),
        "result_kind": structured.get("result_kind"),
        "reviewer_bundle_written": structured.get("reviewer_bundle_written"),
        "semantic_review_ref": structured.get("semantic_review_ref"),
        "ticket_ref": structured.get("ticket_ref"),
        "workflow_state": structured.get("workflow_state"),
        "writes_files": structured.get("writes_files"),
    }
    return (
        "KCS article drafting is paused by the KCS Authoring tool because "
        "Python found likely KCS material, but deterministic item "
        "identification is low-confidence for this clean ticket. No "
        "reviewer-only draft was generated.\n\n"
        "Do not draft manually. Do not create article text from the clean "
        "ticket in chat. Continue only by calling the returned next_tool with "
        "next_arguments exactly as returned.\n\n"
        "Compact status:\n"
        "```json\n"
        f"{_compact_json(status)}\n"
        "```"
    )


def _split_required_tool_result_text(structured: Mapping[str, Any]) -> str:
    choice_request = structured.get("operator_choice_request")
    options = (
        choice_request.get("options")
        if isinstance(choice_request, Mapping)
        else None
    )
    option_lines: list[str] = []
    if isinstance(options, list):
        for index, option in enumerate(options, start=1):
            if not isinstance(option, Mapping):
                continue
            label = str(option.get("label") or option.get("value") or f"Option {index}")
            submit_arguments = option.get("submit_arguments")
            safe_submit_arguments = (
                submit_arguments if isinstance(submit_arguments, Mapping) else {}
            )
            option_lines.append(
                f"{index}. {label}\n"
                "   submit_arguments: "
                f"{_compact_json(safe_submit_arguments)}"
            )
    status = {
        "debug_code": structured.get("debug_code"),
        "draft_request_ready": structured.get("draft_request_ready"),
        "failure_stage": structured.get("failure_stage"),
        "manual_draft_allowed": structured.get("manual_draft_allowed"),
        "next_required_action": structured.get("next_required_action"),
        "operator_selection_ref": structured.get("operator_selection_ref"),
        "recommended_action": structured.get("recommended_action"),
        "result_kind": structured.get("result_kind"),
    }
    options_text = (
        "\n".join(option_lines) if option_lines else "No safe options returned."
    )
    return (
        "Multiple KCS article candidates were detected. Operator selection is "
        "required before drafting.\n\n"
        "Use the native single-choice popup when Claude Desktop provides one. "
        "Do not answer with a prose-only candidate list. If no popup is "
        "available, show these options and then continue only by calling "
        "kcs_draft_article with exactly the selected option's submit_arguments. "
        "Do not call kcs_submit_semantic_review again for this choice. Do not "
        "draft manually.\n\n"
        "Candidate options:\n"
        f"{options_text}\n\n"
        "Compact status:\n"
        "```json\n"
        f"{_compact_json(status)}\n"
        "```"
    )


def _tool_result_payload_for_generic_safety(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            key: (
                _mask_local_tool_ref(item)
                if key in _TOOL_RESULT_LOCAL_REF_FIELDS and isinstance(item, str)
                else _mask_approved_tool_html_urls(item)
                if key in _TOOL_RESULT_HTML_FIELDS and isinstance(item, str)
                else _tool_result_payload_for_generic_safety(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_tool_result_payload_for_generic_safety(item) for item in value]
    return value


def _mask_local_tool_ref(value: str) -> str:
    if _SAFE_LOCAL_REF_RE.fullmatch(value):
        return "safe-local-ref"
    return value


def _mask_approved_tool_html_urls(value: str) -> str:
    masked = value
    for url, safe_ref in _APPROVED_HTML_URL_REFS.items():
        masked = masked.replace(url, safe_ref)
    return masked


def _matches_schema(payload: Mapping[str, Any], schema: Mapping[str, Any]) -> bool:
    any_of = schema.get("anyOf")
    if isinstance(any_of, list):
        return any(
            isinstance(option, Mapping) and _matches_schema(payload, option)
            for option in any_of
        )
    if schema.get("type") != "object":
        return False
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    if not isinstance(properties, Mapping) or not isinstance(required, list):
        return False
    if schema.get("additionalProperties") is False and any(
        key not in properties for key in payload
    ):
        return False
    if any(not isinstance(key, str) or key not in payload for key in required):
        return False
    return all(
        _value_matches_type(value, properties.get(key))
        for key, value in payload.items()
    )


def _value_matches_type(value: object, schema: object) -> bool:
    if not isinstance(schema, Mapping):
        return False
    schema_type = schema.get("type")
    if schema_type == "boolean":
        return isinstance(value, bool)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "array":
        return isinstance(value, list)
    if schema_type == "object":
        return isinstance(value, Mapping)
    return False


def _ensure_no_forbidden_tool_result_payload(
    value: object,
    *,
    current_key: str | None = None,
) -> None:
    if isinstance(value, Mapping):
        _ensure_no_forbidden_tool_result_mapping(value)
        return
    if isinstance(value, list):
        _ensure_no_forbidden_tool_result_list(value, current_key=current_key)
        return
    if isinstance(value, str):
        _ensure_no_forbidden_tool_result_string(value, current_key=current_key)


def _ensure_no_forbidden_tool_result_mapping(value: Mapping[object, object]) -> None:
    for key, item in value.items():
        if not isinstance(key, str):
            raise ContractValidationError("MCP tool result schema mismatch")
        _ensure_no_forbidden_tool_result_key(key)
        _ensure_no_forbidden_tool_result_payload(item, current_key=key)


def _ensure_no_forbidden_tool_result_list(
    value: list[object],
    *,
    current_key: str | None,
) -> None:
    for item in value:
        _ensure_no_forbidden_tool_result_payload(item, current_key=current_key)


def _ensure_no_forbidden_tool_result_string(
    value: str,
    *,
    current_key: str | None,
) -> None:
    if current_key in _TOOL_RESULT_HTML_FIELDS:
        _ensure_no_forbidden_tool_result_html(value)
        return
    _ensure_no_forbidden_tool_result_text(value)


def _ensure_no_forbidden_tool_result_html(value: str) -> None:
    normalized = value.casefold()
    compact = normalized.replace("_", "").replace("-", "")
    if any(fragment in normalized for fragment in _RESULT_FORBIDDEN_FRAGMENTS):
        raise ContractValidationError("MCP tool result contains unsafe value")
    if any(
        fragment in compact for fragment in _RESULT_FORBIDDEN_COMPACT_FRAGMENTS
    ):
        raise ContractValidationError("MCP tool result contains unsafe value")
    for url in _HTML_URL_RE.findall(value):
        if url not in _APPROVED_HTML_URL_REFS:
            raise ContractValidationError("MCP tool result contains unsafe value")


def _ensure_no_forbidden_tool_result_text(value: str) -> None:
    normalized = value.casefold()
    compact = normalized.replace("_", "").replace("-", "")
    if any(fragment in normalized for fragment in _RESULT_FORBIDDEN_FRAGMENTS):
        raise ContractValidationError("MCP tool result contains unsafe value")
    if any(
        fragment in compact for fragment in _RESULT_FORBIDDEN_COMPACT_FRAGMENTS
    ):
        raise ContractValidationError("MCP tool result contains unsafe value")
    if _FORBIDDEN_TEXT_HTML_TAG_RE.search(value):
        raise ContractValidationError("MCP tool result contains unsafe value")


def _ensure_no_forbidden_tool_result_key(value: str) -> None:
    normalized = value.casefold()
    if normalized in _RESULT_FORBIDDEN_EXACT_KEYS:
        raise ContractValidationError("MCP tool result contains unsafe value")
    _ensure_no_forbidden_tool_result_text(value)


def _compact_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, allow_nan=False, separators=(",", ":"))


__all__ = [
    "desktop_structured_content",
    "tool_result_content",
    "tool_result_text",
    "validate_tool_structured_content",
]
