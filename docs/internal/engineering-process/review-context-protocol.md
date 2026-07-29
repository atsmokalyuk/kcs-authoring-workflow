# Review Context Protocol

Status: authoritative KCS-14 Slice 4 review-context specification.

This document defines compact review handoff packets for Codex, ChatGPT Pro
review, Fable 5 review, and a possible future internal runner. It is an
engineering workflow surface, not a runtime product contract.

## Purpose

Review packets reduce context drift by giving reviewers the smallest useful
set of authoritative facts: intent, changed files, affected contracts,
validation, known risks, and what must not change.

The packet should make review precise without exposing private artifacts or
turning chat history into a source of truth.

## Ownership

- This file owns the review packet protocol and promotion candidate protocol.
- The pull-request description owns the material review handoff and validation
  record; durable product or architecture decisions belong in their existing
  authoritative documents.
- `docs/internal/engineering-process/promotion-candidates.md` owns the
  registry of repeated findings that may move down the enforcement ladder.
- `docs/internal/engineering-process/tool-entrypoints.md` owns validation
  commands.
- `docs/internal/engineering-process/agent-operable-engineering-workflow.md`
  owns general agent context hygiene.

## Packet Location

Use the pull-request description as the default durable review packet. Every
material feature/slice separately keeps its authoritative design under
`docs/internal/engineering-process/slice-plans/`; the review packet links that
plan and does not duplicate it. Other tracked design or decision documents are
created only when their content remains authoritative after the PR closes. Do
not create a separate Markdown file for each batch, review pass, or transient
checkpoint.

## Required Sections

Each material review packet must include:

- `Review Task`;
- `Active Slice Plan`;
- `Slice Intent`;
- `Changed Files`;
- `Affected Contracts`;
- `Relevant Tests`;
- `Validation`;
- `Known Deferred Risks`;
- `Must Not Change`;
- `Stale Context To Ignore`;
- `Promotion Candidates`;
- `Questions For Reviewer`.

## Active Slice Plan Gate

`Active Slice Plan` is the autonomous handoff from Design into Delivery and
review. Use this compact shape:

```text
Active Slice Plan:
Path: docs/internal/engineering-process/slice-plans/<plan>.md
Authorized Delivery phase:
Still locked:
Plan/diff alignment: pass | revise | blocked
```

Before reviewing implementation details, the reviewer must resolve the
repo-relative path and verify:

- the file is already tracked or is included in the intended/staged diff;
- the requested outcome and selected boundary cover the implementation diff;
- the exact changed phase is recorded as Delivery-authorized;
- still-locked phases, contracts, and data boundaries are untouched;
- acceptance gates and unchanged contracts cover the changed behavior;
- later operator corrections are reflected in the tracked plan;
- the plan does not use feasibility evidence as stability or parent-integration
  approval.

A missing plan, nonexistent path, locked changed phase, or material plan/diff
mismatch is a review blocker. `Plan/diff alignment: pass` is a named human-review
verdict; a policy test may enforce field presence but must not claim to judge
semantic alignment.

`Affected Contracts` may start as a manual list. After Slice 5, review packets
should reference affected code-map nodes from
`docs/internal/engineering-process/code-review-graph.json` where practical.
The node list is an index to the relevant boundaries, not a substitute for
changed files, tests, or unchanged-contract evidence.

## Forbidden Content

Review packets must not include:

- raw ticket text;
- raw internal comments;
- selected semantic-review excerpt text;
- reviewer bundle bodies;
- provider payloads;
- credentials, tokens, keys, secrets, or private endpoints;
- customer identifiers;
- live domains, hostnames, server IPs, license IDs, or private filesystem
  paths;
- full logs or full HTML output.

Use opaque refs, hashes, counts, status codes, value-safe debug codes, and
repo-relative paths instead.

## Output Budget

Keep review packets compact:

- summarize intent in one short paragraph;
- link the active slice plan and state only the authorized/locked phases;
- list changed files by repo-relative path;
- include only relevant validation commands and results;
- include links or paths to artifacts instead of pasting artifact bodies;
- ask focused questions that a reviewer can answer from the packet and diff.

If a reviewer needs a full local artifact, provide a path and privacy caveat
instead of copying the artifact into the packet.

## Promotion Candidate Protocol

Recurring review findings should move through the enforcement ladder only when
the target layer can enforce the rule honestly.

Use this cadence:

```text
Once = review note, not a registry entry.
Twice = review checklist item.
Three times = candidate for test/tool/check.
Stable across KCS-14 and KCS-15 = reusable infrastructure candidate.
```

