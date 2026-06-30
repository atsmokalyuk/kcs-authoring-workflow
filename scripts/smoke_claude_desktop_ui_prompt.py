"""Send a synthetic KCS prompt to Claude Desktop and verify MCP log behavior."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "kcs_claude_desktop_ui_prompt_smoke_v1"
DEFAULT_LOG_PATH = (
    Path.home() / "Library" / "Logs" / "Claude" / "mcp-server-KCS Authoring.log"
)
DEFAULT_WEB_LOG_PATH = Path.home() / "Library" / "Logs" / "Claude" / "claude.ai-web.log"
DEFAULT_FAILURE_SCREENSHOT_PATH = Path("/private/tmp/kcs-claude-ui-smoke-failure.png")
DEFAULT_MANUAL_PROMPT_PATH = Path("/private/tmp/kcs-claude-ui-smoke-prompt.txt")
_MAX_LOG_BYTES = 1024 * 1024
_TOOL_CALL_RE = re.compile(
    r'Message from client: .*"name":"kcs_draft_article"',
    re.I,
)
_TOOL_RESULT_RE = re.compile(
    r"Message from server: .*kcs_mcp_tool_result_v1",
    re.I,
)
_TOOL_RESULT_DEBUG_CODE_RE = re.compile(
    r'\\?"debug_code\\?"\s*:\s*\\?"(?P<value>[A-Za-z0-9_-]+)',
    re.I,
)
_TOOL_RESULT_FAILURE_STAGE_RE = re.compile(
    r'\\?"failure_stage\\?"\s*:\s*\\?"(?P<value>[A-Za-z0-9_-]+)',
    re.I,
)
_TOOL_RESULT_RECOMMENDED_ACTION_RE = re.compile(
    r'\\?"recommended_action\\?"\s*:\s*\\?"(?P<value>[A-Za-z0-9_-]+)',
    re.I,
)
_SPLIT_RE = re.compile(r"multiple_kcs_items_detected|split_required", re.I)
_SPLIT_FALLBACK_TEXT_RE = re.compile(
    r"Multiple KCS article candidates were detected.*"
    r"submit_arguments.*Do not draft manually",
    re.I | re.S,
)
_DRAFT_RE = re.compile(
    r"draft_only_reuse_search_mi|Reviewer-only Zendesk HTML|"
    r'\\?"recommended_action\\?"\s*:\s*\\?"draft_only',
    re.I,
)
_PROVIDER_UNAVAILABLE_RE = re.compile(
    r"semantic_extraction_provider_unavailable",
    re.I,
)
_OLD_ARG_RE = re.compile(
    r'"(?:item|item_candidates|reference_article_html)"\s*:',
    re.I,
)
_SUMMARY_ARG_RE = re.compile(r'"approved_summary_text"\s*:', re.I)
_SELECTION_REF_ARG_RE = re.compile(r'"operator_selection_ref"\s*:', re.I)
_SELECTED_ITEM_ARG_RE = re.compile(r'"operator_selected_item_ref"\s*:', re.I)
_MANUAL_FALLBACK_RE = re.compile(
    r"\b(?:manual draft|drafted this directly|draft directly|"
    r"I can draft (?:a |the )?KCS-style|"
    r"I can draft .* directly|without the KCS tool|tool .*not respond)\b",
    re.I,
)
_TIMEOUT_OR_DISCONNECT_RE = re.compile(
    r"\b(?:timed out|timeout|Server disconnected|closed unexpectedly)\b",
    re.I,
)
_TIMESTAMP_LEN = 24
_CLIENT_TOOL_CALL_LINE_RE = re.compile(
    r'Message from client: .*"name":"kcs_draft_article"',
    re.I,
)
_WEB_KCS_APPROVAL_GATE_RE = re.compile(
    r'\[MCP\] tool_approval_gate .*"toolName":"KCS Authoring:kcs_draft_article"',
    re.I,
)
_WEB_KCS_APPROVAL_RELEASED_RE = re.compile(
    r'\[MCP\] tool_approval_gate .*"toolName":"KCS Authoring:kcs_draft_article"'
    r'.*"approvalRequired":false',
    re.I,
)
_WEB_COMPLETION_RATE_LIMIT_RE = re.compile(
    r"\[COMPLETION\] Request failed .*rate_limit_error|exceeded_limit",
    re.I,
)
_WEB_COMPLETION_ERROR_RE = re.compile(
    r"\[COMPLETION\] Request failed|\[COMPLETION\] Not retryable error",
    re.I,
)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.print_manual_prompt:
        _write_json(
            sys.stdout,
            _manual_prompt_report(
                prompt_kind=args.prompt_kind,
                prompt_path=args.manual_prompt_path,
                copy_to_clipboard=args.copy_manual_prompt,
            ),
        )
        return 0
    if args.check_accessibility:
        report = _accessibility_preflight_report(
            timeout_seconds=args.osascript_timeout_seconds,
        )
        _write_json(sys.stdout, report)
        return 0 if report["ok"] is True else 2
    started_at = _parse_since_arg(args.since) if args.since else datetime.now(UTC)
    prompt = _prompt(args.prompt_kind)
    send_error_code = None
    frontmost_app = None
    prompt_sent = args.assume_sent
    if args.send:
        accessibility_warning = _accessibility_warning_code(
            timeout_seconds=args.osascript_timeout_seconds,
        )
        if accessibility_warning is not None:
            send_result = {
                "error_code": accessibility_warning,
                "frontmost_app": None,
                "ok": False,
            }
        else:
            send_result = _send_prompt_to_claude(
                prompt=prompt,
                restart=args.restart,
                open_delay_seconds=args.open_delay_seconds,
                click_x_ratio=args.click_x_ratio,
                click_y_ratio=args.click_y_ratio,
                osascript_timeout_seconds=args.osascript_timeout_seconds,
            )
        prompt_sent = send_result["ok"]
        send_error_code = send_result["error_code"]
        frontmost_app = send_result["frontmost_app"]
    report = _wait_for_report(
        log_path=args.log_path,
        web_log_path=args.web_log_path,
        since=started_at,
        timeout_seconds=args.timeout_seconds if prompt_sent else 0.0,
        poll_interval_seconds=args.poll_interval_seconds,
        prompt_kind=args.prompt_kind,
        sent=prompt_sent,
    )
    report["frontmost_app"] = frontmost_app
    report["failure_screenshot_path"] = _maybe_capture_failure_screenshot(
        enabled=args.send and not report["ok"],
        path=args.failure_screenshot_path,
    )
    report["send_error_code"] = send_error_code
    _write_json(sys.stdout, report)
    return 0 if report["ok"] is True else 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--send",
        action="store_true",
        help="Actually paste and submit the synthetic prompt in Claude Desktop.",
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Quit and reopen Claude Desktop before sending the prompt.",
    )
    parser.add_argument(
        "--prompt-kind",
        choices=("single", "split", "narrative", "raw-ticket"),
        default="single",
        help="Synthetic prompt shape to send.",
    )
    parser.add_argument(
        "--log-path",
        default=str(DEFAULT_LOG_PATH),
        type=Path,
        help="Claude Desktop KCS Authoring MCP server log path.",
    )
    parser.add_argument(
        "--web-log-path",
        default=str(DEFAULT_WEB_LOG_PATH),
        type=Path,
        help="Claude Desktop web log path used for pre-MCP failure diagnostics.",
    )
    parser.add_argument(
        "--timeout-seconds",
        default=90.0,
        type=float,
        help="How long to wait for fresh MCP log evidence after sending.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        default=2.0,
        type=float,
        help="Log polling interval.",
    )
    parser.add_argument(
        "--open-delay-seconds",
        default=5.0,
        type=float,
        help="Delay after opening Claude Desktop before pasting.",
    )
    parser.add_argument(
        "--since",
        help=(
            "Analyze log entries at or after this UTC ISO timestamp instead of "
            "the current command start time."
        ),
    )
    parser.add_argument(
        "--assume-sent",
        action="store_true",
        help="Treat an existing-log analysis window as an already sent prompt.",
    )
    parser.add_argument(
        "--click-x-ratio",
        default=0.52,
        type=float,
        help="Claude window-relative x ratio used to focus the composer.",
    )
    parser.add_argument(
        "--click-y-ratio",
        default=0.43,
        type=float,
        help="Claude window-relative y ratio used to focus the composer.",
    )
    parser.add_argument(
        "--osascript-timeout-seconds",
        default=15.0,
        type=float,
        help="Fail the UI send if the AppleScript automation hangs.",
    )
    parser.add_argument(
        "--failure-screenshot-path",
        default=DEFAULT_FAILURE_SCREENSHOT_PATH,
        type=Path,
        help="Screenshot path written when a real UI send attempt fails.",
    )
    parser.add_argument(
        "--check-accessibility",
        action="store_true",
        help="Only check whether macOS is blocking Codex.app GUI control.",
    )
    parser.add_argument(
        "--print-manual-prompt",
        action="store_true",
        help="Print a synthetic prompt and UTC timestamp for manual UI smoke.",
    )
    parser.add_argument(
        "--manual-prompt-path",
        default=DEFAULT_MANUAL_PROMPT_PATH,
        type=Path,
        help="Path where --print-manual-prompt writes raw prompt text.",
    )
    parser.add_argument(
        "--copy-manual-prompt",
        action="store_true",
        help="Copy the manual smoke prompt to the clipboard.",
    )
    return parser


def _send_prompt_to_claude(
    *,
    prompt: str,
    restart: bool,
    open_delay_seconds: float,
    click_x_ratio: float,
    click_y_ratio: float,
    osascript_timeout_seconds: float,
) -> dict[str, Any]:
    if restart:
        subprocess.run(["osascript", "-e", 'quit app "Claude"'], check=False)
        time.sleep(3)
    try:
        subprocess.run(["open", "-a", "Claude"], check=True)
    except subprocess.CalledProcessError:
        return {"error_code": "open_claude_failed", "frontmost_app": None, "ok": False}
    time.sleep(max(0.0, open_delay_seconds))
    if not _write_clipboard_text(prompt):
        return {
            "error_code": "clipboard_write_failed",
            "frontmost_app": None,
            "ok": False,
        }
    script = """
