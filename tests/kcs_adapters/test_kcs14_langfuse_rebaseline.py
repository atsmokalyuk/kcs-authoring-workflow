from __future__ import annotations

import importlib.util
import json
import sys
from contextlib import AbstractContextManager
from pathlib import Path
from types import TracebackType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
SCRIPT = SCRIPTS / "kcs14_langfuse_rebaseline.py"


def _load_module():
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location(
            "kcs14_langfuse_rebaseline",
            SCRIPT,
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPTS))


LF1 = _load_module()
REBASELINE = sys.modules["rebaseline_semantic_issue_projection"]


class _ObservationContext(AbstractContextManager[object]):
    def __enter__(self) -> object:
        return object()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


class _FakeClient:
    def __init__(self, *, auth_ok: bool = True) -> None:
        self.auth_ok = auth_ok
        self.calls: list[dict[str, object]] = []
        self.flush_count = 0

    def auth_check(self) -> bool:
        return self.auth_ok

    def start_as_current_observation(
        self, **kwargs: object
    ) -> AbstractContextManager[object]:
        self.calls.append(dict(kwargs))
        return _ObservationContext()

    def flush(self) -> None:
        self.flush_count += 1


def _record_payload() -> dict[str, object]:
    scenario_id = "split_with_internal_coverage"
    return {
        "blocked_proposal_count": 0,
        "boundary_uncertainty_count": 0,
        "client_identity": "desktop-current",
        "comparison_codes": [
            "shadow_issue_count_match",
            "shadow_selectable_count_match",
            "shadow_issue_source_mapping_match",
            "shadow_nonissue_source_mapping_match",
            "shadow_blocked_source_mapping_match",
            "shadow_origin_distribution_match",
            "shadow_article_type_distribution_match",
            "shadow_visibility_distribution_match",
            "shadow_semantic_content_mismatch",
            "shadow_source_coverage_complete",
            "shadow_blocked_proposals_absent",
        ],
        "coverage_complete": True,
        "coverage_record_count": 1,
        "invariant_codes": [
            "source_coverage_passed",
            "operator_authority_absent_passed",
            "kcs_action_authority_absent_passed",
        ],
        "identity_comparable": True,
        "identity_issue_count": 2,
        "identity_reference_count": 2,
        "identity_set_matches_reference": True,
        "model_identity": "model-current",
        "ok": True,
        "package_sha256": "a" * 64,
        "projected_sha256": "c" * 64,
        "prompt_sha256": REBASELINE._sha256_text(
            REBASELINE.prepare_prompt(scenario_id)
        ),
        "proposal_count": 2,
        "run_index": 1,
        "scenario_id": scenario_id,
        "schema_version": "kcs_semantic_projection_rebaseline_run_v2",
        "system_prompt_sha256": "b" * 64,
        "unassigned_evidence_count": 0,
    }


def _profile_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "conversation_fresh": True,
        "package_guidance_profile_id": "kcs-mcpb-guidance-v1",
        "registry_cache_ok": True,
        "schema_version": "kcs_langfuse_control_surface_profile_v1",
        "source_commit": "85895b1",
        "source_dirty_state": "clean",
        "system_instruction_profile_id": "claude-support-v1",
        "system_prompt_state": "current",
        "tool_instruction_profile_id": "semantic-issue-shadow-v1",
        "tool_surface_profile_id": "kcs-desktop-tools-v1",
    }
    payload.update(overrides)
    return payload


def _runtime_outcome_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "attempted_count": 2,
        "blocked_retryable_count": 1,
        "completed_count": 1,
        "later_candidate_continued": True,
        "manual_fallback_detected": False,
        "milestone": "m3_continuation",
        "native_choice_present": True,
        "operator_action_kind": "all",
        "overall_verdict": "passed",
        "reviewer_bundle_count": 1,
        "run_index": 1,
        "safety_violation": False,
        "scenario_id": "split_with_internal_coverage",
        "schema_version": "kcs_langfuse_runtime_outcome_v1",
        "selected_count": 2,
        "selection_gate_present": True,
        "workflow_stopped_count": 0,
    }
    payload.update(overrides)
    return payload


