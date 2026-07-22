"""Export value-safe KCS-14.5 synthetic rebaseline records to local Langfuse."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import os
import re
import secrets
import sys
from collections.abc import Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast
from urllib.parse import urlsplit

from rebaseline_semantic_issue_projection import read_value_safe_record

TRACE_SCHEMA_VERSION = "kcs_langfuse_rebaseline_trace_v3"
RUNTIME_TRACE_SCHEMA_VERSION = "kcs_langfuse_rebaseline_trace_v4"
PROFILE_SCHEMA_VERSION = "kcs_langfuse_control_surface_profile_v1"
RUNTIME_OUTCOME_SCHEMA_VERSION = "kcs_langfuse_runtime_outcome_v1"
PINNED_LANGFUSE_SDK_VERSION = "4.7.0"
_ZERO_SHA256 = "0" * 64
_MAX_PROFILE_BYTES = 8_192
_IDENTITY_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")
_COMMIT_RE = re.compile(r"[0-9a-f]{7,40}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_PROFILE_FIELDS = frozenset(
    {
        "conversation_fresh",
        "package_guidance_profile_id",
        "registry_cache_ok",
        "schema_version",
        "source_commit",
        "source_dirty_state",
        "system_instruction_profile_id",
        "system_prompt_state",
        "tool_instruction_profile_id",
        "tool_surface_profile_id",
    }
)
_RUNTIME_OUTCOME_FIELDS = frozenset(
    {
        "attempted_count",
        "blocked_retryable_count",
        "completed_count",
        "later_candidate_continued",
        "manual_fallback_detected",
        "milestone",
        "native_choice_present",
        "operator_action_kind",
        "overall_verdict",
        "reviewer_bundle_count",
        "run_index",
        "safety_violation",
        "scenario_id",
        "schema_version",
        "selected_count",
        "selection_gate_present",
        "workflow_stopped_count",
    }
)
_RUNTIME_MILESTONES = frozenset(
    {
        "post_kcs14_legacy_baseline",
        "m3_medium",
        "m3_continuation",
        "m3_complex",
    }
)
_COMPARISON_CODE_PREFIXES = (
    "shadow_issue_count",
    "shadow_selectable_count",
    "shadow_issue_source_mapping",
    "shadow_nonissue_source_mapping",
    "shadow_blocked_source_mapping",
    "shadow_origin_distribution",
    "shadow_article_type_distribution",
    "shadow_visibility_distribution",
    "shadow_semantic_content",
)
_COMPARISON_CODES = frozenset(
    f"{prefix}_{outcome}"
    for prefix in _COMPARISON_CODE_PREFIXES
    for outcome in ("match", "mismatch")
) | frozenset(
    {
        "shadow_source_coverage_complete",
        "shadow_source_coverage_incomplete",
        "shadow_blocked_proposals_absent",
        "shadow_blocked_proposals_present",
    }
)
_INVARIANT_CODES = frozenset(
    {
        "source_coverage_passed",
        "operator_authority_absent_passed",
        "kcs_action_authority_absent_passed",
    }
)


class LangfuseRebaselineError(ValueError):
    """One value-safe LF-1 failure classification."""

    def __init__(self, debug_code: str) -> None:
        super().__init__(debug_code)
        self.debug_code = debug_code


class ObservationClient(Protocol):
    """Minimal Langfuse surface used by the external synthetic adapter."""

    def auth_check(self) -> bool: ...

    def start_as_current_observation(
        self, **kwargs: object
    ) -> AbstractContextManager[object]: ...

    def flush(self) -> None: ...


@dataclass(frozen=True)
class RebaselineRunRecord:
    scenario_id: str
    run_index: int
    model_identity: str
    client_identity: str
    package_sha256: str
    system_prompt_sha256: str
    prompt_sha256: str
    projected_sha256: str
    proposal_count: int
    coverage_record_count: int
    coverage_complete: bool
    unassigned_evidence_count: int
    blocked_proposal_count: int
    boundary_uncertainty_count: int
    identity_comparable: bool
    identity_issue_count: int
    identity_reference_count: int
    identity_set_matches_reference: bool
    comparison_codes: tuple[str, ...]
    invariant_codes: tuple[str, ...]

    @classmethod
    def from_path(cls, path: Path) -> RebaselineRunRecord:
        payload = read_value_safe_record(path)
        comparison_codes = _closed_code_tuple(
            payload["comparison_codes"],
            allowed=_COMPARISON_CODES,
        )
        invariant_codes = _closed_code_tuple(
            payload["invariant_codes"],
            allowed=_INVARIANT_CODES,
        )
        return cls(
            scenario_id=cast(str, payload["scenario_id"]),
            run_index=cast(int, payload["run_index"]),
            model_identity=cast(str, payload["model_identity"]),
            client_identity=cast(str, payload["client_identity"]),
            package_sha256=cast(str, payload["package_sha256"]),
            system_prompt_sha256=cast(str, payload["system_prompt_sha256"]),
            prompt_sha256=cast(str, payload["prompt_sha256"]),
            projected_sha256=cast(str, payload["projected_sha256"]),
            proposal_count=cast(int, payload["proposal_count"]),
            coverage_record_count=cast(int, payload["coverage_record_count"]),
            coverage_complete=cast(bool, payload["coverage_complete"]),
            unassigned_evidence_count=cast(int, payload["unassigned_evidence_count"]),
            blocked_proposal_count=cast(int, payload["blocked_proposal_count"]),
            boundary_uncertainty_count=cast(int, payload["boundary_uncertainty_count"]),
            identity_comparable=cast(bool, payload["identity_comparable"]),
            identity_issue_count=cast(int, payload["identity_issue_count"]),
            identity_reference_count=cast(int, payload["identity_reference_count"]),
            identity_set_matches_reference=cast(
                bool, payload["identity_set_matches_reference"]
            ),
            comparison_codes=comparison_codes,
            invariant_codes=invariant_codes,
        )


@dataclass(frozen=True)
class RuntimeOutcome:
    """Closed value-safe outcome for one installed runtime canary."""

    milestone: str
    scenario_id: str
    run_index: int
    operator_action_kind: str
    selection_gate_present: bool
    native_choice_present: bool
    selected_count: int
    attempted_count: int
    completed_count: int
    blocked_retryable_count: int
    workflow_stopped_count: int
    later_candidate_continued: bool
    reviewer_bundle_count: int
    manual_fallback_detected: bool
    safety_violation: bool
    overall_verdict: str

    @classmethod
    def from_path(cls, path: Path) -> RuntimeOutcome:
        payload = _read_runtime_outcome_payload(path)
        outcome = cls(
            milestone=cast(str, payload["milestone"]),
            scenario_id=cast(str, payload["scenario_id"]),
            run_index=cast(int, payload["run_index"]),
            operator_action_kind=cast(str, payload["operator_action_kind"]),
            selection_gate_present=cast(bool, payload["selection_gate_present"]),
            native_choice_present=cast(bool, payload["native_choice_present"]),
            selected_count=cast(int, payload["selected_count"]),
            attempted_count=cast(int, payload["attempted_count"]),
            completed_count=cast(int, payload["completed_count"]),
            blocked_retryable_count=cast(int, payload["blocked_retryable_count"]),
            workflow_stopped_count=cast(int, payload["workflow_stopped_count"]),
            later_candidate_continued=cast(bool, payload["later_candidate_continued"]),
            reviewer_bundle_count=cast(int, payload["reviewer_bundle_count"]),
            manual_fallback_detected=cast(bool, payload["manual_fallback_detected"]),
            safety_violation=cast(bool, payload["safety_violation"]),
            overall_verdict=cast(str, payload["overall_verdict"]),
        )
        outcome._validate()
        return outcome

    def _validate(self) -> None:
        counts = (
            self.selected_count,
            self.attempted_count,
            self.completed_count,
            self.blocked_retryable_count,
            self.workflow_stopped_count,
            self.reviewer_bundle_count,
        )
        requirements = (
            self.milestone in _RUNTIME_MILESTONES,
            _IDENTITY_RE.fullmatch(self.scenario_id) is not None,
            1 <= self.run_index <= 3,
            self.overall_verdict in {"passed", "failed", "blocked"},
            all(_is_bounded_count(value) for value in counts),
            self._counts_are_consistent(),
            self._continuation_is_consistent(),
            self._pass_verdict_is_consistent(),
        )
        if not all(requirements):
            raise LangfuseRebaselineError("langfuse_runtime_outcome_invalid")

    def _counts_are_consistent(self) -> bool:
        selected_by_action = {
            "none": self.selected_count == 0,
            "one": self.selected_count == 1,
            "all": self.selected_count >= 2,
        }.get(self.operator_action_kind, False)
        return all(
            (
                selected_by_action,
                self.attempted_count <= self.selected_count,
                self.accounted_count <= self.attempted_count,
                self.reviewer_bundle_count <= self.completed_count,
            )
        )

    def _continuation_is_consistent(self) -> bool:
        if not self.later_candidate_continued:
            return True
        return self.attempted_count >= 2 and self.blocked_retryable_count >= 1

    def _pass_verdict_is_consistent(self) -> bool:
        if self.overall_verdict != "passed":
            return True
        return all(
            (
                self.selection_gate_present,
                self.native_choice_present,
                self.attempted_count == self.selected_count,
                self.accounted_count == self.attempted_count,
                not self.manual_fallback_detected,
                not self.safety_violation,
                self.workflow_stopped_count == 0,
            )
        )

    @property
    def accounted_count(self) -> int:
        return (
            self.completed_count
            + self.blocked_retryable_count
            + self.workflow_stopped_count
        )


@dataclass(frozen=True)
class ControlSurfaceProfile:
    source_commit: str
    source_dirty_state: str
    registry_cache_ok: bool
    package_guidance_profile_id: str
    tool_surface_profile_id: str
    system_instruction_profile_id: str
    system_prompt_state: str
    conversation_fresh: bool
    tool_instruction_profile_id: str

    @classmethod
    def from_path(cls, path: Path) -> ControlSurfaceProfile:
        payload = _read_profile_payload(path)
        profile = cls(
            source_commit=_required_string(payload, "source_commit"),
            source_dirty_state=_required_string(payload, "source_dirty_state"),
            registry_cache_ok=_required_bool(payload, "registry_cache_ok"),
            package_guidance_profile_id=_required_string(
                payload, "package_guidance_profile_id"
            ),
            tool_surface_profile_id=_required_string(
                payload, "tool_surface_profile_id"
            ),
            system_instruction_profile_id=_required_string(
                payload, "system_instruction_profile_id"
            ),
            system_prompt_state=_required_string(payload, "system_prompt_state"),
            conversation_fresh=_required_bool(payload, "conversation_fresh"),
            tool_instruction_profile_id=_required_string(
                payload, "tool_instruction_profile_id"
            ),
        )
        profile._validate()
        return profile

    def comparable(self, record: RebaselineRunRecord) -> bool:
        identities = (
            record.model_identity,
            record.client_identity,
            self.package_guidance_profile_id,
            self.tool_surface_profile_id,
            self.system_instruction_profile_id,
            self.tool_instruction_profile_id,
        )
        requirements = (
            self.source_dirty_state == "clean",
            self.registry_cache_ok,
            self.system_prompt_state == "current",
            self.conversation_fresh,
            all(identity != "unknown" for identity in identities),
            set(self.source_commit) != {"0"},
            record.package_sha256 != _ZERO_SHA256,
            record.system_prompt_sha256 != _ZERO_SHA256,
        )
        return all(requirements)

    def validate_record(self, record: RebaselineRunRecord) -> None:
        if (
            self.system_prompt_state == "current"
            and record.system_prompt_sha256 == _ZERO_SHA256
        ):
            raise LangfuseRebaselineError("langfuse_rebaseline_profile_invalid")

    def _validate(self) -> None:
        if _COMMIT_RE.fullmatch(self.source_commit) is None:
            raise LangfuseRebaselineError("langfuse_rebaseline_profile_invalid")
        if self.source_dirty_state not in {"clean", "dirty"}:
            raise LangfuseRebaselineError("langfuse_rebaseline_profile_invalid")
        if self.system_prompt_state not in {"current", "stale", "unknown"}:
            raise LangfuseRebaselineError("langfuse_rebaseline_profile_invalid")
        identities = (
            self.package_guidance_profile_id,
            self.tool_surface_profile_id,
            self.system_instruction_profile_id,
            self.tool_instruction_profile_id,
        )
        if any(_IDENTITY_RE.fullmatch(value) is None for value in identities):
            raise LangfuseRebaselineError("langfuse_rebaseline_profile_invalid")


@dataclass(frozen=True)
class ValueSafeTrace:
    record: RebaselineRunRecord
    profile: ControlSurfaceProfile
    run_correlation_sha256: str
    runtime_outcome: RuntimeOutcome | None = None

    @classmethod
    def build(
        cls,
        record: RebaselineRunRecord,
        profile: ControlSurfaceProfile,
        *,
        runtime_outcome: RuntimeOutcome | None = None,
        run_correlation_sha256: str | None = None,
    ) -> ValueSafeTrace:
        profile.validate_record(record)
        if runtime_outcome is not None and (
            not profile.comparable(record)
            or runtime_outcome.scenario_id != record.scenario_id
            or runtime_outcome.run_index != record.run_index
        ):
            raise LangfuseRebaselineError("langfuse_runtime_outcome_invalid")
        correlation = (
            run_correlation_sha256
            or hashlib.sha256(secrets.token_bytes(32)).hexdigest()
        )
        if _SHA256_RE.fullmatch(correlation) is None:
            raise LangfuseRebaselineError("langfuse_rebaseline_record_invalid")
        return cls(record, profile, correlation, runtime_outcome)

    @property
    def telemetry_schema_version(self) -> str:
        if self.runtime_outcome is not None:
            return RUNTIME_TRACE_SCHEMA_VERSION
        return TRACE_SCHEMA_VERSION

    def root_metadata(self) -> dict[str, object]:
        metadata: dict[str, object] = {
            "telemetry_schema_version": self.telemetry_schema_version,
            "run_correlation_sha256": self.run_correlation_sha256,
            "scenario_id": self.record.scenario_id,
            "run_index": self.record.run_index,
            "comparable": self.profile.comparable(self.record),
            "operator_action_kind": (
                self.runtime_outcome.operator_action_kind
                if self.runtime_outcome is not None
                else "none_shadow_only"
            ),
        }
        if self.runtime_outcome is not None:
            metadata["milestone"] = self.runtime_outcome.milestone
        return metadata

    def preflight_metadata(self) -> dict[str, object]:
        return {
            "source_commit": self.profile.source_commit,
            "source_dirty_state": self.profile.source_dirty_state,
            "registry_cache_ok": self.profile.registry_cache_ok,
            "package_guidance_profile_sha256": _sha256_identity(
                self.profile.package_guidance_profile_id
            ),
            "tool_surface_profile_sha256": _sha256_identity(
                self.profile.tool_surface_profile_id
            ),
            "system_instruction_profile_sha256": _sha256_identity(
                self.profile.system_instruction_profile_id
            ),
            "system_prompt_state": self.profile.system_prompt_state,
            "conversation_fresh": self.profile.conversation_fresh,
            "tool_instruction_profile_sha256": _sha256_identity(
                self.profile.tool_instruction_profile_id
            ),
            "model_identity_sha256": _sha256_identity(self.record.model_identity),
            "client_identity_sha256": _sha256_identity(self.record.client_identity),
            "package_sha256": self.record.package_sha256,
            "system_prompt_sha256": self.record.system_prompt_sha256,
            "prompt_sha256": self.record.prompt_sha256,
        }

    def proposal_metadata(self) -> dict[str, object]:
        return {
            "proposal_count": self.record.proposal_count,
            "coverage_record_count": self.record.coverage_record_count,
            "coverage_complete": self.record.coverage_complete,
            "unassigned_evidence_count": self.record.unassigned_evidence_count,
            "packet_schema_version": "semantic_issue_proposal_v1",
        }

    def projection_metadata(self) -> dict[str, object]:
        return {
            "blocked_proposal_count": self.record.blocked_proposal_count,
            "boundary_uncertainty_count": (self.record.boundary_uncertainty_count),
            "identity_comparable": self.record.identity_comparable,
            "identity_issue_count": self.record.identity_issue_count,
            "identity_reference_count": self.record.identity_reference_count,
            "identity_set_matches_reference": (
                self.record.identity_set_matches_reference
            ),
            "comparison_codes": list(self.record.comparison_codes),
            "invariant_codes": list(self.record.invariant_codes),
        }

    def completion_metadata(self) -> dict[str, object]:
        mismatch_count = sum(
            code.endswith("_mismatch") for code in self.record.comparison_codes
        )
        metadata: dict[str, object] = {
            "outcome": (
                "comparable_recorded"
                if self.profile.comparable(self.record)
                else "non_comparable_recorded"
            ),
            "comparison_mismatch_count": mismatch_count,
            "hard_invariant_failed": (
                self.runtime_outcome is not None
                and (
                    self.runtime_outcome.manual_fallback_detected
                    or self.runtime_outcome.safety_violation
                )
            ),
        }
        if self.runtime_outcome is not None:
            metadata.update(
                {
                    "attempted_count": self.runtime_outcome.attempted_count,
                    "blocked_retryable_count": (
                        self.runtime_outcome.blocked_retryable_count
                    ),
                    "completed_count": self.runtime_outcome.completed_count,
                    "later_candidate_continued": (
                        self.runtime_outcome.later_candidate_continued
                    ),
                    "manual_fallback_detected": (
                        self.runtime_outcome.manual_fallback_detected
                    ),
                    "native_choice_present": (
                        self.runtime_outcome.native_choice_present
                    ),
                    "overall_verdict": self.runtime_outcome.overall_verdict,
                    "reviewer_bundle_count": (
                        self.runtime_outcome.reviewer_bundle_count
                    ),
                    "safety_violation": self.runtime_outcome.safety_violation,
                    "selected_count": self.runtime_outcome.selected_count,
                    "selection_gate_present": (
                        self.runtime_outcome.selection_gate_present
                    ),
                    "workflow_stopped_count": (
                        self.runtime_outcome.workflow_stopped_count
                    ),
                }
            )
        return metadata


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        record = RebaselineRunRecord.from_path(args.record)
        profile = ControlSurfaceProfile.from_path(args.profile)
        runtime_outcome = (
            RuntimeOutcome.from_path(args.runtime_outcome)
            if args.runtime_outcome is not None
            else None
        )
        trace = ValueSafeTrace.build(
            record,
            profile,
            runtime_outcome=runtime_outcome,
        )
        client = build_langfuse_client(profile.source_commit)
        if not client.auth_check():
            raise LangfuseRebaselineError("langfuse_rebaseline_auth_failed")
        emit_trace(client, trace)
        _write_json(
            {
                "debug_code": "langfuse_rebaseline_trace_exported",
                "ok": True,
                "run_correlation_sha256": trace.run_correlation_sha256,
                "run_index": record.run_index,
                "scenario_id": record.scenario_id,
                "trace_exported": True,
            }
        )
        return 0
    except LangfuseRebaselineError as exc:
        _write_json({"debug_code": exc.debug_code, "ok": False})
        return 2
    except (ImportError, OSError, ValueError):
        _write_json(
            {"debug_code": "langfuse_rebaseline_export_unavailable", "ok": False}
        )
        return 2
    except Exception:  # External SDK boundary must not expose exception content.
        _write_json(
            {"debug_code": "langfuse_rebaseline_export_unavailable", "ok": False}
        )
        return 2


def build_langfuse_client(source_commit: str) -> ObservationClient:
    """Build an isolated SDK client from loopback-only local configuration."""

    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")
    base_url = os.environ.get("LANGFUSE_BASE_URL", "http://127.0.0.1:3000")
    if (
        not public_key
        or not secret_key
        or len(public_key) > 256
        or len(secret_key) > 256
    ):
        raise LangfuseRebaselineError("langfuse_rebaseline_config_invalid")
    _validate_loopback_url(base_url)
    _require_pinned_langfuse_sdk()
    try:
        langfuse_module = importlib.import_module("langfuse")
        trace_module = importlib.import_module("opentelemetry.sdk.trace")
    except ImportError as exc:
        raise LangfuseRebaselineError(
            "langfuse_rebaseline_dependency_unavailable"
        ) from exc
    client_type = getattr(langfuse_module, "Langfuse")
    tracer_provider_type = getattr(trace_module, "TracerProvider")
    return cast(
        ObservationClient,
        client_type(
            public_key=public_key,
            secret_key=secret_key,
            base_url=base_url,
            timeout=3,
            tracing_enabled=True,
            flush_at=1,
            flush_interval=0.1,
            environment="local-synthetic",
            release=source_commit,
            media_upload_thread_count=1,
            sample_rate=1.0,
            tracer_provider=tracer_provider_type(),
        ),
    )


def _require_pinned_langfuse_sdk() -> None:
    try:
        installed_version = importlib.metadata.version("langfuse")
    except importlib.metadata.PackageNotFoundError as exc:
        raise LangfuseRebaselineError(
            "langfuse_rebaseline_dependency_unavailable"
        ) from exc
    if installed_version != PINNED_LANGFUSE_SDK_VERSION:
        raise LangfuseRebaselineError("langfuse_rebaseline_dependency_unavailable")


def emit_trace(client: ObservationClient, trace: ValueSafeTrace) -> None:
    """Emit one metadata-only trace without input/output capture."""

    with client.start_as_current_observation(
        name="kcs.synthetic_rebaseline_run",
        as_type="evaluator",
        metadata=trace.root_metadata(),
        version=trace.telemetry_schema_version,
    ):
        _emit_span(client, "control_surface.preflight", trace.preflight_metadata())
        _emit_span(client, "semantic_review.proposal", trace.proposal_metadata())
        _emit_span(client, "semantic_review.project", trace.projection_metadata())
        _emit_span(client, "workflow.complete", trace.completion_metadata())
    client.flush()


def _emit_span(
    client: ObservationClient,
    name: str,
    metadata: Mapping[str, object],
) -> None:
    with client.start_as_current_observation(
        name=name,
        as_type="span",
        metadata=dict(metadata),
    ):
        pass


def _read_profile_payload(path: Path) -> Mapping[str, object]:
    return _read_exact_json_payload(
        path,
        fields=_PROFILE_FIELDS,
        schema_version=PROFILE_SCHEMA_VERSION,
        debug_code="langfuse_rebaseline_profile_invalid",
    )


def _read_exact_json_payload(
    path: Path,
    *,
    fields: frozenset[str],
    schema_version: str,
    debug_code: str,
) -> Mapping[str, object]:
    try:
        data = path.read_bytes()
        payload = json.loads(data)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LangfuseRebaselineError(debug_code) from exc
    if not data or len(data) > _MAX_PROFILE_BYTES:
        raise LangfuseRebaselineError(debug_code)
    if not isinstance(payload, dict) or set(payload) != fields:
        raise LangfuseRebaselineError(debug_code)
    if payload.get("schema_version") != schema_version:
        raise LangfuseRebaselineError(debug_code)
    return payload


def _read_runtime_outcome_payload(path: Path) -> Mapping[str, object]:
    payload = _read_exact_json_payload(
        path,
        fields=_RUNTIME_OUTCOME_FIELDS,
        schema_version=RUNTIME_OUTCOME_SCHEMA_VERSION,
        debug_code="langfuse_runtime_outcome_invalid",
    )
    bool_fields = (
        "later_candidate_continued",
        "manual_fallback_detected",
        "native_choice_present",
        "safety_violation",
        "selection_gate_present",
    )
    count_fields = (
        "attempted_count",
        "blocked_retryable_count",
        "completed_count",
        "reviewer_bundle_count",
        "selected_count",
        "workflow_stopped_count",
    )
    string_fields = ("milestone", "operator_action_kind", "overall_verdict")
    if not _runtime_outcome_types_are_valid(
        payload,
        bool_fields=bool_fields,
        count_fields=count_fields,
        string_fields=string_fields,
    ):
        raise LangfuseRebaselineError("langfuse_runtime_outcome_invalid")
    return payload


def _runtime_outcome_types_are_valid(
    payload: Mapping[str, object],
    *,
    bool_fields: tuple[str, ...],
    count_fields: tuple[str, ...],
    string_fields: tuple[str, ...],
) -> bool:
    return all(
        (
            all(isinstance(payload.get(field), bool) for field in bool_fields),
            all(_is_bounded_count(payload.get(field)) for field in count_fields),
            all(isinstance(payload.get(field), str) for field in string_fields),
            isinstance(payload.get("scenario_id"), str),
            _is_run_index(payload.get("run_index")),
        )
    )


def _required_string(payload: Mapping[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str):
        raise LangfuseRebaselineError("langfuse_rebaseline_profile_invalid")
    return value


def _required_bool(payload: Mapping[str, object], field_name: str) -> bool:
    value = payload.get(field_name)
    if not isinstance(value, bool):
        raise LangfuseRebaselineError("langfuse_rebaseline_profile_invalid")
    return value


def _is_bounded_count(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 12


def _is_run_index(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 3


def _closed_code_tuple(value: object, *, allowed: frozenset[str]) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or not value
        or len(value) != len(set(value))
        or any(not isinstance(code, str) or code not in allowed for code in value)
    ):
        raise LangfuseRebaselineError("langfuse_rebaseline_record_invalid")
    return tuple(value)


def _sha256_identity(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _validate_loopback_url(value: str) -> None:
    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        raise LangfuseRebaselineError("langfuse_rebaseline_config_invalid") from exc
    valid_parts = (
        parsed.scheme in {"http", "https"},
        parsed.hostname in {"127.0.0.1", "localhost", "::1"},
        parsed.username is None,
        parsed.password is None,
        not parsed.query,
        not parsed.fragment,
        parsed.path in {"", "/"},
    )
    if not all(valid_parts):
        raise LangfuseRebaselineError("langfuse_rebaseline_config_invalid")
    try:
        if parsed.port is None or not 1 <= parsed.port <= 65_535:
            raise LangfuseRebaselineError("langfuse_rebaseline_config_invalid")
    except ValueError as exc:
        raise LangfuseRebaselineError("langfuse_rebaseline_config_invalid") from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--runtime-outcome", type=Path)
    return parser


def _write_json(payload: Mapping[str, object]) -> None:
    sys.stdout.write(json.dumps(payload, allow_nan=False, sort_keys=True))
    sys.stdout.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