tell application "Claude" to activate
delay 1
tell application "System Events"
  set frontApp to ""
  repeat 20 times
    set frontApp to name of first application process whose frontmost is true
    if frontApp is "Claude" then exit repeat
    delay 0.25
  end repeat
  if frontApp is not "Claude" then error "frontmost_app=" & frontApp
  key code 53
  delay 0.2
  keystroke "n" using command down
  delay 1
  tell process "Claude"
    set winPosition to position of front window
    set winSize to size of front window
  end tell
  set clickXOffset to ((item 1 of winSize) * clickXRatio) as integer
  set clickYOffset to ((item 2 of winSize) * clickYRatio) as integer
  set clickX to ((item 1 of winPosition) + clickXOffset) as integer
  set clickY to ((item 2 of winPosition) + clickYOffset) as integer
  click at {clickX, clickY}
  delay 0.5
  keystroke "a" using command down
  delay 0.2
  keystroke "v" using command down
  delay 1
  key code 36
end tell
return frontApp
"""
    try:
        completed = subprocess.run(
            [
                "osascript",
                "-e",
                f"set clickXRatio to {click_x_ratio}",
                "-e",
                f"set clickYRatio to {click_y_ratio}",
                "-e",
                script,
            ],
            capture_output=True,
            check=False,
            text=True,
            timeout=max(1.0, osascript_timeout_seconds),
        )
    except subprocess.TimeoutExpired:
        return {
            "error_code": "osascript_timeout",
            "frontmost_app": None,
            "ok": False,
        }
    frontmost_app = (completed.stdout or "").strip() or None
    if completed.returncode != 0:
        return {
            "error_code": "claude_not_frontmost",
            "frontmost_app": _frontmost_app_from_stderr(completed.stderr),
            "ok": False,
        }
    return {"error_code": None, "frontmost_app": frontmost_app, "ok": True}


def _write_clipboard_text(text: str) -> bool:
    script = """
