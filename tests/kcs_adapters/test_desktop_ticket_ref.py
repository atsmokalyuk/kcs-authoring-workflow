from __future__ import annotations

import json

import pytest

from kcs_adapters.desktop_payload import ApprovedSummaryInputError
from kcs_adapters.desktop_ticket_ref import (
    APPROVED_TICKET_FILE_SCHEMA_VERSION,
    approved_ticket_author_arguments,
    approved_ticket_ref_from_arguments,
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
