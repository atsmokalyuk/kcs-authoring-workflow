from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from contextlib import AbstractContextManager
from pathlib import Path
from types import TracebackType
from typing import Any

import pytest

from kcs_adapters.draft_run_accounting import (
    DRAFT_RUN_REPORT_SCHEMA_VERSION,
    DraftRunObservation,
    DraftRunReport,
)

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "kcs14_langfuse_draft_run.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "kcs14_langfuse_draft_run",
        SCRIPT,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


EXPORTER = _load_module()


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
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.flush_count = 0

    def auth_check(self) -> bool:
        return True

    def start_as_current_observation(
        self, **kwargs: object
    ) -> AbstractContextManager[object]:
        self.calls.append(dict(kwargs))
        return _ObservationContext()

    def flush(self) -> None:
        self.flush_count += 1


def _report(*, terminal_outcome: str = "in_progress") -> DraftRunReport:
    observation = DraftRunObservation(
        sequence=1,
        stage="item.reuse_search_comparison",
        tool_name="kcs.draft_article",
        item_index=1,
        duration_ms=42,
        request_bytes=101,
        result_bytes=202,
        model_visible_bytes=202,
        candidate_count=3,
        selected_item_count=1,
        excerpt_count=4,
        attempted_item_count=1,
        completed_item_count=0,
        retryable_blocked_item_count=0,
        workflow_stopped_item_count=0,
        batch_outcome_category="sequential_in_progress",
        retry_count=0,
        semantic_correction_count=0,
        network_calls=True,
        rag_available=True,
        debug_code=None,
        success_classification="success",
    )
    return DraftRunReport(
        schema_version=DRAFT_RUN_REPORT_SCHEMA_VERSION,
        run_correlation_sha256="d" * 64,
        terminal_outcome=terminal_outcome,
        terminal_source="mcp_boundary",
        transition_count=1,
        selected_item_count=1,
        attempted_item_count=1,
        completed_item_count=0,
        retryable_blocked_item_count=0,
        workflow_stopped_item_count=0,
        batch_outcome_category="sequential_in_progress",
        retry_count=0,
        semantic_correction_count=0,
        observed_duration_ms=42,
        observations=(observation,),
    )


def _write_report(tmp_path: Path, report: DraftRunReport) -> Path:
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report.to_json_dict()), encoding="utf-8")
    return path


def test_emit_trace_uses_metadata_only_observations() -> None:
    client = _FakeClient()

    EXPORTER.emit_trace(
        client,
        _report(),
        model_identity="claude-sonnet-safe",
        client_identity="desktop-safe",
    )

    assert client.flush_count == 1
    assert [call["name"] for call in client.calls] == [
        "kcs.draft_run",
        "item.reuse_search_comparison",
    ]
    assert (
        client.calls[0]["metadata"]["model_identity_sha256"]
        == hashlib.sha256(b"claude-sonnet-safe").hexdigest()
    )
    assert (
        client.calls[0]["metadata"]["client_identity_sha256"]
        == hashlib.sha256(b"desktop-safe").hexdigest()
    )
    serialized = json.dumps(client.calls, sort_keys=True)
    assert "claude-sonnet-safe" not in serialized
    assert "desktop-safe" not in serialized
    for forbidden in ("input", "output", "prompt", "ticket_ref", "excerpt_text"):
        assert f'"{forbidden}"' not in serialized


def test_real_sdk_receives_metadata_only_spans() -> None:
    langfuse_module = pytest.importorskip("langfuse")
    trace_module = pytest.importorskip("opentelemetry.sdk.trace")
    export_module = pytest.importorskip("opentelemetry.sdk.trace.export")
    assert EXPORTER.importlib.metadata.version("langfuse") == "4.7.0"

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
        public_key="pk-lf-live-accounting",
        secret_key="sk-lf-live-accounting",
        base_url="http://127.0.0.1:3000",
        tracing_enabled=True,
        flush_at=1,
        tracer_provider=trace_module.TracerProvider(),
        span_exporter=exporter,
    )
    try:
        EXPORTER.emit_trace(client, _report())
    finally:
        client.shutdown()

    assert {span.name for span in exporter.spans} == {
        "kcs.draft_run",
        "item.reuse_search_comparison",
    }
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


def test_desktop_log_classifier_closes_only_explicit_quota_marker(
    tmp_path: Path,
) -> None:
    quota_log = tmp_path / "desktop.log"
    quota_log.write_text(
        "Run stopped: you've reached your usage limit for Claude Desktop Free.",
        encoding="utf-8",
    )

    classified = EXPORTER.classify_desktop_terminal(_report(), quota_log)

    assert classified.terminal_outcome == "host_quota_exhausted"
    assert classified.terminal_source == "desktop_log_classifier"
    assert "Desktop Free" not in json.dumps(classified.to_json_dict())


def test_desktop_log_classifier_does_not_override_terminal_report(
    tmp_path: Path,
) -> None:
    quota_log = tmp_path / "desktop.log"
    quota_log.write_text("you've reached your limit", encoding="utf-8")

    classified = EXPORTER.classify_desktop_terminal(
        _report(terminal_outcome="completed"),
        quota_log,
    )

    assert classified.terminal_outcome == "completed"
    assert classified.terminal_source == "mcp_boundary"


def test_desktop_log_classifier_rejects_generic_unscoped_limit_text(
    tmp_path: Path,
) -> None:
    generic_log = tmp_path / "desktop.log"
    generic_log.write_text(
        "A provider says you've reached your limit.",
        encoding="utf-8",
    )

    classified = EXPORTER.classify_desktop_terminal(_report(), generic_log)

    assert classified.terminal_outcome == "in_progress"
    assert classified.terminal_source == "mcp_boundary"


def test_report_reader_rejects_extra_fields(tmp_path: Path) -> None:
    payload = _report().to_json_dict()
    payload["ticket_ref"] = "private-ticket"
    path = tmp_path / "unsafe.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EXPORTER.DraftRunExportError) as error:
        EXPORTER.read_draft_run_report(path)

    assert error.value.debug_code == "draft_run_report_invalid"


@pytest.mark.parametrize(
    "url",
    [
        "https://cloud.langfuse.com",
        "http://192.168.1.10:3000",
        "http://user:secret@127.0.0.1:3000",
        "http://127.0.0.1",
    ],
)
def test_exporter_rejects_non_loopback_or_credentialed_url(url: str) -> None:
    with pytest.raises(EXPORTER.DraftRunExportError):
        EXPORTER._validate_loopback_url(url)
