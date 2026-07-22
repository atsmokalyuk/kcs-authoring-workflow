# Spec-first Engineering Playbook: How To Use

This is a tracked development playbook for spec-first implementation slices.
It is not a runtime contract and does not replace product, architecture, or
data-handling documents.

Use it when the operator says:

```text
plan new slice
create implementation plan
создай план реализации фичи
```

## Workflow

1. Read `AGENTS.md`.
2. Read the relevant files in this directory.
3. Draft or update the slice spec before implementation.
4. Ask the operator concise questions for material unknowns.
5. Wait for confirmation before changing runtime behavior, privacy boundaries,
   schemas/contracts, persistence, integrations, or public/reviewer output.
6. Implement only the agreed slice.
7. Report changed files, unchanged contracts, validation run, and open risks.

## Slice Planning Location

By default, slice plans are drafted in chat and confirmed by the operator before
implementation.

Use this playbook as the planning template, but do not overwrite the playbook
files for every slice.

If a slice plan needs to persist across sessions, save it under:

```text
docs/internal/engineering-process/slice-plans/
```

Example:

```text
docs/internal/engineering-process/slice-plans/
  kcs-14-style-markup-parity.md
```

Persistent slice plans are engineering artifacts. Commit them when they become
authoritative planning inputs for a reviewable slice; keep temporary personal
notes in `local-docs/`.

## Repository Boundary

These playbook files are dev-time engineering instructions. They are not
runtime artifacts.

Do not commit:

```text
local-docs/
local-data/
runtime reviewer bundles
raw clean tickets
old or unpromoted demo outputs
```

If a local runtime artifact is useful for tests or demo, manually distill it
into a safe fixture or approved showcase artifact first.
