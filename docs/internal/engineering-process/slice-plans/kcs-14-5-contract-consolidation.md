# KCS-14.5 Contract Consolidation

Status: complete.

Base: `d5de32f` (`feature/PAUX-7103-kcs-14.5-m4-simplification`).

Branch: `feature/PAUX-7103-kcs-14.5-contract-consolidation`.

## Purpose

KCS-14 reduced ambiguity and decomposed the Desktop authoring control surface.
KCS-14.5 then added multiple semantic experiments, transition contracts,
compatibility paths, diagnostics, and their tests while trying to stabilize
fresh-call multi-issue semantics.

The strict semantic-stability target is now closed as an architectural no-go:
a fresh nondeterministic model call cannot guarantee stable and correct issue
identity while it is the only semantic boundary authority. Operator-confirmed
requested drafting scopes are documented separately as a possible future
KCS-15 substage and are not part of this slice.

This slice consolidates the code around one active safe runtime contract. It
removes only mechanisms proven to be inactive, rejected, or transitional. It
does not roll the repository back wholesale and does not delete the Git or
tracked design history of the experiments.

## Current-State Evidence

From KCS-14 final closeout `c51ca35` to KCS-14.5 checkpoint `d5de32f`:

- 124 files changed;
- 31,507 insertions and 3,037 deletions overall;
- 58 source/test files changed;
- 14,722 insertions and 2,625 deletions under `src/` and `tests/`.

These counts establish expansion, not waste. Removal decisions must use active
runtime reachability, ownership, recorded experiment verdicts, and behavior
tests rather than line count alone.

## Goal

Leave one understandable active semantic authoring line:

```text
approved clean ticket
-> complete bounded original evidence
-> semantic_issue_proposal_v1
-> Python validation and issue projection
-> native candidate selection when required
-> deterministic authoring, reuse, safety, rendering, and result ledger
```

Historical rejected contracts remain recoverable in Git and described in the
tracked experiment records, but no longer occupy production modules or active
test/control surfaces.

## Stable Contracts And Behaviors

The following remain unchanged:

- `ticket_ref` is the primary operator entry path;
- the existing six-tool Claude Desktop surface;
- no new direct provider API or development MCP surface;
- approved clean-ticket metadata and SHA-256 binding;
- complete eligible bounded original text blocks;
- exact extractive grounding for non-summary semantic observations;
- `semantic_issue_proposal_v1` as the active semantic submit contract;
- Python-owned schema validation, evidence admissibility, projection,
  selection state, KCS action, readiness, rendering, persistence, and batch
  accounting;
- native one/subset/all selection only when the active result carries its
  native choice contract;
- per-issue evidence blockers preserve valid siblings;
- missing mandatory resolution evidence remains fail-closed;
- diagnostic semantic outcomes do not authorize an operator action;
- reviewer artifacts remain local and reviewer-only;
- no manual/freehand draft bypass;
- no Zendesk write, Help Center write, customer reply, or publication path;
- `auto_publish_allowed=false`;
- `public_output_approved=false`;
- Langfuse remains an optional value-safe observer and never a workflow layer.

## Non-Goals

This slice does not:

- attempt fresh-call semantic stabilization;
- implement operator-confirmed drafting scopes;
- change model instructions to seek a different partition;
- add a semantic schema, graph, relation, root, anchor, or retry strategy;
- weaken grounding, completeness, privacy, safety, or renderer gates;
- restore boundary re-proposal, evidence exclusion, accept-scope, or normal
  operator-authored-resolution questions;
- revert wholesale to `c51ca35` or any other unproven historical runtime;
- remove active behavior merely to improve line-count metrics;
- erase experiment documentation or Git history;
- combine KCS-15 style/markup work with consolidation.

## Classification Rules

Every candidate belongs to exactly one class before editing:

| Class | Meaning | Allowed action |
| --- | --- | --- |
| `keep-active` | Called by the installed runtime or required by a stable active contract | Preserve and characterize |
| `retire-inactive` | No active runtime caller; recorded as rejected/retired; tests only itself | Remove from production code and active tests |
| `research-history` | Useful experiment evidence but not an active runtime contract | Keep in tracked docs or Git, not production modules |
| `compatibility-review` | May preserve an old import/payload contract | Remove only after explicit consumer and freeze review |
| `unknown` | Reachability or contract status is incomplete | Do not edit |

