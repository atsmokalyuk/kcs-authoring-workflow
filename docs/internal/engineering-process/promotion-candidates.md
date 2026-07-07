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

| Finding code | Rule / finding | Seen in | Promotion target | Owner slice | Status |
| --- | --- | --- | --- | --- | --- |
| KCS14-PROMO-006 | Contract-term/spec-table extraction should preserve all old terms with all-quantified checks and avoid broad table-driven rewrites | Slice 6 batches 19-22 external review | review checklist item | Slice 6 closeout / future refactor slices | checklist-item |
| KCS14-PROMO-007 | Refactor closeouts that cite complexity measurement should record the full sensor summary/delta block, not only selected headline fields | Slice 6 batches 19-22 external review | measurement-only closeout field | Slice 6 closeout / future refactor slices | accepted |

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

## Contract-Term / Spec-Table Extraction Detail

Finding code:

- see the active candidates row above.

Rule / finding:

- Contract-heavy checks may be clearer as local spec tables or term lists, but
  only when every old term or expected property is preserved with
  all-quantified checks.
- A table-driven rewrite must not weaken semantics from "all terms required"
  to "any term accepted" and must not hide design judgment behind generic data.
- The aggregate review must still ask whether the table hides real contract
  knowledge or creates shallow helper/table sprawl.

Seen in:

- Slice 6 batches 19-20: stdio smoke tool-surface and registry manifest
  contract specs.
- Slice 6 batches 21-22: MCPB package manifest and wrapper test term tables.
- External review for batches 19-22 classified this as checklist-level:
  repeated twice in unrelated areas, but not mechanically enforceable yet.

Evidence:

- Batches 19-22 preserved exact expected terms/properties and used all-term
  checks.
- External review found no test weakening and no dropped terms.
- Aggregates warned that this is not a blanket instruction to convert every
  smoke or test assertion into a table.

Trigger:

- Same implementation pattern repeated in two unrelated areas.

Manual correction needed:

- yes. Reviewers must inspect term preservation and table-sprawl risk.

Can be checked mechanically:

- partly. Tests can prove the current fixture satisfies the table; diff review
  is still needed to prove no old term was dropped.

False-positive risk:

- medium if automated broadly; low as a review checklist item.

KCS-specific or generic:

- generic refactor-review guidance with project-local examples.

Promotion target:

- review checklist item.

Target layer:

- review gate.

Decision:

- record as checklist-level guidance, not policy automation.

Owner slice:

- KCS-14 Slice 6 closeout and future refactor slices.

Scope:

- contract-heavy code/test checks where expected terms, properties, schemas, or
  annotations are already being checked explicitly.

Validation:

- focused characterization tests still pass;
- diff review maps old terms/properties to new table entries;
- no public/runtime surface expands.

Approval:

- external review recommended checklist-level promotion.

Status:

- checklist-item.

## Full Complexity Delta Closeout Detail

Finding code:

- see the active candidates row above.

Rule / finding:

- When a refactor closeout cites complexity measurement, it should record the
  full sensor summary/delta block: `functions_total`, `cc_average`, `max_cc`,
  `high_complexity_functions`, `mi_average`, `import_edges`, `public_defs`, and
  `all_exports`.
- Citing only `max_cc` or `high_complexity_functions` can hide helper growth or
  movement of complexity between files.

Seen in:

- Slice 6 batches 19-22 external review.

Evidence:

- External review noted that the sensor emitted anti-gaming fields but
  aggregate closeouts cited only selected headline fields.

Trigger:

- Stable, low-risk measurement formatting rule discovered during external
  review.

Manual correction needed:

- yes, until the closeout shape validator enforces it.

Can be checked mechanically:

- yes, once closeout shape validation covers refactor closeouts.

False-positive risk:

- low for refactor closeouts that cite the complexity sensor.

KCS-specific or generic:

- generic process with project-local metric names.

Promotion target:

- measurement-only closeout field;
- future closeout shape validator extension.

Target layer:

- measurement now;
- deterministic closeout-shape check later.

Decision:

- accepted for future refactor closeouts; automation deferred to Slice 7 or a
  dedicated closeout-shape validator change.

Owner slice:

- KCS-14 Slice 6 closeout and Slice 7 review tooling.

Scope:

- material refactor closeouts and aggregate reviews that cite
  `scripts/measure_complexity.py`.

Validation:

- future closeouts include the full summary/delta block when complexity
  measurement is cited.

Approval:

- external review recommended the measurement-format promotion.

Status:

- accepted.
