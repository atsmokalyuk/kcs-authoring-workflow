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
  -> tracked material slice plan
  -> separate Delivery authorization
  -> boundary and contract
  -> smallest safe implementation
  -> validation/tests
  -> built/installed runtime identity gate when applicable
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

If the target UX relies on an unfamiliar interaction, an unproved host UI
capability, or a material operator-comfort/cognitive-load judgment, proactively
offer the smallest safe fixture-only walkthrough or UX smoke before production
implementation. The smoke must expose the real decision context closely enough
for the operator to evaluate the interaction, while keeping production
behavior, data, integration, and persistence locked. Record the decision claim,
fixture/condition, exercised interaction, simulated limits, permitted
corrections, evidence budget, and stop condition. A successful UX smoke is
Design evidence only; it does not select the production design or authorize
production Delivery.

Use a progressive evidence ladder. Start with a static example, wireframe, or
clickable fixture that requires no product/runtime installation. Escalate to an
isolated component/protocol harness, then an installed-host smoke, only for
unknowns the cheaper level cannot resolve. Packaging, client activation,
runtime restart, or deployment is justified only when the decision depends on
the real host's rendering, lifecycle, permissions, navigation, or tool routing.
Record the unresolved claim that caused each escalation and stop at the first
level sufficient for the material design decision.

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

## Tracked Material Design Gate

Before requesting or acting on Delivery authorization for a material feature
or slice, create or update its authoritative plan under
`docs/internal/engineering-process/slice-plans/`.

The plan must contain enough current evidence for a later agent or reviewer to
continue without reconstructing the design from chat:

- requested outcome and operational baseline;
- every parent or incident-driven operational outcome that this slice claims
  to resolve, together with the evidence class required to prove it;
- intended entrypoint, target UX, and selected design boundary;
- confirmed, provisional, unknown, and rejected material facts;
- complete unknown inventory and relevant stop conditions;
- Operator Decision Readiness evidence and approval ledger;
- changed and unchanged contracts;
- acceptance-to-gate mapping and model/experiment contract when applicable;
  for a branching or stateful workflow, enumerate the supported
  outcome-by-context transition matrix, including single-item, batch,
  continuation, retry/replay, and terminal behavior where those contexts
  exist;
- authorized and still-locked Delivery phases.

Chat should show only the compact decision-relevant projection. It does not
replace the tracked plan.

If the operator selects or authorizes the slice before the plan is written,
record the selected boundary and exact authorization before implementation.
If later evidence or an operator correction changes the selected design, update
the plan before continuing Delivery.

A small mechanical edit or bounded leaf bugfix may rely on an existing tracked
contract and tests instead of creating a new slice plan when no material
behavior, privacy, schema, persistence, integration, deployment, or
public/reviewer-output boundary changes.

## End-to-End Enforcement Reachability Gate

Before selecting a design or authorizing Delivery for a claimed safety or
workflow invariant, map every supported operator/system entrypoint to the first
deterministic enforcement owner:

```text
supported entrypoint
  -> user-, app-, or model-controlled transitions
  -> first deterministic gate
  -> allowed terminal outcomes
  -> bypass paths before or around the gate
```

Classify control honestly:

- code or an app/controller that directly invokes the gate is deterministic
  within its declared boundary;
- a user-selected prompt or command is an explicit entrypoint, but remains
  model-mediated when the model can answer without invoking the gate;
- a model-controlled tool call is optional behavior and cannot enforce an
  invariant that also covers the period before that call;
- inventory direct model responses and every alternative host tool that can
  produce the prohibited outcome. A guarded connector does not enforce an
  end-to-end invariant when the same model can bypass it through a generic file,
  browser, shell, messaging, or artifact action.

If any supported entrypoint can produce a prohibited outcome before reaching
the gate, Design is not ready. Choose one:

- move the gate earlier behind a user/app-controlled entrypoint;
- restrict and document the supported entrypoint;
- weaken the claim to best-effort behavior and obtain explicit operator
  approval for that weaker contract.

Tool descriptions, system instructions, fixtures, and one successful model
run may improve or demonstrate routing. They do not convert model-controlled
tool selection into deterministic enforcement.

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
  comparison evidence is complete; KCS-15.2b2 Phase A exact public-article
  context is complete, while Phase B Desktop/operator Delivery is authorized
  and its implementation/installed-model smoke closeout remains active. It
  remains outside KCS-14 scope;
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
  -> build / install / reload identity
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

