from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

import kcs_core
from kcs_core.claude_draft import (
    ClaudeDraftProviderErrorCode,
    ClaudeDraftStatus,
    build_claude_draft_request,
    build_reviewer_only_draft_artifact,
    validate_claude_draft_response,
)
from kcs_core.claude_handoff import build_claude_handoff_request
from kcs_core.decision import decide_kcs_action
from kcs_core.errors import ContractValidationError
from kcs_core.models import (
    KcsReviewerPacket,
    NormalizedTicketEvidencePacket,
    ReuseSearchResultsPacket,
)
from kcs_core.readiness import build_validation_report
from kcs_core.renderer import render_reviewer_packet
from kcs_core.reviewer_bundle import (
    REVIEWER_BUNDLE_MANIFEST_SCHEMA_VERSION,
    KcsReviewerBundle,
    build_reviewer_bundle,
    write_reviewer_bundle,
)
from kcs_core.validation import EvidenceValidationResult, validate_evidence_packet

FIXTURE_ROOT = Path(__file__).with_name("cli_fixtures")


def _bundle_parts() -> dict[str, Any]:
    base = FIXTURE_ROOT / "003_create_candidate"
    evidence = NormalizedTicketEvidencePacket.from_json_dict(
        _load_json(base / "evidence_packet.json")
    )
    reuse = ReuseSearchResultsPacket.from_json_dict(
        _load_json(base / "reuse_results.json")
    )
    evidence_validation = validate_evidence_packet(evidence)
    decision = decide_kcs_action(evidence, reuse)
    reviewer_packet = render_reviewer_packet(evidence, decision)
    readiness_report = build_validation_report(evidence, decision, reviewer_packet)
    handoff = build_claude_handoff_request(
        decision,
        readiness_report,
        handoff_ref="handoff-001",
        safe_context={
            "short_public_safe_summary": "Synthetic safe bundle summary.",
            "title_hint": "Synthetic safe title",
        },
    )
    draft_request = build_claude_draft_request(handoff, draft_ref="draft-001")
    draft_response = validate_claude_draft_response(
        {
            "applicable_to": "Plesk for Linux",
            "article_type": draft_request.original_article_type,
            "auto_publish_allowed": False,
            "draft_status": ClaudeDraftStatus.ACCEPTED.value,
            "handoff_ref": draft_request.handoff_ref,
            "internal_only_content_present": False,
            "original_article_type": draft_request.original_article_type,
            "original_decision_status": draft_request.original_decision_status,
            "original_readiness_state": draft_request.original_readiness_state,
            "original_recommended_action": draft_request.original_recommended_action,
            "provider_error_code": ClaudeDraftProviderErrorCode.NONE.value,
            "public_output_approved": False,
            "reviewer_notes": ["Reviewer should validate this synthetic draft."],
            "schema_version": "kcs_claude_draft_response_v1",
            "sections": {
                "cause": "A supported product condition causes this symptom.",
                "resolution": "Apply the documented product-side correction.",
                "symptoms": "A supported product task fails.",
            },
            "title": "Synthetic reviewer-only KCS draft",
            "unsupported_claims_present": False,
            "zendesk_source_html": (
                "<h1>Synthetic reviewer-only KCS draft</h1>"
                "<h2>Applicable to</h2><p>Plesk for Linux</p>"
                "<h2>Symptoms</h2><p>A supported product task fails.</p>"
                "<h2>Cause</h2><p>A supported product condition causes this.</p>"
                "<h2>Resolution</h2><ol><li>Apply the correction.</li></ol>"
            ),
        },
        request=draft_request,
    )
    draft_artifact = build_reviewer_only_draft_artifact(
        draft_request,
        draft_response,
        artifact_ref="artifact-001",
    )
    return {
        "evidence_packet": evidence,
        "evidence_validation": evidence_validation,
        "decision_packet": decision,
        "reviewer_packet": reviewer_packet,
        "readiness_report": readiness_report,
        "claude_handoff_request": handoff,
        "reviewer_only_draft_artifact": draft_artifact,
    }


def _bundle(**overrides: object) -> KcsReviewerBundle:
    values = _bundle_parts()
    values.update(overrides)
    return build_reviewer_bundle(bundle_ref="bundle-001", **values)


def test_build_and_write_reviewer_bundle(tmp_path: Path) -> None:
    bundle = _bundle()
    manifest_path = write_reviewer_bundle(bundle, tmp_path / "bundle")
    manifest = _load_json(manifest_path)

    assert manifest["schema_version"] == REVIEWER_BUNDLE_MANIFEST_SCHEMA_VERSION
    assert manifest["reviewer_only"] is True
    assert manifest["auto_publish_allowed"] is False
    assert manifest["public_output_approved"] is False
    assert manifest["recommended_action"] == "create_candidate"
    assert manifest["readiness_state"] == "ready_for_reviewer"
    assert manifest["has_claude_handoff"] is True
    assert manifest["has_reviewer_only_draft_artifact"] is True
    expected_files = {
        "manifest.json",
        "evidence_packet.json",
        "evidence_validation.json",
        "decision_packet.json",
        "reviewer_packet.json",
        "readiness_report.json",
        "claude_handoff_request.json",
        "reviewer_only_draft_artifact.json",
    }
    assert {path.name for path in manifest_path.parent.iterdir()} == expected_files
    for file_entry in manifest["files"]:
        file_path = manifest_path.parent / file_entry["name"]
        assert file_path.stat().st_mode & 0o777 == 0o600
        assert _sha256_json(_load_json(file_path)) == file_entry["sha256"]


