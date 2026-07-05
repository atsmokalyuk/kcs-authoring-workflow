# Feature Note: Agent-Operable Engineering Workflow

## Problem

Long chat context and local memory can cause agents to mix old plans, fixed
bugs, runtime logs, and current work. Important process rules also drift when
they live only in chat or personal notes.

KCS-14 needs a workflow that agents can follow from tracked repository context
without turning `AGENTS.md` into a long operations manual.

## Decision

Use layered agent instructions:

```text
AGENTS.md
  short non-negotiable policy kernel

agent-operable-engineering-workflow.md
  detailed development-agent workflow

codex-agent-instructions.md
  Codex-specific local implementation details
```

The agent should prefer less context with higher authority: current diff,
tracked docs, relevant files, failing tests, and exact contracts over long chat
history.

## Workflow

For each material task, the agent should:

1. read the relevant authoritative docs;
2. frame the current task narrowly;
3. preserve runtime and safety contracts unless explicitly approved;
4. use compact context and bounded tool output;
5. run targeted validation;
6. produce a concrete closeout with changed files, unchanged contracts,
   validation, risks, and promotion candidates.

## Agent Stop Conditions

The agent should stop and ask when behavior, privacy, schema, persistence,
integration, reviewer-output, or destructive git/deploy boundaries are unclear
and cannot be resolved from tracked docs.

## Not In Scope

- Runtime behavior changes.
- Packet schema changes.
- Desktop/tool schema changes.
- Broad autonomous execution.
- Replacing tests with process prose.
- Turning `AGENTS.md` into a full playbook or script catalog.

## Implemented In Slice 1

- `docs/internal/engineering-process/agent-operable-engineering-workflow.md`
  became the authoritative tracked development-agent workflow below
  `AGENTS.md`.
- `AGENTS.md` references the workflow without duplicating detailed procedure.
- Policy checks ensure the workflow remains tracked and authoritative.

## Later Use

Slice 4 review packets and promotion candidates use this workflow's closeout
and context-hygiene rules.

Slice 7 automation should only automate workflow steps that survived manual use
and have clear validation commands.
