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

No active promotion candidates after the complexity-measurement promotion.
Future promotion decisions for complexity measurement should use the probation
signal from Slice 6/Slice 7 closeouts, not chat memory.

## Implemented Promotions

| Finding code | Rule / finding | Seen in | Promotion target | Owner slice | Status |
| --- | --- | --- | --- | --- | --- |
| KCS14-PROMO-001 | Active docs must not repeat legacy pre-renumbering wording for the active engineering-hardening slice | Slice 0 planning/review | policy test | Slice 0 | implemented |
| KCS14-PROMO-002 | Active docs must not list unavailable development harnesses as active | Slice 1 planning/review | policy test | Slice 1 | implemented |
| KCS14-PROMO-003 | Tool entrypoint list and manual/deterministic classification should not drift | Slice 2 planning/review | policy test and help liveness check | Slice 2 | implemented |
| KCS14-PROMO-004 | Clean-ticket-derived fixtures need provenance and privacy-scan markers | Slice 3 planning/review | policy test | Slice 3 | implemented |
| KCS14-PROMO-005 | Refactor closeouts repeatedly recorded complexity distribution as not measured by a tool | Slice 6 batches 5-16 external review | advisory complexity/coupling/interface measurement entrypoint and baseline snapshot | Slice 6 | probation-advisory |

## Complexity Measurement Promotion Detail

Finding code:

- see the implemented promotions row above.

Rule / finding:

- Refactor closeouts need a deterministic sensor for complexity distribution,
  coupling, and public interface surface.
- Cyclomatic complexity alone does not prove Ousterhout-style complexity
  reduction because many KCS-14 batches moved knowledge rather than branches.

Seen in:

- Slice 6 batch closeouts repeatedly said `complexity distribution: not
  measured by a tool`.
- External Slice 6 review identified this as a dead sensor.

Evidence:

- Batch closeout metadata had no measured complexity distribution.
- The review requested Radon CC plus coupling and interface-surface signals.

Trigger:

- Repeated stable closeout gap across more than three refactor batches.

Manual correction needed:

- yes. Closeout authors previously had to describe complexity reduction by
  judgment only.

Can be checked mechanically:

- partly. The sensor can measure CC, import coupling, and interface surface.
  It cannot decide whether a design is deep or shallow.

False-positive risk:

- low as advisory measurement; high if absolute complexity thresholds become
  blocking too early.

KCS-specific or generic:

- generic process with project-local paths and graph mapping.

Promotion target:

- tool entrypoint;
- measurement-only closeout field;
- future deterministic gate candidate.

Target layer:

- measurement now;
- deterministic gate later only for narrow, proven, low-noise deltas.

Decision:

- implemented as advisory/probation sensor.

Owner slice:

- KCS-14 Slice 6.

Scope:

- `scripts/measure_complexity.py`;
- `docs/internal/engineering-process/kcs-14-complexity-baseline.json`;
- `docs/internal/engineering-process/tool-entrypoints.md`;
- policy tests.

Validation:

- command runs and emits a compatible snapshot/delta;
- values do not block commits;
- command failure is a validation failure.

Approval:

- operator accepted external review recommendation in Slice 6.

Status:

- probation-advisory.
