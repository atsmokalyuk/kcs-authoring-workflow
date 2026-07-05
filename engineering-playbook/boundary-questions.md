# Boundary Questions For Every Slice

Use these questions before implementation and again during review. They are
intended to keep each slice small, explicit, and reviewable.

For every slice, answer:

## Design Boundary

- What complexity are we hiding?
- What should this module not know?
- Which design decision has one owner?
- Are we splitting by ownership of knowledge, not by execution order?
- Does the split reduce what callers must know?
- If this slice splits a class, file, or method, what real ownership boundary
  does the split expose, and what new interface cost does it add?
- If this slice introduces `prepare`, `submit`, `write`, `continue`, or other
  time-ordered modules, what knowledge does each own, and what knowledge must
  not be duplicated?

## Input Boundary

- What input is allowed?
- What input is forbidden?
- Which input classes are synthetic, approved sanitized, local-only, or
  client-visible?
- Which unsafe values must be rejected without echo?

## Output Boundary

- What output contract is stable?
- Which fields, schema versions, flags, paths, refs, or hashes are part of the
  interface?
- Which output must remain compact, value-safe, reviewer-only, or local-only?
- Which fields must never imply write, publish, customer-reply, or public-output
  approval?

## Failure Boundary

- What failure mode must be explicit?
- What safe blocker/debug code should represent the failure?
- Does the failure preserve fail-closed behavior?
- Does the failure avoid raw input echo?
- What is the safe next action for the operator or reviewer?

## Test Boundary

- What test proves the boundary?
- What happy path proves the intended behavior?
- What forbidden path proves rejected input or output?
- What regression fixture protects stable output?
- What review or smoke check proves adjacent contracts were not changed?

## Project Invariants

Each slice must identify the project-specific invariants it preserves. Do not
copy product-specific rules into this generic checklist. Reference the
project's architecture, data-handling, and planning-decision documents instead.

For this project, start from:

- `docs/internal/kcs-core-pipeline-architecture-and-contracts.md`
- `docs/internal/kcs-core-pipeline-technical-design.md`
- `docs/internal/kcs-authoring-mvp-data-handling-baseline.md`
- `docs/internal/engineering-process/kcs-14-planning-decisions.md`

## Minimum Slice Spec

Each slice spec should include:

- objective;
- complexity hidden;
- module knowledge forbidden;
- allowed inputs;
- forbidden inputs;
- stable output contract;
- explicit failure modes;
- tests or acceptance scenarios;
- unchanged contracts;
- review checkpoint.
