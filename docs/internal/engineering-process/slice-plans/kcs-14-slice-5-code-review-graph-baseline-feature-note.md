# Feature Note: Code-Review Graph Baseline

## Problem

Future KCS-14 refactor work can become unsafe if a development agent starts
from a list of files without knowing which module owns which design decision.
That encourages temporal decomposition, duplicated contract knowledge, and
review packets that miss adjacent boundaries.

## Decision

Add an advisory code-review graph baseline before codebase refactor work.

The graph maps ownership areas, contract edges, risky files, related tests, and
stable invariants. It is git-aware through repo-relative paths and file hashes,
so stale or deleted references fail locally instead of silently misleading a
future agent.

The initial Slice 5 graph covers every Python source file under `src/`, every
Python test file under `tests/`, and all refactor-relevant files under
`scripts/` and `packaging/`. Source files and packaging/tooling files are
mapped through hashed graph `files`; test files are mapped either through
hashed graph `files` when the test itself is the owned artifact or through
`related_tests` when the test validates an ownership node.

The graph is an orientation layer. Agents and reviewers must still read touched
files and direct dependencies.

## Workflow

Before coding:

```text
task intent
-> affected code-map nodes
-> module boundaries
-> touched files and direct dependencies
-> related tests
-> unchanged contracts
```

After coding:

```text
changed files
-> affected code-map nodes
-> boundary risks
-> related tests
-> review packet / closeout
```

## Agent Stop Condition

For refactor or cross-module behavior work, if the agent cannot map the change
to an affected code-map node, it must stop and either:

- ask for scope clarification;
- propose a small code-map update first;
- classify the task as outside the current KCS-14 refactor scope.

## Implemented In Slice

KCS-14 Slice 5 implements:

- `docs/internal/engineering-process/code-review-graph.json`;
- `docs/internal/engineering-process/module-boundaries.md`;
- `docs/internal/engineering-process/review-checkpoints.md`;
- policy checks for graph shape, repo-relative paths, file existence, full
  source/test/script/packaging coverage, and file-hash staleness.

## Not In Scope

- runtime behavior changes;
- packet schema changes;
- Desktop tool schema changes;
- automated graph generation;
- broad review tooling;
- KCS-15 style/markup parity;
- replacing source-code reading with summaries.

## Later Use

Slice 6 should select refactor targets from reviewed graph nodes and keep each
refactor PR scoped to one ownership area.

Slice 7 may add tooling that uses the graph for diff-to-contract review only
after the manual protocol proves stable.
