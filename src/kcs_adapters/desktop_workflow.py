"""Desktop-owned KCS draft workflow support.

This module intentionally keeps semantic extraction behind the core
``SemanticExtractionProvider`` contract. The production Desktop default is a
bounded local approved-summary provider that extracts only explicit facts from
sanitized operator-approved text.
"""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kcs_adapters import desktop_semantic_providers as _desktop_semantic_providers
from kcs_adapters.desktop_draft_output import (
    compact_draft_result,
    quality_blocked_result,
    quality_blocker_gaps,
)
from kcs_adapters.desktop_reviewer_bundle import write_desktop_reviewer_bundle
from kcs_adapters.desktop_semantic_candidates import (
    desktop_item_candidates_from_semantic_extraction,
)
from kcs_adapters.zendesk_markup_quality import review_reviewer_only_html
from kcs_core.claude_draft import build_claude_draft_request
from kcs_core.claude_handoff import (
    KcsClaudeHandoffRequestPacket,
    build_claude_handoff_request,
)
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict
from kcs_core.models import (
    ArticleType,
    DecisionStatus,
    KcsActionDecisionPacket,
    KcsReviewerPacket,
    KcsValidationReportPacket,
    NormalizedTicketEvidencePacket,
    ReadinessState,
    RecommendedAction,
)
from kcs_core.safety import SafetyGateResult
from kcs_core.sanitizer import (
    ensure_safe_sanitized_payload,
    normalize_optional_string,
)
from kcs_core.semantic_extraction import (
    SemanticExtractionProvider,
)
from kcs_core.validation import EvidenceValidationResult

SEMANTIC_PROVIDER_ENV = _desktop_semantic_providers.SEMANTIC_PROVIDER_ENV
SEMANTIC_PROVIDER_APPROVED_SUMMARY = (
    _desktop_semantic_providers.SEMANTIC_PROVIDER_APPROVED_SUMMARY
)
SEMANTIC_PROVIDER_FIXTURE = _desktop_semantic_providers.SEMANTIC_PROVIDER_FIXTURE
SEMANTIC_PROVIDER_APPROVED = _desktop_semantic_providers.SEMANTIC_PROVIDER_APPROVED
ApprovedSemanticExtractionClient = (
    _desktop_semantic_providers.ApprovedSemanticExtractionClient
)
ApprovedSemanticExtractionProvider = (
    _desktop_semantic_providers.ApprovedSemanticExtractionProvider
)
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

_DRAFT_SELECTION_REF_BYTES = 12


class OperatorSelectionUnavailableError(RuntimeError):
    """No pending operator selection exists."""


class OperatorSelectionExpiredError(RuntimeError):
    """Pending operator selection expired."""


class OperatorSelectionInvalidError(RuntimeError):
    """Operator selection refs do not match pending state."""


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


@dataclass(frozen=True)
class PendingDraftSelection:
    """Opaque pending operator selection state."""

    selection_ref: str
    approved_summary_text: str
    candidate_refs: tuple[str, ...]
    item_candidates: tuple[JsonDict, ...]
    item_candidate_cards: tuple[JsonDict, ...]
    expires_at: float


class DesktopDraftWorkflow:
    """Own Desktop draft provider calls and pending operator selection state."""

    def __init__(
        self,
        *,
        provider: SemanticExtractionProvider | None | object,
        selection_ttl_seconds: float,
    ) -> None:
        self._provider = provider
        self._selection_ttl_seconds = selection_ttl_seconds
        self._pending_selection: PendingDraftSelection | None = None

    @property
    def pending_selection(self) -> PendingDraftSelection | None:
        """Return current pending selection state, if any."""

        return self._pending_selection

    def clear_pending_selection(self) -> None:
        """Clear pending selection state after accepted continuation."""

        self._pending_selection = None

    def item_candidates_from_summary(
        self, approved_summary_text: str
    ) -> list[JsonDict]:
        """Call the semantic provider and return Desktop draft candidates."""

        provider = self._provider
        if provider is None:
            raise SemanticExtractionProviderUnavailableError
        provider_context = {
            "approved_summary_text": approved_summary_text,
            "request_kind": "desktop_draft_article",
        }
        ensure_safe_sanitized_payload(provider_context)
        extraction = provider.propose_candidates(provider_context)
        return desktop_item_candidates_from_semantic_extraction(extraction)

    def start_pending_selection(
        self,
        item_candidates: list[JsonDict],
        *,
        approved_summary_text: str,
    ) -> PendingDraftSelection:
        """Store split-required candidates for a deterministic second call."""

        self._pending_selection = new_pending_draft_selection(
            item_candidates,
            approved_summary_text=approved_summary_text,
            ttl_seconds=self._selection_ttl_seconds,
        )
        return self._pending_selection

    def selected_candidate(
        self,
        *,
        selection_ref: object,
        selected_item_ref: object,
    ) -> JsonDict:
        """Return selected candidate and clear state after a valid selection."""

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
        self._pending_selection = None
        return candidate


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
            "title_hint": hooks.title(arguments),
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


