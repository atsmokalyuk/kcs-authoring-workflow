# Feature Note: Functional Test From Behavior

## Problem

Agents may start coding from a list of files or modules without first
understanding operator-defined behavior. Tests written after implementation can
then freeze accidental behavior instead of the intended workflow.

KCS-14 needs a process gate that makes behavior and acceptance scenarios clear
before behavior or refactor coding starts.

## Decision

Use `docs/internal/engineering-process/functional-test-from-behavior.md` as
the authoritative process rule for converting accepted behavior into pytest
scenarios.

The agent must not treat a file list as a behavior spec. If behavior,
allowed/forbidden inputs, output contract, failure behavior, or acceptance
scenarios are missing and cannot be reconstructed from tracked docs, the agent
must ask for a compact behavior frame before coding.

## Workflow

```text
behavior definition
  -> functional test spec
  -> test-first skeleton
  -> implementation
  -> review
```

Persistent slice specs should live with the tracked slice plan when needed:

```text
docs/internal/engineering-process/slice-plans/<slice>/behavior.md
docs/internal/engineering-process/slice-plans/<slice>/functional-tests.md
tests/.../test_<slice>_behavior.py
```

## Agent Stop Condition

For behavior or refactor work, stop before coding when the behavior/test frame
is missing and cannot be recovered from tracked repo docs.

This stop condition is not needed for typo-only, formatting-only, or explicitly
scoped documentation edits that do not affect behavior or contracts.

## Not In Scope

- Runtime behavior changes.
- New BDD framework.
- Broad test machinery.
- Article presentation parity work.
- Machine-readable spec registry.
- Wrapper CLI.

## Implemented In Slice 3

- `docs/internal/engineering-process/functional-test-from-behavior.md`
  defines BDD-shaped pytest, behavior-to-code workflow, agent reminder gate,
  fixture tiers, golden boundaries, forbidden-path tests, and refactor safety.
- The generic test-plan playbook points to the authoritative process doc.
- `tests/policy/test_functional_test_policy.py` protects process anchors and
  future fixture provenance rules.

## Later Use

Slice 5 code-map work should reference affected graph nodes from functional
test specs when available.

Slice 6 refactors should have behavior tests around risky boundaries before
movement.
