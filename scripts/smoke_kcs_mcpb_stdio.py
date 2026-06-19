"""Run a deterministic stdio smoke against the KCS Authoring MCPB wrapper."""

from __future__ import annotations

import argparse
import json
import os
import selectors
import shutil
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_NAME = "kcs-authoring-mvp-validator-control"
DEFAULT_SOURCE_WRAPPER = (
    REPO_ROOT
    / "packaging"
    / "claude-desktop"
    / BUNDLE_NAME
    / "server"
    / "index.js"
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
CALL_REQUEST_IDS = (3, 4, 5, 6, 7, 8, 9, 10, 11, 12)


class SmokeError(RuntimeError):
    """Value-safe smoke failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


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

    node = _node_command(node_command)
    if not wrapper.is_file():
        raise SmokeError("wrapper_not_found")
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
    checks["split_choice_ok"] = _split_choice_ok(split_choice)
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
            _structured(split_choice["selected"]).get("debug_code", ""),
        ],
        "registry_cache_checked": _registry_cache_path(wrapper) is not None,
        "tool_count": len(tools.get("result", {}).get("tools", [])),
        "wrapper_kind": (
            "installed" if wrapper == DEFAULT_INSTALLED_WRAPPER else "custom"
        ),
    }


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
    env = {
        **os.environ,
        "KCS_AUTHORING_MVP_REPO_ROOT": str(REPO_ROOT),
        "KCS_AUTHORING_MVP_UV_COMMAND": uv_command,
        "KCS_AUTHORING_SEMANTIC_PROVIDER": "fixture",
    }
    payload = "".join(
        json.dumps(message, separators=(",", ":")) + "\n"
        for message in messages
    )
    try:
        completed = subprocess.run(
            [node, str(wrapper)],
            input=payload,
            capture_output=True,
            check=False,
            env=env,
            text=True,
            timeout=15,
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
    env = {
        **os.environ,
        "KCS_AUTHORING_MVP_REPO_ROOT": str(REPO_ROOT),
        "KCS_AUTHORING_MVP_UV_COMMAND": uv_command,
        "KCS_AUTHORING_SEMANTIC_PROVIDER": "fixture",
    }
    try:
        process = subprocess.Popen(
            [node, str(wrapper)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
        )
    except OSError as exc:
        raise SmokeError("wrapper_failed") from exc
    try:
        initialize = _send_jsonrpc(process, _request(7, "initialize", {
            "protocolVersion": PROTOCOL_VERSION
        }))
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
        submit_arguments = _selected_submit_arguments(split)
        selected = _send_jsonrpc(
            process,
            _request(
                9,
                "tools/call",
                {"name": TOOL_NAME, "arguments": submit_arguments},
            ),
        )
        return {"initialize": initialize, "selected": selected, "split": split}
    finally:
        _close_process(process)


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


def _initialize_ok(response: dict[str, Any]) -> bool:
    result = response.get("result", {})
    return (
        result.get("protocolVersion") == PROTOCOL_VERSION
        and "kcs_draft_article" in str(result.get("instructions", ""))
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
    if not isinstance(tools, list) or len(tools) != 1:
        return False
    tool = tools[0]
    if not isinstance(tool, dict) or tool.get("name") != TOOL_NAME:
        return False
    description = str(tool.get("description", ""))
    long_description = str(value.get("long_description", ""))
    return (
        "pass only approved_summary_text" in description
        and "Python owns semantic extraction" in description
        and "local reviewer bundle output" in description
        and "when the client provides one" in description
        and "submit_arguments exactly" in description
        and "structured item" not in description
        and "Use with either ticket_ref" not in description
        and "show the returned candidates in a native Claude Desktop choice popup"
        not in description
        and "Returns reviewer_only_html" not in description
        and "one primary read-only tool" not in long_description
    )


def _tool_surface_ok(response: dict[str, Any]) -> bool:
    tools = response.get("result", {}).get("tools", [])
    if len(tools) != 1 or tools[0].get("name") != TOOL_NAME:
        return False
    properties = tools[0].get("inputSchema", {}).get("properties", {})
    annotations = tools[0].get("annotations", {})
    description = str(tools[0].get("description", ""))
    debug_description = str(properties.get("debug", {}).get("description", ""))
    return (
        set(properties)
        == {
            "approved_summary_text",
            "debug",
            "operator_selected_item_ref",
            "operator_selection_ref",
        }
        and "item" not in properties
        and "item_candidates" not in properties
        and annotations.get("destructiveHint") is False
        and annotations.get("idempotentHint") is False
        and annotations.get("readOnlyHint") is False
        and "Python owns semantic extraction" in description
        and "local reviewer bundle output" in description
        and "reviewer_only_html" in debug_description
        and "html_path" in debug_description
    )


def _no_candidates_ok(response: dict[str, Any]) -> bool:
    structured = _structured(response)
    return (
        structured.get("pipeline_ok") is False
        and structured.get("failure_stage") == "semantic_extraction"
        and structured.get("debug_code") == "semantic_extraction_no_candidates"
        and "reviewer_only_html" not in structured
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


def _labeled_draft_ok(response: dict[str, Any]) -> bool:
    structured = _structured(response)
    html = structured.get("reviewer_only_html")
    html_path = structured.get("html_path")
    return (
        response.get("result", {}).get("isError") is False
        and structured.get("draft_generated") is True
        and structured.get("debug_code") == "draft_only_reuse_search_missing"
        and structured.get("recommended_action") == "draft_only"
        and structured.get("reuse_search_status") == "skipped"
        and structured.get("reviewer_bundle_written") is True
        and structured.get("writes_files") is True
        and isinstance(html_path, str)
        and html_path.startswith("local-data/reviewer-bundles/")
        and _bundle_file_ok(html_path, structured.get("html_sha256"))
        and isinstance(html, str)
        and "Connect to the Plesk server via SSH.</a>" in html
    )


def _non_debug_labeled_draft_text_ok(response: dict[str, Any]) -> bool:
    structured = _structured(response)
    content = response.get("result", {}).get("content", [])
    text = ""
    if isinstance(content, list) and content and isinstance(content[0], dict):
        text = str(content[0].get("text", ""))
    return (
        response.get("result", {}).get("isError") is False
        and structured.get("draft_generated") is True
        and structured.get("debug_code") == "draft_only_reuse_search_missing"
        and "reviewer_only_html" not in structured
        and text.startswith("Reviewer-only KCS draft generated.")
        and "html_path" in text
        and "Do not draft manually or retry the tool" in text
        and "Reviewer-only Zendesk HTML draft:" not in text
    )


def _selected_submit_arguments(split_response: dict[str, Any]) -> dict[str, Any]:
    structured = _structured(split_response)
    choice_request = structured.get("operator_choice_request")
    if not isinstance(choice_request, dict):
        raise SmokeError("split_choice_missing")
    options = choice_request.get("options")
    if not isinstance(options, list) or len(options) < 2:
        raise SmokeError("split_choice_missing")
    selected = options[1]
    if not isinstance(selected, dict):
        raise SmokeError("split_choice_missing")
    submit_arguments = selected.get("submit_arguments")
    if not isinstance(submit_arguments, dict):
        raise SmokeError("split_choice_missing")
    return dict(submit_arguments)


def _split_choice_ok(responses: dict[str, dict[str, Any]]) -> bool:
    split = _structured(responses["split"])
    selected = _structured(responses["selected"])
    choice_request = split.get("operator_choice_request")
    if not isinstance(choice_request, dict):
        return False
    options = choice_request.get("options")
    selected_html = selected.get("reviewer_only_html")
    return (
        split.get("debug_code") == "multiple_kcs_items_detected"
        and split.get("recommended_action") == "split_required"
        and choice_request.get("mode") == "single_select"
        and choice_request.get("prose_only_choice_allowed") is False
        and isinstance(options, list)
        and len(options) == 2
        and options[1].get("submit_arguments")
        == {
            "operator_selected_item_ref": "candidate-002",
            "operator_selection_ref": split.get("operator_selection_ref"),
        }
        and selected.get("draft_generated") is True
        and selected.get("item_ref") == "candidate-002"
        and selected.get("debug_code") == "draft_only_reuse_search_missing"
        and selected.get("reviewer_bundle_written") is True
        and selected.get("writes_files") is True
        and isinstance(selected.get("html_path"), str)
        and _bundle_file_ok(
            str(selected.get("html_path")),
            selected.get("html_sha256"),
        )
        and selected_html is None
        and _split_choice_text_ok(responses["split"])
    )


def _split_choice_text_ok(response: dict[str, Any]) -> bool:
    content = response.get("result", {}).get("content", [])
    text = ""
    if isinstance(content, list) and content and isinstance(content[0], dict):
        text = str(content[0].get("text", ""))
    return (
        text.startswith("Multiple KCS article candidates were detected.")
        and "Operator selection is required before drafting." in text
        and "Use a native single-choice popup" in text
        and "submit_arguments" in text
        and "Do not draft manually." in text
        and "candidate-002" in text
    )


def _bundle_file_ok(html_path: str, expected_sha256: object) -> bool:
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        return False
    path = REPO_ROOT / html_path
    try:
        content = path.read_bytes()
    except OSError:
        return False
    return sha256(content).hexdigest() == expected_sha256


def _structured(response: dict[str, Any]) -> dict[str, Any]:
    structured = response.get("result", {}).get("structuredContent", {})
    return structured if isinstance(structured, dict) else {}


def _write_json(stream: Any, payload: dict[str, Any]) -> None:
    stream.write(json.dumps(payload, allow_nan=False, sort_keys=True))
    stream.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
