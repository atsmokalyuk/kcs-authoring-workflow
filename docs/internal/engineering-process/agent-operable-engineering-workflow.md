# Agent-Operable Engineering Workflow

Status: authoritative KCS-14 development-agent workflow for this repository.
This document defines the detailed working process below the short `AGENTS.md`
policy kernel.

## Purpose

Define how a development agent should work in this repository without relying
on long chat history or implicit operator memory.

This document is the detailed workflow below the short `AGENTS.md` policy
kernel. It does not replace runtime architecture documents, packet contracts,
tests, or source code.

## Document Layers

```text
AGENTS.md
  = short non-negotiable policy kernel

agent-operable-engineering-workflow.md
  = detailed development-agent working process

codex-agent-instructions.md
  = Codex-specific local implementation details

tool-entrypoints.md
  = official command/tool surface once created

scripts/
  = executable tools

tests/
  = executable behavior and contract checks
```

Authority ladder when sources conflict:

```text
code and executable tests
  -> runtime contracts and data-handling docs under docs/internal/
  -> AGENTS.md policy kernel
  -> tracked engineering-process docs
  -> Codex-specific local instructions
  -> local-only notes
  -> chat history
```

If a lower-authority source conflicts with a higher-authority source, do not
guess. Follow the higher-authority contract, then surface the conflict as a
planning or behavior-change issue.

## Context Principle

Prefer less context with higher authority.

Do not optimize for giving the agent more history. Optimize for giving the
agent the smallest current authoritative context needed for the slice:

- current branch and current diff;
- current task;
- relevant repo docs;
- touched files;
- exact contract that must not change;
- failing test or expected test;
- known good behavior that must not regress;
- explicit ignore/reset note for stale prior context.

Avoid loading by default:

- long chat history;
- full runtime logs;
- full reviewer bundles;
- full HTML;
- raw tickets;
- old review verdicts that no longer apply;
- already-fixed bugs unless they define a regression case.

## Task Start Frame

Before work starts, establish a compact current state:

```text
Current branch:
Last relevant commit:
Current task:
Active slice / batch:
Staged / untracked state:
Relevant files:
Relevant docs:
Affected graph node:
Must preserve:
Known good behavior:
Failure / target behavior:
Validation to run:
Ignore prior context about:
```

If the task is small and the current state is obvious from the repo, this frame
can be brief. If context is noisy, write the frame explicitly before reading or
editing more files.

## Context Window Check

Before every material batch, run a context window check. After each commit,
aggregate review, or external-review checkpoint, the agent must emit a visible
compact checkpoint before starting the next material batch. "Visible" means the
operator can see it in chat, or the batch closeout/review note explicitly
records it as the starting frame for the next batch.

The checkpoint must state:

- current branch and last relevant commit;
- active slice and batch;
- staged and untracked state;
- source-of-truth docs to use;
- affected graph node or reason no graph node applies;
- validation commands expected for the batch;
- prior chat context to ignore.

If the thread is long, noisy, or crossing a batch boundary, the agent should
offer a fresh-thread handoff summary before coding. If continuing in the same
thread, the compact current-state frame becomes the authority for the next
batch, not the older conversation.

Minimum visible checkpoint:

```text
Current branch / commit:
Current slice / next batch:
Declared graph node:
Staged / untracked state:
Authoritative docs:
Stale context to ignore:
Next intended action:
Validation expected:
```

## Clarification Mode

Use clarification mode when task intent, boundaries, contracts, failure
behavior, tests, or non-goals are materially unclear.

The agent should stress-test the task before planning or coding until these are
clear:

- objective;
- allowed inputs;
- forbidden inputs;
- stable output contract;
- failure behavior;
- tests or acceptance scenarios;
- unchanged contracts;
- non-goals.

Ask concise questions only for material ambiguity that cannot be resolved from
repo docs or code. Do not code while a boundary, privacy, schema, persistence,
integration, or reviewer-output ambiguity remains material.

## Slice-Run Discipline

Work in narrow slice runs.

Good task frame:

```text
Fix semantic review submit blocker for one failing case.
Do not refactor renderer code.
Preserve Desktop tool schema and bundle output.
```

Bad task frame:

```text
Continue all KCS-13 work.
Clean up the project.
Improve the agent workflow.
```

Each implementation slice should define:

- objective;
- boundary;
- contracts;
- failure behavior;
- tests;
- review checkpoint.

## Boundary Questions

Before implementation and review, apply
`engineering-playbook/boundary-questions.md`.

At minimum, answer:

- What complexity are we hiding?
- What should this module not know?
- What input is allowed?
- What input is forbidden?
- What output contract is stable?
- What failure mode must be explicit?
- What test proves the boundary?

