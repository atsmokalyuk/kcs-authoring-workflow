from __future__ import annotations

import json

import pytest

from kcs_adapters import desktop_clean_ticket_metadata
from kcs_adapters.desktop_payload import ApprovedSummaryInputError
from kcs_adapters.desktop_ticket_ref import (
    APPROVED_TICKET_CLEAN_TEXT_FILE_NAME,
    APPROVED_TICKET_FILE_SCHEMA_VERSION,
    approved_ticket_author_arguments,
    approved_ticket_clean_metadata_path,
    approved_ticket_ref_from_arguments,
    clean_ticket_semantic_review_metadata,
    register_clean_ticket_arguments,
)
from kcs_core.models import ArticleType


def _approved_ticket_payload(
    *,
    ticket_ref: str = "ticket-001",
) -> dict[str, object]:
    return {
        "approved_summary_text": (
            "Approved sanitized summary: Monitoring graphs show no data."
        ),
        "case_ref": "example-simple",
        "item": {
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "environment": {
                "applicable_to": ["Plesk for Linux"],
            },
            "evidence": "The sanitized summary confirms the config override.",
            "resolution_steps": [
                "Connect to the Plesk server via SSH.",
                "Run systemctl restart sw-collectd.",
            ],
            "root_cause": "A leftover collector config redirects metric data.",
            "solution": "Disable the override and restart the collector.",
            "symptom": "Monitoring graphs show no data.",
            "title": "Monitoring graphs show no data",
        },
        "schema_version": APPROVED_TICKET_FILE_SCHEMA_VERSION,
        "ticket_ref": ticket_ref,
    }


def _write_approved_ticket_summary(
    root,
    payload: dict[str, object],
    *,
    ticket_ref: str = "ticket-001",
) -> None:
    source_dir = root / "local-data" / "approved-summaries"
    source_dir.mkdir(parents=True)
    (source_dir / f"{ticket_ref}.json").write_text(
        json.dumps(payload, sort_keys=True),
        encoding="utf-8",
    )


def _write_clean_ticket_text(
    root,
    text: str,
    *,
    ticket_ref: str = "ticket-001",
) -> None:
    source_dir = root / "local-data" / "approved-summaries" / ticket_ref
    source_dir.mkdir(parents=True)
    (source_dir / APPROVED_TICKET_CLEAN_TEXT_FILE_NAME).write_text(
        text,
        encoding="utf-8",
    )