def approved_summary_draft_request_ready(
    handoff_request: KcsClaudeHandoffRequestPacket,
    item_ref: str,
    readiness: KcsValidationReportPacket,
) -> bool:
    """Return whether a Claude draft request can be built for this run."""

    if not readiness.ready_for_reviewer:
        return False
    try:
        build_claude_draft_request(handoff_request, draft_ref=f"draft-{item_ref}")
    except ContractValidationError:
        return False
    return True


def approved_summary_pipeline_status(
    execution: ApprovedSummaryExecution,
    *,
    schema_version: str,
    reuse_search_status: str,
) -> JsonDict:
    """Return compact status for an approved-summary pipeline execution."""

    decision = execution.decision
    readiness = execution.readiness
    safety = execution.safety
    evidence_validation = execution.evidence_validation
    return {
        "auto_publish_allowed": False,
        "case_ref": execution.evidence.case_ref,
        "checks": [
            {"kind": "input_validation", "ok": True},
            {"kind": "evidence_builder", "ok": True},
            {"kind": "input_safety", "ok": safety.ok},
            {"kind": "evidence_validation", "ok": evidence_validation.ok},
            {
                "kind": "decision",
                "ok": decision.status == DecisionStatus.DECISION_READY.value,
            },
            {"kind": "renderer", "ok": True},
            {"kind": "readiness", "ok": readiness.ready_for_reviewer},
            {"kind": "draft_request_ready", "ok": execution.draft_request_ready},
        ],
        "debug_code": "none",
        "draft_request_ready": execution.draft_request_ready,
        "evidence_valid": evidence_validation.ok,
        "failure_stage": "none",
        "handoff_ref": execution.handoff_request.handoff_ref,
        "input_safety_ok": safety.ok,
        "item_ref": execution.item_ref,
        "network_calls": False,
        "ok": safety.ok and readiness.ready_for_reviewer,
        "original_article_type": decision.article_type,
        "original_decision_status": decision.status,
        "original_readiness_state": readiness.state,
        "original_recommended_action": decision.recommended_action,
        "pipeline_ok": safety.ok and readiness.ready_for_reviewer,
        "provider_calls": False,
        "public_output_approved": False,
        "ready_for_real_ticket_use": False,
        "ready_for_reviewer": readiness.ready_for_reviewer,
        "result_kind": "approved_summary_pipeline",
        "reuse_search_status": reuse_search_status,
        "schema_version": schema_version,
        "validation_ok": evidence_validation.ok,
        "writes_files": False,
    }


def approved_summary_reviewer_only_draft(
    execution: ApprovedSummaryExecution,
) -> JsonDict:
    """Return compact reviewer-only draft sections for Desktop output."""

    candidate = approved_summary_public_candidate(execution.reviewer_packet)
    source_candidate = approved_summary_source_candidate(execution)
    resolution_steps = safe_candidate_list(candidate, "resolution_steps")
    return {
        "applicable_to": approved_summary_applicable_to(candidate),
        "cause": safe_candidate_string(candidate, "cause"),
        "resolution": safe_candidate_string(
            source_candidate, "supported_resolution_or_workaround"
        )
        or safe_candidate_string(source_candidate, "supported_answer")
        or safe_candidate_string(candidate, "resolution")
        or " ".join(resolution_steps),
        "resolution_steps": resolution_steps,
        "status": "reviewer_only",
        "symptoms": safe_candidate_list(candidate, "symptoms"),
        "title": safe_candidate_string(candidate, "title"),
    }


