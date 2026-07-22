"""Prepare and evaluate value-safe M2 semantic projection shadow runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kcs_adapters.desktop_semantic_candidates import (
    project_semantic_issue_proposals,
    semantic_projection_shadow_comparison,
)
from kcs_adapters.desktop_semantic_review import (
    semantic_issue_proposal_contract_packet,
)
from kcs_core.errors import ContractValidationError
from kcs_core.semantic_extraction import (
    SemanticIssueProposal,
    SemanticIssueProposalPacket,
    SemanticObservation,
)

SCHEMA_VERSION = "kcs_semantic_projection_rebaseline_run_v2"
SUMMARY_SCHEMA_VERSION = "kcs_semantic_projection_rebaseline_summary_v2"
SCENARIO_IDS = (
    "single_customer_issue",
    "split_with_internal_coverage",
    "boundary_uncertain",
)
_MAX_RESPONSE_BYTES = 128_000
_IDENTITY_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_CODE_RE = re.compile(r"[a-z][a-z0-9_]{0,99}")
_COUNT_FIELDS = (
    "blocked_proposal_count",
    "boundary_uncertainty_count",
    "coverage_record_count",
    "identity_issue_count",
    "identity_reference_count",
    "proposal_count",
    "unassigned_evidence_count",
)
_FORBIDDEN_PROJECTION_FIELDS = frozenset(
    {
        "kcs_ready",
        "public_output_approved",
        "recommended_action",
        "reuse_search_status",
    }
)


@dataclass(frozen=True)
class _Scenario:
    scenario_id: str
    semantic_review_ref: str
    excerpts: tuple[dict[str, str], ...]
    role_index: dict[str, dict[str, object]]
    legacy_extraction: dict[str, object]
    expected_identities: tuple[_IdentityRefShape, ...]

    @property
    def source_refs(self) -> tuple[str, ...]:
        return tuple(excerpt["source_ref"] for excerpt in self.excerpts)


@dataclass(frozen=True)
class _IdentityRefShape:
    kind: str
    anchor_source_refs: tuple[str, ...]
    outcome_source_refs: tuple[str, ...]


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "prepare":
            prompt = prepare_prompt(args.scenario)
            if args.output is None:
                sys.stdout.write(prompt)
            else:
                args.output.write_text(prompt, encoding="utf-8")
                _write_json(
                    {
                        "ok": True,
                        "prompt_sha256": _sha256_text(prompt),
                        "scenario_id": args.scenario,
                    }
                )
            return 0
        if args.command == "evaluate":
            record = evaluate_response(
                scenario_id=args.scenario,
                response_path=args.response,
                model_identity=args.model_identity,
                client_identity=args.client_identity,
                package_sha256=args.package_sha256,
                system_prompt_sha256=args.system_prompt_sha256,
                run_index=args.run_index,
            )
            _write_json(record)
            return 0
        _write_json(summarize_records(args.records))
        return 0
    except (ContractValidationError, OSError, ValueError) as exc:
        _write_json({"debug_code": _debug_code(exc), "ok": False})
        return 2


def prepare_prompt(scenario_id: str) -> str:
    """Return one fixed synthetic prompt for a manual model shadow run."""

    scenario = _scenario(scenario_id)
    contract = semantic_issue_proposal_contract_packet(
        allowed_source_refs=scenario.source_refs,
        semantic_review_ref=scenario.semantic_review_ref,
    )
    payload = {
        "bounded_excerpts": list(scenario.excerpts),
        "shadow_contract": contract,
    }
    payload_text = json.dumps(
        payload,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return (
        "Perform a shadow-only semantic issue proposal. This is not a drafting "
        "or KCS-action request. Return exactly one JSON object with the single "
        "top-level key semantic_issue_proposal. Use only the bounded excerpts "
        "and exact fields allowed by shadow_contract. Represent every allowed "
        "source ref in an issue observation or coverage record. Do not choose "
        "an operator action, reuse result, readiness state, renderer output, "
        "publication action, or workflow state. Do not use Markdown fences.\n\n"
        f"{payload_text}\n"
    )


def evaluate_response(
    *,
    scenario_id: str,
    response_path: Path,
    model_identity: str,
    client_identity: str,
    package_sha256: str,
    system_prompt_sha256: str,
    run_index: int,
) -> dict[str, object]:
    """Validate one model response and return a text-free value-safe record."""

    scenario = _scenario(scenario_id)
    _validate_run_identity(
        client_identity=client_identity,
        model_identity=model_identity,
        package_sha256=package_sha256,
        run_index=run_index,
        system_prompt_sha256=system_prompt_sha256,
    )
    packet = _read_response_packet(response_path)
    _validate_response_identity(packet, scenario)
    projected = project_semantic_issue_proposals(packet, scenario.role_index)
    comparison = semantic_projection_shadow_comparison(
        legacy_extraction=scenario.legacy_extraction,
        projected=projected,
    )
    projected_payload = projected.to_json_dict()
    if _contains_forbidden_projection_field(projected_payload):
        raise ContractValidationError("rebaseline projection authority invalid")
    invariant_codes = _invariant_codes(projected)
    if any(code.endswith("_failed") for code in invariant_codes):
        raise ContractValidationError("rebaseline hard invariant failed")
    identity_comparison = _identity_comparison(packet, scenario)
    return {
        "blocked_proposal_count": len(projected.blocked_proposals),
        "boundary_uncertainty_count": 0,
        "client_identity": client_identity,
        "comparison_codes": list(comparison.codes),
        "coverage_complete": not projected.unassigned_evidence,
        "coverage_record_count": len(packet.coverage_records),
        "invariant_codes": list(invariant_codes),
        **identity_comparison,
        "model_identity": model_identity,
        "ok": True,
        "package_sha256": package_sha256,
        "projected_sha256": comparison.projected_sha256,
        "prompt_sha256": _sha256_text(prepare_prompt(scenario_id)),
        "proposal_count": len(packet.issues),
        "run_index": run_index,
        "scenario_id": scenario_id,
        "schema_version": SCHEMA_VERSION,
        "system_prompt_sha256": system_prompt_sha256,
        "unassigned_evidence_count": len(projected.unassigned_evidence),
    }


def summarize_records(paths: Sequence[Path]) -> dict[str, object]:
    """Aggregate value-safe run records without model response content."""

    records = [read_value_safe_record(path) for path in paths]
    _validate_record_matrix(records)
    comparison_codes = _list_value_counts(records, "comparison_codes")
    invariant_codes = _list_value_counts(records, "invariant_codes")
    proposal_counts = _scalar_value_counts(records, "proposal_count")
    scenario_counts = _scalar_value_counts(records, "scenario_id")
    return {
        "blocked_proposal_total": _integer_total(records, "blocked_proposal_count"),
        "boundary_uncertainty_total": _integer_total(
            records, "boundary_uncertainty_count"
        ),
        "comparison_code_counts": dict(sorted(comparison_codes.items())),
        "client_identity": _single_record_value(records, "client_identity"),
        "coverage_complete_runs": {
            "denominator": len(records),
            "numerator": _true_total(records, "coverage_complete"),
        },
        "invariant_code_counts": dict(sorted(invariant_codes.items())),
        "identity_comparable_runs": {
            "denominator": len(records),
            "numerator": _true_total(records, "identity_comparable"),
        },
        "identity_set_match_runs": {
            "denominator": len(records),
            "numerator": _true_total(records, "identity_set_matches_reference"),
        },
        "model_identity": _single_record_value(records, "model_identity"),
        "package_sha256": _single_record_value(records, "package_sha256"),
        "prompt_sha256_by_scenario": {
            scenario_id: _scenario_prompt_sha256(records, scenario_id)
            for scenario_id in SCENARIO_IDS
        },
        "ok": True,
        "proposal_count_distribution": dict(sorted(proposal_counts.items())),
        "run_count": len(records),
        "scenario_run_counts": dict(sorted(scenario_counts.items())),
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "system_prompt_sha256": _single_record_value(records, "system_prompt_sha256"),
        "unassigned_evidence_total": _integer_total(
            records, "unassigned_evidence_count"
        ),
    }


def _validate_record_matrix(records: Sequence[Mapping[str, object]]) -> None:
    expected_runs = set(range(1, 4))
    if len(records) != len(SCENARIO_IDS) * len(expected_runs):
        raise ValueError("rebaseline records invalid")
    _validate_matrix_identity(records)
    _validate_scenario_runs(records, expected_runs=expected_runs)


def _validate_matrix_identity(records: Sequence[Mapping[str, object]]) -> None:
    for field_name in (
        "client_identity",
        "model_identity",
        "package_sha256",
        "system_prompt_sha256",
    ):
        _single_record_value(records, field_name)


def _validate_scenario_runs(
    records: Sequence[Mapping[str, object]], *, expected_runs: set[int]
) -> None:
    scenario_counts = _scalar_value_counts(records, "scenario_id")
    expected_scenarios = Counter(
        {scenario_id: len(expected_runs) for scenario_id in SCENARIO_IDS}
    )
    if scenario_counts != expected_scenarios:
        raise ValueError("rebaseline records invalid")
    for scenario_id in SCENARIO_IDS:
        run_indices = {
            int(record["run_index"])
            for record in records
            if record["scenario_id"] == scenario_id
        }
        if run_indices != expected_runs:
            raise ValueError("rebaseline records invalid")


def _single_record_value(
    records: Sequence[Mapping[str, object]], field_name: str
) -> str:
    values = {str(record[field_name]) for record in records}
    if len(values) != 1:
        raise ValueError("rebaseline records invalid")
    return values.pop()


def _scenario_prompt_sha256(
    records: Sequence[Mapping[str, object]], scenario_id: str
) -> str:
    scenario_records = [
        record for record in records if record["scenario_id"] == scenario_id
    ]
    return _single_record_value(scenario_records, "prompt_sha256")


def _list_value_counts(
    records: Sequence[Mapping[str, object]], field_name: str
) -> Counter[str]:
    values: list[str] = []
    for record in records:
        values.extend(str(value) for value in record[field_name])
    return Counter(values)


def _scalar_value_counts(
    records: Sequence[Mapping[str, object]], field_name: str
) -> Counter[str]:
    return Counter(str(record[field_name]) for record in records)


def _integer_total(records: Sequence[Mapping[str, object]], field_name: str) -> int:
    return sum(int(record[field_name]) for record in records)


def _true_total(records: Sequence[Mapping[str, object]], field_name: str) -> int:
    return sum(record[field_name] is True for record in records)


def _scenario(scenario_id: str) -> _Scenario:
    builders = {
        "single_customer_issue": _single_customer_issue,
        "split_with_internal_coverage": _split_with_internal_coverage,
        "boundary_uncertain": _boundary_uncertain,
    }
    try:
        return builders[scenario_id]()
    except KeyError as exc:
        raise ValueError("rebaseline scenario invalid") from exc


def _single_customer_issue() -> _Scenario:
    excerpts = (
        _excerpt(
            "excerpt-001",
            "reported_symptom",
            "A supported service task returns no result.",
        ),
        _excerpt("excerpt-002", "supported_cause", "A required component is disabled."),
        _excerpt(
            "excerpt-003",
            "supported_resolution",
            "Enable the component and verify the task.",
        ),
    )
    return _Scenario(
        scenario_id="single_customer_issue",
        semantic_review_ref="semantic-shadow-single-001",
        excerpts=excerpts,
        expected_identities=(
            _identity_ref_shape(
                "technical_scr",
                anchor_source_refs=("excerpt-002",),
                outcome_source_refs=("excerpt-003",),
            ),
        ),
        role_index=_role_index(excerpts),
        legacy_extraction=_legacy_extraction(
            case_ref="semantic-shadow-single-001",
            source_refs=_source_refs(excerpts),
            items=[
                _legacy_scr_item(
                    candidate_id="candidate-001",
                    source_refs=_source_refs(excerpts),
                    summary="A supported service task returns no result.",
                    symptom="A supported service task returns no result.",
                    cause="A required component is disabled.",
                    resolution="Enable the component and verify the task.",
                )
            ],
        ),
    )


def _split_with_internal_coverage() -> _Scenario:
    excerpts = (
        _excerpt(
            "excerpt-001",
            "reported_symptom",
            "A primary service task returns no result.",
        ),
        _excerpt(
            "excerpt-002",
            "supported_cause",
            "The primary component is disabled.",
        ),
        _excerpt(
            "excerpt-003",
            "supported_resolution",
            "Enable the primary component and verify it.",
        ),
        _excerpt(
            "excerpt-004",
            "customer_question",
            "How can the local service cache be refreshed?",
        ),
        _excerpt(
            "excerpt-005",
            "supported_resolution",
            "Run the supported cache refresh operation.",
        ),
        _excerpt(
            "excerpt-006",
            "internal_workflow_note",
            "The conversation was split for routing.",
        ),
    )
    return _Scenario(
        scenario_id="split_with_internal_coverage",
        semantic_review_ref="semantic-shadow-split-001",
        excerpts=excerpts,
        expected_identities=(
            _identity_ref_shape(
                "technical_scr",
                anchor_source_refs=("excerpt-002",),
                outcome_source_refs=("excerpt-003",),
            ),
            _identity_ref_shape(
                "howto_qa",
                anchor_source_refs=("excerpt-004",),
                outcome_source_refs=("excerpt-005",),
            ),
        ),
        role_index=_role_index(excerpts),
        legacy_extraction=_legacy_extraction(
            case_ref="semantic-shadow-split-001",
            source_refs=_source_refs(excerpts),
            items=[
                _legacy_scr_item(
                    candidate_id="candidate-001",
                    source_refs=("excerpt-001", "excerpt-002", "excerpt-003"),
                    summary="A primary service task returns no result.",
                    symptom="A primary service task returns no result.",
                    cause="The primary component is disabled.",
                    resolution="Enable the primary component and verify it.",
                ),
                _legacy_qa_item(),
                _legacy_no_article_item(),
            ],
        ),
    )


def _boundary_uncertain() -> _Scenario:
    excerpts = (
        _excerpt(
            "excerpt-001",
            "reported_symptom",
            "Two related service checks fail together.",
        ),
        _excerpt(
            "excerpt-002",
            "supported_cause",
            "The available evidence does not separate their causes.",
        ),
        _excerpt(
            "excerpt-003",
            "supported_resolution",
            "Collect separate verification evidence before acting.",
        ),
    )
    item = _legacy_scr_item(
        candidate_id="candidate-001",
        source_refs=_source_refs(excerpts),
        summary="Two related service checks fail together.",
        symptom="Two related service checks fail together.",
        cause="The available evidence does not separate their causes.",
        resolution="Collect separate verification evidence before acting.",
    )
    item["kcs_item_status"] = "blocked_need_more_evidence"
    return _Scenario(
        scenario_id="boundary_uncertain",
        semantic_review_ref="semantic-shadow-boundary-001",
        excerpts=excerpts,
        expected_identities=(
            _identity_ref_shape(
                "technical_scr",
                anchor_source_refs=("excerpt-002",),
                outcome_source_refs=("excerpt-003",),
            ),
        ),
        role_index=_role_index(excerpts),
        legacy_extraction=_legacy_extraction(
            case_ref="semantic-shadow-boundary-001",
            source_refs=_source_refs(excerpts),
            items=[item],
        ),
    )


def _excerpt(source_ref: str, role: str, text: str) -> dict[str, str]:
    return {"role": role, "source_ref": source_ref, "text": text}


def _identity_ref_shape(
    kind: str,
    *,
    anchor_source_refs: tuple[str, ...],
    outcome_source_refs: tuple[str, ...],
) -> _IdentityRefShape:
    return _IdentityRefShape(
        kind=kind,
        anchor_source_refs=tuple(sorted(set(anchor_source_refs))),
        outcome_source_refs=tuple(sorted(set(outcome_source_refs))),
    )


def _source_refs(excerpts: Sequence[Mapping[str, str]]) -> tuple[str, ...]:
    return tuple(excerpt["source_ref"] for excerpt in excerpts)


def _role_index(
    excerpts: Sequence[Mapping[str, str]],
) -> dict[str, dict[str, object]]:
    return {
        excerpt["source_ref"]: {
            "content_sha256": _sha256_text(excerpt["text"]),
            "provenance_trusted": True,
            "roles": [excerpt["role"]],
            "visibility": (
                "internal_reviewer_only"
                if excerpt["role"] == "internal_workflow_note"
                else "public_customer_safe"
            ),
        }
        for excerpt in excerpts
    }


def _legacy_extraction(
    *,
    case_ref: str,
    source_refs: tuple[str, ...],
    items: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "case_ref": case_ref,
        "extraction_source_ref": "legacy-shadow-001",
        "items": items,
        "schema_version": "candidate_semantic_extraction_v1",
        "source_refs": list(source_refs),
    }


def _legacy_scr_item(
    *,
    candidate_id: str,
    source_refs: tuple[str, ...],
    summary: str,
    symptom: str,
    cause: str,
    resolution: str,
) -> dict[str, object]:
    return {
        "article_type_hint": "technical_scr",
        "candidate_id": candidate_id,
        "candidate_origin": "customer_reported",
        "confirmed_facts": [cause],
        "environment": {},
        "kcs_item_status": "candidate_allowed",
        "product_relation": "plesk_owned",
        "resolution_steps": [resolution],
        "source_refs": list(source_refs),
        "summary": summary,
        "supportability": "supported",
        "supportability_basis": "not_checked",
        "supported_cause": cause,
        "supported_resolution_or_workaround": resolution,
        "symptoms": [symptom],
        "visibility_hint": "public_customer_safe",
    }


def _legacy_qa_item() -> dict[str, object]:
    return {
        "article_type_hint": "howto_qa",
        "candidate_id": "candidate-002",
        "candidate_origin": "customer_reported",
        "confirmed_facts": ["A supported cache refresh operation is available."],
        "environment": {},
        "kcs_item_status": "candidate_allowed",
        "product_relation": "plesk_owned",
        "question": "How can the local service cache be refreshed?",
        "resolution_steps": ["Run the supported cache refresh operation."],
        "source_refs": ["excerpt-004", "excerpt-005"],
        "summary": "How can the local service cache be refreshed?",
        "supportability": "supported",
        "supportability_basis": "not_checked",
        "supported_answer": "Run the supported cache refresh operation.",
        "symptoms": [],
        "visibility_hint": "public_customer_safe",
    }


def _legacy_no_article_item() -> dict[str, object]:
    return {
        "article_type_hint": "none",
        "candidate_id": "candidate-003",
        "candidate_origin": "support_discovered",
        "confirmed_facts": [],
        "environment": {},
        "kcs_item_status": "no_article",
        "product_relation": "customer_environment_specific",
        "resolution_steps": [],
        "source_refs": ["excerpt-006"],
        "summary": "The conversation was split for routing.",
        "supportability": "unclear",
        "supportability_basis": "not_checked",
        "symptoms": [],
        "visibility_hint": "internal_reviewer_only",
    }


def _identity_comparison(
    packet: SemanticIssueProposalPacket,
    scenario: _Scenario,
) -> dict[str, object]:
    actual_keys = tuple(
        key
        for issue in packet.issues
        if (key := _issue_identity_ref_key(issue)) is not None
    )
    expected_keys = tuple(
        _identity_ref_key(identity) for identity in scenario.expected_identities
    )
    comparable = len(actual_keys) == len(packet.issues)
    return {
        "identity_comparable": comparable,
        "identity_issue_count": len(actual_keys),
        "identity_reference_count": len(expected_keys),
        "identity_set_matches_reference": (
            comparable and sorted(actual_keys) == sorted(expected_keys)
        ),
    }


def _issue_identity_ref_key(issue: SemanticIssueProposal) -> str | None:
    has_question_shape = issue.question is not None or bool(issue.answer_evidence)
    if has_question_shape and not issue.error_evidence:
        question_refs = (
            issue.question.source_refs if issue.question is not None else ()
        )
        answer_refs = _observation_source_refs(
            (*issue.answer_evidence, *issue.resolution_evidence)
        )
        if question_refs and answer_refs:
            return _identity_ref_key(
                _identity_ref_shape(
                    "howto_qa",
                    anchor_source_refs=tuple(question_refs),
                    outcome_source_refs=answer_refs,
                )
            )
        return None
    cause_refs = _observation_source_refs(issue.cause_evidence)
    resolution_refs = _observation_source_refs(issue.resolution_evidence)
    if cause_refs and resolution_refs:
        return _identity_ref_key(
            _identity_ref_shape(
                "technical_scr",
                anchor_source_refs=cause_refs,
                outcome_source_refs=resolution_refs,
            )
        )
    return None


def _observation_source_refs(
    observations: Sequence[SemanticObservation],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                source_ref
                for observation in observations
                for source_ref in observation.source_refs
            }
        )
    )


def _identity_ref_key(identity: _IdentityRefShape) -> str:
    payload = {
        "anchor_source_refs": list(identity.anchor_source_refs),
        "kind": identity.kind,
        "outcome_source_refs": list(identity.outcome_source_refs),
    }
    serialized = json.dumps(
        payload,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _read_response_packet(path: Path) -> SemanticIssueProposalPacket:
    data = path.read_bytes()
    if not data or len(data) > _MAX_RESPONSE_BYTES:
        raise ContractValidationError("rebaseline response invalid")
    try:
        payload = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractValidationError("rebaseline response invalid") from exc
    if not isinstance(payload, dict) or set(payload) != {"semantic_issue_proposal"}:
        raise ContractValidationError("rebaseline response invalid")
    return SemanticIssueProposalPacket.from_json_dict(
        payload["semantic_issue_proposal"]
    )


def read_value_safe_record(path: Path) -> dict[str, object]:
    """Read one exact value-safe record for aggregation or external export."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("rebaseline records invalid") from exc
    required = {
        "blocked_proposal_count",
        "boundary_uncertainty_count",
        "client_identity",
        "comparison_codes",
        "coverage_complete",
        "coverage_record_count",
        "invariant_codes",
        "identity_comparable",
        "identity_issue_count",
        "identity_reference_count",
        "identity_set_matches_reference",
        "model_identity",
        "ok",
        "package_sha256",
        "projected_sha256",
        "prompt_sha256",
        "proposal_count",
        "run_index",
        "scenario_id",
        "schema_version",
        "system_prompt_sha256",
        "unassigned_evidence_count",
    }
    if not _record_shape_is_valid(payload, required):
        raise ValueError("rebaseline records invalid")
    return payload