An item cannot be classified `retire-inactive` from naming, age, or apparent
complexity alone.

## Initial Keep/Delete Map

### Keep active

- `semantic_issue_proposal_v1` packet and validators;
- issue proposal projection and per-issue disposition;
- exact evidence preservation and source-ref validation;
- model-neutral ordinary evidence roles;
- proposal wire canonicalization for the installed client;
- complete transcript-turn preservation and bounds failure;
- native operator selection and Python-owned sequential batch accounting;
- value-safe blocker/counter diagnostics;
- explicit terminal no-action presentation;
- narrow explicit public-resolution-reference reuse behavior;
- safety, renderer, reviewer-only, and publication prohibitions.

### Retire in first batch

`semantic_claim_ownership_v1` is recorded by the decision log as rejected and
reverted. The code-review graph explicitly calls its contract and projection
inactive. Production search finds no caller of
`project_semantic_claim_ownership`; only the contract's own tests exercise it.

First-batch removal perimeter:

- `SemanticClaimKind`;
- `SemanticClaim`;
- `SemanticClaimOwnershipPacket`;
- claim-only constants, allowed-field sets, and validators;
- `ClaimOwnershipLedgerEntry`;
- `ClaimOwnershipProjection`;
- `_ClaimRoot`;
- `project_semantic_claim_ownership` and claim-only projection helpers;
- claim-only unit/projection test files;
- code-review graph entries that describe the inactive source/tests as active
  review coverage.

The flat-claim design and canary documents remain as research history.

### Require later review

- legacy `candidate_semantic_extraction_v1` compatibility surface;
- semantic shadow comparison helpers and rebaseline scripts;
- compatibility selection payloads;
- Langfuse rebaseline tests and scripts;
- incident-only characterization tests;
- any function imported through a private historical path;
- any package guidance or freeze snapshot that still describes a supported
  runtime surface.

These are not authorized deletion targets in the first batch.

## Implementation Batches

### C0: Active-path characterization

Before deletion:

- run focused core issue-proposal tests;
- run focused issue-projection tests;
- run semantic-review submission tests;
- run Desktop adapter tests that prove the active submit and native selection
  contracts;
- record exact test counts and failures.

### C1: Remove inactive claim ownership island

- remove claim-only production definitions and projector code;
- remove claim-only self-tests;
- narrow shared type annotations to the active issue-proposal packet;
- update code-review graph and policy/freeze references only where they falsely
  list the inactive contract as an active surface;
- preserve historical design/canary documentation;
- rerun the C0 characterization and policy checks.

Acceptance for C1:

- no source/package/script reference to the inactive claim contract remains;
- active issue-proposal tests have identical outcomes;
- active Desktop schemas and tool descriptors are unchanged;
- no model-visible instruction, tool name, or result field changes;
- source/test line reduction is reported but is not the acceptance criterion.

### C2: Compatibility and shadow inventory

After C1 checkpoint, audit each later-review candidate for:

- runtime importers;
- packaged consumer references;
- schema/freeze snapshots;
- local scripts and official entrypoints;
- existing external/client compatibility evidence;
- whether its purpose is active product behavior, engineering diagnostics, or
  historical research.

Produce a new keep/delete table. Do not implement C2 deletions in the same
batch as C1.

### C3: Optional second deletion batch

Authorize only from the C2 inventory and a separate compact checkpoint. Each
deletion family needs one stable-contract statement, one focused
characterization set, and one stop condition.

## Test And Validation Plan

Minimum C1 validation:

```text
focused semantic issue proposal tests
focused active issue projection tests
semantic review submission tests
focused Desktop MCP characterization tests
policy/freeze tests affected by the deleted inactive surface
Ruff on touched Python files
git diff --check
```

The installed Claude Desktop canary is not required for deletion of code that
has no installed runtime caller and causes no model-visible diff. If package,
tool schema, descriptor, instruction text, or result shaping changes, stop and
add an installed smoke gate before promotion.

## Behavior Drift Review

For every deletion batch record:

```text
old -> new
  inactive contract accepted internally -> contract no longer exists

new -> old
  active semantic_issue_proposal_v1 behavior -> identical active behavior
```

Review must verify:

