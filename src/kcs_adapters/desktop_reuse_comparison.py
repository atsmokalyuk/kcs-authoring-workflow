"""Desktop-owned pending reuse-comparison state and safe result helpers."""

from __future__ import annotations

import re
import secrets
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict
from kcs_core.models import RecommendedAction
from kcs_core.reuse_comparison import (
    PublicArticleReference,
    ReuseComparisonCandidate,
    ReuseComparisonEvidence,
    ReuseComparisonEvidenceProvider,
    ReuseComparisonEvidenceRequest,
    ensure_valid_reuse_comparison_evidence,
    is_reusable_kcs_article_url,
    request_from_symptoms,
)
from kcs_core.sanitizer import ensure_safe_sanitized_payload

REUSE_COMPARISON_OUTCOMES = (
    "reuse",
    "update",
    "none_fit",
    "need_more_evidence",
)
REUSE_COMPARISON_REF_BYTES = 12
REUSE_COMPARISON_MAX_ACCEPTED_FACTS = 8
REUSE_COMPARISON_MAX_FACT_BYTES = 1_000
REUSE_COMPARISON_MAX_TOTAL_FACT_BYTES = 6_000
REUSE_COMPARISON_MAX_QUERY_CHARS = 512

_PUBLIC_ARTICLE_URL_RE = re.compile(
    r"https://(?:support\.plesk\.com/hc/[A-Za-z-]+/articles/"
    r"|kb\.plesk\.com/[A-Za-z0-9/_-]*|docs\.plesk\.com/[A-Za-z0-9/_.-]*)"
    r"[^\s<>\"]*",
    re.I,
)
_CONFIRMED_OUTCOME_RE = re.compile(
    r"\b(?:using\s+|the\s+)?(?:article\s+|guide\s+|instructions?\s+|link\s+)?"
    r"public_article_url\s+"
    r"(?:(?:has|was)\s+)?(?:partially\s+)?"
    r"(?:fixed|helped|helpful|resolved|solved|worked)\b"
    r"(?:\s+(?:the\s+)?(?:issue|problem|error))?",
    re.I,
)
_NEGATIVE_OUTCOME_RE = re.compile(
    r"\b(?:"
    r"did\s+not|didn['’]t|does\s+not|doesn['’]t|failed\s+to|"
    r"not|never|no\s+longer|unhelpful|unsuccessful"
    r")\b.{0,32}\b(?:fix|help|resolve|work)\w*\b",
    re.I,
)
_OUTCOME_SCOPE_DISQUALIFIER_RE = re.compile(
    r"(?:"
    r"\b(?:a\s+)?(?:different|another|other)\s+"
    r"(?:issue|problem|case|customer|server)\b"
    r"|\bnot\s+(?:this|the\s+current)\s+(?:issue|problem|case|customer|server)\b"
    r"|\bonly\s+as\s+background\b"
    r"|\b(?:but|however)\b.{0,80}\b(?:separate|different|another)\s+"
    r"(?:workaround|solution|fix)\b"
    r")",
    re.I,
)
_FACT_FIELDS = (
    "summary",
    "question",
    "symptoms",
    "confirmed_facts",
    "supported_cause",
    "supported_resolution_or_workaround",
    "supported_answer",
    "resolution_steps",
)


class ReuseComparisonUnavailableError(RuntimeError):
    """No pending reuse comparison exists."""


class ReuseComparisonExpiredError(RuntimeError):
    """Pending reuse comparison expired."""


class ReuseComparisonInvalidError(RuntimeError):
    """Reuse comparison submit did not match pending state."""


@dataclass(frozen=True)
class PendingReuseComparison:
    """One bounded in-memory pre-draft comparison."""

    comparison_ref: str
    approved_summary_text: str
    approved_summary_source_kind: str | None
    issue_candidate: JsonDict
    evidence: ReuseComparisonEvidence
    selected_item_refs: tuple[str, ...]
    current_index: int
    selection_ref: str | None
    debug: bool
    completed_outcomes: tuple[JsonDict, ...]
    expires_at: float


