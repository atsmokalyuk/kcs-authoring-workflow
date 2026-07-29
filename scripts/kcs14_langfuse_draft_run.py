"""Export one value-safe live draft run report to loopback Langfuse."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import os
import re
import sys
from collections.abc import Mapping
from contextlib import AbstractContextManager
from dataclasses import replace
from pathlib import Path
from typing import Protocol, cast
from urllib.parse import urlsplit

from kcs_adapters.draft_run_accounting import (
    DRAFT_RUN_REPORT_SCHEMA_VERSION,
    DraftRunObservation,
    DraftRunReport,
    validate_draft_run_report,
)

PINNED_LANGFUSE_SDK_VERSION = "4.7.0"
MAX_REPORT_BYTES = 256_000
MAX_DESKTOP_LOG_SCAN_BYTES = 512_000
MAX_OBSERVATIONS = 200
_IDENTITY_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")
_HOST_QUOTA_RE = re.compile(
    r"(?:"
    r"(?:claude\s+(?:desktop\s+)?free).{0,100}"
    r"(?:reached|exhausted|usage\s+limit)|"
    r"(?:reached|exhausted|usage\s+limit).{0,100}"
    r"(?:claude\s+(?:desktop\s+)?free)"
    r")",
    re.IGNORECASE,
)
_REPORT_FIELDS = frozenset(
    {
        "observations",
        "observed_duration_ms",
        "attempted_item_count",
        "batch_outcome_category",
        "completed_item_count",
        "retry_count",
        "retryable_blocked_item_count",
        "run_correlation_sha256",
        "schema_version",
        "selected_item_count",
        "semantic_correction_count",
        "terminal_outcome",
        "terminal_source",
        "transition_count",
        "workflow_stopped_item_count",
    }
)
_OBSERVATION_FIELDS = frozenset(
    {
        "candidate_count",
        "attempted_item_count",
        "batch_outcome_category",
        "completed_item_count",
        "debug_code",
        "duration_ms",
        "excerpt_count",
        "item_index",
        "model_visible_bytes",
        "network_calls",
        "rag_available",
        "request_bytes",
        "result_bytes",
        "retry_count",
        "retryable_blocked_item_count",
        "selected_item_count",
        "semantic_correction_count",
        "sequence",
        "stage",
        "success_classification",
        "tool_name",
        "workflow_stopped_item_count",
    }
)


class DraftRunExportError(ValueError):
    """One value-safe external adapter failure classification."""

    def __init__(self, debug_code: str) -> None:
        super().__init__(debug_code)
        self.debug_code = debug_code


class ObservationClient(Protocol):
    def auth_check(self) -> bool: ...

    def start_as_current_observation(
        self, **kwargs: object
    ) -> AbstractContextManager[object]: ...

    def flush(self) -> None: ...


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = read_draft_run_report(args.report)
        if args.desktop_log is not None:
            report = classify_desktop_terminal(report, args.desktop_log)
        if args.classified_output is not None:
            write_draft_run_report(args.classified_output, report)
        client = build_langfuse_client()
        if not client.auth_check():
            raise DraftRunExportError("langfuse_draft_run_auth_failed")
        emit_trace(
            client,
            report,
            model_identity=_safe_identity(args.model_identity),
            client_identity=_safe_identity(args.client_identity),
        )
        _write_stdout(
            {
                "debug_code": "langfuse_draft_run_exported",
                "ok": True,
                "run_correlation_sha256": report.run_correlation_sha256,
                "terminal_outcome": report.terminal_outcome,
                "trace_exported": True,
            }
        )
        return 0
    except DraftRunExportError as exc:
        _write_stdout({"debug_code": exc.debug_code, "ok": False})
        return 2
    except (ImportError, OSError, TypeError, ValueError):
        _write_stdout(
            {"debug_code": "langfuse_draft_run_export_unavailable", "ok": False}
        )
        return 2
    except Exception:
        _write_stdout(
            {"debug_code": "langfuse_draft_run_export_unavailable", "ok": False}
        )
        return 2


def read_draft_run_report(path: Path) -> DraftRunReport:
    payload = _read_report_payload(path)
    observations_payload = payload["observations"]
    assert isinstance(observations_payload, list)
    observations = tuple(
        _observation_from_payload(item) for item in observations_payload
    )
    return _report_from_payload(payload, observations)


def _read_report_payload(path: Path) -> Mapping[str, object]:
    data, payload = _read_report_json(path)
    if not _valid_report_payload(data, payload):
        raise DraftRunExportError("draft_run_report_invalid")
    return cast(Mapping[str, object], payload)


def _read_report_json(path: Path) -> tuple[bytes, object]:
    try:
        data = path.read_bytes()
        payload = json.loads(data)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DraftRunExportError("draft_run_report_invalid") from exc
    return data, payload


def _valid_report_payload(data: bytes, payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    observations_payload = payload.get("observations")
    return all(
        (
            bool(data),
            len(data) <= MAX_REPORT_BYTES,
            set(payload) == _REPORT_FIELDS,
            payload.get("schema_version") == DRAFT_RUN_REPORT_SCHEMA_VERSION,
            isinstance(observations_payload, list),
            isinstance(observations_payload, list)
            and len(observations_payload) <= MAX_OBSERVATIONS,
        )
    )


def _report_from_payload(
    payload: Mapping[str, object],
    observations: tuple[DraftRunObservation, ...],
) -> DraftRunReport:
    try:
        report = DraftRunReport(
            schema_version=cast(str, payload["schema_version"]),
            run_correlation_sha256=cast(str, payload["run_correlation_sha256"]),
            terminal_outcome=cast(str, payload["terminal_outcome"]),
            terminal_source=cast(str, payload["terminal_source"]),
            transition_count=_required_int(payload, "transition_count"),
            selected_item_count=_required_int(payload, "selected_item_count"),
            attempted_item_count=_required_int(payload, "attempted_item_count"),
            completed_item_count=_required_int(payload, "completed_item_count"),
            retryable_blocked_item_count=_required_int(
                payload, "retryable_blocked_item_count"
            ),
            workflow_stopped_item_count=_required_int(
                payload, "workflow_stopped_item_count"
            ),
            batch_outcome_category=_required_string(payload, "batch_outcome_category"),
            retry_count=_required_int(payload, "retry_count"),
            semantic_correction_count=_required_int(
                payload, "semantic_correction_count"
            ),
            observed_duration_ms=_required_int(payload, "observed_duration_ms"),
            observations=observations,
        )
        validate_draft_run_report(report)
    except (KeyError, TypeError, ValueError) as exc:
        raise DraftRunExportError("draft_run_report_invalid") from exc
    return report


def classify_desktop_terminal(
    report: DraftRunReport,
    desktop_log: Path,
) -> DraftRunReport:
    """Close only an unfinished report with an explicit host quota marker."""

    if report.terminal_outcome != "in_progress":
        return report
    try:
        with desktop_log.open("rb") as stream:
            stream.seek(0, os.SEEK_END)
            size = stream.tell()
            stream.seek(max(0, size - MAX_DESKTOP_LOG_SCAN_BYTES))
            text = stream.read(MAX_DESKTOP_LOG_SCAN_BYTES).decode(
                "utf-8", errors="replace"
            )
    except OSError as exc:
        raise DraftRunExportError("desktop_log_unavailable") from exc
    if not _HOST_QUOTA_RE.search(text):
        return report
    return replace(
        report,
        terminal_outcome="host_quota_exhausted",
        terminal_source="desktop_log_classifier",
    )


def write_draft_run_report(path: Path, report: DraftRunReport) -> None:
    validate_draft_run_report(report)
    path.write_text(
        json.dumps(
            report.to_json_dict(),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def build_langfuse_client() -> ObservationClient:
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")
    base_url = os.environ.get("LANGFUSE_BASE_URL", "http://127.0.0.1:3000")
    if (
        not public_key
        or not secret_key
        or len(public_key) > 256
        or len(secret_key) > 256
    ):
        raise DraftRunExportError("langfuse_draft_run_config_invalid")
    _validate_loopback_url(base_url)
    _require_pinned_langfuse_sdk()
    try:
        langfuse_module = importlib.import_module("langfuse")
        trace_module = importlib.import_module("opentelemetry.sdk.trace")
    except ImportError as exc:
        raise DraftRunExportError("langfuse_draft_run_dependency_unavailable") from exc
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
            environment="local-live-accounting",
            media_upload_thread_count=1,
            sample_rate=1.0,
            tracer_provider=tracer_provider_type(),
        ),
    )


def emit_trace(
    client: ObservationClient,
    report: DraftRunReport,
    *,
    model_identity: str | None = None,
    client_identity: str | None = None,
) -> None:
    """Emit metadata-only hierarchy; no input or output attributes are used."""

    root_metadata: dict[str, object] = {
        "telemetry_schema_version": report.schema_version,
        "run_correlation_sha256": report.run_correlation_sha256,
        "terminal_outcome": report.terminal_outcome,
        "terminal_source": report.terminal_source,
        "transition_count": report.transition_count,
        "selected_item_count": report.selected_item_count,
        "attempted_item_count": report.attempted_item_count,
        "completed_item_count": report.completed_item_count,
        "retryable_blocked_item_count": report.retryable_blocked_item_count,
        "workflow_stopped_item_count": report.workflow_stopped_item_count,
        "batch_outcome_category": report.batch_outcome_category,
        "retry_count": report.retry_count,
        "semantic_correction_count": report.semantic_correction_count,
        "observed_duration_ms": report.observed_duration_ms,
    }
    if model_identity is not None:
        root_metadata["model_identity_sha256"] = _identity_sha256(model_identity)
    if client_identity is not None:
        root_metadata["client_identity_sha256"] = _identity_sha256(client_identity)
    with client.start_as_current_observation(
        name="kcs.draft_run",
        as_type="span",
        metadata=root_metadata,
        version=report.schema_version,
    ):
        for observation in report.observations:
            _emit_observation(client, observation)
    client.flush()


def _emit_observation(
    client: ObservationClient,
    observation: DraftRunObservation,
) -> None:
    metadata = {
        key: value
        for key, value in observation.__dict__.items()
        if key not in {"stage"} and value is not None
    }
    with client.start_as_current_observation(
        name=observation.stage,
        as_type="span",
        metadata=metadata,
    ):
        pass


def _observation_from_payload(payload: object) -> DraftRunObservation:
    if not isinstance(payload, dict) or set(payload) != _OBSERVATION_FIELDS:
        raise DraftRunExportError("draft_run_report_invalid")
    try:
        _validate_nullable_observation_fields(payload)
        return _build_observation(payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise DraftRunExportError("draft_run_report_invalid") from exc


def _validate_nullable_observation_fields(
    payload: Mapping[str, object],
) -> None:
    item_index = payload["item_index"]
    if item_index is not None and not _is_int(item_index):
        raise ValueError
    for field in ("network_calls", "rag_available"):
        value = payload[field]
        if value is not None and not isinstance(value, bool):
            raise ValueError


def _build_observation(
    payload: Mapping[str, object],
) -> DraftRunObservation:
    return DraftRunObservation(
        sequence=_required_int(payload, "sequence"),
        stage=_required_string(payload, "stage"),
        tool_name=_required_string(payload, "tool_name"),
        item_index=cast(int | None, payload["item_index"]),
        duration_ms=_required_int(payload, "duration_ms"),
        request_bytes=_required_int(payload, "request_bytes"),
        result_bytes=_required_int(payload, "result_bytes"),
        model_visible_bytes=_required_int(payload, "model_visible_bytes"),
        candidate_count=_required_int(payload, "candidate_count"),
        selected_item_count=_required_int(payload, "selected_item_count"),
        excerpt_count=_required_int(payload, "excerpt_count"),
        attempted_item_count=_required_int(payload, "attempted_item_count"),
        completed_item_count=_required_int(payload, "completed_item_count"),
        retryable_blocked_item_count=_required_int(
            payload, "retryable_blocked_item_count"
        ),
        workflow_stopped_item_count=_required_int(
            payload, "workflow_stopped_item_count"
        ),
        batch_outcome_category=_required_string(payload, "batch_outcome_category"),
        retry_count=_required_int(payload, "retry_count"),
        semantic_correction_count=_required_int(payload, "semantic_correction_count"),
        network_calls=cast(bool | None, payload["network_calls"]),
        rag_available=cast(bool | None, payload["rag_available"]),
        debug_code=_optional_string(payload, "debug_code"),
        success_classification=_required_string(payload, "success_classification"),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export one value-safe /draft report to local Langfuse."
    )
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--desktop-log", type=Path)
    parser.add_argument("--classified-output", type=Path)
    parser.add_argument("--model-identity")
    parser.add_argument("--client-identity")
    return parser


def _safe_identity(value: str | None) -> str | None:
    if value is None:
        return None
    if _IDENTITY_RE.fullmatch(value) is None:
        raise DraftRunExportError("draft_run_identity_invalid")
    return value


def _identity_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _validate_loopback_url(value: str) -> None:
    parsed = urlsplit(value)
    invalid = any(
        (
            parsed.scheme not in {"http", "https"},
            parsed.hostname not in {"127.0.0.1", "::1", "localhost"},
            parsed.port is None,
            parsed.username is not None,
            parsed.password is not None,
            bool(parsed.query),
            bool(parsed.fragment),
        )
    )
    if invalid:
        raise DraftRunExportError("langfuse_draft_run_config_invalid")


def _require_pinned_langfuse_sdk() -> None:
    try:
        version = importlib.metadata.version("langfuse")
    except importlib.metadata.PackageNotFoundError as exc:
        raise DraftRunExportError("langfuse_draft_run_dependency_unavailable") from exc
    if version != PINNED_LANGFUSE_SDK_VERSION:
        raise DraftRunExportError("langfuse_draft_run_dependency_unavailable")


def _required_string(payload: Mapping[str, object], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str):
        raise ValueError
    return value


def _optional_string(payload: Mapping[str, object], field: str) -> str | None:
    value = payload.get(field)
    if value is not None and not isinstance(value, str):
        raise ValueError
    return cast(str | None, value)


def _required_int(payload: Mapping[str, object], field: str) -> int:
    value = payload.get(field)
    if not _is_int(value):
        raise ValueError
    return cast(int, value)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _write_stdout(payload: Mapping[str, object]) -> None:
    sys.stdout.write(json.dumps(dict(payload), sort_keys=True) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
