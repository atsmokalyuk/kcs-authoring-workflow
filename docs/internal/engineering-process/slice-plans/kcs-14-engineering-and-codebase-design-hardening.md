# KCS-14: Engineering And Codebase Design Hardening

## Goal

Improve the repository engineering process, review support, and codebase design
in small reviewable slices without changing the proven KCS authoring workflow.

KCS-14 is not "make docs and code nicer". KCS-14 is "reduce ambiguity for
future AI-assisted engineering while preserving runtime behavior".

KCS-14 is an umbrella. It must not become one large branch or one large PR.

Outcome contract:
`docs/internal/engineering-process/slice-plans/kcs-14-outcome-contract.md`

Each KCS-14 slice must answer the boundary questions in
`engineering-playbook/boundary-questions.md` before implementation.

Ousterhout's design rules are not the grounding source for every KCS-14 slice
equally. Use them primarily for design/refactor/review criteria, and use
spec-first or agentic-engineering process material for tooling and automation
details.

## Scope Boundary

Allowed:

- documentation ownership cleanup;
- tracked engineering process baseline;
- local tool entrypoints;
- functional acceptance test conventions;
- compact review context protocol;
- minimal code map before refactor;
- behavior-preserving codebase design refactor;
- review tooling after the criteria and code map exist.

Forbidden in KCS-14:

- KCS-15 style and markup parity behavior changes;
- extracting `engineering-spec-kit` or any reusable process/tooling package
  before the workflow is stable and reused by a second project;
- runtime behavior changes hidden inside doc or refactor work;
- packet contract changes unless explicitly approved as a later behavior-change
  slice;
- Desktop tool schema changes unless explicitly approved;
- privacy boundary changes;
- publish/write/customer-reply behavior;
- generated platform-specific development-agent skill packages.

## Required Boundary Questions

For each slice, answer:

- What complexity are we hiding?
- What should this module not know?
- What input is allowed?
- What input is forbidden?
- What output contract is stable?
- What failure mode must be explicit?
- What test proves the boundary?

## Design Grounding By Slice

Use Ousterhout as the primary review lens for:

- `1. engineering-process-baseline`: strategic programming, continuous design,
  small design investments, design per slice, and the rule that working code is
  not enough;
- `4. review-context-protocol`: review for complexity, hidden dependencies,
  interface drift, information leakage, and contract drift;
- `5. minimal-code-map`: dependencies, information leakage, ownership of
  knowledge, cross-module decisions, and unknown unknowns;
- `6. codebase-design-refactor`: deep modules, shallow abstractions, classitis,
  temporal decomposition, pass-through methods and variables, pulling
  complexity downward, and defining errors out of existence.

Use Ousterhout as a supporting lens for:

- `0. documentation-ownership-cleanup`: source-of-truth clarity, cross-module
  documentation, separating what matters from what does not matter, and
  avoiding duplicated rules in incidental locations;
- `3. functional-test-from-behavior`: tests as refactor safety and behavior
  protection. The BDD-shaped `Given / When / Then` convention comes from the
  local spec-first process, not from Ousterhout.

Use Ousterhout as a required supporting design lens, but not as the primary
source for implementation details, for:

- `2. local-tool-entrypoints`: ground this in repo process, deterministic tool
  surfaces, supported commands, and agent operational discipline. Ousterhout is
  still required for interface simplicity, obviousness, and avoiding noisy
  pass-through tool surfaces;
- `7. review-and-agent-tooling`: ground this in spec-first workflow, review
  packet protocol, output budgets, harness constraints, and local automation
  policy. Ousterhout is still required for consistency, complexity control,
  information hiding, and avoiding automation around unstable or shallow
  process abstractions.

Defer `Architecture Patterns with Python` until `6. codebase-design-refactor`
needs implementation-level decisions about Python core, service-layer,
adapter/port, and test boundaries.

## Slice Order

### 0. documentation-ownership-cleanup

