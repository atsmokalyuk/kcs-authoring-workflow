# KCS-14 Slice 6 Refactor Methodology

Status: planned methodology for behavior-preserving codebase design refactor.

Source: distilled from Fable 5 methodology review after Slice 5 code-review
graph expansion. This file records the decision, not the raw review transcript.

## Purpose

Slice 6 refactor work must reduce codebase complexity without changing runtime
behavior. The goal is not a broad cleanup pass. Each refactor commit should
target one reviewed ownership node, preserve contracts, and leave clearer
module ownership than it found.

## Pre-Refactor Commit 0

Before the first code movement commit, add freeze/snapshot checks that prove
behavior-preserving intent mechanically.

Required checks:

- Desktop `tools/list` snapshot for exact tool names and input schema
  properties;
- packet schema/version/field-set snapshot for current packet families;
- compact-result key-set snapshot for Desktop/tool result surfaces;
- freeze-list or diff gate for high-risk public/runtime contract files;
- graph coverage check for `src/`, `tests/`, `scripts/`, and `packaging/`;
- green baseline for the full relevant policy suite and selected node tests.

Implemented baseline:

- `tests/policy/test_kcs14_freeze_snapshots.py`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-6-commit-0-freeze-snapshots.md`

Graph hash checks prove staleness. They do not prove contract preservation.
Freeze/snapshot checks must land before behavior-preserving refactor commits.
Until those checks exist and pass, Slice 6 is ready for planning only, not code
movement.

## First Refactor Target

Start with `smoke_log_tooling`.

Reason:

- medium risk and lower runtime blast radius;
- exercises Slice 6 process without touching packet schemas, Desktop schemas,
  renderer behavior, reviewer-bundle behavior, or semantic-review gates;
- official tool entrypoints already cover parts of this surface;
- useful as a process calibration target before higher-risk nodes.

Constraints:

- CLI argument surfaces remain stable;
- output shape remains value-safe and compact;
- Desktop/manual checks remain classified as manual or local-runtime checks;
- no raw transcript or private artifact is introduced into review context.

## Proposed Sequence

1. `smoke_log_tooling`: process rehearsal and internal consolidation only.
2. Result-shaping ownership decision: write the ownership paragraph below
   before touching `desktop_draft_workflow` or `desktop_tool_surface`.
3. `desktop_draft_workflow`: consolidate only inside the node; keep runtime
   behavior and related assertions stable. Prefer sub-batches such as
   arguments/output first, then results/status.
4. `desktop_tool_surface`: consolidate tool identity/schema/descriptors only
   after the `tools/list` snapshot is green.
5. Result-shaping ownership consolidation: only after the written ownership
   decision exists and graph nodes are updated intentionally.
6. `desktop_protocol_transport` and `cli_ingest_readiness`: mid-risk follow-up
   nodes if budget remains.

Do not start with the highest-invariant nodes.

## Nodes To Avoid Initially

Avoid these until lower-risk refactor targets prove the process:

- `packet_validation_decision`: maximum invariant density;
- `renderer_style_gates`: can drift into deferred KCS-15 style/markup parity;
- `reviewer_bundle_output`: privacy and path-contract density;
- `semantic_review_fallback`: fresh controlled fallback behavior and high
  safety density;
- `provider_handoff_boundary`: provider trust and cross-package risk;
- `clean_ticket_storage`: path traversal and local file safety;
- `package_surface`: negligible payoff unless import contracts are explicitly
  in scope.

## Result-Shaping Ownership Gate

Before touching result-shaping files, write a one-paragraph ownership decision
for:

- `src/kcs_adapters/desktop_tool_results.py`
- `src/kcs_adapters/desktop_mcp_results.py`
- `src/kcs_adapters/desktop_draft_output.py`
- `src/kcs_adapters/desktop_workflow_results.py`
- `src/kcs_adapters/desktop_workflow_status.py`

The decision must answer:

- which layer owns the protocol envelope;
- which layer owns Desktop tool result shape;
- which layer owns workflow status and compact result semantics;
- what adjacent layers must not know.

This is the Slice 6 `design it twice` checkpoint. It must be written before
target 2 starts, because target 2 and target 3 touch files on this disputed
boundary. Do not let a refactor commit make this decision implicitly.

## Cross-Package Movement Rule

Do not move files across `kcs_core` and `kcs_adapters` during ordinary Slice 6
refactor commits.

Cross-package movement changes the core/adapter architecture boundary and
requires its own explicitly scoped slice, behavior/test frame, graph update,
and review checkpoint.

## Characterization And Test Rules

For each refactor target:

- check `promotion-candidates.md` and KCS-14 closeouts before starting the
  target;
- run the node's related tests before and after the change;
- run a behavior drift check before staged-diff review:
  - any Slice 6 batch touching `src/` files must perform the check by default;
    pure documentation and policy-test-only batches may state that no runtime
    behavior surface was touched;
  - for pure internal refactors with a stable public function/output surface,
    compare old `HEAD` behavior with the staged behavior on representative
    inputs where practical;
  - otherwise use freeze/snapshot checks, characterization tests, unchanged
    assertion review, and frozen-path evidence;
  - map old behavior elements to their new location and map every new field,
    branch, condition, helper, or dataclass back to old behavior or an explicit
    intentional-change note;
  - if direct old-vs-new comparison is not practical, state why and record the
    substitute evidence;
  - if a review-only drift risk appears in two closeouts, record a promotion
    candidate for a future characterization test, snapshot, freeze check, or
    review checklist item;
- record affected graph nodes in the review packet or closeout;
- keep test assertion edits out of the refactor unless explicitly justified;
- treat `tests/kcs_adapters/test_mcp_desktop.py` as a frozen
  characterization suite during Slice 6;
- update graph hashes in the same reviewed commit when source/test files move
  or change intentionally;
- update graph file lists and hashes with the code commit when files move,
  change, appear, or disappear intentionally;
- keep graph ownership-definition edits separate unless changing ownership is
  the declared scope of the batch;
- keep move-only commits separate from behavior-shape commits when practical.

## Ousterhout Review Lens

Use the Ousterhout checklist as a targeted design lens, not a linear
file-by-file comparison.

Required Slice 6 questions:

- Information hiding: is one design decision encoded in multiple modules?
- Deep modules: did the refactor reduce what callers must know?
- Classitis: did the change create tiny wrappers/classes without real
  ownership?
- Temporal decomposition: did the split follow execution order instead of
  knowledge ownership?
- Pass-through layers: does each new layer add policy, validation,
  translation, or real boundary value?
- Change amplification: would a future related change touch fewer files?
- Cognitive load: can a future maintainer or agent find the owner faster?
- Better together or apart: should result/status/output files live together or
  remain separate?
- Error design: did failure handling become simpler without weakening
  fail-closed behavior?

## First Refactor Review Checkpoint

Review the first Slice 6 refactor commit as process calibration.

Required evidence:

- declared node covers the full diff;
- boundary questions answered before implementation;
- promotion registry and prior closeouts checked before implementation;
- pre/post characterization baseline recorded;
- behavior drift check recorded;
- behavior drift verdict is evidence-based, for example `no drift found by
  listed checks; residual risks listed above`, not a standalone safety claim;
- freeze/snapshot checks green;
- absence of runtime, packet, Desktop, privacy, and reviewer-bundle drift is
  demonstrated by green snapshots, related tests passing, and frozen paths
  untouched, not asserted as a standalone claim;
- zero unapproved test assertion edits;
- graph hashes updated with intent stated;
- net module count does not increase without a named knowledge owner;
- closeout includes promotion candidates or `none`;
- reviewer verdict states whether the Slice 6 machinery was proportionate to
  the risk protected.

Canonical behavior drift mapping example from Batch 1:

```text
Old behavior element:
  local variable tool_names
