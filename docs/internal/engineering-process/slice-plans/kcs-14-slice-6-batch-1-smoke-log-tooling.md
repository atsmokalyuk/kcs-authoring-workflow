# KCS-14 Slice 6 Batch 1 Smoke Log Tooling

Status: in progress behavior-preserving refactor batch.

## Objective

Exercise the Slice 6 refactor process on the `smoke_log_tooling` graph node
without changing runtime behavior or public output contracts.

Initial target:

```text
src/kcs_adapters/smoke_accounting.py
```

## Boundary Questions

What complexity are we hiding?

- Repeated regex marker extraction and derived smoke-accounting counters.

What should this module not know?

- KCS action decisions, provider output validation, reviewer bundle content,
  raw transcript storage, Desktop UI automation, or MCPB package layout.

What input is allowed?

- Operator-provided local smoke transcript text or a local log path supplied to
  the CLI.

What input is forbidden?

- Raw ticket data in committed tests, provider payload bodies in closeouts,
  reviewer bundle bodies, credentials, and private local artifacts.

What output contract is stable?

- `SmokeAccountingReport.to_json_dict()` keys and values remain stable.
- CLI exit codes and value-safe JSON error codes remain stable.
- The module must not echo missing local paths or transcript content in errors.

What failure mode must be explicit?

- Invalid numeric options, missing logs, non-UTF-8 logs, unreadable logs, and
  CLI usage errors remain explicit value-safe error codes.

What test proves the boundary?

- `tests/kcs_adapters/test_smoke_accounting.py`
- `tests/policy/test_kcs14_freeze_snapshots.py`
- `tests/policy/test_code_review_graph_policy.py`

## Acceptance

- Only `smoke_log_tooling` and engineering-policy graph metadata are affected.
- Public smoke-accounting JSON schema remains unchanged.
- CLI behavior remains unchanged.
- No raw/private transcript content is added to repo docs, tests, or closeouts.
- Graph hash for the touched source file is updated after validation.

## Not In Scope

- Desktop tool schema changes.
- MCPB behavior changes.
- Desktop UI smoke behavior changes.
- Log-check behavior changes.
- Packet schema changes.
- KCS-15 style/markup parity.