Objective: make each document's purpose clear before adding more process.

Likely touched:

- `docs/internal/engineering-process/engineering-roadmap.md`
- `AGENTS.md`
- `README.md`
- `docs/internal/kcs-core-pipeline-architecture-and-contracts.md`
- `docs/internal/kcs-core-pipeline-technical-design.md`
- `docs/internal/engineering-process/feature-engineering-playbook.md`

Must not change:

- runtime behavior;
- packet contracts;
- Desktop behavior;
- privacy and fail-closed boundaries;
- `auto_publish_allowed=false`.

Acceptance:

- roadmap contains future plan and ordering only;
- architecture docs own runtime invariants;
- playbooks own engineering process rules;
- completed status stays in README or tracking docs;
- constraints are moved or referenced, not silently deleted.

Review checkpoint: docs ownership review before process baseline.

### 1. engineering-process-baseline

Objective: make spec-first engineering and deterministic agent behavior part of
the repo process.

Draft artifact:

- `docs/internal/engineering-process/agent-operable-engineering-workflow.md`

Its final authoritative status and tracking location must be confirmed by
`0. documentation-ownership-cleanup`.

Document ownership:

- `AGENTS.md` remains the short policy kernel for non-negotiable development
  agent rules.
- `agent-operable-engineering-workflow.md` owns the detailed agent working
  process for this repository.
- `codex-agent-instructions.md` owns Codex-specific local implementation
  details and should reference the generic workflow instead of duplicating it.

Expected workflow content:

- context principle: prefer less context with higher authority. Use repo docs,
  current diff, failing test, and exact contracts instead of long chat history;
- narrow slice-run discipline;
- clarification mode for vague tasks: stress-test the task before planning or
  coding until objective, boundaries, stable contracts, failure behavior, tests,
  and non-goals are explicit;
- compact current-state format before work starts;
- authoritative-context preference over long chat history;
- context reset protocol when task direction changes;
- context freshness rule: start a fresh task frame instead of compacting noisy
  sessions when old plans, fixed bugs, runtime logs, or previous review verdicts
  begin to obscure the current task;
- tool output budget policy;
- retry/struggle feedback rule: repeated agent retries, tool misuse, or
  recurring validation failures should trigger a process improvement note
  against docs, tests, tool entrypoints, code map, or boundary questions instead
  of an unbounded retry loop;
- checkpoint summary format;
- review packet handoff expectations;
- code-map usage once available;
- dirty-worktree handling expectations;
- stop/ask conditions for material ambiguity or boundary risk;
- autonomy gate: AFK-style or broad autonomous execution is out of scope until
  commands, tests, review packets, and task boundaries are stable and reviewed.

Context reset frame:

```text
Current task:
Relevant files:
Must preserve:
Failure / target behavior:
Validation to run:
Ignore prior context about:
```

Context to prefer:

- current branch and current diff;
- current task;
- relevant repo docs;
- touched files;
- exact contract that must not change;
- failing test or expected test;
- known good behavior that must not regress;
- explicit ignore/reset note for stale prior context.

Context to avoid by default:

- long chat history;
- full runtime logs;
- full reviewer bundles;
- full HTML;
- raw tickets;
- old review verdicts that no longer apply;
- already-fixed bugs unless they define a regression case.

Acceptance:

- supported planning flow is documented;
- agent-operable engineering workflow is planned as the detailed procedure
  below the existing `AGENTS.md` policy kernel;
- tracked repo process is separated from local-only personal process;
- Codex, ChatGPT Pro review, Fable 5 review, and future internal runner are
  named accurately;
- unavailable development harnesses are not described as active.

Review checkpoint: process review focused on source-of-truth drift.

### 2. local-tool-entrypoints

Objective: define official repo-local commands for supported tasks.

Local tool entrypoints are the agent tool-surface specification for the
repository engineering workflow, not a product behavior spec.

Planned artifact:

- `docs/internal/engineering-process/tool-entrypoints.md`