@dataclass(frozen=True)
class ReuseComparisonSubmission:
    """Validated single-use operator outcome bound to pending state."""

    pending: PendingReuseComparison
    outcome: str
    selected_candidate: ReuseComparisonCandidate | None


def collect_pending_reuse_comparison(
    *,
    provider: ReuseComparisonEvidenceProvider,
    issue_candidate: Mapping[str, object],
    approved_summary_text: str,
    approved_summary_source_kind: str | None,
    selected_item_refs: Sequence[str],
    current_index: int,
    selection_ref: str | None,
    debug: bool,
    completed_outcomes: Sequence[Mapping[str, object]] = (),
    ttl_seconds: float,
) -> PendingReuseComparison | ReuseComparisonEvidence:
    """Collect provider evidence and create state only for a usable comparison."""

    request = request_from_symptoms(
        comparison_symptoms(issue_candidate),
        explicit_article=confirmed_helpful_public_article(
            issue_candidate,
            approved_summary_text=approved_summary_text,
        ),
    )
    try:
        evidence = provider.collect_comparison_evidence(request)
        ensure_valid_reuse_comparison_evidence(evidence)
    except ContractValidationError:
        return _provider_failure_evidence(
            request,
            status="comparison_provider_invalid_response",
        )
    except Exception:
        return _provider_failure_evidence(
            request,
            status="comparison_provider_unavailable",
        )
    if evidence.status != "comparison_evidence_ready":
        return evidence
    refs = tuple(selected_item_refs)
    if not refs or not 0 <= current_index < len(refs):
        raise ContractValidationError("reuse comparison selected item refs invalid")
    return PendingReuseComparison(
        comparison_ref=(
            "reuse-comparison-"
            f"{secrets.token_urlsafe(REUSE_COMPARISON_REF_BYTES)}"
        ),
        approved_summary_text=approved_summary_text,
        approved_summary_source_kind=approved_summary_source_kind,
        issue_candidate=dict(issue_candidate),
        evidence=evidence,
        selected_item_refs=refs,
        current_index=current_index,
        selection_ref=selection_ref,
        debug=debug,
        completed_outcomes=tuple(dict(item) for item in completed_outcomes),
        expires_at=time.monotonic() + ttl_seconds,
    )


def _provider_failure_evidence(
    request: ReuseComparisonEvidenceRequest,
    *,
    status: str,
) -> ReuseComparisonEvidence:
    explicit_article = request.explicit_article
    return ReuseComparisonEvidence(
        searched=False,
        status=status,
        search_run_ref="",
        explicit_reference_status=(
            "not_checked" if explicit_article is not None else "not_provided"
        ),
        explicit_article=explicit_article,
        blockers=(status,),
    )


def validate_reuse_comparison_submit(
    pending: PendingReuseComparison,
    *,
    comparison_ref: object,
    outcome: object,
    candidate_ref: object = None,
) -> ReuseComparisonSubmission:
    """Validate one closed-enum operator response without accepting evidence."""

    if comparison_ref != pending.comparison_ref:
        raise ReuseComparisonInvalidError
    if not isinstance(outcome, str) or outcome not in REUSE_COMPARISON_OUTCOMES:
        raise ReuseComparisonInvalidError
    candidate = _selected_comparison_candidate(
        pending.evidence.candidates,
        outcome=outcome,
        candidate_ref=candidate_ref,
    )
    return ReuseComparisonSubmission(pending, outcome, candidate)