def _write_json(tmp_path: Path, name: str, payload: object) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _trace(tmp_path: Path, *, with_runtime_outcome: bool = False):
    record = LF1.RebaselineRunRecord.from_path(
        _write_json(tmp_path, "record.json", _record_payload())
    )
    profile = LF1.ControlSurfaceProfile.from_path(
        _write_json(tmp_path, "profile.json", _profile_payload())
    )
    runtime_outcome = None
    if with_runtime_outcome:
        runtime_outcome = LF1.RuntimeOutcome.from_path(
            _write_json(
                tmp_path,
                "runtime-outcome.json",
                _runtime_outcome_payload(),
            )
        )
    return LF1.ValueSafeTrace.build(
        record,
        profile,
        runtime_outcome=runtime_outcome,
        run_correlation_sha256="d" * 64,
    )


def test_trace_is_comparable_and_contains_only_value_safe_fields(
    tmp_path: Path,
) -> None:
    trace = _trace(tmp_path)

    assert trace.profile.comparable(trace.record) is True
    assert trace.root_metadata() == {
        "telemetry_schema_version": "kcs_langfuse_rebaseline_trace_v3",
        "run_correlation_sha256": "d" * 64,
        "scenario_id": "split_with_internal_coverage",
        "run_index": 1,
        "comparable": True,
        "operator_action_kind": "none_shadow_only",
    }
    assert trace.projection_metadata()["identity_comparable"] is True
    assert trace.projection_metadata()["identity_issue_count"] == 2
    assert trace.projection_metadata()["identity_reference_count"] == 2
    assert trace.projection_metadata()["identity_set_matches_reference"] is True
    assert "projected_sha256" not in trace.projection_metadata()
    serialized = json.dumps(
        {
            **trace.root_metadata(),
            **trace.preflight_metadata(),
            **trace.proposal_metadata(),
            **trace.projection_metadata(),
            **trace.completion_metadata(),
        }
    )
    for forbidden in (
        "ticket_ref",
        "candidate_title",
        "reviewer_bundle",
        "PRIVATE_MARKER",
        "input",
        "output",
        "excerpt-",
        "identity_key",
    ):
        assert forbidden not in serialized


def test_unknown_system_profile_is_exportable_but_not_comparable(
    tmp_path: Path,
) -> None:
    record_payload = _record_payload()
    record_payload["system_prompt_sha256"] = "0" * 64
    record = LF1.RebaselineRunRecord.from_path(
        _write_json(tmp_path, "record.json", record_payload)
    )
    profile = LF1.ControlSurfaceProfile.from_path(
        _write_json(
            tmp_path,
            "profile.json",
            _profile_payload(
                system_instruction_profile_id="unknown",
                system_prompt_state="unknown",
            ),
        )
    )

    trace = LF1.ValueSafeTrace.build(record, profile)

    assert profile.comparable(record) is False
    assert trace.completion_metadata()["outcome"] == "non_comparable_recorded"


def test_runtime_outcome_adds_closed_progress_metadata(tmp_path: Path) -> None:
    trace = _trace(tmp_path, with_runtime_outcome=True)

    assert trace.root_metadata() == {
        "telemetry_schema_version": "kcs_langfuse_rebaseline_trace_v4",
        "run_correlation_sha256": "d" * 64,
        "scenario_id": "split_with_internal_coverage",
        "run_index": 1,
        "comparable": True,
        "milestone": "m3_continuation",
        "operator_action_kind": "all",
    }
    assert trace.completion_metadata() == {
        "attempted_count": 2,
        "blocked_retryable_count": 1,
        "completed_count": 1,
        "comparison_mismatch_count": 1,
        "hard_invariant_failed": False,
        "later_candidate_continued": True,
        "manual_fallback_detected": False,
        "native_choice_present": True,
        "outcome": "comparable_recorded",
        "overall_verdict": "passed",
        "reviewer_bundle_count": 1,
        "safety_violation": False,
        "selected_count": 2,
        "selection_gate_present": True,
        "workflow_stopped_count": 0,
    }