def approved_summary_reviewer_only_html(
    execution: ApprovedSummaryExecution,
) -> str:
    """Return reviewer-only Zendesk HTML from the reviewer packet."""

    html = execution.reviewer_packet.zendesk_source_html
    if not isinstance(html, str):
        return ""
    return html


def approved_summary_reviewer_only_preview(draft: Mapping[str, Any]) -> JsonDict:
    """Return structured preview fields for a reviewer-only draft."""

    return {
        "applicable_to": safe_candidate_list(draft, "applicable_to"),
        "cause": safe_candidate_string(draft, "cause"),
        "resolution": safe_candidate_string(draft, "resolution"),
        "resolution_steps": safe_candidate_list(draft, "resolution_steps"),
        "status": safe_candidate_string(draft, "status"),
        "symptoms": safe_candidate_list(draft, "symptoms"),
        "title": safe_candidate_string(draft, "title"),
    }


def approved_summary_reviewer_only_preview_text(
    draft: Mapping[str, Any],
) -> str:
    """Return plain-text reviewer preview for a reviewer-only draft."""

    preview = approved_summary_reviewer_only_preview(draft)
    lines = [
        f"Title: {preview['title']}",
        f"Status: {preview['status']}",
        "",
        "Applicable to:",
        *numbered_or_bulleted_lines(preview["applicable_to"], bullet="-"),
        "",
        "Symptoms:",
        *numbered_or_bulleted_lines(preview["symptoms"], bullet="1."),
        "",
        "Cause:",
        str(preview["cause"]),
        "",
        "Resolution:",
        str(preview["resolution"]),
        "",
        "Resolution steps:",
        *numbered_or_bulleted_lines(preview["resolution_steps"], bullet="1."),
    ]
    return "\n".join(line for line in lines if line is not None).strip()


def numbered_or_bulleted_lines(values: object, *, bullet: str) -> list[str]:
    """Return simple preview lines for list-like values."""

    if not isinstance(values, list) or not values:
        return ["-"]
    if bullet == "1.":
        return [f"{index}. {value}" for index, value in enumerate(values, start=1)]
    return [f"{bullet} {value}" for value in values]


def approved_summary_quality_gaps(
    execution: ApprovedSummaryExecution,
    draft: Mapping[str, Any],
) -> list[JsonDict]:
    """Return adapter-facing quality gaps for reviewer-only Desktop output."""

    gaps: list[JsonDict] = []
    is_howto = execution.decision.article_type == ArticleType.HOWTO_QA.value
    if not safe_candidate_list(draft, "applicable_to"):
        gaps.append({"kind": "missing_applicable_to", "severity": "blocker"})
    if not safe_candidate_list(draft, "symptoms"):
        gaps.append({"kind": "missing_symptoms", "severity": "blocker"})
    if not is_howto and not safe_candidate_string(draft, "cause"):
        gaps.append({"kind": "missing_cause", "severity": "blocker"})
    if not safe_candidate_string(draft, "resolution"):
        gaps.append({"kind": "missing_resolution", "severity": "blocker"})
    reference_text = approved_summary_reference_text(execution.arguments)
    if reference_text is None:
        gaps.append({"kind": "reference_not_provided", "severity": "info"})
    else:
        gaps.extend(approved_summary_reference_section_gaps(reference_text, draft))
    if not approved_summary_reuse_was_checked(execution.arguments):
        gaps.append({"kind": "reuse_search_skipped", "severity": "warning"})
    gaps.extend(approved_summary_html_quality_gaps(execution))
    return gaps


def approved_summary_html_quality_gaps(
    execution: ApprovedSummaryExecution,
) -> list[JsonDict]:
    """Return quality gaps from reviewer-only Zendesk HTML."""

    return review_reviewer_only_html(
        approved_summary_reviewer_only_html(execution),
        require_resolution_container=(
            execution.decision.article_type == ArticleType.TECHNICAL_SCR.value
        ),
    )