- no active caller was removed;
- no exception/debug code changed on the active route;
- no input/output schema changed on the six tools;
- no safety or data boundary weakened;
- no test was deleted merely because it failed after an unrelated behavior
  change;
- research evidence remains available in Git/tracked docs;
- code-review graph no longer misrepresents retired code as active.

## Stop Conditions

Stop the batch when any of the following occurs:

1. a proposed deletion has an active runtime, package, script, or external
   compatibility consumer;
2. an active characterization result changes;
3. a tool schema, descriptor, instruction, compact result, or native choice
   payload changes unexpectedly;
4. a safety, privacy, grounding, completeness, reviewer-only, or publication
   invariant changes;
5. removal requires a compatibility shim larger than the code being removed;
6. the batch crosses from inactive removal into semantic behavior redesign;
7. the same failure prompts another speculative helper or contract;
8. the diff cannot be reviewed as one ownership-boundary deletion.

## Review And Closeout

The slice requires:

- staged diff sanity and unintended-touch review;
- module-boundary and code-review-graph review;
- behavior drift mapping;
- focused deterministic validation;
- deeper architecture/data-boundary review if a later batch reaches package,
  metadata, persistence, or model-visible surfaces;
- a compact checkpoint after each commit or aggregate review;
- promotion-candidate review for any repeated rule that should move from prose
  to a deterministic or structural gate.

The slice closes when one active semantic contract remains clearly documented,
all removed mechanisms are recoverable from Git/history, and no authorized
deletion candidate remains unclassified. It does not need to return to the
KCS-14 line count.

## C1 Implementation Checkpoint

Status: committed in `698c77a`; post-commit validation passed.

Changed behavior:

- the rejected internal `semantic_claim_ownership_v1` packet and projector are
  no longer importable from production modules.

Unchanged behavior:

- the active `semantic_issue_proposal_v1` parser, validator, projector,
  Desktop submit route, native selection, authoring, safety, renderer, storage,
  and result contracts are unchanged;
- the active submit surface still rejects `semantic_claim_ownership` and
  `semantic_claim_ownership_v1`;
- no model-visible tool schema, descriptor, prompt, result text, or package
  entrypoint changed.

Pre-edit characterization: 132 passed.

Post-edit active-path characterization: 382 passed, 1 freeze-only dirty-tree
check deselected. The deselected check is intentionally post-commit because it
requires frozen files to match `HEAD`. Ruff passed. The code-review graph
policy also exposed one pre-existing stale hash for
`desktop_tool_results.py`; the graph evidence was corrected without changing
that source file.

Net source/test change before documentation and graph metadata: 1,156 lines
removed and 3 blank-line/type-narrowing lines added.

## C2 Compatibility And Shadow Inventory Checkpoint

| Surface | Classification | Evidence and action |
| --- | --- | --- |
| `candidate_semantic_extraction_v1` | `keep-active` | Used by the current approved-summary and fixture providers, candidate conversion, core package exports, and Desktop tests. It remains a bounded legacy island, not dead code. |
| native selection refs and one/all payloads | `keep-active` | Used by tool schemas, draft argument validation, pending selection, batch continuation, packaging tests, and installed smoke parsing. |
| semantic shadow comparison and rebaseline harness | `keep-engineering` | Not called by product runtime, but it is a documented engineering entrypoint and feeds the Langfuse record exporter. Retirement requires a separate tooling decision. |
| Langfuse rebaseline exporter | `keep-engineering` | Optional and runtime-independent, but still an explicitly documented value-safe observability entrypoint with privacy tests. Do not remove implicitly as product legacy. |
| runtime control-surface incident characterization | `keep-active-regression` | Protects the terminal-presentation incident contract recorded in the decision log. Deleting it would remove a regression guard, not simplify runtime. |
| generic `ApprovedSemanticExtractionClient` / `ApprovedSemanticExtractionProvider` | `retire-inactive` | No runtime, environment, package, script, or test constructs it. Only its own `__all__` entry and `desktop_workflow` re-export reference it. It is an unimplemented future external-provider seam; the active local approved-summary provider is separate. |

The generic approved-provider seam is the sole authorized C3 deletion from
this inventory. `SEMANTIC_PROVIDER_APPROVED`, the approved-summary provider,
fixture provider, unavailable-provider behavior, and `SemanticExtractionProvider`
core protocol remain unchanged.

