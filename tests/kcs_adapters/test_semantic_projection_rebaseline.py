from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from kcs_core.errors import ContractValidationError
from kcs_core.semantic_extraction import CandidateSemanticExtraction

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "rebaseline_semantic_issue_projection.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "rebaseline_semantic_issue_projection",
        SCRIPT,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


REBASELINE = _load_module()


def _observation(text: str, *source_refs: str) -> dict[str, object]:
    return {"source_refs": list(source_refs), "text": text}


def _split_response() -> dict[str, object]:
    return {
        "semantic_issue_proposal": {
            "case_ref": "semantic-shadow-split-001",
            "coverage_records": [
                {
                    "coverage_ref": "coverage-001",
                    "duplicate_of_source_ref": None,
                    "reason_code": "internal_workflow_note",
                    "source_refs": ["excerpt-006"],
                }
            ],
            "extraction_source_ref": "model-shadow-001",
            "issues": [
                {
                    "answer_evidence": [],
                    "cause_evidence": [
                        _observation(
                            "The primary component is disabled.",
                            "excerpt-002",
                        )
                    ],
                    "context_evidence": [],
                    "issue_ref": "issue-001",
                    "question": None,
                    "resolution_evidence": [
                        _observation(
                            "Enable the primary component and verify it.",
                            "excerpt-003",
                        )
                    ],
                    "summary": _observation(
                        "A primary service task returns no result.",
                        "excerpt-001",
                    ),
                    "symptoms": [
                        _observation(
                            "A primary service task returns no result.",
                            "excerpt-001",
                        )
                    ],
                    "verification_evidence": [],
                },
                {
                    "answer_evidence": [
                        _observation(
                            "Run the supported cache refresh operation.",
                            "excerpt-005",
                        )
                    ],
                    "cause_evidence": [],
                    "context_evidence": [],
                    "issue_ref": "issue-002",
                    "question": _observation(
                        "How can the local service cache be refreshed?",
                        "excerpt-004",
                    ),
                    "resolution_evidence": [],
                    "summary": _observation(
                        "How can the local service cache be refreshed?",
                        "excerpt-004",
                    ),
                    "symptoms": [],
                    "verification_evidence": [],
                },
            ],
            "schema_version": "semantic_issue_proposal_v1",
            "source_refs": [
                "excerpt-001",
                "excerpt-002",
                "excerpt-003",
                "excerpt-004",
                "excerpt-005",
                "excerpt-006",
            ],
        }
    }


def _write_response(tmp_path: Path, payload: object) -> Path:
    path = tmp_path / "response.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _evaluate(tmp_path: Path, *, run_index: int = 1) -> dict[str, object]:
    return REBASELINE.evaluate_response(
        scenario_id="split_with_internal_coverage",
        response_path=_write_response(tmp_path, _split_response()),
        model_identity="model-current",
        client_identity="desktop-current",
        package_sha256="a" * 64,
        system_prompt_sha256="b" * 64,
        run_index=run_index,
    )


def test_prepare_prompt_is_fixed_synthetic_and_shadow_only() -> None:
    first = REBASELINE.prepare_prompt("split_with_internal_coverage")
    second = REBASELINE.prepare_prompt("split_with_internal_coverage")

    assert first == second
    assert '"semantic_issue_proposal"' in first
    assert "shadow-only" in first
    assert "Do not choose an operator action" in first
    assert "Do not use Markdown fences" in first
    assert '"proposal_shape_contracts"' in first
    assert '"summary":"required_observation"' in first
    assert '"question":"nullable_observation"' in first
    assert (
        '"text":"exact_text_from_one_referenced_selected_excerpt_except_summary"'
        in first
    )
    assert '"issue_boundary_contract"' in first
    assert '"bounded_excerpts_preserve_ticket_chronology"' in first
    assert '"allow_interleaved_issue_threads"' in first
    assert '"order_evidence_within_issue_not_define_boundary"' in first
    assert '"supported_cause_and_supported_resolution_or_workaround_pair"' in first
    assert '"symptom_and_resolution"' in first
    assert '"issue_shape_contract"' in first
    assert '"error_evidence":"optional_observation_list"' in first
    assert '"question_or_task_without_relevant_error_evidence"' in first
    assert '"supports_issue_but_does_not_determine_shape"' in first


def test_all_scenarios_build_valid_prompt_inputs() -> None:
    for scenario_id in REBASELINE.SCENARIO_IDS:
        scenario = REBASELINE._scenario(scenario_id)
        prompt = REBASELINE.prepare_prompt(scenario_id)

        assert scenario.source_refs
        assert scenario.semantic_review_ref in prompt
        assert set(scenario.role_index) == set(scenario.source_refs)
        CandidateSemanticExtraction.from_json_dict(scenario.legacy_extraction)


def test_evaluate_response_emits_value_safe_record(tmp_path: Path) -> None:
    record = _evaluate(tmp_path)

    assert record["ok"] is True
    assert record["proposal_count"] == 2
    assert record["coverage_record_count"] == 1
    assert record["coverage_complete"] is True
    assert record["unassigned_evidence_count"] == 0
    assert record["blocked_proposal_count"] == 0
    assert record["identity_comparable"] is True
    assert record["identity_issue_count"] == 2
    assert record["identity_reference_count"] == 2
    assert record["identity_set_matches_reference"] is True
    assert record["prompt_sha256"] == REBASELINE._sha256_text(
        REBASELINE.prepare_prompt("split_with_internal_coverage")
    )
    serialized = json.dumps(record)
    assert "primary component" not in serialized
    assert "cache refresh" not in serialized
    assert "excerpt-" not in serialized
    assert "identity_key" not in serialized