def approved_summary_reference_text(arguments: Mapping[str, Any]) -> str | None:
    """Return optional safe reference article text from authoring arguments."""

    reference_keys = (
        "reference_article",
        "reference_article_text",
        "reference_article_html",
    )
    for key in reference_keys:
        value = arguments.get(key)
        if isinstance(value, str) and value.strip():
            ensure_safe_sanitized_payload(value)
            return value.strip()
    return None


def approved_summary_reference_section_gaps(
    reference_text: str,
    draft: Mapping[str, Any],
) -> list[JsonDict]:
    """Return reference section coverage warnings for reviewer-only drafts."""

    gaps: list[JsonDict] = []
    reference = reference_text.casefold()
    section_checks = (
        (
            "applicable_to",
            "applicable to",
            safe_candidate_list(draft, "applicable_to"),
        ),
        ("symptoms", "symptoms", safe_candidate_list(draft, "symptoms")),
        ("cause", "cause", [safe_candidate_string(draft, "cause")]),
        ("resolution", "resolution", [safe_candidate_string(draft, "resolution")]),
    )
    for kind, marker, values in section_checks:
        if marker in reference and not any(values):
            gaps.append(
                {
                    "kind": f"reference_section_missing_{kind}",
                    "severity": "warning",
                }
            )
    if not gaps:
        gaps.append({"kind": "reference_section_coverage_ok", "severity": "info"})
    return gaps


def approved_summary_open_questions(
    execution: ApprovedSummaryExecution,
) -> list[str]:
    """Return safe open questions from the public candidate."""

    candidate = approved_summary_public_candidate(execution.reviewer_packet)
    return safe_candidate_list(candidate, "open_questions")


def approved_summary_public_candidate(packet: KcsReviewerPacket) -> JsonDict:
    """Return public article candidate as a JSON dict."""

    candidate = packet.public_article_candidate
    if not isinstance(candidate, Mapping):
        return {}
    return dict(candidate)


def approved_summary_applicable_to(candidate: Mapping[str, Any]) -> list[str]:
    """Return public Applicable To values, excluding internal refs."""

    values = safe_candidate_list(candidate, "applicable_to")
    return [
        value
        for value in values
        if not value.casefold().startswith("approved-summary-")
    ]


def approved_summary_source_candidate(
    execution: ApprovedSummaryExecution,
) -> JsonDict:
    """Return the source issue candidate from the approved-summary payload."""

    candidates = execution.payload.get("issue_candidates")
    if not isinstance(candidates, list) or not candidates:
        return {}
    candidate = candidates[0]
    if not isinstance(candidate, Mapping):
        return {}
    return dict(candidate)


def safe_candidate_string(candidate: Mapping[str, Any], key: str) -> str:
    """Return a string candidate field or empty string."""

    value = candidate.get(key)
    if isinstance(value, str):
        return value
    return ""


def safe_candidate_list(candidate: Mapping[str, Any], key: str) -> list[str]:
    """Return a normalized string list candidate field."""

    value = candidate.get(key)
    if isinstance(value, str) and value:
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item]
    return []


def approved_summary_reuse_was_checked(arguments: Mapping[str, Any]) -> bool:
    """Return whether the authoring request claims reuse search was checked."""

    reuse_checked = arguments.get("reuse_search_checked")
    item = arguments.get("item")
    if reuse_checked is None and isinstance(item, Mapping):
        reuse_checked = item.get("reuse_search_checked")
    return reuse_checked is True


def approved_summary_reuse_search_status(arguments: Mapping[str, Any]) -> str:
    """Return compact reuse search status for Desktop results."""

    return "checked" if approved_summary_reuse_was_checked(arguments) else "skipped"