New location:
  _SmokeMarkers.tool_names
Evidence:
  old-vs-new SmokeAccountingReport.to_json_dict() equivalence check

Old behavior element:
  local variable upload_ticket_ref_count
New location:
  _SmokeMarkers.draft_upload_ticket_ref_count ->
  SmokeAccountingReport.kcs_draft_upload_ticket_ref_count
Evidence:
  old-vs-new equivalence case for uploaded ticket_ref path

Old behavior element:
  inline deterministic_draft_passed formula
New location:
  _SmokeMarkers.deterministic_draft_passed
Evidence:
  old-vs-new equivalence case for split + selected draft success

New element:
  _SmokeMarkers dataclass
Old source:
  old inline marker extraction local variables
Evidence:
  no new public interface; existing smoke-accounting tests and old-vs-new
  equivalence checks passed
```

## Aggregate Design Review Gate

Per-batch review catches local correctness. Slice 6 also needs an aggregate
design review to catch recurring design signals that one batch cannot see.

Run an aggregate review:

- after every two completed refactor batches;
- immediately after the second graph `owns` or `must_not_own` edit to the same
  node;
- after any freeze/snapshot false positive;
- when the same ownership conflict appears in two closeouts;
- when a batch cannot stay inside its declared graph node;
- at the end of Slice 6 before Slice 7 or KCS-15 starts.

Aggregate review catches these signals:

- repeated ownership conflicts;
- hidden higher-level redesign pressure;
- graph drift across `owns` or `must_not_own`;
- classitis, shallow splits, or interface growth without caller simplicity;
- temporal decomposition that spreads schema, rule, or blocker knowledge;
- noisy freeze, snapshot, or policy checks;
- promotion candidates clustering around one node;
- batches that cannot stay inside their declared graph node;
- test-coupling churn, especially repeated justified exceptions to the rule
  against changing test assertions during behavior-preserving refactor;
- safety-floor pressure around recommend/draft/validate separation, human
  control, no publish/write/customer-reply paths, or raw-data boundaries.

Each refactor closeout should record countable substrate for the aggregate
review:

- batches since aggregate review;
- affected graph nodes;
- net module/file count change by node;
- public interface or export count change;
- number of files a caller must read to use the node;
- McCabe or complexity distribution when available;
- review blockers by stable code;
- `must_not_own` near-misses caught in review;
- promotion candidates by node;
- graph ownership edits by node;
- freeze/snapshot false positives.
- test assertion edits or justified exceptions by node.

Aggregate review must triage each recurring signal before proposing design
work:

- `map_error`: the code-review graph was incomplete or stale; fix the graph.
- `process_error`: the batch ignored scope, review, or closeout rules; fix the
  process or batch discipline.
- `architecture_error`: the current core/adapter/test boundary model is
  causing repeated friction; write a design note.

Only `architecture_error` activates architecture-level grounding such as
Architecture Patterns with Python. Do not use one ownership conflict as a
reason for broad redesign.

Aggregate review outcomes:

- continue current node-by-node refactor;
- pause and write a higher-level design proposal;
- promote recurring checks, tools, freeze-list entries, or review checklist
  items;
- demote or retire noisy checks;
- defer high-risk redesign to a separate KCS slice.

Threshold:

- one incident is recorded in closeout;
- the same boundary conflict in two aggregate reviews in a row requires a
  design note;
- a design note frames a separate slice question and is not implementation
  authorization.

A higher-level design proposal is not redesign authorization. It must become a
separately scoped slice with boundary questions, behavior/test frame, graph
updates, review checkpoint, and explicit classification as behavior-preserving
or behavior-change.

If Aggregate Review diagnoses `architecture_error` for core/adapters/tests, use
Architecture Patterns with Python only as targeted grounding for the relevant
chapters: service layer, ports/dependency inversion, and test boundary gears.
Do not introduce Repository, Unit of Work, Aggregates, message bus, or broader
framework patterns unless the design note names the concrete project pressure
they solve and the extra indirection is explicitly accepted.

Aggregate review must also confirm the MVP safety floor from
`docs/internal/kcs-authoring-mvp-goal-and-success-criteria.md` still holds:
recommend/draft/validate remain separated, human control remains intact, no
publish/write/customer-reply path appears, and raw-data boundaries remain
protected. This is evidenced by freeze/snapshot checks and related tests, not
re-argued from product success criteria.

Do not judge Slice 6 by product-value metrics such as faster KCS prep. Slice 6
is behavior-preserving and should be judged by agent-facing KCS-14 success
signals: clearer ownership, fewer recurring conflicts, quieter checks, and
more reviewable refactor batches.

## Readiness

Slice 6 is not ready for code movement until commit 0 freeze/snapshot checks
exist and the code-review graph covers repo refactor surfaces without an
unexplained gap.