Every material recurring finding should be classified as one of:

- deterministic check candidate;
- structural boundary candidate;
- advisory review tripwire;
- measurement-only signal.

Do not automate design judgment with blocking regex checks. Deep module
quality, ownership-vs-time decomposition, classitis, and information leakage
remain review-gated unless a narrow mechanically decidable rule emerges.

## Compact Ousterhout Closeout Record

Material implementation, refactor, deployment, and integration review packets
must include the compact Ousterhout record defined in the spec-first review
checklist. This applies when the change creates or moves a module/service,
ownership boundary, interface, dependency, persistence/failure boundary,
deployment topology, material abstraction, or material internal
algorithm/control-flow complexity.

Required `reviewed` shape:

```text
Ousterhout gate: reviewed
Trigger:
Complexity hidden:
Owner and what it must not know:
Interface depth and caller cognitive load:
Information leakage and change amplification:
Complexity removed, moved, or added:
Residual design risk:
Verdict: pass | revise | reject
```

For a small leaf change, use only the short exception form:

```text
Ousterhout gate: not triggered
Not-triggered reason: small leaf change; no material boundary, abstraction,
  algorithm, control-flow, or internal-complexity change
```

A large internal change is reviewed even when its external interface remains
stable. Deterministic policy may check that the applicable shape exists; the
reviewer owns the design judgment. Missing triggered evidence or an unresolved
`revise` / `reject` verdict blocks closeout.

## Agent Promotion Responsibility

Promotion discovery is automatic at aggregate closeout and after a repeated
validation or review failure with the same cause. The development agent must
surface a promotion candidate when a process finding is repeated, stable, or
mechanically checkable.

Staged-diff review may attach evidence to an already identified candidate, but
it does not require a fresh registry scan or a `none` declaration for every
micro-batch.

Promotion implementation is approval-gated. The operator should only need to
approve or reject surfaced promotions; the operator should not need to remember
to ask whether a candidate exists.

The agent should propose:

- the rule or finding;
- why it now qualifies for promotion;
- the target layer;
- the suggested owner slice or follow-up commit;
- the validation that would prove the promotion.

The agent must not silently implement unrelated promotion work inside a feature
or refactor slice. Promotion implementation should be its own small scoped
action or commit, unless the promotion directly locks in the current slice's
accepted outcome.

## Promotion Checkpoints

The agent must check promotion candidates at these checkpoints:

- during aggregate review or aggregate closeout;
- after repeated validation or review failure with the same cause.

Every aggregate closeout must say either:

```text
Promotion candidates: none
```

or:

```text
Promotion candidates:
- <rule / finding>
```

Counts must come from
`docs/internal/engineering-process/promotion-candidates.md` and merged pull
requests or final closeout records. The agent must not rely on chat memory to
decide whether a finding is repeated. Micro-batch closeouts only mention
promotion when they add evidence to an existing candidate or surface a new
repeated finding.

Use stable value-safe finding codes such as `KCS14-PROMO-NNN` when recording
promotion candidates. Without a code or closeout entry, a finding does not
count toward the repeated-finding threshold.

## Promotion Readiness Gates

The agent must propose a promotion candidate when any trigger is true:

- the same finding code appears in two or more material slice reviews or
  closeouts;
- the same validation or review failure happens two or more times in one
  material slice;
- the same command or check is required in three or more consecutive slices;
- a rule is stable, mechanically checkable, and low false-positive risk;
- a runtime or safety contract is repeatedly checked manually;
- a reviewer explicitly asks for a test, tool, freeze-list check, code-map
  entry, or reusable-infrastructure candidate.

The agent may propose a candidate when a finding appears once but is high risk,
cheap to check, or directly locks in the current slice outcome.

The agent must not implement promotion automatically when any of these are
true:

- the promotion changes runtime behavior;
- the promotion adds broad tooling or a framework;
- false-positive risk is medium or high;
- the rule requires design judgment;
- the rule is KCS-specific but proposed as generic reusable infrastructure;
- the promotion touches files unrelated to the current slice.

Implicit approval is allowed only when all must-not conditions are false and
the diff is limited to `tests/policy/` plus the current slice's process docs.
All other material promotions need explicit operator or reviewer approval.

AI reviewer suggestions may trigger a proposal, but model output never grants
implicit approval.

Use a short form for implicit-path checks:

```text
Rule / finding:
Trigger:
Scope:
Validation:
```