Document ownership:

- `AGENTS.md` should contain only a compact index of official entrypoints.
- `AGENTS.md` must not become a full scripts catalog, architecture map,
  exhaustive pytest matrix, or duplicate README/playbook procedure.
- `tool-entrypoints.md` owns detailed command usage, when to use each command,
  deterministic vs manual/UI classification, output budget expectations, and
  links to deeper procedures.
- `scripts/` owns executable tools.
- `tests/` owns executable behavior and contract checks.

Acceptance:

- commands are exact and current;
- deterministic checks are separated from manual Desktop/UI checks;
- agents can run supported tools without inventing ad hoc shell workflows.
- AGENTS.md provides a short stable entrypoint index without duplicating
  detailed procedures.

Review checkpoint: command review against `README.md`, `pyproject.toml`, and
`scripts/`.

### 3. functional-test-from-behavior

Objective: define how behavior becomes executable acceptance tests before
implementation where practical.

Acceptance:

- BDD-shaped pytest is the default;
- golden checks protect stable outputs only through synthetic fixtures,
  approved clean-ticket fixtures that are safe under the data-handling
  baseline, or structural/hash assertions;
- committed clean-ticket-derived fixtures must be sanitized, approved,
  privacy-scanned, and portable;
- local clean-ticket refs are allowed only as skip-if-absent fixtures and must
  not make the suite machine-dependent;
- forbidden-path tests protect data boundaries;
- refactor work has behavior tests around risky boundaries before movement.

Review checkpoint: test-process review before design refactor.

### 4. review-context-protocol

Objective: define compact review handoff packets for Codex, ChatGPT Pro review,
Fable 5 review, and future internal review.

Acceptance:

- packet includes intent, changed files, affected contracts, relevant tests,
  known deferred risks, and what must not change;
- packet excludes raw tickets, bundles, excerpts, credentials, and private
  paths;
- output budget policy is clear.
- the `affected contracts` field may start manual and should be revised after
  `5. minimal-code-map` exists.

Review checkpoint: dry-run one doc-only review packet.

### 5. minimal-code-map

Objective: create a small orientation map before codebase refactor.

Acceptance:

- module ownership and contract edges are documented;
- risky files and related tests are identified;
- graph/map is advisory and git-aware;
- stale or deleted file references can be detected.

Review checkpoint: code-map review before behavior-preserving refactor.

### 6. codebase-design-refactor

Objective: simplify code structure without changing behavior.

Acceptance:

- public contracts stay stable;
- refactor targets are pre-declared from the reviewed code map;
- each refactor PR covers one ownership area and remains independently
  reviewable;
- freeze-list contracts are published before refactor starts;
- refactor splits by ownership of knowledge, not execution order;
- split is accepted only when it reduces what callers must know;
- no classitis, pass-through modules, or shallow helper sprawl;
- regression tests cover touched risky boundaries;
- modified test assertions are blockers unless explicitly justified;
- golden/contract checks remain stable for behavior-preserving refactors.

Review checkpoint: staged code review after each ownership-area refactor.
Start with lower-blast-radius adapter or smoke/log tooling before safety gates,
validation gates, renderer behavior, or output boundaries.

### 7. review-and-agent-tooling

Objective: automate the stable review process after criteria and code map exist.

Acceptance:

- tooling uses documented entrypoints and review protocol;
- review packet generation is bounded and safe;
- review packet tooling has forbidden-content tests and must not leak the data
  it is meant to exclude;
- diff-to-contract checks use the code map;
- tooling does not become the source of truth.

Review checkpoint: tooling review after dry-run packets match the documented
protocol.

## Fable Review Packet

Before Fable 5 review, send:

- this KCS-14 umbrella plan;
- `docs/internal/engineering-process/review-criteria/ousterhout-design-review-checklist.md`;
- current repo constraints and what must not change;
- expected slice order;
- focused questions about sequence, missing gates, risk boundaries, and review
  checkpoints.
