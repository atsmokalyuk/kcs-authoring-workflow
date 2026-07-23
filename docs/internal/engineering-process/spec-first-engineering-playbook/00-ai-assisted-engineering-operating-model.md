# AI-Assisted Engineering Operating Model

This document defines how agent policy, spec-first planning, executable tests,
and deterministic implementation relate to each other in AI-assisted
engineering.

## Operating Layers

```text
AGENTS.md
  defines how the coding agent should behave

docs/internal/engineering-process/spec-first-engineering-playbook/
  defines how a slice is specified before code

tests and evals
  prove behavior and protect contracts

src/
  implements the agreed deterministic behavior
```

## Core Model

```text
policy -> spec -> tests -> implementation -> validation -> review
```

The model is not "AI writes code and humans inspect the diff." The model is:

```text
human and agent clarify the requested outcome
agent drafts a bounded spec
agent prepares decision-ready design evidence
human selects the design and separately authorizes Delivery
agent implements only the selected and authorized slice
tests/evals prove the behavior
review checks contracts, privacy, failure behavior, and drift
```

## Role Of Each Artifact

`AGENTS.md` is the local repo behavior contract for Codex. It says how the
agent should work: read local context, preserve contracts, ask questions on
material ambiguity, use the playbook on planning triggers, validate locally,
and report concrete results.

The playbook is the spec-first planning layer. It turns a feature idea into a
slice with goal, user/operator, allowed inputs, forbidden inputs, output
contract, failure behavior, tests/evals, acceptance criteria, and review
checklist.

Tests, bounded trials, and named human reviews are guardrails matched to the
kind of acceptance criterion. Deterministic behavior should use executable
tests. Model-mediated stability needs a predeclared bounded trial. Judgment-
based properties need a named human-review gate with stated evidence.

Source code is the deterministic runtime owner. AI may assist with drafting or
semantic reasoning only inside bounded contracts; code owns validation,
decisions, rendering, persistence, and failure behavior.

## BDD In This Project

This project uses BDD-shaped pytest by default.

Deterministically testable acceptance criteria should be translated into
executable pytest tests that read as `Given / When / Then`, but remain ordinary
Python tests unless a dedicated BDD runner becomes necessary. Do not force
model-mediated or judgment-based criteria into dishonest deterministic tests;
map them to the bounded-model-trial or human-review gates defined by this
playbook.

Default mapping:

```text
Given = state, fixture, or precondition
When  = action, function call, or tool call
Then  = contract assertion, safety assertion, or output assertion
```

Use `.feature` files or a Gherkin framework only when scenarios must be shared
with non-Python reviewers or when plain pytest no longer keeps behavior
readable.

For now:

```text
spec-first playbook defines the slice
acceptance criteria define expected behavior
BDD-shaped pytest proves deterministic behavior
bounded trials evaluate model-mediated stability
named human reviews evaluate judgment-based properties
golden fixtures protect stable output
forbidden-path tests protect safety boundaries
```

Do not add BDD tooling for simple contract tests when pytest comments, names,
and assertions are sufficient.

## Trigger Phrases

Use this operating model when the operator says:

```text
plan new slice
create implementation plan
создай план реализации фичи
```

Equivalent requests to plan a new feature or implementation slice should follow
the same flow.

## Planning Flow

Before implementation:

1. Read `AGENTS.md`.
2. Read the relevant files in `docs/internal/engineering-process/spec-first-engineering-playbook/`.
3. Draft or update the slice spec.
4. Ask concise clarifying questions for material unknowns.
5. Record outcome agreement, design selection, and Delivery authorization as
   three independent facts when the slice affects runtime behavior, data
   handling, privacy boundaries, schemas/contracts, persistence, integrations,
   or public/reviewer output.
6. Keep Delivery locked until the operator has sufficient visible evidence,
   selects the design, and separately authorizes Delivery.
7. Implement only the selected and authorized slice.
8. Run targeted validation.
9. Report changed files, unchanged contracts, validation run, and open risks.

## Review Questions

Every implementation slice should be reviewed against these questions:

- Does it satisfy the acceptance criteria?
- Does it preserve the privacy boundary?
- Does it fail closed?
- Does it avoid unsafe input echo?
- Is the output schema stable?
- Are tests covering happy and forbidden paths?
- Did AI invent behavior outside the spec?
- Are runtime decisions still owned by deterministic code?

## Repository Boundary

This is an engineering operating model. It is tracked so development agents
and reviewers can share the same baseline from a fresh clone.

Do not treat this file as runtime behavior. Runtime behavior must be enforced
by source code, typed contracts, policy evaluators, and tests.
