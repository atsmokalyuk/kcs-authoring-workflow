"""Run a deterministic stdio smoke against the KCS Authoring MCPB wrapper."""

from __future__ import annotations

import argparse
import json
import os
import selectors
import shutil
import subprocess
import sys
import time
from hashlib import sha256
from pathlib import Path
from typing import Any, NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_NAME = "kcs-authoring-mvp-validator-control"
DEFAULT_SOURCE_WRAPPER = (
    REPO_ROOT / "packaging" / "claude-desktop" / BUNDLE_NAME / "server" / "index.js"
)
DEFAULT_INSTALLED_WRAPPER = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Claude"
    / "Claude Extensions"
    / "local.mcpb.kcs-authoring-mvp.kcs-authoring-mvp-validator-control"
    / "server"
    / "index.js"
)
DEFAULT_MCPB_PACKAGE = REPO_ROOT / "dist" / f"{BUNDLE_NAME}.mcpb"
DEFAULT_CODEX_NODE = (
    Path.home()
    / ".cache"
    / "codex-runtimes"
    / "codex-primary-runtime"
    / "dependencies"
    / "node"
    / "bin"
    / "node"
)
PROTOCOL_VERSION = "2025-11-25"
TOOL_NAME = "kcs_draft_article"
TICKET_REF_TOOL_NAME = "kcs_draft_ticket"
REGISTER_TOOL_NAME = "kcs_register_clean_ticket"
PREPARE_SEMANTIC_REVIEW_TOOL_NAME = "kcs_prepare_semantic_review"
SUBMIT_SEMANTIC_REVIEW_TOOL_NAME = "kcs_submit_semantic_review"
CONFIRM_REUSE_COMPARISON_TOOL_NAME = "kcs_confirm_reuse_comparison"
BEHAVIOR_TOOL_NAME = "support_get_behavior_instructions"
CALL_REQUEST_IDS = (3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
APPROVED_TICKET_STORE_ROOT_ENV = "KCS_AUTHORING_MVP_APPROVED_TICKET_STORE_ROOT"
_BUNDLE_FILE_ROOTS = (REPO_ROOT,)


class SmokeError(RuntimeError):
    """Value-safe smoke failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class _ExpectedToolSurface(NamedTuple):
    name: str
    properties: frozenset[str]
    required: tuple[str, ...] | None
    destructive: bool
    idempotent: bool
    open_world: bool
    read_only: bool
    description_includes: tuple[str, ...] = ()
    description_excludes: tuple[str, ...] = ()
    debug_description_includes: tuple[str, ...] = ()


class _ExpectedManifestToolDescription(NamedTuple):
    name: str
    includes: tuple[str, ...] = ()
    excludes: tuple[str, ...] = ()


_EXPECTED_TOOL_SURFACES: tuple[_ExpectedToolSurface, ...] = (
    _ExpectedToolSurface(
        name=REGISTER_TOOL_NAME,
        properties=frozenset({"clean_ticket_text", "debug", "ticket_ref"}),
        required=("clean_ticket_text",),
        destructive=False,
        idempotent=False,
        open_world=False,
        read_only=False,
    ),
    _ExpectedToolSurface(
        name=TICKET_REF_TOOL_NAME,
        properties=frozenset({"debug", "ticket_ref"}),
        required=("ticket_ref",),
        destructive=False,
        idempotent=False,
        open_world=False,
        read_only=False,
        description_includes=(
            "/draft <ticket_ref>",
            "only ticket_ref",
            "Do not ask for an attachment",
        ),
    ),
    _ExpectedToolSurface(
        name=TOOL_NAME,
        properties=frozenset(
            {
                "approved_summary_text",
                "debug",
                "operator_confirmed_resolution_steps",
                "operator_selected_item_ref",
                "operator_selected_item_refs",
                "operator_selection_ref",
            }
        ),
        required=None,
        destructive=False,
        idempotent=False,
        open_world=False,
        read_only=False,
        description_includes=(
            "operator-selected candidate batch",
            "Operator-confirmed resolution steps",
            "/draft <ticket_ref>",
            "use kcs_draft_ticket",
        ),
        description_excludes=("raw comments", "internal notes"),
        debug_description_includes=("reviewer-only Zendesk HTML",),
    ),
    _ExpectedToolSurface(
        name=CONFIRM_REUSE_COMPARISON_TOOL_NAME,
        properties=frozenset({"candidate_ref", "comparison_ref", "outcome"}),
        required=("comparison_ref", "outcome"),
        destructive=False,
        idempotent=False,
        open_world=False,
        read_only=False,
        description_includes=(
            "operator-confirmed outcome",
            "Copy comparison_ref exactly",
            "Do not include ticket facts",
        ),
    ),
    _ExpectedToolSurface(
        name=PREPARE_SEMANTIC_REVIEW_TOOL_NAME,
        properties=frozenset({"semantic_review_ref"}),
        required=("semantic_review_ref",),
        destructive=False,
        idempotent=True,
        open_world=False,
        read_only=True,
        description_includes=("semantic_review_required", "bounded excerpts"),
    ),
    _ExpectedToolSurface(
        name=SUBMIT_SEMANTIC_REVIEW_TOOL_NAME,
        properties=frozenset(
            {
                "semantic_issue_proposal",
                "semantic_review_ref",
            }
        ),
        required=("semantic_issue_proposal", "semantic_review_ref"),
        destructive=False,
        idempotent=False,
        open_world=False,
        read_only=False,
        description_includes=("semantic_issue_proposal_v1", "No article draft"),
    ),
    _ExpectedToolSurface(
        name=BEHAVIOR_TOOL_NAME,
        properties=frozenset(),
        required=(),
        destructive=False,
        idempotent=True,
        open_world=False,
        read_only=True,
        description_includes=("Legacy compatibility helper", "continue /draft"),
    ),
)

_EXPECTED_REGISTRY_MANIFEST_TOOL_DESCRIPTIONS: tuple[
    _ExpectedManifestToolDescription,
    ...,
] = (
    _ExpectedManifestToolDescription(
        name=REGISTER_TOOL_NAME,
        includes=("clean_ticket_text", "next_arguments"),
    ),
    _ExpectedManifestToolDescription(
        name=TICKET_REF_TOOL_NAME,
        includes=(
            "/draft <ticket_ref>",
            "only ticket_ref",
            "Do not ask for an attachment",
        ),
    ),
    _ExpectedManifestToolDescription(
        name=TOOL_NAME,
        includes=(
            "short approved_summary_text",
            "/draft <ticket_ref>",
            "use kcs_draft_ticket",
        ),
        excludes=(
            "structured item",
            "raw comments",
            "internal notes",
            "show the returned candidates in a native Claude Desktop choice popup",
        ),
    ),
    _ExpectedManifestToolDescription(
        name=CONFIRM_REUSE_COMPARISON_TOOL_NAME,
        includes=(
            "operator-confirmed outcome",
            "comparison_ref exactly",
            "Do not include ticket facts",
        ),
    ),
    _ExpectedManifestToolDescription(
        name=PREPARE_SEMANTIC_REVIEW_TOOL_NAME,
        includes=("semantic_review_required", "bounded excerpts"),
    ),
    _ExpectedManifestToolDescription(
        name=SUBMIT_SEMANTIC_REVIEW_TOOL_NAME,
        includes=("semantic_issue_proposal_v1", "No article draft"),
    ),
    _ExpectedManifestToolDescription(
        name=BEHAVIOR_TOOL_NAME,
        includes=("Legacy compatibility helper", "continue /draft"),
    ),
)

_EXPECTED_REGISTRY_LONG_DESCRIPTION_INCLUDES = (
    "Use only the listed KCS Authoring tools",
    "legacy instruction requires",
    "support_get_behavior_instructions",
    "Plesk Support Assistant Local",
    "Do not report Plesk Support Assistant Local as missing",
)
_EXPECTED_REGISTRY_LONG_DESCRIPTION_EXCLUDES = ("one primary read-only tool",)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = run_smoke(
            node_command=args.node_command,
            wrapper=args.wrapper,
            uv_command=args.uv_command,
        )
    except SmokeError as exc:
        report = {
            "checks": {exc.code: False},
            "error_code": exc.code,
            "ok": False,
            "schema_version": "kcs_mcpb_stdio_smoke_v1",
        }
    _write_json(sys.stdout, report)
    return 0 if report["ok"] is True else 2


def run_smoke(
    *,
    node_command: str | None,
    wrapper: Path,
    uv_command: str,
) -> dict[str, Any]:
    """Run initialize, tools/list, split, and selected draft calls."""

    global _BUNDLE_FILE_ROOTS
    node = _node_command(node_command)
    if not wrapper.is_file():
        raise SmokeError("wrapper_not_found")
    previous_bundle_roots = _BUNDLE_FILE_ROOTS
    _BUNDLE_FILE_ROOTS = _runtime_bundle_file_roots(wrapper)
    try:
        responses = _run_jsonrpc_session(
            node=node,
            wrapper=wrapper,
            uv_command=uv_command,
            messages=_smoke_messages(),
        )
        by_id = _responses_by_id(responses)
        initialize = by_id[1]
        tools = by_id[2]
        no_candidates = by_id[3]
        selection_invalid = by_id[4]
        mixed_invalid = by_id[5]
        labeled_draft = by_id[6]
        selection_ref_only_invalid = by_id[7]
        selected_item_only_invalid = by_id[8]
        narrative_draft = by_id[9]
        raw_ticket_draft = by_id[10]
        live_raw_ticket_draft = by_id[11]
        non_debug_labeled_draft = by_id[12]
        checks = {
            "initialize_ok": _initialize_ok(initialize),
            "registry_cache_ok": _registry_cache_ok(wrapper),
            "tool_surface_ok": _tool_surface_ok(tools),
            "no_candidates_ok": _no_candidates_ok(no_candidates),
            "selection_invalid_ok": _selection_invalid_ok(selection_invalid),
            "mixed_call_shape_invalid_ok": _mixed_call_shape_invalid_ok(mixed_invalid),
            "labeled_draft_ok": _labeled_draft_ok(labeled_draft),
            "narrative_draft_ok": _labeled_draft_ok(narrative_draft),
            "raw_ticket_draft_ok": _labeled_draft_ok(raw_ticket_draft),
            "live_raw_ticket_draft_ok": _labeled_draft_ok(live_raw_ticket_draft),
            "non_debug_labeled_draft_text_ok": _non_debug_labeled_draft_text_ok(
                non_debug_labeled_draft
            ),
            "selection_ref_only_invalid_ok": _mixed_call_shape_invalid_ok(
                selection_ref_only_invalid
            ),
            "selected_item_only_invalid_ok": _mixed_call_shape_invalid_ok(
                selected_item_only_invalid
            ),
        }
        split_choice = _run_split_choice_smoke(
            node=node,
            wrapper=wrapper,
            uv_command=uv_command,
        )
        registered_ticket = _run_register_then_draft_smoke(
            node=node,
            wrapper=wrapper,
            uv_command=uv_command,
        )
        checks["split_choice_ok"] = _split_choice_ok(split_choice)
        checks["register_then_draft_ok"] = _register_then_draft_ok(registered_ticket)
        semantic_review = _run_semantic_review_submit_smoke(
            node=node,
            wrapper=wrapper,
            uv_command=uv_command,
        )
        semantic_review_invalid = _run_semantic_review_invalid_submit_smoke(
            node=node,
            wrapper=wrapper,
            uv_command=uv_command,
        )
        checks["semantic_review_submit_ok"] = _semantic_review_submit_ok(
            semantic_review
        )
        checks["semantic_review_invalid_submit_ok"] = (
            _semantic_review_invalid_submit_ok(semantic_review_invalid)
        )
        return {
            "checks": checks,
            "ok": all(checks.values()),
            "schema_version": "kcs_mcpb_stdio_smoke_v1",
            "debug_codes": [
                _structured(response).get("debug_code", "")
                for response in (
                    no_candidates,
                    selection_invalid,
                    mixed_invalid,
                    labeled_draft,
                    selection_ref_only_invalid,
                    selected_item_only_invalid,
                    narrative_draft,
                    raw_ticket_draft,
                    live_raw_ticket_draft,
                    non_debug_labeled_draft,
                )
            ],
            "split_choice_debug_codes": [
                _structured(split_choice["split"]).get("debug_code", ""),
                _structured(split_choice["batch"]).get("debug_code", ""),
            ],
            "registered_ticket_debug_code": _structured(registered_ticket["draft"]).get(
                "debug_code", ""
            ),
            "semantic_review_debug_codes": [
                _structured(semantic_review["draft"]).get("debug_code", ""),
                _structured(semantic_review["submit"]).get("debug_code", ""),
                _structured(semantic_review_invalid["submit"]).get(
                    "debug_code",
                    "",
                ),
            ],
            "registry_cache_checked": _registry_cache_path(wrapper) is not None,
            "tool_count": len(tools.get("result", {}).get("tools", [])),
            "wrapper_kind": (
                "installed" if wrapper == DEFAULT_INSTALLED_WRAPPER else "custom"
            ),
        }
    finally:
        _BUNDLE_FILE_ROOTS = previous_bundle_roots


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wrapper",
        default=str(
            DEFAULT_INSTALLED_WRAPPER
            if DEFAULT_INSTALLED_WRAPPER.is_file()
            else DEFAULT_SOURCE_WRAPPER
        ),
        type=Path,
        help="Path to MCPB server/index.js wrapper.",
    )
    parser.add_argument(
        "--node-command",
        default=None,
        help="Node executable. Defaults to PATH node, then bundled Codex node.",
    )
    parser.add_argument(
        "--uv-command",
        default="uv",
        help="uv executable name/path passed to the wrapper.",
    )
    return parser


def _node_command(value: str | None) -> str:
    if value:
        return value
    node = shutil.which("node")
    if node is not None:
        return node
    if DEFAULT_CODEX_NODE.is_file():
        return str(DEFAULT_CODEX_NODE)
    raise SmokeError("node_not_found")


def _run_jsonrpc_session(
    *,
    node: str,
    wrapper: Path,
    uv_command: str,
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    payload = "".join(
        json.dumps(message, separators=(",", ":")) + "\n" for message in messages
    )
    try:
        completed = subprocess.run(
            [node, str(wrapper)],
            input=payload,
            capture_output=True,
            check=False,
            env=_wrapper_env(
                uv_command=uv_command,
                semantic_provider="fixture",
            ),
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired as exc:
        raise SmokeError("wrapper_timeout") from exc
    if completed.returncode != 0:
        raise SmokeError("wrapper_failed")
    responses = []
    for line in completed.stdout.splitlines():
        if line.strip():
            responses.append(json.loads(line))
    return responses


def _run_split_choice_smoke(
    *,
    node: str,
    wrapper: Path,
    uv_command: str,
) -> dict[str, dict[str, Any]]:
    try:
        process = subprocess.Popen(
            [node, str(wrapper)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_wrapper_env(
                uv_command=uv_command,
                semantic_provider="fixture",
            ),
            text=True,
        )
    except OSError as exc:
        raise SmokeError("wrapper_failed") from exc
    try:
        initialize = _send_jsonrpc(
            process, _request(7, "initialize", {"protocolVersion": PROTOCOL_VERSION})
        )
        _write_process_message(
            process,
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
        split = _send_jsonrpc(
            process,
            _request(
                8,
                "tools/call",
                {"name": TOOL_NAME, "arguments": _multi_item_summary_args()},
            ),
        )
        batch_arguments = _native_batch_submit_arguments(split)
        batch = _send_jsonrpc(
            process,
            _request(
                9,
                "tools/call",
                {"name": TOOL_NAME, "arguments": batch_arguments},
            ),
        )
        return {
            "batch": batch,
            "initialize": initialize,
            "split": split,
        }
    finally:
        _close_process(process)


def _run_register_then_draft_smoke(
    *,
    node: str,
    wrapper: Path,
    uv_command: str,
) -> dict[str, dict[str, Any]]:
    try:
        process = subprocess.Popen(
            [node, str(wrapper)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_wrapper_env(
                uv_command=uv_command,
                semantic_provider="fixture",
            ),
            text=True,
        )
    except OSError as exc:
        raise SmokeError("wrapper_failed") from exc
    try:
        initialize = _send_jsonrpc(
            process,
            _request(10, "initialize", {"protocolVersion": PROTOCOL_VERSION}),
        )
        _write_process_message(
            process,
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
        register_started_at = time.time()
        ticket_ref = f"smoke-monitoring-{int(register_started_at * 1000)}"
        register = _send_jsonrpc(
            process,
            _request(
                11,
                "tools/call",
                {
                    "name": REGISTER_TOOL_NAME,
                    "arguments": {
                        "clean_ticket_text": _raw_ticket_summary_text(),
                        "ticket_ref": ticket_ref,
                    },
                },
            ),
        )
        registered = _structured(register)
        next_arguments = registered.get("next_arguments")
        if not isinstance(next_arguments, dict):
            raise SmokeError("register_then_draft_missing_next_arguments")
        draft = _send_jsonrpc(
            process,
            _request(
                12,
                "tools/call",
                {"name": TOOL_NAME, "arguments": dict(next_arguments)},
            ),
        )
        draft_structured = _structured(draft)
        comparison_ref = draft_structured.get("comparison_ref")
        if not isinstance(comparison_ref, str):
            raise SmokeError("register_then_draft_missing_comparison_ref")
        confirmed = _send_jsonrpc(
            process,
            _request(
                13,
                "tools/call",
                {
                    "name": CONFIRM_REUSE_COMPARISON_TOOL_NAME,
                    "arguments": {
                        "comparison_ref": comparison_ref,
                        "outcome": "none_fit",
                    },
                },
            ),
        )
        return {
            "_register_started_at": {"value": register_started_at},
            "confirmed": confirmed,
            "draft": draft,
            "initialize": initialize,
            "register": register,
        }
    finally:
        _close_process(process)


def _run_semantic_review_submit_smoke(
    *,
    node: str,
    wrapper: Path,
    uv_command: str,
) -> dict[str, dict[str, Any]]:
    return _run_semantic_review_smoke(
        node=node,
        wrapper=wrapper,
        uv_command=uv_command,
        invalid_submit=False,
        identity_overlap=True,
    )


def _run_semantic_review_invalid_submit_smoke(
    *,
    node: str,
    wrapper: Path,
    uv_command: str,
) -> dict[str, dict[str, Any]]:
    return _run_semantic_review_smoke(
        node=node,
        wrapper=wrapper,
        uv_command=uv_command,
        invalid_submit=True,
        identity_overlap=False,
    )


def _run_semantic_review_smoke(
    *,
    node: str,
    wrapper: Path,
    uv_command: str,
    invalid_submit: bool,
    identity_overlap: bool,
) -> dict[str, dict[str, Any]]:
    ticket_ref = f"smoke-semantic-review-{int(time.time() * 1000)}"
    try:
        process = subprocess.Popen(
            [node, str(wrapper)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_wrapper_env(
                uv_command=uv_command,
                semantic_provider=None,
            ),
            text=True,
        )
    except OSError as exc:
        raise SmokeError("wrapper_failed") from exc
    try:
        initialize = _send_jsonrpc(
            process,
            _request(13, "initialize", {"protocolVersion": PROTOCOL_VERSION}),
        )
        _write_process_message(
            process,
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
        register = _send_jsonrpc(
            process,
            _request(
                14,
                "tools/call",
                {
                    "name": REGISTER_TOOL_NAME,
                    "arguments": {
                        "clean_ticket_text": _semantic_review_ticket_text(),
                        "ticket_ref": ticket_ref,
                    },
                },
            ),
        )
        draft = _send_jsonrpc(
            process,
            _request(
                15,
                "tools/call",
                {
                    "name": TOOL_NAME,
                    "arguments": {"ticket_ref": ticket_ref},
                },
            ),
        )
        semantic_review_ref = _structured(draft).get("semantic_review_ref")
        if not isinstance(semantic_review_ref, str):
            raise SmokeError("semantic_review_ref_missing")
        prepare = _send_jsonrpc(
            process,
            _request(
                16,
                "tools/call",
                {
                    "name": PREPARE_SEMANTIC_REVIEW_TOOL_NAME,
                    "arguments": {"semantic_review_ref": semantic_review_ref},
                },
            ),
        )
        packet = _structured(prepare)
        proposal = _semantic_issue_proposal(
            packet,
            invalid_submit=invalid_submit,
            identity_overlap=identity_overlap,
        )
        initial_submit = _send_jsonrpc(
            process,
            _request(
                17,
                "tools/call",
                {
                    "name": SUBMIT_SEMANTIC_REVIEW_TOOL_NAME,
                    "arguments": {
                        "semantic_issue_proposal": proposal,
                        "semantic_review_ref": semantic_review_ref,
                    },
                },
            ),
        )
        submit = initial_submit
        responses = {
            "draft": draft,
            "initialize": initialize,
            "prepare": prepare,
            "register": register,
            "submit": submit,
        }
        if not invalid_submit:
            batch = _send_jsonrpc(
                process,
                _request(
                    19,
                    "tools/call",
                    {
                        "name": TOOL_NAME,
                        "arguments": _native_batch_submit_arguments(submit),
                    },
                ),
            )
            responses["batch"] = batch
        return responses
    finally:
        _close_process(process)


def _wrapper_env(
    *,
    uv_command: str,
    semantic_provider: str | None,
) -> dict[str, str]:
    env = {
        **os.environ,
        "KCS_AUTHORING_MVP_UV_COMMAND": uv_command,
    }
    if semantic_provider is None:
        env.pop("KCS_AUTHORING_SEMANTIC_PROVIDER", None)
    else:
        env["KCS_AUTHORING_SEMANTIC_PROVIDER"] = semantic_provider
    env.pop("KCS_AUTHORING_MVP_REPO_ROOT", None)
    return env


def _send_jsonrpc(
    process: subprocess.Popen[str],
    message: dict[str, Any],
) -> dict[str, Any]:
    _write_process_message(process, message)
    return _read_process_response(process)


def _write_process_message(
    process: subprocess.Popen[str],
    message: dict[str, Any],
) -> None:
    if process.stdin is None:
        raise SmokeError("wrapper_failed")
    try:
        process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        process.stdin.flush()
    except OSError as exc:
        raise SmokeError("wrapper_failed") from exc


def _read_process_response(process: subprocess.Popen[str]) -> dict[str, Any]:
    if process.stdout is None:
        raise SmokeError("wrapper_failed")
    selector = selectors.DefaultSelector()
    try:
        selector.register(process.stdout, selectors.EVENT_READ)
        events = selector.select(timeout=15)
        if not events:
            raise SmokeError("wrapper_timeout")
        line = process.stdout.readline()
    finally:
        selector.close()
    if not line:
        raise SmokeError("missing_jsonrpc_response")
    try:
        return json.loads(line)
    except json.JSONDecodeError as exc:
        raise SmokeError("wrapper_failed") from exc


def _close_process(process: subprocess.Popen[str]) -> None:
    if process.stdin is not None:
        try:
            process.stdin.close()
        except OSError:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _responses_by_id(responses: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    by_id = {response.get("id"): response for response in responses}
    expected_ids = {1, 2, *CALL_REQUEST_IDS}
    if not expected_ids.issubset(by_id):
        raise SmokeError("missing_jsonrpc_response")
    return by_id


def _smoke_messages() -> list[dict[str, Any]]:
    return [
        _request(1, "initialize", {"protocolVersion": PROTOCOL_VERSION}),
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        _request(2, "tools/list", {}),
        _request(
            3,
            "tools/call",
            {"name": TOOL_NAME, "arguments": _primary_summary_args()},
        ),
        _request(
            4,
            "tools/call",
            {"name": TOOL_NAME, "arguments": _selection_args()},
        ),
        _request(
            5,
            "tools/call",
            {"name": TOOL_NAME, "arguments": _mixed_call_shape_args()},
        ),
        _request(
            6,
            "tools/call",
            {"name": TOOL_NAME, "arguments": _labeled_summary_args()},
        ),
        _request(
            7,
            "tools/call",
            {"name": TOOL_NAME, "arguments": _selection_ref_only_args()},
        ),
        _request(
            8,
            "tools/call",
            {"name": TOOL_NAME, "arguments": _selected_item_only_args()},
        ),
        _request(
            9,
            "tools/call",
            {"name": TOOL_NAME, "arguments": _narrative_summary_args()},
        ),
        _request(
            10,
            "tools/call",
            {"name": TOOL_NAME, "arguments": _raw_ticket_summary_args()},
        ),
        _request(
            11,
            "tools/call",
            {"name": TOOL_NAME, "arguments": _live_raw_ticket_summary_args()},
        ),
        _request(
            12,
            "tools/call",
            {"name": TOOL_NAME, "arguments": _non_debug_labeled_summary_args()},
        ),
    ]


def _request(request_id: int, method: str, params: dict[str, Any]) -> dict[str, Any]:
    return {"id": request_id, "jsonrpc": "2.0", "method": method, "params": params}


def _primary_summary_args() -> dict[str, Any]:
    return {
        "approved_summary_text": _unstructured_summary_text(),
        "debug": True,
    }


def _labeled_summary_args() -> dict[str, Any]:
    return {
        "approved_summary_text": _labeled_summary_text(),
        "debug": True,
    }


def _non_debug_labeled_summary_args() -> dict[str, Any]:
    return {"approved_summary_text": _labeled_summary_text()}


def _narrative_summary_args() -> dict[str, Any]:
    return {
        "approved_summary_text": _narrative_summary_text(),
        "debug": True,
    }


def _raw_ticket_summary_args() -> dict[str, Any]:
    return {
        "approved_summary_text": _raw_ticket_summary_text(),
        "debug": True,
    }


def _live_raw_ticket_summary_args() -> dict[str, Any]:
    return {
        "approved_summary_text": _live_raw_ticket_summary_text(),
        "debug": True,
    }


def _multi_item_summary_args() -> dict[str, Any]:
    return {"approved_summary_text": _multi_item_labeled_summary_text()}


def _selection_args() -> dict[str, Any]:
    return {
        "debug": True,
        "operator_selected_item_ref": "candidate-001",
        "operator_selection_ref": "selection-opaque",
    }


def _selection_ref_only_args() -> dict[str, Any]:
    return {
        "debug": True,
        "operator_selection_ref": "selection-opaque",
    }


def _selected_item_only_args() -> dict[str, Any]:
    return {
        "debug": True,
        "operator_selected_item_ref": "candidate-001",
    }


def _mixed_call_shape_args() -> dict[str, Any]:
    return {
        **_primary_summary_args(),
        **_selection_args(),
    }


def _unstructured_summary_text() -> str:
    return "Approved sanitized summary: Monitoring graphs show no data."


def _labeled_summary_text() -> str:
    return (
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


def _narrative_summary_text() -> str:
    return (
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


def _raw_ticket_summary_text() -> str:
    return (
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


def _live_raw_ticket_summary_text() -> str:
    return (
        "# Customer Ticket Content\n\n"
        "When loading the monitoring module in Plesk, none of the graphs show "
        "any data. We have un-installed and re-installed the extension, and it "
        "still displays no data.\n\n"
        "The datasource endpoint returns metric names, but no datapoints are "
        "returned for the graphs. The affected server has "
        "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf with a DataDir "
        "value pointing under /usr/local/psa/var/modules/monitoring/rrd. That "
        "location is not queried by the Monitoring backend.\n\n"
        "After correcting the collectd configuration, the Monitoring graphs "
        "started displaying data again. The graphs repopulate gradually with "
        "newly collected metrics; older data from before the correction may "
        "not be visible.\n"
    )


def _multi_item_labeled_summary_text() -> str:
    return (
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


def _semantic_review_ticket_text() -> str:
    return (
        "Customer Ticket Content\n"
        "Customer reports that a product task fails with an error.\n"
        "Support confirmed that a required Plesk service was unavailable.\n"
        "Support connected through SSH and ran systemctl restart sw-cp-server.\n"
        "Support opened Plesk and confirmed that the task completed.\n"
        "The investigation later discussed another possible issue."
    )


def _semantic_issue_proposal(
    packet: dict[str, Any],
    *,
    invalid_submit: bool,
    identity_overlap: bool,
) -> dict[str, object]:
    allowed_refs = packet.get("allowed_source_refs")
    if not isinstance(allowed_refs, list) or not allowed_refs:
        raise SmokeError("semantic_review_packet_invalid")
    source_refs = [str(ref) for ref in allowed_refs]
    proposal_refs = (
        source_refs[:-1]
        if identity_overlap and not invalid_submit and len(source_refs) > 1
        else source_refs
    )
    excerpt_text_by_ref = _semantic_excerpt_text_by_ref(packet)
    if invalid_submit:
        issues = [
            _invalid_semantic_smoke_issue(
                issue_ref="issue-001",
                proposal_refs=proposal_refs,
                source_refs=source_refs,
            )
        ]
    else:
        if len(source_refs) < 2:
            raise SmokeError("semantic_review_packet_invalid")
        issues = [
            _extractive_semantic_smoke_issue(
                excerpt_text_by_ref=excerpt_text_by_ref,
                proposal_refs=proposal_refs,
                issue_ref="issue-001",
                summary="Plesk task fails with an error",
            ),
            _extractive_semantic_smoke_issue(
                excerpt_text_by_ref=excerpt_text_by_ref,
                proposal_refs=proposal_refs,
                issue_ref="issue-002",
                summary="Second Plesk task fails after service interruption",
            ),
        ]

    coverage_records: list[dict[str, object]] = []
    if proposal_refs != source_refs:
        coverage_records.append(
            {
                "coverage_ref": "coverage-smoke-unassigned-001",
                "duplicate_of_source_ref": None,
                "reason_code": "ticket_metadata",
                "source_refs": source_refs[len(proposal_refs) :],
            }
        )

    return {
        "case_ref": packet.get("case_ref"),
        "coverage_records": coverage_records,
        "extraction_source_ref": "semantic-proposal-smoke-submit-001",
        "issues": issues,
        "schema_version": "semantic_issue_proposal_v1",
        "source_refs": source_refs,
    }


def _semantic_excerpt_text_by_ref(packet: dict[str, Any]) -> dict[str, str]:
    selected_excerpts = packet.get("selected_excerpts")
    if not isinstance(selected_excerpts, list):
        raise SmokeError("semantic_review_packet_invalid")
    index: dict[str, str] = {}
    for excerpt in selected_excerpts:
        if not isinstance(excerpt, dict):
            raise SmokeError("semantic_review_packet_invalid")
        source_ref = excerpt.get("source_ref")
        text = excerpt.get("text")
        if not isinstance(source_ref, str) or not isinstance(text, str):
            raise SmokeError("semantic_review_packet_invalid")
        index[source_ref] = text
    return index


def _extractive_semantic_smoke_issue(
    *,
    excerpt_text_by_ref: dict[str, str],
    proposal_refs: list[str],
    issue_ref: str,
    summary: str,
) -> dict[str, object]:
    symptom_ref = _semantic_ref_containing(
        excerpt_text_by_ref,
        proposal_refs,
        "product task fails",
    )
    cause_ref = _semantic_ref_containing(
        excerpt_text_by_ref,
        proposal_refs,
        "required Plesk service",
    )
    resolution_ref = _semantic_ref_containing(
        excerpt_text_by_ref,
        proposal_refs,
        "systemctl restart",
    )
    verification_ref = _semantic_ref_containing(
        excerpt_text_by_ref,
        proposal_refs,
        "task completed",
    )
    symptom = _semantic_smoke_observation(
        excerpt_text_by_ref[symptom_ref],
        [symptom_ref],
    )
    return {
        "answer_evidence": [],
        "cause_evidence": [
            _semantic_smoke_observation(
                excerpt_text_by_ref[cause_ref],
                [cause_ref],
            )
        ],
        "context_evidence": [],
        "error_evidence": [symptom],
        "issue_ref": issue_ref,
        "question": None,
        "resolution_evidence": [
            _semantic_smoke_observation(
                excerpt_text_by_ref[resolution_ref],
                [resolution_ref],
            )
        ],
        "summary": _semantic_smoke_observation(summary, proposal_refs),
        "symptoms": [symptom],
        "verification_evidence": [
            _semantic_smoke_observation(
                excerpt_text_by_ref[verification_ref],
                [verification_ref],
            )
        ],
    }


def _invalid_semantic_smoke_issue(
    *,
    issue_ref: str,
    proposal_refs: list[str],
    source_refs: list[str],
) -> dict[str, object]:
    return {
        "answer_evidence": [],
        "cause_evidence": [
            _semantic_smoke_observation(
                "A required Plesk service was unavailable.",
                source_refs,
            )
        ],
        "context_evidence": [],
        "error_evidence": [
            _semantic_smoke_observation(
                "A product task fails with an error.",
                proposal_refs,
            )
        ],
        "issue_ref": issue_ref,
        "question": None,
        "resolution_evidence": [
            _semantic_smoke_observation(
                "Connect to the Plesk server through SSH.",
                source_refs,
            ),
            _semantic_smoke_observation("<h1>Article draft</h1>", source_refs),
            _semantic_smoke_observation(
                "Run systemctl restart sw-cp-server.",
                source_refs,
            ),
        ],
        "summary": _semantic_smoke_observation(
            "Plesk task fails with an error",
            proposal_refs,
        ),
        "symptoms": [
            _semantic_smoke_observation(
                "A product task fails with an error.",
                proposal_refs,
            )
        ],
        "verification_evidence": [
            _semantic_smoke_observation(
                "Open Plesk and confirm the task completes successfully.",
                proposal_refs,
            )
        ],
    }


def _semantic_ref_containing(
    excerpt_text_by_ref: dict[str, str],
    proposal_refs: list[str],
    needle: str,
) -> str:
    for source_ref in proposal_refs:
        if needle in excerpt_text_by_ref.get(source_ref, ""):
            return source_ref
    raise SmokeError("semantic_review_packet_invalid")


def _semantic_smoke_observation(
    text: str,
    refs: list[str],
) -> dict[str, object]:
    return {"source_refs": refs, "text": text}


def _initialize_ok(response: dict[str, Any]) -> bool:
    result = response.get("result", {})
    return (
        result.get("protocolVersion") == PROTOCOL_VERSION
        and "kcs_draft_ticket" in str(result.get("instructions", ""))
        and "kcs_draft_article" in str(result.get("instructions", ""))
        and "kcs_register_clean_ticket" in str(result.get("instructions", ""))
    )


def _registry_cache_ok(wrapper: Path) -> bool:
    registry_path = _registry_cache_path(wrapper)
    if registry_path is None:
        return True
    extension_dir = wrapper.parent.parent
    manifest_path = extension_dir / "manifest.json"
    registry = _read_json_object(registry_path)
    installed_manifest = _read_json_object(manifest_path)
    if registry is None or installed_manifest is None:
        return False
    extensions = registry.get("extensions")
    if not isinstance(extensions, dict):
        return False
    entry = extensions.get(extension_dir.name)
    if not isinstance(entry, dict):
        return False
    registry_manifest = entry.get("manifest")
    if registry_manifest != installed_manifest:
        return False
    if not _registry_hash_ok(entry.get("hash")):
        return False
    return _registry_manifest_has_thin_contract(registry_manifest)


def _read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _registry_hash_ok(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    if not DEFAULT_MCPB_PACKAGE.is_file():
        return True
    try:
        return sha256(DEFAULT_MCPB_PACKAGE.read_bytes()).hexdigest() == value
    except OSError:
        return False


def _registry_cache_path(wrapper: Path) -> Path | None:
    if wrapper.name != "index.js" or wrapper.parent.name != "server":
        return None
    extension_dir = wrapper.parent.parent
    if not extension_dir.name.startswith("local.mcpb."):
        return None
    return extension_dir.parent.parent / "extensions-installations.json"


def _registry_manifest_has_thin_contract(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    tools = value.get("tools")
    if not isinstance(tools, list) or len(tools) != 7:
        return False
    long_description = str(value.get("long_description", ""))
    return _registry_manifest_tools_have_expected_descriptions(
        tools
    ) and _text_has_expected_terms(
        long_description,
        includes=_EXPECTED_REGISTRY_LONG_DESCRIPTION_INCLUDES,
        excludes=_EXPECTED_REGISTRY_LONG_DESCRIPTION_EXCLUDES,
    )


def _tool_surface_ok(response: dict[str, Any]) -> bool:
    tools = response.get("result", {}).get("tools", [])
    if len(tools) != 7:
        return False
    for spec in _EXPECTED_TOOL_SURFACES:
        tool = _tool_by_name(tools, spec.name)
        if tool is None or not _tool_matches_surface_spec(tool, spec):
            return False
    return True


def _registry_manifest_tools_have_expected_descriptions(tools: list[object]) -> bool:
    for spec in _EXPECTED_REGISTRY_MANIFEST_TOOL_DESCRIPTIONS:
        tool = _registry_manifest_tool_by_name(tools, spec.name)
        if tool is None:
            return False
        description = str(tool.get("description", ""))
        if not _text_has_expected_terms(
            description,
            includes=spec.includes,
            excludes=spec.excludes,
        ):
            return False
    return True


def _registry_manifest_tool_by_name(
    tools: list[object],
    name: str,
) -> dict[str, Any] | None:
    return next(
        (item for item in tools if isinstance(item, dict) and item.get("name") == name),
        None,
    )


def _tool_by_name(tools: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    return next((item for item in tools if item.get("name") == name), None)


def _text_has_expected_terms(
    text: str,
    *,
    includes: tuple[str, ...],
    excludes: tuple[str, ...],
) -> bool:
    return all(term in text for term in includes) and not any(
        term in text for term in excludes
    )


def _tool_matches_surface_spec(
    tool: dict[str, Any],
    spec: _ExpectedToolSurface,
) -> bool:
    schema = tool.get("inputSchema", {})
    properties = schema.get("properties", {})
    annotations = tool.get("annotations", {})
    description = str(tool.get("description", ""))
    if set(properties) != set(spec.properties):
        return False
    if spec.required is not None and schema.get("required") != list(spec.required):
        return False
    if (
        annotations.get("destructiveHint") is not spec.destructive
        or annotations.get("idempotentHint") is not spec.idempotent
        or annotations.get("openWorldHint") is not spec.open_world
        or annotations.get("readOnlyHint") is not spec.read_only
    ):
        return False
    if not _text_has_expected_terms(
        description,
        includes=spec.description_includes,
        excludes=spec.description_excludes,
    ):
        return False
    if spec.debug_description_includes:
        debug_description = str(properties.get("debug", {}).get("description", ""))
        return all(
            text in debug_description for text in spec.debug_description_includes
        )
    return True


def _no_candidates_ok(response: dict[str, Any]) -> bool:
    structured = _structured(response)
    text = _response_text(response)
    return (
        structured.get("pipeline_ok") is False
        and structured.get("failure_stage") == "semantic_extraction"
        and structured.get("debug_code") == "semantic_extraction_no_candidates"
        and "reviewer_only_html" not in structured
        and "KCS article drafting is blocked" in text
        and "Do not draft manually" in text
    )


def _selection_invalid_ok(response: dict[str, Any]) -> bool:
    structured = _structured(response)
    return (
        structured.get("pipeline_ok") is False
        and structured.get("failure_stage") == "operator_selection"
        and structured.get("debug_code") == "operator_selection_invalid"
        and "reviewer_only_html" not in structured
    )


def _mixed_call_shape_invalid_ok(response: dict[str, Any]) -> bool:
    structured = _structured(response)
    return (
        structured.get("pipeline_ok") is False
        and structured.get("failure_stage") == "input_validation"
        and structured.get("debug_code") == "draft_article_call_shape_invalid"
        and "reviewer_only_html" not in structured
    )


def _response_text(response: dict[str, Any]) -> str:
    content = response.get("result", {}).get("content", [])
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                return str(item.get("text", ""))
    return ""


def _response_html_resource_text(response: dict[str, Any]) -> str:
    content = response.get("result", {}).get("content", [])
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "text":
                continue
            text = str(item.get("text", ""))
            if text.startswith("```html\n") and "\n```\n\n```json\n" in text:
                return text.split("```html\n", 1)[1].split(
                    "\n```\n\n```json\n",
                    1,
                )[0]
    return ""


def _response_bundle_html_text(response: dict[str, Any]) -> str:
    html_path = _structured(response).get("html_path")
    if not isinstance(html_path, str):
        return ""
    roots = tuple(dict.fromkeys((REPO_ROOT, *_BUNDLE_FILE_ROOTS)))
    for root in roots:
        path = root / html_path
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            continue
    return ""


def _labeled_draft_ok(response: dict[str, Any]) -> bool:
    structured = _structured(response)
    return _comparison_required_ok(response, structured)


def _non_debug_labeled_draft_text_ok(response: dict[str, Any]) -> bool:
    structured = _structured(response)
    text = _response_text(response)
    return (
        _comparison_required_ok(response, structured)
        and not text.startswith("```html\n")
        and "Compare only accepted_ticket_facts" in text
        and "ask exactly one operator question" in text
        and "Do not call the submit tool until the operator answers." in text
    )


def _comparison_required_ok(
    response: dict[str, Any],
    structured: dict[str, Any] | None = None,
) -> bool:
    value = structured if structured is not None else _structured(response)
    candidates = value.get("comparison_candidates")
    return (
        response.get("result", {}).get("isError") is False
        and value.get("result_kind") == "reuse_comparison_required"
        and value.get("draft_generated") is False
        and value.get("reviewer_bundle_written") is False
        and value.get("writes_files") is False
        and value.get("next_tool") == CONFIRM_REUSE_COMPARISON_TOOL_NAME
        and value.get("submit_tool") == CONFIRM_REUSE_COMPARISON_TOOL_NAME
        and isinstance(value.get("comparison_ref"), str)
        and value.get("comparison_outcomes")
        == ["reuse", "update", "none_fit", "need_more_evidence"]
        and isinstance(candidates, list)
        and 1 <= len(candidates) <= 3
        and isinstance(value.get("accepted_ticket_facts"), list)
        and 1 <= len(value["accepted_ticket_facts"]) <= 8
        and "reviewer_only_html" not in value
        and "html_path" not in value
    )


def _native_batch_submit_arguments(
    split_response: dict[str, Any],
) -> dict[str, Any]:
    structured = _structured(split_response)
    choice_request = structured.get("operator_choice_request")
    if not isinstance(choice_request, dict):
        raise SmokeError("split_choice_missing")
    options = choice_request.get("options")
    if not isinstance(options, list) or not options:
        raise SmokeError("split_choice_missing")
    all_option = options[-1]
    if not isinstance(all_option, dict) or all_option.get("value") != "all":
        raise SmokeError("split_choice_missing")
    submit_arguments = all_option.get("submit_arguments")
    if not isinstance(submit_arguments, dict):
        raise SmokeError("split_choice_missing")
    return dict(submit_arguments)


def _split_choice_ok(responses: dict[str, dict[str, Any]]) -> bool:
    split = _structured(responses["split"])
    batch = _structured(responses["batch"])
    choice_request = split.get("operator_choice_request")
    if not isinstance(choice_request, dict):
        return False
    options = choice_request.get("options")
    return (
        isinstance(options, list)
        and _split_choice_request_ok(split, choice_request, options)
        and _comparison_required_ok(responses["batch"], batch)
        and _split_choice_text_ok(responses["split"])
    )


def _split_choice_request_ok(
    split: dict[str, Any],
    choice_request: dict[str, Any],
    options: list[object],
) -> bool:
    second_submit_arguments = None
    all_option = None
    if len(options) == 3 and isinstance(options[1], dict):
        second_submit_arguments = options[1].get("submit_arguments")
    if len(options) == 3 and isinstance(options[2], dict):
        all_option = options[2]
    selection_ref = split.get("operator_selection_ref")
    actual = {
        "all_option": all_option,
        "debug_code": split.get("debug_code"),
        "detached_arguments_absent": "all_submit_arguments" not in choice_request,
        "mode": choice_request.get("mode"),
        "option_count": len(options),
        "prose_only_choice_allowed": choice_request.get("prose_only_choice_allowed"),
        "recommended_action": split.get("recommended_action"),
        "second_submit_arguments": second_submit_arguments,
    }
    return actual == {
        "all_option": {
            "label": "All candidates",
            "submit_arguments": {
                "operator_selected_item_refs": ["candidate-001", "candidate-002"],
                "operator_selection_ref": selection_ref,
            },
            "value": "all",
        },
        "debug_code": "multiple_kcs_items_detected",
        "detached_arguments_absent": True,
        "mode": "single_or_batch_select",
        "option_count": 3,
        "prose_only_choice_allowed": False,
        "recommended_action": "split_required",
        "second_submit_arguments": {
            "operator_selected_item_ref": "candidate-002",
            "operator_selection_ref": selection_ref,
        },
    }


def _completed_batch_ok(batch: dict[str, Any]) -> bool:
    candidate_outcomes = batch.get("candidate_outcomes")
    if not isinstance(candidate_outcomes, list) or not all(
        isinstance(item, dict) for item in candidate_outcomes
    ):
        return False
    actual = {
        "batch_status": batch.get("batch_status"),
        "draft_generated_count": batch.get("draft_generated_count"),
        "item_refs": [item.get("item_ref") for item in candidate_outcomes],
        "outcomes": [item.get("outcome") for item in candidate_outcomes],
        "result_kind": batch.get("result_kind"),
        "reviewer_only_html_present": "reviewer_only_html" in batch,
    }
    return actual == {
        "batch_status": "batch_completed",
        "draft_generated_count": 2,
        "item_refs": ["candidate-001", "candidate-002"],
        "outcomes": ["completed_draft", "completed_draft"],
        "result_kind": "draft_article_batch",
        "reviewer_only_html_present": False,
    } and _batch_bundle_files_ok(candidate_outcomes)


def _batch_bundle_files_ok(candidate_outcomes: list[object]) -> bool:
    return all(
        isinstance(item, dict)
        and isinstance(item.get("html_path"), str)
        and _bundle_file_ok(str(item["html_path"]), item.get("html_sha256"))
        and _bundle_file_contains(str(item["html_path"]), "<h2>Resolution</h2>")
        for item in candidate_outcomes
    )


def _bundle_file_contains(html_path: str, expected_text: str) -> bool:
    roots = tuple(dict.fromkeys((REPO_ROOT, *_BUNDLE_FILE_ROOTS)))
    for root in roots:
        try:
            content = (root / html_path).read_text(encoding="utf-8")
        except OSError:
            continue
        if expected_text in content:
            return True
    return False


def _register_then_draft_ok(responses: dict[str, dict[str, Any]]) -> bool:
    registered = _structured(responses["register"])
    draft = _structured(responses["draft"])
    confirmed = _structured(responses["confirmed"])
    ticket_ref = registered.get("ticket_ref")
    register_text = json.dumps(responses["register"], sort_keys=True)
    return (
        responses["register"].get("result", {}).get("isError") is False
        and responses["draft"].get("result", {}).get("isError") is False
        and responses["confirmed"].get("result", {}).get("isError") is False
        and registered.get("result_kind") == "clean_ticket_registered"
        and isinstance(ticket_ref, str)
        and ticket_ref.startswith("smoke-monitoring-")
        and _clean_ticket_file_ok(
            ticket_ref,
            registered.get("clean_ticket_sha256"),
            min_mtime=_register_started_at(responses),
        )
        and registered.get("next_tool_name") == TOOL_NAME
        and registered.get("next_arguments") == {"ticket_ref": ticket_ref}
        and "clean_ticket_text" not in register_text
        and "When loading the monitoring module" not in register_text
        and _comparison_required_ok(responses["draft"], draft)
        and draft.get("ticket_ref") == ticket_ref
        and draft.get("approved_summary_source") == "local_clean_ticket"
        and confirmed.get("result_kind") == "approved_summary_authoring"
        and confirmed.get("draft_generated") is True
        and confirmed.get("recommended_action") == "create_candidate"
        and confirmed.get("reuse_search_status") == "checked"
        and confirmed.get("reviewer_bundle_written") is True
        and confirmed.get("writes_files") is True
        and _single_none_fit_sequence_ok(confirmed)
    )


def _single_none_fit_sequence_ok(confirmed: dict[str, Any]) -> bool:
    return confirmed.get("comparison_sequence_outcomes") == [
        {
            "bundle_ref": confirmed.get("bundle_ref"),
            "comparison_outcome": "none_fit",
            "draft_generated": True,
            "html_path": confirmed.get("html_path"),
            "item_ref": "candidate-001",
            "manifest_path": confirmed.get("manifest_path"),
            "recommended_action": "create_candidate",
            "reviewer_bundle_written": True,
        }
    ]


def _semantic_review_submit_ok(responses: dict[str, dict[str, Any]]) -> bool:
    draft = _structured(responses["draft"])
    prepare = _structured(responses["prepare"])
    submit = _structured(responses["submit"])
    batch = _structured(responses["batch"])
    response_text = json.dumps(responses["submit"], sort_keys=True)
    return (
        responses["draft"].get("result", {}).get("isError") is False
        and responses["prepare"].get("result", {}).get("isError") is False
        and responses["submit"].get("result", {}).get("isError") is False
        and draft.get("workflow_state") == "semantic_review_required"
        and draft.get("debug_code") == "semantic_identification_low_confidence"
        and draft.get("next_tool") == PREPARE_SEMANTIC_REVIEW_TOOL_NAME
        and prepare.get("result_kind") == "semantic_review_packet"
        and prepare.get("submit_tool") == SUBMIT_SEMANTIC_REVIEW_TOOL_NAME
        and prepare.get("selected_excerpts")
        and "active_output_schema" not in prepare
        and "allowed_output_schema" not in prepare
        and "runtime_default" not in prepare
        and "shadow_mode" not in prepare
        and set(prepare.get("proposal_field_contracts", {}))
        == {"reason_code"}
        and "semantic_issue_proposal" in prepare.get("required_submit_shape", {})
        and _unassigned_ledger_ok(submit)
        and _shared_identity_refs_remain_audit_only(submit)
        and _active_semantic_comparison_gate_ok(submit, responses["batch"], batch)
        and "reviewer_only_html" not in submit
        and "semantic_issue_proposal" not in response_text
    )


def _active_semantic_comparison_gate_ok(
    submit: dict[str, Any],
    batch_response: dict[str, Any],
    batch: dict[str, Any],
) -> bool:
    choice_request = submit.get("operator_choice_request")
    if not isinstance(choice_request, dict):
        return False
    options = choice_request.get("options")
    if not isinstance(options, list) or not options:
        return False
    all_option = options[-1]
    return (
        isinstance(all_option, dict)
        and submit.get("recommended_action") == "split_required"
        and submit.get("operator_prompt_style") == "native_choice_popup"
        and choice_request.get("prose_only_choice_allowed") is False
        and all_option.get("value") == "all"
        and (
            _comparison_required_ok(batch_response, batch)
            or _comparison_provider_blocked_ok(batch_response, batch)
        )
    )


def _comparison_provider_blocked_ok(
    response: dict[str, Any],
    structured: dict[str, Any],
) -> bool:
    return (
        response.get("result", {}).get("isError") is False
        and structured.get("result_kind") == "reuse_comparison_blocked"
        and structured.get("failure_stage") == "reuse_comparison"
        and structured.get("debug_code")
        in {
            "comparison_provider_invalid_response",
            "comparison_provider_unavailable",
        }
        and structured.get("draft_generated") is False
        and structured.get("reviewer_bundle_written") is False
        and structured.get("writes_files") is False
        and structured.get("manual_draft_allowed") is False
    )


def _shared_identity_refs_remain_audit_only(submit: dict[str, Any]) -> bool:
    outcomes = submit.get("semantic_item_outcomes")
    if not isinstance(outcomes, list):
        return False
    issue_outcomes = [
        outcome
        for outcome in outcomes
        if isinstance(outcome, dict) and outcome.get("outcome") == "draft_candidate"
    ]
    return (
        len(issue_outcomes) == 2
        and all(
            "boundary_state" not in outcome
            and "boundary_provenance" not in outcome
            for outcome in issue_outcomes
        )
    )


def _unassigned_ledger_ok(submit: dict[str, Any]) -> bool:
    outcomes = submit.get("semantic_item_outcomes")
    return (
        isinstance(outcomes, list)
        and any(
            isinstance(outcome, dict)
            and outcome.get("outcome") == "unassigned_evidence"
            for outcome in outcomes
        )
        and submit.get("workflow_state")
        != "semantic_review_boundary_choice_required"
    )


def _active_semantic_all_batch_ok(
    submit: dict[str, Any],
    batch: dict[str, Any],
) -> bool:
    choice_request = submit.get("operator_choice_request")
    if not isinstance(choice_request, dict):
        return False
    options = choice_request.get("options")
    if not isinstance(options, list) or not options:
        return False
    all_option = options[-1]
    if not isinstance(all_option, dict):
        return False
    return (
        submit.get("recommended_action") == "split_required"
        and submit.get("operator_prompt_style") == "native_choice_popup"
        and choice_request.get("prose_only_choice_allowed") is False
        and all_option.get("value") == "all"
        and _active_semantic_batch_outcomes_ok(batch)
    )


def _active_semantic_batch_outcomes_ok(batch: dict[str, Any]) -> bool:
    outcomes = batch.get("candidate_outcomes")
    if not isinstance(outcomes, list) or not all(
        isinstance(outcome, dict) for outcome in outcomes
    ):
        return False
    return (
        batch.get("result_kind") == "draft_article_batch"
        and batch.get("batch_status") == "batch_completed"
        and batch.get("draft_generated_count") == 2
        and [outcome.get("item_ref") for outcome in outcomes]
        == ["issue-001", "issue-002"]
        and all(outcome.get("attempted") is True for outcome in outcomes)
    )


def _semantic_review_invalid_submit_ok(
    responses: dict[str, dict[str, Any]],
) -> bool:
    submit = _structured(responses["submit"])
    text = _response_text(responses["submit"])
    return (
        responses["submit"].get("result", {}).get("isError") is False
        and submit.get("workflow_state") == "semantic_review_submit_blocked"
        and submit.get("debug_code")
        == "semantic_review_forbidden_html_or_markdown"
        and submit.get("draft_generated") is False
        and submit.get("reviewer_bundle_written") is False
        and submit.get("manual_draft_allowed") is False
        and "reviewer_only_html" not in submit
        and "Do not draft manually" in text
    )


def _split_choice_text_ok(response: dict[str, Any]) -> bool:
    content = response.get("result", {}).get("content", [])
    text = ""
    if isinstance(content, list) and content and isinstance(content[0], dict):
        text = str(content[0].get("text", ""))
    return (
        text.startswith("Multiple KCS article candidates were detected.")
        and "Operator selection is required before drafting." in text
        and "Use the native choice popup" in text
        and "Do not answer with a prose-only candidate list." in text
        and "submit_arguments" in text
        and "operator_all_submit_arguments" not in text
        and "do not call each option independently" in text
        and "Do not draft manually." in text
        and "candidate-002" in text
    )


def _batch_result_text_ok(response: dict[str, Any]) -> bool:
    structured = _structured(response)
    followup = structured.get("operator_followup")
    text = _response_text(response)
    return (
        isinstance(followup, dict)
        and followup.get("kind") == "none"
        and followup.get("retryable_candidates") == []
        and "Present the Python-owned ordered candidate summary" in text
        and "Operator result summary:" in text
        and "1. **" in text
        and "2. **" in text
        and "Reviewer bundle:" in text
        and "Reviewer HTML:" in text
        and "Authoritative per-candidate summary" not in text
        and '"candidate_outcomes"' not in text
        and "- Next:" not in text
    )


def _bundle_file_ok(html_path: str, expected_sha256: object) -> bool:
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        return False
    roots = tuple(dict.fromkeys((REPO_ROOT, *_BUNDLE_FILE_ROOTS)))
    for root in roots:
        path = root / html_path
        try:
            content = path.read_bytes()
        except OSError:
            continue
        if sha256(content).hexdigest() == expected_sha256:
            return True
    return False


def _clean_ticket_file_ok(
    ticket_ref: str,
    expected_sha256: object,
    *,
    min_mtime: float,
) -> bool:
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        return False
    roots = tuple(dict.fromkeys((REPO_ROOT, *_BUNDLE_FILE_ROOTS)))
    for root in roots:
        path = (
            root / "local-data" / "approved-summaries" / ticket_ref / "clean.ticket.txt"
        )
        try:
            stat = path.stat()
            content = path.read_bytes()
        except OSError:
            continue
        if stat.st_mtime < min_mtime:
            continue
        if sha256(content).hexdigest() == expected_sha256:
            return True
    return False


def _register_started_at(responses: dict[str, dict[str, Any]]) -> float:
    value = responses.get("_register_started_at", {}).get("value")
    return value if isinstance(value, (int, float)) else 0.0


def _runtime_bundle_file_roots(wrapper: Path) -> tuple[Path, ...]:
    roots = [
        Path.home() / "Library" / "Application Support" / "KCS Authoring",
        REPO_ROOT,
    ]
    if approved_ticket_store_root := os.environ.get(APPROVED_TICKET_STORE_ROOT_ENV):
        roots.insert(0, Path(approved_ticket_store_root))
    bundled_root = wrapper.parent.parent / "python"
    if (bundled_root / "pyproject.toml").is_file():
        roots.insert(1, Path.home() / "Documents" / "KCS Authoring")
        roots.insert(2, bundled_root)
    return tuple(dict.fromkeys(root.resolve() for root in roots))


def _structured(response: dict[str, Any]) -> dict[str, Any]:
    structured = response.get("result", {}).get("structuredContent", {})
    return structured if isinstance(structured, dict) else {}


def _write_json(stream: Any, payload: dict[str, Any]) -> None:
    stream.write(json.dumps(payload, allow_nan=False, sort_keys=True))
    stream.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