def reuse_comparison_required_result(
    pending: PendingReuseComparison,
    *,
    schema_version: str,
    submit_tool: str,
) -> JsonDict:
    """Return bounded evidence and exact operator submit choices."""

    result: JsonDict = {
        "accepted_ticket_facts": accepted_ticket_facts(pending.issue_candidate),
        "auto_publish_allowed": False,
        "blockers": [],
        "comparison_candidates": comparison_candidate_cards(
            pending.evidence.candidates
        ),
        "comparison_outcomes": list(REUSE_COMPARISON_OUTCOMES),
        "comparison_ref": pending.comparison_ref,
        "draft_generated": False,
        "manual_draft_allowed": False,
        "network_calls": True,
        "next_required_action": "operator_confirm_reuse_comparison",
        "next_tool": submit_tool,
        "ok": True,
        "operator_choice_confirmed": False,
        "operator_prompt": (
            "Compare the accepted ticket facts with the cited public excerpts. "
            "Display every candidate title as a clickable public_url link and "
            "keep its candidate_ref visible. "
            "Present one concise coverage and missing-knowledge recommendation, "
            "then ask exactly one operator question using the allowed outcomes."
        ),
        "public_output_approved": False,
        "publishes": False,
        "result_kind": "reuse_comparison_required",
        "reviewer_bundle_written": False,
        "schema_version": schema_version,
        "submit_tool": submit_tool,
        "validation_ok": True,
        "writes_files": False,
    }
    # Candidate cards are accepted public evidence under the stricter
    # ReuseComparisonEvidence contract. Keep the generic private-data check on
    # every other field; it intentionally rejects public excerpts containing
    # identifiers that would be unsafe if they came from a ticket.
    ensure_safe_sanitized_payload(
        {key: value for key, value in result.items() if key != "comparison_candidates"}
    )
    return result


def reuse_comparison_blocked_result(
    evidence: ReuseComparisonEvidence,
    *,
    schema_version: str,
) -> JsonDict:
    """Return a value-safe terminal block when comparison cannot be shown."""

    return {
        "auto_publish_allowed": False,
        "blockers": list(evidence.blockers or (evidence.status,)),
        "debug_code": evidence.status,
        "draft_generated": False,
        "failure_stage": "reuse_comparison",
        "manual_draft_allowed": False,
        "network_calls": True,
        "next_required_action": "restart_reuse_comparison_after_provider_ready",
        "ok": False,
        "pipeline_ok": False,
        "public_output_approved": False,
        "publishes": False,
        "result_kind": "reuse_comparison_blocked",
        "reviewer_bundle_written": False,
        "schema_version": schema_version,
        "validation_ok": False,
        "writes_files": False,
    }


def reuse_comparison_terminal_result(
    submission: ReuseComparisonSubmission,
    *,
    schema_version: str,
) -> JsonDict:
    """Return a no-draft terminal result for reuse, update, or evidence stop."""

    action = comparison_outcome_action(submission.outcome)
    result: JsonDict = {
        "auto_publish_allowed": False,
        "blockers": (
            ["need_more_evidence"]
            if submission.outcome == "need_more_evidence"
            else []
        ),
        "comparison_outcome": submission.outcome,
        "draft_generated": False,
        "manual_draft_allowed": False,
        "network_calls": False,
        "ok": submission.outcome != "need_more_evidence",
        "pipeline_ok": submission.outcome != "need_more_evidence",
        "public_output_approved": False,
        "publishes": False,
        "recommended_action": action,
        "result_kind": "reuse_comparison_completed",
        "reviewer_bundle_written": False,
        "schema_version": schema_version,
        "validation_ok": submission.outcome != "need_more_evidence",
        "writes_files": False,
    }
    if submission.selected_candidate is not None:
        result["selected_reuse_match"] = comparison_candidate_card(
            submission.selected_candidate,
            submission.pending.evidence.candidates.index(
                submission.selected_candidate
            ),
            include_excerpts=False,
        )
    return result


