from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import kcs_core
from kcs_core import (
    ZendeskAdapterConfig,
    ZendeskIngestPolicy,
    ZendeskRawTicketSnapshot,
    ZendeskSourceClient,
    build_evidence_packet_from_zendesk_export,
    ingest_zendesk_ticket_for_cleanup,
)
from kcs_core.errors import ContractValidationError

APPROVED_REF = "approved-zendesk-ref-001"
PRIVATE_SUBJECT = "Synthetic subject SECRET_SUBJECT"
PRIVATE_COMMENT = "Synthetic raw comment SECRET_COMMENT"
PRIVATE_URL = "https://customer.example.net/private.log"


class FakeZendeskClient:
    def __init__(self, snapshot: ZendeskRawTicketSnapshot | None = None) -> None:
        self.calls: list[str] = []
        self.snapshot = snapshot or _snapshot()

    def fetch_ticket_snapshot(self, ticket_ref: str) -> ZendeskRawTicketSnapshot:
        self.calls.append(ticket_ref)
        return self.snapshot


class FailingZendeskClient:
    def fetch_ticket_snapshot(self, ticket_ref: str) -> ZendeskRawTicketSnapshot:
        raise RuntimeError(f"client failed for {ticket_ref} {PRIVATE_SUBJECT}")


def _policy(**overrides: Any) -> ZendeskIngestPolicy:
    values = {
        "approved_ticket_refs": (APPROVED_REF,),
        "allow_partial_comments": False,
        "allow_raw_handoff_files": False,
    }
    values.update(overrides)
    return ZendeskIngestPolicy(**values)


def _snapshot(**overrides: Any) -> ZendeskRawTicketSnapshot:
    values = {
        "ticket_ref": APPROVED_REF,
        "ticket": {
            "subject": PRIVATE_SUBJECT,
            "description": "Synthetic raw ticket body",
            "requester_id": 12345678,
        },
        "comments": (
            {
                "body": PRIVATE_COMMENT,
                "author_id": 987654,
                "public": True,
            },
        ),
        "comments_complete": True,
        "partial_comment_bodies": False,
        "attachments_present": False,
    }
    values.update(overrides)
    return ZendeskRawTicketSnapshot(**values)


def _safe_result(**overrides: Any) -> dict[str, Any]:
    result = ingest_zendesk_ticket_for_cleanup(
        ticket_ref=APPROVED_REF,
        client=FakeZendeskClient(_snapshot(**overrides)),
        policy=_policy(),
    )
    return result.safe_payload()


def test_allowlisted_ticket_ref_returns_safe_cleanup_manifest() -> None:
    client = FakeZendeskClient()

    result = ingest_zendesk_ticket_for_cleanup(
        ticket_ref=APPROVED_REF,
        client=client,
        policy=_policy(),
    )

    assert client.calls == [APPROVED_REF]
    payload = result.safe_payload()
    assert payload["schema_version"] == "zendesk_raw_cleanup_snapshot_v1"
    assert payload["source_kind"] == "zendesk_ticket_snapshot"
    assert payload["ticket_ref"] == APPROVED_REF
    assert payload["cleanup_required"] is True
    assert payload["kcs_authoring_ready"] is False
    assert payload["sanitized_export_ready"] is False
    assert payload["comments_complete"] is True
    assert payload["partial_comment_bodies"] is False
    assert payload["raw_handoff_written"] is False
    assert PRIVATE_SUBJECT not in repr(payload)
    assert PRIVATE_COMMENT not in repr(payload)


def test_non_allowlisted_ticket_ref_fails_before_client_call() -> None:
    client = FakeZendeskClient()
    private_ref = "approved-zendesk-ref-002"

    with pytest.raises(ContractValidationError) as captured:
        ingest_zendesk_ticket_for_cleanup(
            ticket_ref=private_ref,
            client=client,
            policy=_policy(),
        )

    assert client.calls == []
    assert private_ref not in str(captured.value)


@pytest.mark.parametrize("ticket_ref", ["123456", "ticket-123456", "zd123456"])
def test_malformed_or_raw_ticket_refs_fail_closed(ticket_ref: str) -> None:
    with pytest.raises(ContractValidationError) as captured:
        ZendeskIngestPolicy(approved_ticket_refs=(ticket_ref,))

    assert ticket_ref not in str(captured.value)


def test_empty_ticket_ref_fails_closed() -> None:
    with pytest.raises(ContractValidationError):
        ZendeskIngestPolicy(approved_ticket_refs=("",))


