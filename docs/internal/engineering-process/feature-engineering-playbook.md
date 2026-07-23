# Feature Engineering Playbook

## Purpose

Local developer playbook for implementing KCS Authoring MVP features in controlled slices.

This document is development-time guidance. Product, data-handling, and architecture commitments live in `docs/internal/`.

## Default Feature Flow

Use this sequence for every implementation slice:

```text
requested outcome and operational baseline
  -> target UX and design evidence
  -> exact integration operational feasibility when applicable
  -> Operator Decision Readiness
  -> design selection
  -> separate Delivery authorization
  -> boundary and contract
  -> smallest safe implementation
  -> validation/tests
  -> safe output/report
  -> docs update or explicit no-doc note
  -> next gate decision
```

Do not start from a broad end-to-end workflow unless the earlier contracts and gates already exist.

If a slice reuses an existing runtime/API capability, check the exact endpoint,
mode, request, response shape, and required operating condition before
substantial implementation. Use fresh evidence or one bounded safe smoke with
a declared claim and stop condition. Fixtures remain required for deterministic
contract coverage, but they do not establish live operational compatibility.

## Approval And Enabling-Slice Containment

For a behavior-changing slice, keep these decisions independent:

```text
outcome agreement
design selection
Delivery authorization
```

An operator may grant two decisions together only by stating both. A plain
design selection leaves Delivery locked. General continuation wording applies
only to work already inside the selected and authorized boundary.

An enabling slice such as an isolated adapter, spike, prototype, or bounded
experiment may have its own explicit design and Delivery authorization. Its
closeout must state:

- the feasibility question answered;
- evidence produced and its limits;
- parent UX/design state;
- parent integration authorization state;
- remaining decision-readiness evidence.

Enabling-slice success proves feasibility only. It does not approve the parent
UX, select the parent design, authorize integration, or widen the next slice.
The parent Delivery state remains locked until the parent decision is ready,
selected, and separately authorized.

## Material Design Review At Closeout

Before closing a material implementation, refactor, deployment, or integration
slice, apply the compact Ousterhout gate in
`docs/internal/engineering-process/spec-first-engineering-playbook/06-review-checklist.md`.

The gate is triggered by a material ownership, interface, dependency,
persistence, failure, integration, abstraction, deployment-boundary, or
internal algorithm/control-flow complexity change. It is not triggered merely
because a file is under `src/` or because a small leaf implementation changed.
A non-triggered closeout records only the gate status and a concrete reason.
A large internal change is reviewed even when its external interface remains
stable.

The closeout record is a design review, not an implementation tutorial. It
must say what complexity the slice hides, who owns it, what callers no longer
need to know, whether leakage or change amplification grew, whether complexity
was removed or moved, the residual risk, and the reviewer verdict.

## Slice Discipline

Each PR should map to one Jira slice:

- KCS-0: data handling baseline and implementation scope;
- KCS-1: packet contracts and fixtures only;
- KCS-2: safety and evidence gates;
- KCS-3: deterministic KCS action decision;
- KCS-4: reviewer packet and Zendesk HTML rendering;
- KCS-5: validation report and ready/blocked loop state;
- KCS-6: local CLI verification;
- KCS-7: evidence package builder from approved fixtures/exported tickets;
- KCS-8: Zendesk read-only ingest adapter;
- KCS-9: Claude Enterprise/Desktop bounded handoff;
  - KCS-9a: semantic KCS item identification;
  - KCS-9b: bounded reviewer-assist handoff contract;
  - KCS-9c: reviewer-only draft generation;
- KCS-10: local reviewer bundle writer for audit/debug artifacts;
- KCS-11: live Claude provider adapter for real provider smoke tests;
- KCS-12: Claude Desktop MCP validator/control adapter and MCPB package;
- KCS-13: controlled semantic review fallback for complex/noisy approved clean
  tickets;
- KCS-14: engineering and codebase design hardening. This slice owns
  documentation ownership cleanup, spec-first process baseline, local tool
  entrypoints, functional test conventions, compact review context protocol,
  code-review graph baseline, behavior-preserving codebase design refactor, and
  review/agent tooling after the manual protocol is stable;
- KCS-15: KCS authoring quality through source style/markup parity, Article
  Quality criteria, KCS practices, approved examples, assisted reuse, and
  portable `plesk_support` rules. This was deferred during KCS-14 and is now active
  through independently approved behavior slices. KCS-15.1 trigger parity and
  KCS-15.2a adapter feasibility is complete; KCS-15.2b1 bounded public
  comparison evidence is complete; KCS-15.2b2
  Desktop/model/operator integration remains Delivery-locked. It remains
  outside KCS-14 scope;
- Future deployment slice: optional managed internal service version of the
  current local Claude Desktop workflow.

If a change touches multiple slices, split it unless there is a clear reason not to.

## Core Rules

- Keep KCS core runtime-independent.
- Keep adapters outside the core.
- Keep packet contracts schema-versioned.
- Keep validation deterministic.
- Keep Claude output treated as untrusted draft text.
- Keep `auto_publish_allowed=false` in MVP outputs.
- Keep normal workflow artifacts out of committable repository paths.
- Keep logs and validation summaries code/enum-based, not evidence-text-based.

## Semantic Extraction Planning

`CandidateSemanticExtraction` is a future internal intermediate packet, not a
KCS-1 deliverable.

Use this split:

```text
CandidateSemanticExtraction
  -> what a human/parser/bounded Claude extractor thinks the ticket means

NormalizedTicketEvidencePacket
  -> what Python validation accepts as safe normalized evidence
```

