# Review Checkpoints

Status: authoritative KCS-14 Slice 5 review-orientation layer.

This document defines how to use the code-review graph during planning,
staged-diff review, and closeout. It is an engineering review protocol, not a
runtime product contract.

## Before Coding Or Refactor

For behavior or refactor work, do not start from a file list alone.

Use this sequence:

1. Define the behavior or refactor objective.
2. Identify affected nodes in `code-review-graph.json`.
3. Read `module-boundaries.md` for those nodes.
4. Read touched files and direct dependencies.
5. List unchanged contracts and related tests.
6. Confirm the behavior/test frame exists.

If no affected graph node can be identified, either the change is outside
KCS-14 refactor scope or the graph needs an explicit advisory update before the
refactor proceeds.

## During Staged-Diff Review

Map every staged source file to one or more graph nodes.

Check:

- changed files belong to the declared node scope;
- public/runtime contract preservation is demonstrated by snapshots, related
  tests, and frozen-path evidence unless a behavior change is explicitly
  approved;
- `must_not_own` boundaries remain true;
- no temporal split duplicates schema, validation, blocker, or format rules;
- no new shallow helper/class layer was added only to reduce file size;
- related tests cover the affected boundary;
- policy tests still pass for graph path and hash integrity.

Design judgment remains review-gated. Do not turn deep-module, classitis, or
ownership-quality questions into blocking regex checks unless a narrow
mechanically decidable rule exists.

## Review Packet Usage

After Slice 5, review packets should include affected graph nodes when
practical:

```text
Affected code-map nodes:
- semantic_review_fallback
- desktop_draft_workflow
```

The packet must still include changed files, affected contracts, validation,
and what must not change. The graph node list is an index, not evidence by
itself.

## Staleness Handling

`code-review-graph.json` records `file_hash` values for key files. If a file
hash changes, the graph entry is stale until reviewed.

Allowed outcomes:

- update graph file lists and hashes in the same slice when code movement is
  intentional and reviewed;
- leave the graph unchanged and treat the failing policy check as a blocker;
- change graph ownership definitions only when the ownership change is the
  declared scope of the batch.

Do not silence graph-staleness failures by deleting risky files from the map
without explaining the new owner.

## Closeout

Material slice closeout should state:

- affected graph nodes;
- batches since aggregate review, when the slice is part of Slice 6 refactor;
- whether graph hashes were updated;
- related tests run;
- unchanged contracts;
- promotion candidates or `none`.

If the same graph ambiguity recurs in two material reviews, record a promotion
candidate for a clearer code-map entry, review checklist item, or deterministic
policy check.

For new refactor work, the task's accepted behavior specification and this
document own the review cadence. Historical KCS-14 batch methodology remains
available in Git history; it is not an active release-tree dependency.
