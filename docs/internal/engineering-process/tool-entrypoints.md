# Local Tool Entrypoints

Status: authoritative KCS-14 Slice 2 tool-surface specification.

This document defines the supported local commands for repository engineering
work. It is an engineering workflow surface, not a runtime product contract.
Use exact commands from this file instead of inventing ad hoc shell workflows.

## Ownership

- `AGENTS.md` owns the compact entrypoint index.
- This file owns detailed command usage, command classification, output budget
  expectations, and links to deeper procedures.
- `scripts/` and package console entrypoints own executable behavior.
- `tests/` owns executable behavior and policy checks.
- `README.md` may keep operator-facing Desktop/MCPB procedures; this file
  references those procedures instead of duplicating all caveats.

## Output Budget

Prefer compact terminal output in chat:

- command;
- pass/fail result;
- failing test name or value-safe debug code;
- path to logs/artifacts when needed.

Do not paste full logs, full reviewer bundles, raw tickets, provider payloads,
or full HTML into chat. Write large output to local artifacts and summarize the
relevant lines.

## Deterministic Checks

Use these before commits when relevant to the touched files.

| Task | Command | Classification | Notes |
| --- | --- | --- | --- |
| Policy docs check | `uv run pytest tests/policy/test_kcs14_docs_policy.py -q` | deterministic | Required for KCS-14 process/doc changes. |
| Review protocol and promotion check | `uv run pytest tests/policy/test_review_context_policy.py -q` | deterministic | Required for KCS-14 review, promotion, closeout-shape, or review-packet protocol changes. |
| Code-review graph policy check | `uv run pytest tests/policy/test_code_review_graph_policy.py -q` | deterministic | Required for code-map, graph hash, ownership-node, or refactor-boundary changes. |
| KCS-14 freeze/snapshot check | `uv run pytest tests/policy/test_kcs14_freeze_snapshots.py -q` | deterministic | Required before and after Slice 6 refactor batches. |
| Narrow pytest | `uv run pytest <test-path> -q` | deterministic | Use the narrowest relevant test path for touched behavior. |
| Full local pytest | `uv run pytest -q` | deterministic | Use before broad behavior or refactor changes when practical. |
| Ruff check | `uv run ruff check <path>` | deterministic | Use for touched Python files. |
| Diff whitespace check | `git diff --check` | deterministic | Use for unstaged working-tree diff. |
| Staged whitespace check | `git diff --cached --check` | deterministic | Use before commit. |
| Staged file review | `git diff --cached --name-status` | deterministic | Confirms the commit contains only intended files. |
| Complexity measurement | `uv run --extra dev python scripts/measure_complexity.py --paths src tests scripts --baseline docs/internal/engineering-process/kcs-14-complexity-baseline.json` | deterministic | Advisory sensor for refactor closeouts. It fails only if the measurement command crashes; values do not block commits. |

## Deterministic Tool Help / Liveness

These checks prove the local entrypoint still imports and exposes help text.
They do not prove full workflow behavior.

| Tool | Command | Classification | Notes |
| --- | --- | --- | --- |
| KCS core CLI | `uv run kcs-core --help` | deterministic | Console entrypoint from `pyproject.toml`. |
| Smoke accounting CLI | `uv run kcs-smoke-account --help` | deterministic | Console entrypoint from `pyproject.toml`. |
| MCPB build script | `uv run python scripts/build_kcs_mcpb.py --help` | deterministic | Help-only check; does not build package. |
| Cowork plugin build script | `uv run python scripts/build_kcs_cowork_plugin.py --help` | deterministic | Help-only check; does not build package. |
| MCPB stdio smoke script | `uv run python scripts/smoke_kcs_mcpb_stdio.py --help` | deterministic | Help-only check; actual smoke is a separate validation step. |
| Desktop log checker | `uv run python scripts/check_claude_kcs_desktop_log.py --help` | deterministic | Help-only check; actual log check needs local Desktop logs. |
| Desktop UI smoke script | `uv run python scripts/smoke_claude_desktop_ui_prompt.py --help` | deterministic | Help-only check; GUI send is manual/UI. |
| Complexity measurement | `uv run --extra dev python scripts/measure_complexity.py --help` | deterministic | Help-only check; actual measurement is advisory and listed above. |

## Desktop / MCPB Validation

Use these when MCPB, Desktop adapter, or operator-surface behavior changes.
See `README.md` for operator-facing caveats and manual Desktop steps.

| Task | Command | Classification | Notes |
| --- | --- | --- | --- |
| Build MCPB package | `uv run python scripts/build_kcs_mcpb.py` | deterministic | Writes build output under ignored `dist/`. |
| Install local MCPB package | `uv run python scripts/install_kcs_mcpb.py` | manual/local-side-effect | Writes to Claude Desktop extension locations. |
| Run source/installed stdio smoke | `uv run python scripts/smoke_kcs_mcpb_stdio.py` | deterministic-with-local-runtime | Requires local Node/uv wrapper availability. |
| Check Desktop MCP logs | `uv run python scripts/check_claude_kcs_desktop_log.py` | manual/local-state | Requires local Claude Desktop log state. |
| Check macOS GUI accessibility | `uv run python scripts/smoke_claude_desktop_ui_prompt.py --check-accessibility` | manual/UI | Checks local GUI permission only. |
| Print manual Desktop prompt | `uv run python scripts/smoke_claude_desktop_ui_prompt.py --print-manual-prompt --prompt-kind raw-ticket` | manual/UI | Produces a synthetic prompt for manual Desktop send. |
| Send Desktop UI smoke | `uv run python scripts/smoke_claude_desktop_ui_prompt.py --send --prompt-kind single` | manual/UI | Uses macOS GUI automation and may be rate-limited. |

## Artifact Rules

- Generated build outputs stay in ignored build/dist paths.
- Runtime reviewer bundles stay local and uncommitted.
- Raw tickets, private logs, provider payloads, credentials, and local debug
  artifacts must not be committed.
- Commit only synthetic or approved sanitized fixtures that pass the
  data-handling baseline.

## Later Machine-Readable Surface

Once the documented command surface proves stable, selected parts may move to a
machine-readable registry or wrapper CLI. This readable document remains the
human/agent contract and explains when commands apply, what they prove, manual
caveats, and output-budget rules.