def new_pending_draft_selection(
    item_candidates: list[JsonDict],
    *,
    approved_summary_text: str,
    ttl_seconds: float,
) -> PendingDraftSelection:
    """Create opaque in-memory selection state for one split-required result."""

    item_candidate_cards = split_candidate_cards(item_candidates)
    return PendingDraftSelection(
        selection_ref=(
            "operator-selection-"
            f"{secrets.token_urlsafe(_DRAFT_SELECTION_REF_BYTES)}"
        ),
        approved_summary_text=approved_summary_text,
        candidate_refs=tuple(
            candidate["item_ref"]
            for candidate in item_candidates
            if isinstance(candidate.get("item_ref"), str)
        ),
        item_candidates=tuple(dict(candidate) for candidate in item_candidates),
        item_candidate_cards=tuple(item_candidate_cards),
        expires_at=time.monotonic() + ttl_seconds,
    )


def split_candidate_cards(candidates: list[JsonDict]) -> list[JsonDict]:
    """Return compact operator-facing cards for split candidate choices."""

    cards: list[JsonDict] = []
    for index, candidate in enumerate(candidates, start=1):
        item_ref = candidate.get("item_ref")
        title = candidate.get("title")
        card: JsonDict = {
            "item_ref": (
                item_ref if isinstance(item_ref, str) and item_ref else f"item-{index}"
            ),
            "title": _safe_choice_text(title, fallback=f"Item {index}"),
        }
        article_type = candidate.get("article_type")
        if isinstance(article_type, str) and article_type:
            card["article_type"] = article_type
        ensure_safe_sanitized_payload(card)
        cards.append(card)
    return cards


def operator_choice_request(
    pending_selection: PendingDraftSelection,
    *,
    submit_tool: str,
) -> JsonDict:
    """Return deterministic operator choice request payload."""

    options = [
        {
            "label": str(candidate.get("title") or candidate["item_ref"]),
            "submit_arguments": {
                "operator_selected_item_ref": candidate["item_ref"],
                "operator_selection_ref": pending_selection.selection_ref,
            },
            "value": candidate["item_ref"],
        }
        for candidate in pending_selection.item_candidate_cards
    ]
    request: JsonDict = {
        "automatic_item_retry_allowed": False,
        "manual_draft_allowed": False,
        "mode": "single_select",
        "options": options,
        "presentation": "native_choice_popup_preferred",
        "prose_only_choice_allowed": False,
        "selection_ref": pending_selection.selection_ref,
        "submit_tool": submit_tool,
    }
    ensure_safe_sanitized_payload(request)
    return request


def operator_choice_review_summary(
    pending_selection: PendingDraftSelection,
) -> JsonDict:
    """Return compact review summary for a pending operator choice."""

    return {
        "mode": "single_select",
        "option_count": len(pending_selection.item_candidate_cards),
        "presentation": "native_choice_popup_preferred",
        "prose_only_choice_allowed": False,
        "selection_ref": pending_selection.selection_ref,
    }


def semantic_provider_unavailable_result(*, schema_version: str) -> JsonDict:
    """Return controlled result when no approved semantic provider is configured."""

    result = draft_author_failure_result(
        failure_stage="semantic_extraction",
        debug_code="semantic_extraction_provider_unavailable",
        schema_version=schema_version,
    )
    result["next_required_action"] = "configure_semantic_extraction_provider"
    result["review_summary"] = {
        "draft_available": False,
        "next_required_action": "configure_semantic_extraction_provider",
        "reason": "semantic_extraction_provider_unavailable",
    }
    return result


def operator_selection_unavailable_result(*, schema_version: str) -> JsonDict:
    """Return controlled result when a second call has no pending state."""

    result = draft_author_failure_result(
        failure_stage="operator_selection",
        debug_code="operator_selection_invalid",
        schema_version=schema_version,
    )
    result["next_required_action"] = "restart_with_approved_summary_text"
    result["review_summary"] = {
        "draft_available": False,
        "next_required_action": "restart_with_approved_summary_text",
        "reason": "operator_selection_invalid",
    }
    return result


def operator_selection_expired_result(*, schema_version: str) -> JsonDict:
    """Return controlled result when pending operator selection expired."""

    result = draft_author_failure_result(
        failure_stage="operator_selection",
        debug_code="operator_selection_expired",
        schema_version=schema_version,
    )
    result["next_required_action"] = "restart_with_approved_summary_text"
    result["review_summary"] = {
        "draft_available": False,
        "next_required_action": "restart_with_approved_summary_text",
        "reason": "operator_selection_expired",
    }
    return result