def test_client_failure_returns_value_safe_error() -> None:
    with pytest.raises(ContractValidationError) as captured:
        ingest_zendesk_ticket_for_cleanup(
            ticket_ref=APPROVED_REF,
            client=FailingZendeskClient(),
            policy=_policy(),
        )

    assert str(captured.value) == "zendesk source client failed"
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None
    assert PRIVATE_SUBJECT not in str(captured.value)
    assert APPROVED_REF not in str(captured.value)


@pytest.mark.parametrize(
    "ticket_payload",
    [
        {1: "raw-key"},
        {"score": float("nan")},
        {"nested": {1: "raw-key"}},
    ],
)
def test_snapshot_payload_must_be_strict_json(
    ticket_payload: dict[object, object],
) -> None:
    with pytest.raises(ContractValidationError) as captured:
        ingest_zendesk_ticket_for_cleanup(
            ticket_ref=APPROVED_REF,
            client=FakeZendeskClient(_snapshot(ticket=ticket_payload)),
            policy=_policy(),
        )

    assert str(captured.value) == "zendesk snapshot must be strict JSON"


def test_attachment_metadata_is_safe_and_no_attachment_api_exists() -> None:
    payload = _safe_result(
        comments=(
            {
                "body": PRIVATE_COMMENT,
                "attachments": [
                    {"content_url": PRIVATE_URL, "file_name": "private.log"}
                ],
            },
        ),
    )

    assert payload["attachments_present"] is True
    assert "attachments_present" in payload["reason_codes"]
    assert PRIVATE_URL not in repr(payload)
    assert not hasattr(ZendeskSourceClient, "fetch_attachment")
    assert not hasattr(FakeZendeskClient(), "download_attachment")


def test_no_broad_ticket_access_methods_are_part_of_source_protocol() -> None:
    assert not hasattr(ZendeskSourceClient, "list_tickets")
    assert not hasattr(ZendeskSourceClient, "search")
    assert not hasattr(ZendeskSourceClient, "bulk_export")


@pytest.mark.parametrize(
    "snapshot_overrides",
    [
        {"comments_complete": None},
        {"comments_complete": False},
        {"comments_complete": True, "partial_comment_bodies": True},
    ],
)
def test_missing_or_false_comment_completeness_is_cleanup_only(
    snapshot_overrides: dict[str, Any],
) -> None:
    payload = _safe_result(**snapshot_overrides)

    assert payload["comments_complete"] is False
    assert payload["partial_comment_bodies"] is True
    assert payload["kcs_authoring_ready"] is False
    assert "partial_comments" in payload["reason_codes"]


def test_raw_kcs8_manifest_is_not_accepted_by_kcs7_builder() -> None:
    payload = _safe_result()

    with pytest.raises(ContractValidationError) as captured:
        build_evidence_packet_from_zendesk_export(
            payload,
            case_ref="approved-case-001",
            policy=kcs_core.EvidenceBuildPolicy(),
        )

    assert PRIVATE_SUBJECT not in str(captured.value)
    assert PRIVATE_COMMENT not in str(captured.value)
    assert "issue_candidates" not in payload
    assert "visibility_summary" not in payload
    assert payload["kcs_authoring_ready"] is False


def test_ingest_does_not_call_kcs7_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_builder(*args: object, **kwargs: object) -> None:
        raise AssertionError("builder must not be called")

    monkeypatch.setattr(
        kcs_core.evidence_builder,
        "build_evidence_packet_from_zendesk_export",
        fail_builder,
    )

    payload = _safe_result()

    assert payload["cleanup_required"] is True


@pytest.mark.parametrize(
    "config",
    [
        ZendeskAdapterConfig(
            mode="service_endpoint",
            service_endpoint="https://internal-zendesk-service.local",
        ),
        ZendeskAdapterConfig(
            mode="mcp_stdio",
            mcp_command="zendesk-source-adapter --profile kcs8-readonly",
        ),
        ZendeskAdapterConfig(mode="fake"),
    ],
)
def test_transport_config_accepts_injected_profiles(
    config: ZendeskAdapterConfig,
) -> None:
    assert config.mode in {"service_endpoint", "mcp_stdio", "fake"}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"mode": "service_endpoint", "service_endpoint": "https://internal/path?token=secret"},
        {"mode": "mcp_stdio", "mcp_command": "zendesk-source --api-key SECRET"},
        {"mode": "mcp_stdio", "mcp_command": "env ZENDESK_TOKEN=SECRET zendesk-source"},
    ],
)
def test_transport_config_rejects_inline_credentials(kwargs: dict[str, str]) -> None:
    with pytest.raises(ContractValidationError) as captured:
        ZendeskAdapterConfig(**kwargs)

    assert "SECRET" not in str(captured.value)


