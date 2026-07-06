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
- `docs/internal/engineering-process/kcs-14-review-notes.md` owns material
  review verdicts and slice closeouts.
- `docs/internal/engineering-process/promotion-candidates.md` owns the
  registry of repeated findings that may move down the enforcement ladder.
- `docs/internal/engineering-process/review-packets/` may hold file-based
  review packets when a review needs a persistent artifact.
- `docs/internal/engineering-process/tool-entrypoints.md` owns validation
  commands.
- `docs/internal/engineering-process/agent-operable-engineering-workflow.md`
  owns general agent context hygiene.

## Packet Location

For material or external review, create a file-based packet:

```text
docs/internal/engineering-process/review-packets/<slice>-review-packet.md
```

Chat-only review is acceptable for tiny local checkpoints, but any material
review that changes authoritative process docs, contract wording, acceptance
criteria, ownership maps, or promotion decisions should have a file-based
packet or a closeout entry that preserves the same fields.

## Required Sections

Each file-based review packet should include:

- `Review Task`;
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
Once = note.
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

## Agent Promotion Responsibility

Promotion discovery is automatic. During task framing, staged-diff review, and
slice closeout, the development agent must check the promotion registry and
material closeouts. The development agent must surface a promotion candidate
when a finding is repeated, stable, or mechanically checkable.

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

For material slices, the agent must check promotion candidates at these
checkpoints:

- before starting a refactor target or other material implementation slice;
- during staged-diff review;
- during slice closeout before commit;
- after repeated validation or review failure with the same cause.

Every material closeout must say either:

```text
Promotion candidates: none
```

or:

```text
Promotion candidates:
- <rule / finding>
```

Counts must come from
`docs/internal/engineering-process/promotion-candidates.md` and material
closeout entries in `docs/internal/engineering-process/kcs-14-review-notes.md`.
The agent must not rely on chat memory to decide whether a finding is repeated.
The agent must report that it checked these durable sources even when the
result is `Promotion candidates: none`.

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

## Probation And Demotion

New deterministic checks should run in advisory mode for one slice before they
become blocking, unless they directly lock in the current slice's accepted
outcome.

A blocking check that produces a false positive must be demoted to advisory and
recorded in the promotion registry before it can become blocking again.

Promotion candidates in `note`, `checklist-item`, `candidate`, or `deferred`
status expire after three completed slices without new evidence. Expired
candidates require a fresh finding code or evidence update before promotion.

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