on run argv
  set the clipboard to item 1 of argv
  return length of (the clipboard as text)
end run
"""
    try:
        completed = subprocess.run(
            ["osascript", "-e", script, "--", text],
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        return False
    if completed.returncode != 0:
        return False
    try:
        clipboard_length = int(completed.stdout.strip())
    except ValueError:
        return False
    return clipboard_length == len(text)


def _accessibility_warning_code(*, timeout_seconds: float) -> str | None:
    script = r'''
import ApplicationServices
import CoreGraphics
import Foundation

func attr(_ el: AXUIElement, _ name: String) -> CFTypeRef? {
    var out: CFTypeRef?
    AXUIElementCopyAttributeValue(el, name as CFString, &out)
    return out
}

func collectText(_ el: AXUIElement, _ depth: Int = 0) -> String {
    if depth > 5 { return "" }
    var parts: [String] = []
    for key in [kAXTitleAttribute, kAXDescriptionAttribute, kAXValueAttribute] {
        if let value = attr(el, key) {
            parts.append(String(describing: value))
        }
    }
    if let children = attr(el, kAXChildrenAttribute) as? [AXUIElement] {
        for child in children {
            parts.append(collectText(child, depth + 1))
        }
    }
    return parts.joined(separator: "\n")
}

let windows = CGWindowListCopyWindowInfo(
    CGWindowListOption(arrayLiteral: .optionOnScreenOnly),
    kCGNullWindowID
) as? [[String: Any]] ?? []

for window in windows {
    let owner = window[kCGWindowOwnerName as String] as? String ?? ""
    if owner == "universalAccessAuthWarn" {
        let pid = window[kCGWindowOwnerPID as String] as? pid_t ?? 0
        let text = pid > 0 ? collectText(AXUIElementCreateApplication(pid)) : ""
        if text.contains("Codex.app") {
            print("codex_accessibility_permission_required")
        } else {
            print("accessibility_permission_prompt_present")
        }
        exit(0)
    }
}
'''
    try:
        completed = subprocess.run(
            ["swift", "-"],
            capture_output=True,
            check=False,
            env={
                **os.environ,
                "CLANG_MODULE_CACHE_PATH": "/private/tmp/kcs-swift-module-cache",
            },
            input=script,
            text=True,
            timeout=max(1.0, timeout_seconds),
        )
    except subprocess.TimeoutExpired:
        return None
    if completed.returncode != 0:
        return None
    output = completed.stdout.strip()
    if output in {
        "accessibility_permission_prompt_present",
        "codex_accessibility_permission_required",
    }:
        return output
    return None


def _accessibility_preflight_report(*, timeout_seconds: float) -> dict[str, Any]:
    warning_code = _accessibility_warning_code(timeout_seconds=timeout_seconds)
    return {
        "checks": {
            "codex_accessibility_permission_available": warning_code is None,
        },
        "ok": warning_code is None,
        "schema_version": SCHEMA_VERSION,
        "send_error_code": warning_code,
    }


def _manual_prompt_report(
    *,
    prompt_kind: str,
    prompt_path: Path | None,
    copy_to_clipboard: bool = False,
) -> dict[str, Any]:
    since = datetime.now(UTC)
    prompt_text = _prompt(prompt_kind)
    written_prompt_path = _write_manual_prompt(
        prompt_text=prompt_text,
        prompt_path=prompt_path,
    )
    prompt_copied_to_clipboard = (
        _write_clipboard_text(prompt_text) if copy_to_clipboard else False
    )
    return {
        "follow_up_command": (
            "uv run python scripts/smoke_claude_desktop_ui_prompt.py "
            f"--since {since.isoformat(timespec='seconds').replace('+00:00', 'Z')} "
            f"--assume-sent --prompt-kind {prompt_kind}"
        ),
        "manual_prompt_path": (
            str(written_prompt_path) if written_prompt_path is not None else None
        ),
        "prompt_copied_to_clipboard": prompt_copied_to_clipboard,
        "prompt_kind": prompt_kind,
        "prompt_text": prompt_text,
        "schema_version": SCHEMA_VERSION,
        "since": since.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    }


def _write_manual_prompt(*, prompt_text: str, prompt_path: Path | None) -> Path | None:
    if prompt_path is None:
        return None
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt_text, encoding="utf-8")
    return prompt_path


def _maybe_capture_failure_screenshot(*, enabled: bool, path: Path) -> str | None:
    if not enabled:
        return None
    try:
        completed = subprocess.run(
            ["screencapture", "-x", str(path)],
            capture_output=True,
            check=False,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        return None
    if completed.returncode != 0 or not path.is_file():
        return None
    return str(path)


def _wait_for_report(
    *,
    log_path: Path,
    web_log_path: Path,
    since: datetime,
    timeout_seconds: float,
    poll_interval_seconds: float,
    prompt_kind: str,
    sent: bool,
) -> dict[str, Any]:
    deadline = time.monotonic() + max(0.0, timeout_seconds)
    while True:
        text = _fresh_log_text(log_path=log_path, since=since)
        web_text = _fresh_web_log_text(log_path=web_log_path, since=since)
        report = _report_from_log(
            text=text,
            web_text=web_text,
            prompt_kind=prompt_kind,
            sent=sent,
            since=since,
            log_path=log_path,
            web_log_path=web_log_path,
        )
        if report["ok"] is True or time.monotonic() >= deadline:
            return report
        time.sleep(max(0.25, poll_interval_seconds))


def _report_from_log(
    *,
    text: str,
    prompt_kind: str,
    sent: bool,
    since: datetime,
    log_path: Path,
    web_text: str = "",
    web_log_path: Path = DEFAULT_WEB_LOG_PATH,
) -> dict[str, Any]:
    client_call_text = _client_tool_call_text(text)
    tool_activity_text = _tool_activity_text(text)
    tool_result_summary = _tool_result_summary(text)
    web_diagnostics = _web_diagnostics(web_text)
    manual_fallback_text = f"{text}\n{web_text}"
    timeout_or_disconnect_observed = (
        _TIMEOUT_OR_DISCONNECT_RE.search(tool_activity_text) is not None
    )
    draft_result_observed = _DRAFT_RE.search(text) is not None
    provider_unavailable_result_observed = (
        _PROVIDER_UNAVAILABLE_RE.search(text) is not None
    )
    terminal_result_observed = (
        draft_result_observed or provider_unavailable_result_observed
    )
    post_success_disconnect_observed = _post_success_disconnect_observed(
        text=text,
        prompt_kind=prompt_kind,
        draft_result_observed=draft_result_observed,
    )
    checks = {
        "prompt_sent": sent,
        "claude_completion_error_absent": not web_diagnostics[
            "completion_error_observed"
        ],
        "claude_completion_rate_limit_absent": not web_diagnostics[
            "completion_rate_limit_observed"
        ],
        "tool_call_observed": bool(client_call_text),
        "tool_result_observed": _TOOL_RESULT_RE.search(text) is not None,
        "approved_summary_text_argument_observed": (
            _SUMMARY_ARG_RE.search(client_call_text) is not None
        ),
        "old_structured_arguments_absent": (
            _OLD_ARG_RE.search(client_call_text) is None
        ),
        "manual_fallback_absent": (
            _MANUAL_FALLBACK_RE.search(manual_fallback_text) is None
        ),
        "timeout_or_disconnect_absent": (
            not timeout_or_disconnect_observed or post_success_disconnect_observed
        ),
        "semantic_no_candidates_absent": (
            "semantic_extraction_no_candidates"
            not in tool_result_summary["debug_codes"]
        ),
    }
    if prompt_kind == "split":
        checks["split_result_observed"] = _SPLIT_RE.search(text) is not None
        checks["split_fallback_text_observed"] = (
            _SPLIT_FALLBACK_TEXT_RE.search(text) is not None
        )
        selected_call_text = _selected_tool_call_text(text)
        if selected_call_text:
            checks["selected_call_uses_refs_only"] = (
                _SELECTION_REF_ARG_RE.search(selected_call_text) is not None
                and _SELECTED_ITEM_ARG_RE.search(selected_call_text) is not None
                and _SUMMARY_ARG_RE.search(selected_call_text) is None
                and _OLD_ARG_RE.search(selected_call_text) is None
            )
            checks["selected_draft_result_observed"] = draft_result_observed
    else:
        checks["terminal_result_observed"] = terminal_result_observed
    ok = all(checks.values())
    failure_stage = _failure_stage(
        checks,
        web_diagnostics,
        prompt_kind=prompt_kind,
    )
    return {
        "attention": _attention(
            ok=ok,
            failure_stage=failure_stage,
            post_success_disconnect_observed=post_success_disconnect_observed,
        ),
        "checks": checks,
        "failed_checks": _failed_check_names(checks),
        "failure_stage": failure_stage,
        "latest_log_timestamp": _latest_timestamp(text),
        "latest_web_log_timestamp": _latest_web_timestamp(web_text),
        "log_file": log_path.name,
        "next_steps": _next_steps(
            ok=ok,
            failure_stage=failure_stage,
            post_success_disconnect_observed=post_success_disconnect_observed,
        ),
        "ok": ok,
        "post_success_disconnect_observed": post_success_disconnect_observed,
        "prompt_kind": prompt_kind,
        "draft_result_observed": draft_result_observed,
        "provider_unavailable_result_observed": provider_unavailable_result_observed,
        "schema_version": SCHEMA_VERSION,
        "since": since.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "mcp_result_debug_codes": tool_result_summary["debug_codes"],
        "mcp_result_failure_stages": tool_result_summary["failure_stages"],
        "mcp_result_recommended_actions": tool_result_summary["recommended_actions"],
        "web_diagnostics": web_diagnostics,
        "web_log_file": web_log_path.name,
    }


def _fresh_log_text(*, log_path: Path, since: datetime) -> str:
    try:
        text = _read_log_tail(log_path=log_path, max_bytes=_MAX_LOG_BYTES)
    except OSError:
        return ""
    lines = [
        line
        for line in text.splitlines()
        if (timestamp := _parse_line_timestamp(line)) is not None and timestamp >= since
    ]
    return "\n".join(lines)


def _fresh_web_log_text(*, log_path: Path, since: datetime) -> str:
    try:
        text = _read_log_tail(log_path=log_path, max_bytes=_MAX_LOG_BYTES)
    except OSError:
        return ""
    lines = [
        line
        for line in text.splitlines()
        if (timestamp := _parse_web_line_timestamp(line)) is not None
        and timestamp >= since
    ]
    return "\n".join(lines)


def _web_diagnostics(text: str) -> dict[str, bool]:
    return {
        "completion_error_observed": _WEB_COMPLETION_ERROR_RE.search(text) is not None,
        "completion_rate_limit_observed": (
            _WEB_COMPLETION_RATE_LIMIT_RE.search(text) is not None
        ),
        "kcs_tool_approval_gate_observed": (
            _WEB_KCS_APPROVAL_GATE_RE.search(text) is not None
        ),
        "kcs_tool_approval_released_observed": (
            _WEB_KCS_APPROVAL_RELEASED_RE.search(text) is not None
        ),
    }


def _failure_stage(
    checks: dict[str, bool],
    web_diagnostics: dict[str, bool],
    *,
    prompt_kind: str,
) -> str | None:
    if all(checks.values()):
        return None
    stages = (
        (not checks["prompt_sent"], "prompt_not_sent"),
        (
            web_diagnostics["completion_rate_limit_observed"],
            "claude_completion_rate_limit",
        ),
        (web_diagnostics["completion_error_observed"], "claude_completion_error"),
        (
            web_diagnostics["kcs_tool_approval_gate_observed"]
            and not checks["tool_call_observed"],
            "claude_tool_approval_gate_no_mcp_call",
        ),
        (not checks["tool_call_observed"], "mcp_tool_call_not_observed"),
        (not checks["tool_result_observed"], "mcp_tool_result_not_observed"),
        (
            not checks["semantic_no_candidates_absent"],
            "mcp_semantic_extraction_no_candidates",
        ),
        (
            not checks["manual_fallback_absent"],
            "manual_fallback_observed",
        ),
        (
            prompt_kind == "split" and not checks.get("split_result_observed", True),
            "expected_split_result_not_observed",
        ),
        (
            prompt_kind == "split"
            and not checks.get("split_fallback_text_observed", True),
            "expected_split_fallback_text_not_observed",
        ),
        (
            prompt_kind != "split"
            and not checks.get("terminal_result_observed", True),
            "expected_terminal_result_not_observed",
        ),
    )
    for failed, stage in stages:
        if failed:
            return stage
    return "tool_contract_check_failed"


def _failed_check_names(checks: dict[str, bool]) -> list[str]:
    return [name for name, passed in sorted(checks.items()) if not passed]


def _attention(
    *,
    ok: bool,
    failure_stage: str | None,
    post_success_disconnect_observed: bool,
) -> list[str]:
    if post_success_disconnect_observed:
        return [
            "post_success_disconnect_observed",
            "draft_result_observed_before_disconnect",
        ]
    if ok:
        return []
    if failure_stage is None:
        return ["tool_contract_check_failed"]
    return [failure_stage]


def _next_steps(
    *,
    ok: bool,
    failure_stage: str | None,
    post_success_disconnect_observed: bool,
) -> list[str]:
    if ok and post_success_disconnect_observed:
        return [
            "Treat the KCS draft tool call as passed for this log window.",
            (
                "Ignore the later MCP disconnect toast unless it happens before "
                "the next draft result."
            ),
        ]
    if ok:
        return ["Treat the KCS draft tool call as passed for this log window."]
    failure_steps = {
        "mcp_tool_call_not_observed": (
            "Do not treat the run as passed: kcs_draft_article was not called."
        ),
        "mcp_tool_result_not_observed": (
            "Do not treat the run as passed: no kcs_draft_article result was observed."
        ),
        "mcp_semantic_extraction_no_candidates": (
            "Do not draft manually; fix semantic extraction coverage or input routing."
        ),
        "manual_fallback_observed": (
            "Do not treat the run as passed: Claude produced a manual fallback draft."
        ),
        "expected_split_fallback_text_not_observed": (
            "Do not treat the split run as passed: fallback choice text "
            "was not observed."
        ),
    }
    if failure_stage in failure_steps:
        return [failure_steps[failure_stage]]
    return ["Do not treat the Claude Desktop MCPB prompt run as passed."]


def _tool_result_summary(text: str) -> dict[str, list[str]]:
    result_lines = [
        line
        for line in text.splitlines()
        if "Message from server:" in line and "kcs_mcp_tool_result_v1" in line
    ]
    return {
        "debug_codes": _tool_result_values(result_lines, _TOOL_RESULT_DEBUG_CODE_RE),
        "failure_stages": _tool_result_values(
            result_lines,
            _TOOL_RESULT_FAILURE_STAGE_RE,
        ),
        "recommended_actions": _tool_result_values(
            result_lines,
            _TOOL_RESULT_RECOMMENDED_ACTION_RE,
        ),
    }


def _tool_result_values(lines: list[str], pattern: re.Pattern[str]) -> list[str]:
    values: list[str] = []
    for line in lines:
        for match in pattern.finditer(line):
            value = match.group("value")
            if value not in values:
                values.append(value)
    return values


def _post_success_disconnect_observed(
    *,
    text: str,
    prompt_kind: str,
    draft_result_observed: bool,
) -> bool:
    if not draft_result_observed:
        return False
    lines = text.splitlines()
    result_indexes = [
        index
        for index, line in enumerate(lines)
        if "Message from server:" in line and "kcs_mcp_tool_result_v1" in line
    ]
    if not result_indexes:
        return False
    success_result_index = result_indexes[-1]
    tail = "\n".join(lines[success_result_index + 1 :])
    if _TIMEOUT_OR_DISCONNECT_RE.search(tail) is None:
        return False
    if _CLIENT_TOOL_CALL_LINE_RE.search(tail) is not None:
        return False
    if (
        prompt_kind == "split"
        and _SPLIT_RE.search(lines[success_result_index]) is not None
    ):
        return False
    return True


def _tool_activity_text(text: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if _CLIENT_TOOL_CALL_LINE_RE.search(line):
            return "\n".join(lines[index:])
    return text


def _client_tool_call_text(text: str) -> str:
    return "\n".join(
        line for line in text.splitlines() if _CLIENT_TOOL_CALL_LINE_RE.search(line)
    )


def _selected_tool_call_text(text: str) -> str:
    return "\n".join(
        line
        for line in text.splitlines()
        if _CLIENT_TOOL_CALL_LINE_RE.search(line)
        and _SELECTION_REF_ARG_RE.search(line)
        and _SELECTED_ITEM_ARG_RE.search(line)
    )


def _read_log_tail(*, log_path: Path, max_bytes: int) -> str:
    with log_path.open("rb") as stream:
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(max(0, size - max_bytes))
        return stream.read().decode("utf-8", errors="replace")


def _latest_timestamp(text: str) -> str | None:
    for line in reversed(text.splitlines()):
        timestamp = _parse_line_timestamp(line)
        if timestamp is not None:
            return timestamp.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return None


def _latest_web_timestamp(text: str) -> str | None:
    for line in reversed(text.splitlines()):
        timestamp = _parse_web_line_timestamp(line)
        if timestamp is not None:
            return timestamp.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return None


def _parse_line_timestamp(line: str) -> datetime | None:
    if len(line) < _TIMESTAMP_LEN:
        return None
    try:
        return datetime.fromisoformat(line[:_TIMESTAMP_LEN].replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_web_line_timestamp(line: str) -> datetime | None:
    if len(line) < 19:
        return None
    try:
        timestamp = datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    local_tz = datetime.now().astimezone().tzinfo
    return timestamp.replace(tzinfo=local_tz).astimezone(UTC)


def _parse_since_arg(value: str) -> datetime:
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SystemExit(f"invalid --since timestamp: {value}") from exc
    if timestamp.tzinfo is None:
        raise SystemExit("--since timestamp must include a timezone")
    return timestamp.astimezone(UTC)


def _frontmost_app_from_stderr(stderr: str) -> str | None:
    match = re.search(r"frontmost_app=([^\r\n\"]+)", stderr)
    if match is None:
        return None
    return match.group(1).strip() or None


def _prompt(kind: str) -> str:
    if kind == "split":
        return _split_prompt()
    if kind == "narrative":
        return _narrative_prompt()
    if kind == "raw-ticket":
        return _raw_ticket_prompt()
    return _single_prompt()


def _single_prompt() -> str:
    return (
        "draft me an article from this approved sanitized support ticket:\n\n"
        "Title: Monitoring graphs show no data in Plesk\n"
        "Applicable To: Plesk for Linux\n"
        "Symptoms:\n"
        "- Monitoring graphs show no data.\n"
        "Confirmed facts:\n"
        "- The diagnostic summary references service.log and service.conf.\n"
        "Cause: A required product-side package is missing.\n"
        "Resolution steps:\n"
        "- Run rpm -q product-side-package to confirm the package status.\n"
        "- Run systemctl restart product-service to restart the related service.\n"
        "- Open the monitoring module page in the Plesk UI and confirm graphs load.\n"
    )


def _narrative_prompt() -> str:
    return (
        "draft me an article from this approved sanitized support ticket:\n\n"
        "Summary: Monitoring graphs show no data in Plesk.\n\n"
        "Investigation:\n"
        "1. Logs showed plugin-loading errors, but the datasource endpoint "
        "still returned metric names.\n"
        "2. A working reference server did not have the same ownership issue "
        "under /usr/local/psa/var/modules/monitoring/.\n"
        "3. Root cause was found in "
        "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf, an unowned "
        "configuration file. Its DataDir setting pointed collectd to write RRD "
        "metric files to a non-standard path that the Monitoring backend does "
        "not query.\n\n"
        "Resolution: The unowned collectd config file was backed up and "
        "removed from /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf, and "
        "the sw-collectd service was restarted. New metric data began writing "
        "to the expected location and Monitoring graphs started displaying "
        "data again. Older data may not appear, and graphs repopulate "
        "gradually as new metrics are collected.\n"
    )


def _raw_ticket_prompt() -> str:
    return (
        "draft me an article from this approved sanitized support ticket:\n\n"
        "# Customer Ticket Content\n\n"
        "When loading the monitoring module in Plesk, none of the graphs show "
        "any data. Uninstalling and reinstalling the Monitoring extension did "
        "not resolve the issue.\n\n"
        "The datasource endpoint returned metric names, but no datapoints were "
        "returned for the graphs. A working reference server was compared with "
        "the affected server. Root cause was found in "
        "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf. This unowned "
        "collectd configuration file set DataDir to a non-standard path under "
        "/usr/local/psa/var/modules/monitoring/rrd that the Monitoring backend "
        "does not query.\n\n"
        "The config file was backed up and removed from "
        "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf, and the "
        "sw-collectd service was restarted. The Monitoring graphs started "
        "displaying data again. Older data may not appear; graphs repopulate "
        "gradually as new metrics are collected.\n"
    )


def _split_prompt() -> str:
    return (
        "draft me an article from this approved sanitized support ticket:\n\n"
        "Item 1: Monitoring graphs show no data in Plesk\n"
        "Applicable To: Plesk for Linux\n"
        "Symptoms:\n"
        "- Monitoring graphs show no data.\n"
        "Confirmed facts:\n"
        "- The diagnostic summary references service.log and service.conf.\n"
        "Cause: A required product-side package is missing.\n"
        "Resolution steps:\n"
        "- Run rpm -q product-side-package to confirm the package status.\n"
        "- Run systemctl restart product-service to restart the related service.\n"
        "\n"
        "Item 2: Monitoring extension post-install fails\n"
        "Applicable To: Plesk for Linux\n"
        "Symptoms:\n"
        "- Monitoring extension post-install fails.\n"
        "Confirmed facts:\n"
        "- The module directory ownership is incorrect.\n"
        "Cause: The module directory is owned by root instead of psaadm.\n"
        "Resolution steps:\n"
        "- Run ls -ld /usr/local/psa/var/modules/monitoring/.\n"
        "- Reinstall the monitoring extension from Plesk Extensions.\n"
    )


def _write_json(stream: Any, payload: dict[str, Any]) -> None:
    stream.write(json.dumps(payload, allow_nan=False, sort_keys=True))
    stream.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
