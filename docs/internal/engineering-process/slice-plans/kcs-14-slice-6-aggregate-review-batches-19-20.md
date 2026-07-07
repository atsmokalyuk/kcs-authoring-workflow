# KCS-14 Slice 6 Aggregate Review - Batches 19-20

Status: complete.

Scope:

- Batch 19: `smoke_log_tooling` /
  `scripts/smoke_kcs_mcpb_stdio.py` /
  stdio tool-surface specs.
- Batch 20: `smoke_log_tooling` /
  `scripts/smoke_kcs_mcpb_stdio.py` /
  registry manifest description specs.

## Purpose

Check whether the stdio smoke refactor pair reduced meaningful complexity or
created process, map, architecture, promotion, or demotion signals before any
additional Slice 6 refactor batch.

## Countable Substrate

| Signal | Batch 19 | Batch 20 | Aggregate finding |
| --- | --- | --- | --- |
| Affected graph node | `smoke_log_tooling` | `smoke_log_tooling` | Both batches stayed inside the declared node. |
| Net file/module count change | 0 | 0 | No file-count growth. |
| Public interface/export change | 0 | 0 | CLI, report shape, check names, and public package exports stayed stable. |
| Files caller must read | unchanged | unchanged | Public use still goes through the same stdio smoke script entrypoints. |
| Graph ownership edits | none | none | Only file hashes changed. |
| Freeze/snapshot false positives | none | none | Checks stayed quiet. |
| Test assertion edits | none | none | No assertion weakening or test-coupling churn. |
| Review blockers | none | none | No recurring blocker code. |
| `must_not_own` near-misses | none | none | No boundary leak observed. |
| Promotion candidates | none | none | No repeated rule needs promotion. |
| Complexity measurement | script max CC moved from 70 to 51 | script max CC moved from 51 to 22 | Full-repo delta from baseline is now `max_cc: -13` and `high_complexity_functions: -3`. |

## Signal Triage

Repeated ownership conflicts:

- finding: none. Both batches made local smoke-script contract knowledge
  explicit without touching Desktop schema owners or packaging manifests.
- triage: no `map_error`, `process_error`, or `architecture_error`.

Hidden higher-level redesign pressure:

- finding: none. The refactor needed private spec tables inside the smoke
  script, not a new cross-module contract or service layer.
- triage: no `architecture_error`.

Graph drift:

- finding: none. File hash updates were expected; `owns` and `must_not_own`
  definitions did not change.
- triage: no `map_error`.

Classitis / shallow split:

- finding: acceptable low-to-medium risk. Two private `NamedTuple` specs and
  helper functions were added, but they group concrete contract knowledge and
  do not create a caller-facing interface.
- triage: no process error. Stop same-node momentum after this pair unless a
  new explicit ownership question has higher payoff than review cost.

Temporal decomposition:

- finding: none. The batches grouped by knowledge ownership: tool-surface
  contract and registry-manifest description contract.
- triage: no architecture issue.

Noisy enforcement:

- finding: none. Complexity, graph, freeze/snapshot, Ruff, and diff checks
  stayed green after expected graph hash updates.
- triage: no demotion needed.

Promotion clustering:

- finding: none. No repeated review-only drift risk or recurring manual check
  appeared.
- triage: no promotion needed.

Uncontained batches:

- finding: none. Both batches remained inside `smoke_log_tooling` plus expected
  graph and closeout metadata.
- triage: no process issue.

Test-coupling churn:

- finding: none. Both batches used existing focused tests and old-vs-new
  equivalence checks; no assertions changed.
- triage: no architecture issue around test boundaries.

Safety-floor pressure:

- finding: none. No publish/write/customer-reply path, packet schema change,
  Desktop tool schema change, or raw-data boundary change.
- triage: safety floor holds by freeze/snapshot checks and related tests.

## Outcome

Decision: stop same-node `smoke_log_tooling` momentum.

Rationale:

- Batches 19-20 delivered the intended stdio smoke complexity reduction:
  script max CC dropped from 70 to 22 across the pair.
- The remaining stdio smoke hotspots are scenario-result checks, not the
  explicit tool-surface/registry-manifest ownership question that justified
  this pair.
- Continuing this same file now would require a new ownership question and
  higher payoff than the review overhead.

Architecture Patterns with Python is not activated:

- no `architecture_error` was diagnosed;
- no recurring friction around core/adapters/tests appeared;
- no service-layer, repository, unit-of-work, aggregate, message-bus, or
  event-driven design note is justified by these batches.

Promotion/demotion:

- promotion candidates: none.
- demotion candidates: none.

Process adjustment:

- none required.

## Ousterhout Review Lens

The two batches improved local information hiding:

- Batch 19 made the expected stdio tool surface a private table.
- Batch 20 made the registry manifest description contract a private table.

The changes reduced change amplification for this script:

- future expected tool-surface or manifest-description changes should touch a
  spec entry instead of a long boolean expression.

The changes did not increase caller cognitive load:

- CLI entrypoints, report shape, check names, and package surfaces stayed
  stable;
- no public helper or new file was introduced.

The main design risk is spec-table sprawl:

- acceptable for these two contract-heavy checks;
- not a blanket authorization to convert every smoke scenario assertion into a
  table.

## Next Gate

Slice 6 may continue only with a new explicit ownership question in another
node or a clearly higher-payoff remaining hotspot.

Recommended options:

- stop Slice 6 and prepare final Slice 6 closeout / external review; or
- inspect a different graph node for a contained ownership problem with
  measured payoff and lower review overhead than continuing the stdio smoke
  file.

Do not treat this aggregate review as authorization for cross-package
architecture redesign.
