# KCS Authoring MVP - Feature Engineering Approach

## Purpose

Define the engineering approach for developing the KCS Authoring MVP in small, controlled, reviewable slices.

This document captures the project-level feature engineering rules learned from the local `plesk_support` prototype and adapts them for the corporate KCS Authoring MVP. It is not a Git policy and does not replace the Data Handling Baseline or Architecture and Contracts documents.

## Core Principle

The MVP must be workflow-first, not prompt-first.

```text
Code decides.
LLM drafts.
Validators block.
```

The LLM may draft text, suggest wording, or help review style. It must not own safety decisions, KCS action decisions, publication readiness, data-handling boundaries, or final reviewer approval.

## Standard Feature Lifecycle

Every feature slice should follow this sequence:

```text
Define boundary
  -> define contract
  -> implement the smallest safe slice
  -> add validation/tests
  -> expose safe output
  -> document operator path
  -> gate promotion to the next risk level
```

This avoids the unstable shortcut:

```text
ticket in -> LLM prompt -> article out
```

The MVP should instead use explicit workflow state, typed packets, deterministic checks, and reviewer-ready outputs.

## Engineering Rules

### 1. Define the boundary first

Before implementing a feature, define what it may read, what it may output, and what it must not do.

Examples:

- PR-1 may use synthetic or approved sanitized fixtures only.
- Zendesk read-only ingest starts only in KCS-8.
- Claude handoff starts only after bounded packet contracts and validation exist.
- The MVP never writes to Zendesk, Help Center, Jira, Confluence, or customer-facing systems.

### 2. Define the contract before implementation

A feature should expose typed, schema-versioned packets or reports before it grows behavior.

Examples:

- normalized evidence packet;
- reuse/search result packet;
- KCS action decision packet;
- reviewer-ready KCS packet;
- validation report;
- ready/blocked loop state.

If the contract is unclear, the implementation should stay narrow until the contract is clarified.

### 3. Keep implementation slices small

Each PR should prove one behavior family.

Recommended slice order:

- KCS-1: packet contracts and fixtures;
- KCS-2: safety and evidence validation gates;
- KCS-3: KCS action decision engine;
- KCS-4: reviewer packet renderer and Zendesk HTML output;
- KCS-5: validation report and ready_for_reviewer loop state;
- KCS-6: CLI entrypoint for local verification;
- KCS-7: evidence package builder from approved fixtures/exported tickets;
- KCS-8: Zendesk read-only ingest adapter;
- KCS-9: Claude Enterprise/Desktop bounded handoff;
  - KCS-9a: semantic KCS item identification;
  - KCS-9b: bounded reviewer-assist handoff contract;
  - KCS-9c: reviewer-only draft generation;
- KCS-10: local reviewer bundle writer for audit/debug;
- KCS-11: live Claude provider adapter for real provider smoke tests;
- KCS-12: Claude Desktop MCP validator/control adapter and MCPB package;
- KCS-13: controlled semantic review fallback for complex/noisy approved
  clean tickets;
- KCS-14: engineering and codebase design hardening. This slice owns
  documentation ownership cleanup, spec-first process baseline, local tool
  entrypoints, functional test conventions, compact review context protocol,
  minimal code map, behavior-preserving codebase design refactor, and
  review/agent tooling after the manual protocol is stable;
- KCS-15: KCS authoring quality through source style/markup parity, Article
  Quality criteria, KCS practices, approved examples, assisted reuse, and
  portable `plesk_support` rules. This was deferred during KCS-14 and is now active
  through independently approved behavior slices. KCS-15.1 trigger parity and
  KCS-15.2a adapter feasibility is complete; KCS-15.2b1 bounded public
  comparison evidence is complete; KCS-15.2b2 Phase A exact public-article
  context is complete and the deterministic local controlled-comparison
  implementation is committed. Operational closeout remains open because the
  approved sanitized super-noisy canary reaches all five comparison decisions
  only in current-source replay; the latest boundary correction still needs
  commit/install/Desktop evidence and remaining `none_fit` drafts reach
  separate authoring-quality gates. Phase C in-chat UI is host-blocked and
  deferred pending a host-owned direct launcher. It remains outside KCS-14
  scope;
- Future harness-portable agent engineering support: git-aware code-review
  graph, compact agent context, official local tool entrypoints, and review
  handoffs for Codex, ChatGPT Pro review, Fable 5 review, or future internal
  runner. The source of truth remains repo-local docs, specs, scripts, tests,
  and graph artifacts;
- Post-KCS-15 process retrospective: decide whether the KCS-14 engineering
  process stayed stable through both a refactor-heavy slice and the KCS-15
  feature-heavy style/markup slice;
- KCS-16a: engineering process stabilization, only if the retrospective shows
  unstable specs, weak acceptance tests, poor review packets, unclear tool
  entrypoints, or recurring agent/review failures;
