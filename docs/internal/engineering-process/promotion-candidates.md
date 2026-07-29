# Promotion Candidates

Status: authoritative KCS-14 promotion-candidate registry.

This file records repeated findings that may move from prose guidance to a
stronger enforcement layer. It is a review/process artifact, not a runtime
product contract.

This registry tracks local enforcement maturity. It does not prove that a rule
is portable. Cross-project evidence and extraction readiness are tracked
separately in
`docs/internal/engineering-process/engineering-rule-portability.md`.

An implemented policy test may remain project-specific. A portable
judgment-based rule may remain a review gate. Do not infer one ladder's status
from the other.

## Promotion Cadence

```text
Once = review note, not a registry entry.
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

- checklist-item;
- candidate;
- accepted;
- blocking;
- implemented;
- deferred;
- rejected.

## Agent Responsibility

During aggregate review, aggregate closeout, or repeated validation/review
failure with the same cause, the development agent should propose a candidate
when a process finding is repeated, stable, or mechanically checkable. The
agent should record the candidate here with a stable value-safe finding code
such as `KCS14-PROMO-NNN`, or explicitly state at aggregate closeout that there
are no new promotion candidates.

Before writing "Promotion candidates: none" in an aggregate closeout, the
agent must re-read the Findings, watch-item, warnings, and aggregate-review
sections for the slice being closed. Repeated findings found there must be
recorded here or explicitly rejected with a reason.

Promotion implementation should be a small scoped action or commit, not hidden
inside unrelated feature or refactor work.

Counts must come from this registry and merged pull requests or final closeout
records. The agent must not count chat memory as evidence.

AI reviewer suggestions may trigger a proposal, but model output never grants
implicit approval.

Runtime and contract defects with known expected behavior go directly to
focused regression tests. Parked ownership or import-contract questions stay
in the code map, design notes, or an explicitly scoped follow-up. They do not
need registry lifecycle states.

## Active Candidates

| Finding code | Rule / finding | Seen in | Promotion target | Owner slice | Status |
| --- | --- | --- | --- | --- | --- |
| KCS14-PROMO-009 | Packaged guidance and tracked engineering docs can drift around supported tool names, manual/freehand drafting boundaries, publication/customer-reply boundaries, and command-surface wording | Slice 8 packaging aggregate, desktop protocol aggregate, Slice 8 closeout, external Slice 8 review | review checklist item now; possible policy/package test later | KCS-14 Slice 9 / future package-edit slice | checklist-item |
| KCS14-PROMO-012 | Intentional frozen-path implementation changes still need human old-to-new behavior mapping and a residual drift judgment after deterministic snapshot, graph, and freeze checks pass | Slice 9 Targets 2-3, KCS-14.5 M0-M4 | review checklist item | future frozen-path implementation changes | checklist-item |

The complexity sensor is implemented but remains advisory. A blocking threshold
would require separately approved repeated evidence.

## Frozen-Path Human Review Residue

Finding code:

- see the active human-review residue row above.

Rule / finding:

- Deterministic snapshot, graph-hash, and freeze checks now detect frozen-path
  changes and stale evidence.
- They cannot decide whether an intentional change preserves behavior. That
  residue stays as one human review judgment rather than a second workflow.

Seen in:

- Slice 9 Target 2 touched `src/kcs_adapters/desktop_semantic_review.py`.
- Slice 9 Target 3 touched `src/kcs_adapters/desktop_reviewer_bundle.py`.

Evidence:

- Both touched frozen-path files.
- Both preserved public/runtime behavior through focused characterization
  tests.
- Both required graph hash updates.
- Broad freeze diff checks were expected to pass after commit, not before.

Trigger:

- The review concern appeared in two Slice 9 runtime targets and throughout
  the KCS-14.5 frozen-path changes.

Manual correction needed:

- yes, for the semantic old-to-new mapping and residual drift judgment.

Can be checked mechanically:

- no. Detection and evidence freshness are already mechanical; equivalence
  remains review-gated.

False-positive risk:

- low as a review checklist item; high if a mechanical check pretends to prove
  semantic equivalence.

KCS-specific or generic:

- generic process, project-local frozen-path names.

Promotion target:

- review checklist item.

Target layer:

- review gate for semantic equivalence only.

Decision:

- retain only the human semantic-equivalence residue as a checklist item.

Owner slice:

- future frozen-path implementation changes.

Scope:

- behavior-preserving refactors touching paths protected by
  `FROZEN_CONTRACT_PATHS`.

Validation:

- aggregate closeout must state the intentional frozen path touched, unchanged
  contract, old-to-new mapping, and residual review-only drift risks.

Approval:

- generated from Slice 9 aggregate review evidence.

Status:

- checklist-item.

## Packaged Guidance / Tracked Docs Drift Detail

Finding code:

- see the active candidates row above.

Rule / finding:

- Packaged skill guidance, package initialize instructions, and tool-surface
  text can drift from tracked engineering docs and runtime tool-name constants.
- Future package edits should compare shipped guidance against tracked
  `tool-entrypoints.md`, runtime tool-name constants, and boundary terms such
  as no manual/freehand drafting, no publication, and no customer reply.

Seen in:

- Slice 8 packaging/install aggregate: packaged guidance drift was the main
  review finding.
- Slice 8 desktop protocol aggregate: duplicated operator guidance was a main
  watch item.
- Slice 8 closeout: packaging guidance drift was kept visible for future
  review.
- External Slice 8 review classified the repeated finding as checklist-level.

Evidence:

- Existing package tests already anchor a subset of shipped tool names and
  no-secret/no-publication boundary terms.
- Repeated review findings show that guidance drift needs a durable checklist
  item before it becomes a broader mechanical check.

Trigger:

- Same finding family appeared in two independent node reviews and the final
  Slice 8 closeout.

Manual correction needed:

- yes. Reviewers must compare package guidance against tracked docs and runtime
  constants when package files are edited.

Can be checked mechanically:

- partly. Tests can compare shipped tool names and required boundary terms, but
  review judgment is still needed for explanatory guidance.

False-positive risk:

- low as a checklist item; medium if turned into broad wording regexes.

KCS-specific or generic:

- generic pattern with KCS-specific package guidance and tool names.

Promotion target:

- review checklist item now;
- possible policy/package test later if repeated package edits require manual
  comparison.

Target layer:

- review gate now;
- deterministic check later for narrow shipped-term/tool-name coverage only.

Decision:

- record as checklist-level guidance; do not add automation during KCS-14
  closeout.

Owner slice:

- KCS-14 Slice 9 / future package-edit slice.

Scope:

- packaged skill guidance;
- package initialize instructions;
- tool-surface docs;
- tracked `tool-entrypoints.md`;
- Desktop tool-name constants and package tests.

Validation:

- future package edits must list guidance-drift review evidence when touching
  package guidance or shipped tool text.

Approval:

- external Slice 8 review recommended checklist-level promotion.

Status:

- checklist-item.

## Implemented Promotions

| Finding code | Rule / finding | Seen in | Promotion target | Owner slice | Status |
| --- | --- | --- | --- | --- | --- |
| KCS14-PROMO-001 | Active docs must not repeat legacy pre-renumbering wording for the active engineering-hardening slice | Slice 0 planning/review | policy test | Slice 0 | implemented |
| KCS14-PROMO-002 | Active docs must not list unavailable development harnesses as active | Slice 1 planning/review | policy test | Slice 1 | implemented |
| KCS14-PROMO-003 | Tool entrypoint list and manual/deterministic classification should not drift | Slice 2 planning/review | policy test and help liveness check | Slice 2 | implemented |
| KCS14-PROMO-004 | Clean-ticket-derived fixtures need provenance and privacy-scan markers | Slice 3 planning/review | policy test | Slice 3 | implemented |
| KCS14-PROMO-005 | Refactor closeouts repeatedly recorded complexity distribution as not measured by a tool | Slice 6 batches 5-16 external review | advisory complexity/coupling/interface measurement entrypoint and baseline snapshot | Slice 6 | implemented |
| KCS14-PROMO-006 | Contract-term/spec-table extraction should preserve all old terms with all-quantified checks and avoid broad table-driven rewrites | Slice 6 batches 19-22 external review | review checklist item and policy anchor | Slice 7 | implemented |
| KCS14-PROMO-007 | Refactor closeouts that cite complexity measurement should record the full sensor summary/delta block, not only selected headline fields | Slice 6 batches 19-22 external review | closeout shape policy anchor | Slice 7 | implemented |
| KCS14-PROMO-008 | Behavior-preserving refactors need explicit old-to-new and new-to-old drift mapping evidence | Slice 6 batches 1-22 closeouts and external review | behavior drift checklist and policy anchor | Slice 7 | implemented |
| KCS14-PROMO-010 | Frozen-path implementation changes must be detected and stale snapshot or graph evidence must fail deterministic policy checks | Slice 9 Targets 2-3, repeated KCS-14.5 frozen-path changes | freeze snapshot, graph hash, and post-commit freeze/graph checks | KCS-14.5 | implemented |
| KCS14-PROMO-011 | Durable review notes must not record absolute local artifact paths; use an opaque basename plus value-safe hash/count/verdict | M3 aggregate closeout review, 13 repeated paths | review-context policy test | KCS-14.5 M3 closeout | implemented |
| KCS14-PROMO-013 | M3 canaries must run in fail-closed order: legacy baseline, medium, continuation, then complex only after the first two stages are stable | M2 closeout and M3 staged canary gate | ordered documentation policy test | KCS-14.5 M2 closeout | implemented |
| KCS14-PROMO-014 | Material implementation, refactor, deployment, or integration closeout needs a compact Ousterhout review record or a concrete leaf-change `not triggered` reason | KCS-14 design-review usage and KCS-15.2a closeout audit | review gate plus deterministic record-shape anchor | KCS-15 process hardening | implemented |
| KCS14-PROMO-015 | An existing runtime/API dependency needs exact endpoint/mode/response-shape operational evidence before substantial implementation; fixtures and adjacent endpoints are insufficient | KCS-15.2b1 `/api/snippets` pre-implementation correction | clarification/playbook/review gate plus policy anchor | KCS-15.2b1 | implemented |
| KCS14-PROMO-016 | Configuration declared at a launcher or intermediate wrapper must not be treated as effective at the terminal runtime; prove propagation with a value-safe effective-config or derived-effect preflight on the current live process | PAUX-7103 source/installed-wrapper accounting smokes passed, but Claude Desktop did not propagate `launchctl` values to its MCPB connector and the real run remained unobserved | extend installed-runtime identity gate plus deterministic wording anchor | PAUX-7103 | implemented |

## Exact Integration Feasibility Promotion Detail

Finding code:

- see the exact-integration feasibility row above.

Rule / finding:

- KCS-15.2a had proven local RAG readiness and metadata search, while the new
  KCS-15.2b1 design depended on the distinct `/api/snippets` endpoint and its
  wrapper, bounds, and public-excerpt shape.
- The first implementation plan placed the live check near validation. The
  operator correction moved it before substantial adapter work.
- The bounded smoke confirmed the live schema and bounds and exposed two
  nominal/operational differences: supported status CLI arguments and the
  top-level result wrapper.

Can be checked mechanically:

- presence of the exact-path gate in tracked process docs: yes;
- whether a particular smoke is safe, fresh, and decision-relevant: reviewer-owned.

Decision:

- embed the gate in the existing clarification, feature, and review paths;
- do not add a new workflow layer or treat one smoke as stability evidence.

Status:

- implemented.

## Compact Ousterhout Closeout Promotion Detail

Finding code:

- see the implemented promotions row above.

Rule / finding:

- Ousterhout principles were authoritative for code movement and required as a
  deployment design lens, but material feature closeouts did not consistently
  leave auditable evidence that the review occurred.
- A triggered closeout must record complexity hidden, ownership, interface
  depth/caller cognitive load, information leakage/change amplification,
  whether complexity was removed or moved, residual risk, and verdict.
- A small leaf change may record `not triggered` only with a concrete boundary
  and unchanged-internal-complexity reason; it uses the two-field short form
  rather than the full reviewed record.

Seen in:

- KCS-14 code-map and refactor reviews established the stable design lens.
- KCS-15.2a satisfied the principles through an isolated adapter boundary, but
  its first closeout had no explicit Ousterhout record.

Can be checked mechanically:

- record shape and required vocabulary: yes;
- module depth, information leakage, cognitive load, or design quality: no.

False-positive risk:

- low with the leaf-change exception; high if every source edit is treated as
  proof that a material design review triggered. A large internal complexity
  change remains reviewed even when its external boundary is stable.

Promotion target:

- compact named-human-review gate;
- deterministic policy anchor for required process text only.

Decision:

- implement in the existing Builder, playbook, review checklist, and review
  packet protocol; do not create a new workflow or design-scoring tool.

Owner slice:

- KCS-15 process hardening.

Validation:

- `tests/policy/test_engineering_process_docs_policy.py` anchors the trigger, record shape,
  leaf exception, and review-only judgment boundary.

Approval:

- operator approved the trigger-based gate after the KCS-15.2a closeout audit.

Status:

- implemented.

## Durable Review Artifact Reference Promotion Detail

Finding code:

- see the implemented promotions row above.

Rule / finding:

- Durable review and closeout notes must not store absolute local artifact
  paths. Record only an opaque artifact basename plus value-safe
  hash/count/verdict evidence.

Seen in:

- M3 aggregate closeout review found 13 absolute local canary artifact paths
  in the tracked review notes.

Evidence:

- The paths added no comparison value beyond the basename and violated the
  existing private-filesystem boundary in the review-context protocol.

Trigger:

- repeated mechanically checkable finding in one material closeout.

Manual correction needed:

- replace the local root with an opaque basename.

Can be checked mechanically:

- yes, against the durable KCS-14 review-notes artifact.

False-positive risk:

- low for the exact absolute local canary root.

KCS-specific or generic:

- generic durable-review privacy boundary.

Promotion target:

- policy test.

Target layer:

- review-context policy.

Decision:

- implement in the M3 closeout because it directly locks the reviewed privacy
  correction and is limited to policy/docs.

Owner slice:

- KCS-14.5 M3 closeout.

Scope:

- tracked KCS-14 durable review notes only.

Validation:

- review-context policy suite and `git diff --check`.

Approval:

- implicit promotion path: stable mechanical rule, low false-positive risk,
  and policy/docs-only diff.

Status:

- implemented.

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

- implemented as an advisory sensor.

Owner slice:

- KCS-14 Slice 6.

Scope:

- `scripts/measure_complexity.py`;
- `docs/internal/engineering-process/tool-entrypoints.md`;
- policy tests.

Validation:

- command runs and emits a compatible on-demand snapshot;
- values do not block commits;
- command failure is a validation failure.

Approval:

- operator accepted external review recommendation in Slice 6.

Status:

- implemented.

## Contract-Term / Spec-Table Extraction Detail

Finding code:

- see the implemented promotions row above.

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

- KCS-14 Slice 7 review/agent tooling.

Scope:

- contract-heavy code/test checks where expected terms, properties, schemas, or
  annotations are already being checked explicitly.

Validation:

- focused characterization tests still pass;
- diff review maps old terms/properties to new table entries;
- no public/runtime surface expands.
- `tests/policy/test_review_context_policy.py` anchors the checklist guidance.

Approval:

- external review recommended checklist-level promotion.

Status:

- implemented.

## Behavior Drift Mapping Support Detail

Finding code:

- see the implemented promotions row above.

Rule / finding:

- Behavior-preserving refactors repeatedly needed direct old-vs-new comparison
  and a mapping from old behavior elements to their new locations.
- A generic equivalence runner would be too broad because Slice 6 compared
  report JSON, helper outputs, payload normalization, renderer blockers,
  environment construction, and private alias values.
- The durable rule is therefore a review/closeout protocol: record
  old behavior element -> new location -> evidence, and new element -> old
  source or intentional-change note -> evidence.

Seen in:

- Slice 6 refactor log and closeouts across batches 1-22.
- External Slice 6 review identified old-vs-new equivalence support as a
  natural Slice 7 seed.

Evidence:

- Multiple batches used direct old-vs-new checks against `HEAD` or focused
  characterization cases.
- Review-only drift mapping was necessary to prove that helper extraction,
  field grouping, and table extraction did not change behavior.

Trigger:

- The same manual behavior-drift evidence pattern appeared across more than
  three behavior-preserving refactor batches.

Manual correction needed:

- yes. Reviewers need the mapping table to inspect behavior-preserving claims.

Can be checked mechanically:

- partly. A policy test can anchor the required mapping fields, but judgment is
  still required to verify semantic equivalence.

False-positive risk:

- low as a required closeout/review section; high as a fully automated
  equivalence claim.

KCS-specific or generic:

- generic refactor-review protocol with project-local examples.

Promotion target:

- review checklist item;
- behavior drift closeout protocol;
- future review packet/closeout shape check.

Target layer:

- review gate now;
- deterministic shape check later only for section presence, not equivalence.

Decision:

- implemented as protocol and policy anchor, not as a generic equivalence
  runner.

Owner slice:

- KCS-14 Slice 7 review/agent tooling.

Scope:

- behavior-preserving refactors and material slices touching `src/`.

Validation:

- `tests/policy/test_review_context_policy.py` anchors the required mapping
  language.

Approval:

- operator approved continuing Slice 7 promotion backlog implementation.

Status:

- implemented.

## Full Complexity Delta Closeout Detail

Finding code:

- see the implemented promotions row above.

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

- accepted for future refactor closeouts and anchored by a Slice 7 policy
  test over the final Slice 6 closeout.

Owner slice:

- KCS-14 Slice 7 review/agent tooling.

Scope:

- material refactor closeouts and aggregate reviews that cite
  `scripts/measure_complexity.py`.

Validation:

- future closeouts include the full summary/delta block when complexity
  measurement is cited.
- `tests/policy/test_review_context_policy.py` checks the final Slice 6
  closeout for the full summary/delta block.

Approval:

- external review recommended the measurement-format promotion.

Status:

- implemented.
