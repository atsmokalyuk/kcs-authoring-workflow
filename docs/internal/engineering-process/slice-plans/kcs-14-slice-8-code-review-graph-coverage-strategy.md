# KCS-14 Slice 8 Code-Review Graph Coverage Strategy

Status: complete.

## Purpose

Slice 8 exists because Slice 6 improved a targeted subset of the codebase, but
the code-review graph covers more source, test, script, and packaging files
than Slice 6 reviewed or refactored.

The goal is to make remaining graph coverage explicit before more code
movement. Slice 8 starts as a review/planning slice, not a refactor slice.

## Current Baseline

Graph baseline:

- graph nodes: 14;
- source files scanned by complexity sensor: 53;
- test files scanned by complexity sensor: 46;
- scripts scanned by complexity sensor: 7.

Current complexity sensor summary:

```text
functions_total: 2439
cc_average: 3.72
max_cc: 56
high_complexity_functions: 226
mi_average: 34.29
import_edges: 429
public_defs: 1510
all_exports: 372
```

Current hotspots are concentrated in:

- frozen Desktop MCP characterization tests;
- deferred provider-handoff semantic extraction;
- remaining stdio smoke scenario checks.

This means the remaining review work is not a linear "largest file first"
exercise. Each next action needs a graph-node question and a contract-risk
gate.

## Coverage Categories

Use these statuses for each graph node:

- `covered-refactor`: behavior-preserving refactor evidence exists and was
  reviewed.
- `partial`: some files or related tests were touched, but node coverage is
  not complete.
- `review-only-needed`: inspect ownership, contracts, and tests before deciding
  whether code movement is useful.
- `deferred-risk`: do not refactor without explicit operator approval and a
  new behavior/test frame.
- `low-payoff`: leave alone unless a future change creates a concrete question.

Coverage means "reviewed for ownership and risk", not necessarily "refactored".

## Node Coverage Triage

| Graph node | Risk | Current status | Why | Next action |
| --- | --- | --- | --- | --- |
| `smoke_log_tooling` | medium | covered-refactor | Slice 6 covered smoke/log batches with refactor evidence, aggregate reviews, and external review acceptance. Remaining stdio scenario checks were explicitly classified as question-less. | No separate Slice 8 pass required; do not mine more smoke code without a new ownership question. |
| `desktop_draft_workflow` | high | covered-refactor / partial | Slice 6 batches 5-14 covered many workflow internals with behavior-drift evidence and external review. | Review-only pass before any new code movement; check whether remaining files still have concrete ownership problems. |
| `desktop_protocol_transport` | medium | covered-refactor / partial | Slice 6 batches 15-16 covered protocol constants and approved-summary alias table. | Review-only pass for remaining transport/payload boundaries; no source movement without a specific behavior-preserving question. |
| `cli_ingest_readiness` | medium | partial | Slice 6 batches 17-18 covered strict JSON scalar/readiness blocker extraction. | Review-only pass; identify whether remaining CLI/readiness complexity is useful or accidental. |
| `packaging_and_install_tooling` | medium | partial | Slice 6 batches 21-22 covered test-term tables only. | Review package/install source and tests separately; do not continue same-file test cleanup by inertia. |
| `engineering_policy_tests` | medium | partial | KCS-14 added many policy checks and graph hash anchors. | Review policy tests for brittleness and source-of-truth drift; refactor only if tests are shallow or duplicate docs. |
| `desktop_tool_surface` | high | review-only-needed | Freeze/snapshot checks and result-shaping ownership decision exist, but broad tool-surface files were not linearly reviewed. | Review tool schemas/descriptors/results against freeze snapshots before any refactor. |
| `clean_ticket_storage` | high | review-only-needed | Core `ticket_ref` storage path is proven behavior, but Slice 6 did not refactor this node. | Review path safety, metadata binding, and related tests; code movement only with strong drift checks. |
| `semantic_review_fallback` | high | review-only-needed | Controlled fallback is proven and safety-sensitive; Slice 6 did not refactor this node. | Review packet/state ownership only; defer code movement unless a concrete blocker appears. |
| `packet_validation_decision` | high | review-only-needed | Maximum invariant density; Slice 6 intentionally avoided it. | Review contracts/tests first; refactor only with narrow characterization coverage. |
| `renderer_style_gates` | high | deferred-risk | Refactor can drift into KCS-15 style/markup parity. | Review-only unless explicitly scoped as behavior-preserving; style/markup parity remains KCS-15. |
| `reviewer_bundle_output` | high | review-only-needed | Privacy/path-contract dense and not refactored in Slice 6. | Review privacy/output boundaries; avoid code movement without reviewer-bundle contract tests. |
| `provider_handoff_boundary` | high | deferred-risk | Includes `approved_summary_semantic.py` hotspot and provider trust boundary. | Do not refactor for complexity cleanup; requires explicit provider-boundary design question. |
| `package_surface` | low | low-payoff | Import surface has low current payoff unless import contracts change. | Leave alone unless packaging/import change creates a concrete question. |

