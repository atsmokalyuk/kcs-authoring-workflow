"""Validation report and ready-for-reviewer loop state for KCS-5."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable

from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import dumps_payload
from kcs_core.models import (
    DecisionStatus,
    KcsActionDecisionPacket,
    KcsReviewerPacket,
    KcsValidationReportPacket,
    NormalizedTicketEvidencePacket,
    ReadinessState,
    RecommendedAction,
    RequiredNextStep,
)
from kcs_core.validation import validate_evidence_packet

_ARTICLE_OUTPUT_ACTIONS = frozenset(
    {
        RecommendedAction.CREATE_CANDIDATE.value,
        RecommendedAction.UPDATE_EXISTING.value,
        RecommendedAction.FLAG_EXISTING.value,
    }
)
_REUSE_SEARCH_BLOCKERS = frozenset(
    {
        "possible_duplicate_not_checked",
        "reuse_search_status_missing",
    }
)
_SAFE_CODE_RE = re.compile(r"[a-z][a-z0-9_]*")
_MAX_CODE_LENGTH = 100
_UNSAFE_REPORT_CODE = "unsafe_report_code"


def build_validation_report(
    evidence: NormalizedTicketEvidencePacket,
    decision: KcsActionDecisionPacket,
    reviewer_packet: KcsReviewerPacket | None = None,
) -> KcsValidationReportPacket:
    """Return the deterministic KCS-5 validation report."""

    evidence_result = validate_evidence_packet(evidence)
    evidence_validation = evidence_result.to_json_dict()
    decision_summary = _decision_summary(decision)
    renderer_validation = _renderer_validation(reviewer_packet)
    checks = _base_checks(reviewer_packet)
    warnings = _safe_codes(evidence_result.warnings, "warnings")
    warnings.extend(_renderer_warnings(reviewer_packet))
    state, next_step, blockers = _readiness_outcome(
        evidence,
        decision,
        reviewer_packet,
        evidence_result.ok,
    )
    ok = state == ReadinessState.READY_FOR_REVIEWER
    return KcsValidationReportPacket(
        case_ref=evidence.case_ref,
        ok=ok,
        ready_for_reviewer=ok,
        state=state.value,
        required_next_step=next_step.value,
        checks=_safe_codes(checks, "checks"),
        blockers=_safe_codes(blockers, "blockers"),
        warnings=_safe_codes(warnings, "warnings"),
        evidence_validation=evidence_validation,
        decision_summary=decision_summary,
        renderer_validation=renderer_validation,
        reviewer_packet_sha256=_reviewer_packet_hash(reviewer_packet),
        zendesk_source_sha256=_zendesk_source_hash(reviewer_packet),
        auto_publish_allowed=False,
    )


def ensure_ready_for_reviewer(report: KcsValidationReportPacket) -> None:
    """Raise when the KCS-5 report is not ready for reviewer handoff."""

    if not report.ready_for_reviewer:
        raise ContractValidationError(
            f"KCS output is not ready for reviewer: {report.state}"
        )


def _readiness_outcome(
    evidence: NormalizedTicketEvidencePacket,
    decision: KcsActionDecisionPacket,
    reviewer_packet: KcsReviewerPacket | None,
    evidence_ok: bool,
) -> tuple[ReadinessState, RequiredNextStep, list[str]]:
    if decision.recommended_action == RecommendedAction.SPLIT_REQUIRED.value:
        return _split_required_outcome()
    if not evidence_ok:
        return (
            ReadinessState.BLOCKED,
            RequiredNextStep.FIX_EVIDENCE,
            _evidence_blockers(evidence),
        )
    if _decision_is_blocked(decision):
        return _blocked_decision_outcome(decision)
    if reviewer_packet is None:
        return _missing_reviewer_packet_outcome()
    blocked_review = _blocked_review_outcome(evidence, decision, reviewer_packet)
    if blocked_review is not None:
        return blocked_review
    if _draft_required(decision, reviewer_packet):
        return _draft_required_outcome()
    return (
        ReadinessState.READY_FOR_REVIEWER,
        RequiredNextStep.NONE,
        [],
    )


def _split_required_outcome() -> tuple[ReadinessState, RequiredNextStep, list[str]]:
    return (
        ReadinessState.REVIEW_BLOCKED,
        RequiredNextStep.REVIEW_SPLIT_ITEMS,
        ["split_required"],
    )


def _missing_reviewer_packet_outcome() -> tuple[
    ReadinessState, RequiredNextStep, list[str]
]:
    return (
        ReadinessState.DRAFT_REQUIRED,
        RequiredNextStep.RENDER_REVIEWER_PACKET,
        ["reviewer_packet_missing"],
    )


def _blocked_review_outcome(
    evidence: NormalizedTicketEvidencePacket,
    decision: KcsActionDecisionPacket,
    reviewer_packet: KcsReviewerPacket,
) -> tuple[ReadinessState, RequiredNextStep, list[str]] | None:
    blockers = _reviewer_packet_mismatch_blockers(evidence, decision, reviewer_packet)
    blockers.extend(_renderer_blockers(reviewer_packet))
    if not blockers:
        return None
    return (
        ReadinessState.REVIEW_BLOCKED,
        RequiredNextStep.FIX_REVIEWER_PACKET,
        blockers,
    )


def _draft_required_outcome() -> tuple[ReadinessState, RequiredNextStep, list[str]]:
    return (
        ReadinessState.DRAFT_REQUIRED,
        RequiredNextStep.RENDER_REVIEWER_PACKET,
        ["public_article_output_missing"],
    )


def _evidence_blockers(evidence: NormalizedTicketEvidencePacket) -> list[str]:
    return list(validate_evidence_packet(evidence).blockers)


def _decision_is_blocked(decision: KcsActionDecisionPacket) -> bool:
    return (
        decision.status == DecisionStatus.BLOCKED.value
        or decision.recommended_action == RecommendedAction.BLOCKED.value
        or bool(decision.blockers)
    )


def _blocked_decision_outcome(
    decision: KcsActionDecisionPacket,
) -> tuple[ReadinessState, RequiredNextStep, list[str]]:
    blockers = list(decision.blockers) or ["decision_blocked"]
    next_step = RequiredNextStep.FIX_EVIDENCE
    if any(blocker in _REUSE_SEARCH_BLOCKERS for blocker in blockers):
        next_step = RequiredNextStep.RUN_REUSE_SEARCH
    return (ReadinessState.BLOCKED, next_step, blockers)


def _reviewer_packet_mismatch_blockers(
    evidence: NormalizedTicketEvidencePacket,
    decision: KcsActionDecisionPacket,
    reviewer_packet: KcsReviewerPacket,
) -> list[str]:
    blockers: list[str] = []
    if reviewer_packet.case_ref != evidence.case_ref:
        blockers.append("reviewer_packet_case_ref_mismatch")
    if reviewer_packet.recommended_action != decision.recommended_action:
        blockers.append("reviewer_packet_decision_mismatch")
    if reviewer_packet.auto_publish_allowed is not False:
        blockers.append("auto_publish_allowed_not_false")
    return blockers


def _renderer_blockers(reviewer_packet: KcsReviewerPacket) -> list[str]:
    blockers, blockers_invalid = _renderer_report_codes(
        reviewer_packet.validation_report, "blockers"
    )
    _, checks_invalid = _renderer_report_codes(
        reviewer_packet.validation_report, "checks"
    )
    _, warnings_invalid = _renderer_report_codes(
        reviewer_packet.validation_report, "warnings"
    )
    if blockers_invalid or checks_invalid or warnings_invalid:
        return blockers + ["renderer_validation_report_invalid"]
    return blockers


def _draft_required(
    decision: KcsActionDecisionPacket, reviewer_packet: KcsReviewerPacket
) -> bool:
    if decision.recommended_action not in _ARTICLE_OUTPUT_ACTIONS:
        return False
    return (
        reviewer_packet.public_article_candidate is None
        or reviewer_packet.zendesk_source_html is None
    )


def _decision_summary(decision: KcsActionDecisionPacket) -> dict[str, object]:
    return {
        "schema_version": decision.schema_version,
        "candidate_id": _safe_metadata(decision.candidate_id),
        "recommended_action": decision.recommended_action,
        "article_type": decision.article_type,
        "status": decision.status,
        "blockers": _safe_codes(decision.blockers, "blockers"),
        "split_item_count": len(decision.split_items),
        "has_selected_reuse_match": decision.selected_reuse_match is not None,
        "operator_override_allowed": decision.operator_override_allowed,
        "allowed_override_modes": _safe_codes(
            decision.allowed_override_modes, "allowed_override_modes"
        ),
        "override_status": decision.override_status,
        "auto_publish_allowed": decision.auto_publish_allowed,
    }


def _renderer_validation(
    reviewer_packet: KcsReviewerPacket | None,
) -> dict[str, object]:
    if reviewer_packet is None:
        return {
            "schema_version": "kcs_renderer_validation_report_v1",
            "renderer_status": "not_run",
            "checks": [],
            "blockers": ["reviewer_packet_missing"],
            "warnings": [],
            "has_public_article_candidate": False,
            "has_zendesk_source_html": False,
        }
    report = reviewer_packet.validation_report
    checks, _ = _renderer_report_codes(report, "checks")
    blockers, blockers_invalid = _renderer_report_codes(report, "blockers")
    warnings, _ = _renderer_report_codes(report, "warnings")
    if blockers_invalid:
        blockers.append("renderer_validation_report_invalid")
    return {
        "schema_version": _safe_metadata(report.get("schema_version")),
        "renderer_status": _safe_metadata(report.get("renderer_status")),
        "checks": _safe_codes(checks, "checks"),
        "blockers": _safe_codes(blockers, "blockers"),
        "warnings": _safe_codes(warnings, "warnings"),
        "has_public_article_candidate": reviewer_packet.public_article_candidate
        is not None,
        "has_zendesk_source_html": reviewer_packet.zendesk_source_html is not None,
    }


def _base_checks(reviewer_packet: KcsReviewerPacket | None) -> list[str]:
    checks = [
        "evidence_validation_checked",
        "decision_checked",
        "auto_publish_allowed_false",
    ]
    if reviewer_packet is not None:
        checks.extend(
            [
                "renderer_validation_checked",
                "reviewer_packet_hash_computed",
            ]
        )
        if reviewer_packet.zendesk_source_html is not None:
            checks.append("zendesk_source_hash_computed")
    return checks


def _renderer_warnings(reviewer_packet: KcsReviewerPacket | None) -> list[str]:
    if reviewer_packet is None:
        return []
    warnings, invalid = _renderer_report_codes(
        reviewer_packet.validation_report, "warnings"
    )
    if invalid:
        return ["renderer_validation_report_invalid"]
    return _safe_codes(
        warnings,
        "warnings",
    )


def _reviewer_packet_hash(reviewer_packet: KcsReviewerPacket | None) -> str:
    if reviewer_packet is None:
        return ""
    return hashlib.sha256(dumps_payload(reviewer_packet).encode("utf-8")).hexdigest()


def _zendesk_source_hash(reviewer_packet: KcsReviewerPacket | None) -> str:
    if reviewer_packet is None or reviewer_packet.zendesk_source_html is None:
        return ""
    return hashlib.sha256(
        reviewer_packet.zendesk_source_html.encode("utf-8")
    ).hexdigest()


def _safe_codes(values: Iterable[str], field_name: str) -> list[str]:
    safe_values: list[str] = []
    unsafe_found = False
    for value in values:
        if (
            isinstance(value, str)
            and len(value) <= _MAX_CODE_LENGTH
            and _SAFE_CODE_RE.fullmatch(value)
        ):
            safe_values.append(value)
        else:
            unsafe_found = True
    if unsafe_found:
        safe_values.append(f"{field_name}_{_UNSAFE_REPORT_CODE}")
    return list(dict.fromkeys(safe_values))


def _safe_metadata(value: object) -> str:
    if isinstance(value, str) and _SAFE_CODE_RE.fullmatch(value.replace("-", "_")):
        return value
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:-]+", value):
        return value
    return ""


def _string_list(value: object) -> list[str]:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    return []


def _renderer_report_codes(
    report: dict[str, object], key: str
) -> tuple[list[str], bool]:
    values = report.get(key)
    if isinstance(values, list) and all(isinstance(item, str) for item in values):
        return list(values), False
    return [], True