def attach_pending_selection(
    result: JsonDict,
    pending_selection: PendingDraftSelection,
    *,
    submit_tool: str,
) -> None:
    """Attach deterministic pending selection refs and choice request."""

    result["item_candidates"] = list(pending_selection.item_candidate_cards)
    result["operator_choice_options"] = list(pending_selection.item_candidate_cards)
    result["operator_choice_request"] = operator_choice_request(
        pending_selection,
        submit_tool=submit_tool,
    )
    result["operator_selection_ref"] = pending_selection.selection_ref
    result["operator_choice_confirmed"] = False
    result["review_summary"]["operator_selection_ref"] = pending_selection.selection_ref
    result["review_summary"]["operator_choice_request"] = (
        operator_choice_review_summary(pending_selection)
    )


def selection_error_result(
    arguments: Mapping[str, Any],
    pending_selection: PendingDraftSelection,
    *,
    schema_version: str,
    submit_tool: str,
) -> JsonDict | None:
    """Return split selection error result, or None when selection is confirmed."""

    selection_ref = arguments.get("operator_selection_ref")
    selected_item_ref = arguments.get("operator_selected_item_ref")
    choice_confirmed = arguments.get("operator_choice_confirmed")
    if (
        selection_ref == pending_selection.selection_ref
        and selected_item_ref in pending_selection.candidate_refs
        and choice_confirmed is True
    ):
        return None

    debug_code = "operator_selection_required"
    if selection_ref or selected_item_ref or choice_confirmed is not None:
        debug_code = "operator_selection_invalid"
    result = draft_author_failure_result(
        failure_stage="operator_selection",
        debug_code=debug_code,
        schema_version=schema_version,
    )
    result["automatic_item_retry_allowed"] = False
    result["item_candidates"] = list(pending_selection.item_candidate_cards)
    result["manual_draft_allowed"] = False
    result["next_required_action"] = "operator_select_single_item"
    result["operator_choice_options"] = list(pending_selection.item_candidate_cards)
    result["operator_choice_request"] = operator_choice_request(
        pending_selection,
        submit_tool=submit_tool,
    )
    result["operator_choice_confirmed"] = False
    result["operator_prompt"] = (
        "The approved sanitized ticket contains multiple separately searchable "
        "KCS items. Choose one item in the native choice popup before drafting."
    )
    result["operator_prompt_style"] = "native_choice_popup"
    result["operator_selection_ref"] = pending_selection.selection_ref
    result["recommended_action"] = "split_required"
    result["review_summary"] = {
        "draft_available": False,
        "next_required_action": "operator_select_single_item",
        "operator_prompt_style": "native_choice_popup",
        "operator_choice_request": operator_choice_review_summary(pending_selection),
        "operator_selection_ref": pending_selection.selection_ref,
        "reason": debug_code,
    }
    return result


def split_required_result(
    candidates: list[JsonDict],
    *,
    schema_version: str,
) -> JsonDict | None:
    """Return a split-required result for multiple KCS item candidates."""

    if len(candidates) <= 1:
        return None
    result = draft_author_failure_result(
        failure_stage="item_identification",
        debug_code="multiple_kcs_items_detected",
        schema_version=schema_version,
    )
    result["item_candidates"] = split_candidate_cards(candidates)
    result["automatic_item_retry_allowed"] = False
    result["manual_draft_allowed"] = False
    result["next_required_action"] = "operator_select_single_item"
    result["operator_choice_options"] = result["item_candidates"]
    result["operator_prompt"] = (
        "The approved sanitized ticket contains multiple separately searchable "
        "KCS items. Choose which article to draft first."
    )
    result["operator_prompt_style"] = "native_choice_popup"
    result["recommended_action"] = "split_required"
    result["review_summary"] = {
        "draft_available": False,
        "next_required_action": "operator_select_single_item",
        "operator_prompt_style": "native_choice_popup",
        "reason": "multiple_kcs_items_detected",
    }
    return result


