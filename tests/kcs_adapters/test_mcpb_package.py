from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import zipfile
from hashlib import sha256
from pathlib import Path

import pytest

from kcs_adapters.mcp_desktop import (
    CLAUDE_DESKTOP_TOOL_ALIASES,
    DESKTOP_OPERATOR_TOOLS,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MCPB_SOURCE = (
    REPO_ROOT
    / "packaging"
    / "claude-desktop"
    / "kcs-authoring-mvp-validator-control"
)
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_kcs_mcpb.py"
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install_kcs_mcpb.py"
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "smoke_kcs_mcpb_stdio.py"
LOG_CHECK_SCRIPT = REPO_ROOT / "scripts" / "check_claude_kcs_desktop_log.py"
UI_SMOKE_SCRIPT = REPO_ROOT / "scripts" / "smoke_claude_desktop_ui_prompt.py"
EXPECTED_STATIC_BUNDLE_FILES = {
    "README.md",
    "manifest.json",
    "server/index.js",
}
NODE_COMMAND = shutil.which("node")


def _load_build_module():
    spec = importlib.util.spec_from_file_location("build_kcs_mcpb", BUILD_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_install_module():
    spec = importlib.util.spec_from_file_location("install_kcs_mcpb", INSTALL_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_smoke_module():
    spec = importlib.util.spec_from_file_location("smoke_kcs_mcpb_stdio", SMOKE_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_log_check_module():
    spec = importlib.util.spec_from_file_location(
        "check_claude_kcs_desktop_log", LOG_CHECK_SCRIPT
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_ui_smoke_module():
    spec = importlib.util.spec_from_file_location(
        "smoke_claude_desktop_ui_prompt", UI_SMOKE_SCRIPT
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _copy_mcpb_source(tmp_path: Path) -> Path:
    source = tmp_path / "bundle"
    shutil.copytree(MCPB_SOURCE, source)
    return source


def test_mcpb_manifest_exposes_desktop_alias_tools_only() -> None:
    manifest = json.loads((MCPB_SOURCE / "manifest.json").read_text(encoding="utf-8"))
    expected_tool_names = {
        CLAUDE_DESKTOP_TOOL_ALIASES[tool_name]
        for tool_name in DESKTOP_OPERATOR_TOOLS
    }

    assert manifest["manifest_version"] == "0.3"
    assert manifest["name"] == "kcs-authoring-mvp-validator-control"
    assert manifest["server"]["type"] == "node"
    assert manifest["server"]["entry_point"] == "server/index.js"
    assert manifest["server"]["mcp_config"]["command"] == "node"
    assert {tool["name"] for tool in manifest["tools"]} == expected_tool_names
    assert "primary tool is kcs_draft_article" in manifest["long_description"]
    assert "kcs_prepare_semantic_review" in manifest["long_description"]
    assert "kcs_submit_semantic_review" in manifest["long_description"]
    assert "selected excerpts only" in manifest["long_description"]
    assert "support_get_behavior_instructions compatibility helper" in (
        manifest["long_description"]
    )
    assert "Claude Desktop-owned provider calls" in manifest["long_description"]
    assert "Claude CLI/Code dependency" in manifest["long_description"]
    assert "API-key dependency" in manifest["long_description"]
    assert "Claude Desktop-owned provider calls" in manifest["long_description"]
    assert all(
        not tool["name"].startswith("kcs_validate_")
        for tool in manifest["tools"]
    )
    assert all("." not in tool["name"] for tool in manifest["tools"])
    register_tool = next(
        tool
        for tool in manifest["tools"]
        if tool["name"] == "kcs_register_clean_ticket"
    )
    assert "Register one approved sanitized" in register_tool["description"]
    assert "automatic first step" in register_tool["description"]
    assert "even when long" in register_tool["description"]
    assert "clean_ticket_text" in register_tool["description"]
    assert "clean.ticket.txt" in register_tool["description"]
    assert "next_arguments for kcs_draft_article" in register_tool["description"]
    draft_tool = next(
        tool for tool in manifest["tools"] if tool["name"] == "kcs_draft_article"
    )
    assert "Primary KCS authoring tool" in draft_tool["description"]
    assert "ticket_ref" in draft_tool["description"]
    assert "approved_summary_text" in draft_tool["description"]
    assert "operator-provided sanitized attachment or long paste" in (
        draft_tool["description"]
    )
    assert "kcs_register_clean_ticket first" in draft_tool["description"]
    assert "approved_summary_text only as a fallback" in draft_tool["description"]
    assert "upload filenames, paths, item, item_candidates" in draft_tool[
        "description"
    ]
    assert "Claude Desktop file card is not a filesystem path" in draft_tool[
        "description"
    ]
    assert "do not inspect upload directories" in draft_tool["description"]
    assert "file_content_unavailable" in draft_tool["description"]
    assert "Python validates the input and owns semantic extraction" in (
        draft_tool["description"]
    )
    assert "raw comments" not in draft_tool["description"]
    assert "internal notes" not in draft_tool["description"]
    assert "operator_selection_ref" in draft_tool["description"]
    assert "operator_selected_item_ref" in draft_tool["description"]
    assert "reviewer-only Zendesk HTML" in draft_tool["description"]
    prepare_tool = next(
        tool
        for tool in manifest["tools"]
        if tool["name"] == "kcs_prepare_semantic_review"
    )
    assert "bounded Claude-visible semantic-review packet" in prepare_tool[
        "description"
    ]
    assert "selected excerpts only" in prepare_tool["description"]
    assert "candidate_semantic_extraction_v1" in prepare_tool["description"]
    assert "Do not draft an article" in prepare_tool["description"]
    submit_tool = next(
        tool
        for tool in manifest["tools"]
        if tool["name"] == "kcs_submit_semantic_review"
    )
    assert "candidate_semantic_extraction_v1" in submit_tool["description"]
    assert "selected_excerpts source refs" in submit_tool["description"]
    assert "Do not submit article drafts" in submit_tool["description"]
    behavior_tool = next(
        tool
        for tool in manifest["tools"]
        if tool["name"] == "support_get_behavior_instructions"
    )
    assert "Compatibility helper" in behavior_tool["description"]
    assert "kcs_draft_article" in behavior_tool["description"]
    assert "copy the tool content verbatim" not in draft_tool["description"]
    assert "Do not rewrite it into a Markdown article" not in draft_tool["description"]
    assert "let me know if you want adjustments" not in draft_tool["description"]
    assert "structured item" not in draft_tool["description"]
    assert "break-fix" not in draft_tool["description"]
    assert manifest["prompts_generated"] is False
    assert manifest["tools_generated"] is False


def test_mcpb_manifest_requires_no_user_config_or_secrets() -> None:
    text = (MCPB_SOURCE / "manifest.json").read_text(encoding="utf-8")
    manifest = json.loads(text)

    assert "user_config" not in manifest
    assert "${user_config.repository_root}" not in text
    assert "${user_config.uv_command}" not in text
    assert manifest["server"]["mcp_config"]["env"] == {}
    assert "Installing this MCPB is the only required Claude Desktop setup step" in (
        manifest["long_description"]
    )
    assert "autodetected local runtime" in manifest["long_description"]
    assert "/Users/" not in text
    assert "api_key" not in text.casefold()
    assert "token" not in text.casefold()
    assert "secret" not in text.casefold()


def test_mcpb_node_wrapper_launches_bundled_or_source_stdio_server() -> None:
    text = (MCPB_SOURCE / "server" / "index.js").read_text(encoding="utf-8")

    assert "KCS_AUTHORING_MVP_REPO_ROOT" in text
    assert "KCS_AUTHORING_MVP_APPROVED_TICKET_STORE_ROOT" in text
    assert "KCS_AUTHORING_MVP_APPROVED_TICKET_STORAGE_HINT" in text
    assert "KCS_AUTHORING_MVP_APPROVED_TICKET_STORAGE_REF" in text
    assert "defaultCleanTicketStoreRoot" in text
    assert (
        "KCS_AUTHORING_MVP_APPROVED_TICKET_STORE_ROOT:\n"
        "    process.env.KCS_AUTHORING_MVP_APPROVED_TICKET_STORE_ROOT ||\n"
        "    defaultCleanTicketStoreRoot"
    ) in text
    assert "KCS_AUTHORING_MVP_REVIEWER_BUNDLE_ROOT" in text
    assert "KCS_AUTHORING_MVP_REVIEWER_BUNDLE_STORAGE_HINT" in text
    assert "KCS_AUTHORING_MVP_REVIEWER_BUNDLE_STORAGE_REF" in text
    assert "KCS_AUTHORING_MVP_UV_COMMAND" in text
    assert "KCS_AUTHORING_MVP_PYTHON_COMMAND" in text
    assert "KCS_AUTHORING_MVP_RUNTIME" in text
    assert "bundledRoot" in text
    assert '"python"' in text
    assert '"python3.11"' in text
    assert "PYTHONPATH" in text
    assert "sourceRoot" in text
    assert 'name = "kcs-authoring-mvp"' in text
    assert "src\", \"kcs_adapters\", \"mcp_desktop.py" in text
    assert '"--project"' in text
    assert '"kcs-desktop-mcp"' in text
    assert '"claude_desktop_aliases"' in text
    assert "/Users/" not in text
    assert "plesk" not in text.casefold()
    assert "process.stdin.pipe(child.stdin)" in text
    assert "child.stdout" in text
    assert "USERPROFILE" in text
    assert "APPDATA" in text
    assert "Application Support" in text
    assert "Documents" in text
    assert "KCS Authoring" in text
    assert "TMPDIR" in text


def test_stdio_smoke_checks_persisted_clean_ticket_file(
    tmp_path,
    monkeypatch,
) -> None:
    smoke = _load_smoke_module()
    ticket_ref = "ticket-96024747"
    clean_ticket = (
        tmp_path
        / "local-data"
        / "approved-summaries"
        / ticket_ref
        / "clean.ticket.txt"
    )
    clean_ticket.parent.mkdir(parents=True)
    content = b"When loading the monitoring module in Plesk, graphs show no data."
    clean_ticket.write_bytes(content)
    expected_sha256 = sha256(content).hexdigest()
    min_mtime = clean_ticket.stat().st_mtime - 1.0
    monkeypatch.setattr(smoke, "_BUNDLE_FILE_ROOTS", (tmp_path,))

    assert (
        smoke._clean_ticket_file_ok(
            ticket_ref,
            expected_sha256,
            min_mtime=min_mtime,
        )
        is True
    )
    assert (
        smoke._clean_ticket_file_ok(
            ticket_ref,
            "0" * 64,
            min_mtime=min_mtime,
        )
        is False
    )
    assert (
        smoke._clean_ticket_file_ok(
            ticket_ref,
            expected_sha256,
            min_mtime=clean_ticket.stat().st_mtime + 1.0,
        )
        is False
    )
    assert (
        smoke._clean_ticket_file_ok(
            "ticket-missing",
            expected_sha256,
            min_mtime=min_mtime,
        )
        is False
    )


def test_stdio_smoke_roots_include_approved_ticket_store_override(
    tmp_path,
    monkeypatch,
) -> None:
    smoke = _load_smoke_module()
    monkeypatch.setenv(smoke.APPROVED_TICKET_STORE_ROOT_ENV, str(tmp_path))

    roots = smoke._runtime_bundle_file_roots(MCPB_SOURCE / "server" / "index.js")

    assert tmp_path.resolve() in roots


def test_mcpb_node_wrapper_rejects_wrong_explicit_repo_root_without_spawn(
    tmp_path: Path,
) -> None:
    if NODE_COMMAND is None:
        pytest.skip("node is not installed")
    repo = tmp_path / "wrong-repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "not-kcs-authoring-mvp"\n',
        encoding="utf-8",
    )

    completed = subprocess.run(
        [NODE_COMMAND, str(MCPB_SOURCE / "server" / "index.js")],
        check=False,
        env={
            "KCS_AUTHORING_MVP_REPO_ROOT": str(repo),
            "KCS_AUTHORING_MVP_UV_COMMAND": "uv",
            "PATH": "",
        },
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert completed.returncode != 0
    assert (
        "KCS_AUTHORING_MVP_REPO_ROOT must point to the KCS Authoring MVP project"
        in completed.stderr
    )
    assert "not-kcs-authoring-mvp" not in completed.stderr


def test_mcpb_node_wrapper_rejects_uv_command_with_arguments() -> None:
    if NODE_COMMAND is None:
        pytest.skip("node is not installed")
    completed = subprocess.run(
        [NODE_COMMAND, str(MCPB_SOURCE / "server" / "index.js")],
        check=False,
        env={
            "KCS_AUTHORING_MVP_REPO_ROOT": str(REPO_ROOT),
            "KCS_AUTHORING_MVP_UV_COMMAND": "uv --project /private",
            "PATH": "",
        },
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert completed.returncode != 0
    assert (
        "KCS_AUTHORING_MVP_UV_COMMAND must be an executable name or path "
        "without arguments" in completed.stderr
    )
    assert "/private" not in completed.stderr


def test_mcpb_node_wrapper_forwards_semantic_provider_env() -> None:
    text = (MCPB_SOURCE / "server" / "index.js").read_text(encoding="utf-8")

    assert "KCS_AUTHORING_SEMANTIC_PROVIDER" in text
    assert "KCS_AUTHORING_APPROVED_SEMANTIC_PROVIDER_REF" in text


def test_build_script_creates_mcpb_archive(tmp_path: Path) -> None:
    module = _load_build_module()
    output = tmp_path / "kcs-authoring-mvp-validator-control.mcpb"

    built = module.build_mcpb(source=MCPB_SOURCE, output=output)

    assert built == output
    assert output.is_file()
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert names == {
            path.as_posix() for path in module.expected_bundle_files()
        }
        assert EXPECTED_STATIC_BUNDLE_FILES.issubset(names)
        assert "python/pyproject.toml" in names
        assert "python/src/kcs_adapters/mcp_desktop.py" in names
        assert "python/src/kcs_core/semantic_extraction.py" in names
        assert all(".venv" not in name for name in names)
        assert all("__pycache__" not in name for name in names)
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
    assert manifest["name"] == "kcs-authoring-mvp-validator-control"


def test_mcpb_stdio_smoke_tool_surface_check_accepts_current_contract() -> None:
    module = _load_smoke_module()
    response = {
        "result": {
            "tools": [
                {
                    "annotations": {
                        "destructiveHint": False,
                        "idempotentHint": False,
                        "openWorldHint": False,
                        "readOnlyHint": False,
                    },
                    "description": (
                        "Register one approved sanitized transcript. "
                        "Use clean_ticket_text. Writes clean.ticket.txt and "
                        "returns next_arguments. A Claude Desktop file card is "
                        "not a filesystem path; do not inspect upload "
                        "directories."
                    ),
                    "inputSchema": {
                        "properties": {
                            "clean_ticket_text": {},
                            "debug": {},
                            "ticket_ref": {},
                        },
                        "required": ["clean_ticket_text"],
                    },
                    "name": "kcs_register_clean_ticket",
                },
                {
                    "annotations": {
                        "destructiveHint": False,
                        "idempotentHint": False,
                        "openWorldHint": False,
                        "readOnlyHint": False,
                    },
                    "description": (
                        "Prefer ticket_ref. Python validates the input and "
                        "owns semantic extraction. A Claude Desktop file card "
                        "is not a filesystem path; do not inspect upload "
                        "directories. file_content_unavailable."
                    ),
                    "inputSchema": {
                        "properties": {
                            "approved_summary_text": {},
                            "debug": {
                                "description": (
                                    "Successful Desktop draft results already "
                                    "include reviewer-only Zendesk HTML."
                                )
                            },
                            "operator_selected_item_ref": {},
                            "operator_selection_ref": {},
                            "ticket_ref": {},
                        }
                    },
                    "name": "kcs_draft_article",
                },
                {
                    "annotations": {
                        "destructiveHint": False,
                        "idempotentHint": True,
                        "openWorldHint": False,
                        "readOnlyHint": True,
                    },
                    "description": (
                        "Return a bounded Claude-visible semantic-review packet "
                        "with selected excerpts only in "
                        "candidate_semantic_extraction_v1 format. Do not draft "
                        "an article."
                    ),
                    "inputSchema": {
                        "properties": {"semantic_review_ref": {}},
                        "required": ["semantic_review_ref"],
                    },
                    "name": "kcs_prepare_semantic_review",
                },
                {
                    "annotations": {
                        "destructiveHint": False,
                        "idempotentHint": False,
                        "openWorldHint": False,
                        "readOnlyHint": False,
                    },
                    "description": (
                        "Submit candidate_semantic_extraction_v1 grounded in "
                        "selected_excerpts source refs. Do not submit article "
                        "drafts."
                    ),
                    "inputSchema": {
                        "properties": {
                            "candidate_semantic_extraction": {},
                            "semantic_review_ref": {},
                        },
                        "required": [
                            "semantic_review_ref",
                            "candidate_semantic_extraction",
                        ],
                    },
                    "name": "kcs_submit_semantic_review",
                },
                {
                    "annotations": {
                        "destructiveHint": False,
                        "idempotentHint": True,
                        "openWorldHint": False,
                        "readOnlyHint": True,
                    },
                    "description": "Compatibility helper for kcs_draft_article.",
                    "inputSchema": {"properties": {}},
                    "name": "support_get_behavior_instructions",
                },
            ]
        }
    }

    assert module._tool_surface_ok(response) is True


def test_mcpb_stdio_smoke_tool_surface_rejects_upload_reference_contract() -> None:
    module = _load_smoke_module()
    response = {
        "result": {
            "tools": [
                {
                    "description": "Python owns semantic extraction.",
                    "inputSchema": {
                        "properties": {
                            "approved_summary_text": {},
                            "debug": {},
                            "operator_selected_item_ref": {},
                            "operator_selection_ref": {},
                            "ticket_ref": {},
                        }
                    },
                    "name": "kcs_draft_article",
                }
            ]
        }
    }

    assert module._tool_surface_ok(response) is False


def test_mcpb_stdio_smoke_result_checks_controlled_statuses(tmp_path: Path) -> None:
    module = _load_smoke_module()
    html_path = "local-data/reviewer-bundles/run/item/reviewer_only.html"
    html = (
        '<a href="https://support.plesk.com/hc/en-us/articles/'
        '12377512781975-How-to-connect-to-a-Plesk-server-via-SSH">'
        "Connect to the Plesk server via SSH.</a>"
    )
    old_repo_root = module.REPO_ROOT
    module.REPO_ROOT = tmp_path
    bundle_file = tmp_path / html_path
    bundle_file.parent.mkdir(parents=True, exist_ok=True)
    bundle_file.write_text(html, encoding="utf-8")
    no_candidates = {
        "result": {
            "content": [
                {
                    "text": (
                        "KCS article drafting is blocked by the KCS Authoring "
                        "tool. Do not draft manually."
                    ),
                    "type": "text",
                }
            ],
            "structuredContent": {
                "debug_code": "semantic_extraction_no_candidates",
                "failure_stage": "semantic_extraction",
                "pipeline_ok": False,
            }
        }
    }
    selection_invalid = {
        "result": {
            "structuredContent": {
                "debug_code": "operator_selection_invalid",
                "failure_stage": "operator_selection",
                "pipeline_ok": False,
            }
        }
    }
    mixed_invalid = {
        "result": {
            "structuredContent": {
                "debug_code": "draft_article_call_shape_invalid",
                "failure_stage": "input_validation",
                "pipeline_ok": False,
            }
        }
    }
    labeled_draft = {
        "result": {
            "content": [
                {
                    "text": "```html\n"
                    f"{html}\n"
                    "```\n\n"
                    "```json\n"
                    '{"html_path":"local-data/reviewer-bundles/run/item/'
                    'reviewer_only.html"}\n'
                    "```",
                    "type": "text",
                },
            ],
            "isError": False,
            "structuredContent": {
                "debug_code": "draft_only_reuse_search_missing",
                "draft_generated": True,
                "html_path": html_path,
                "html_sha256": module.sha256(html.encode("utf-8")).hexdigest(),
                "recommended_action": "draft_only",
                "reuse_search_status": "skipped",
                "reviewer_bundle_written": True,
                "writes_files": True,
            },
        }
    }

    try:
        assert module._no_candidates_ok(no_candidates) is True
        assert module._selection_invalid_ok(selection_invalid) is True
        assert module._mixed_call_shape_invalid_ok(mixed_invalid) is True
        assert module._labeled_draft_ok(labeled_draft) is True
    finally:
        module.REPO_ROOT = old_repo_root


def test_mcpb_stdio_smoke_result_checks_split_choice_flow(tmp_path: Path) -> None:
    module = _load_smoke_module()
    html_path = "local-data/reviewer-bundles/run/candidate-002/reviewer_only.html"
    html = (
        "<h1>Monitoring extension post-install fails</h1>"
        "<h2>Resolution</h2><ol><li>Restart the service.</li></ol>"
    )
    old_repo_root = module.REPO_ROOT
    module.REPO_ROOT = tmp_path
    bundle_file = tmp_path / html_path
    bundle_file.parent.mkdir(parents=True, exist_ok=True)
    bundle_file.write_text(html, encoding="utf-8")
    split = {
        "result": {
            "content": [
                {
                    "text": (
                        "Multiple KCS article candidates were detected. "
                        "Operator selection is required before drafting.\n\n"
                        "Use a native single-choice popup if Claude Desktop "
                        "provides one. submit_arguments. Do not draft manually.\n"
                        "candidate-002"
                    ),
                    "type": "text",
                }
            ],
            "structuredContent": {
                "debug_code": "multiple_kcs_items_detected",
                "operator_choice_request": {
                    "mode": "single_select",
                    "options": [
                        {
                            "submit_arguments": {
                                "operator_selected_item_ref": "candidate-001",
                                "operator_selection_ref": "operator-selection-abc",
                            },
                            "value": "candidate-001",
                        },
                        {
                            "submit_arguments": {
                                "operator_selected_item_ref": "candidate-002",
                                "operator_selection_ref": "operator-selection-abc",
                            },
                            "value": "candidate-002",
                        },
                    ],
                    "prose_only_choice_allowed": False,
                },
                "operator_selection_ref": "operator-selection-abc",
                "recommended_action": "split_required",
            }
        }
    }
    selected = {
        "result": {
            "content": [
                {
                    "text": "```html\n"
                    f"{html}\n"
                    "```\n\n"
                    "```json\n"
                    '{"html_path":"local-data/reviewer-bundles/run/'
                    'candidate-002/reviewer_only.html"}\n'
                    "```",
                    "type": "text",
                },
            ],
            "structuredContent": {
                "debug_code": "draft_only_reuse_search_missing",
                "draft_generated": True,
                "html_path": html_path,
                "html_sha256": module.sha256(html.encode("utf-8")).hexdigest(),
                "item_ref": "candidate-002",
                "reviewer_bundle_written": True,
                "writes_files": True,
            }
        }
    }

    try:
        assert module._selected_submit_arguments(split) == {
            "operator_selected_item_ref": "candidate-002",
            "operator_selection_ref": "operator-selection-abc",
        }
        assert module._split_choice_ok({"selected": selected, "split": split}) is True
    finally:
        module.REPO_ROOT = old_repo_root


def test_mcpb_stdio_smoke_checks_installed_registry_cache(tmp_path: Path) -> None:
    build_module = _load_build_module()
    install_module = _load_install_module()
    smoke_module = _load_smoke_module()
    package = build_module.build_mcpb(
        source=MCPB_SOURCE,
        output=tmp_path / "kcs-authoring-mvp-validator-control.mcpb",
    )
    install_dir = (
        tmp_path
        / "Claude Extensions"
        / "local.mcpb.kcs-authoring-mvp.kcs-authoring-mvp-validator-control"
    )
    install_module.install_mcpb(package=package, install_dir=install_dir)
    old_package = smoke_module.DEFAULT_MCPB_PACKAGE
    smoke_module.DEFAULT_MCPB_PACKAGE = package

    try:
        assert smoke_module._registry_cache_path(install_dir / "server" / "index.js")
        assert smoke_module._registry_cache_ok(install_dir / "server" / "index.js")
    finally:
        smoke_module.DEFAULT_MCPB_PACKAGE = old_package


def test_mcpb_stdio_smoke_rejects_stale_installed_registry_cache(
    tmp_path: Path,
) -> None:
    build_module = _load_build_module()
    install_module = _load_install_module()
    smoke_module = _load_smoke_module()
    package = build_module.build_mcpb(
        source=MCPB_SOURCE,
        output=tmp_path / "kcs-authoring-mvp-validator-control.mcpb",
    )
    install_dir = (
        tmp_path
        / "Claude Extensions"
        / "local.mcpb.kcs-authoring-mvp.kcs-authoring-mvp-validator-control"
    )
    install_module.install_mcpb(package=package, install_dir=install_dir)
    registry_path = tmp_path / "extensions-installations.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["extensions"][install_dir.name]["manifest"]["tools"][0][
        "description"
    ] = "Use with either ticket_ref or one structured item."
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    old_package = smoke_module.DEFAULT_MCPB_PACKAGE
    smoke_module.DEFAULT_MCPB_PACKAGE = package

    try:
        assert not smoke_module._registry_cache_ok(install_dir / "server" / "index.js")
    finally:
        smoke_module.DEFAULT_MCPB_PACKAGE = old_package


def test_mcpb_stdio_smoke_rejects_registry_cache_with_old_popup_contract(
    tmp_path: Path,
) -> None:
    build_module = _load_build_module()
    install_module = _load_install_module()
    smoke_module = _load_smoke_module()
    package = build_module.build_mcpb(
        source=MCPB_SOURCE,
        output=tmp_path / "kcs-authoring-mvp-validator-control.mcpb",
    )
    install_dir = (
        tmp_path
        / "Claude Extensions"
        / "local.mcpb.kcs-authoring-mvp.kcs-authoring-mvp-validator-control"
    )
    install_module.install_mcpb(package=package, install_dir=install_dir)
    registry_path = tmp_path / "extensions-installations.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["extensions"][install_dir.name]["manifest"]["tools"][0][
        "description"
    ] = (
        "Primary operator tool. Python owns semantic extraction. "
        "For chat attachments pass only approved_summary_text. "
        "Uses local reviewer bundle output. If the tool returns split_required, "
        "show the returned candidates in a native Claude Desktop choice popup."
    )
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    old_package = smoke_module.DEFAULT_MCPB_PACKAGE
    smoke_module.DEFAULT_MCPB_PACKAGE = package

    try:
        assert not smoke_module._registry_cache_ok(install_dir / "server" / "index.js")
    finally:
        smoke_module.DEFAULT_MCPB_PACKAGE = old_package


def test_mcpb_stdio_smoke_skips_registry_for_source_wrapper() -> None:
    module = _load_smoke_module()

    assert module._registry_cache_path(MCPB_SOURCE / "server" / "index.js") is None
    assert module._registry_cache_ok(MCPB_SOURCE / "server" / "index.js")


def test_claude_desktop_log_check_accepts_latest_thin_tool_surface(
    tmp_path: Path,
) -> None:
    module = _load_log_check_module()
    log = tmp_path / "mcp-server-KCS Authoring.log"
    latest_surface = {
        "id": 1,
        "result": {
            "tools": [
                {
                    "annotations": {
                        "destructiveHint": False,
                        "idempotentHint": False,
                        "openWorldHint": False,
                        "readOnlyHint": False,
                    },
                    "inputSchema": {
                        "properties": {
                            "clean_ticket_text": {},
                            "debug": {},
                            "ticket_ref": {},
                        }
                    },
                    "name": "kcs_register_clean_ticket",
                },
                {
                    "annotations": {
                        "destructiveHint": False,
                        "idempotentHint": False,
                        "openWorldHint": False,
                        "readOnlyHint": False,
                    },
                    "description": "Python owns semantic extraction",
                    "inputSchema": {
                        "properties": {
                            "approved_summary_text": {},
                            "debug": {},
                            "operator_selected_item_ref": {},
                            "operator_selection_ref": {},
                            "ticket_ref": {},
                        }
                    },
                    "name": "kcs_draft_article",
                },
                {
                    "annotations": {
                        "destructiveHint": False,
                        "idempotentHint": True,
                        "openWorldHint": False,
                        "readOnlyHint": True,
                    },
                    "inputSchema": {
                        "properties": {"semantic_review_ref": {}}
                    },
                    "name": "kcs_prepare_semantic_review",
                },
                {
                    "annotations": {
                        "destructiveHint": False,
                        "idempotentHint": False,
                        "openWorldHint": False,
                        "readOnlyHint": False,
                    },
                    "inputSchema": {
                        "properties": {
                            "candidate_semantic_extraction": {},
                            "semantic_review_ref": {},
                        }
                    },
                    "name": "kcs_submit_semantic_review",
                },
                {
                    "annotations": {
                        "destructiveHint": False,
                        "idempotentHint": True,
                        "openWorldHint": False,
                        "readOnlyHint": True,
                    },
                    "inputSchema": {"properties": {}},
                    "name": "support_get_behavior_instructions",
                },
            ]
        },
    }
    log.write_text(
        "\n".join(
            [
                (
                    '2026-06-18T22:32:52.901Z [KCS Authoring] [info] '
                    'Message from client: {"method":"initialize","params":{'
                    '"capabilities":{"extensions":{'
                    '"io.modelcontextprotocol/ui":{"mimeTypes":['
                    '"text/html;profile=mcp-app"]}}},'
                    '"clientInfo":{"name":"claude-ai","version":"0.1.0"},'
                    '"protocolVersion":"2025-11-25"},'
                    '"jsonrpc":"2.0","id":0}'
                ),
                (
                    '2026-06-18T20:23:38.460Z [KCS Authoring] [info] '
                    'Message from server: {"id":1,"result":{"tools":[{'
                    '"annotations":{"idempotentHint":true,"readOnlyHint":true},'
                    '"inputSchema":{"properties":{"item":{},'
                    '"item_candidates":{},"reference_article_html":{}}},'
                    '"name":"kcs_draft_article"}]}}'
                ),
                (
                    '2026-06-18T22:32:53.261Z [KCS Authoring] [info] '
                    f"Message from server: {json.dumps(latest_surface)}"
                ),
            ]
        ),
        encoding="utf-8",
    )

    report = module.check_log(log_path=log, max_bytes=10000)

    assert report["ok"] is True
    assert report["client_capabilities"] == {
        "elicitation_declared": False,
        "initialize_observed": True,
        "mcp_ui_extension_declared": True,
    }
    assert report["latest_initialize_at"] == "2026-06-18T22:32:52.901Z"
    assert report["latest_tools_list_at"] == "2026-06-18T22:32:53.261Z"
    assert all(report["checks"].values())


def test_claude_desktop_log_check_rejects_stale_tool_surface(tmp_path: Path) -> None:
    module = _load_log_check_module()
    log = tmp_path / "mcp-server-KCS Authoring.log"
    log.write_text(
        (
            '2026-06-18T20:23:38.460Z [KCS Authoring] [info] '
            'Message from server: {"id":1,"result":{"tools":[{'
            '"annotations":{"idempotentHint":true,"readOnlyHint":true},'
            '"inputSchema":{"properties":{"approved_summary_text":{},'
            '"item":{},"item_candidates":{},'
            '"reference_article_html":{}}},'
            '"name":"kcs_draft_article"}]}}'
        ),
        encoding="utf-8",
    )

    report = module.check_log(log_path=log, max_bytes=10000)

    assert report["ok"] is False
    assert report["checks"]["annotations_exact"] is False
    assert report["checks"]["draft_schema_exact"] is False
    assert report["checks"]["old_item_schema_absent"] is False
    assert report["checks"]["old_item_candidates_schema_absent"] is False
    assert report["checks"]["old_reference_article_html_absent"] is False


def test_claude_desktop_log_check_accepts_truncated_latest_tool_surface(
    tmp_path: Path,
) -> None:
    module = _load_log_check_module()
    log = tmp_path / "mcp-server-KCS Authoring.log"
    log.write_text(
        (
            '2026-06-20T06:33:03.146Z [KCS Authoring] [info] '
            'Message from server: {"id":1,"jsonrpc":"2.0","result":{"tools":[{'
            '"annotations":{"destructiveHint":false,"idempotentHint":false,'
            '"openWorldHint":false,"readOnlyHint":false},'
            '"description":"Register one approved sanitized support-ticket '
            'transcript as a configured clean ticket file...[4624 chars '
            'truncated]...sanitized ticket article drafting.",'
            '"inputSchema":{"additionalProperties":false,"properties":{},'
            '"required":[],"type":"object"},'
            '"name":"kcs_register_clean_ticket"}]}}'
        ),
        encoding="utf-8",
    )

    report = module.check_log(log_path=log, max_bytes=10000)

    assert report["ok"] is True
    assert report["checks"]["tool_surface_truncated"] is True
    assert report["checks"]["truncated_annotations_visible"] is True
    assert "tool_names_exact" not in report["checks"]
    assert "draft_schema_exact" not in report["checks"]


def test_claude_desktop_log_check_honors_since_timestamp(tmp_path: Path) -> None:
    module = _load_log_check_module()
    log = tmp_path / "mcp-server-KCS Authoring.log"
    log.write_text(
        (
            '2026-06-18T20:23:38.460Z [KCS Authoring] [info] '
            'Message from server: {"id":1,"result":{"tools":[{'
            '"annotations":{"idempotentHint":false,"readOnlyHint":false},'
            '"description":"Python owns semantic extraction",'
            '"inputSchema":{"properties":{"approved_summary_text":{},'
            '"operator_selected_item_ref":{},"operator_selection_ref":{}}},'
            '"name":"kcs_draft_article"}]}}'
        ),
        encoding="utf-8",
    )

    report = module.check_log(
        log_path=log,
        max_bytes=10000,
        since="2026-06-18T22:00:00Z",
    )

    assert report["ok"] is False
    assert report["error_code"] == "tools_list_not_found"


def test_claude_desktop_ui_prompt_smoke_accepts_single_draft_log() -> None:
    module = _load_ui_smoke_module()
    since = module.datetime.fromisoformat("2026-06-18T22:32:53+00:00")
    text = "\n".join(
        [
            (
                '2026-06-18T22:33:01.100Z [KCS Authoring] [info] '
                'Message from client: {"method":"tools/call","params":{'
                '"name":"kcs_draft_article","arguments":{'
                '"approved_summary_text":"Title: Monitoring graphs show no data"}}}'
            ),
            (
                '2026-06-18T22:33:03.200Z [KCS Authoring] [info] '
                'Message from server: {"id":4,"result":{"content":[{"text":'
                '"{\\"debug_code\\":\\"draft_only_reuse_search_missing\\",'
                '\\"schema_version\\":\\"kcs_mcp_tool_result_v1\\"}"}]}}'
            ),
        ]
    )

    report = module._report_from_log(
        text=text,
        prompt_kind="single",
        sent=True,
        since=since,
        log_path=Path("mcp-server-KCS Authoring.log"),
    )

    assert report["ok"] is True
    assert all(report["checks"].values())
    assert report["latest_log_timestamp"] == "2026-06-18T22:33:03.200Z"
    assert report["checks"]["terminal_result_observed"] is True
    assert report["draft_result_observed"] is True
    assert report["provider_unavailable_result_observed"] is False
    assert report["mcp_result_debug_codes"] == ["draft_only_reuse_search_missing"]


def test_claude_desktop_ui_prompt_smoke_accepts_prod_provider_unavailable() -> None:
    module = _load_ui_smoke_module()
    since = module.datetime.fromisoformat("2026-06-18T22:32:53+00:00")
    text = "\n".join(
        [
            (
                '2026-06-18T22:33:01.100Z [KCS Authoring] [info] '
                'Message from client: {"method":"tools/call","params":{'
                '"name":"kcs_draft_article","arguments":{'
                '"approved_summary_text":"Title: Monitoring graphs show no data"}}}'
            ),
            (
                '2026-06-18T22:33:03.200Z [KCS Authoring] [info] '
                'Message from server: {"id":4,"result":{"content":[{"text":'
                '"{\\"blockers\\":[\\"semantic_extraction_provider_unavailable\\"],'
                '\\"failure_stage\\":\\"semantic_extraction\\",'
                '\\"schema_version\\":\\"kcs_mcp_tool_result_v1\\"}"}]}}'
            ),
        ]
    )

    report = module._report_from_log(
        text=text,
        prompt_kind="raw-ticket",
        sent=True,
        since=since,
        log_path=Path("mcp-server-KCS Authoring.log"),
    )

    assert report["ok"] is True
    assert report["checks"]["terminal_result_observed"] is True
    assert report["draft_result_observed"] is False
    assert report["provider_unavailable_result_observed"] is True


def test_claude_desktop_ui_prompt_smoke_rejects_manual_fallback_after_blocker() -> None:
    module = _load_ui_smoke_module()
    since = module.datetime.fromisoformat("2026-06-18T22:32:53+00:00")
    text = "\n".join(
        [
            (
                '2026-06-18T22:33:01.100Z [KCS Authoring] [info] '
                'Message from client: {"method":"tools/call","params":{'
                '"name":"kcs_draft_article","arguments":{'
                '"approved_summary_text":"Title: Monitoring graphs show no data"}}}'
            ),
            (
                '2026-06-18T22:33:03.200Z [KCS Authoring] [info] '
                'Message from server: {"id":4,"result":{"content":[{"text":'
                '"{\\"blockers\\":[\\"semantic_extraction_provider_unavailable\\"],'
                '\\"schema_version\\":\\"kcs_mcp_tool_result_v1\\"}"}]}}'
            ),
        ]
    )
    web_text = (
        "2026-06-18T22:33:05.000Z [info] It looks like the KCS Authoring "
        "tool is not able to complete the draft right now. That said, I can "
        "draft a KCS-style knowledge base article for you directly based on "
        "the ticket."
    )

    report = module._report_from_log(
        text=text,
        web_text=web_text,
        prompt_kind="raw-ticket",
        sent=True,
        since=since,
        log_path=Path("mcp-server-KCS Authoring.log"),
    )

    assert report["ok"] is False
    assert report["checks"]["terminal_result_observed"] is True
    assert report["checks"]["manual_fallback_absent"] is False
    assert "manual_fallback_absent" in report["failed_checks"]


def test_claude_desktop_ui_prompt_smoke_ignores_stale_disconnect_before_call() -> None:
    module = _load_ui_smoke_module()
    since = module.datetime.fromisoformat("2026-06-18T22:32:53+00:00")
    text = "\n".join(
        [
            (
                "2026-06-18T22:33:00.100Z [KCS Authoring] [error] "
                "Server disconnected."
            ),
            (
                '2026-06-18T22:33:01.100Z [KCS Authoring] [info] '
                'Message from client: {"method":"tools/call","params":{'
                '"name":"kcs_draft_article","arguments":{'
                '"approved_summary_text":"# Customer Ticket Content"}}}'
            ),
            (
                '2026-06-18T22:33:03.200Z [KCS Authoring] [info] '
                'Message from server: {"id":4,"result":{"content":[{"text":'
                '"{\\"debug_code\\":\\"draft_only_reuse_search_missing\\",'
                '\\"recommended_action\\":\\"draft_only\\",'
                '\\"schema_version\\":\\"kcs_mcp_tool_result_v1\\"}"}]}}'
            ),
        ]
    )

    report = module._report_from_log(
        text=text,
        prompt_kind="raw-ticket",
        sent=True,
        since=since,
        log_path=Path("mcp-server-KCS Authoring.log"),
    )

    assert report["ok"] is True
    assert report["checks"]["timeout_or_disconnect_absent"] is True


def test_claude_desktop_ui_prompt_smoke_rejects_disconnect_after_call() -> None:
    module = _load_ui_smoke_module()
    since = module.datetime.fromisoformat("2026-06-18T22:32:53+00:00")
    text = "\n".join(
        [
            (
                '2026-06-18T22:33:01.100Z [KCS Authoring] [info] '
                'Message from client: {"method":"tools/call","params":{'
                '"name":"kcs_draft_article","arguments":{'
                '"approved_summary_text":"# Customer Ticket Content"}}}'
            ),
            (
                "2026-06-18T22:33:02.100Z [KCS Authoring] [error] "
                "Server disconnected."
            ),
        ]
    )

    report = module._report_from_log(
        text=text,
        prompt_kind="raw-ticket",
        sent=True,
        since=since,
        log_path=Path("mcp-server-KCS Authoring.log"),
    )

    assert report["ok"] is False
    assert report["checks"]["timeout_or_disconnect_absent"] is False
    assert "timeout_or_disconnect_absent" in report["failed_checks"]


def test_claude_desktop_ui_prompt_smoke_warns_on_disconnect_after_draft() -> None:
    module = _load_ui_smoke_module()
    since = module.datetime.fromisoformat("2026-06-18T22:32:53+00:00")
    text = "\n".join(
        [
            (
                '2026-06-18T22:33:01.100Z [KCS Authoring] [info] '
                'Message from client: {"method":"tools/call","params":{'
                '"name":"kcs_draft_article","arguments":{'
                '"approved_summary_text":"# Customer Ticket Content"}}}'
            ),
            (
                '2026-06-18T22:33:03.200Z [KCS Authoring] [info] '
                'Message from server: {"id":4,"result":{"content":[{"text":'
                '"{\\"debug_code\\":\\"draft_only_reuse_search_missing\\",'
                '\\"recommended_action\\":\\"draft_only\\",'
                '\\"schema_version\\":\\"kcs_mcp_tool_result_v1\\"}"}]}}'
            ),
            (
                "2026-06-18T22:39:34.888Z [KCS Authoring] [error] "
                "Server disconnected."
            ),
        ]
    )

    report = module._report_from_log(
        text=text,
        prompt_kind="raw-ticket",
        sent=True,
        since=since,
        log_path=Path("mcp-server-KCS Authoring.log"),
    )

    assert report["ok"] is True
    assert report["post_success_disconnect_observed"] is True
    assert report["checks"]["timeout_or_disconnect_absent"] is True
    assert report["attention"] == [
        "post_success_disconnect_observed",
        "draft_result_observed_before_disconnect",
    ]
    assert report["failed_checks"] == []
    assert report["next_steps"] == [
        "Treat the KCS draft tool call as passed for this log window.",
        (
            "Ignore the later MCP disconnect toast unless it happens before "
            "the next draft result."
        ),
    ]


def test_claude_desktop_ui_prompt_smoke_accepts_truncated_draft_status() -> None:
    module = _load_ui_smoke_module()
    since = module.datetime.fromisoformat("2026-06-18T22:32:53+00:00")
    text = "\n".join(
        [
            (
                '2026-06-18T22:33:01.100Z [KCS Authoring] [info] '
                'Message from client: {"method":"tools/call","params":{'
                '"name":"kcs_draft_article","arguments":{'
                '"approved_summary_text":"# Customer Ticket Content"}}}'
            ),
            (
                '2026-06-18T22:33:03.200Z [KCS Authoring] [info] '
                'Message from server: {"id":4,"result":{"content":[{"text":'
                '"{\\"debug_code\\":\\"draft_only_reuse_search_mi...[1680 chars '
                'truncated]...alse,\\"recommended_action\\":\\"draft_only\\",'
                '\\"schema_version\\":\\"kcs_mcp_tool_result_v1\\",'
                '\\"writes_files\\":true}"}]}}'
            ),
        ]
    )

    report = module._report_from_log(
        text=text,
        prompt_kind="raw-ticket",
        sent=True,
        since=since,
        log_path=Path("mcp-server-KCS Authoring.log"),
    )

    assert report["ok"] is True
    assert report["checks"]["terminal_result_observed"] is True
    assert report["draft_result_observed"] is True
    assert report["mcp_result_debug_codes"] == ["draft_only_reuse_search_mi"]


def test_claude_desktop_ui_prompt_smoke_reports_semantic_no_candidates() -> None:
    module = _load_ui_smoke_module()
    since = module.datetime.fromisoformat("2026-06-18T22:32:53+00:00")
    text = "\n".join(
        [
            (
                '2026-06-18T22:33:01.100Z [KCS Authoring] [info] '
                'Message from client: {"method":"tools/call","params":{'
                '"name":"kcs_draft_article","arguments":{'
                '"approved_summary_text":"# Customer Ticket Content"}}}'
            ),
            (
                '2026-06-18T22:33:03.200Z [KCS Authoring] [info] '
                'Message from server: {"id":4,"result":{"content":[{"text":'
                '"{\\"debug_code\\":\\"semantic_extraction_no_candidates\\",'
                '\\"failure_stage\\":\\"semantic_extraction\\",'
                '\\"schema_version\\":\\"kcs_mcp_tool_result_v1\\"}"}]}}'
            ),
        ]
    )

    report = module._report_from_log(
        text=text,
        prompt_kind="raw-ticket",
        sent=True,
        since=since,
        log_path=Path("mcp-server-KCS Authoring.log"),
    )

    assert report["ok"] is False
    assert report["failure_stage"] == "mcp_semantic_extraction_no_candidates"
    assert report["checks"]["semantic_no_candidates_absent"] is False
    assert report["mcp_result_debug_codes"] == ["semantic_extraction_no_candidates"]
    assert report["mcp_result_failure_stages"] == ["semantic_extraction"]


def test_claude_desktop_ui_prompt_smoke_rejects_old_arguments() -> None:
    module = _load_ui_smoke_module()
    since = module.datetime.fromisoformat("2026-06-18T22:32:53+00:00")
    text = (
        '2026-06-18T22:33:01.100Z [KCS Authoring] [info] '
        'Message from client: {"method":"tools/call","params":{'
        '"name":"kcs_draft_article","arguments":{'
        '"approved_summary_text":"safe","item_candidates":[]}}}'
    )

    report = module._report_from_log(
        text=text,
        prompt_kind="split",
        sent=True,
        since=since,
        log_path=Path("mcp-server-KCS Authoring.log"),
    )

    assert report["ok"] is False
    assert report["checks"]["old_structured_arguments_absent"] is False
    assert report["checks"]["split_result_observed"] is False


def test_claude_desktop_ui_prompt_smoke_ignores_output_candidates_as_old_args() -> None:
    module = _load_ui_smoke_module()
    since = module.datetime.fromisoformat("2026-06-18T22:32:53+00:00")
    text = "\n".join(
        [
            (
                '2026-06-18T22:33:01.100Z [KCS Authoring] [info] '
                'Message from client: {"method":"tools/call","params":{'
                '"name":"kcs_draft_article","arguments":{'
                '"approved_summary_text":"Item 1: A\\nItem 2: B"}}}'
            ),
            (
                '2026-06-18T22:33:03.200Z [KCS Authoring] [info] '
                'Message from server: {"id":4,"result":{"content":[{"text":'
                '"Multiple KCS article candidates were detected. '
                'Operator selection is required before drafting. '
                'submit_arguments: {\\"operator_selected_item_ref\\":'
                '\\"candidate-001\\"}. Do not draft manually. '
                '{\\"blockers\\":[\\"multiple_kcs_items_detected\\"],'
                '\\"item_candidates\\":[{\\"item_id\\":\\"A\\"}],'
                '\\"schema_version\\":\\"kcs_mcp_tool_result_v1\\"}"}]}}'
            ),
        ]
    )

    report = module._report_from_log(
        text=text,
        prompt_kind="split",
        sent=True,
        since=since,
        log_path=Path("mcp-server-KCS Authoring.log"),
    )

    assert report["ok"] is True
    assert report["checks"]["old_structured_arguments_absent"] is True
    assert report["checks"]["split_result_observed"] is True
    assert report["checks"]["split_fallback_text_observed"] is True
    assert "selected_call_uses_refs_only" not in report["checks"]


def test_claude_desktop_ui_prompt_smoke_requires_split_fallback_text() -> None:
    module = _load_ui_smoke_module()
    since = module.datetime.fromisoformat("2026-06-18T22:32:53+00:00")
    text = "\n".join(
        [
            (
                '2026-06-18T22:33:01.100Z [KCS Authoring] [info] '
                'Message from client: {"method":"tools/call","params":{'
                '"name":"kcs_draft_article","arguments":{'
                '"approved_summary_text":"Item 1: A\\nItem 2: B"}}}'
            ),
            (
                '2026-06-18T22:33:03.200Z [KCS Authoring] [info] '
                'Message from server: {"id":4,"result":{"content":[{"text":'
                '"{\\"debug_code\\":\\"multiple_kcs_items_detected\\",'
                '\\"schema_version\\":\\"kcs_mcp_tool_result_v1\\"}"}]}}'
            ),
        ]
    )

    report = module._report_from_log(
        text=text,
        prompt_kind="split",
        sent=True,
        since=since,
        log_path=Path("mcp-server-KCS Authoring.log"),
    )

    assert report["ok"] is False
    assert report["failure_stage"] == "expected_split_fallback_text_not_observed"
    assert report["checks"]["split_result_observed"] is True
    assert report["checks"]["split_fallback_text_observed"] is False


def test_claude_desktop_ui_prompt_smoke_accepts_split_selected_continuation() -> None:
    module = _load_ui_smoke_module()
    since = module.datetime.fromisoformat("2026-06-18T22:32:53+00:00")
    text = "\n".join(
        [
            (
                '2026-06-18T22:33:01.100Z [KCS Authoring] [info] '
                'Message from client: {"method":"tools/call","params":{'
                '"name":"kcs_draft_article","arguments":{'
                '"approved_summary_text":"Item 1: A\\nItem 2: B"}}}'
            ),
            (
                '2026-06-18T22:33:03.200Z [KCS Authoring] [info] '
                'Message from server: {"id":4,"result":{"content":[{"text":'
                '"Multiple KCS article candidates were detected. '
                'Operator selection is required before drafting. '
                'submit_arguments: {\\"operator_selected_item_ref\\":'
                '\\"candidate-002\\"}. Do not draft manually. '
                '{\\"debug_code\\":\\"multiple_kcs_items_detected\\",'
                '\\"operator_selection_ref\\":\\"selection-opaque\\",'
                '\\"schema_version\\":\\"kcs_mcp_tool_result_v1\\"}"}]}}'
            ),
            (
                '2026-06-18T22:33:10.100Z [KCS Authoring] [info] '
                'Message from client: {"method":"tools/call","params":{'
                '"name":"kcs_draft_article","arguments":{'
                '"operator_selection_ref":"selection-opaque",'
                '"operator_selected_item_ref":"candidate-002"}}}'
            ),
            (
                '2026-06-18T22:33:12.200Z [KCS Authoring] [info] '
                'Message from server: {"id":5,"result":{"content":[{"text":'
                '"{\\"recommended_action\\":\\"draft_only\\",'
                '\\"schema_version\\":\\"kcs_mcp_tool_result_v1\\",'
                '\\"writes_files\\":true}"}]}}'
            ),
        ]
    )

    report = module._report_from_log(
        text=text,
        prompt_kind="split",
        sent=True,
        since=since,
        log_path=Path("mcp-server-KCS Authoring.log"),
    )

    assert report["ok"] is True
    assert report["checks"]["split_result_observed"] is True
    assert report["checks"]["split_fallback_text_observed"] is True
    assert report["checks"]["selected_call_uses_refs_only"] is True
    assert report["checks"]["selected_draft_result_observed"] is True


def test_claude_desktop_ui_prompt_smoke_dry_run_is_not_success() -> None:
    module = _load_ui_smoke_module()
    since = module.datetime.fromisoformat("2026-06-18T22:32:53+00:00")

    report = module._report_from_log(
        text="",
        prompt_kind="single",
        sent=False,
        since=since,
        log_path=Path("mcp-server-KCS Authoring.log"),
    )

    assert report["ok"] is False
    assert report["checks"]["prompt_sent"] is False


def test_claude_desktop_ui_prompt_smoke_parses_since_timestamp() -> None:
    module = _load_ui_smoke_module()

    parsed = module._parse_since_arg("2026-06-18T22:32:53Z")

    assert parsed.isoformat() == "2026-06-18T22:32:53+00:00"


def test_claude_desktop_ui_prompt_smoke_parses_frontmost_error() -> None:
    module = _load_ui_smoke_module()

    app_name = module._frontmost_app_from_stderr(
        'execution error: frontmost_app=Google Chrome (-2700)\n'
    )

    assert app_name == "Google Chrome (-2700)"


def test_claude_desktop_ui_prompt_smoke_captures_failure_screenshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_ui_smoke_module()
    screenshot = tmp_path / "failure.png"

    def fake_run(*args, **kwargs):
        screenshot.write_bytes(b"png")
        return subprocess.CompletedProcess(args=args[0], returncode=0)

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    captured = module._maybe_capture_failure_screenshot(
        enabled=True,
        path=screenshot,
    )

    assert captured == str(screenshot)


def test_claude_desktop_ui_prompt_smoke_detects_codex_accessibility_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_ui_smoke_module()

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="codex_accessibility_permission_required\n",
        )

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert (
        module._accessibility_warning_code(timeout_seconds=1)
        == "codex_accessibility_permission_required"
    )


def test_claude_desktop_ui_prompt_smoke_accepts_no_accessibility_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_ui_smoke_module()

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert module._accessibility_warning_code(timeout_seconds=1) is None


def test_claude_desktop_ui_prompt_smoke_reports_accessibility_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_ui_smoke_module()

    monkeypatch.setattr(
        module,
        "_accessibility_warning_code",
        lambda *, timeout_seconds: "codex_accessibility_permission_required",
    )

    report = module._accessibility_preflight_report(timeout_seconds=1)

    assert report == {
        "checks": {
            "codex_accessibility_permission_available": False,
        },
        "ok": False,
        "schema_version": module.SCHEMA_VERSION,
        "send_error_code": "codex_accessibility_permission_required",
    }


def test_claude_desktop_ui_prompt_smoke_prints_manual_prompt_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_ui_smoke_module()
    prompt_path = tmp_path / "manual-prompt.txt"

    class FixedDatetime(module.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls.fromisoformat("2026-06-18T23:45:00+00:00")

    monkeypatch.setattr(module, "datetime", FixedDatetime)
    monkeypatch.setattr(
        module,
        "_write_clipboard_text",
        lambda text: text.startswith("draft"),
    )

    report = module._manual_prompt_report(
        prompt_kind="split",
        prompt_path=prompt_path,
        copy_to_clipboard=True,
    )

    assert report["prompt_kind"] == "split"
    assert report["since"] == "2026-06-18T23:45:00.000Z"
    assert report["manual_prompt_path"] == str(prompt_path)
    assert report["prompt_copied_to_clipboard"] is True
    assert "Item 1:" in report["prompt_text"]
    assert "Item 2:" in report["prompt_text"]
    assert prompt_path.read_text(encoding="utf-8") == report["prompt_text"]
    assert report["follow_up_command"] == (
        "uv run python scripts/smoke_claude_desktop_ui_prompt.py "
        "--since 2026-06-18T23:45:00Z --assume-sent --prompt-kind split"
    )


def test_claude_desktop_ui_prompt_smoke_supports_narrative_prompt_kind(
    tmp_path: Path,
) -> None:
    module = _load_ui_smoke_module()
    prompt_path = tmp_path / "manual-prompt.txt"

    report = module._manual_prompt_report(
        prompt_kind="narrative",
        prompt_path=prompt_path,
    )

    assert report["prompt_kind"] == "narrative"
    assert "Summary:" in report["prompt_text"]
    assert "Investigation:" in report["prompt_text"]
    assert "Resolution:" in report["prompt_text"]
    assert "02rrdtool-monitoring.conf" in report["prompt_text"]
    assert prompt_path.read_text(encoding="utf-8") == report["prompt_text"]


def test_claude_desktop_ui_prompt_smoke_supports_raw_ticket_prompt_kind(
    tmp_path: Path,
) -> None:
    module = _load_ui_smoke_module()
    prompt_path = tmp_path / "manual-prompt.txt"

    report = module._manual_prompt_report(
        prompt_kind="raw-ticket",
        prompt_path=prompt_path,
    )

    assert report["prompt_kind"] == "raw-ticket"
    assert "# Customer Ticket Content" in report["prompt_text"]
    assert "02rrdtool-monitoring.conf" in report["prompt_text"]
    assert "sw-collectd service was restarted" in report["prompt_text"]
    assert prompt_path.read_text(encoding="utf-8") == report["prompt_text"]


def test_build_script_rejects_symlinked_files(tmp_path: Path) -> None:
    module = _load_build_module()
    source = _copy_mcpb_source(tmp_path)
    private_file = tmp_path / "private-token.txt"
    private_file.write_text("token=SECRET", encoding="utf-8")
    (source / "server" / "leak.txt").symlink_to(private_file)

    try:
        module.build_mcpb(source=source, output=tmp_path / "out.mcpb")
    except SystemExit as exc:
        assert "leak.txt" in str(exc)
        assert "SECRET" not in str(exc)
    else:  # pragma: no cover - failure path for assertion clarity
        raise AssertionError("expected symlinked MCPB source to fail closed")


def test_build_script_rejects_unexpected_extra_files(tmp_path: Path) -> None:
    module = _load_build_module()
    source = _copy_mcpb_source(tmp_path)
    (source / ".env").write_text("TOKEN=SECRET", encoding="utf-8")

    try:
        module.build_mcpb(source=source, output=tmp_path / "out.mcpb")
    except SystemExit as exc:
        assert ".env" in str(exc)
        assert "SECRET" not in str(exc)
    else:  # pragma: no cover - failure path for assertion clarity
        raise AssertionError("expected unexpected MCPB source file to fail closed")


def test_install_script_installs_built_mcpb(tmp_path: Path) -> None:
    build_module = _load_build_module()
    install_module = _load_install_module()
    package = build_module.build_mcpb(
        source=MCPB_SOURCE,
        output=tmp_path / "kcs-authoring-mvp-validator-control.mcpb",
    )
    install_dir = (
        tmp_path
        / "Claude Extensions"
        / "local.mcpb.kcs-authoring-mvp.kcs-authoring-mvp-validator-control"
    )

    installed = install_module.install_mcpb(
        package=package,
        install_dir=install_dir,
    )

    assert installed == install_dir.resolve()
    assert {
        path.relative_to(install_dir).as_posix()
        for path in install_dir.rglob("*")
        if path.is_file()
    } == {
        path.as_posix() for path in build_module.expected_bundle_files()
    }
    registry_path = tmp_path / "extensions-installations.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    entry = registry["extensions"][install_dir.name]
    assert entry["id"] == install_dir.name
    assert entry["hash"] == sha256(package.read_bytes()).hexdigest()
    assert entry["source"] == "local"
    assert entry["signatureInfo"] == {"status": "unsigned"}
    draft_tool = next(
        tool
        for tool in entry["manifest"]["tools"]
        if tool["name"] == "kcs_draft_article"
    )
    assert "approved_summary_text" in draft_tool["description"]
    assert "structured item" not in draft_tool["description"]


def test_install_script_replaces_stale_claude_registry_manifest(
    tmp_path: Path,
) -> None:
    build_module = _load_build_module()
    install_module = _load_install_module()
    package = build_module.build_mcpb(
        source=MCPB_SOURCE,
        output=tmp_path / "kcs-authoring-mvp-validator-control.mcpb",
    )
    install_dir = (
        tmp_path
        / "Claude Extensions"
        / "local.mcpb.kcs-authoring-mvp.kcs-authoring-mvp-validator-control"
    )
    registry_path = tmp_path / "extensions-installations.json"
    registry_path.write_text(
        json.dumps(
            {
                "extensions": {
                    install_dir.name: {
                        "id": install_dir.name,
                        "version": "0.0.1",
                        "hash": "stale",
                        "installedAt": "2026-01-01T00:00:00.000Z",
                        "manifest": {
                            "tools": [
                                {
                                    "name": "kcs_draft_article",
                                    "description": "Use one structured item.",
                                }
                            ]
                        },
                        "signatureInfo": {"status": "unsigned"},
                        "source": "local",
                    },
                    "unrelated.extension": {
                        "id": "unrelated.extension",
                        "manifest": {"name": "keep-me"},
                    },
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    install_module.install_mcpb(
        package=package,
        install_dir=install_dir,
        installations_file=registry_path,
    )

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    entry = registry["extensions"][install_dir.name]
    assert entry["hash"] == sha256(package.read_bytes()).hexdigest()
    assert entry["manifest"]["long_description"] == json.loads(
        (MCPB_SOURCE / "manifest.json").read_text(encoding="utf-8")
    )["long_description"]
    draft_tool = next(
        tool
        for tool in entry["manifest"]["tools"]
        if tool["name"] == "kcs_draft_article"
    )
    description = draft_tool["description"]
    assert "ticket_ref" in description
    assert "approved_summary_text" in description
    assert "structured item" not in description
    unrelated = registry["extensions"]["unrelated.extension"]
    assert unrelated["manifest"]["name"] == "keep-me"
    backups = sorted(tmp_path.glob("extensions-installations.json.codex-backup-*"))
    assert len(backups) == 1
    assert "Use one structured item." in backups[0].read_text(encoding="utf-8")


def test_install_script_rejects_mcpb_with_unexpected_files(tmp_path: Path) -> None:
    install_module = _load_install_module()
    package = tmp_path / "bad.mcpb"
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.md", "safe")
        archive.writestr("manifest.json", "{}")
        archive.writestr("server/index.js", "console.log('safe')")
        archive.writestr(".env", "TOKEN=SECRET")

    with pytest.raises(SystemExit) as exc_info:
        install_module.install_mcpb(
            package=package,
            install_dir=tmp_path / "extension",
        )

    assert "unexpected files" in str(exc_info.value)
    assert "SECRET" not in str(exc_info.value)
