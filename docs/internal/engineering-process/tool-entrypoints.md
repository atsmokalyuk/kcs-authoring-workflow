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
| Pre-model input adequacy diagnostic | `uv run pytest tests/kcs_adapters/test_semantic_review_input_adequacy.py --runxfail -q --tb=short` | deterministic-diagnostic | Expected to fail until the tracked strict-xfail representation invariants are satisfied. This is a pre-model measurement, not a normal green gate or runtime contract claim. |
| Full local pytest | `uv run pytest -q` | deterministic | Use before broad behavior or refactor changes when practical. |
| Ruff check | `uv run ruff check <path>` | deterministic | Use for touched Python files. |
| Diff whitespace check | `git diff --check` | deterministic | Use for unstaged working-tree diff. |
| Staged whitespace check | `git diff --cached --check` | deterministic | Use before commit. |
| Staged file review | `git diff --cached --name-status` | deterministic | Confirms the commit contains only intended files. |
| Complexity measurement | `uv run --extra dev python scripts/measure_complexity.py --paths src tests scripts` | deterministic | Optional on-demand advisory sensor. Generated snapshots are not tracked; values do not block commits. |

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
| Semantic projection rebaseline | `uv run python scripts/rebaseline_semantic_issue_projection.py --help` | deterministic | Help-only check; model execution and response capture remain manual/local-state. |
| Langfuse synthetic rebaseline export | `uv run python scripts/kcs14_langfuse_rebaseline.py --help` | deterministic | Help-only check; export requires the separately managed local Langfuse service and pinned SDK command below. |
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

## Semantic Projection Rebaseline

Use this local-only harness for the KCS-14.5 M2 model/client matrix. It prepares
fixed synthetic prompts, validates an exact saved JSON response through the M1
parser and M2 Python projection, and aggregates value-safe run records. It does
not call a model, add an MCP tool, or change the active Desktop route.

| Task | Command | Classification | Notes |
| --- | --- | --- | --- |
| Prepare fixed synthetic prompt | `uv run python scripts/rebaseline_semantic_issue_projection.py prepare --scenario <scenario-id> --output <local-prompt-path>` | manual/local-state | Store prompts outside tracked paths. Allowed scenarios are listed by `--help`. |
| Evaluate saved model response | `uv run python scripts/rebaseline_semantic_issue_projection.py evaluate --scenario <scenario-id> --response <local-response.json> --model-identity <value-safe-id> --client-identity <value-safe-id> --package-sha256 <sha256> --system-prompt-sha256 <sha256> --run-index <n>` | manual/local-state | Emits counts, hashes, identities, and codes only. Redirect output to an ignored local record. |
| Summarize rebaseline records | `uv run python scripts/rebaseline_semantic_issue_projection.py summarize <local-run-record.json>...` | deterministic | Aggregates already value-safe records; does not read model response text. |

For the current model, run every fixed scenario three times with the same
package and system-prompt identities. Repeat with the previous model only when
it remains selectable. Record unavailability instead of reconstructing old
behavior from screenshots or memory. These records are M2 review evidence;
Desktop UI interpretation remains a separate manual smoke gate.

## Local Langfuse Synthetic Rebaseline

LF-1 exports one already value-safe semantic-projection run record to the
loopback-only Langfuse service. It records metadata spans only. It does not
capture prompts, model responses, ticket text, excerpts, candidate titles,
reviewer bundles, Desktop logs, or runtime tool inputs and outputs.

| Task | Command | Classification | Notes |
| --- | --- | --- | --- |
| Export one synthetic record | `uv run --python 3.11 --with langfuse==4.7.0 python scripts/kcs14_langfuse_rebaseline.py --record <value-safe-record.json> --profile <control-surface-profile.json> [--runtime-outcome <runtime-outcome.json>]` | manual/local-state | Requires `LANGFUSE_BASE_URL`, `LANGFUSE_PUBLIC_KEY`, and `LANGFUSE_SECRET_KEY`. The optional closed runtime outcome adds M3 progress metadata without raw workflow content. The URL must be explicit loopback with a port. |
| Validate LF-1 adapter with pinned SDK | `uv run --python 3.11 --extra dev --with langfuse==4.7.0 python -m pytest tests/kcs_adapters/test_kcs14_langfuse_rebaseline.py tests/kcs_adapters/test_semantic_projection_rebaseline.py -q` | deterministic-with-local-dependency | Uses an isolated tracer provider and verifies that no input/output attributes are emitted. |

Use a local ignored profile derived from
`evals/kcs14_langfuse_control_surface_profile.example.json`. Do not source the
Langfuse Compose `.env` as a shell script; map only the required project keys
into the three SDK environment variables without printing them. A trace marked
`comparable=false` proves only that the observability path works. It is not
model-version comparison evidence.

For installed M3 canaries, derive an ignored runtime outcome from
`evals/kcs14_langfuse_runtime_outcome.example.json`. Use the exact milestone
sequence `post_kcs14_legacy_baseline`, `m3_medium`, `m3_continuation`, then
`m3_complex`. Require `N=3` comparable passing runs for `m3_medium`, then
`N=3` comparable passing runs with retryable-blocker continuation for
`m3_continuation`. Do not start `m3_complex` until both stages are stable.
Compare only runs with the same scenario and control-surface identity hashes.
The exporter rejects a runtime outcome when the profile is not comparable.

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