def test_runtime_outcome_must_match_canonical_record_identity(
    tmp_path: Path,
) -> None:
    record = LF1.RebaselineRunRecord.from_path(
        _write_json(tmp_path, "record.json", _record_payload())
    )
    profile = LF1.ControlSurfaceProfile.from_path(
        _write_json(tmp_path, "profile.json", _profile_payload())
    )
    outcome = LF1.RuntimeOutcome.from_path(
        _write_json(
            tmp_path,
            "runtime-outcome.json",
            _runtime_outcome_payload(run_index=2),
        )
    )

    with pytest.raises(
        LF1.LangfuseRebaselineError,
        match="langfuse_runtime_outcome_invalid",
    ):
        LF1.ValueSafeTrace.build(record, profile, runtime_outcome=outcome)


def test_none_action_can_pass_without_candidate_attempts(tmp_path: Path) -> None:
    outcome = LF1.RuntimeOutcome.from_path(
        _write_json(
            tmp_path,
            "runtime-outcome.json",
            _runtime_outcome_payload(
                attempted_count=0,
                blocked_retryable_count=0,
                completed_count=0,
                later_candidate_continued=False,
                operator_action_kind="none",
                reviewer_bundle_count=0,
                selected_count=0,
            ),
        )
    )

    assert outcome.overall_verdict == "passed"
    assert outcome.accounted_count == 0


def test_noncomparable_runtime_outcome_is_rejected_before_export(
    tmp_path: Path,
) -> None:
    record = LF1.RebaselineRunRecord.from_path(
        _write_json(tmp_path, "record.json", _record_payload())
    )
    profile = LF1.ControlSurfaceProfile.from_path(
        _write_json(
            tmp_path,
            "profile.json",
            _profile_payload(source_dirty_state="dirty"),
        )
    )
    outcome = LF1.RuntimeOutcome.from_path(
        _write_json(
            tmp_path,
            "runtime-outcome.json",
            _runtime_outcome_payload(),
        )
    )

    with pytest.raises(
        LF1.LangfuseRebaselineError,
        match="langfuse_runtime_outcome_invalid",
    ):
        LF1.ValueSafeTrace.build(
            record,
            profile,
            runtime_outcome=outcome,
        )


def test_committed_runtime_outcome_example_is_valid() -> None:
    outcome = LF1.RuntimeOutcome.from_path(
        ROOT / "evals" / "kcs14_langfuse_runtime_outcome.example.json"
    )

    assert outcome.milestone == "m3_continuation"
    assert outcome.overall_verdict == "passed"


@pytest.mark.parametrize(
    "overrides",
    [
        {"milestone": "ticket-example-multi"},
        {"operator_action_kind": "both"},
        {"private_ticket": "PRIVATE_MARKER"},
        {"selected_count": 1},
        {"attempted_count": 3},
        {"reviewer_bundle_count": 2},
        {"later_candidate_continued": True, "blocked_retryable_count": 0},
        {"overall_verdict": "passed", "manual_fallback_detected": True},
        {"overall_verdict": "passed", "safety_violation": True},
    ],
)
def test_runtime_outcome_rejects_unknown_or_inconsistent_values(
    tmp_path: Path,
    overrides: dict[str, object],
) -> None:
    with pytest.raises(
        LF1.LangfuseRebaselineError,
        match="langfuse_runtime_outcome_invalid",
    ):
        LF1.RuntimeOutcome.from_path(
            _write_json(
                tmp_path,
                "runtime-outcome.json",
                _runtime_outcome_payload(**overrides),
            )
        )


def test_runtime_outcome_is_optional_for_existing_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client = _FakeClient()
    monkeypatch.setattr(LF1, "build_langfuse_client", lambda _: client)

    exit_code = LF1.main(
        [
            "--record",
            str(_write_json(tmp_path, "record.json", _record_payload())),
            "--profile",
            str(_write_json(tmp_path, "profile.json", _profile_payload())),
        ]
    )

    assert exit_code == 0
    assert "langfuse_rebaseline_trace_exported" in capsys.readouterr().out
    assert client.calls[0]["metadata"]["operator_action_kind"] == ("none_shadow_only")