## C3 Implementation Checkpoint

Status: committed in `66f0dc7`; post-commit validation passed.

Removed:

- unused generic `ApprovedSemanticExtractionClient` protocol;
- unused generic `ApprovedSemanticExtractionProvider` adapter;
- their `__all__` entries and `desktop_workflow` aliases.

Unchanged:

- environment routing still selects the local approved-summary, fixture, or
  unavailable provider exactly as before;
- `SEMANTIC_PROVIDER_APPROVED` remains an alias for the active local
  approved-summary route;
- `CandidateSemanticExtraction`, provider validation, semantic review, native
  selection, tool schemas, and installed package behavior are unchanged.

Pre-edit provider/workflow characterization: 245 passed. Post-edit targeted
characterization: 244 passed with the post-commit dirty-tree freeze check
deselected. Ruff passed.

## Final Dead-Helper Audit

An AST/token inventory over production modules found three private helpers with
no caller in source, scripts, packaging, or tests:

- `_batch_followup_group_line`;
- `_string_array_schema`;
- `_validate_validation_report_metadata_string`.

Each helper is removed mechanically. Their owning active paths remain covered
by Desktop/MCPB schema and result tests plus core model/validation tests.
Pre-edit characterization: 288 passed. Private helpers with an explicit
characterization-test consumer, including `_segments`, are retained.

No other production symbol from the inventory is authorized for removal. The
remaining low-reference helpers are called from active code, intentionally
exercised by incident characterization, or form documented engineering tools.

The helper cleanup is committed in `ae79087`; post-commit validation passed.

## Closeout

Commits:

- `698c77a` retires the rejected flat claim-ownership contract and projector;
- `66f0dc7` removes the unused future external-provider seam;
- `ae79087` removes three unreachable private helpers.

Aggregate diff from `d5de32f`:

- 12 files changed;
- 436 insertions, primarily this plan and the decision-log record;
- 1,250 deletions;
- under `src/` and `tests/`: 5 insertions and 1,240 deletions.

Behavior drift:

```text
old -> new
  rejected/internal contracts and unreachable helpers existed -> removed

new -> old
  active semantic proposal, provider routing, Desktop tools, selection,
  authoring, safety, rendering, persistence, diagnostics -> unchanged
```

Final validation:

- full post-commit suite: 1,427 passed, 1 skipped;
- Ruff passed for every touched Python file;
- freeze/snapshot and code-review-graph policies passed;
- `git diff --check` passed;
- worktree clean.

No installed Desktop canary was required because no tool schema, descriptor,
instruction, model-visible result, environment routing, packaging entrypoint,
or runtime behavior changed.

The active semantic submit contract is now `semantic_issue_proposal_v1`.
`candidate_semantic_extraction_v1` remains as an explicitly bounded active
provider-compatibility island rather than being mislabeled as dead legacy.
Synthetic rebaseline/Langfuse tooling remains an explicitly bounded engineering
surface. Further removal needs a new compatibility or tooling-retirement
decision; it is not part of this closeout.

## Integration Readiness

The consolidation branch is a direct descendant of the KCS-14.5 M4 checkpoint
`d5de32f`. Its four commits can be reviewed as the consolidation-only range
`d5de32f..465bce3` plus this integration-readiness note. No merge back into the
M4 branch is required; this branch is the newer KCS-14.5 checkpoint.

The local `feature/PAUX-7103-kcs-14-engineering-hardening` and
`feature/PAUX-7103-test-suite-maintainability` refs point to ancestor
`497d22d`. The primary workspace on that commit contains unrelated uncommitted
changes, including files touched by later KCS-14.5 work. Do not merge,
fast-forward, checkout, or cherry-pick into that worktree until those changes
are independently closed or relocated.

Remote `main` is still at the KCS-13 line. A direct PR from this branch to
remote `main` would contain 219 commits and about 60,000 inserted lines, not a
reviewable contract-consolidation PR. Integration therefore needs an explicit
stacking decision: first integrate the existing KCS-14/KCS-14.5 ancestor
chain, or review this four-commit consolidation range against `d5de32f` on a
stacked branch. Do not present a direct-to-main PR as consolidation-only.

No push, PR, merge, branch deletion, or primary-worktree mutation is performed
by this closeout.