def _record_shape_is_valid(payload: object, required: set[str]) -> bool:
    if not isinstance(payload, dict) or set(payload) != required:
        return False
    if payload.get("schema_version") != SCHEMA_VERSION or payload.get("ok") is not True:
        return False
    return _record_values_are_valid(payload)


def _record_values_are_valid(payload: Mapping[str, object]) -> bool:
    scenario_id = payload.get("scenario_id")
    if scenario_id not in SCENARIO_IDS:
        return False
    if not _record_scalar_values_are_valid(payload):
        return False
    if not _record_identities_are_valid(payload):
        return False
    if not _record_codes_are_valid(payload):
        return False
    if not _record_identity_comparison_is_valid(payload):
        return False
    expected_prompt_sha256 = _sha256_text(prepare_prompt(str(scenario_id)))
    return payload.get("prompt_sha256") == expected_prompt_sha256


def _record_scalar_values_are_valid(payload: Mapping[str, object]) -> bool:
    if not all(
        isinstance(payload.get(field_name), bool)
        for field_name in (
            "coverage_complete",
            "identity_comparable",
            "identity_set_matches_reference",
        )
    ):
        return False
    if not all(_is_nonnegative_int(payload.get(field)) for field in _COUNT_FIELDS):
        return False
    return _is_run_index(payload.get("run_index"))


