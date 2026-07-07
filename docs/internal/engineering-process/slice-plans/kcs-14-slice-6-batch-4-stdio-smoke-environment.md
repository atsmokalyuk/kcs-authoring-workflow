# KCS-14 Slice 6 Batch 4 Stdio Smoke Environment

Status: ready for staged-diff review.

## Objective

Continue the `smoke_log_tooling` refactor with a narrow batch focused on MCPB
stdio smoke wrapper environment construction.

Target:

```text
scripts/smoke_kcs_mcpb_stdio.py
```

## Boundary Questions

What complexity are we hiding?

- The local process environment passed to the MCPB wrapper during deterministic
  stdio smoke sessions.

What should this module not know?

- Runtime KCS decisions, provider output validation internals, reviewer bundle
  content, raw transcript storage, or Desktop UI automation.

What input is allowed?

- Wrapper path, Node command, uv command, deterministic JSON-RPC smoke
  messages, and the explicit choice of fixture vs inherited semantic provider
  behavior for each smoke session.

What input is forbidden?

- Private ticket bodies, committed raw logs, credentials, private provider
  payloads, reviewer bundle bodies, and local debug artifacts.

What output contract is stable?

- `run_smoke()` report keys remain stable.
- CLI arguments and exit codes remain stable.
- JSON-RPC request order and check names remain stable.
- Value-safe `SmokeError` codes remain stable.

What failure mode must be explicit?

- Wrapper not found, node not found, wrapper timeout/failure, missing JSON-RPC
  response, invalid semantic review packet, and missing semantic review refs
  remain explicit through existing `SmokeError` codes.

What test proves the boundary?

- `tests/kcs_adapters/test_mcpb_package.py` MCPB stdio smoke tests.
- `tests/policy/test_code_review_graph_policy.py`.
- `tests/policy/test_kcs14_freeze_snapshots.py`.

## Acceptance

- Only `smoke_log_tooling` and refactor-log/closeout metadata are affected.
- The stdio smoke report shape remains unchanged.
- No JSON-RPC request payloads, response checks, CLI arguments, or error codes
  change.
- Behavior drift check compares old `HEAD` behavior with staged behavior where
  practical. Completed: new `_wrapper_env()` matched old inline env formulas
  for fixture-provider and inherited-provider paths.
- Graph hash for the touched script is updated after validation. Completed:
  `scripts/smoke_kcs_mcpb_stdio.py`.

## Not In Scope

- Desktop UI smoke behavior.
- Desktop log checker behavior.
- Runtime Desktop tool schema changes.
- Packet schema changes.
- KCS-15 style/markup parity.