def draft_author_failure_result(
    *,
    failure_stage: str,
    debug_code: str,
    schema_version: str,
) -> JsonDict:
    """Return a Desktop draft authoring failure result."""

    return {
        **_workflow_failure_result(
            failure_stage=failure_stage,
            debug_code=debug_code,
            schema_version=schema_version,
        ),
        "article_type": ArticleType.NONE.value,
        "atomic_item": {},
        "blockers": [debug_code],
        "open_questions": [],
        "quality_gaps": [],
        "recommended_action": "blocked",
        "result_kind": "approved_summary_authoring",
        "review_summary": {
            "draft_available": False,
            "reason": debug_code,
        },
        "should_be_kcs_article": False,
    }


def _workflow_failure_result(
    *,
    failure_stage: str,
    debug_code: str,
    schema_version: str,
) -> JsonDict:
    stage_order = {
        "input_validation": 0,
        "item_identification": 0,
        "operator_selection": 0,
        "semantic_extraction": 0,
        "evidence_builder": 1,
        "input_safety": 2,
        "evidence_validation": 3,
        "decision": 4,
        "renderer": 5,
        "readiness": 6,
        "draft_request_ready": 7,
    }
    failed_index = stage_order.get(failure_stage, len(stage_order))

    def stage_passed(stage: str) -> bool:
        return stage_order[stage] < failed_index

    return {
        "auto_publish_allowed": False,
        "case_ref": "approved-summary-case-001",
        "checks": [
            {"kind": "input_validation", "ok": stage_passed("input_validation")},
            {"kind": "evidence_builder", "ok": stage_passed("evidence_builder")},
            {"kind": "input_safety", "ok": stage_passed("input_safety")},
            {
                "kind": "evidence_validation",
                "ok": stage_passed("evidence_validation"),
            },
            {"kind": "decision", "ok": stage_passed("decision")},
            {"kind": "renderer", "ok": stage_passed("renderer")},
            {"kind": "readiness", "ok": stage_passed("readiness")},
            {
                "kind": "draft_request_ready",
                "ok": stage_passed("draft_request_ready"),
            },
        ],
        "debug_code": debug_code,
        "draft_request_ready": False,
        "evidence_valid": stage_passed("evidence_validation"),
        "failure_stage": failure_stage,
        "input_safety_ok": stage_passed("input_safety"),
        "network_calls": False,
        "ok": False,
        "original_article_type": ArticleType.NONE.value,
        "original_decision_status": DecisionStatus.BLOCKED.value,
        "original_readiness_state": ReadinessState.BLOCKED.value,
        "original_recommended_action": RecommendedAction.BLOCKED.value,
        "pipeline_ok": False,
        "provider_calls": False,
        "public_output_approved": False,
        "ready_for_real_ticket_use": False,
        "ready_for_reviewer": False,
        "result_kind": "approved_summary_pipeline",
        "schema_version": schema_version,
        "validation_ok": False,
        "writes_files": False,
    }


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
    if quality_blockers:
        return quality_blocked_result(
            result,
            quality_blockers,
            schema_version=schema_version,
        )
    try:
        bundle = write_desktop_reviewer_bundle(
            root=bundle_root,
            result=result,
            reviewer_only_html=html,
        )
    except OSError:
        return draft_author_failure_result(
            failure_stage="renderer",
            debug_code="reviewer_bundle_write_failed",
            schema_version=schema_version,
        )
    return compact_draft_result(
        result,
        bundle,
        include_reviewer_only_html=include_reviewer_only_html,
        reviewer_only_html=html,
    )


def selected_pending_candidate(
    pending_selection: PendingDraftSelection,
    selected_item_ref: object,
) -> JsonDict:
    """Return the selected pending candidate or raise a contract error."""

    for candidate in pending_selection.item_candidates:
        if candidate.get("item_ref") == selected_item_ref:
            return dict(candidate)
    raise ContractValidationError("operator selection invalid")


def _safe_choice_text(value: object, *, fallback: str) -> str:
    text = normalize_optional_string(value)
    if text is None:
        return fallback
    text = text[:140].strip()
    if not text:
        return fallback
    try:
        ensure_safe_sanitized_payload(text)
    except ContractValidationError:
        return fallback
    return text