def _record_identity_comparison_is_valid(payload: Mapping[str, object]) -> bool:
    scenario_id = payload.get("scenario_id")
    if not isinstance(scenario_id, str):
        return False
    expected_count = len(_scenario(scenario_id).expected_identities)
    if payload.get("identity_reference_count") != expected_count:
        return False
    if payload.get("identity_set_matches_reference") is not True:
        return True
    return (
        payload.get("identity_comparable") is True
        and payload.get("identity_issue_count") == expected_count
    )


def _record_identities_are_valid(payload: Mapping[str, object]) -> bool:
    identities = (payload.get("client_identity"), payload.get("model_identity"))
    hashes = (
        payload.get("package_sha256"),
        payload.get("projected_sha256"),
        payload.get("prompt_sha256"),
        payload.get("system_prompt_sha256"),
    )
    return all(_identity_is_valid(value) for value in identities) and all(
        _sha256_is_valid(value) for value in hashes
    )


def _record_codes_are_valid(payload: Mapping[str, object]) -> bool:
    return _code_list_is_valid(payload.get("comparison_codes")) and _code_list_is_valid(
        payload.get("invariant_codes")
    )


def _code_list_is_valid(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(code, str) and _CODE_RE.fullmatch(code) is not None for code in value
    )


def _is_nonnegative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_run_index(value: object) -> bool:
    return _is_nonnegative_int(value) and 1 <= value <= 3


