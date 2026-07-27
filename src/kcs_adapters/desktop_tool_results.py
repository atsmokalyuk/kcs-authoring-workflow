"""Claude Desktop MCP tool-result formatting and output-boundary checks."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from kcs_adapters.desktop_draft_batch import closed_blocker_codes
from kcs_adapters.desktop_protocol import SEMANTIC_CONTROL_GUIDANCE
from kcs_adapters.desktop_semantic_candidate_contract import (
    semantic_submission_correction,
)
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
_SEMANTIC_OBSERVATION_FIELD_PATH_RE = re.compile(
    r"issues\[(?:0|[1-9][0-9]*)\]\.(?:"
    r"answer_evidence|cause_evidence|context_evidence|error_evidence|question|"
    r"resolution_evidence|summary|symptoms|verification_evidence"
    r")\Z"
)
_SEMANTIC_FIELD_PATH_CORRECTION_CODES = frozenset(
    {
        "semantic_observation_shape_invalid",
        "semantic_observation_text_not_extractive",
    }
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
    pre_draft_text = _initial_tool_result_text(structured)
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
        sequence = _comparison_sequence_section(
            structured.get("comparison_sequence_outcomes"),
            heading="Ordered sequence results",
        )
        suffix = f"\n\n{sequence}" if sequence else ""
        return (
            f"```html\n{html}\n```\n\n"
            f"```json\n{_compact_json(status)}\n```"
            f"{suffix}"
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
        sequence = _comparison_sequence_section(
            structured.get("comparison_sequence_outcomes"),
            heading="Ordered sequence results",
        )
        sequence_suffix = (
            "\n\nReport every ordered result below; do not report only the "
            f"current item.\n\n{sequence}"
            if sequence
            else ""
        )
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
                f"{sequence_suffix}"
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
            f"{sequence_suffix}"
        )
    if structured.get("recommended_action") == "split_required" and isinstance(
        structured.get("operator_choice_request"), Mapping
    ):
        return _split_required_tool_result_text(structured)
    return _compact_json(structured)


def _initial_tool_result_text(structured: Mapping[str, Any]) -> str | None:
    if structured.get("result_kind") == "reuse_comparison_required":
        return _reuse_comparison_required_tool_result_text(structured)
    if structured.get("result_kind") in {
        "reuse_comparison_blocked",
        "reuse_comparison_completed",
        "reuse_comparison_submit_failed",
    }:
        return _reuse_comparison_terminal_tool_result_text(structured)
    if structured.get("result_kind") == "draft_article_batch":
        return _draft_article_batch_tool_result_text(structured)
    return _pre_draft_tool_result_text(structured)


def _reuse_comparison_required_tool_result_text(
    structured: Mapping[str, Any],
) -> str:
    context = {
        "accepted_ticket_facts": structured.get("accepted_ticket_facts"),
        "comparison_candidates": structured.get("comparison_candidates"),
        "comparison_outcomes": structured.get("comparison_outcomes"),
        "comparison_ref": structured.get("comparison_ref"),
        "submit_tool": structured.get("submit_tool"),
    }
    completed = _comparison_sequence_section(
        structured.get("comparison_sequence_outcomes"),
        heading="Completed item results",
    )
    completed_section = (
        "\n\nReport these already completed item results before the current "
        "comparison. Preserve every artifact reference exactly.\n\n"
        f"{completed}"
        if completed
        else ""
    )
    return (
        "A bounded public-article comparison is required before drafting. "
        "Compare only accepted_ticket_facts with the cited candidate excerpts. "
        "Display every candidate title as a clickable Markdown link using that "
        "candidate's public_url, and keep its candidate_ref visible. "
        "Present one concise recommendation that states what is covered and "
        "what relevant knowledge is missing, then ask exactly one operator "
        "question using only reuse, update, none_fit, or need_more_evidence. "
        "Do not call the submit tool until the operator answers.\n\n"
        "After the answer, call submit_tool with comparison_ref and outcome "
        "exactly. For reuse or update, also copy one displayed candidate_ref. "
        "For none_fit or need_more_evidence, omit candidate_ref; if one displayed "
        "candidate_ref is redundantly supplied, Python validates and ignores it. "
        "Do not submit ticket facts, excerpts, URLs, recommendations, or "
        "free-form text."
        f"{completed_section}\n\n"
        "Comparison context:\n"
        "```json\n"
        f"{_compact_json(context)}\n"
        "```"
    )


def _comparison_sequence_section(
    value: object,
    *,
    heading: str,
) -> str:
    if not isinstance(value, list):
        return ""
    lines: list[str] = []
    for index, outcome in enumerate(value, start=1):
        if not isinstance(outcome, Mapping):
            continue
        item_ref = outcome.get("item_ref")
        item_label = item_ref if isinstance(item_ref, str) else "item"
        comparison_outcome = outcome.get("comparison_outcome")
        outcome_label = (
            comparison_outcome
            if isinstance(comparison_outcome, str)
            else "completed"
        )
        lines.append(f"{index}. **{item_label}** — `{outcome_label}`")
        for label, key in (
            ("Recommended action", "recommended_action"),
            ("Reviewer bundle", "bundle_ref"),
            ("Manifest", "manifest_path"),
            ("Reviewer HTML", "html_path"),
        ):
            field = outcome.get(key)
            if isinstance(field, str) and field:
                lines.append(f"   - {label}: `{field}`")
    if not lines:
        return ""
    return f"{heading}:\n" + "\n".join(lines)


def _reuse_comparison_terminal_tool_result_text(
    structured: Mapping[str, Any],
) -> str:
    if structured.get("next_required_action") == "resubmit_pending_reuse_comparison":
        status = {
            "comparison_outcomes": structured.get("comparison_outcomes"),
            "comparison_ref": structured.get("comparison_ref"),
            "debug_code": structured.get("debug_code"),
            "next_required_action": structured.get("next_required_action"),
            "result_kind": structured.get("result_kind"),
        }
        return (
            "The previous submit shape was invalid, but the active comparison "
            "is preserved. Submit the same comparison_ref again with the "
            "outcome argument set to exactly one value listed in "
            "comparison_outcomes. Use only the operator's latest "
            "answer; when it maps unambiguously to a listed value, correct the "
            "tool argument without asking the operator to reconfirm. For reuse "
            "or update include one displayed candidate_ref. For none_fit or "
            "need_more_evidence omit candidate_ref. Do not restart drafting or "
            "change the operator's decision.\n\n"
            "Compact status:\n"
            "```json\n"
            f"{_compact_json(status)}\n"
            "```"
        )
    status = {
        "blockers": structured.get("blockers"),
        "comparison_outcome": structured.get("comparison_outcome"),
        "debug_code": structured.get("debug_code"),
        "draft_generated": structured.get("draft_generated"),
        "next_required_action": structured.get("next_required_action"),
        "recommended_action": structured.get("recommended_action"),
        "result_kind": structured.get("result_kind"),
        "selected_reuse_match": structured.get("selected_reuse_match"),
    }
    return (
        "The operator-confirmed comparison step is complete or has stopped "
        "fail-closed. Follow only the returned recommended_action or "
        "next_required_action. Do not draft manually, infer another outcome, "
        "or replay the comparison reference.\n\n"
        "Compact status:\n"
        "```json\n"
        f"{_compact_json(status)}\n"
        "```"
    )


def _draft_article_batch_tool_result_text(
    structured: Mapping[str, Any],
) -> str:
    operator_followup = _safe_batch_operator_followup(
        structured.get("operator_followup")
    )
    status = {
        "attempted_count": structured.get("attempted_count"),
        "auto_publish_allowed": structured.get("auto_publish_allowed"),
        "batch_status": structured.get("batch_status"),
        "blockers": closed_blocker_codes(structured.get("blockers")),
        "completed_count": structured.get("completed_count"),
        "debug_code": structured.get("debug_code"),
        "draft_generated_count": structured.get("draft_generated_count"),
        "failure_stage": structured.get("failure_stage"),
        "new_draft_created_count": structured.get("new_draft_created_count"),
        "next_required_action": structured.get("next_required_action"),
        "operator_followup": operator_followup,
        "public_output_approved": structured.get("public_output_approved"),
        "remaining_item_candidates": structured.get("remaining_item_candidates"),
        "retryable_blocked_count": structured.get("retryable_blocked_count"),
        "retryable_item_candidates": structured.get("retryable_item_candidates"),
        "result_kind": structured.get("result_kind"),
        "reviewer_bundle_written": structured.get("reviewer_bundle_written"),
        "selected_count": structured.get("selected_count"),
        "terminal_blocked_count": structured.get("terminal_blocked_count"),
        "workflow_stopped_count": structured.get("workflow_stopped_count"),
        "writes_files": structured.get("writes_files"),
    }
    guidance = (
        "Present the Python-owned ordered candidate summary below. Preserve each "
        "candidate title, outcome meaning, reviewer bundle reference, and HTML "
        "path. Follow `operator_followup` exactly. When its kind is `none`, do "
        "not ask the operator to provide retry detail or confirm leaving a "
        "candidate blocked. Do not reproduce raw "
        "machine fields, invent actions, retry terminal or not-attempted "
        "candidates, fan out a batch, draft manually, offer artifact inspection, "
        "or ask an open-ended follow-up question. Closed blocker kinds and "
        "aggregate counters in the compact status are value-safe diagnostics "
        "and may be reported exactly."
    )
    followup_text = _batch_operator_followup_text(operator_followup)
    return (
        f"{guidance}\n\n"
        "Operator result summary:\n"
        f"{followup_text}\n\n"
        "Compact status:\n"
        "```json\n"
        f"{_compact_json(status)}\n"
        "```\n\n"
        "Response end condition: the batch result is complete. End after the "
        "ordered summary. Do not ask a question, request resolution detail, or "
        "offer a retry. A deferred candidate may be resumed only after the "
        "operator independently supplies confirmed detail in a later turn."
    )


def _batch_operator_followup_text(value: object) -> str:
    if not isinstance(value, Mapping):
        return "- Follow-up contract unavailable; stop and request tool-side review."
    candidates = value.get("summary_candidates")
    lines = _batch_candidate_summary_lines(candidates)
    prompt = value.get("prompt")
    if value.get("kind") != "none" and isinstance(prompt, str) and prompt:
        label = "Status" if value.get("kind") == "tool_review_required" else "Next"
        lines.append(f"- {label}: {prompt}")
    return "\n".join(lines) if lines else "- No operator follow-up is required."


def _batch_candidate_summary_lines(candidates: object) -> list[str]:
    if not isinstance(candidates, list):
        return []
    lines: list[str] = []
    for index, candidate in enumerate(candidates, start=1):
        if not isinstance(candidate, Mapping):
            continue
        label = _batch_followup_candidate_label(candidate, include_artifacts=False)
        item_ref = candidate.get("item_ref")
        heading = f"{label} ({item_ref})" if isinstance(item_ref, str) else label
        headline, explanation = _batch_candidate_outcome_text(candidate)
        lines.extend(
            (
                f"{index}. **{heading}**",
                f"   - **{headline}** - {explanation}",
            )
        )
        for artifact_label, key in (
            ("Reviewer bundle", "bundle_ref"),
            ("Reviewer HTML", "html_path"),
        ):
            artifact = candidate.get(key)
            if isinstance(artifact, str) and artifact:
                lines.append(f"   - {artifact_label}: `{artifact}`")
        blockers = closed_blocker_codes(candidate.get("blockers"))
        if blockers:
            lines.append(
                "   - Closed blockers: "
                + ", ".join(blockers)
            )
    return lines


def _safe_batch_operator_followup(value: object) -> object:
    if not isinstance(value, Mapping):
        return value
    safe_followup = dict(value)
    for key in (
        "completed_not_ready_candidates",
        "not_attempted_candidates",
        "retryable_candidates",
        "reviewer_ready_candidates",
        "summary_candidates",
        "tool_review_candidates",
    ):
        cards = value.get(key)
        if not isinstance(cards, list):
            continue
        safe_cards: list[JsonDict] = []
        for card in cards:
            if not isinstance(card, Mapping):
                continue
            safe_card = dict(card)
            blockers = closed_blocker_codes(card.get("blockers"))
            if blockers:
                safe_card["blockers"] = blockers
            else:
                safe_card.pop("blockers", None)
            safe_cards.append(safe_card)
        safe_followup[key] = safe_cards
    return safe_followup


def _batch_candidate_outcome_text(value: Mapping[str, Any]) -> tuple[str, str]:
    status = value.get("presentation_status")
    action = value.get("recommended_action")
    if status == "existing_article_review" or action == "flag_existing":
        return (
            "Flag existing article",
            "A matching article was found; review it instead of creating a duplicate.",
        )
    if status == "draft_generated_not_kcs_ready":
        return (
            "Draft generated, not KCS-ready",
            "A reviewer draft was written but still requires the recorded checks.",
        )
    if status == "blocked_retryable":
        return (
            "Blocked, deferred",
            (
                "No current operator action is required; resume only after the "
                "operator later initiates with exact confirmed resolution or "
                "workaround steps."
            ),
        )
    if status in {"completed_blocked", "workflow_stopped"}:
        return (
            "Blocked",
            "No operator retry is available; tool-side review is required.",
        )
    if status == "not_attempted":
        return "Not attempted", "The fail-closed batch stop prevented this attempt."
    if value.get("ready_for_reviewer") is True:
        return "Ready for reviewer", "The reviewer artifact was generated successfully."
    return "Completed", "The candidate was processed with no further operator action."


def _batch_followup_candidate_label(
    value: Mapping[str, Any],
    *,
    include_artifacts: bool = True,
) -> str:
    title = value.get("title")
    if isinstance(title, str) and title:
        label = title
    else:
        option_label = value.get("label")
        if isinstance(option_label, str) and option_label:
            label = option_label
        else:
            item_ref = value.get("item_ref")
            label = item_ref if isinstance(item_ref, str) else "candidate"
    artifact_fields = (
        ("bundle", value.get("bundle_ref")),
        ("html", value.get("html_path")),
    )
    artifacts = "; ".join(
        f"{name}={field_value}"
        for name, field_value in artifact_fields
        if isinstance(field_value, str) and field_value
    )
    return f"{label} ({artifacts})" if include_artifacts and artifacts else label


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


def _early_pre_draft_tool_result_text(
    structured: Mapping[str, Any],
) -> str | None:
    if structured.get("result_kind") == "clean_ticket_registered":
        status = {
            "clean_ticket_sha256": structured.get("clean_ticket_sha256"),
            "clean_ticket_store_ref": structured.get("clean_ticket_store_ref"),
            "clean_ticket_storage_hint": structured.get("clean_ticket_storage_hint"),
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
    return None


def _semantic_review_packet_result_text(structured: Mapping[str, Any]) -> str:
    required_submit_shape = structured.get("required_submit_shape")
    return (
        "Semantic review packet prepared by the KCS Authoring tool. "
        f"{SEMANTIC_CONTROL_GUIDANCE}\n\n"
        "Propose observation-only issue boundaries and explicit coverage "
        "records from selected_excerpts. Do not choose an operator action, "
        "KCS action, reuse result, readiness state, renderer output, or "
        "workflow state. Cover every allowed_source_ref with an issue "
        "observation or a valid non-issue coverage record. Except for summary, "
        "copy each observation text exactly from one referenced selected_excerpt; "
        "do not paraphrase. Do not draft an article or use legacy candidate "
        "fields.\n\n"
        "Call kcs_submit_semantic_review with this argument shape:\n"
        "```json\n"
        f"{_compact_json(required_submit_shape)}\n"
        "```\n\n"
        "Packet:\n"
        "```json\n"
        f"{_compact_json(structured)}\n"
        "```"
    )


def _pre_draft_tool_result_text(structured: Mapping[str, Any]) -> str | None:
    early_text = _early_pre_draft_tool_result_text(structured)
    if early_text is not None:
        return early_text
    if structured.get("result_kind") == "semantic_review_packet":
        return _semantic_review_packet_result_text(structured)
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
        "semantic_review_boundary_terminal",
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
    if _is_terminal_authoring_failure(structured):
        return _terminal_authoring_failure_tool_result_text(structured)
    return None


def _is_terminal_authoring_failure(structured: Mapping[str, Any]) -> bool:
    return (
        structured.get("result_kind") == "draft_article_authoring"
        and structured.get("ok") is False
        and structured.get("pipeline_ok") is False
        and structured.get("recommended_action") == "blocked"
        and structured.get("manual_draft_allowed") is False
        and structured.get("reviewer_bundle_written") is False
        and not structured.get("next_required_action")
        and structured.get("draft_generated") is not True
    )


def _terminal_authoring_failure_tool_result_text(
    structured: Mapping[str, Any],
) -> str:
    status = {
        "auto_publish_allowed": structured.get("auto_publish_allowed"),
        "blockers": structured.get("blockers"),
        "debug_code": structured.get("debug_code"),
        "draft_generated": structured.get("draft_generated"),
        "failure_stage": structured.get("failure_stage"),
        "manual_draft_allowed": structured.get("manual_draft_allowed"),
        "next_required_action": structured.get("next_required_action"),
        "pipeline_ok": structured.get("pipeline_ok"),
        "public_output_approved": structured.get("public_output_approved"),
        "ready_for_reviewer": structured.get("ready_for_reviewer"),
        "recommended_action": structured.get("recommended_action"),
        "result_kind": structured.get("result_kind"),
        "reviewer_bundle_written": structured.get("reviewer_bundle_written"),
    }
    return (
        "KCS article authoring reached a terminal blocked state. No "
        "reviewer-only draft was generated. No operator selection or further "
        "tool action was returned.\n\n"
        "Any semantic_item_outcomes in structuredContent are a diagnostic "
        "ledger only; they are not candidate options and do not authorize "
        "another tool call. Do not ask the operator to select an item, do not "
        "call another KCS tool, and do not draft manually. Stop and report the "
        "compact status for tool-side review.\n\n"
        "Compact status:\n"
        "```json\n"
        f"{_compact_json(status)}\n"
        "```"
    )


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
            "the clean ticket file was found but rejected by input/safety validation"
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
    correction_hint = ""
    correction = structured.get("semantic_submission_correction")
    if correction is not None:
        correction_text = _semantic_correction_text(
            correction,
            debug_code=structured.get("debug_code"),
        )
        correction_hint = f"\n\n{correction_text}"
    recovery_instruction = _semantic_review_recovery_instruction(
        correction,
        debug_code=structured.get("debug_code"),
    )
    status = {
        "auto_publish_allowed": structured.get("auto_publish_allowed"),
        "boundary_blocker_codes": structured.get("boundary_blocker_codes"),
        "boundary_blocker_count": structured.get("boundary_blocker_count"),
        "debug_code": structured.get("debug_code"),
        "draft_generated": structured.get("draft_generated"),
        "failure_stage": structured.get("failure_stage"),
        "manual_draft_allowed": structured.get("manual_draft_allowed"),
        "next_required_action": structured.get("next_required_action"),
        "public_output_approved": structured.get("public_output_approved"),
        "recommended_action": structured.get("recommended_action"),
        "result_kind": structured.get("result_kind"),
        "reviewer_bundle_written": structured.get("reviewer_bundle_written"),
        "terminal_cause_debug_code": structured.get("terminal_cause_debug_code"),
        "workflow_state": structured.get("workflow_state"),
        "writes_files": structured.get("writes_files"),
    }
    return (
        "KCS semantic review is blocked by the KCS Authoring tool. No "
        "reviewer-only draft was generated.\n\n"
        "Do not draft manually. Do not ask the operator to choose a recovery "
        "strategy. "
        f"{recovery_instruction} Do not restart or retry the same ticket_ref "
        "automatically "
        "unless the compact status explicitly asks for a restart. Re-register "
        "only when workflow_state is semantic_review_metadata_blocked.\n\n"
        f"{correction_hint}\n\n"
        "Compact status:\n"
        "```json\n"
        f"{_compact_json(status)}\n"
        "```"
    )


def _semantic_correction_text(value: object, *, debug_code: object) -> str:
    correction = _validated_semantic_correction(value, debug_code=debug_code)
    if correction.get("correction_kind") == "submit_shape":
        return _semantic_shape_correction_text(correction)
    field_name = correction["field_name"]
    accepted_values = correction["accepted_values"]
    retry_allowed = correction["retry_allowed"]
    if (
        not isinstance(field_name, str)
        or not isinstance(accepted_values, list)
        or not all(isinstance(item, str) for item in accepted_values)
        or not isinstance(retry_allowed, bool)
    ):
        raise ContractValidationError("semantic correction contract invalid")
    accepted_text = ", ".join(accepted_values)
    retry_text = str(retry_allowed).lower()
    text = (
        f"Submit enum correction: field {field_name} accepts: "
        f"{accepted_text}; retry_allowed={retry_text}."
    )
    return text


def _semantic_shape_correction_text(correction: Mapping[object, object]) -> str:
    field_name = correction.get("field_name")
    instruction = correction.get("instruction")
    retry_allowed = correction.get("retry_allowed")
    if (
        not isinstance(field_name, str)
        or not field_name
        or not isinstance(instruction, str)
        or not instruction
        or not isinstance(retry_allowed, bool)
    ):
        raise ContractValidationError("semantic correction contract invalid")
    retry_text = str(retry_allowed).lower()
    field_paths = correction.get("field_paths")
    field_path_text = (
        f" Correct every invalid field: {', '.join(field_paths)}."
        if isinstance(field_paths, list)
        else ""
    )
    return (
        f"Submit shape correction for {field_name}: {instruction} "
        f"retry_allowed={retry_text}.{field_path_text}"
    )


def _validated_semantic_correction(
    value: object,
    *,
    debug_code: object,
) -> JsonDict:
    if not isinstance(value, Mapping) or not isinstance(debug_code, str):
        raise ContractValidationError("semantic correction contract invalid")
    retry_allowed = value.get("retry_allowed")
    expected = semantic_submission_correction(debug_code)
    if expected is None or not isinstance(retry_allowed, bool):
        raise ContractValidationError("semantic correction contract invalid")
    expected["retry_allowed"] = retry_allowed
    field_paths = value.get("field_paths")
    if field_paths is not None:
        if (
            debug_code not in _SEMANTIC_FIELD_PATH_CORRECTION_CODES
            or not isinstance(field_paths, list)
            or not field_paths
            or len(field_paths) > 45
            or len(field_paths) != len(set(field_paths))
            or any(
                not isinstance(field_path, str)
                or _SEMANTIC_OBSERVATION_FIELD_PATH_RE.fullmatch(field_path) is None
                for field_path in field_paths
            )
        ):
            raise ContractValidationError("semantic correction contract invalid")
        expected["field_paths"] = list(field_paths)
    if dict(value) != expected:
        raise ContractValidationError("semantic correction contract invalid")
    return expected


def _semantic_review_recovery_instruction(
    correction: object,
    *,
    debug_code: object,
) -> str:
    if debug_code in {
        "semantic_review_expired",
        "semantic_review_unavailable",
    }:
        return (
            "Semantic review state is unavailable; stop and report the compact status."
        )
    if isinstance(correction, Mapping):
        if correction.get("retry_allowed") is True:
            return (
                "Retry kcs_submit_semantic_review once with the same "
                "semantic_review_ref and the corrected semantic_issue_proposal."
            )
        return "The correction retry is exhausted; stop and report the compact status."
    return "No bounded correction is available; stop and report the compact status."


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
    boundary_correction = structured.get("operator_boundary_correction")
    options = (
        choice_request.get("options") if isinstance(choice_request, Mapping) else None
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
        "operator_boundary_correction": boundary_correction,
        "recommended_action": structured.get("recommended_action"),
        "result_kind": structured.get("result_kind"),
        "semantic_item_outcomes": structured.get("semantic_item_outcomes"),
    }
    options_text = (
        "\n".join(option_lines) if option_lines else "No safe options returned."
    )
    outcome_text = _semantic_item_outcome_text(structured.get("semantic_item_outcomes"))
    boundary_correction_text = (
        "If the operator says this list missed an issue or merged separate "
        "problems, do not ask them for schema fields or source refs. Build one "
        "complete amended semantic_issue_proposal from the same prepared "
        "excerpts, then call kcs_submit_semantic_review once with that proposal, "
        "the returned semantic_review_ref, and operator_selection_ref. Treat "
        "the operator's prose only as steering context; do not copy it into "
        "evidence. Wait for the revised native selection before any draft or "
        "reuse action. "
        if isinstance(boundary_correction, Mapping)
        and boundary_correction.get("available") is True
        else "Do not call kcs_submit_semantic_review again for this choice. "
    )
    return (
        "Multiple KCS article candidates were detected. Operator selection is "
        "required before drafting. Selection eligibility does not mean a "
        "candidate is ready to draft, KCS-ready, or ready for reviewer handoff; "
        "those states are determined only by the later Python authoring result.\n\n"
        "Use the native choice popup when Claude Desktop provides one. "
        "Do not answer with a prose-only candidate list. If no popup is "
        "available, show these options. For one selected item, call "
        "kcs_draft_article with exactly that option's submit_arguments. If the "
        "operator answers 'both' or 'all', use the native All candidates "
        "option and call kcs_draft_article once with exactly its nested "
        "submit_arguments. Python owns the sequential batch; "
        "do not call each option independently. "
        f"{boundary_correction_text}Do not "
        "draft manually.\n\n"
        f"{outcome_text}"
        "Candidate options:\n"
        f"{options_text}\n\n"
        "Compact status:\n"
        "```json\n"
        f"{_compact_json(status)}\n"
        "```"
    )


def _semantic_item_outcome_text(value: object) -> str:
    if not isinstance(value, list) or not value:
        return ""
    lines = ["All identified KCS items and outcomes:"]
    for index, item in enumerate(value, start=1):
        if not isinstance(item, Mapping):
            continue
        title = str(item.get("title") or item.get("item_ref") or f"Item {index}")
        outcome = str(item.get("outcome") or item.get("kcs_item_status") or "unknown")
        lines.append(f"{index}. {title} — {outcome}")
    if len(lines) == 1:
        return ""
    return "\n".join(lines) + "\n\n"


def _tool_result_payload_for_generic_safety(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            key: (
                "accepted-public-comparison-evidence"
                if (
                    (
                        key == "comparison_candidates"
                        and value.get("result_kind") == "reuse_comparison_required"
                    )
                    or (
                        key == "selected_reuse_match"
                        and value.get("result_kind") == "reuse_comparison_completed"
                    )
                )
                else
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
    if any(fragment in compact for fragment in _RESULT_FORBIDDEN_COMPACT_FRAGMENTS):
        raise ContractValidationError("MCP tool result contains unsafe value")
    for url in _HTML_URL_RE.findall(value):
        if url not in _APPROVED_HTML_URL_REFS:
            raise ContractValidationError("MCP tool result contains unsafe value")


def _ensure_no_forbidden_tool_result_text(value: str) -> None:
    normalized = value.casefold()
    compact = normalized.replace("_", "").replace("-", "")
    if any(fragment in normalized for fragment in _RESULT_FORBIDDEN_FRAGMENTS):
        raise ContractValidationError("MCP tool result contains unsafe value")
    if any(fragment in compact for fragment in _RESULT_FORBIDDEN_COMPACT_FRAGMENTS):
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