def test_local_raw_handoff_requires_explicit_policy(tmp_path: Path) -> None:
    with pytest.raises(ContractValidationError):
        ingest_zendesk_ticket_for_cleanup(
            ticket_ref=APPROVED_REF,
            client=FakeZendeskClient(),
            policy=_policy(),
            cleanup_workspace=tmp_path / "cleanup",
        )


def test_local_raw_handoff_writes_snapshot_and_safe_manifest(tmp_path: Path) -> None:
    workspace = tmp_path / "cleanup"

    result = ingest_zendesk_ticket_for_cleanup(
        ticket_ref=APPROVED_REF,
        client=FakeZendeskClient(),
        policy=_policy(allow_raw_handoff_files=True),
        cleanup_workspace=workspace,
    )

    snapshot_path = workspace / "zendesk-raw-cleanup-snapshot.json"
    manifest_path = workspace / "zendesk-ingest-manifest.json"
    assert snapshot_path.exists()
    assert manifest_path.exists()
    assert result.safe_payload()["raw_handoff_written"] is True
    assert PRIVATE_SUBJECT in snapshot_path.read_text(encoding="utf-8")
    manifest_text = manifest_path.read_text(encoding="utf-8")
    assert PRIVATE_SUBJECT not in manifest_text
    assert PRIVATE_COMMENT not in manifest_text
    assert snapshot_path.stat().st_mode & 0o777 == 0o600
    assert manifest_path.stat().st_mode & 0o777 == 0o600


def test_local_raw_handoff_rejects_repo_paths() -> None:
    repo_path = Path.cwd() / "tmp-kcs8-cleanup"

    with pytest.raises(ContractValidationError):
        ingest_zendesk_ticket_for_cleanup(
            ticket_ref=APPROVED_REF,
            client=FakeZendeskClient(),
            policy=_policy(allow_raw_handoff_files=True),
            cleanup_workspace=repo_path,
        )


def test_local_raw_handoff_rejects_overwrite(tmp_path: Path) -> None:
    workspace = tmp_path / "cleanup"
    workspace.mkdir()
    (workspace / "zendesk-raw-cleanup-snapshot.json").write_text(
        "existing",
        encoding="utf-8",
    )

    with pytest.raises(ContractValidationError):
        ingest_zendesk_ticket_for_cleanup(
            ticket_ref=APPROVED_REF,
            client=FakeZendeskClient(),
            policy=_policy(allow_raw_handoff_files=True),
            cleanup_workspace=workspace,
        )


def test_local_raw_handoff_rejects_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)

    with pytest.raises(ContractValidationError):
        ingest_zendesk_ticket_for_cleanup(
            ticket_ref=APPROVED_REF,
            client=FakeZendeskClient(),
            policy=_policy(allow_raw_handoff_files=True),
            cleanup_workspace=link,
        )


def test_local_raw_handoff_rolls_back_partial_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import kcs_core.zendesk_ingest as zendesk_ingest

    workspace = tmp_path / "cleanup"
    original_write = zendesk_ingest._write_private_text
    calls: list[Path] = []

    def flaky_write(path: Path, text: str) -> None:
        calls.append(path)
        if len(calls) == 2:
            raise ContractValidationError("could not write zendesk handoff files")
        original_write(path, text)

    monkeypatch.setattr(zendesk_ingest, "_write_private_text", flaky_write)

    with pytest.raises(ContractValidationError):
        ingest_zendesk_ticket_for_cleanup(
            ticket_ref=APPROVED_REF,
            client=FakeZendeskClient(),
            policy=_policy(allow_raw_handoff_files=True),
            cleanup_workspace=workspace,
        )

    assert not (workspace / "zendesk-raw-cleanup-snapshot.json").exists()
    assert not (workspace / "zendesk-ingest-manifest.json").exists()


def test_kcs8_api_exports_are_available() -> None:
    assert kcs_core.ZendeskIngestPolicy is ZendeskIngestPolicy
    assert kcs_core.ZendeskAdapterConfig is ZendeskAdapterConfig
    assert kcs_core.ZendeskRawTicketSnapshot is ZendeskRawTicketSnapshot
    assert (
        kcs_core.ingest_zendesk_ticket_for_cleanup
        is ingest_zendesk_ticket_for_cleanup
    )
