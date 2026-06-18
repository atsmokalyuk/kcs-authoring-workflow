from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = Path(__file__).with_name("cli_fixtures")
SCENARIO_DIRS = tuple(sorted(path for path in FIXTURE_ROOT.iterdir() if path.is_dir()))
SRC_ROOT = REPO_ROOT / "src"
EXPECTED_SCENARIOS = {
    "001_reuse_existing",
    "002_update_existing",
    "003_create_candidate",
    "004_no_article_unsolved",
    "005_blocked_missing_search",
    "006_split_multiple_issues",
    "007_blocked_internal_only_evidence",
    # KCS-6 task name kept; fixture covers an incorrect public article flag path.
    "008_flag_existing_wrong_article_type",
}
REQUIRED_SCENARIO_FILES = {
    "evidence_packet.json",
    "expected_decision.json",
    "expected_validation.json",
    "reuse_results.json",
}

PRIVATE_VALUE_PATTERNS = (
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}\b", re.I),
    re.compile(r"https?://[^\s\"']+", re.I),
    re.compile(
        r"\b(?!example\.(?:com|net|org|invalid)\b)"
        r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.[a-z]{2,63}\b",
        re.I,
    ),
    re.compile(r"(?:/Users/|/home/|C:\\Users\\)", re.I),
    re.compile(r"\b(?:PLSK|EXT)[-_.]?\d{4,}(?:[-_.]?\d+)*\b", re.I),
    re.compile(r"\b(?:ticket|zendesk|zd)[-_ #:]?\d{4,}\b", re.I),
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    re.compile(
        r"\b(?:password|passwd|api[_-]?key|token|secret)\s*[:=-]\s*\S+",
        re.I,
    ),
    re.compile(r"\bauthorization:\s*bearer\s+\S+", re.I),
)
SAFE_PUBLIC_SUPPORT_URL_RE = re.compile(
    r"https://support\.plesk\.com/hc/en-us/articles/[0-9A-Za-z_-]+"
)
FORBIDDEN_FIXTURE_FRAGMENTS = (
    ".private",
    "account_id",
    "api_key",
    "article_body",
    "chunk_text",
    "credential",
    "customer_id",
    "full_text",
    "internal_comment",
    "license_id",
    "private_path",
    "raw_html",
    "raw_internal",
    "raw_ticket",
    "raw_zendesk",
    "redaction_map",
    "secret",
    "snippet_text",
    "ticket.redacted.md",
    "ticket_id",
    "ticket.txt",
    "token",
    "vector",
    "zendesk_id",
)


def _scenario_id(path: Path) -> str:
    return path.name


def test_expected_cli_fixture_scenarios_are_present() -> None:
    scenario_names = {path.name for path in FIXTURE_ROOT.iterdir() if path.is_dir()}
    assert scenario_names == EXPECTED_SCENARIOS

    for scenario in EXPECTED_SCENARIOS:
        actual_files = {path.name for path in (FIXTURE_ROOT / scenario).iterdir()}
        assert actual_files == REQUIRED_SCENARIO_FILES


@pytest.mark.parametrize("scenario_dir", SCENARIO_DIRS, ids=_scenario_id)
def test_validate_evidence_cli_matches_expected_validation(
    scenario_dir: Path,
) -> None:
    result = _run_cli(
        "validate-evidence",
        "--input",
        str(scenario_dir / "evidence_packet.json"),
        "--json",
    )

    assert result.returncode == 0
    payload = _stdout_json(result)
    assert payload["schema_version"] == "kcs_cli_result_v1"
    assert payload["command"] == "validate-evidence"
    assert payload["payload"]["evidence_validation"] == _load_json(
        scenario_dir / "expected_validation.json"
    )


@pytest.mark.parametrize("scenario_dir", SCENARIO_DIRS, ids=_scenario_id)
def test_decide_cli_matches_expected_decision(scenario_dir: Path) -> None:
    result = _run_cli(
        "decide",
        "--input",
        str(scenario_dir / "evidence_packet.json"),
        "--reuse-results",
        str(scenario_dir / "reuse_results.json"),
        "--json",
    )

    assert result.returncode == 0
    payload = _stdout_json(result)
    assert payload["schema_version"] == "kcs_cli_result_v1"
    assert payload["command"] == "decide"
    assert _stable_decision(payload["payload"]["decision"]) == _stable_decision(
        _load_json(scenario_dir / "expected_decision.json")
    )
    assert not _contains_auto_publish_true(payload)
    assert not _contains_private_value(payload)


