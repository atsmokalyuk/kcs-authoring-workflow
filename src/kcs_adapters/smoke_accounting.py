"""Local smoke transcript accounting for Claude Desktop MCP runs."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SMOKE_ACCOUNTING_SCHEMA_VERSION = "kcs_smoke_accounting_v1"
DEFAULT_CHARS_PER_TOKEN = 4.0
DEFAULT_INPUT_PRICE_PER_MTOK_USD = 3.0
DEFAULT_OUTPUT_PRICE_PER_MTOK_USD = 15.0

_TOOL_NAME_RE = re.compile(r"\bkcs_[a-z0-9_]+\b", re.I)
_TOOL_CALL_HINT_RE = re.compile(
    r"\b(?:call(?:ed|ing)?|tool|Kcs|kcs)[^\n]{0,80}\bkcs_[a-z0-9_]+\b",
    re.I,
)
_FAILURE_RE = re.compile(
    r"\b(?:failed|failure|timeout|timed out|tool_failed|validation_failed|"
    r"input_validation|blocked|invalid)\b",
    re.I,
)
_CONTROLLED_SUCCESS_RE = re.compile(
    r"\b(?:pipeline_ok|validation_ok|ready_for_reviewer|smoke_ok)\b"
    r"[^\\n]{0,40}\b(?:true|✅)",
    re.I,
)
_MANUAL_FALLBACK_RE = re.compile(
    r"\b(?:draft(?:ed)? (?:this )?directly|manual draft|in the meantime,? "
    r"I can draft|without (?:the )?KCS tool|tool .*not respond)\b",
    re.I,
)
_KCS_DRAFT_CLIENT_CALL_RE = re.compile(
    r"Message from client: (?=.*?\"name\":\"kcs_draft_article\")",
    re.I,
)
_KCS_DRAFT_SELECTION_RE = re.compile(
    r"Message from client: (?=.*?\"name\":\"kcs_draft_article\")"
    r"(?=.*?\"operator_choice_confirmed\":true)",
    re.I,
)
_KCS_DRAFT_UPLOAD_REF_RE = re.compile(
    r"Message from client: (?=.*?\"name\":\"kcs_draft_article\")"
    r"(?=.*?\"ticket_ref\":\"/(?:mnt|Users|private|tmp|var)/)",
    re.I,
)
_KCS_DRAFT_SUCCESS_RE = re.compile(
    r"Reviewer-only Zendesk HTML draft:.*?\\?\"should_be_kcs_article\\?\":true"
    r".*?\\?\"validation_ok\\?\":true",
    re.I,
)
_KCS_DRAFT_SPLIT_RE = re.compile(
    r"\\?\"blockers\\?\":\[\\?\"multiple_kcs_items_detected\\?\"\].*?"
    r"\\?\"operator_prompt_style\\?\":\\?\"native_choice_popup\\?\"",
    re.I,
)
_KCS_DRAFT_BLOCKER_RE = re.compile(
    r"\\?\"blockers\\?\":\[\\?\"([a-z0-9_]+)\\?\"\]",
    re.I,
)
_TOOL_RESULT_INVALID_RE = re.compile(
    r"\\?\"error_code\\?\":\\?\"tool_result_invalid\\?\"",
    re.I,
)
_TIMEOUT_OR_DISCONNECT_RE = re.compile(
    r"\b(?:timed out|timeout|Server disconnected|closed unexpectedly)\b",
    re.I,
)


@dataclass(frozen=True)
class SmokeAccountingReport:
    """Compact value-safe accounting result for one local smoke transcript."""

    schema_version: str
    ok: bool
    source_kind: str
    log_bytes: int
    log_chars: int
    estimated_log_tokens: int
    estimated_input_cost_usd: float
    estimated_output_cost_usd: float
    estimated_upper_bound_cost_usd: float
    chars_per_token: float
    input_price_per_mtok_usd: float
    output_price_per_mtok_usd: float
    tool_call_count: int
    unique_tools: tuple[str, ...]
    failure_marker_count: int
    controlled_success_marker_count: int
    manual_fallback_marker_count: int
    kcs_draft_call_count: int
    kcs_draft_selected_call_count: int
    kcs_draft_split_required_count: int
    kcs_draft_success_count: int
    kcs_draft_upload_ticket_ref_count: int
    kcs_draft_blocker_codes: tuple[str, ...]
    tool_result_invalid_count: int
    timeout_or_disconnect_count: int
    manual_fallback_observed: bool
    deterministic_kcs_draft_smoke_passed: bool
    retry_risk: str
    billing_exact: bool
    notes: tuple[str, ...]

    def to_json_dict(self) -> dict[str, object]:
        return {
            "billing_exact": self.billing_exact,
            "chars_per_token": self.chars_per_token,
            "controlled_success_marker_count": self.controlled_success_marker_count,
            "estimated_input_cost_usd": self.estimated_input_cost_usd,
            "estimated_log_tokens": self.estimated_log_tokens,
            "estimated_output_cost_usd": self.estimated_output_cost_usd,
            "estimated_upper_bound_cost_usd": self.estimated_upper_bound_cost_usd,
            "failure_marker_count": self.failure_marker_count,
            "input_price_per_mtok_usd": self.input_price_per_mtok_usd,
            "log_bytes": self.log_bytes,
            "log_chars": self.log_chars,
            "kcs_draft_blocker_codes": list(self.kcs_draft_blocker_codes),
            "kcs_draft_call_count": self.kcs_draft_call_count,
            "kcs_draft_selected_call_count": self.kcs_draft_selected_call_count,
            "kcs_draft_split_required_count": self.kcs_draft_split_required_count,
            "kcs_draft_success_count": self.kcs_draft_success_count,
            "kcs_draft_upload_ticket_ref_count": self.kcs_draft_upload_ticket_ref_count,
            "manual_fallback_marker_count": self.manual_fallback_marker_count,
            "manual_fallback_observed": self.manual_fallback_observed,
            "notes": list(self.notes),
            "ok": self.ok,
            "output_price_per_mtok_usd": self.output_price_per_mtok_usd,
            "deterministic_kcs_draft_smoke_passed": (
                self.deterministic_kcs_draft_smoke_passed
            ),
            "retry_risk": self.retry_risk,
            "schema_version": self.schema_version,
            "source_kind": self.source_kind,
            "timeout_or_disconnect_count": self.timeout_or_disconnect_count,
            "tool_call_count": self.tool_call_count,
            "tool_result_invalid_count": self.tool_result_invalid_count,
            "unique_tools": list(self.unique_tools),
        }


@dataclass(frozen=True)
class _CliError(Exception):
    code: str


@dataclass(frozen=True)
class _SmokeMarkers:
    tool_names: tuple[str, ...]
    tool_call_count: int
    failure_count: int
    fallback_count: int
    controlled_success_count: int
    draft_call_count: int
    draft_selected_count: int
    draft_split_count: int
    draft_success_count: int
    draft_upload_ticket_ref_count: int
    draft_blocker_codes: tuple[str, ...]
    tool_result_invalid_count: int
    timeout_or_disconnect_count: int

    @property
    def deterministic_draft_passed(self) -> bool:
        return (
            self.draft_call_count > 0
            and self.draft_split_count > 0
            and self.draft_selected_count > 0
            and self.draft_success_count > 0
            and self.fallback_count == 0
            and self.tool_result_invalid_count == 0
        )


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _CliError("cli_usage_error")


def build_smoke_accounting_report(
    text: str,
    *,
    source_kind: str = "claude_desktop_transcript",
    chars_per_token: float = DEFAULT_CHARS_PER_TOKEN,
    input_price_per_mtok_usd: float = DEFAULT_INPUT_PRICE_PER_MTOK_USD,
    output_price_per_mtok_usd: float = DEFAULT_OUTPUT_PRICE_PER_MTOK_USD,
) -> SmokeAccountingReport:
    """Return a value-safe cost proxy for a local Claude Desktop smoke transcript."""

    _validate_positive_number(chars_per_token)
    _validate_non_negative_number(input_price_per_mtok_usd)
    _validate_non_negative_number(output_price_per_mtok_usd)

    log_chars = len(text)
    estimated_tokens = _estimate_tokens(log_chars, chars_per_token)
    markers = _smoke_markers(text)
    return SmokeAccountingReport(
        billing_exact=False,
        chars_per_token=chars_per_token,
        controlled_success_marker_count=markers.controlled_success_count,
        deterministic_kcs_draft_smoke_passed=markers.deterministic_draft_passed,
        estimated_input_cost_usd=_cost(estimated_tokens, input_price_per_mtok_usd),
        estimated_log_tokens=estimated_tokens,
        estimated_output_cost_usd=_cost(estimated_tokens, output_price_per_mtok_usd),
        estimated_upper_bound_cost_usd=_cost(
            estimated_tokens,
            input_price_per_mtok_usd + output_price_per_mtok_usd,
        ),
        failure_marker_count=markers.failure_count,
        input_price_per_mtok_usd=input_price_per_mtok_usd,
        kcs_draft_blocker_codes=markers.draft_blocker_codes,
        kcs_draft_call_count=markers.draft_call_count,
        kcs_draft_selected_call_count=markers.draft_selected_count,
        kcs_draft_split_required_count=markers.draft_split_count,
        kcs_draft_success_count=markers.draft_success_count,
        kcs_draft_upload_ticket_ref_count=markers.draft_upload_ticket_ref_count,
        log_bytes=len(text.encode("utf-8")),
        log_chars=log_chars,
        manual_fallback_marker_count=markers.fallback_count,
        manual_fallback_observed=markers.fallback_count > 0,
        notes=_notes(),
        ok=True,
        output_price_per_mtok_usd=output_price_per_mtok_usd,
        retry_risk=_retry_risk(markers.failure_count, markers.fallback_count),
        schema_version=SMOKE_ACCOUNTING_SCHEMA_VERSION,
        source_kind=source_kind,
        timeout_or_disconnect_count=markers.timeout_or_disconnect_count,
        tool_call_count=markers.tool_call_count,
        tool_result_invalid_count=markers.tool_result_invalid_count,
        unique_tools=markers.tool_names,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        description="Estimate local Claude Desktop MCP smoke transcript cost."
    )
    parser.add_argument("--log", required=True, type=Path, help="Transcript/log file.")
    parser.add_argument(
        "--chars-per-token",
        default=DEFAULT_CHARS_PER_TOKEN,
        type=float,
        help="Approximation divisor for token estimate. Default: 4.",
    )
    parser.add_argument(
        "--input-price-per-mtok",
        default=DEFAULT_INPUT_PRICE_PER_MTOK_USD,
        type=float,
        help="Input token price per million tokens in USD. Default: 3.",
    )
    parser.add_argument(
        "--output-price-per-mtok",
        default=DEFAULT_OUTPUT_PRICE_PER_MTOK_USD,
        type=float,
        help="Output token price per million tokens in USD. Default: 15.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Accepted for explicit JSON output.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        text = _read_text(args.log)
        report = build_smoke_accounting_report(
            text,
            chars_per_token=args.chars_per_token,
            input_price_per_mtok_usd=args.input_price_per_mtok,
            output_price_per_mtok_usd=args.output_price_per_mtok,
        )
        _write_json(sys.stdout, report.to_json_dict())
        return 0
    except _CliError as exc:
        _write_json(
            sys.stderr,
            {
                "error": {"code": exc.code},
                "ok": False,
                "schema_version": SMOKE_ACCOUNTING_SCHEMA_VERSION,
            },
        )
        return 2


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise _CliError("log_file_not_found") from exc
    except UnicodeDecodeError as exc:
        raise _CliError("log_file_not_utf8") from exc
    except OSError as exc:
        raise _CliError("log_file_unreadable") from exc


def _tool_names(text: str) -> tuple[str, ...]:
    return tuple(
        sorted({match.group(0).lower() for match in _TOOL_NAME_RE.finditer(text)})
    )


def _tool_call_count(text: str) -> int:
    return sum(1 for line in text.splitlines() if _TOOL_CALL_HINT_RE.search(line))


def _smoke_markers(text: str) -> _SmokeMarkers:
    return _SmokeMarkers(
        controlled_success_count=len(_CONTROLLED_SUCCESS_RE.findall(text)),
        draft_blocker_codes=_kcs_draft_blocker_codes(text),
        draft_call_count=len(_KCS_DRAFT_CLIENT_CALL_RE.findall(text)),
        draft_selected_count=len(_KCS_DRAFT_SELECTION_RE.findall(text)),
        draft_split_count=len(_KCS_DRAFT_SPLIT_RE.findall(text)),
        draft_success_count=len(_KCS_DRAFT_SUCCESS_RE.findall(text)),
        draft_upload_ticket_ref_count=len(_KCS_DRAFT_UPLOAD_REF_RE.findall(text)),
        failure_count=len(_FAILURE_RE.findall(text)),
        fallback_count=len(_MANUAL_FALLBACK_RE.findall(text)),
        timeout_or_disconnect_count=len(_TIMEOUT_OR_DISCONNECT_RE.findall(text)),
        tool_call_count=_tool_call_count(text),
        tool_names=_tool_names(text),
        tool_result_invalid_count=len(_TOOL_RESULT_INVALID_RE.findall(text)),
    )


def _kcs_draft_blocker_codes(text: str) -> tuple[str, ...]:
    return tuple(
        sorted({match.group(1) for match in _KCS_DRAFT_BLOCKER_RE.finditer(text)})
    )


def _estimate_tokens(chars: int, chars_per_token: float) -> int:
    if chars == 0:
        return 0
    return math.ceil(chars / chars_per_token)


def _cost(tokens: int, price_per_mtok: float) -> float:
    return round((tokens / 1_000_000) * price_per_mtok, 6)


def _retry_risk(failure_count: int, fallback_count: int) -> str:
    if fallback_count > 0 or failure_count >= 5:
        return "high"
    if failure_count > 0:
        return "medium"
    return "low"


def _notes() -> tuple[str, ...]:
    return (
        "Claude Desktop/MCP does not expose exact provider billing tokens here.",
        "Token and cost values are local estimates for comparing smoke runs.",
        "Use provider API usage fields for exact billing when direct API is used.",
    )


def _validate_positive_number(value: float) -> None:
    if not math.isfinite(value) or value <= 0:
        raise _CliError("invalid_numeric_option")


def _validate_non_negative_number(value: float) -> None:
    if not math.isfinite(value) or value < 0:
        raise _CliError("invalid_numeric_option")


def _write_json(stream: Any, payload: dict[str, object]) -> None:
    stream.write(json.dumps(payload, allow_nan=False, sort_keys=True))
    stream.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