def test_reviewer_bundle_can_omit_optional_claude_artifacts(tmp_path: Path) -> None:
    bundle = _bundle(
        claude_handoff_request=None,
        reviewer_only_draft_artifact=None,
    )
    manifest_path = write_reviewer_bundle(bundle, tmp_path / "bundle")
    manifest = _load_json(manifest_path)

    assert manifest["has_claude_handoff"] is False
    assert manifest["has_reviewer_only_draft_artifact"] is False
    assert "claude_handoff_request.json" not in {
        path.name for path in manifest_path.parent.iterdir()
    }


def test_reviewer_bundle_rejects_case_mismatch() -> None:
    values = _bundle_parts()
    reviewer_packet = values["reviewer_packet"]
    values["reviewer_packet"] = KcsReviewerPacket(
        case_ref="other-case",
        recommended_action=reviewer_packet.recommended_action,
        review_required=reviewer_packet.review_required,
        public_article_candidate=reviewer_packet.public_article_candidate,
        internal_reviewer_notes=reviewer_packet.internal_reviewer_notes,
        evidence_basis=reviewer_packet.evidence_basis,
        validation_report=reviewer_packet.validation_report,
        zendesk_source_html=reviewer_packet.zendesk_source_html,
        auto_publish_allowed=False,
    )

    with pytest.raises(ContractValidationError):
        build_reviewer_bundle(bundle_ref="bundle-001", **values)


def test_reviewer_bundle_rejects_unsafe_payload_without_echo() -> None:
    values = _bundle_parts()
    private_value = "person@example.com"
    evidence = values["evidence_packet"]
    values["evidence_packet"] = NormalizedTicketEvidencePacket(
        case_ref=evidence.case_ref,
        input_class=evidence.input_class,
        source_refs=evidence.source_refs,
        issue_candidates=evidence.issue_candidates,
        environment=evidence.environment,
        symptoms=[private_value],
        confirmed_facts=evidence.confirmed_facts,
        supported_cause=evidence.supported_cause,
        supported_resolution_or_workaround=evidence.supported_resolution_or_workaround,
        open_questions=evidence.open_questions,
        visibility_summary=evidence.visibility_summary,
        sanitizer_report=evidence.sanitizer_report,
    )

    with pytest.raises(ContractValidationError) as captured:
        build_reviewer_bundle(bundle_ref="bundle-001", **values)

    assert private_value not in str(captured.value)


def test_reviewer_bundle_rejects_stale_evidence_validation() -> None:
    values = _bundle_parts()
    evidence = values["evidence_packet"]
    payload = evidence.to_json_dict()
    payload["supported_resolution_or_workaround"] = ""
    values["evidence_packet"] = NormalizedTicketEvidencePacket.from_json_dict(payload)
    values["evidence_validation"] = EvidenceValidationResult(
        ok=True,
        blockers=(),
        warnings=(),
    )

    with pytest.raises(ContractValidationError):
        build_reviewer_bundle(bundle_ref="bundle-001", **values)


def test_reviewer_bundle_rejects_draft_artifact_without_handoff() -> None:
    values = _bundle_parts()
    values["claude_handoff_request"] = None

    with pytest.raises(ContractValidationError):
        build_reviewer_bundle(bundle_ref="bundle-001", **values)


def test_reviewer_bundle_writer_rejects_overwrite_symlink_and_traversal(
    tmp_path: Path,
) -> None:
    bundle = _bundle()
    output_dir = tmp_path / "bundle"
    write_reviewer_bundle(bundle, output_dir)

    with pytest.raises(ContractValidationError):
        write_reviewer_bundle(bundle, output_dir)

    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ContractValidationError):
        write_reviewer_bundle(bundle, link)

    with pytest.raises(ContractValidationError):
        write_reviewer_bundle(bundle, link / "bundle")

    with pytest.raises(ContractValidationError):
        write_reviewer_bundle(bundle, tmp_path / ".." / "outside")


def test_writer_does_not_delete_preexisting_temp_file(tmp_path: Path) -> None:
    bundle = _bundle()
    output_dir = tmp_path / "bundle"
    output_dir.mkdir()
    temp = output_dir / ".manifest.json.tmp"
    temp.write_text("do not delete", encoding="utf-8")

    with pytest.raises(ContractValidationError):
        write_reviewer_bundle(bundle, output_dir)

    assert temp.exists()
    assert temp.read_text(encoding="utf-8") == "do not delete"


def test_root_exports_include_kcs_10_api() -> None:
    assert kcs_core.KcsReviewerBundle is KcsReviewerBundle
    assert kcs_core.build_reviewer_bundle is build_reviewer_bundle
    assert kcs_core.write_reviewer_bundle is write_reviewer_bundle
    assert (
        kcs_core.REVIEWER_BUNDLE_MANIFEST_SCHEMA_VERSION
        == REVIEWER_BUNDLE_MANIFEST_SCHEMA_VERSION
    )


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _sha256_json(payload: dict[str, Any]) -> str:
    text = json.dumps(
        payload,
        sort_keys=True,
        allow_nan=False,
        separators=(",", ":"),
    )
    return sha256(text.encode("utf-8")).hexdigest()