Implementation rule:

- KCS-1 must not implement `CandidateSemanticExtraction`.
- KCS-1 fixtures should be already-normalized packet fixtures.
- KCS-7 may define the extraction interface if evidence package building needs
  it, but it must not call Claude or perform semantic KCS item identification.
- KCS-9a may add bounded Claude semantic KCS item identification if approved.
- KCS-9b may add a bounded reviewer-assist handoff contract from compact safe
  summaries.
- KCS-9c may add reviewer-only draft generation from validated handoff packets.
- KCS-10 may write local reviewer bundles from already-validated packets and
  validated draft/handoff artifacts.
- KCS-11 may call an explicitly configured provider adapter for bounded smoke
  tests after KCS-9b/KCS-9c validation.
- KCS-12 may expose a thin Claude Desktop MCP control surface, but Python must
  still own workflow state, validation, decisions, rendering, and bundle
  output.
- KCS-13 may expose bounded selected excerpts for controlled semantic review
  only when clean-ticket metadata, hash, and eligibility gates pass.
- KCS-14 may harden engineering process, review support, test conventions, and
  behavior-preserving codebase design, but must not change data boundaries,
  model ownership, style/markup behavior, or runtime contracts.
- KCS-15 may harden KCS style, markup, validation, and golden cases, but must
  not change data boundaries or model ownership.
- The KCS decision engine must consume `NormalizedTicketEvidencePacket`, not
  raw extraction output.

## Client Integration Readiness Procedure

Use this only for adapter/client integration work, especially KCS-8 through
KCS-13 and the future deployment slice.

It is not required for KCS-1 through KCS-6 pure core development.

### When Required

Run this readiness procedure before any manual attempt through:

- Claude Desktop or Claude Enterprise connector;
- MCP connector/server path;
- Zendesk read-only adapter connected to approved tickets;
- future internal search adapter;
- any runtime that can expose tool output to a hosted model or external client.

### Required Sequence

```text
design / ADR note
  -> profile contract and threat model
  -> allowed tool surface
  -> implementation slice
  -> unit and contract tests
  -> preflight / smoke / dry-run
  -> operator readiness
  -> rehearsal
  -> practice-run
  -> manual synthetic attempt
  -> enum-only closeout
  -> security / next-scope decision
```

### Design / ADR Note

Before implementation, record:

- why the adapter/client path is needed;
- which Jira slice owns it;
- allowed inputs;
- allowed outputs;
- forbidden tools/actions;
- whether any hosted model may see outputs;
- whether corporate resources are involved.

### Profile Contract

Define at minimum:

- target client/runtime;
- inference location;
- tool execution location;
- allowed input classes;
- allowed tool list;
- forbidden tool list;
- whether ticket context is allowed;
- whether internal knowledge is allowed;
- whether customer reply generation is allowed;
- whether write/publish actions are allowed.

Default MVP answer for write/publish/customer-reply actions is no.

### Tool Surface Checks

Before a manual client attempt, verify:

- only expected tools are exposed;
- forbidden tools are absent;
- resources/prompts/templates are absent unless explicitly approved;
- tool schemas match expected contracts;
- tool responses are bounded and safe;
- private-looking probes do not echo unsafe values.

### Preflight / Smoke / Dry-run

Preflight may prove wiring, but it does not approve real ticket use.

A successful dry-run means only:

- configuration is coherent;
- local/runtime startup works;
- expected safe tools respond;
- no forbidden client-visible surface is exposed.

It does not mean:

- live Zendesk access is approved;
- Claude-visible raw ticket data is approved;
- customer replies are approved;
- Help Center publication is approved.

### Operator Readiness

Before a manual synthetic attempt, prepare:

- startup commands;
- expected visible tools;
- synthetic prompt/input;
- stop conditions;
- closeout command or checklist;
- validation command;
- troubleshooting notes.

### Rehearsal

Run rehearsal for one selected client/runtime path.

Rehearsal should answer:

- is the selected client path configured enough for one synthetic attempt?
- are allowed/forbidden surfaces understood?
- are stop conditions clear?
- are logs and outputs safe?

Rehearsal must not use real tickets by default.

### Practice-run

Practice-run is the final pre-manual-attempt package.

It should include:

- exact client to open;
- exact prompt to use;
- expected safe output shape;
- what to do if forbidden output appears;
- how to record enum-only closeout.

### Manual Synthetic Attempt

Manual attempt must use synthetic or approved sanitized input only unless a later scope explicitly approves real ticket use.

The attempt should not create customer-facing changes, publish articles, update tickets, or write to corporate systems.

### Closeout

Record closeout with safe enum/status values only:

- passed;
- blocked_config;
- blocked_tool_surface;
- blocked_data_handling;
- blocked_model_behavior;
- blocked_validation;
- needs_security_review;
- needs_scope_change.

Do not store raw prompts, raw outputs, ticket data, snippets, chunks, or private identifiers in closeout logs.

## Documentation Updates

For pure core changes, update docs only when contracts, data handling, architecture, or Jira scope changes.

For adapter/client changes, update the relevant readiness notes and identify whether the change promotes the MVP to a higher risk level.

## Common Anti-patterns

Avoid:

- ticket in -> prompt -> article out;
- adding a connector before packet contracts exist;
- allowing Claude to decide final KCS action without code validation;
- treating local MCP execution as automatically private when hosted inference can see tool output;
- writing runtime drafts into the repo during normal workflow;
- logging validation summaries with copied evidence text;
- merging search adapter behavior into KCS core;
- using a successful synthetic test as approval for real ticket data.
