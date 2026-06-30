from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import kcs_adapters
from kcs_adapters.smoke_accounting import (
    SMOKE_ACCOUNTING_SCHEMA_VERSION,
    build_smoke_accounting_report,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"


def test_smoke_accounting_report_counts_tools_failures_and_cost_proxy() -> None:
    transcript = "\n".join(
        [
            "User: draft an article",
            "Calling tool kcs_draft_article",
            "Result: validation_failed",
            "Calling tool kcs_draft_article",
            '{"pipeline_ok": true, "ready_for_reviewer": true}',
            "Calling tool kcs_run_contract_smoke",
            '{"smoke_ok": true}',
        ]
    )

    report = build_smoke_accounting_report(transcript)
    payload = report.to_json_dict()

    assert payload["schema_version"] == SMOKE_ACCOUNTING_SCHEMA_VERSION
    assert payload["billing_exact"] is False
    assert payload["tool_call_count"] == 3
    assert payload["unique_tools"] == [
        "kcs_draft_article",
        "kcs_run_contract_smoke",
    ]
    assert payload["failure_marker_count"] == 1
    assert payload["controlled_success_marker_count"] == 2
    assert payload["manual_fallback_marker_count"] == 0
    assert payload["retry_risk"] == "medium"
    assert payload["estimated_log_tokens"] > 0
    assert payload["estimated_upper_bound_cost_usd"] >= (
        payload["estimated_input_cost_usd"]
    )


def test_smoke_accounting_summarizes_deterministic_kcs_draft_smoke() -> None:
    split_call = _claude_log_line(
        "client",
        {
            "method": "tools/call",
            "params": {
                "arguments": {
                    "item_candidates": [{"item_ref": "A"}, {"item_ref": "B"}]
                },
                "name": "kcs_draft_article",
            },
        },
    )
    split_result = _claude_log_line(
        "server",
        {
            "result": {
                "content": [
                    {
                        "text": json.dumps(
                            {
                                "blockers": ["multiple_kcs_items_detected"],
                                "operator_prompt_style": "native_choice_popup",
                                "should_be_kcs_article": False,
                                "validation_ok": False,
                            },
                            separators=(",", ":"),
                        )
                    }
                ]
            }
        },
    )
    selected_call = _claude_log_line(
        "client",
        {
            "method": "tools/call",
            "params": {
                "arguments": {
                    "operator_choice_confirmed": True,
                    "operator_selected_item_ref": "A",
                    "operator_selection_ref": "operator-selection-001",
                },
                "name": "kcs_draft_article",
            },
        },
    )
    selected_result = _claude_log_line(
        "server",
        {
            "result": {
                "content": [
                    {
                        "text": (
                            "Reviewer-only Zendesk HTML draft:\n```html\n"
                            "<h1>Safe title</h1>\n```\n"
                            + json.dumps(
                                {
                                    "should_be_kcs_article": True,
                                    "validation_ok": True,
                                },
                                separators=(",", ":"),
                            )
                        )
                    }
                ]
            }
        },
    )
    transcript = "\n".join(
        [split_call, split_result, selected_call, selected_result]
    )

    payload = build_smoke_accounting_report(transcript).to_json_dict()

    assert payload["deterministic_kcs_draft_smoke_passed"] is True
    assert payload["kcs_draft_call_count"] == 2
    assert payload["kcs_draft_split_required_count"] == 1
    assert payload["kcs_draft_selected_call_count"] == 1
    assert payload["kcs_draft_success_count"] == 1
    assert payload["manual_fallback_observed"] is False
    assert payload["tool_result_invalid_count"] == 0
    assert payload["kcs_draft_blocker_codes"] == ["multiple_kcs_items_detected"]


def test_smoke_accounting_flags_upload_ticket_ref_and_tool_result_invalid() -> None:
    transcript = "\n".join(
        [
            _claude_log_line(
                "client",
                {
                    "params": {
                        "arguments": {
                            "ticket_ref": "/mnt/user-data/uploads/sanitized.txt"
                        },
                        "name": "kcs_draft_article",
                    }
                },
            ),
            _claude_log_line(
                "server",
                {"structuredContent": {"error_code": "tool_result_invalid"}},
            ),
        ]
    )

    payload = build_smoke_accounting_report(transcript).to_json_dict()

    assert payload["deterministic_kcs_draft_smoke_passed"] is False
    assert payload["kcs_draft_upload_ticket_ref_count"] == 1
    assert payload["tool_result_invalid_count"] == 1


def test_smoke_accounting_marks_manual_fallback_as_high_retry_risk() -> None:
    report = build_smoke_accounting_report(
        "The local KCS tool did not respond. I drafted this directly instead."
    )

    payload = report.to_json_dict()

    assert payload["manual_fallback_marker_count"] == 2
    assert payload["manual_fallback_observed"] is True
    assert payload["retry_risk"] == "high"


def test_smoke_accounting_empty_transcript_has_zero_tokens() -> None:
    payload = build_smoke_accounting_report("").to_json_dict()

    assert payload["log_chars"] == 0
    assert payload["estimated_log_tokens"] == 0
    assert payload["estimated_upper_bound_cost_usd"] == 0


def test_smoke_accounting_rejects_invalid_numeric_options(tmp_path: Path) -> None:
    result = _run_cli(
        "--log",
        str(_write_transcript(tmp_path, "Calling tool kcs_draft_article")),
        "--chars-per-token",
        "0",
        "--json",
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert json.loads(result.stderr) == {
        "error": {"code": "invalid_numeric_option"},
        "ok": False,
        "schema_version": SMOKE_ACCOUNTING_SCHEMA_VERSION,
    }


def test_smoke_accounting_cli_returns_value_safe_json(tmp_path: Path) -> None:
    transcript = _write_transcript(
        tmp_path,
        "Calling tool kcs_draft_article\n"
        "Failed to call tool kcs_draft_article\n"
        '{"pipeline_ok": true}'
    )

    result = _run_cli("--log", str(transcript), "--json")

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == SMOKE_ACCOUNTING_SCHEMA_VERSION
    assert payload["tool_call_count"] == 2
    assert payload["failure_marker_count"] == 1
    assert "Failed to call" not in result.stdout
    assert str(transcript) not in result.stdout


def test_smoke_accounting_cli_missing_file_does_not_echo_path(tmp_path: Path) -> None:
    missing = tmp_path / "missing-log.txt"

    result = _run_cli("--log", str(missing), "--json")

    assert result.returncode == 2
    assert result.stdout == ""
    assert json.loads(result.stderr)["error"]["code"] == "log_file_not_found"
    assert str(missing) not in result.stderr


def test_root_exports_include_smoke_accounting_api() -> None:
    assert kcs_adapters.SMOKE_ACCOUNTING_SCHEMA_VERSION == (
        SMOKE_ACCOUNTING_SCHEMA_VERSION
    )
    assert kcs_adapters.build_smoke_accounting_report is build_smoke_accounting_report


def _write_transcript(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "smoke-transcript.txt"
    path.write_text(text, encoding="utf-8")
    return path


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from kcs_adapters.smoke_accounting import main; "
                "raise SystemExit(main())"
            ),
            *args,
        ],
        cwd=REPO_ROOT,
        env={"PYTHONPATH": str(SRC_ROOT)},
        capture_output=True,
        check=False,
        text=True,
    )


def _claude_log_line(direction: str, payload: dict[str, object]) -> str:
    return (
        f"2026-06-18T18:39:22.000Z [KCS Authoring] [info] "
        f"Message from {direction}: "
        f"{json.dumps(payload, separators=(',', ':'))}"
    )