def reuse_comparison_submit_failure_result(
    *,
    comparison_ref: str | None,
    correction_allowed: bool,
    debug_code: str,
    schema_version: str,
) -> JsonDict:
    """Return value-safe recovery guidance for an invalid comparison submit."""

    next_required_action = (
        "resubmit_pending_reuse_comparison"
        if debug_code == "reuse_comparison_invalid" and correction_allowed
        else "restart_reuse_comparison"
    )
    result: JsonDict = {
        "auto_publish_allowed": False,
        "blockers": [debug_code],
        "debug_code": debug_code,
        "draft_generated": False,
        "failure_stage": "reuse_comparison",
        "manual_draft_allowed": False,
        "network_calls": False,
        "next_required_action": next_required_action,
        "ok": False,
        "pipeline_ok": False,
        "public_output_approved": False,
        "publishes": False,
        "result_kind": "reuse_comparison_submit_failed",
        "reviewer_bundle_written": False,
        "schema_version": schema_version,
        "validation_ok": False,
        "writes_files": False,
    }
    if correction_allowed and comparison_ref is not None:
        result["comparison_outcomes"] = sorted(REUSE_COMPARISON_OUTCOMES)
        result["comparison_ref"] = comparison_ref
    return result


def comparison_outcome_action(outcome: str) -> str:
    actions = {
        "reuse": RecommendedAction.REUSE_EXISTING.value,
        "update": RecommendedAction.FLAG_EXISTING.value,
        "none_fit": RecommendedAction.CREATE_CANDIDATE.value,
        "need_more_evidence": RecommendedAction.BLOCKED.value,
    }
    try:
        return actions[outcome]
    except KeyError as exc:  # pragma: no cover - validated caller invariant
        raise ContractValidationError("reuse comparison outcome invalid") from exc


def comparison_candidate_cards(
    candidates: Sequence[ReuseComparisonCandidate],
) -> list[JsonDict]:
    return [
        comparison_candidate_card(candidate, index, include_excerpts=True)
        for index, candidate in enumerate(candidates)
    ]


def comparison_candidate_card(
    candidate: ReuseComparisonCandidate,
    index: int,
    *,
    include_excerpts: bool,
) -> JsonDict:
    card: JsonDict = {
        "article_status": candidate.article_status,
        "candidate_ref": f"comparison-candidate-{index + 1:03d}",
        "origin": candidate.origin,
        "public_url": candidate.public_url,
        "title": candidate.title,
        "updated_at": candidate.updated_at,
    }
    if include_excerpts:
        card["excerpts"] = [
            {
                "citation": excerpt.citation,
                "excerpt_ref": excerpt.excerpt_ref,
                "section_path": excerpt.section_path,
                "text": excerpt.text,
            }
            for excerpt in candidate.excerpts
        ]
    return card


def accepted_ticket_facts(candidate: Mapping[str, object]) -> list[str]:
    facts: list[str] = []
    total_bytes = 0
    for value in _candidate_text_values(candidate):
        text = value.strip()
        if not text or text in facts:
            continue
        size = len(text.encode("utf-8"))
        if size > REUSE_COMPARISON_MAX_FACT_BYTES:
            text = text.encode("utf-8")[:REUSE_COMPARISON_MAX_FACT_BYTES].decode(
                "utf-8", errors="ignore"
            ).strip()
            size = len(text.encode("utf-8"))
        if (
            not text
            or len(facts) >= REUSE_COMPARISON_MAX_ACCEPTED_FACTS
            or total_bytes + size > REUSE_COMPARISON_MAX_TOTAL_FACT_BYTES
        ):
            break
        ensure_safe_sanitized_payload(text)
        facts.append(text)
        total_bytes += size
    if not facts:
        raise ContractValidationError("reuse comparison accepted facts unavailable")
    return facts


def comparison_symptoms(candidate: Mapping[str, object]) -> tuple[str, ...]:
    values = _comparison_query_values(candidate)
    selected: list[str] = []
    total_chars = 0
    for value in values:
        separator_chars = len(selected)
        remaining = (
            REUSE_COMPARISON_MAX_QUERY_CHARS
            - total_chars
            - separator_chars
        )
        if remaining <= 0 or len(selected) >= 5:
            break
        bounded = value[:remaining].strip()
        if bounded:
            ensure_safe_sanitized_payload(bounded)
            selected.append(bounded)
            total_chars += len(bounded)
    if not selected:
        raise ContractValidationError("reuse comparison symptoms unavailable")
    return tuple(selected)