- KCS-16b: reusable engineering infrastructure extraction, only after the
  process is stable and a second project or independent subsystem confirms
  portability. This slice is not automatic: it starts only if the
  retrospective shows that the same templates, review packets, tool
  entrypoints, and gates worked across both refactor-heavy and feature-heavy
  slices with less manual correction. Extract only generic design/spec
  workflow pieces; KCS-specific contracts, ticket policy, privacy rules, and
  article standards stay in this repository;
- KCS-17: handoff and initiation boundary for a separate personal agentic
  engineering kit project, only after reusable extraction is stable and useful
  outside the immediate KCS workflow. KCS-17 may produce an export manifest,
  compatibility boundary, and evidence handoff; it does not implement agent
  roles, orchestration, the integration gate, or the stable kit package in this
  repository. The separate project assigns extracted assets to beta roles,
  runs the end-to-end integration gate, and packages a stable kit only after
  that gate passes. Choose its architecture after KCS-14/KCS-15 field results
  and a current review of agentic-engineering tooling;
- Future deployment slice: intranet remote MCP service for managed
  operator use. Claude Desktop would connect through a custom remote MCP
  connector URL to an internal service endpoint, not through the local MCPB
  stdio wrapper.

Do not move runtime integration, live Zendesk access, Claude handoff, or publication-adjacent behavior into earlier slices.

### 4. Fail closed

When data, evidence, search status, sanitizer status, article identity, or validation status is incomplete, the workflow should return a blocked or review-required state instead of guessing.

Examples:

- missing supported resolution -> blocked;
- unsafe input -> blocked;
- duplicate/reuse search not performed -> review blocker;
- multiple unrelated issues -> split_required;
- unsupported cause -> blocked;
- invalid Zendesk HTML -> review_blocked or markup_blocked;
- validation not rerun after draft changes -> not ready_for_reviewer.

### 5. Separate search from issue identity

Search is symptom-oriented. Issue identity is not.

The workflow may search existing articles by symptoms, error text, product area, and environment signals.

For Technical SCR articles, the issue identity should be based on the article type plus the supported cause-resolution pair. Symptoms may vary across tickets.

For How-to Q&A articles, the identity should be based on the question-answer pair.

This prevents both duplicate articles and incorrect reuse.

### 6. Keep adapters outside the core

The core pipeline should be runtime-independent Python logic.

Adapters may fetch or prepare inputs, but they must not own KCS decisions.

Examples of adapters:

- fixture loader;
- temporary local/public RAG search adapter;
- future kcs-search-mcp adapter;
- Zendesk read-only ingest adapter;
- Claude Enterprise/Desktop handoff adapter.

The core receives normalized packets and returns typed decisions, reviewer packets, and validation reports.

### 7. Treat Claude output as untrusted draft text

Claude may receive only bounded, approved packets according to the Data Handling Baseline.

Claude output must be validated before it can be marked reviewer-ready.

The core must not assume that Claude followed instructions, templates, KCS style rules, privacy rules, or Zendesk HTML requirements.

### 8. No repo artifacts during normal workflow

Normal KCS runs should not create draft articles, temporary candidate files, ticket extracts, or runtime reports inside committable repository paths unless the command explicitly asks to write a named artifact.

Temporary runtime files should stay outside the repo or inside ignored cache/runtime storage.

Generated runtime artifacts are not product source.

### 9. Keep observability safe

Logs and reports should use opaque IDs, statuses, blocker codes, schema versions, and validation summaries.

They must not contain raw ticket text, raw Zendesk JSON, customer identifiers, raw search queries, raw snippets, vector values, internal article chunks, credentials, private paths, or source-ticket quotes.

### 10. Documentation must stay aligned

When a feature changes behavior, update the corresponding document or explicitly explain why no doc update is needed.

Relevant source documents:

- `docs/internal/kcs-authoring-mvp-goal-and-success-criteria.md`;
- `docs/internal/kcs-authoring-mvp-data-handling-baseline.md`;
- `docs/internal/kcs-core-pipeline-architecture-and-contracts.md`;
- `docs/internal/kcs-core-pipeline-technical-design.md`;
- `docs/internal/kcs-authoring-mvp-jira-tracking.md`.

Product and architecture commitments belong in `docs/internal/`.

### 11. Deterministic quality gates for generated or assisted code

Prose guidance and process notes are not enforcement. The project must rely on
deterministic checks for code quality, contract safety, and regression
prevention.

For Python implementation slices, quality gates should include:

- contract and fixture tests for every packet schema;
- focused unit tests for safety, decision, validation, and rendering behavior;
- `git diff --check` before commit;
- Ruff linting and import checks once `pyproject.toml` tooling is active;
- a strict McCabe complexity threshold for new Python logic.

For this MVP, new decision, validation, sanitizer, renderer, and adapter functions should stay small and testable. A McCabe complexity threshold of `7` is the default target for AI-assisted code. If a function exceeds it, prefer decomposing the function before adding more branching behavior.

Quality gates should be introduced progressively:

