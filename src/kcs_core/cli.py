"""Local CLI entrypoint for deterministic KCS core verification."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kcs_core.decision import decide_kcs_action
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import dump_json_dict
from kcs_core.models import (
    NormalizedTicketEvidencePacket,
    ReuseSearchResultsPacket,
)
from kcs_core.readiness import build_validation_report
from kcs_core.renderer import render_reviewer_packet
from kcs_core.validation import EvidenceBlocker, validate_evidence_packet

_CLI_SCHEMA_VERSION = "kcs_cli_result_v1"
_PRIVATE_VALUE_PATTERNS = (
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
_SAFE_CONFIG_FILENAME_RE = re.compile(
    r"\b[A-Za-z0-9_-]+\.(?:conf|ini|cnf|yaml|yml|json|xml)\b"
)
_RAW_ID_VALUE_RE = re.compile(r"\d{6,}")
_UNSAFE_RAW_FRAGMENTS = (
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


@dataclass(frozen=True)
class _CliError(Exception):
    code: str


class _CliArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _CliError("cli_usage_error")


def validate_evidence_command(args: argparse.Namespace) -> int:
    """Validate a normalized evidence packet and print deterministic JSON."""

    evidence = _load_evidence(args.input)
    validation = validate_evidence_packet(evidence)
    _print_result(
        args.command,
        validation.ok,
        {
            "packet_schema_version": evidence.schema_version,
            "evidence_validation": validation.to_json_dict(),
        },
    )
    return _exit_code_for_validation(validation.blockers)


def decide_command(args: argparse.Namespace) -> int:
    """Run deterministic KCS decision logic and print deterministic JSON."""

    evidence = _load_evidence(args.input)
    _ensure_safe_cli_boundary(evidence)
    reuse_results = _load_reuse_results(args.reuse_results)
    decision = decide_kcs_action(evidence, reuse_results)
    _print_result(
        args.command,
        True,
        {
            "decision": dump_json_dict(decision),
        },
    )
    return 0


def run_command(args: argparse.Namespace) -> int:
    """Run implemented KCS core stages and print deterministic JSON."""

    evidence = _load_evidence(args.input)
    _ensure_safe_cli_boundary(evidence)
    reuse_results = _load_reuse_results(args.reuse_results)
    decision = decide_kcs_action(evidence, reuse_results)
    reviewer_packet = render_reviewer_packet(evidence, decision)
    validation_report = build_validation_report(evidence, decision, reviewer_packet)
    _print_result(
        args.command,
        True,
        {
            "decision": dump_json_dict(decision),
            "reviewer_packet": dump_json_dict(reviewer_packet),
            "validation_report": dump_json_dict(validation_report),
        },
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Return the KCS local verification CLI parser."""

    parser = _CliArgumentParser(
        description="Run local deterministic KCS core verification commands."
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        parser_class=_CliArgumentParser,
    )

    validate_parser = subparsers.add_parser(
        "validate-evidence",
        help="Validate a normalized evidence packet.",
    )
    _add_input_arg(validate_parser)
    _add_json_arg(validate_parser)
    validate_parser.set_defaults(func=validate_evidence_command)

    decide_parser = subparsers.add_parser(
        "decide",
        help="Run deterministic KCS action decision logic.",
    )
    _add_input_arg(decide_parser)
    _add_reuse_results_arg(decide_parser)
    _add_json_arg(decide_parser)
    decide_parser.set_defaults(func=decide_command)

    run_parser = subparsers.add_parser(
        "run",
        help="Run implemented local KCS stages.",
    )
    _add_input_arg(run_parser)
    _add_reuse_results_arg(run_parser)
    _add_json_arg(run_parser)
    run_parser.set_defaults(func=run_command)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI process entrypoint."""

    try:
        parser = build_parser()
        args = parser.parse_args(argv)
        return args.func(args)
    except _CliError as exc:
        _print_error(exc.code)
        return 2
    except ContractValidationError:
        _print_error("contract_validation_failed")
        return 2


def _add_input_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to a normalized evidence packet JSON file.",
    )


def _add_reuse_results_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--reuse-results",
        required=True,
        type=Path,
        help="Path to a reuse/search results packet JSON file.",
    )


def _add_json_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        help="Accepted for explicit local verification JSON output.",
    )


def _load_evidence(path: Path) -> NormalizedTicketEvidencePacket:
    return NormalizedTicketEvidencePacket.from_json_dict(_load_json_object(path))


def _load_reuse_results(path: Path) -> ReuseSearchResultsPacket:
    return ReuseSearchResultsPacket.from_json_dict(_load_json_object(path))


def _load_json_object(path: Path) -> Mapping[str, Any]:
    try:
        data = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_json_constant,
        )
    except FileNotFoundError as exc:
        raise _CliError("input_file_not_found") from exc
    except UnicodeDecodeError as exc:
        raise _CliError("malformed_json") from exc
    except OSError as exc:
        raise _CliError("input_file_unreadable") from exc
    except (json.JSONDecodeError, ValueError) as exc:
        raise _CliError("malformed_json") from exc
    if not isinstance(data, Mapping):
        raise _CliError("json_payload_not_object")
    _ensure_safe_raw_json_boundary(data)
    return data


def _reject_json_constant(value: str) -> None:
    raise ValueError("non-standard JSON constant")


def _ensure_safe_raw_json_boundary(payload: Mapping[str, Any]) -> None:
    if _contains_private_raw_value(payload):
        raise _CliError("unsafe_input")


def _contains_private_raw_value(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_private_raw_item(key, item) for key, item in value.items())
    if isinstance(value, list | tuple):
        return any(_contains_private_raw_value(item) for item in value)
    if isinstance(value, str):
        return _contains_private_raw_text(value)
    return False


def _contains_private_raw_item(key: object, value: object) -> bool:
    return (
        _contains_private_raw_value(key)
        or _is_generic_raw_id_value(key, value)
        or _contains_private_raw_value(value)
    )


def _is_generic_raw_id_value(key: object, value: object) -> bool:
    if not isinstance(key, str) or key.casefold() != "id":
        return False
    if isinstance(value, int) and not isinstance(value, bool):
        return value >= 100000
    if isinstance(value, str):
        return bool(_RAW_ID_VALUE_RE.fullmatch(value.strip()))
    return False


def _contains_private_raw_text(value: str) -> bool:
    normalized = value.casefold()
    if any(fragment in normalized for fragment in _UNSAFE_RAW_FRAGMENTS):
        return True
    text_without_config_names = _SAFE_CONFIG_FILENAME_RE.sub("", value)
    return any(
        pattern.search(text_without_config_names) for pattern in _PRIVATE_VALUE_PATTERNS
    )


def _ensure_safe_cli_boundary(packet: NormalizedTicketEvidencePacket) -> None:
    result = validate_evidence_packet(packet)
    if EvidenceBlocker.UNSAFE_INPUT.value in result.blockers:
        raise _CliError("unsafe_input")


def _exit_code_for_validation(blockers: Sequence[str]) -> int:
    if EvidenceBlocker.UNSAFE_INPUT.value in blockers:
        return 2
    return 0


def _print_result(command: str, ok: bool, payload: Mapping[str, Any]) -> None:
    print(
        _json_dumps(
            {
                "schema_version": _CLI_SCHEMA_VERSION,
                "command": command,
                "ok": ok,
                "payload": dict(payload),
            }
        )
    )


def _print_error(code: str) -> None:
    print(
        _json_dumps(
            {
                "schema_version": _CLI_SCHEMA_VERSION,
                "ok": False,
                "error": {"code": code},
            }
        ),
        file=sys.stderr,
    )


def _json_dumps(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, allow_nan=False, indent=2, sort_keys=True)


if __name__ == "__main__":
    raise SystemExit(main())