def _comparison_query_values(candidate: Mapping[str, object]) -> tuple[str, ...]:
    symptoms = _string_sequence(candidate.get("symptoms"))
    if symptoms:
        return symptoms
    for key in ("question", "summary"):
        value = candidate.get(key)
        if isinstance(value, str) and value.strip():
            return (value.strip(),)
    return ()


def confirmed_helpful_public_article(
    candidate: Mapping[str, object],
    *,
    approved_summary_text: str,
) -> PublicArticleReference | None:
    """Return exact priority only for a verbatim source-grounded outcome."""

    for text in _candidate_text_values(candidate):
        if text not in approved_summary_text:
            continue
        for match, public_url in _reusable_article_matches(text):
            start = max(0, match.start() - 180)
            end = min(len(text), match.end() + 180)
            context = text[start:end]
            if _NEGATIVE_OUTCOME_RE.search(
                context
            ) or _OUTCOME_SCOPE_DISQUALIFIER_RE.search(context):
                continue
            local_start = match.start() - start
            local_end = match.end() - start
            marked_context = (
                context[:local_start]
                + " PUBLIC_ARTICLE_URL "
                + context[local_end:]
            )
            if _CONFIRMED_OUTCOME_RE.search(marked_context):
                return PublicArticleReference(public_url=public_url)
    return None


def _reusable_article_matches(
    text: str,
) -> tuple[tuple[re.Match[str], str], ...]:
    matches: list[tuple[re.Match[str], str]] = []
    for match in _PUBLIC_ARTICLE_URL_RE.finditer(text):
        public_url = match.group(0).rstrip(".,;)")
        if is_reusable_kcs_article_url(public_url):
            matches.append((match, public_url))
    return tuple(matches)


def has_public_article_url(value: str) -> bool:
    """Return whether text contains an allowlisted public Plesk article URL."""

    return _PUBLIC_ARTICLE_URL_RE.search(value) is not None


def _selected_comparison_candidate(
    candidates: Sequence[ReuseComparisonCandidate],
    *,
    outcome: str,
    candidate_ref: object,
) -> ReuseComparisonCandidate | None:
    if outcome in {"none_fit", "need_more_evidence"}:
        if candidate_ref is not None and not _is_displayed_candidate_ref(
            candidates,
            candidate_ref,
        ):
            raise ReuseComparisonInvalidError
        return None
    if not isinstance(candidate_ref, str):
        raise ReuseComparisonInvalidError
    for index, candidate in enumerate(candidates):
        if candidate_ref == f"comparison-candidate-{index + 1:03d}":
            return candidate
    raise ReuseComparisonInvalidError


def _is_displayed_candidate_ref(
    candidates: Sequence[ReuseComparisonCandidate],
    candidate_ref: object,
) -> bool:
    return isinstance(candidate_ref, str) and any(
        candidate_ref == f"comparison-candidate-{index + 1:03d}"
        for index in range(len(candidates))
    )


def _candidate_text_values(candidate: Mapping[str, object]) -> tuple[str, ...]:
    values: list[str] = []
    for field in _FACT_FIELDS:
        value = candidate.get(field)
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, list):
            values.extend(item for item in value if isinstance(item, str))
    return tuple(values)


def _string_sequence(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not isinstance(value, list):
        return ()
    return tuple(
        item.strip()
        for item in value
        if isinstance(item, str) and item.strip()
    )


__all__ = [
    "PendingReuseComparison",
    "REUSE_COMPARISON_OUTCOMES",
    "ReuseComparisonExpiredError",
    "ReuseComparisonInvalidError",
    "ReuseComparisonSubmission",
    "ReuseComparisonUnavailableError",
    "accepted_ticket_facts",
    "collect_pending_reuse_comparison",
    "comparison_outcome_action",
    "confirmed_helpful_public_article",
    "has_public_article_url",
    "reuse_comparison_blocked_result",
    "reuse_comparison_required_result",
    "reuse_comparison_submit_failure_result",
    "reuse_comparison_terminal_result",
    "validate_reuse_comparison_submit",
]