## Slice 8 Work Plan

1. Record this coverage strategy.
2. Create review-only packets or notes for remaining high-risk nodes before
   code movement.
3. For each node, decide one of:
   - no action;
   - docs/graph ownership clarification only;
   - targeted behavior-preserving refactor batch;
   - defer to KCS-15 or a later explicitly approved slice.
4. Run aggregate review after every two node reviews, even if no code changes.

## Node-Specific Naming

When a future Slice 8 follow-up is scoped to one graph node, include the node
id in the slice artifact name, heading, review packet, and commit message.

Use names like:

```text
kcs-14-slice-8-review-node-engineering-policy-tests.md
kcs-14-slice-8-review-node-desktop-tool-surface.md
kcs-14-slice-8-refactor-node-clean-ticket-storage.md
```

Commit messages should make the node visible too:

```text
KCS-14 Slice 8 review engineering_policy_tests node
KCS-14 Slice 8 refactor clean_ticket_storage node
```

If a slice touches multiple nodes, name the explicit ownership question instead
of hiding the scope behind a generic "cleanup" or "refactor" label.

## Entry Gate For Any New Refactor Batch

Before another refactor batch starts:

- declare the graph node;
- state the ownership question;
- list files likely touched;
- list related tests;
- run the relevant policy/freeze/graph checks;
- state frozen/deferred boundaries;
- prepare behavior-drift mapping expectations;
- check promotion candidates and process-gap audit.

If the node has no concrete ownership or contract question, do not refactor it.

## Review Order Recommendation

Start with review-only passes before new code movement:

1. `engineering_policy_tests`: medium risk, validates that Slice 7 did not
   leave brittle policy scaffolding.
2. `desktop_tool_surface`: high value and already protected by snapshots.
3. `clean_ticket_storage`: high-value proven workflow path.
4. `reviewer_bundle_output`: high privacy density.
5. `semantic_review_fallback`: high safety density.
6. `packet_validation_decision`: highest invariant density; review after the
   review process is warmed up.

Keep these deferred unless explicitly reopened:

- `provider_handoff_boundary`;
- `renderer_style_gates`;
- frozen `tests/kcs_adapters/test_mcp_desktop.py` maintainability work.

## Non-Goals

Slice 8 must not:

- claim full codebase refactor coverage without node-level evidence;
- refactor files just because they are large;
- change runtime behavior;
- change packet schemas;
- change Desktop/tool schemas;
- change privacy, fail-closed, reviewer-bundle, publication, or customer-reply
  boundaries;
- turn advisory complexity metrics into blocking gates.

## Completion Decision

Slice 8 is complete as a review-only graph coverage pass.

Coverage disposition:

- `smoke_log_tooling`: covered by Slice 6 refactor evidence, aggregate reviews,
  and external review; no separate Slice 8 pass required.
- `desktop_draft_workflow`, `desktop_protocol_transport`,
  `cli_ingest_readiness`, `packaging_and_install_tooling`,
  `engineering_policy_tests`, `desktop_tool_surface`, `clean_ticket_storage`,
  `semantic_review_fallback`, `packet_validation_decision`,
  `reviewer_bundle_output`, `package_surface`, `renderer_style_gates`, and
  `provider_handoff_boundary`: covered by Slice 8 node review notes and
  aggregate reviews.

Slice 8 found no `architecture_error`. Architecture Patterns with Python is not
activated. Do not continue node mining unless the operator opens a new scoped
ownership question.