- KCS-1: package/test baseline, contract tests, fixture checks, Ruff configuration;
- KCS-2: safety/evidence gate tests and unsafe fixture rejection tests;
- KCS-3: deterministic decision matrix tests;
- KCS-4: renderer and Zendesk HTML validation tests;
- KCS-5: loop-state and readiness validation tests;
- KCS-6: CLI output stability tests;
- KCS-8/KCS-9: adapter and bounded handoff tests with approved inputs only.

CI can be added after the local command set is stable. CI should block merges on tests and lint/format checks once enabled.

## Risk Levels and Promotion Gates

The MVP should not promote to a higher-risk scope just because tests pass at a lower-risk scope.

```text
synthetic fixture
  -> approved sanitized fixture
  -> exported approved ticket evidence
  -> read-only Zendesk ingest
  -> bounded Claude handoff
  -> approved pilot
```

Each promotion requires explicit scope, validation, and approval appropriate to that risk level.

Examples:

- Passing fixture tests does not approve live Zendesk access.
- Passing local CLI tests does not approve Claude-visible raw ticket data.
- Passing HTML validation does not approve Help Center publication.
- Reviewer-ready output does not mean auto-publication.

`auto_publish_allowed` must remain `false` for MVP outputs.


## Client Integration Readiness Gate

This gate applies only to adapter and client integration work, such as Zendesk read-only ingest, MCP connector paths, Claude Enterprise/Desktop handoff, future `kcs-search-mcp`, or future internal search adapters.

It is not required for pure KCS core slices such as packet contracts, fixtures, deterministic gates, decision logic, renderer logic, validation reports, or local CLI checks.

Before any adapter/client path is used with a real client or approved pilot input, the implementation must pass a readiness sequence:

```text
profile contract and threat model
  -> allowed tool surface
  -> preflight / smoke / dry-run
  -> operator readiness
  -> rehearsal / practice-run
  -> manual synthetic attempt
  -> enum-only closeout
  -> security or next-scope decision
```

The purpose is to prove that the client-visible surface is safe before moving beyond synthetic or approved sanitized inputs.

This gate must confirm:

- allowed tools are explicitly listed;
- forbidden tools are absent;
- resources, prompts, templates, and hidden data surfaces are not exposed unless explicitly approved;
- tool outputs are bounded and safe for the target runtime;
- no customer-facing writes, publication actions, or unsupported corporate-resource access are introduced;
- a successful dry-run does not automatically approve real ticket use, Claude-visible raw ticket data, customer replies, or Help Center publication.

Detailed readiness procedure should be documented in tracked project docs before adapter/client integration work starts.

## PR Expectations

Each implementation PR should state:

- Jira subtask scope;
- changed contracts or explicitly unchanged contracts;
- data-handling assumptions;
- validation commands run;
- fixtures added or changed;
- known risks or deferred behavior;
- confirmation that no publication/write behavior was added.

For documentation-only PRs, explain which implementation slice the document supports and whether it changes engineering behavior.

## Validation Expectations

Validation should be proportional to the slice.

Minimum expectations:

- packet contracts have schema/version tests;
- fixtures have privacy/safety scans;
- safety gates have allowed/blocked input tests;
- decision engine has deterministic action tests;
- renderer has Zendesk HTML structure tests;
- loop state has ready/blocked transition tests;
- CLI has fixture-based smoke tests;
- adapters have no-write and no-secret tests.

Do not use live Zendesk or Claude connector tests before their dedicated slices.

## Semantic Extraction Boundary

The KCS core does not pretend that pure Python can reliably understand long
support-ticket narratives. Semantic extraction from narrative text is an
evidence-preparation concern, not KCS decision-core logic.

Allowed pattern:

```text
human/fixture/deterministic parser/bounded Claude extraction
  -> candidate evidence fields
  -> Python sanitizer/normalizer/validator
  -> accepted packet or blocker
```

KCS-1 defines packet contracts and fixtures only. KCS-7 may define evidence
package builder behavior and extraction interfaces, but it does not call Claude
or perform semantic KCS item identification from ticket narrative. KCS-9a may
introduce bounded Claude-assisted KCS item identification if approved. KCS-9b
may introduce a bounded reviewer-assist handoff contract from compact safe
summaries. KCS-9c may introduce reviewer-only draft generation. No slice may
make an LLM the owner of packet acceptance, KCS action decisions, safety gates,
or readiness state.

## Portability From `plesk_support`

The local `plesk_support` project is reference material, not a source project to copy wholesale.

Reusable lessons:

- workflow-first architecture;
- typed packet contracts;
- deterministic gates;
- value-free blocker/status codes;
- fixture-driven tests;
- HTML validation before reviewer handoff;
- no-auto-publish invariant;
- bounded LLM handoff.

Any code adapted from `plesk_support` must be reviewed for portability, data boundaries, source-project assumptions, and test coverage before it is committed.

## First Implementation Anchor

The first code PR should be KCS-1 only:

```text
packet contracts + safe fixtures + basic contract tests
```

It should not implement safety gates, KCS decision logic, renderer behavior, CLI orchestration, Zendesk ingest, search adapters, or Claude handoff.

Those belong to later Jira slices.