Before any installed-client, model, or operator trial, verify the complete
runtime identity chain:

```text
current source
  -> current built artifact
  -> installed files, client registry/cache, and explicit enabled/activation state
  -> reloaded client process
  -> every dependency service's source revision / process / config-data identity
  -> exact required capability on those same live instances
  -> deterministic installed-runtime preflight
  -> model/operator trial
```

The agent owns this preparation when local mutation is already authorized. Do
not give the operator a prompt or ask them to diagnose a trial until the
installed runtime is proven to match the current source and built artifact.
Source-only tests, a successful package build, matching version strings, or an
installed package that matches only a registry entry are insufficient. Verify
the host's separate enabled/activation state when one exists; discovery,
allowlisting, or `can_install` success does not prove that the host will launch
the component. If the client caches tools or schemas, restart/reload it and
verify the live surface before the trial. For a dependency owned by another
repository or worktree,
record the expected revision and the observed running executable/process
provenance. Evidence from a different worktree, process, deployment, or earlier
runtime instance does not transfer to the current trial. When a service cannot
self-report a revision or artifact identity, run the bounded exact capability
probe required by the slice and keep provenance `provisional`; do not infer
freshness from a generic health/status endpoint. A stale-identity result is a
Delivery/preflight failure, not model behavior evidence.

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

### Duplicate And Re-entrant Continuation Gate

For a stateful or side-effecting tool/API continuation, define retry behavior
before an installed-client or model trial. Assume the client may submit the
same logical action twice before receiving the first response.

The contract must state:

- the idempotency or opaque operation/ref owner;
- whether an exact logical duplicate replays the first result or returns a
  deterministic no-op;
- the TTL and memory/persistence bound for replay state;
- that a duplicate cannot repeat the side effect;
- that a conflicting replay remains invalid;
- that a stale or conflicting prior ref cannot consume a newer unrelated
  pending operation;
- how equivalent accepted call shapes are normalized;
- the deterministic test that sends the duplicate while the next workflow
  state is active.

Prompt instructions such as “call once” are not enforcement. A successful
single-call fixture or smoke does not prove retry safety.

### Representative Operational Outcome Gate

Before closing a material slice, compare its validation evidence with the
requested outcome and every parent incident or canary that the slice claims to
resolve.

Classify each validation result as one of:

- deterministic fixture or contract evidence;
- synthetic installed/runtime feasibility evidence;
- approved sanitized representative-case evidence;
- production-like or real operational evidence.

Synthetic evidence may prove mechanics, safety, wiring, or feasibility. It
does not prove that a named real-ticket failure, noisy input, deployment
incident, or parent operational outcome is resolved.

When a material slice is motivated by a named operational failure, its tracked
plan must name a safe representative case, the supported entrypoint, fixed
conditions, expected outcome, invariants, permitted corrections, and stop
condition. Before closeout, run that case at the evidence level required by the
claim. Use approved sanitized input rather than raw/private data unless a
separate data-handling decision allows otherwise.

If the representative case is unavailable, unsafe, fails, or is intentionally
deferred, narrow the completion claim explicitly. Record the mechanism as
feasible or locally verified and keep the parent outcome open; do not replace
the missing evidence with additional synthetic successes.

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

### Version-Control And Artifact Closeout Gate

Pre-commit tests, package builds, and installed smokes may be used for
implementation feedback and feasibility. They do not by themselves complete a
repository slice.

Before declaring a material slice delivered, promoted, or ready for the next
material slice:

- isolate the intended diff from unrelated, deferred, and user-owned work;
- review the staged content against the tracked slice boundary;
- run the required gates against that isolated content;
- create the coherent slice commit, or record an explicit operator-approved
  no-commit/defer disposition;
- map the built and installed artifact evidence to that commit's content, or
  rebuild and repeat the required identity/preflight gate from the commit;
- record the commit, validation, artifact identity, and remaining risks in the
  closeout.

An installed artifact built from an uncommitted or mixed worktree is
provisional evidence. It may demonstrate the behavior under test, but the
slice remains open until its source boundary and Git traceability are closed;
the accepted artifact must be traceable to the committed content.

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
