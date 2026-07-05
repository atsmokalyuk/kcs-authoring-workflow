# Feature Note: Local Tool Entrypoints

## Problem

Agents can waste context and introduce drift by inventing shell workflows,
running broad commands when narrow checks are enough, or treating manual
Desktop/UI checks as deterministic tests.

KCS-14 needs an official local command surface that is readable to humans and
agents, but does not prematurely become a wrapper CLI or automation framework.

## Decision

Use `docs/internal/engineering-process/tool-entrypoints.md` as the
authoritative command surface:

```text
AGENTS.md
  compact pointer

tool-entrypoints.md
  command usage, classification, output budget, caveats

scripts/ and console entrypoints
  executable behavior

tests/
  liveness and policy checks
```

Commands must be classified honestly as deterministic, deterministic with local
runtime, manual/local-state, manual/local-side-effect, or manual/UI.

## Workflow

Before commit, agents should pick the narrowest relevant commands from
`tool-entrypoints.md` and summarize compact results instead of pasting large
logs or artifacts into chat.

Help/liveness checks prove importability and command availability. They do not
prove full Desktop or runtime workflow behavior.

## Not In Scope

- Runtime behavior changes.
- Desktop/tool schema changes.
- Treating Desktop UI smoke as fully deterministic.
- Wrapper CLI or machine-readable registry.
- Broad validation runner.
- Review packet generator.

## Implemented In Slice 2

- `docs/internal/engineering-process/tool-entrypoints.md` defines supported
  local commands, classifications, output budget, and artifact rules.
- `AGENTS.md` points to the command surface without becoming a script catalog.
- `tests/policy/test_tool_entrypoints.py` checks command coverage,
  manual/deterministic classifications, and help-only liveness.

## Later Use

Repeated command groups may later move into a wrapper CLI or machine-readable
registry only after the documented command surface proves stable.

Slice 7 may automate only stable command surfaces that are already documented
and tested.
