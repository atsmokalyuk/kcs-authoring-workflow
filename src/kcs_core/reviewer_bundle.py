"""Local reviewer bundle writer for KCS-10 audit/debug artifacts."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from kcs_core.claude_draft import KcsReviewerOnlyDraftArtifact
from kcs_core.claude_handoff import KcsClaudeHandoffRequestPacket
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict, JsonPayload, dump_json_dict
from kcs_core.models import (
    KcsActionDecisionPacket,
    KcsReviewerPacket,
    KcsValidationReportPacket,
    NormalizedTicketEvidencePacket,
)
from kcs_core.sanitizer import ensure_safe_ref, ensure_safe_sanitized_payload
from kcs_core.validation import (
    EvidenceBlocker,
    EvidenceValidationResult,
    validate_evidence_packet,
)

REVIEWER_BUNDLE_MANIFEST_SCHEMA_VERSION = "kcs_reviewer_bundle_manifest_v1"

_MANIFEST_FILE = "manifest.json"
_EVIDENCE_FILE = "evidence_packet.json"
_EVIDENCE_VALIDATION_FILE = "evidence_validation.json"
_DECISION_FILE = "decision_packet.json"
_REVIEWER_PACKET_FILE = "reviewer_packet.json"
_READINESS_REPORT_FILE = "readiness_report.json"
_CLAUDE_HANDOFF_FILE = "claude_handoff_request.json"
_DRAFT_ARTIFACT_FILE = "reviewer_only_draft_artifact.json"


@dataclass(frozen=True)
class KcsReviewerBundle:
    """In-memory reviewer bundle assembled from existing validated KCS packets."""

    bundle_ref: str
    evidence_packet: NormalizedTicketEvidencePacket
    evidence_validation: EvidenceValidationResult
    decision_packet: KcsActionDecisionPacket
    reviewer_packet: KcsReviewerPacket
    readiness_report: KcsValidationReportPacket
    claude_handoff_request: KcsClaudeHandoffRequestPacket | None = None
    reviewer_only_draft_artifact: KcsReviewerOnlyDraftArtifact | None = None
    reviewer_only: bool = True
    auto_publish_allowed: bool = False
    public_output_approved: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "bundle_ref",
            ensure_safe_ref(self.bundle_ref, label="bundle_ref"),
        )
        if self.reviewer_only is not True:
            raise ContractValidationError("reviewer bundle must be reviewer-only")
        _require_false(self.auto_publish_allowed, "auto_publish_allowed")
        _require_false(self.public_output_approved, "public_output_approved")
        _validate_bundle_consistency(self)
        if EvidenceBlocker.UNSAFE_INPUT.value in self.evidence_validation.blockers:
            raise ContractValidationError("reviewer bundle evidence is unsafe")
        for payload in self._payloads().values():
            ensure_safe_sanitized_payload(payload)
        _validate_evidence_validation_matches(self)

    @property
    def case_ref(self) -> str:
        return self.evidence_packet.case_ref

    def file_payloads(self) -> dict[str, JsonDict]:
        """Return deterministic file payloads excluding the manifest."""

        return self._payloads()

    def manifest_json_dict(self) -> JsonDict:
        """Return the safe manifest/index for this bundle."""

        files = [
            {
                "name": name,
                "role": role,
                "sha256": _sha256_json(payload),
                "schema_version": _payload_schema_version(payload),
            }
            for name, role, payload in _bundle_file_entries(self)
        ]
        manifest: JsonDict = {
            "schema_version": REVIEWER_BUNDLE_MANIFEST_SCHEMA_VERSION,
            "bundle_ref": self.bundle_ref,
            "case_ref": self.case_ref,
            "reviewer_only": True,
            "auto_publish_allowed": False,
            "public_output_approved": False,
            "recommended_action": self.decision_packet.recommended_action,
            "article_type": self.decision_packet.article_type,
            "decision_status": self.decision_packet.status,
            "readiness_state": self.readiness_report.state,
            "ready_for_reviewer": self.readiness_report.ready_for_reviewer,
            "has_claude_handoff": self.claude_handoff_request is not None,
            "has_reviewer_only_draft_artifact": (
                self.reviewer_only_draft_artifact is not None
            ),
            "files": files,
        }
        ensure_safe_sanitized_payload(manifest)
        return manifest

    def _payloads(self) -> dict[str, JsonDict]:
        return {
            name: payload for name, _role, payload in _bundle_file_entries(self)
        }


def build_reviewer_bundle(
    *,
    bundle_ref: str,
    evidence_packet: NormalizedTicketEvidencePacket,
    evidence_validation: EvidenceValidationResult,
    decision_packet: KcsActionDecisionPacket,
    reviewer_packet: KcsReviewerPacket,
    readiness_report: KcsValidationReportPacket,
    claude_handoff_request: KcsClaudeHandoffRequestPacket | None = None,
    reviewer_only_draft_artifact: KcsReviewerOnlyDraftArtifact | None = None,
) -> KcsReviewerBundle:
    """Build a local reviewer bundle from existing KCS packet objects."""

    return KcsReviewerBundle(
        bundle_ref=bundle_ref,
        evidence_packet=evidence_packet,
        evidence_validation=evidence_validation,
        decision_packet=decision_packet,
        reviewer_packet=reviewer_packet,
        readiness_report=readiness_report,
        claude_handoff_request=claude_handoff_request,
        reviewer_only_draft_artifact=reviewer_only_draft_artifact,
    )


def write_reviewer_bundle(bundle: KcsReviewerBundle, output_dir: Path) -> Path:
    """Write a fixed local reviewer bundle directory and return manifest path."""

    output_dir = _prepare_output_dir(output_dir)
    payloads = bundle.file_payloads()
    all_payloads = {_MANIFEST_FILE: bundle.manifest_json_dict(), **payloads}
    target_paths = {name: output_dir / name for name in all_payloads}
    temp_paths = {
        name: path.with_name(f".{path.name}.tmp")
        for name, path in target_paths.items()
    }
    for path in tuple(target_paths.values()) + tuple(temp_paths.values()):
        _reject_symlink_path(path)
        if path.exists() or path.is_symlink():
            raise ContractValidationError("refusing to overwrite reviewer bundle")
    written: list[Path] = []
    created_temps: list[Path] = []
    try:
        for name, payload in all_payloads.items():
            target = target_paths[name]
            temp = temp_paths[name]
            _write_json_file(temp, payload)
            created_temps.append(temp)
            temp.replace(target)
            written.append(target)
    except OSError:
        for path in created_temps + written:
            _cleanup_path(path)
        raise ContractValidationError("could not write reviewer bundle") from None
    return target_paths[_MANIFEST_FILE]


def _bundle_file_entries(
    bundle: KcsReviewerBundle,
) -> tuple[tuple[str, str, JsonDict], ...]:
    entries: list[tuple[str, str, JsonDict]] = [
        (_EVIDENCE_FILE, "evidence_packet", _packet_json(bundle.evidence_packet)),
        (
            _EVIDENCE_VALIDATION_FILE,
            "evidence_validation",
            _packet_json(bundle.evidence_validation),
        ),
        (_DECISION_FILE, "decision_packet", _packet_json(bundle.decision_packet)),
        (
            _REVIEWER_PACKET_FILE,
            "reviewer_packet",
            _packet_json(bundle.reviewer_packet),
        ),
        (
            _READINESS_REPORT_FILE,
            "readiness_report",
            _packet_json(bundle.readiness_report),
        ),
    ]
    if bundle.claude_handoff_request is not None:
        entries.append(
            (
                _CLAUDE_HANDOFF_FILE,
                "claude_handoff_request",
                _packet_json(bundle.claude_handoff_request),
            )
        )
    if bundle.reviewer_only_draft_artifact is not None:
        entries.append(
            (
                _DRAFT_ARTIFACT_FILE,
                "reviewer_only_draft_artifact",
                _packet_json(bundle.reviewer_only_draft_artifact),
            )
        )
    return tuple(entries)


def _validate_bundle_consistency(bundle: KcsReviewerBundle) -> None:
    case_ref = bundle.evidence_packet.case_ref
    _validate_base_packet_consistency(bundle, case_ref)
    if bundle.claude_handoff_request is not None:
        _validate_handoff_consistency(bundle, case_ref)
    if bundle.reviewer_only_draft_artifact is not None:
        if bundle.claude_handoff_request is None:
            raise ContractValidationError("reviewer bundle draft requires handoff")
        _validate_draft_artifact_consistency(bundle, case_ref)


def _validate_evidence_validation_matches(bundle: KcsReviewerBundle) -> None:
    actual = validate_evidence_packet(bundle.evidence_packet).to_json_dict()
    provided = bundle.evidence_validation.to_json_dict()
    if actual != provided:
        raise ContractValidationError("reviewer bundle evidence validation mismatch")


def _validate_base_packet_consistency(
    bundle: KcsReviewerBundle,
    case_ref: str,
) -> None:
    if bundle.reviewer_packet.case_ref != case_ref:
        raise ContractValidationError("reviewer bundle case_ref mismatch")
    if bundle.readiness_report.case_ref != case_ref:
        raise ContractValidationError("reviewer bundle case_ref mismatch")
    if (
        bundle.reviewer_packet.recommended_action
        != bundle.decision_packet.recommended_action
    ):
        raise ContractValidationError("reviewer bundle action mismatch")
    summary_action = bundle.readiness_report.decision_summary.get("recommended_action")
    if summary_action != bundle.decision_packet.recommended_action:
        raise ContractValidationError("reviewer bundle action mismatch")


def _validate_handoff_consistency(bundle: KcsReviewerBundle, case_ref: str) -> None:
    handoff = bundle.claude_handoff_request
    assert handoff is not None
    if handoff.case_ref != case_ref:
        raise ContractValidationError("reviewer bundle case_ref mismatch")
    if handoff.original_recommended_action != bundle.decision_packet.recommended_action:
        raise ContractValidationError("reviewer bundle action mismatch")
    if handoff.original_article_type != bundle.decision_packet.article_type:
        raise ContractValidationError("reviewer bundle article_type mismatch")
    if handoff.original_decision_status != bundle.decision_packet.status:
        raise ContractValidationError("reviewer bundle decision status mismatch")
    if handoff.original_readiness_state != bundle.readiness_report.state:
        raise ContractValidationError("reviewer bundle readiness mismatch")


def _validate_draft_artifact_consistency(
    bundle: KcsReviewerBundle,
    case_ref: str,
) -> None:
    artifact = bundle.reviewer_only_draft_artifact
    handoff = bundle.claude_handoff_request
    assert artifact is not None and handoff is not None
    if artifact.case_ref != case_ref:
        raise ContractValidationError("reviewer bundle case_ref mismatch")
    if artifact.handoff_ref != handoff.handoff_ref:
        raise ContractValidationError("reviewer bundle handoff mismatch")
    if (
        artifact.original_recommended_action
        != bundle.decision_packet.recommended_action
    ):
        raise ContractValidationError("reviewer bundle action mismatch")
    if artifact.original_article_type != bundle.decision_packet.article_type:
        raise ContractValidationError("reviewer bundle article_type mismatch")
    if artifact.original_decision_status != bundle.decision_packet.status:
        raise ContractValidationError("reviewer bundle decision status mismatch")
    if artifact.original_readiness_state != bundle.readiness_report.state:
        raise ContractValidationError("reviewer bundle readiness mismatch")


def _packet_json(packet: JsonPayload) -> JsonDict:
    data = dump_json_dict(packet)
    ensure_safe_sanitized_payload(data)
    return data


def _payload_schema_version(payload: Mapping[str, Any]) -> str:
    value = payload.get("schema_version")
    return value if isinstance(value, str) else ""


def _sha256_json(payload: Mapping[str, Any]) -> str:
    text = json.dumps(
        payload,
        sort_keys=True,
        allow_nan=False,
        separators=(",", ":"),
    )
    return sha256(text.encode("utf-8")).hexdigest()


def _json_text(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, allow_nan=False, indent=2) + "\n"


def _prepare_output_dir(path: Path) -> Path:
    if ".." in path.parts:
        raise ContractValidationError("reviewer bundle path invalid")
    for parent in path.parents:
        if parent.exists() and parent.is_symlink():
            raise ContractValidationError("reviewer bundle path must not use symlinks")
    if path.exists() and path.is_symlink():
        raise ContractValidationError("reviewer bundle path must not use symlinks")
    if path.exists() and not path.is_dir():
        raise ContractValidationError("reviewer bundle path invalid")
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        raise ContractValidationError("could not create reviewer bundle") from None
    return path


def _write_json_file(path: Path, payload: Mapping[str, Any]) -> None:
    text = _json_text(payload)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)


def _reject_symlink_path(path: Path) -> None:
    if path.is_symlink():
        raise ContractValidationError("reviewer bundle path must not use symlinks")


def _cleanup_path(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return
    except OSError:
        return


def _require_false(value: object, label: str) -> None:
    if value is not False:
        raise ContractValidationError(f"{label} must be false")
