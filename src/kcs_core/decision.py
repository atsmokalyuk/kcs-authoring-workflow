"""Deterministic KCS action recommendation for accepted evidence packets."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import StrEnum
from typing import Any

from kcs_core.models import (
    ArticleType,
    KcsActionDecisionPacket,
    NormalizedTicketEvidencePacket,
    RecommendedAction,
    ReuseSearchResultsPacket,
)
from kcs_core.validation import (
    EvidenceBlocker,
    validate_evidence_packet,
)


class DecisionBlocker(StrEnum):
    """Value-free KCS decision blocker codes."""

    POSSIBLE_DUPLICATE_NOT_CHECKED = "possible_duplicate_not_checked"
    REUSE_SEARCH_STATUS_MISSING = "reuse_search_status_missing"
    INTERNAL_ONLY_SOLUTION = "internal_only_solution"
    NO_CUSTOMER_REPORTED_ISSUE = "no_customer_reported_issue"
    KCS_NOT_APPLICABLE = "kcs_not_applicable"
    NO_SUPPORTED_ANSWER = "no_supported_answer"
    CUSTOMER_SPECIFIC = "customer_specific"
    THIRD_PARTY_ONLY = "third_party_only"
    THIRD_PARTY_GENERIC = "third_party_generic"
    UNSUPPORTED_PUBLIC_ARTICLE = "unsupported_public_article"


CONFIDENCE_BY_ACTION = {
    RecommendedAction.REUSE_EXISTING: 0.9,
    RecommendedAction.UPDATE_EXISTING: 0.8,
    RecommendedAction.CREATE_CANDIDATE: 0.6,
    RecommendedAction.FLAG_EXISTING: 0.5,
    RecommendedAction.SPLIT_REQUIRED: 0.5,
    RecommendedAction.NO_ARTICLE: 0.4,
    RecommendedAction.BLOCKED: 0.0,
}


def decide_kcs_action(
    evidence: NormalizedTicketEvidencePacket,
    reuse_results: ReuseSearchResultsPacket,
) -> KcsActionDecisionPacket:
    """Return a deterministic KCS action decision packet."""

    candidate = _first_candidate(evidence)
    validation_blockers = validate_evidence_packet(evidence).blockers
    if _should_split_candidates(evidence, validation_blockers):
        return _split_required_packet(evidence, reuse_results, validation_blockers)
    validation_decision = _decision_for_validation_blockers(
        evidence, candidate, validation_blockers
    )
    if validation_decision is not None:
        return validation_decision
    if not reuse_results.searched:
        return _packet(
            evidence=evidence,
            candidate=candidate,
            action=RecommendedAction.BLOCKED,
            article_type=ArticleType.NONE,
            blockers=[
                DecisionBlocker.POSSIBLE_DUPLICATE_NOT_CHECKED.value,
                *reuse_results.blockers,
            ],
        )
    if reuse_results.blockers:
        return _packet(
            evidence=evidence,
            candidate=candidate,
            action=RecommendedAction.BLOCKED,
            article_type=ArticleType.NONE,
            blockers=reuse_results.blockers,
        )
    return _decision_for_ready_evidence(
        evidence,
        candidate,
        _matches_for_candidate(reuse_results.matches, candidate),
    )


def _decision_for_validation_blockers(
    evidence: NormalizedTicketEvidencePacket,
    candidate: Mapping[str, Any],
    blockers: tuple[str, ...],
) -> KcsActionDecisionPacket | None:
    if not blockers:
        return None
    action = RecommendedAction.BLOCKED
    if EvidenceBlocker.UNSAFE_INPUT.value not in blockers and any(
        blocker in blockers
        for blocker in (
            EvidenceBlocker.MULTI_ISSUE.value,
            EvidenceBlocker.EVIDENCE_NOT_ATOMIC.value,
        )
    ):
        action = RecommendedAction.SPLIT_REQUIRED
    return _packet(
        evidence=evidence,
        candidate=candidate,
        action=action,
        article_type=ArticleType.NONE,
        blockers=blockers,
    )


def _decision_for_ready_evidence(
    evidence: NormalizedTicketEvidencePacket,
    candidate: Mapping[str, Any],
    matches: list[dict[str, Any]],
) -> KcsActionDecisionPacket:
    article_type = _article_type(evidence, candidate)
    no_article_blocker = _no_article_blocker(candidate)
    if no_article_blocker is not None:
        return _packet(
            evidence,
            candidate,
            RecommendedAction.NO_ARTICLE,
            article_type,
            blockers=[no_article_blocker],
        )
    if _has_internal_only_solution(evidence, candidate):
        return _packet(
            evidence=evidence,
            candidate=candidate,
            action=RecommendedAction.BLOCKED,
            article_type=article_type,
            blockers=[DecisionBlocker.INTERNAL_ONLY_SOLUTION.value],
        )
    match = _select_match(evidence, candidate, article_type, matches)
    if match is not None:
        return _packet(
            evidence=evidence,
            candidate=candidate,
            action=_action_for_match(match),
            article_type=article_type,
            selected_match=_selected_match(match),
        )
    return _packet(
        evidence,
        candidate,
        RecommendedAction.CREATE_CANDIDATE,
        article_type,
    )


def _packet(
    evidence: NormalizedTicketEvidencePacket,
    candidate: Mapping[str, Any],
    action: RecommendedAction,
    article_type: ArticleType,
    blockers: Iterable[str] = (),
    selected_match: dict[str, Any] | None = None,
) -> KcsActionDecisionPacket:
    return KcsActionDecisionPacket(
        candidate_id=_candidate_id(evidence, candidate),
        recommended_action=action.value,
        article_type=article_type.value,
        confidence=CONFIDENCE_BY_ACTION[action],
        blockers=list(_dedupe(blockers)),
        evidence_basis=_evidence_basis(evidence, article_type),
        selected_reuse_match=selected_match,
        split_items=[],
        auto_publish_allowed=False,
    )


def _split_required_packet(
    evidence: NormalizedTicketEvidencePacket,
    reuse_results: ReuseSearchResultsPacket,
    blockers: tuple[str, ...],
) -> KcsActionDecisionPacket:
    return KcsActionDecisionPacket(
        candidate_id=evidence.case_ref,
        recommended_action=RecommendedAction.SPLIT_REQUIRED.value,
        article_type=ArticleType.NONE.value,
        confidence=CONFIDENCE_BY_ACTION[RecommendedAction.SPLIT_REQUIRED],
        blockers=list(_dedupe(_split_required_blockers(blockers))),
        evidence_basis=_evidence_basis(evidence, ArticleType.NONE),
        selected_reuse_match=None,
        split_items=[
            _split_item(evidence, candidate, index, reuse_results, blockers)
            for index, candidate in enumerate(evidence.issue_candidates)
        ],
        auto_publish_allowed=False,
    )


def _split_required_blockers(blockers: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        blocker
        for blocker in blockers
        if blocker
        in {
            EvidenceBlocker.MULTI_ISSUE.value,
            EvidenceBlocker.EVIDENCE_NOT_ATOMIC.value,
        }
    )


def _split_item(
    evidence: NormalizedTicketEvidencePacket,
    candidate: Mapping[str, Any],
    candidate_index: int,
    reuse_results: ReuseSearchResultsPacket,
    root_blockers: tuple[str, ...],
) -> dict[str, object]:
    item_evidence = _candidate_evidence(evidence, candidate)
    item_candidate_id = _candidate_id(evidence, candidate, candidate_index)
    item_reuse_status = _reuse_search_status(candidate, reuse_results)
    item_reuse_matches = _matches_for_candidate(reuse_results.matches, candidate)
    item_decision = _decision_for_split_item(
        item_evidence,
        candidate,
        root_blockers,
        item_reuse_status,
        item_reuse_matches,
        reuse_results.blockers,
    )
    return {
        "candidate_id": item_candidate_id,
        "summary": _summary_for_split_item(candidate, item_decision.blockers),
        "recommended_action": item_decision.recommended_action,
        "article_type": item_decision.article_type,
        "confidence": item_decision.confidence,
        "blockers": list(item_decision.blockers),
        "evidence_basis": dict(item_decision.evidence_basis),
        "selected_reuse_match": (
            dict(item_decision.selected_reuse_match)
            if item_decision.selected_reuse_match is not None
            else None
        ),
        "reuse_search_status": item_reuse_status,
    }


def _decision_for_split_item(
    item_evidence: NormalizedTicketEvidencePacket,
    candidate: Mapping[str, Any],
    root_blockers: tuple[str, ...],
    reuse_search_status: str,
    matches: list[dict[str, Any]],
    reuse_blockers: list[str],
) -> KcsActionDecisionPacket:
    article_type = _article_type(item_evidence, candidate)
    validation_blockers = validate_evidence_packet(item_evidence).blockers
    blocking_root_findings = _split_item_root_blockers(root_blockers)
    if blocking_root_findings:
        return _packet(
            item_evidence,
            candidate,
            RecommendedAction.BLOCKED,
            article_type,
            blockers=blocking_root_findings,
        )
    no_article_blocker = _no_article_blocker(candidate)
    if (
        no_article_blocker is not None
        and EvidenceBlocker.UNSAFE_INPUT.value not in validation_blockers
    ):
        return _packet(
            item_evidence,
            candidate,
            RecommendedAction.NO_ARTICLE,
            article_type,
            blockers=[no_article_blocker],
        )
    if validation_blockers:
        return _packet(
            item_evidence,
            candidate,
            RecommendedAction.BLOCKED,
            article_type,
            blockers=validation_blockers,
        )
    if _has_internal_only_solution(item_evidence, candidate):
        return _packet(
            item_evidence,
            candidate,
            RecommendedAction.BLOCKED,
            article_type,
            blockers=[DecisionBlocker.INTERNAL_ONLY_SOLUTION.value],
        )
    if reuse_search_status != "checked":
        return _packet(
            item_evidence,
            candidate,
            RecommendedAction.BLOCKED,
            ArticleType.NONE,
            blockers=[
                DecisionBlocker.REUSE_SEARCH_STATUS_MISSING.value,
                *reuse_blockers,
            ],
        )
    if reuse_blockers:
        return _packet(
            item_evidence,
            candidate,
            RecommendedAction.BLOCKED,
            ArticleType.NONE,
            blockers=reuse_blockers,
        )
    return _decision_for_ready_evidence(item_evidence, candidate, matches)


def _select_match(
    evidence: NormalizedTicketEvidencePacket,
    candidate: Mapping[str, Any],
    article_type: ArticleType,
    matches: list[dict[str, Any]],
) -> dict[str, Any] | None:
    same_identity = [
        match
        for match in matches
        if _article_type_value(match) == article_type.value
        and _identity_matches(evidence, candidate, article_type, match)
    ]
    exact = _first_with_status(same_identity, {"complete", "incomplete", "outdated"})
    if exact is not None:
        return exact
    return _first_with_status(same_identity, {"incorrect"})


def _action_for_match(match: Mapping[str, Any]) -> RecommendedAction:
    status = _string_value(match, "content_status")
    if status == "complete":
        return RecommendedAction.REUSE_EXISTING
    if status in {"incomplete", "outdated"}:
        return RecommendedAction.UPDATE_EXISTING
    if status == "incorrect":
        return RecommendedAction.FLAG_EXISTING
    return RecommendedAction.CREATE_CANDIDATE


def _identity_matches(
    evidence: NormalizedTicketEvidencePacket,
    candidate: Mapping[str, Any],
    article_type: ArticleType,
    match: Mapping[str, Any],
) -> bool:
    identity = match.get("identity")
    if not isinstance(identity, Mapping):
        return False
    if article_type == ArticleType.TECHNICAL_SCR:
        return _same_text(
            identity.get("cause"), evidence.supported_cause
        ) and _same_text(
            identity.get("resolution_or_answer"),
            evidence.supported_resolution_or_workaround,
        )
    if article_type == ArticleType.HOWTO_QA:
        return _same_text(
            identity.get("question"), _question(candidate)
        ) and _same_text(
            identity.get("resolution_or_answer"),
            evidence.supported_resolution_or_workaround,
        )
    return False


def _article_type(
    evidence: NormalizedTicketEvidencePacket, candidate: Mapping[str, Any]
) -> ArticleType:
    article_type = _string_value(candidate, "article_type")
    if article_type:
        try:
            return ArticleType(article_type)
        except ValueError:
            return ArticleType.NONE
    if _has_text(evidence.supported_cause):
        return ArticleType.TECHNICAL_SCR
    if _has_text(_question(candidate)):
        return ArticleType.HOWTO_QA
    return ArticleType.NONE


def _no_article_blocker(candidate: Mapping[str, Any]) -> str | None:
    checks = (
        (
            candidate.get("customer_reported") is False,
            DecisionBlocker.NO_CUSTOMER_REPORTED_ISSUE,
        ),
        (candidate.get("kcs_applicable") is False, DecisionBlocker.KCS_NOT_APPLICABLE),
        (
            candidate.get("resolution_state")
            in {"unsolved", "unanswered", "unsupported"},
            DecisionBlocker.NO_SUPPORTED_ANSWER,
        ),
        (candidate.get("customer_specific") is True, DecisionBlocker.CUSTOMER_SPECIFIC),
        (candidate.get("third_party_only") is True, DecisionBlocker.THIRD_PARTY_ONLY),
        (
            candidate.get("third_party_generic") is True,
            DecisionBlocker.THIRD_PARTY_GENERIC,
        ),
        (
            candidate.get("unsupported_public_article") is True,
            DecisionBlocker.UNSUPPORTED_PUBLIC_ARTICLE,
        ),
    )
    for condition, blocker in checks:
        if condition:
            return blocker.value
    return None


def _should_split_candidates(
    evidence: NormalizedTicketEvidencePacket, blockers: tuple[str, ...]
) -> bool:
    return (
        len(evidence.issue_candidates) > 1
        and EvidenceBlocker.MULTI_ISSUE.value in blockers
        and EvidenceBlocker.UNSAFE_INPUT.value not in blockers
    )


def _has_internal_only_solution(
    evidence: NormalizedTicketEvidencePacket, candidate: Mapping[str, Any]
) -> bool:
    classes = evidence.visibility_summary.get(
        "classes", evidence.visibility_summary.get("visibility_classes", ())
    )
    if isinstance(classes, str):
        classes = (classes,)
    if candidate.get("public_solution_safe") is False:
        return True
    return "internal_reviewer_only" in classes


def _evidence_basis(
    evidence: NormalizedTicketEvidencePacket, article_type: ArticleType
) -> dict[str, object]:
    return {
        "case_ref": evidence.case_ref,
        "source_refs": list(evidence.source_refs),
        "article_type": article_type.value,
        "identity_rule": _identity_rule(article_type),
    }


def _identity_rule(article_type: ArticleType) -> str:
    if article_type == ArticleType.TECHNICAL_SCR:
        return "article_type_cause_resolution"
    if article_type == ArticleType.HOWTO_QA:
        return "question_answer"
    return "none"


def _selected_match(match: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "match_ref": match.get("match_ref"),
        "article_type": match.get("article_type"),
        "content_status": match.get("content_status"),
    }


def _first_candidate(evidence: NormalizedTicketEvidencePacket) -> Mapping[str, Any]:
    if evidence.issue_candidates:
        return evidence.issue_candidates[0]
    return {}


def _candidate_id(
    evidence: NormalizedTicketEvidencePacket,
    candidate: Mapping[str, Any],
    candidate_index: int | None = None,
) -> str:
    value = candidate.get("candidate_id")
    if isinstance(value, str) and value:
        return value
    if candidate_index is not None:
        return f"{evidence.case_ref}:issue-{candidate_index + 1}"
    return evidence.case_ref


def _question(candidate: Mapping[str, Any]) -> str | None:
    value = candidate.get("question")
    return value if isinstance(value, str) else None


def _candidate_evidence(
    evidence: NormalizedTicketEvidencePacket, candidate: Mapping[str, Any]
) -> NormalizedTicketEvidencePacket:
    return NormalizedTicketEvidencePacket(
        case_ref=evidence.case_ref,
        input_class=evidence.input_class,
        source_refs=_candidate_string_list(candidate, "source_refs")
        or list(evidence.source_refs),
        issue_candidates=[dict(candidate)],
        environment=(
            _candidate_dict(candidate, "environment") or dict(evidence.environment)
        ),
        symptoms=_candidate_symptoms(evidence, candidate),
        confirmed_facts=_candidate_evidence_list(
            candidate, "confirmed_facts", evidence.confirmed_facts
        ),
        supported_cause=_candidate_evidence_string(
            candidate, "supported_cause", evidence.supported_cause
        ),
        supported_resolution_or_workaround=_candidate_resolution(evidence, candidate),
        open_questions=_candidate_string_list(candidate, "open_questions"),
        visibility_summary=dict(evidence.visibility_summary),
        sanitizer_report=dict(evidence.sanitizer_report),
    )


def _candidate_resolution(
    evidence: NormalizedTicketEvidencePacket, candidate: Mapping[str, Any]
) -> str | None:
    if "supported_resolution_or_workaround" in candidate:
        return _candidate_optional_string(
            candidate, "supported_resolution_or_workaround"
        )
    if "supported_answer" in candidate:
        return _candidate_optional_string(candidate, "supported_answer")
    return evidence.supported_resolution_or_workaround


def _candidate_symptoms(
    evidence: NormalizedTicketEvidencePacket, candidate: Mapping[str, Any]
) -> list[str]:
    if "symptoms" in candidate:
        return _candidate_string_list(candidate, "symptoms")
    return _summary_as_symptom(candidate) or list(evidence.symptoms)


def _candidate_evidence_list(
    candidate: Mapping[str, Any],
    key: str,
    fallback: list[str],
) -> list[str]:
    if key in candidate:
        return _candidate_string_list(candidate, key)
    return list(fallback)


def _candidate_evidence_string(
    candidate: Mapping[str, Any],
    key: str,
    fallback: str | None,
) -> str | None:
    if key in candidate:
        return _candidate_optional_string(candidate, key)
    return fallback


def _summary_as_symptom(candidate: Mapping[str, Any]) -> list[str]:
    summary = _candidate_optional_string(candidate, "summary")
    return [summary] if summary else []


def _candidate_optional_string(
    candidate: Mapping[str, Any], key: str
) -> str | None:
    value = candidate.get(key)
    if isinstance(value, str) and value.strip():
        return value
    return None


def _candidate_string_list(candidate: Mapping[str, Any], key: str) -> list[str]:
    value = candidate.get(key)
    if isinstance(value, str) and value.strip():
        return [value]
    if isinstance(value, list | tuple) and all(isinstance(item, str) for item in value):
        return [item for item in value if item.strip()]
    return []


def _candidate_dict(candidate: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = candidate.get(key)
    return dict(value) if isinstance(value, Mapping) else {}


def _matches_for_candidate(
    matches: list[dict[str, Any]], candidate: Mapping[str, Any]
) -> list[dict[str, Any]]:
    candidate_id = _candidate_optional_string(candidate, "candidate_id")
    if candidate_id is None:
        return [
            match
            for match in matches
            if not _has_text(_string_value(match, "candidate_id"))
        ]
    return [
        match
        for match in matches
        if _match_candidate_id(match) in {"", candidate_id}
    ]


def _match_candidate_id(match: Mapping[str, Any]) -> str:
    return _string_value(match, "candidate_id")


def _reuse_search_status(
    candidate: Mapping[str, Any], reuse_results: ReuseSearchResultsPacket
) -> str:
    if not reuse_results.searched:
        return "missing"
    explicit_status = _candidate_optional_string(candidate, "reuse_search_status")
    if explicit_status:
        return explicit_status
    if (
        candidate.get("reuse_checked") is True
        or _candidate_optional_string(candidate, "reuse_search_run_ref")
    ):
        return "checked"
    return "missing"


def _summary_for_split_item(
    candidate: Mapping[str, Any], blockers: list[str]
) -> str:
    if EvidenceBlocker.UNSAFE_INPUT.value in blockers:
        return ""
    return _candidate_optional_string(candidate, "summary") or ""


def _split_item_root_blockers(blockers: tuple[str, ...]) -> tuple[str, ...]:
    item_global_blockers = {
        EvidenceBlocker.OPEN_QUESTIONS_PRESENT.value,
    }
    return tuple(blocker for blocker in blockers if blocker in item_global_blockers)


def _article_type_value(match: Mapping[str, Any]) -> str:
    return _string_value(match, "article_type")


def _string_value(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    return item if isinstance(item, str) else ""


def _same_text(left: object, right: object) -> bool:
    if not isinstance(left, str) or not isinstance(right, str):
        return False
    return left.strip().casefold() == right.strip().casefold()


def _has_text(value: str | None) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _first_with_status(
    matches: Iterable[dict[str, Any]], statuses: set[str]
) -> dict[str, Any] | None:
    for match in matches:
        if _string_value(match, "content_status") in statuses:
            return match
    return None


def _dedupe(items: Iterable[str]) -> tuple[str, ...]:
    result: list[str] = []
    for item in items:
        if item not in result:
            result.append(item)
    return tuple(result)
