# KCS-14 Slice 6 Commit 0 Freeze/Snapshot Checks

Status: implemented pre-refactor safety layer.

## Problem

Slice 6 is allowed to simplify code structure, but it is not allowed to change
runtime behavior, packet contracts, Desktop tool behavior, privacy boundaries,
reviewer-bundle behavior, publication behavior, or customer-reply behavior.

Without mechanical baselines, a refactor can accidentally change a public shape
while presenting the change as internal cleanup.

## Decision

Before the first code movement commit, freeze the current contract surfaces that
are most likely to drift during refactor:

- Desktop `tools/list` names, aliases, input properties, required fields, and
  read/idempotency hints;
- Desktop tool output success key set;
- packet schema versions and dataclass field sets for current core, handoff,
  draft, and reviewer-only artifact packets;
- MCP result envelope keys and compact Desktop result key sets;
- high-risk public/runtime contract files through a pre-commit diff gate.

These checks are not architecture claims. They only say: if Slice 6 changes one
of these surfaces, the change must be reviewed as contract drift or an explicit
behavior-change candidate.

## Enforcement

Implemented in:

```text
tests/policy/test_kcs14_freeze_snapshots.py
```

The checks are deterministic and local. They do not read raw tickets, provider
payloads, reviewer bundles, Desktop logs, or private local artifacts.

## Review Use

For every Slice 6 refactor batch:

1. Run the freeze/snapshot tests with the relevant node tests.
2. If a snapshot fails, inspect the public shape change before updating the
   snapshot.
3. If the change is intentional, record the affected contract, review approval,
   and graph node in the batch closeout.
4. If the change is incidental, fix the refactor before commit.

## Not In Scope

- No runtime behavior changes.
- No packet schema changes.
- No Desktop tool schema changes.
- No reviewer-bundle path or content changes.
- No KCS-15 style/markup parity work.
- No broad automation framework.
