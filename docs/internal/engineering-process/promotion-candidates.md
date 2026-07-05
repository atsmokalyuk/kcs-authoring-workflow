# Promotion Candidates

Status: authoritative KCS-14 promotion-candidate registry.

This file records repeated findings that may move from prose guidance to a
stronger enforcement layer. It is a review/process artifact, not a runtime
product contract.

## Promotion Cadence

```text
Once = note.
Twice = review checklist item.
Three times = candidate for test/tool/check.
Stable across KCS-14 and KCS-15 = reusable infrastructure candidate.
```

## Candidate Template

```text
Finding code:
Rule / finding:
Seen in:
Evidence:
Trigger:
Manual correction needed:
Can be checked mechanically:
False-positive risk:
KCS-specific or generic:
Promotion target:
Target layer:
Decision:
Owner slice:
Scope:
Validation:
Approval:
Status:
```

Valid promotion targets:

- policy test;
- tool entrypoint or wrapper;
- freeze-list or hash check;
- code-map entry;
- review checklist item;
- measurement-only closeout field;
- reusable infrastructure candidate.

Valid statuses:

- note;
- checklist-item;
- candidate;
- accepted;
- probation-advisory;
- blocking;
- implemented;
- deferred;
- rejected.
- expired.

## Agent Responsibility

During staged-diff review, slice closeout before commit, or repeated
validation/review failure with the same cause, the development agent should
propose a candidate when a finding is repeated, stable, or mechanically
checkable. The agent should record the candidate here with a stable value-safe
finding code such as `KCS14-PROMO-NNN`, or explicitly state that there are no
new promotion candidates.

Promotion implementation should be a small scoped action or commit, not hidden
inside unrelated feature or refactor work.

Counts must come from this registry and material closeout entries in
`docs/internal/engineering-process/kcs-14-review-notes.md`. The agent must not
count chat memory as evidence.

AI reviewer suggestions may trigger a proposal, but model output never grants
implicit approval.

Candidates in `note`, `checklist-item`, `candidate`, or `deferred` status
expire after three completed slices without new evidence. Expired candidates
require fresh evidence before promotion.

## Active Candidates

No active promotion candidates at Slice 4 creation time.

## Implemented Promotions

| Finding code | Rule / finding | Seen in | Promotion target | Owner slice | Status |
| --- | --- | --- | --- | --- | --- |
| KCS14-PROMO-001 | Active docs must not repeat legacy pre-renumbering wording for the active engineering-hardening slice | Slice 0 planning/review | policy test | Slice 0 | implemented |
| KCS14-PROMO-002 | Active docs must not list unavailable development harnesses as active | Slice 1 planning/review | policy test | Slice 1 | implemented |
| KCS14-PROMO-003 | Tool entrypoint list and manual/deterministic classification should not drift | Slice 2 planning/review | policy test and help liveness check | Slice 2 | implemented |
| KCS14-PROMO-004 | Clean-ticket-derived fixtures need provenance and privacy-scan markers | Slice 3 planning/review | policy test | Slice 3 | implemented |