@pytest.mark.parametrize("scenario_dir", SCENARIO_DIRS, ids=_scenario_id)
def test_run_cli_returns_combined_safe_payload(scenario_dir: Path) -> None:
    result = _run_cli(
        "run",
        "--input",
        str(scenario_dir / "evidence_packet.json"),
        "--reuse-results",
        str(scenario_dir / "reuse_results.json"),
        "--json",
    )

    assert result.returncode == 0
    payload = _stdout_json(result)
    assert payload["schema_version"] == "kcs_cli_result_v1"
    assert payload["command"] == "run"
    assert set(payload["payload"]) == {
        "decision",
        "reviewer_packet",
        "validation_report",
    }
    expected_decision = _load_json(scenario_dir / "expected_decision.json")
    assert _stable_decision(payload["payload"]["decision"]) == _stable_decision(
        expected_decision
    )
    _assert_run_behavior(payload["payload"], expected_decision)
    assert not _contains_auto_publish_true(payload)
    assert not _contains_private_value(payload)


def test_malformed_json_returns_safe_error(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not-json", encoding="utf-8")

    result = _run_cli(
        "validate-evidence",
        "--input",
        str(malformed),
        "--json",
    )

    assert result.returncode == 2
    assert result.stdout == ""
    payload = json.loads(result.stderr)
    assert payload == {
        "schema_version": "kcs_cli_result_v1",
        "ok": False,
        "error": {"code": "malformed_json"},
    }
    assert "{not-json" not in result.stderr


@pytest.mark.parametrize(
    ("raw_json", "expected_code"),
    [
        ("[]", "json_payload_not_object"),
        ('{"schema_version": NaN}', "malformed_json"),
        ('{"schema_version": Infinity}', "malformed_json"),
        ('{"schema_version": -Infinity}', "malformed_json"),
    ],
)
def test_invalid_json_boundary_returns_safe_error(
    tmp_path: Path,
    raw_json: str,
    expected_code: str,
) -> None:
    payload_path = tmp_path / "invalid.json"
    payload_path.write_text(raw_json, encoding="utf-8")

    result = _run_cli(
        "validate-evidence",
        "--input",
        str(payload_path),
        "--json",
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert _stderr_json(result)["error"]["code"] == expected_code
    assert raw_json not in result.stderr


def test_invalid_utf8_returns_safe_error(tmp_path: Path) -> None:
    payload_path = tmp_path / "invalid-utf8.json"
    payload_path.write_bytes(b"\xff\xfe\x00")

    result = _run_cli(
        "validate-evidence",
        "--input",
        str(payload_path),
        "--json",
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert _stderr_json(result)["error"]["code"] == "malformed_json"
    assert "Traceback" not in result.stderr


def test_missing_file_returns_safe_error_without_echoing_path(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.json"

    result = _run_cli(
        "validate-evidence",
        "--input",
        str(missing_path),
        "--json",
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert _stderr_json(result)["error"]["code"] == "input_file_not_found"
    assert str(missing_path) not in result.stderr


def test_missing_required_cli_argument_returns_json_error() -> None:
    result = _run_cli("validate-evidence", "--json")

    assert result.returncode == 2
    assert result.stdout == ""
    assert _stderr_json(result)["error"]["code"] == "cli_usage_error"
    assert "usage:" not in result.stderr


def test_unsafe_evidence_returns_safe_boundary_output(tmp_path: Path) -> None:
    private_value = "person@example.com"
    evidence = _load_json(
        FIXTURE_ROOT / "003_create_candidate" / "evidence_packet.json"
    )
    evidence["symptoms"] = [f"Contact {private_value} for synthetic handling."]
    evidence_path = tmp_path / "unsafe-evidence.json"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    validate_result = _run_cli(
        "validate-evidence",
        "--input",
        str(evidence_path),
        "--json",
    )
    decide_result = _run_cli(
        "decide",
        "--input",
        str(evidence_path),
        "--reuse-results",
        str(FIXTURE_ROOT / "003_create_candidate" / "reuse_results.json"),
        "--json",
    )

    assert validate_result.returncode == 2
    assert validate_result.stdout == ""
    assert _stderr_json(validate_result)["error"]["code"] == "unsafe_input"
    assert private_value not in validate_result.stdout
    assert decide_result.returncode == 2
    assert decide_result.stdout == ""
    assert _stderr_json(decide_result)["error"]["code"] == "unsafe_input"
    assert private_value not in decide_result.stderr


def test_extra_raw_evidence_field_returns_safe_boundary_error(tmp_path: Path) -> None:
    private_value = "person@example.com"
    evidence = _load_json(
        FIXTURE_ROOT / "003_create_candidate" / "evidence_packet.json"
    )
    evidence["raw_ticket"] = private_value
    evidence_path = tmp_path / "evidence-extra-private.json"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    result = _run_cli(
        "validate-evidence",
        "--input",
        str(evidence_path),
        "--json",
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert _stderr_json(result)["error"]["code"] == "unsafe_input"
    assert private_value not in result.stderr


def test_extra_numeric_ticket_id_field_returns_safe_boundary_error(
    tmp_path: Path,
) -> None:
    private_value = 12345678
    evidence = _load_json(
        FIXTURE_ROOT / "003_create_candidate" / "evidence_packet.json"
    )
    evidence["ticket_id"] = private_value
    evidence_path = tmp_path / "evidence-extra-ticket-id.json"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    result = _run_cli(
        "validate-evidence",
        "--input",
        str(evidence_path),
        "--json",
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert _stderr_json(result)["error"]["code"] == "unsafe_input"
    assert str(private_value) not in result.stderr


def test_extra_numeric_id_field_returns_safe_boundary_error(tmp_path: Path) -> None:
    private_value = 12345678
    evidence = _load_json(
        FIXTURE_ROOT / "003_create_candidate" / "evidence_packet.json"
    )
    evidence["id"] = private_value
    evidence_path = tmp_path / "evidence-extra-id.json"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    result = _run_cli(
        "validate-evidence",
        "--input",
        str(evidence_path),
        "--json",
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert _stderr_json(result)["error"]["code"] == "unsafe_input"
    assert str(private_value) not in result.stderr


def test_public_config_filename_in_reuse_metadata_is_not_private_domain(
    tmp_path: Path,
) -> None:
    reuse_results = _load_json(
        FIXTURE_ROOT / "003_create_candidate" / "reuse_results.json"
    )
    reuse_results["synthetic_config_filename"] = "nginx.conf"
    reuse_path = tmp_path / "reuse-config-file.json"
    reuse_path.write_text(json.dumps(reuse_results), encoding="utf-8")

    result = _run_cli(
        "decide",
        "--input",
        str(FIXTURE_ROOT / "003_create_candidate" / "evidence_packet.json"),
        "--reuse-results",
        str(reuse_path),
        "--json",
    )

    assert result.returncode == 0
    assert result.stderr == ""


@pytest.mark.parametrize("command", ["decide", "run"])
def test_private_reuse_metadata_returns_safe_boundary_error(
    tmp_path: Path, command: str
) -> None:
    private_value = "PLSK.12345678.1234"
    reuse_results = _load_json(
        FIXTURE_ROOT / "001_reuse_existing" / "reuse_results.json"
    )
    reuse_results["matches"][0]["match_ref"] = private_value
    reuse_path = tmp_path / "reuse-private.json"
    reuse_path.write_text(json.dumps(reuse_results), encoding="utf-8")

    result = _run_cli(
        command,
        "--input",
        str(FIXTURE_ROOT / "001_reuse_existing" / "evidence_packet.json"),
        "--reuse-results",
        str(reuse_path),
        "--json",
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert _stderr_json(result)["error"]["code"] == "unsafe_input"
    assert private_value not in result.stderr


@pytest.mark.parametrize(
    "private_value",
    [
        "https://customer.example.net/private",
        "customer.example.net",
        "PLSK-12345678-1234",
        "EXT-12345678",
    ],
)
def test_private_reuse_metadata_shapes_are_rejected_by_cli_boundary(
    tmp_path: Path,
    private_value: str,
) -> None:
    reuse_results = _load_json(
        FIXTURE_ROOT / "001_reuse_existing" / "reuse_results.json"
    )
    reuse_results["matches"][0]["match_ref"] = private_value
    reuse_path = tmp_path / "reuse-private-shape.json"
    reuse_path.write_text(json.dumps(reuse_results), encoding="utf-8")

    result = _run_cli(
        "decide",
        "--input",
        str(FIXTURE_ROOT / "001_reuse_existing" / "evidence_packet.json"),
        "--reuse-results",
        str(reuse_path),
        "--json",
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert _stderr_json(result)["error"]["code"] == "unsafe_input"
    assert private_value not in result.stderr


def test_cli_fixtures_are_synthetic_and_do_not_embed_raw_source_material() -> None:
    for path in FIXTURE_ROOT.rglob("*.json"):
        text = path.read_text(encoding="utf-8").casefold()
        assert not any(fragment in text for fragment in FORBIDDEN_FIXTURE_FRAGMENTS), (
            f"{path} contains a forbidden raw/private fixture fragment"
        )
        assert not _contains_private_value(_load_json(path)), (
            f"{path} contains a private-looking value"
        )


def test_private_value_scanner_checks_mapping_keys() -> None:
    assert _contains_private_value({"ticket-12345": "safe"})


@pytest.mark.parametrize(
    "private_value",
    [
        "https://customer.example.net/private",
        "customer.example.net",
        "PLSK-12345678-1234",
        "EXT-12345678",
    ],
)
def test_private_value_scanner_catches_more_private_shapes(
    private_value: str,
) -> None:
    assert _contains_private_value({"safe": private_value})


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC_ROOT)
    return subprocess.run(
        [sys.executable, "-m", "kcs_core.cli", *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _stdout_json(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    return payload


def _stderr_json(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    payload = json.loads(result.stderr)
    assert isinstance(payload, dict)
    return payload


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _stable_decision(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": decision["schema_version"],
        "candidate_id": decision["candidate_id"],
        "recommended_action": decision["recommended_action"],
        "article_type": decision["article_type"],
        "status": decision["status"],
        "blockers": decision["blockers"],
        "selected_reuse_match": decision["selected_reuse_match"],
        "split_items": [_stable_split_item(item) for item in decision["split_items"]],
        "operator_override_allowed": decision["operator_override_allowed"],
        "allowed_override_modes": decision["allowed_override_modes"],
        "override_status": decision["override_status"],
        "auto_publish_allowed": decision["auto_publish_allowed"],
    }


def _stable_split_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": item["candidate_id"],
        "summary": item["summary"],
        "recommended_action": item["recommended_action"],
        "article_type": item["article_type"],
        "status": item["status"],
        "blockers": item["blockers"],
        "selected_reuse_match": item["selected_reuse_match"],
        "reuse_search_status": item["reuse_search_status"],
        "operator_override_allowed": item["operator_override_allowed"],
        "allowed_override_modes": item["allowed_override_modes"],
        "override_status": item["override_status"],
        "auto_publish_allowed": item["auto_publish_allowed"],
    }


def _assert_run_behavior(
    run_payload: dict[str, Any],
    expected_decision: dict[str, Any],
) -> None:
    action = expected_decision["recommended_action"]
    reviewer_packet = run_payload["reviewer_packet"]
    validation_report = run_payload["validation_report"]
    public_candidate = reviewer_packet["public_article_candidate"]
    zendesk_html = reviewer_packet["zendesk_source_html"]

    if action in {"create_candidate", "update_existing", "flag_existing"}:
        assert public_candidate is not None
        assert zendesk_html
    else:
        assert public_candidate is None
        assert zendesk_html is None

    if action in {"blocked", "split_required"}:
        assert validation_report["ready_for_reviewer"] is False
        assert validation_report["required_next_step"] != "none"
    else:
        assert validation_report["ready_for_reviewer"] is True
        assert validation_report["required_next_step"] == "none"


def _contains_auto_publish_true(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            (key == "auto_publish_allowed" and item is True)
            or _contains_auto_publish_true(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_auto_publish_true(item) for item in value)
    return False


def _contains_private_value(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            _contains_private_value(key) or _contains_private_value(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_private_value(item) for item in value)
    if isinstance(value, str):
        text_without_safe_public_urls = SAFE_PUBLIC_SUPPORT_URL_RE.sub("", value)
        return any(
            pattern.search(text_without_safe_public_urls)
            for pattern in PRIVATE_VALUE_PATTERNS
        )
    return False
