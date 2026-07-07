# KCS-14 Slice 6 Batch 3 Desktop UI Smoke Observations

Status: ready for staged-diff review.

## Objective

Continue the `smoke_log_tooling` refactor with a narrow batch focused on
Claude Desktop UI smoke report internals.

Target:

```text
scripts/smoke_claude_desktop_ui_prompt.py
```

## Boundary Questions

What complexity are we hiding?

- Derived observations from MCP server logs and Claude Desktop web logs used
  to build the UI smoke report.

What should this module not know?

- KCS action decisions, packet validation internals, provider output
  validation, reviewer bundle content, raw ticket storage, or article
  rendering rules.

What input is allowed?

- Local Claude Desktop MCP server log text, Claude Desktop web log text,
  prompt kind, timestamp boundary, and value-safe log file names.

What input is forbidden?

- Committed raw logs, full private transcript bodies, provider payload bodies,
  reviewer bundle bodies, credentials, and private local artifacts.

What output contract is stable?

- `_report_from_log()` report keys remain stable.
- CLI arguments and exit codes remain stable.
- `checks`, `failed_checks`, `failure_stage`, attention, next steps, debug
  code lists, and value-safe file-name metadata remain stable.

What failure mode must be explicit?

- Missing prompt send evidence, completion errors, approval-gate stalls, MCP
  call/result absence, manual fallback, old arguments, split-flow failures,
  semantic no-candidate results, and timeout/disconnect findings remain
  explicit through existing check names and failure stages.

What test proves the boundary?

- `tests/kcs_adapters/test_mcpb_package.py` Claude Desktop UI prompt smoke
  tests.
- `tests/policy/test_code_review_graph_policy.py`.
- `tests/policy/test_kcs14_freeze_snapshots.py`.

## Acceptance

- Only `smoke_log_tooling` and refactor-log/closeout metadata are affected.
- The UI smoke report shape remains unchanged.
- No raw/private log content is added to docs, tests, or closeouts.
- Behavior drift check compares old `HEAD` output with staged output on
  representative synthetic log cases. Completed: old and new
  `_report_from_log()` dictionaries matched for single draft success, provider
  unavailable, manual fallback after blocker, disconnect after call, split
  selected continuation, old-argument rejection, and dry-run not-success.
- Graph hash for the touched script is updated after validation. Completed:
  `scripts/smoke_claude_desktop_ui_prompt.py`.

## Not In Scope

- MCPB stdio smoke behavior.
- Desktop log checker behavior.
- Runtime Desktop tool schema changes.
- Packet schema changes.
- KCS-15 style/markup parity.