def _write_cleanup_form_metadata(
    root,
    text: str,
    *,
    ticket_ref: str = "ticket-001",
) -> None:
    clean_dir = root / "local-data" / "approved-summaries" / ticket_ref
    clean_path = clean_dir / APPROVED_TICKET_CLEAN_TEXT_FILE_NAME
    digest = desktop_clean_ticket_metadata.clean_ticket_sha256(text)
    metadata_path = (
        clean_dir / desktop_clean_ticket_metadata.CLEAN_TICKET_METADATA_FILE_NAME
    )
    metadata_path.write_text(
        json.dumps(
            {
                "schema_version": (
                    desktop_clean_ticket_metadata
                    .CLEAN_TICKET_CLEANUP_FORM_METADATA_SCHEMA_VERSION
                ),
                "clean_ticket_ref": ticket_ref,
                "clean_ticket_path": str(clean_path),
                "clean_ticket_sha256": digest,
                "confirmed_no_pii": True,
                "scan_clean": True,
                "updated_at": "2026-06-20T00:00:00Z",
                "version": 1,
                "write_target": "mvp_approved_summary",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def test_desktop_ticket_ref_loads_and_merges_local_approved_summary(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    _write_approved_ticket_summary(tmp_path, _approved_ticket_payload())

    arguments = approved_ticket_author_arguments(
        {
            "ticket_ref": "ticket-001",
            "debug": True,
            "reuse_search_checked": True,
            "reuse_search_run_ref": "reuse-search-001",
        }
    )

    assert arguments["approved_summary_text"] == (
        "Approved sanitized summary: Monitoring graphs show no data."
    )
    assert arguments["case_ref"] == "example-simple"
    assert arguments["debug"] is True
    assert arguments["reuse_search_checked"] is True
    assert arguments["reuse_search_run_ref"] == "reuse-search-001"
    assert "schema_version" not in arguments
    assert "ticket_ref" not in arguments


def test_desktop_ticket_ref_rejects_legacy_summary_with_compressed_ipv6(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    payload = _approved_ticket_payload()
    private_value = "2001:db8::1"
    payload["approved_summary_text"] = f"Affected server: {private_value}"
    _write_approved_ticket_summary(tmp_path, payload)

    with pytest.raises(ApprovedSummaryInputError) as exc_info:
        approved_ticket_author_arguments({"ticket_ref": "ticket-001"})

    assert exc_info.value.debug_code == "approved_ticket_summary_invalid"
    assert private_value not in str(exc_info.value)


def test_desktop_ticket_ref_loads_clean_ticket_text_file(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    _write_clean_ticket_text(
        tmp_path,
        (
            "Customer Ticket Content\n"
            "Title: Monitoring graphs show no data in Plesk\n"
            "Cause: Leftover collectd DataDir override.\n"
            "Resolution: Disable the override and restart sw-collectd.\n"
        ),
    )

    arguments = approved_ticket_author_arguments(
        {
            "ticket_ref": "ticket-001",
            "debug": True,
        }
    )

    assert arguments["approved_summary_text"].startswith("Customer Ticket Content")
    assert arguments["case_ref"] == "approved-ticket-ticket-001"
    assert arguments["debug"] is True
    assert "schema_version" not in arguments
    assert "ticket_ref" not in arguments
    assert "item" not in arguments


def test_desktop_ticket_ref_loads_cleanup_clean_ticket_with_urls_and_paths(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    text = (
        "Customer Ticket Content\n"
        "The update failed with curl: (6) Could not resolve host.\n"
        "The investigation checked /etc/resolv.conf and "
        "/etc/httpd/conf/plesk.conf.d/server.conf.\n"
        "The support article used during analysis was "
        "https://support.plesk.com/hc/en-us/articles/12377512781975.\n"
        "Resolution: fixed the network DNS issue and regenerated Apache "
        "configuration.\n"
    )
    _write_clean_ticket_text(tmp_path, text, ticket_ref="ticket-clean-form")
    _write_cleanup_form_metadata(tmp_path, text, ticket_ref="ticket-clean-form")

    arguments = approved_ticket_author_arguments(
        {
            "ticket_ref": "ticket-clean-form",
            "debug": True,
        }
    )
    metadata = clean_ticket_semantic_review_metadata(
        ticket_ref="ticket-clean-form",
        approved_summary_text=text.strip(),
    )

    assert arguments["approved_summary_text"] == text
    assert arguments["case_ref"] == "approved-ticket-ticket-clean-form"
    assert metadata["source_kind"] == (
        desktop_clean_ticket_metadata.CLEAN_TICKET_SOURCE_CLEANUP_FORM
    )


def test_desktop_ticket_ref_rejects_clean_ticket_file_tool_artifact(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    text = (
        "Customer Ticket Content\n"
        "Issue: safe ticket.\n"
        '<parameter name="ticket_ref">ticket-001</parameter>\n'
        "Resolution: fixed the configuration.\n"
    )
    _write_clean_ticket_text(tmp_path, text, ticket_ref="ticket-clean-form")
    _write_cleanup_form_metadata(tmp_path, text, ticket_ref="ticket-clean-form")

    with pytest.raises(ApprovedSummaryInputError) as exc_info:
        approved_ticket_author_arguments({"ticket_ref": "ticket-clean-form"})

    assert exc_info.value.debug_code == "approved_ticket_summary_invalid"


def test_desktop_ticket_ref_rejects_clean_ticket_file_secret_artifact(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    text = (
        "Customer Ticket Content\n"
        "Issue: safe ticket.\n"
        "Authorization: Bearer abc123\n"
        "Resolution: fixed the configuration.\n"
    )
    _write_clean_ticket_text(tmp_path, text, ticket_ref="ticket-clean-form")
    _write_cleanup_form_metadata(tmp_path, text, ticket_ref="ticket-clean-form")

    with pytest.raises(ApprovedSummaryInputError) as exc_info:
        approved_ticket_author_arguments({"ticket_ref": "ticket-clean-form"})

    assert exc_info.value.debug_code == "approved_ticket_summary_invalid"


def test_desktop_ticket_ref_rejects_cleanup_file_with_compressed_ipv6(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    private_value = "2001:db8::1"
    text = (
        "Customer Ticket Content\n"
        "Issue: safe ticket.\n"
        f"Affected server address: {private_value}\n"
        "Resolution: fixed the configuration.\n"
    )
    _write_clean_ticket_text(tmp_path, text, ticket_ref="ticket-clean-form")
    _write_cleanup_form_metadata(tmp_path, text, ticket_ref="ticket-clean-form")

    with pytest.raises(ApprovedSummaryInputError) as exc_info:
        approved_ticket_author_arguments({"ticket_ref": "ticket-clean-form"})

    assert exc_info.value.debug_code == "approved_ticket_summary_invalid"
    assert private_value not in str(exc_info.value)


def test_register_clean_ticket_writes_clean_ticket_file(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    result = register_clean_ticket_arguments(
        {
            "clean_ticket_text": (
                "Customer Ticket Content\n"
                "Monitoring graphs show no data in Plesk.\n"
                "Cause: custom collectd config.\n"
                "Resolution: disable config and restart sw-collectd.\n"
            ),
            "ticket_ref": "monitoring-001",
        }
    )

    clean_path = (
        tmp_path
        / "local-data"
        / "approved-summaries"
        / "monitoring-001"
        / APPROVED_TICKET_CLEAN_TEXT_FILE_NAME
    )
    assert clean_path.read_text(encoding="utf-8").startswith(
        "Customer Ticket Content"
    )
    assert result["ticket_ref"] == "monitoring-001"
    assert result["next_arguments"] == {"ticket_ref": "monitoring-001"}
    assert result["clean_ticket_store_ref"] == "approved-summary-clean-ticket"
    assert "clean_ticket_text" not in result
    metadata_path = approved_ticket_clean_metadata_path("monitoring-001")
    metadata = desktop_clean_ticket_metadata.read_clean_ticket_metadata(
        metadata_path
    )
    source_kind = (
        desktop_clean_ticket_metadata.CLEAN_TICKET_SOURCE_CLAUDE_VISIBLE_REGISTRATION
    )
    assert metadata == {
        "clean_ticket_sha256": result["clean_ticket_sha256"],
        "schema_version": (
            desktop_clean_ticket_metadata.CLEAN_TICKET_METADATA_SCHEMA_VERSION
        ),
        "semantic_review_allowed": True,
        "source_kind": source_kind,
        "ticket_ref": "monitoring-001",
    }


def test_register_clean_ticket_uses_configured_store_root(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    storage_root = tmp_path / "Application Support" / "KCS Authoring"
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(project_root))
    monkeypatch.setenv(
        "KCS_AUTHORING_MVP_APPROVED_TICKET_STORE_ROOT",
        str(storage_root),
    )
    monkeypatch.setenv(
        "KCS_AUTHORING_MVP_APPROVED_TICKET_STORAGE_HINT",
        "~/Library/Application Support/KCS Authoring",
    )
    monkeypatch.setenv(
        "KCS_AUTHORING_MVP_APPROVED_TICKET_STORAGE_REF",
        "user_application_support_kcs_authoring",
    )

    result = register_clean_ticket_arguments(
        {
            "clean_ticket_text": "Customer Ticket Content\nSafe sanitized text.",
            "ticket_ref": "monitoring-001",
        }
    )

    stored = (
        storage_root
        / "local-data"
        / "approved-summaries"
        / "monitoring-001"
        / APPROVED_TICKET_CLEAN_TEXT_FILE_NAME
    )
    assert stored.is_file()
    assert not (
        project_root
        / "local-data"
        / "approved-summaries"
        / "monitoring-001"
        / APPROVED_TICKET_CLEAN_TEXT_FILE_NAME
    ).exists()
    assert (
        result["clean_ticket_storage_hint"]
        == "~/Library/Application Support/KCS Authoring"
    )
    assert (
        result["clean_ticket_storage_ref"]
        == "user_application_support_kcs_authoring"
    )


def test_register_clean_ticket_generates_ref_from_text(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    result = register_clean_ticket_arguments(
        {"clean_ticket_text": "Customer Ticket Content\nSafe sanitized text."}
    )

    assert isinstance(result["ticket_ref"], str)
    assert result["ticket_ref"].startswith("ticket-")
    assert result["next_arguments"] == {"ticket_ref": result["ticket_ref"]}


def test_register_clean_ticket_accepts_operator_ticket_ref(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))

    result = register_clean_ticket_arguments(
        {
            "clean_ticket_text": "Customer Ticket Content\nSafe sanitized text.",
            "ticket_ref": "ticket-example-simple",
        }
    )
    arguments = approved_ticket_author_arguments(
        {"ticket_ref": "ticket-example-simple"}
    )

    assert result["ticket_ref"] == "ticket-example-simple"
    assert result["next_arguments"] == {"ticket_ref": "ticket-example-simple"}
    assert arguments["case_ref"] == "approved-ticket-ticket-example-simple"
    assert arguments["approved_summary_text"] == (
        "Customer Ticket Content\nSafe sanitized text."
    )


def test_clean_ticket_semantic_review_metadata_validates_hash_binding(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    text = "Customer Ticket Content\nIssue: safe noisy ticket.\n"
    result = register_clean_ticket_arguments(
        {
            "clean_ticket_text": text,
            "ticket_ref": "ticket-semantic-review",
        }
    )

    metadata = clean_ticket_semantic_review_metadata(
        ticket_ref="ticket-semantic-review",
        approved_summary_text=text.strip(),
    )

    assert metadata["ticket_ref"] == "ticket-semantic-review"
    assert metadata["clean_ticket_sha256"] == result["clean_ticket_sha256"]


def test_clean_ticket_semantic_review_metadata_accepts_cleanup_form_metadata(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    text = "Customer Ticket Content\nIssue: safe noisy ticket.\n"
    ticket_ref = "ticket-semantic-review"
    clean_dir = tmp_path / "local-data" / "approved-summaries" / ticket_ref
    clean_dir.mkdir(parents=True)
    clean_path = clean_dir / APPROVED_TICKET_CLEAN_TEXT_FILE_NAME
    clean_path.write_text(text, encoding="utf-8")
    digest = desktop_clean_ticket_metadata.clean_ticket_sha256(text)
    metadata_path = (
        clean_dir / desktop_clean_ticket_metadata.CLEAN_TICKET_METADATA_FILE_NAME
    )
    metadata_path.write_text(
        json.dumps(
            {
                "schema_version": (
                    desktop_clean_ticket_metadata
                    .CLEAN_TICKET_CLEANUP_FORM_METADATA_SCHEMA_VERSION
                ),
                "clean_ticket_ref": ticket_ref,
                "clean_ticket_path": str(clean_path),
                "clean_ticket_sha256": digest,
                "confirmed_no_pii": True,
                "scan_clean": True,
                "updated_at": "2026-06-20T00:00:00Z",
                "version": 1,
                "write_target": "mvp_approved_summary",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    metadata = clean_ticket_semantic_review_metadata(
        ticket_ref=ticket_ref,
        approved_summary_text=text.strip(),
    )

    assert metadata == {
        "clean_ticket_sha256": digest,
        "schema_version": (
            desktop_clean_ticket_metadata.CLEAN_TICKET_METADATA_SCHEMA_VERSION
        ),
        "semantic_review_allowed": True,
        "source_kind": desktop_clean_ticket_metadata.CLEAN_TICKET_SOURCE_CLEANUP_FORM,
        "ticket_ref": ticket_ref,
    }


def test_clean_ticket_semantic_review_metadata_rejects_unclean_cleanup_form_metadata(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    text = "Customer Ticket Content\nIssue: safe noisy ticket.\n"
    ticket_ref = "ticket-semantic-review"
    clean_dir = tmp_path / "local-data" / "approved-summaries" / ticket_ref
    clean_dir.mkdir(parents=True)
    clean_path = clean_dir / APPROVED_TICKET_CLEAN_TEXT_FILE_NAME
    clean_path.write_text(text, encoding="utf-8")
    digest = desktop_clean_ticket_metadata.clean_ticket_sha256(text)
    metadata_path = (
        clean_dir / desktop_clean_ticket_metadata.CLEAN_TICKET_METADATA_FILE_NAME
    )
    metadata_path.write_text(
        json.dumps(
            {
                "schema_version": (
                    desktop_clean_ticket_metadata
                    .CLEAN_TICKET_CLEANUP_FORM_METADATA_SCHEMA_VERSION
                ),
                "clean_ticket_ref": ticket_ref,
                "clean_ticket_path": str(clean_path),
                "clean_ticket_sha256": digest,
                "confirmed_no_pii": True,
                "scan_clean": False,
                "updated_at": "2026-06-20T00:00:00Z",
                "write_target": "mvp_approved_summary",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ApprovedSummaryInputError) as exc_info:
        clean_ticket_semantic_review_metadata(
            ticket_ref=ticket_ref,
            approved_summary_text=text,
        )

    assert exc_info.value.debug_code == "clean_ticket_semantic_review_not_allowed"


def test_clean_ticket_semantic_review_metadata_rejects_hash_mismatch(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    register_clean_ticket_arguments(
        {
            "clean_ticket_text": "Customer Ticket Content\nIssue: safe noisy ticket.",
            "ticket_ref": "ticket-semantic-review",
        }
    )
    clean_path = (
        tmp_path
        / "local-data"
        / "approved-summaries"
        / "ticket-semantic-review"
        / APPROVED_TICKET_CLEAN_TEXT_FILE_NAME
    )
    clean_path.write_text(
        "Customer Ticket Content\nIssue: safe noisy ticket changed.",
        encoding="utf-8",
    )

    with pytest.raises(ApprovedSummaryInputError) as exc_info:
        clean_ticket_semantic_review_metadata(
            ticket_ref="ticket-semantic-review",
            approved_summary_text="Customer Ticket Content\nIssue: safe noisy ticket.",
        )

    assert exc_info.value.debug_code == "clean_ticket_hash_mismatch"


def test_register_clean_ticket_rejects_metadata_broken_symlink(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    metadata_path = (
        tmp_path
        / "local-data"
        / "approved-summaries"
        / "ticket-semantic-review"
        / desktop_clean_ticket_metadata.CLEAN_TICKET_METADATA_FILE_NAME
    )
    metadata_path.parent.mkdir(parents=True)
    outside_target = tmp_path / "outside" / "metadata.json"
    try:
        metadata_path.symlink_to(outside_target)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    with pytest.raises(ApprovedSummaryInputError) as exc_info:
        register_clean_ticket_arguments(
            {
                "clean_ticket_text": (
                    "Customer Ticket Content\nIssue: safe noisy ticket."
                ),
                "ticket_ref": "ticket-semantic-review",
            }
        )

    assert exc_info.value.debug_code == "clean_ticket_metadata_write_invalid"
    assert not outside_target.exists()


def test_register_clean_ticket_accepts_large_complete_transcript(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    text = (
        "Customer Ticket Content\n"
        "Plesk Monitoring graphs show no data.\n"
        + ("Safe sanitized investigation line with product facts.\n" * 6200)
        + "Root cause: custom collectd configuration redirects metrics.\n"
        + "Resolution: disabled the configuration and restarted sw-collectd.\n"
    )
    assert len(text.encode("utf-8")) > 300 * 1024

    result = register_clean_ticket_arguments(
        {
            "clean_ticket_text": text,
            "ticket_ref": "large-monitoring-001",
        }
    )
    arguments = approved_ticket_author_arguments(
        {"ticket_ref": "large-monitoring-001"}
    )
    saved_text = text.strip()

    assert result["ticket_ref"] == "large-monitoring-001"
    assert result["byte_length"] == len(saved_text.encode("utf-8"))
    assert arguments["approved_summary_text"] == saved_text


def test_register_clean_ticket_rejects_compressed_ipv6_before_storage(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    private_value = "2001:db8::1"

    with pytest.raises(ApprovedSummaryInputError) as exc_info:
        register_clean_ticket_arguments(
            {
                "clean_ticket_text": (
                    "Customer Ticket Content\n"
                    f"The affected server address is {private_value}.\n"
                ),
                "ticket_ref": "compressed-ipv6-001",
            }
        )

    assert exc_info.value.debug_code == "clean_ticket_text_invalid"
    assert private_value not in str(exc_info.value)
    assert not (tmp_path / "local-data").exists()


def test_register_clean_ticket_rejects_upload_path_ref_without_echo(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    unsafe_ref = "/mnt/user-data/uploads/ticket.txt"

    with pytest.raises(ApprovedSummaryInputError) as exc_info:
        register_clean_ticket_arguments(
            {
                "clean_ticket_text": "Customer Ticket Content\nSafe sanitized text.",
                "ticket_ref": unsafe_ref,
            }
        )

    assert exc_info.value.debug_code == "approved_ticket_ref_invalid"
    assert not (tmp_path / "local-data").exists()


def test_register_clean_ticket_rejects_tool_argument_markup_without_echo(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))

    with pytest.raises(ApprovedSummaryInputError) as exc_info:
        register_clean_ticket_arguments(
            {
                "clean_ticket_text": (
                    "Customer Ticket Content\n"
                    "Plesk Monitoring graphs show no data.\n"
                    '<parameter name="ticket_ref">'
                    "monitoring-graphs-no-data-rrd-path\n"
                    "Resolution: disable config and restart the service.\n"
                ),
                "ticket_ref": "monitoring-001",
            }
        )

    assert exc_info.value.debug_code == "clean_ticket_text_invalid"
    assert not (tmp_path / "local-data").exists()


def test_register_clean_ticket_rejects_truncated_tail_without_echo(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))

    with pytest.raises(ApprovedSummaryInputError) as exc_info:
        register_clean_ticket_arguments(
            {
                "clean_ticket_text": (
                    "Customer Ticket Content\n"
                    "Plesk Monitoring graphs show no data.\n"
                    "Internal investigation notes continue.\n"
                    "With grafana debug enabled:\n"
                    "[debug output truncated]\n"
                ),
                "ticket_ref": "monitoring-001",
            }
        )

    assert exc_info.value.debug_code == "clean_ticket_text_incomplete"
    assert not (tmp_path / "local-data").exists()


def test_register_clean_ticket_rejects_collapsed_investigation_tail_without_echo(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))

    with pytest.raises(ApprovedSummaryInputError) as exc_info:
        register_clean_ticket_arguments(
            {
                "clean_ticket_text": (
                    "Customer Ticket Content\n"
                    + ("Safe sanitized investigation line.\n" * 80)
                    + "Show more\n"
                    + "So investigation continues and we'll update you once "
                    "there's more information.\n"
                    + "Looks like theres some issues when reinstalling.\n"
                ),
                "ticket_ref": "monitoring-001",
            }
        )

    assert exc_info.value.debug_code == "clean_ticket_text_incomplete"
    assert not (tmp_path / "local-data").exists()


def test_register_clean_ticket_allows_truncated_log_with_later_final_evidence(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))

    result = register_clean_ticket_arguments(
        {
            "clean_ticket_text": (
                "Customer Ticket Content\n"
                "Plesk Monitoring graphs show no data.\n"
                "With grafana debug enabled:\n"
                "[debug output truncated]\n"
                "Root cause: custom collectd configuration redirects metrics.\n"
                "Resolution: disabled the configuration and restarted "
                "sw-collectd.\n"
            ),
            "ticket_ref": "monitoring-001",
        }
    )

    assert result["ticket_ref"] == "monitoring-001"


def test_register_clean_ticket_allows_show_more_with_later_final_evidence(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))

    result = register_clean_ticket_arguments(
        {
            "clean_ticket_text": (
                "Customer Ticket Content\n"
                + ("Safe sanitized investigation line.\n" * 80)
                + "Show more\n"
                + "Root cause: custom configuration redirects metrics.\n"
                + "Resolution: disabled the configuration and restarted the "
                "service.\n"
            ),
            "ticket_ref": "monitoring-001",
        }
    )

    assert result["ticket_ref"] == "monitoring-001"


def test_desktop_ticket_ref_uses_default_case_ref_when_file_omits_it(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    payload = _approved_ticket_payload()
    del payload["case_ref"]
    _write_approved_ticket_summary(tmp_path, payload)

    arguments = approved_ticket_author_arguments({"ticket_ref": "ticket-001"})

    assert arguments["case_ref"] == "approved-ticket-ticket-001"


def test_desktop_ticket_ref_resolves_existing_bare_numeric_alias(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    canonical_ref = "ticket-123456"
    _write_approved_ticket_summary(
        tmp_path,
        _approved_ticket_payload(ticket_ref=canonical_ref),
        ticket_ref=canonical_ref,
    )

    arguments = approved_ticket_author_arguments({"ticket_ref": "123456"})

    assert approved_ticket_ref_from_arguments({"ticket_ref": "123456"}) == (
        canonical_ref
    )
    assert arguments["case_ref"] == "example-simple"


def test_desktop_ticket_ref_does_not_invent_missing_numeric_alias(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))

    assert approved_ticket_ref_from_arguments({"ticket_ref": "123456"}) == "123456"
    with pytest.raises(ApprovedSummaryInputError) as exc_info:
        approved_ticket_author_arguments({"ticket_ref": "123456"})

    assert exc_info.value.debug_code == "approved_ticket_summary_not_found"


def test_desktop_ticket_ref_prefers_existing_exact_numeric_ref(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    canonical_ref = "ticket-123456"
    _write_approved_ticket_summary(
        tmp_path,
        _approved_ticket_payload(ticket_ref=canonical_ref),
        ticket_ref=canonical_ref,
    )
    exact_payload = _approved_ticket_payload(ticket_ref="123456")
    exact_payload["case_ref"] = "exact-numeric-ref"
    source_dir = tmp_path / "local-data" / "approved-summaries"
    (source_dir / "123456.json").write_text(
        json.dumps(exact_payload, sort_keys=True),
        encoding="utf-8",
    )

    arguments = approved_ticket_author_arguments({"ticket_ref": "123456"})

    assert approved_ticket_ref_from_arguments({"ticket_ref": "123456"}) == "123456"
    assert arguments["case_ref"] == "exact-numeric-ref"


def test_desktop_ticket_ref_rejects_unsafe_ref_without_echo() -> None:
    unsafe_ref = "../private-token"

    assert approved_ticket_ref_from_arguments({"ticket_ref": unsafe_ref}) == (
        "invalid-ticket-ref"
    )
    with pytest.raises(ApprovedSummaryInputError) as exc_info:
        approved_ticket_author_arguments({"ticket_ref": unsafe_ref})

    assert exc_info.value.debug_code == "approved_ticket_ref_invalid"


def test_desktop_ticket_ref_missing_file_is_controlled_failure(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))

    with pytest.raises(ApprovedSummaryInputError) as exc_info:
        approved_ticket_author_arguments({"ticket_ref": "ticket-001"})

    assert exc_info.value.debug_code == "approved_ticket_summary_not_found"


def test_desktop_ticket_ref_rejects_unknown_file_keys(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    payload = _approved_ticket_payload()
    payload["raw_ticket_path"] = "/Users/alex/private-ticket.txt"
    _write_approved_ticket_summary(tmp_path, payload)

    with pytest.raises(ApprovedSummaryInputError) as exc_info:
        approved_ticket_author_arguments({"ticket_ref": "ticket-001"})

    assert exc_info.value.debug_code == "approved_ticket_summary_invalid"


def test_desktop_ticket_ref_rejects_policy_flag_override(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    _write_approved_ticket_summary(tmp_path, _approved_ticket_payload())

    with pytest.raises(ApprovedSummaryInputError) as exc_info:
        approved_ticket_author_arguments(
            {
                "ticket_ref": "ticket-001",
                "auto_publish_allowed": True,
            }
        )

    assert exc_info.value.debug_code == "approved_summary_policy_flag_invalid"
