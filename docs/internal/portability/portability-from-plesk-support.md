
# Portability From plesk_support

## Purpose

Define how the local `plesk_support` prototype may be used as reference material for the corporate KCS Authoring MVP.

The goal is to reuse proven architecture and small portable implementation patterns without copying personal/local data, runtime artifacts, private paths, or environment-specific assumptions.

## Principle

The corporate project must be implemented in the approved corporate repository or sandbox.

The local `plesk_support` project may be used as a reference for:
- architecture;
- packet design;
- validation patterns;
- fixture structure;
- test coverage ideas;
- CLI/reporting behavior;
- KCS authoring lessons learned.

It must not be treated as a source project to copy wholesale.

For post-KCS-13 style/markup hardening, the target is result-level parity with
mature `plesk_support` KCS behavior, not code-level parity. Prefer the cleaner
`kcs-authoring-workflow` architecture whenever an equivalent rule can be
expressed as a deterministic renderer, quality, or style contract. Do not port
old chat-flow behavior, subject-specific heuristics, duplicated abstractions,
or adapter code that would weaken the current tool-owned workflow.

## Portable Concepts

These concepts are portable:

- runtime-independent Python core;
- typed packet contracts;
- schema-versioned JSON payloads;
- deterministic KCS action decision;
- safety and evidence gates;
- validation report;
- ready/blocked workflow state;
- reviewer-ready packet;
- Zendesk HTML renderer;
- no auto-publish invariant;
- bounded Claude handoff;
- temporary adapter boundary for search/reuse;
- principle: Code decides. LLM drafts. Validators block.

## Potentially Portable Code Patterns

Code may be reused only after review and cleanup.

Potentially portable:

- dataclass or typed model patterns;
- schema version constants;
- enum/value validation helpers;
- `to_json_dict()` style serialization;
- safe JSON loading helpers;
- value-free validation findings;
- blocker/warning/status structures;
- deterministic decision matrix shape;
- reviewer packet rendering structure;
- Zendesk HTML quality checks;
- fixture/golden test structure;
- CLI JSON output pattern.

## Not Portable

Do not copy:

- real or sanitized ticket data from the local project;
- `.private/**`;
- `.knowledge/**`;
- runtime artifacts;
- generated draft articles;
- local RAG indexes, chunks, vectors, or query logs;
- machine-specific paths;
- usernames;
- credentials, tokens, private endpoints;
- local-only scripts unrelated to KCS core;
- project-specific policy/evaluator code unless explicitly reviewed;
- unrelated solve/evolve portal code;
- UI/portal/Azure code;
- generated reports or snapshots.
- Plesk-only assumptions unless the corporate MVP explicitly confirms them;
- project-specific `AGENTS.md` policies that do not apply to the corporate repo;

## Import Strategy

Use the corporate documents as the source of truth:

- KCS Authoring MVP — Goal and Success Criteria;
- KCS Authoring MVP — Data Handling Baseline;
- KCS Core Pipeline — Architecture and Contracts;
- KCS Authoring MVP — Jira Tracking.

For each implementation slice:

1. Start from the corporate contract.
2. Inspect the relevant `plesk_support` module only as reference.
3. Copy only small, clearly portable code units when it saves duplicate work.
4. Remove source-project names, paths, assumptions, and unrelated behavior.
5. Add corporate tests before relying on reused logic.
6. Treat imported logic as new corporate code after review.

## KCS-1 Portability Scope

For KCS-1, only these are in scope:

- packet model shape ideas;
- schema version constants;
- enum validation approach;
- JSON serialization helpers;
- fixture layout ideas;
- basic contract tests.

Out of scope for KCS-1:

- full safety gates;
- KCS decision engine;
- Zendesk HTML renderer;
- article loop state;
- Claude handoff;
- live Zendesk adapter;
- local RAG adapter;
- style discriminator.

## Review Checklist Before Reusing Code

Before any code is copied or adapted:

- no private data;
- no local paths;
- no dependency on `plesk_support` repo layout;
- no raw ticket assumptions;
- no hosted/private data leakage;
- no write/publish behavior;
- no Claude-owned decision logic;
- no dependency on unavailable local tools;
- tests pass in the corporate repo;
- code style matches the corporate repo.
- no Plesk-only assumptions unless confirmed by corporate MVP scope;
- no copied local `AGENTS.md` behavior that conflicts with corporate repo rules;


## Source-Specific Tail Cleanup

Any adapted code must be reviewed for source-project tails before commit:

- no `plesk_support` package/module names;
- no local filesystem paths;
- no local workspace assumptions;
- no project-specific command names unless intentionally adopted;
- no references to local-only ticket preparation artifacts;
- no references to `.private`, `.knowledge`, local RAG storage, or generated report paths;
- no old branch names, Jira keys, PR names, or personal workflow assumptions;
- no copied comments that describe the old project instead of the corporate MVP.

## Deferred

Creating a shared reusable package is deferred.

Do not package common code until the corporate MVP proves which parts are stable enough to share.