def _invariant_codes(projected: Any) -> tuple[str, ...]:
    return (
        "source_coverage_passed"
        if not projected.unassigned_evidence
        else "source_coverage_failed",
        "operator_authority_absent_passed",
        "kcs_action_authority_absent_passed",
    )


def _contains_forbidden_projection_field(value: object) -> bool:
    if isinstance(value, Mapping):
        if set(value) & _FORBIDDEN_PROJECTION_FIELDS:
            return True
        return any(
            _contains_forbidden_projection_field(item) for item in value.values()
        )
    if isinstance(value, list | tuple):
        return any(_contains_forbidden_projection_field(item) for item in value)
    return False


def _validate_identity(value: str) -> None:
    if not _identity_is_valid(value):
        raise ValueError("rebaseline identity invalid")


def _validate_run_identity(
    *,
    client_identity: str,
    model_identity: str,
    package_sha256: str,
    run_index: int,
    system_prompt_sha256: str,
) -> None:
    _validate_identity(model_identity)
    _validate_identity(client_identity)
    _validate_sha256(package_sha256)
    _validate_sha256(system_prompt_sha256)
    if run_index < 1 or run_index > 99:
        raise ValueError("rebaseline identity invalid")


def _validate_response_identity(
    packet: SemanticIssueProposalPacket, scenario: _Scenario
) -> None:
    if packet.case_ref != scenario.semantic_review_ref:
        raise ContractValidationError("rebaseline response identity invalid")
    if packet.source_refs != scenario.source_refs:
        raise ContractValidationError("rebaseline response identity invalid")