Use the full promotion-candidate template for material promotions.

## Promotion Scope

The registry is for repeated process findings that may move to a stronger
enforcement layer. It is not an intermediate queue for every defect or design
question:

- runtime and contract defects go directly to focused regression tests when
  the expected behavior is known;
- parked ownership or import-contract questions stay in the code map, design
  notes, or an explicitly scoped follow-up;
- deterministic checks may be blocking immediately when they are narrow,
  low-noise, and directly lock in an accepted outcome;
- advisory measurements remain advisory until a separately approved threshold
  exists.

Candidates remain in the registry while they have an owner or durable repeated
evidence. No probation, demotion, or time-based expiry state machine is
maintained.

## Promotion Candidate Fields

When a finding becomes a promotion candidate, record it in
`docs/internal/engineering-process/promotion-candidates.md` with:

- `Finding code`;
- `Rule / finding`;
- `Seen in`;
- `Evidence`;
- `Trigger`;
- `Manual correction needed`;
- `Can be checked mechanically`;
- `False-positive risk`;
- `KCS-specific or generic`;
- `Promotion target`;
- `Target layer`;
- `Decision`;
- `Owner slice`;
- `Scope`;
- `Validation`;
- `Approval`;
- `Status`.

Valid promotion targets:

- policy test;
- tool entrypoint or wrapper;
- freeze-list or hash check;
- code-map entry;
- review checklist item;
- measurement-only closeout field;
- reusable infrastructure candidate.

## Review Harness Routing

Use review harnesses by role:

- Codex review: staged diff, local repo context, policy/test/doc consistency.
- ChatGPT Pro review: broader reasoning on process, wording, and missing
  gates when no local tool access is required.
- Fable 5 review: external review of sequence, risk boundaries, missing gates,
  and slice boundaries.
- Future internal runner: only after the packet format, code map, and
  validation commands are stable.

Review harnesses are not development harnesses. Claude Desktop remains a
runtime/product smoke surface, not a planning or code-review harness.

## Closeout Requirements

Every material slice closeout should answer:

- what changed;
- what contracts did not change;
- what validation ran;
- what findings remain;
- which findings, if any, were added to promotion candidates;
- whether the next slice gate is satisfied.

For refactor-heavy slices, the closeout may link to a refactor-log entry
instead of repeating the full design rationale. The log entry should remain
evidence-oriented: outcome-contract reason, applied design lens, behavior
mapping, validation evidence, and follow-up risks. It must not store raw/private
artifacts or full command output.

If a refactor closeout cites the complexity sensor, include the full metric
set, not only selected headline values.

Required phrase: full summary/delta block.

- `functions_total`;
- `cc_average`;
- `max_cc`;
- `high_complexity_functions`;
- `mi_average`;
- `import_edges`;
- `public_defs`;
- `all_exports`.

These fields are advisory evidence for aggregate review. They do not replace
design review for information hiding, shallow abstractions, temporal
decomposition, or caller cognitive load.

## Behavior Drift Check

Every material slice must include a behavior drift check before closeout. Any
slice touching files under `src/` must include the check by default; pure
documentation and policy-test-only slices may state that no runtime behavior
surface was touched.

The agent must perform mechanical checks where possible and surface remaining
review-only drift risks instead of silently marking them safe.

Closeout and review packets should include:

```text
Behavior change intended:
- yes/no

Mechanical checks:
- <test/command/check>
- <test/command/check>

Reviewed drift risks:
- <old behavior element -> new location -> evidence>
- <new element -> old source or intentional-change note -> evidence>

Review-only drift risks:
- <risk that cannot be mechanically proven>

Verdict:
- no drift found by listed checks; residual risks listed above
- intentional behavior change
- blocker found
```

For behavior-preserving slices, check:

- old inputs still map to the same outputs;
- old failure modes remain the same;
- old blocker/status codes remain the same;
- renamed variables or fields still map to the same report fields;
- extracted helpers/dataclasses preserve the old formulas;
- every removed behavior element maps to a new location;
- every new field, branch, condition, or helper maps back to old behavior or is
  explicitly listed as new;
- public/runtime contracts are unchanged;
- packet schemas are unchanged;
- Desktop/tool surface is unchanged;
- privacy and fail-closed behavior are unchanged;
- reviewer-bundle, publication, and customer-reply boundaries are unchanged;
- focused tests pass without weakening expected assertions.

If a review-only drift risk appears in two closeouts, record a promotion
candidate for a characterization test, snapshot, freeze check, or review
checklist item.