def test_identity_mismatch_is_reported_without_exporting_refs(
    tmp_path: Path,
) -> None:
    response = _split_response()
    issue = response["semantic_issue_proposal"]["issues"][0]
    issue["cause_evidence"] = [
        _observation("The primary component is disabled.", "excerpt-001")
    ]
    issue["context_evidence"] = [
        _observation("The original cause excerpt remains covered.", "excerpt-002")
    ]

    record = REBASELINE.evaluate_response(
        scenario_id="split_with_internal_coverage",
        response_path=_write_response(tmp_path, response),
        model_identity="model-current",
        client_identity="desktop-current",
        package_sha256="a" * 64,
        system_prompt_sha256="b" * 64,
        run_index=1,
    )

    assert record["identity_comparable"] is True
    assert record["identity_set_matches_reference"] is False
    serialized = json.dumps(record)
    assert "excerpt-" not in serialized
    assert "identity_key" not in serialized


def test_evaluate_response_rejects_non_exact_wrapper(tmp_path: Path) -> None:
    response = _split_response()
    response["unexpected"] = True

    with pytest.raises(ContractValidationError, match="response invalid"):
        REBASELINE.evaluate_response(
            scenario_id="split_with_internal_coverage",
            response_path=_write_response(tmp_path, response),
            model_identity="model-current",
            client_identity="desktop-current",
            package_sha256="a" * 64,
            system_prompt_sha256="b" * 64,
            run_index=1,
        )


def test_evaluate_response_rejects_identity_mismatch(tmp_path: Path) -> None:
    response = _split_response()
    response["semantic_issue_proposal"]["case_ref"] = "wrong-case-ref"

    with pytest.raises(ContractValidationError, match="identity invalid"):
        REBASELINE.evaluate_response(
            scenario_id="split_with_internal_coverage",
            response_path=_write_response(tmp_path, response),
            model_identity="model-current",
            client_identity="desktop-current",
            package_sha256="a" * 64,
            system_prompt_sha256="b" * 64,
            run_index=1,
        )


def test_cli_error_does_not_echo_invalid_response(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    response_path = _write_response(
        tmp_path,
        {"invalid": "PRIVATE_MODEL_RESPONSE_MARKER"},
    )

    exit_code = REBASELINE.main(
        [
            "evaluate",
            "--scenario",
            "split_with_internal_coverage",
            "--response",
            str(response_path),
            "--model-identity",
            "model-current",
            "--client-identity",
            "desktop-current",
            "--package-sha256",
            "a" * 64,
            "--system-prompt-sha256",
            "b" * 64,
            "--run-index",
            "1",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "semantic_projection_rebaseline_response_invalid" in output
    assert "PRIVATE_MODEL_RESPONSE_MARKER" not in output


def test_summarize_records_requires_and_aggregates_value_safe_records(
    tmp_path: Path,
) -> None:
    paths: list[Path] = []
    for scenario_id in REBASELINE.SCENARIO_IDS:
        for run_index in range(1, 4):
            record = _evaluate(tmp_path, run_index=run_index)
            record["scenario_id"] = scenario_id
            record["prompt_sha256"] = REBASELINE._sha256_text(
                REBASELINE.prepare_prompt(scenario_id)
            )
            expected_count = len(
                REBASELINE._scenario(scenario_id).expected_identities
            )
            record["identity_issue_count"] = expected_count
            record["identity_reference_count"] = expected_count
            record["identity_set_matches_reference"] = True
            run_path = tmp_path / f"{scenario_id}-{run_index}.json"
            run_path.write_text(json.dumps(record), encoding="utf-8")
            paths.append(run_path)

    summary = REBASELINE.summarize_records(paths)

    assert summary["run_count"] == 9
    assert summary["scenario_run_counts"] == {
        "boundary_uncertain": 3,
        "single_customer_issue": 3,
        "split_with_internal_coverage": 3,
    }
    assert summary["proposal_count_distribution"] == {"2": 9}
    assert summary["coverage_complete_runs"] == {
        "denominator": 9,
        "numerator": 9,
    }
    assert summary["identity_comparable_runs"] == {
        "denominator": 9,
        "numerator": 9,
    }
    assert summary["identity_set_match_runs"] == {
        "denominator": 9,
        "numerator": 9,
    }
    assert summary["unassigned_evidence_total"] == 0


def test_summarize_records_rejects_incomplete_matrix(tmp_path: Path) -> None:
    record_path = tmp_path / "run.json"
    record_path.write_text(json.dumps(_evaluate(tmp_path)), encoding="utf-8")

    with pytest.raises(ValueError, match="records invalid"):
        REBASELINE.summarize_records([record_path])


def test_summarize_records_rejects_unknown_fields(tmp_path: Path) -> None:
    record = _evaluate(tmp_path)
    record["raw_model_text"] = "must not be accepted"
    record_path = tmp_path / "run.json"
    record_path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ValueError, match="records invalid"):
        REBASELINE.summarize_records([record_path])


def test_summarize_records_rejects_wrong_prompt_hash(tmp_path: Path) -> None:
    record = _evaluate(tmp_path)
    record["prompt_sha256"] = "c" * 64
    record_path = tmp_path / "run.json"
    record_path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ValueError, match="records invalid"):
        REBASELINE.summarize_records([record_path])
