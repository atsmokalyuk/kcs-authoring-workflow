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
        "case_ref": "96024747",
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
    assert arguments["case_ref"] == "96024747"
    assert arguments["debug"] is True
    assert arguments["reuse_search_checked"] is True
    assert arguments["reuse_search_run_ref"] == "reuse-search-001"
    assert "schema_version" not in arguments
    assert "ticket_ref" not in arguments


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
            "ticket_ref": "ticket-96024747",
        }
    )
    arguments = approved_ticket_author_arguments({"ticket_ref": "ticket-96024747"})

    assert result["ticket_ref"] == "ticket-96024747"
    assert result["next_arguments"] == {"ticket_ref": "ticket-96024747"}
    assert arguments["case_ref"] == "approved-ticket-ticket-96024747"
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

    with pytest.raises(ApprovedSummaryInputError) as exc_info:
        clean_ticket_semantic_review_metadata(
            ticket_ref="ticket-semantic-review",
            approved_summary_text=(
                "Customer Ticket Content\nIssue: safe noisy ticket changed."
            ),
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
