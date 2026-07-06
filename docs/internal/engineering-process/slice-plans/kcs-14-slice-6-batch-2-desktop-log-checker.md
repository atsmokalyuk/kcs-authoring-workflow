# KCS-14 Slice 6 Batch 2 Desktop Log Checker

Status: ready for commit.

## Objective

Continue the `smoke_log_tooling` refactor with a second low-blast-radius batch
focused on Desktop log checker internals.

Target:

```text
scripts/check_claude_kcs_desktop_log.py
```

## Boundary Questions

What complexity are we hiding?

- The current active Desktop tool-surface expectation: tool names, input
  property sets, and read/idempotency annotations.

What should this module not know?

- KCS action decisions, packet validation internals, provider output
  validation, reviewer bundle content, raw transcript storage, or Desktop UI
  automation.

What input is allowed?

- A local Claude Desktop MCP server log path and optional timestamp boundary.

What input is forbidden?

- Committed raw logs, full private transcript bodies, provider payload bodies,
  reviewer bundle bodies, credentials, and private local artifacts.

What output contract is stable?

- `check_log()` report keys remain stable.
- CLI arguments and exit codes remain stable.
- `checks` keys remain stable for full and truncated tool surfaces.
- Only compact value-safe metadata such as log file name and timestamps is
  returned.

What failure mode must be explicit?

- Missing log path still returns `log_not_found`.
- Missing fresh tools/list line still returns `tools_list_not_found`.
- Invalid `--since` remains an explicit CLI timestamp failure.

What test proves the boundary?

- `tests/kcs_adapters/test_mcpb_package.py` Desktop log checker tests.
- `tests/policy/test_tool_entrypoints.py` help/liveness check.
- `tests/policy/test_code_review_graph_policy.py`.
- `tests/policy/test_kcs14_freeze_snapshots.py`.

## Acceptance

- Only `smoke_log_tooling` and refactor-log/closeout metadata are affected.
- The Desktop log checker report shape remains unchanged.
- No raw/private log content is added to docs, tests, or closeouts.
- Behavior drift check compares old `HEAD` output with staged output on
  representative synthetic log cases. Completed: old and new `check_log()`
  report dictionaries matched for latest thin tool surface, stale tool surface,
  truncated tool surface, `--since` filtering, and missing log path.
- Graph hash for the touched script is updated after validation. Completed:
  `scripts/check_claude_kcs_desktop_log.py`.

## Not In Scope

- MCPB stdio smoke behavior.
- Desktop UI smoke behavior.
- Runtime Desktop tool schema changes.
- Packet schema changes.
- KCS-15 style/markup parity.
