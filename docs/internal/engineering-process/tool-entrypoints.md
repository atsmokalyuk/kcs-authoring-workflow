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
| Engineering process docs check | `uv run pytest tests/policy/test_engineering_process_docs_policy.py -q` | deterministic | Required for tracked engineering-process and policy-document changes. |
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
| Controlled authoring CLI | `uv run kcs-controlled-draft --help` | deterministic | Help-only check for the direct operator-controlled comparison skeleton. |
| Smoke accounting CLI | `uv run kcs-smoke-account --help` | deterministic | Console entrypoint from `pyproject.toml`. |
| MCPB build script | `uv run python scripts/build_kcs_mcpb.py --help` | deterministic | Help-only check; does not build package. |
| Cowork plugin build script | `uv run python scripts/build_kcs_cowork_plugin.py --help` | deterministic | Help-only check; does not build package. |
| MCPB stdio smoke script | `uv run python scripts/smoke_kcs_mcpb_stdio.py --help` | deterministic | Help-only check; actual smoke is a separate validation step. |
| Desktop log checker | `uv run python scripts/check_claude_kcs_desktop_log.py --help` | deterministic | Help-only check; actual log check needs local Desktop logs. |
| Desktop UI smoke script | `uv run python scripts/smoke_claude_desktop_ui_prompt.py --help` | deterministic | Help-only check; prompt print/send fails closed when source, built package, installed files, or Desktop registry identity is stale. GUI send remains manual/UI. |
| Semantic projection rebaseline | `uv run python scripts/rebaseline_semantic_issue_projection.py --help` | deterministic | Help-only check; model execution and response capture remain manual/local-state. |
| Langfuse synthetic rebaseline export | `uv run python scripts/kcs14_langfuse_rebaseline.py --help` | deterministic | Help-only check; export requires the separately managed local Langfuse service and pinned SDK command below. |
| Langfuse live draft-run export | `uv run python scripts/kcs14_langfuse_draft_run.py --help` | deterministic | Help-only check; reads only a closed value-safe local run report. Optional Desktop-log classification stays local. |
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
| Print manual Desktop prompt | `uv run python scripts/smoke_claude_desktop_ui_prompt.py --print-manual-prompt --prompt-kind raw-ticket` | manual/UI | Produces a synthetic prompt only after static installed-artifact identity and live Desktop/RAG exact-capability preflights pass. |
| Send Desktop UI smoke | `uv run python scripts/smoke_claude_desktop_ui_prompt.py --send --prompt-kind single` | manual/UI | Uses macOS GUI automation and may be rate-limited; fails before send when installed-artifact identity, Desktop reload, or exact live RAG capability is unproven. |

Treat `installed_artifact_identity_stale` and `live_runtime_preflight_failed`
as autonomous Delivery/preflight corrections: rebuild/reinstall through the
supported installer, reload Claude Desktop, verify the exact required
capability on the active dependency instance, rerun the installed stdio smoke,
and only then expose a prompt to the operator. Static artifact identity is not
reported as complete runtime provenance.

## Controlled Authoring Skeleton

Use this entrypoint only with an existing approved local `ticket_ref`:

```text
uv run kcs-controlled-draft <ticket_ref>
```

Classification: manual/local-state with deterministic entry and interactive
operator confirmation.

The command creates the existing Desktop adapter and approved local public RAG
provider in one process, calls the draft comparison gate directly, displays
only bounded accepted facts and eligible public article excerpts, and then
reads one closed-enum outcome from the local terminal menu. It has no
`--outcome` argument: the choice is collected only after the comparison is
shown. `reuse` and `update` additionally require selection of one displayed
article. Normal execution requires interactive stdin and stdout before the
adapter is created; piped or redirected outcome input fails closed.

Use the write-incapable first-transition smoke when only live provider
feasibility is required:

```text
uv run kcs-controlled-draft --preflight <ticket_ref>
```

Preflight directly collects and renders the comparison, then exits without
reading or submitting an outcome.

The first workflow result must be `reuse_comparison_required` or fail-closed
`reuse_comparison_blocked`. A draft, reviewer bundle, file write, or unexpected
result before the menu is structurally unavailable through the controller's
comparison-only begin port and is also treated as an invariant failure. Only
operator-confirmed `none_fit` may continue into the existing reviewer-only
authoring path.

This is an enforcement skeleton for KCS-15.2b2, not the final Desktop UX.
Generic Claude chat remains model-routed and is outside this deterministic
entrypoint claim.

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

## Local Langfuse Live Draft-Run Accounting

Live accounting is an optional auxiliary adapter around the existing Desktop
MCP dispatch boundary. It is disabled unless both
`KCS_DRAFT_RUN_ACCOUNTING=local-json` and `KCS_DRAFT_RUN_REPORT_DIR` are set.
Use an ignored local directory such as `.runtime/kcs-draft-runs`. The runtime
checkpoints counts, closed codes, durations, byte sizes, and a random
correlation hash only. Sink failure is ignored and must not alter authoring.
The environment-created file sink uses a bounded non-blocking background queue,
so Desktop tool responses do not wait for local filesystem persistence. Under
sustained queue pressure an older checkpoint may be replaced by a newer one.

The external exporter validates the exact report schema before constructing
Langfuse observations. It never sends tool arguments/results or Desktop log
text. `--desktop-log` must point to a run-scoped Desktop log capture and scans
only a bounded local tail for an allowlisted Claude Desktop Free quota message;
generic limit text is not sufficient. `--classified-output` can persist the
resulting value-safe closed report at an operator-selected ignored path.

| Task | Command | Classification | Notes |
| --- | --- | --- | --- |
| Enable local report checkpoints | Source/dev: `KCS_DRAFT_RUN_ACCOUNTING=local-json KCS_DRAFT_RUN_REPORT_DIR=.runtime/kcs-draft-runs uv run kcs-desktop-mcp`. Installed MCPB: select the optional **Draft run accounting directory** extension setting. | manual/local-state | Changes only auxiliary local reporting. Selecting the installed-extension directory enables `local-json` mode inside the wrapper; leaving it unset preserves normal authoring. Langfuse and its SDK are not required. |
| Export one live run | `uv run --python 3.11 --with langfuse==4.7.0 python scripts/kcs14_langfuse_draft_run.py --report <value-safe-report.json> [--desktop-log <local-desktop-log>] [--classified-output <ignored-classified-report.json>] [--model-identity <safe-id>] [--client-identity <safe-id>]` | manual/local-state | Requires the three loopback Langfuse environment values. Desktop logs are read locally and their contents are never included in metadata. Optional model/client identities are exported only as SHA-256 values. |
| Validate live accounting and exporter | `uv run --extra dev pytest tests/kcs_adapters/test_draft_run_accounting.py tests/kcs_adapters/test_kcs14_langfuse_draft_run.py -q` | deterministic | Covers fail-open equivalence, strict field validation, privacy canaries, and host-quota classification. |

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