def _validate_sha256(value: str) -> None:
    if not _sha256_is_valid(value):
        raise ValueError("rebaseline identity invalid")


def _identity_is_valid(value: object) -> bool:
    return isinstance(value, str) and _IDENTITY_RE.fullmatch(value) is not None


def _sha256_is_valid(value: object) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _debug_code(exc: Exception) -> str:
    text = str(exc)
    if "identity" in text:
        return "semantic_projection_rebaseline_identity_invalid"
    if "records" in text:
        return "semantic_projection_rebaseline_records_invalid"
    if "scenario" in text:
        return "semantic_projection_rebaseline_scenario_invalid"
    if "invariant" in text:
        return "semantic_projection_rebaseline_invariant_failed"
    return "semantic_projection_rebaseline_response_invalid"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare", help="Write a fixed synthetic prompt.")
    prepare.add_argument("--scenario", choices=SCENARIO_IDS, required=True)
    prepare.add_argument("--output", type=Path)
    evaluate = subparsers.add_parser(
        "evaluate", help="Validate one saved model JSON response."
    )
    evaluate.add_argument("--scenario", choices=SCENARIO_IDS, required=True)
    evaluate.add_argument("--response", type=Path, required=True)
    evaluate.add_argument("--model-identity", required=True)
    evaluate.add_argument("--client-identity", required=True)
    evaluate.add_argument("--package-sha256", required=True)
    evaluate.add_argument("--system-prompt-sha256", required=True)
    evaluate.add_argument("--run-index", type=int, required=True)
    summary = subparsers.add_parser(
        "summarize", help="Aggregate value-safe run records."
    )
    summary.add_argument("records", nargs="+", type=Path)
    return parser


def _write_json(payload: Mapping[str, object]) -> None:
    sys.stdout.write(json.dumps(payload, allow_nan=False, sort_keys=True))
    sys.stdout.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