def test_runtime_outcome_cli_exports_progress_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client = _FakeClient()
    monkeypatch.setattr(LF1, "build_langfuse_client", lambda _: client)

    exit_code = LF1.main(
        [
            "--record",
            str(_write_json(tmp_path, "record.json", _record_payload())),
            "--profile",
            str(_write_json(tmp_path, "profile.json", _profile_payload())),
            "--runtime-outcome",
            str(
                _write_json(
                    tmp_path,
                    "runtime-outcome.json",
                    _runtime_outcome_payload(),
                )
            ),
        ]
    )

    assert exit_code == 0
    assert "langfuse_rebaseline_trace_exported" in capsys.readouterr().out
    assert client.calls[0]["metadata"]["milestone"] == "m3_continuation"
    assert client.calls[-1]["metadata"]["later_candidate_continued"] is True


@pytest.mark.parametrize(
    ("record_field", "profile_field"),
    [
        ("model_identity", None),
        ("client_identity", None),
        (None, "package_guidance_profile_id"),
        (None, "tool_surface_profile_id"),
        (None, "system_instruction_profile_id"),
        (None, "tool_instruction_profile_id"),
    ],
)
def test_identity_values_are_hashed_before_export(
    tmp_path: Path,
    record_field: str | None,
    profile_field: str | None,
) -> None:
    marker = "PRIVATE_MARKER_001"
    record_payload = _record_payload()
    profile_payload = _profile_payload()
    if record_field is not None:
        record_payload[record_field] = marker
    if profile_field is not None:
        profile_payload[profile_field] = marker
    record = LF1.RebaselineRunRecord.from_path(
        _write_json(tmp_path, "record.json", record_payload)
    )
    profile = LF1.ControlSurfaceProfile.from_path(
        _write_json(tmp_path, "profile.json", profile_payload)
    )

    trace = LF1.ValueSafeTrace.build(record, profile)
    serialized = json.dumps(trace.preflight_metadata())

    assert marker not in serialized
    assert LF1._sha256_identity(marker) in serialized


@pytest.mark.parametrize(
    ("record_overrides", "profile_overrides"),
    [
        ({"model_identity": "unknown"}, {}),
        ({"client_identity": "unknown"}, {}),
        ({}, {"package_guidance_profile_id": "unknown"}),
        ({}, {"tool_surface_profile_id": "unknown"}),
        ({}, {"system_instruction_profile_id": "unknown"}),
        ({}, {"tool_instruction_profile_id": "unknown"}),
        ({}, {"source_commit": "0000000"}),
    ],
)
def test_incomplete_identity_is_not_comparable(
    tmp_path: Path,
    record_overrides: dict[str, object],
    profile_overrides: dict[str, object],
) -> None:
    record_payload = _record_payload()
    record_payload.update(record_overrides)
    record = LF1.RebaselineRunRecord.from_path(
        _write_json(tmp_path, "record.json", record_payload)
    )
    profile = LF1.ControlSurfaceProfile.from_path(
        _write_json(
            tmp_path,
            "profile.json",
            _profile_payload(**profile_overrides),
        )
    )

    assert profile.comparable(record) is False


def test_current_profile_rejects_unknown_system_prompt_hash(tmp_path: Path) -> None:
    record_payload = _record_payload()
    record_payload["system_prompt_sha256"] = "0" * 64
    record = LF1.RebaselineRunRecord.from_path(
        _write_json(tmp_path, "record.json", record_payload)
    )
    profile = LF1.ControlSurfaceProfile.from_path(
        _write_json(tmp_path, "profile.json", _profile_payload())
    )

    with pytest.raises(
        LF1.LangfuseRebaselineError,
        match="langfuse_rebaseline_profile_invalid",
    ):
        LF1.ValueSafeTrace.build(record, profile)


def test_record_rejects_unreviewed_comparison_code(tmp_path: Path) -> None:
    payload = _record_payload()
    payload["comparison_codes"] = ["shadow_private_ticket_text_match"]

    with pytest.raises(
        LF1.LangfuseRebaselineError,
        match="langfuse_rebaseline_record_invalid",
    ):
        LF1.RebaselineRunRecord.from_path(_write_json(tmp_path, "record.json", payload))


