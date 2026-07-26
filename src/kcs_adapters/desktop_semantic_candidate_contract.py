"""Desktop-facing metadata for the semantic issue proposal contract."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from kcs_core.json_payload import JsonDict
from kcs_core.semantic_extraction import (
    SEMANTIC_ISSUE_PROPOSAL_SCHEMA_VERSION,
    SemanticCoverageReason,
)


@dataclass(frozen=True)
class _SemanticFieldContract:
    enum_type: type[StrEnum]
    invalid_debug_code: str


_PROPOSAL_FIELD_CONTRACTS = MappingProxyType(
    {
        "reason_code": _SemanticFieldContract(
            SemanticCoverageReason,
            "semantic_coverage_reason_invalid",
        ),
    }
)

_DEBUG_CODE_RULES = (
    (
        "sanitized input contains unsafe value",
        "semantic_review_unsafe_value_blocked",
    ),
    ("must be an opaque safe reference", "semantic_ref_shape_invalid"),
    ("semantic source_refs invalid", "semantic_source_refs_shape_invalid"),
    ("semantic observation", "semantic_observation_shape_invalid"),
    ("observation text", "semantic_observation_shape_invalid"),
    ("observation source_refs", "semantic_observation_shape_invalid"),
    ("semantic issue summary", "semantic_observation_shape_invalid"),
    ("semantic issue question", "semantic_observation_shape_invalid"),
    ("semantic symptoms", "semantic_observation_shape_invalid"),
    ("semantic error_evidence", "semantic_observation_shape_invalid"),
    ("semantic cause_evidence", "semantic_observation_shape_invalid"),
    ("semantic resolution_evidence", "semantic_observation_shape_invalid"),
    ("semantic verification_evidence", "semantic_observation_shape_invalid"),
    ("semantic answer_evidence", "semantic_observation_shape_invalid"),
    ("semantic context_evidence", "semantic_observation_shape_invalid"),
    ("text must be a non-empty string", "semantic_observation_shape_invalid"),
    ("payload must", "semantic_issue_proposal_shape_invalid"),
    ("unsupported semantic reason_code", "semantic_coverage_reason_invalid"),
    ("unsupported semantic coverage_reason", "semantic_coverage_reason_invalid"),
    (
        "semantic issue proposal coverage incomplete",
        "semantic_issue_coverage_incomplete",
    ),
    ("semantic duplicate coverage", "semantic_coverage_shape_invalid"),
    ("semantic coverage", "semantic_coverage_shape_invalid"),
    ("semantic issue proposal", "semantic_issue_proposal_shape_invalid"),
)

_SUBMISSION_SHAPE_CORRECTIONS = MappingProxyType(
    {
        "semantic_observation_shape_invalid": {
            "correction_kind": "submit_shape",
            "field_name": "observation_fields",
            "instruction": (
                "Use an object with exactly text and source_refs for every "
                "observation. source_refs must be a non-empty list of unique "
                "exact refs from allowed_source_refs. "
                "Use observation lists for symptoms, error_evidence, "
                "cause_evidence, resolution_evidence, verification_evidence, "
                "answer_evidence, and context_evidence. Use one required "
                "observation for summary and null or one observation for question. "
                "Correct every listed field path in one submission and preserve "
                "unlisted fields."
            ),
        },
        "semantic_issue_case_ref_mismatch": {
            "correction_kind": "submit_shape",
            "field_name": "case_ref",
            "instruction": (
                "Use the exact case_ref from required_submit_shape in the "
                "prepared semantic review packet."
            ),
        },
        "semantic_issue_candidate_limit_exceeded": {
            "correction_kind": "submit_shape",
            "field_name": "issues",
            "instruction": (
                "Keep the issues list within max_candidates from the prepared "
                "semantic review packet."
            ),
        },
        "semantic_issue_coverage_incomplete": {
            "correction_kind": "submit_shape",
            "field_name": "source_coverage",
            "instruction": (
                "Cover every allowed_source_ref in issue observations or in "
                "coverage_records."
            ),
        },
        "semantic_issue_top_level_source_refs_mismatch": {
            "correction_kind": "submit_shape",
            "field_name": "source_refs",
            "instruction": (
                "Use the exact top-level source_refs from required_submit_shape "
                "in the prepared semantic review packet."
            ),
        },
        "semantic_observation_text_not_extractive": {
            "correction_kind": "submit_shape",
            "field_name": "observation_text",
            "instruction": (
                "Except for summary, copy each observation text exactly from "
                "one referenced selected_excerpt. Preserve the original words, "
                "commands, URLs, questions, and punctuation; do not paraphrase. "
                "Summary remains generative."
            ),
        },
        "semantic_issue_entry_speaker_incompatible": {
            "correction_kind": "submit_shape",
            "field_name": "symptoms_or_question_source_refs",
            "instruction": (
                "Copy symptoms and question from customer-authored excerpts "
                "when available. Do not ground those fields only in explicitly "
                "support-authored excerpts. Excerpts marked unknown remain "
                "admissible; do not guess their speaker."
            ),
        },
    }
)
_GROUNDING_CORRECTION_CODES = frozenset(
    {
        "semantic_issue_entry_speaker_incompatible",
        "semantic_observation_text_not_extractive",
    }
)


def semantic_issue_proposal_contract_metadata() -> JsonDict:
    """Return discoverable closed fields for the active proposal contract."""

    return {
        "proposal_field_contracts": {
            field_name: _field_contract_json(contract)
            for field_name, contract in _PROPOSAL_FIELD_CONTRACTS.items()
        },
        "issue_boundary_contract": _issue_boundary_contract_metadata(),
        "issue_shape_contract": _issue_shape_contract_metadata(),
        "proposal_shape_contracts": {
            "coverage_record": {
                "coverage_ref": "required_safe_ref",
                "duplicate_of_source_ref": "nullable_allowed_source_ref",
                "reason_code": "required_closed_enum",
                "source_refs": "non_empty_allowed_source_ref_list",
            },
            "issue": {
                "answer_evidence": "observation_list",
                "cause_evidence": "observation_list",
                "context_evidence": "observation_list",
                "error_evidence": "optional_observation_list",
                "issue_ref": "required_safe_ref",
                "question": "nullable_observation",
                "resolution_evidence": "observation_list",
                "summary": "required_observation",
                "symptoms": "observation_list",
                "verification_evidence": "observation_list",
            },
            "observation": {
                "source_refs": "non_empty_allowed_source_ref_list",
                "text": (
                    "exact_text_from_one_referenced_selected_excerpt_except_summary"
                ),
            },
        },
        "schema_version": SEMANTIC_ISSUE_PROPOSAL_SCHEMA_VERSION,
    }


def _issue_boundary_contract_metadata() -> JsonDict:
    return {
        "evidence_order": "bounded_excerpts_preserve_ticket_chronology",
        "issue_unit": "coherent_separately_searchable_problem_or_question",
        "technical_issue_identity": (
            "supported_cause_and_supported_resolution_or_workaround_pair"
        ),
        "question_issue_identity": (
            "customer_question_or_task_and_supported_answer_or_resolution_pair"
        ),
        "symptom_role": "search_entry_evidence_not_issue_identity",
        "chronology_role": "order_evidence_within_issue_not_define_boundary",
        "chronology_rules": [
            "reconstruct_each_issue_thread_in_ticket_order",
            "allow_interleaved_issue_threads",
            "require_cause_resolution_link_not_temporal_adjacency",
            "later_confirmed_evidence_may_refine_earlier_hypothesis_within_issue",
            "do_not_merge_resolved_problem_with_distinct_remaining_failure",
        ],
        "resolved_problem_rule": (
            "If one problem is resolved before a distinct failure remains, "
            "propose separate issues even when the later diagnostic or repair "
            "action was triggered by the first problem."
        ),
        "causal_chain_rule": (
            "Treat a symptom, intermediate diagnostic fact, and confirmed cause "
            "as one issue when the evidence links them to one resolution outcome. "
            "Do not propose stages of that causal chain as separate issues."
        ),
        "final_partition_check": [
            "compare_every_proposed_issue_with_every_other_issue_before_submit",
            (
                "group_evidence_by_independently_searchable_problem_or_question_"
                "and_its_linked_resolution_outcome"
            ),
            (
                "attach_diagnostic_or_repair_output_to_parent_when_it_is_part_of_"
                "the_same_causal_chain_and_has_no_independent_issue_identity"
            ),
            (
                "keep_independent_unresolved_customer_problem_separate_even_"
                "without_resolution_evidence"
            ),
            "do_not_merge_distinct_issues_only_to_complete_evidence_shape",
        ],
        "merge_signals": [
            "same_supported_cause_and_resolution_pair",
            "same_question_or_task_and_answer_or_resolution_pair",
            "same_linked_causal_chain_and_resolution_outcome",
        ],
        "split_signals": [
            "different_supported_cause_and_resolution_pair",
            "different_question_or_task_and_answer_or_resolution_pair",
            "one_issue_can_resolve_without_the_other",
            "one_problem_resolved_before_distinct_failure_remains",
            "later_failure_has_independent_cause_or_resolution",
        ],
        "not_split_by_itself": [
            "different_wording_for_stages_of_one_linked_causal_chain",
            "intermediate_diagnostic_fact_within_one_linked_causal_chain",
        ],
        "not_issue_identity_by_itself": [
            "symptom_and_cause",
            "symptom_and_resolution",
            "shared_symptom",
            "chronological_proximity",
            "contiguous_excerpt_range",
            "later_diagnostic_or_repair_action_triggered_by_earlier_issue",
        ],
    }


def _issue_shape_contract_metadata() -> JsonDict:
    return {
        "classification_method": "semantic_evidence_shape_not_error_keyword_match",
        "error_evidence_role": (
            "source_grounded_relevant_reported_or_support_discovered_error"
        ),
        "technical_problem_signal": (
            "problem_observation_with_or_without_literal_error_evidence"
        ),
        "howto_signal": "question_or_task_without_relevant_error_evidence",
        "resolution_evidence_role": "supports_issue_but_does_not_determine_shape",
        "mixed_problem_question": (
            "technical_only_when_question_seeks_resolution_of_error_evidence"
        ),
        "error_detection": "model_proposed_source_grounded_not_lexical_regex",
        "ambiguous_shape": "fail_closed",
    }


def semantic_contract_debug_code(validation_message: str) -> str:
    """Map a safe core validation message to a Desktop debug code."""

    normalized = validation_message.casefold()
    for needle, debug_code in _DEBUG_CODE_RULES:
        if needle in normalized:
            return debug_code
    return "semantic_review_submission_invalid"


def semantic_submission_correction(debug_code: str) -> JsonDict | None:
    """Return bounded correction metadata without echoing submitted values."""

    shape_correction = _SUBMISSION_SHAPE_CORRECTIONS.get(debug_code)
    if shape_correction is not None:
        return dict(shape_correction)
    for field_name, contract in _PROPOSAL_FIELD_CONTRACTS.items():
        if contract.invalid_debug_code == debug_code:
            return {
                **_field_contract_json(contract),
                "field_name": field_name,
            }
    return None


def semantic_submission_correction_stage(debug_code: str) -> str | None:
    """Classify one registered correction without exposing submitted values."""

    if semantic_submission_correction(debug_code) is None:
        return None
    if debug_code in _GROUNDING_CORRECTION_CODES:
        return "grounding"
    return "structure"


def _field_contract_json(contract: _SemanticFieldContract) -> JsonDict:
    return {
        "accepted_values": [member.value for member in contract.enum_type],
        "invalid_debug_code": contract.invalid_debug_code,
    }
