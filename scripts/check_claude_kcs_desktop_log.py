"""Check Claude Desktop logs for the active KCS Authoring tool surface."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_LOG_PATH = (
    Path.home() / "Library" / "Logs" / "Claude" / "mcp-server-KCS Authoring.log"
)
SCHEMA_VERSION = "kcs_claude_desktop_log_check_v1"
_TIMESTAMP_LEN = 24
_MAX_LOG_BYTES = 1024 * 1024


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = check_log(
        log_path=args.log_path,
        max_bytes=args.max_bytes,
        since=args.since,
    )
    _write_json(sys.stdout, report)
    return 0 if report["ok"] is True else 2


def check_log(
    *,
    log_path: Path,
    max_bytes: int,
    since: str | None = None,
) -> dict[str, Any]:
    since_dt = _parse_timestamp(since) if since else None
    text = _read_log_tail(log_path=log_path, max_bytes=max_bytes)
    if text is None:
        return _failure("log_not_found", log_path=log_path)
    line = _latest_tool_surface_line(text, since=since_dt)
    if line is None:
        return _failure("tools_list_not_found", log_path=log_path)
    checks = _tool_surface_checks(line)
    initialize_line = _latest_initialize_line(text, since=since_dt)
    return {
        "checks": checks,
        "client_capabilities": _client_capability_summary(initialize_line),
        "latest_initialize_at": _line_timestamp(initialize_line)
        if initialize_line is not None
        else None,
        "latest_tools_list_at": _line_timestamp(line),
        "log_file": log_path.name,
        "ok": all(checks.values()),
        "schema_version": SCHEMA_VERSION,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--log-path",
        default=str(DEFAULT_LOG_PATH),
        type=Path,
        help="Claude Desktop KCS Authoring MCP server log path.",
    )
    parser.add_argument(
        "--max-bytes",
        default=_MAX_LOG_BYTES,
        type=int,
        help="Maximum bytes to inspect from the end of the log.",
    )
    parser.add_argument(
        "--since",
        default=None,
        help="Optional UTC ISO timestamp. Older log entries are ignored.",
    )
    return parser


def _read_log_tail(*, log_path: Path, max_bytes: int) -> str | None:
    if max_bytes <= 0:
        return ""
    try:
        with log_path.open("rb") as stream:
            stream.seek(0, 2)
            size = stream.tell()
            stream.seek(max(0, size - max_bytes))
            return stream.read().decode("utf-8", errors="replace")
    except OSError:
        return None


def _latest_tool_surface_line(text: str, *, since: datetime | None) -> str | None:
    for line in reversed(text.splitlines()):
        if not _is_tool_surface_line(line):
            continue
        timestamp = _parse_line_timestamp(line)
        if since is not None and (timestamp is None or timestamp < since):
            continue
        return line
    return None


def _latest_initialize_line(text: str, *, since: datetime | None) -> str | None:
    for line in reversed(text.splitlines()):
        if not _is_initialize_line(line):
            continue
        timestamp = _parse_line_timestamp(line)
        if since is not None and (timestamp is None or timestamp < since):
            continue
        return line
    return None


def _is_tool_surface_line(line: str) -> bool:
    return (
        "Message from server" in line
        and '"tools":[' in line
        and '"name":"kcs_draft_article"' in line
    )


def _is_initialize_line(line: str) -> bool:
    return (
        "Message from client" in line
        and '"method":"initialize"' in line
        and '"capabilities"' in line
    )


def _tool_surface_checks(line: str) -> dict[str, bool]:
    return {
        "annotations_non_read_only": '"readOnlyHint":false' in line,
        "annotations_non_idempotent": '"idempotentHint":false' in line,
        "thin_argument_visible": _thin_argument_visible(line),
        "old_item_schema_absent": '"item"' not in line,
        "old_item_candidates_schema_absent": '"item_candidates"' not in line,
        "old_reference_article_html_absent": '"reference_article_html"' not in line,
    }


def _client_capability_summary(line: str | None) -> dict[str, bool]:
    if line is None:
        return {
            "elicitation_declared": False,
            "initialize_observed": False,
            "mcp_ui_extension_declared": False,
        }
    return {
        "elicitation_declared": '"elicitation"' in line,
        "initialize_observed": True,
        "mcp_ui_extension_declared": "io.modelcontextprotocol/ui" in line,
    }


def _thin_argument_visible(line: str) -> bool:
    return any(
        fragment in line
        for fragment in (
            '"approved_summary_text"',
            '"operator_selected_item_ref"',
            '"operator_selection_ref"',
        )
    )


def _parse_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        raise SystemExit("Invalid --since timestamp") from None


def _parse_line_timestamp(line: str) -> datetime | None:
    if len(line) < _TIMESTAMP_LEN:
        return None
    return _parse_timestamp(line[:_TIMESTAMP_LEN])


def _line_timestamp(line: str) -> str | None:
    timestamp = _parse_line_timestamp(line)
    if timestamp is None:
        return None
    return timestamp.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _failure(code: str, *, log_path: Path) -> dict[str, Any]:
    return {
        "checks": {code: False},
        "error_code": code,
        "log_file": log_path.name,
        "ok": False,
        "schema_version": SCHEMA_VERSION,
    }


def _write_json(stream: Any, payload: dict[str, Any]) -> None:
    stream.write(json.dumps(payload, allow_nan=False, sort_keys=True))
    stream.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