def test_profile_rejects_unknown_fields_without_echoing_content(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    profile = _profile_payload()
    profile["raw_ticket"] = "PRIVATE_MARKER"

    exit_code = LF1.main(
        [
            "--record",
            str(_write_json(tmp_path, "record.json", _record_payload())),
            "--profile",
            str(_write_json(tmp_path, "profile.json", profile)),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "langfuse_rebaseline_profile_invalid" in output
    assert "PRIVATE_MARKER" not in output


@pytest.mark.parametrize(
    "url",
    [
        "https://cloud.langfuse.com",
        "http://127.0.0.1:3000/path",
        "http://user:secret@127.0.0.1:3000",
        "http://127.0.0.1",
    ],
)
def test_endpoint_must_be_explicit_loopback(url: str) -> None:
    with pytest.raises(
        LF1.LangfuseRebaselineError,
        match="langfuse_rebaseline_config_invalid",
    ):
        LF1._validate_loopback_url(url)


def test_unreviewed_sdk_version_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(LF1.importlib.metadata, "version", lambda _: "4.8.0")

    with pytest.raises(
        LF1.LangfuseRebaselineError,
        match="langfuse_rebaseline_dependency_unavailable",
    ):
        LF1._require_pinned_langfuse_sdk()


def test_emit_trace_has_fixed_span_shape_and_no_input_output(tmp_path: Path) -> None:
    client = _FakeClient()

    LF1.emit_trace(client, _trace(tmp_path))

    assert [call["name"] for call in client.calls] == [
        "kcs.synthetic_rebaseline_run",
        "control_surface.preflight",
        "semantic_review.proposal",
        "semantic_review.project",
        "workflow.complete",
    ]
    assert client.flush_count == 1
    assert all("input" not in call and "output" not in call for call in client.calls)
    allowed_keys = {"as_type", "metadata", "name", "version"}
    assert all(set(call) <= allowed_keys for call in client.calls)


def test_real_sdk_exporter_receives_metadata_only_spans(tmp_path: Path) -> None:
    langfuse_module = pytest.importorskip("langfuse")
    trace_module = pytest.importorskip("opentelemetry.sdk.trace")
    export_module = pytest.importorskip("opentelemetry.sdk.trace.export")
    assert LF1.importlib.metadata.version("langfuse") == "4.7.0"

    class _CaptureExporter(export_module.SpanExporter):
        def __init__(self) -> None:
            self.spans: list[Any] = []

        def export(self, spans: list[Any]) -> Any:
            self.spans.extend(spans)
            return export_module.SpanExportResult.SUCCESS

        def shutdown(self) -> None:
            return None

    exporter = _CaptureExporter()
    client = langfuse_module.Langfuse(
        public_key="pk-lf-synthetic",
        secret_key="sk-lf-synthetic",
        base_url="http://127.0.0.1:3000",
        tracing_enabled=True,
        flush_at=1,
        tracer_provider=trace_module.TracerProvider(),
        span_exporter=exporter,
    )
    try:
        LF1.emit_trace(client, _trace(tmp_path, with_runtime_outcome=True))
    finally:
        client.shutdown()

    assert {span.name for span in exporter.spans} == {
        "kcs.synthetic_rebaseline_run",
        "control_surface.preflight",
        "semantic_review.proposal",
        "semantic_review.project",
        "workflow.complete",
    }
    assert len(exporter.spans) == 5
    root = next(
        span for span in exporter.spans if span.name == "kcs.synthetic_rebaseline_run"
    )
    completion = next(
        span for span in exporter.spans if span.name == "workflow.complete"
    )
    assert root.attributes["langfuse.observation.metadata.milestone"] == (
        "m3_continuation"
    )
    assert (
        completion.attributes["langfuse.observation.metadata.later_candidate_continued"]
        is True
    )
    attribute_keys = {key for span in exporter.spans for key in span.attributes}
    resource_keys = {key for span in exporter.spans for key in span.resource.attributes}
    assert not any("input" in key or "output" in key for key in attribute_keys)
    assert resource_keys <= {
        "service.instance.id",
        "service.name",
        "telemetry.sdk.language",
        "telemetry.sdk.name",
        "telemetry.sdk.version",
    }