## Context Reset Protocol

Start a fresh task frame instead of compacting noisy sessions when:

- old plans conflict with current decisions;
- fixed bugs keep reappearing in context;
- runtime logs obscure design decisions;
- previous review verdicts no longer apply;
- the task changes from runtime debugging to docs/process/refactor work;
- the current goal can be described more accurately than the existing thread.

Reset frame:

```text
Current task:
Relevant files:
Must preserve:
Failure / target behavior:
Validation to run:
Ignore prior context about:
```

## Tool Output Budget

Prefer compact outputs in chat and detailed outputs in local artifacts.

Use chat for:

- failing test names;
- debug codes;
- compact status;
- changed file list;
- artifact paths;
- hashes;
- validation command summaries.

Avoid pasting into chat by default:

- full HTML;
- full logs;
- full reviewer bundles;
- raw tickets;
- long transcripts;
- full diffs over large files;
- raw provider payloads.

If a large output is needed, write or reference a local artifact and summarize
the relevant lines.

## Retry And Struggle Feedback

Repeated agent retries are a process signal, not just an implementation issue.

If the agent repeatedly misuses tools, fails the same validation, or loops on a
task, record which process surface likely needs improvement:

- docs;
- tests;
- tool entrypoints;
- code map;
- boundary questions;
- review packet;
- module interface.

Default destination for durable process-improvement notes:
`docs/internal/engineering-process/` once the tracked process docs exist.
Local-only or personal observations may stay in
`local-docs/engineering-process/implementation-mistake-log.md`, but local-only
notes are not authoritative process.

Do not continue unbounded retry loops. Fix the missing process surface or
surface the blocker.

If the same review finding recurs twice, classify it as one of:

- deterministic check candidate;
- structural boundary candidate;
- advisory review tripwire;
- measurement-only signal.

## Checkpoint Summary

At the end of a material slice, report:

- changed files;
- unchanged contracts;
- validation run;
- review route and verdict path, when review was required;
- open risks or deferred items;
- whether any behavior-change proposal was discovered;
- any repeated finding that should move down the enforcement ladder.

For doc/process slices, also report:

- source-of-truth changes;
- moved, referenced, or unchanged constraints;
- follow-up migration items.

## Review Packet Handoff

Use compact review packets for non-trivial review.
Detailed file-based packet rules live in
`docs/internal/engineering-process/review-context-protocol.md`.

A review packet should include:

- slice intent;
- changed files;
- affected contracts;
- relevant tests;
- validation run;
- known deferred risks;
- what must not change;
- explicit stale context to ignore.

It must exclude:

- raw tickets;
- raw internal comments;
- selected semantic-review excerpts;
- reviewer bundles;
- credentials;
- private paths;
- provider payloads.

## Code Map Usage

When a code map exists, use it before refactor or review to identify:

- module ownership;
- contract edges;
- hard invariants;
- related tests;
- known risk areas.

The code map is an orientation layer, not a replacement for reading touched
files and direct dependencies.

KCS-14 code-map artifacts:

- `docs/internal/engineering-process/code-review-graph.json`
- `docs/internal/engineering-process/module-boundaries.md`
- `docs/internal/engineering-process/review-checkpoints.md`

Before behavior or refactor coding:

```text
task intent
-> affected code-map nodes
-> module boundaries
-> touched files and direct dependencies
-> related tests
-> unchanged contracts
```

After coding:

```text
changed files
-> affected code-map nodes
-> boundary risks
-> related tests
-> review packet / closeout
```

If a refactor or cross-module behavior task cannot be mapped to a code-map
node, stop and ask for scope clarification or propose a small code-map update
first.

## Dirty Worktree Handling

Before edits:

- inspect current status;
- distinguish existing user changes from agent changes;
- do not revert unrelated changes;
- work with existing changes if they affect the task;
- ask only if existing changes make the task impossible or unsafe.

## Stop Or Ask Conditions

Stop and ask when:

- the requested change would alter runtime behavior, privacy boundaries,
  schemas/contracts, persistence, integrations, or reviewer output without
  approval;
- allowed/forbidden inputs are unclear and cannot be inferred from repo docs;
- the safe failure behavior is unclear;
- the task requires destructive git, deploy, delete, reset, force, or
  production-like infrastructure action;
- available context conflicts with authoritative repo docs.

## Autonomy Gate

AFK-style or broad autonomous execution is out of scope until commands, tests,
review packets, task boundaries, and review checkpoints are stable and
reviewed.

Autonomy must be gated by:

- explicit task queue;
- official tool entrypoints;
- deterministic validation;
- compact review packets;
- clear stop conditions;
- human review for behavior, privacy, schema, persistence, integration, or
  reviewer-output changes.
