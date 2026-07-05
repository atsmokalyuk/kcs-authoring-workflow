# Engineering Roadmap

## Current Anchor

Current implementation state is anchored by the repository README and Jira
tracking document:

```text
Last completed implementation slice: KCS-13 Controlled Semantic Review
Current planned engineering/process hardening: KCS-14 Engineering and Codebase
Design Hardening
Deferred runtime hardening: KCS-15 KCS Style and Markup Parity
```

Historical KCS-1 guidance remains useful only as an early-slice boundary:
KCS-1 must not extract facts from clean-ticket prose. Use synthetic or approved
sanitized fixtures that are already shaped as normalized packet JSON.

## Semantic Extraction Placement

Plain meaning:

```text
Claude/parser may suggest what KCS items exist in a ticket.
Python decides whether that suggestion is valid enough to use.
Only validated Python output becomes canonical evidence for the KCS workflow.
```

`CandidateSemanticExtraction` means "a proposed interpretation of the ticket."
It is not trusted. It can come from a bounded Claude semantic review, a parser,
or another approved extractor.

`NormalizedTicketEvidencePacket` means "validated evidence accepted by Python."
This is what the decision engine, renderer, readiness checks, and bundle writer
are allowed to use.

Planned relationship:

```text
ticket / clean-ticket excerpts
  -> CandidateSemanticExtraction
     (proposed KCS items; untrusted)
  -> Python sanitizer / normalizer / validator
  -> NormalizedTicketEvidencePacket
     or blocker
```

Do not build this shortcut:

```text
clean ticket prose
  -> random Python code tries to understand the ticket directly
  -> NormalizedTicketEvidencePacket
```

Why: Python code is not a semantic reasoner. If the ticket is noisy or complex,
semantic identification must happen in an explicit bounded step. That step may
produce candidates, but it never owns the final workflow decision.

For Claude-assisted review, the safe path is:

```text
approved clean ticket
  -> bounded sanitized excerpts
  -> Claude proposes candidate_semantic_extraction_v1
  -> Python validates the proposal
  -> Python decides split/single/block
  -> Python renders the reviewer bundle
```

Claude helps identify candidate KCS items. Python still owns validation, KCS
action decisions, rendering, bundle output, and failure behavior.

If a future slice needs a chronology-preserving conversation builder, its job is
only to prepare a safe ordered context: turn order, speaker role, visibility
class, customer confirmation, support answer/resolution, open questions, and
explicit EOL mentions. It must replace/remove private values. It must not infer
KCS actions, perform online EOL lookup, call Claude, or create canonical
evidence directly.

## Slice Notes

- KCS-0: data handling baseline and implementation scope.
- KCS-1: contracts and fixtures only; establish pytest/Ruff baseline and basic contract checks.
- KCS-2: safety/evidence validation gates; add unsafe input and sanitizer expectation tests.
- KCS-3: deterministic KCS action decision; add decision matrix tests and keep branch complexity low.
- KCS-4: reviewer packet and Zendesk HTML renderer; add renderer and markup validation tests.
- KCS-5: validation report and ready/blocked loop state; add readiness regression tests.
- KCS-6: local CLI verification; add stable JSON output tests.
- KCS-7: evidence package builder; may define extraction interface but does not
  call Claude or perform semantic KCS item identification.
- KCS-8: Zendesk read-only ingest adapter.
- KCS-9: bounded Claude handoff umbrella.
  - KCS-9a-prep: chronology-preserving sanitized conversation context builder.
  - KCS-9a: approved semantic KCS item identification.
  - KCS-9b: bounded reviewer-assist handoff contract from compact safe packets.
  - KCS-9c: reviewer-only draft generation from validated handoff packets.
- KCS-10: local reviewer bundle writer for deterministic audit/debug artifacts.
- KCS-11: live Claude provider adapter for bounded provider smoke tests.
- KCS-12: Claude Desktop MCP validator/control adapter and MCPB package.
- KCS-13: controlled semantic-review fallback for complex/noisy approved clean
  tickets.
- KCS-14: Engineering and Codebase Design Hardening. Repo-native spec-first
  process, harness-portable review support, local tool entrypoints, code-review
  graph, compact agent context, and behavior-preserving codebase design
  refactor.
- KCS-15: KCS style and markup parity with the source KCS Style Guide, Article
  Quality criteria, KCS practices, approved article examples, and portable
  `plesk_support` rules. This is deferred and is not part of the current
  engineering/process hardening cycle.
- Future deployment slice: optional managed internal service version of the
  current local Claude Desktop workflow.

## Runtime Slice Boundary Reference

KCS-10 through KCS-13 are implemented runtime slices. Their active boundaries
are documented in the repository README, the core architecture/technical design
documents, and the KCS Desktop authoring refactor plan.

This roadmap does not duplicate completed runtime slice contracts. Future work
must preserve those active contracts unless an approved behavior-change slice
explicitly changes them.

## Deferred Runtime Hardening

KCS-15 style and markup parity is deferred and is not part of the current
engineering/process hardening cycle.

## KCS-14 Umbrella: Engineering And Codebase Design Hardening

KCS-14 is an umbrella plan, not a single implementation branch. It should be
implemented as small, reviewable slices that separate documentation ownership,
engineering process, local tool entrypoints, review context, code orientation,
behavior-preserving refactor, and later tooling.

Detailed local plan:
`docs/internal/engineering-process/slice-plans/kcs-14-engineering-and-codebase-design-hardening.md`

Design-review criteria:
`docs/internal/engineering-process/review-criteria/ousterhout-design-review-checklist.md`

Planned slice order:

```text
0. documentation-ownership-cleanup
1. engineering-process-baseline
2. local-tool-entrypoints
3. functional-test-from-behavior
4. review-context-protocol
5. minimal-code-map
6. codebase-design-refactor
7. review-and-agent-tooling
```

Documentation and process slices must not change runtime behavior, packet
contracts, Desktop behavior, privacy boundaries, fail-closed behavior, or the
`auto_publish_allowed=false` invariant.

Documentation ownership cleanup should happen first. The roadmap should remain
future-oriented; runtime invariants belong in architecture/contracts docs;
engineering rules belong in playbooks; completed runtime history belongs in
README or tracking docs; detailed slice plans belong under `slice-plans/`.
Move or reference constraints when reorganizing docs; do not delete active
constraints unless a later approved slice supersedes them.

KCS-14 engineering-process hardening should group spec-first design,
functional acceptance tests, evaluation, harness-portable review context, and
post-coding review support into a single workflow.

The target workflow:

```text
behavior definition
  -> functional acceptance tests
  -> implementation
  -> post-coding review against tests, contracts, and code-review graph
```

Planned features:

- behavior-defined functional tests: operator-defined behavior is converted
  into executable functional scenarios before implementation where practical;
- consolidated golden-case evaluation: pass/fail rubric for existing workflow
  contracts such as action correctness, evidence grounding, split/single/block
  behavior, blocker behavior, and no invented resolution details. KCS style,
  markup parity, and domain-output-quality hardening remain KCS-15 work;
- code-review graph: compact map of module ownership, contract edges, hard
  invariants, known risk areas, related tests, and recent review decisions;
- review handoff context: small review packets for ChatGPT Pro, Codex
  subagents, Fable 5 review, or future internal agents that include changed
  files, relevant graph nodes, expected contracts, and known deferred risks;
- agent-operable engineering workflow: detailed development-agent operating
  procedure below the existing `AGENTS.md` policy kernel, covering compact
  current state, context reset, output budgets, checkpoint summaries, review
  packets, and code-map usage. Codex work should prefer less context with
  higher authority: repo docs, current diff, failing test, and exact contracts
  over long chat history;
- local tool entrypoint spec: official repo-local commands for build,
  validation, smoke, install, log checks, and review-bundle generation so
  agents run supported tools instead of inventing ad-hoc shell workflows. This
  is the agent tool-surface specification for repository engineering workflow:
  `AGENTS.md` should carry a compact entrypoint index, while detailed usage
  belongs in a tool-entrypoints playbook and the executable behavior remains in
  `scripts/` and `tests/`;
- tool output budget policy: large outputs go to local files or bundles while
  chat/tool responses carry compact status, refs, hashes, and next actions;
- agent loop budget policy: retry limits, terminal blockers, and value-safe
  next actions prevent expensive or confusing agent loops. This belongs in the
  agent-operable engineering workflow, not runtime code;
- checkpoint and review metadata: manual process artifacts may record compact
  validation evidence, review verdicts, and deferred risks. Runtime/product
  transition records are out of KCS-14 unless approved as a later behavior
  change.

This should be repo-native and harness-portable. The source of truth should
stay in tracked repository docs, specs, scripts, tests, and graph artifacts. Codex,
ChatGPT Pro review, Fable 5 review, or a future internal runner may have thin
adapters that explain how to consume the same repo-local process, but those
adapters must not become the authoritative copy of the workflow.

Reusable design/spec infrastructure should start as project-local generic
templates, schemas, and validators. If the same workflow becomes useful in a
second project, extract the generic parts into a reusable package. Keep
project-specific contracts, such as KCS workflow rules, ticket storage,
semantic-review policy, and article-style rules, in this project.

The local tool entrypoint spec should live near `AGENTS.md` and the engineering
playbooks. It should be compact: name the supported task, the exact command,
and when to use it. This improves review determinism because agents can follow
stable tool surfaces such as "run installed stdio smoke" or "check Desktop
logs" instead of translating prose into inconsistent commands.

Functional tests should be written from behavior, not from accidental
implementation output. For example:

```text
behavior:
  "/draft ticket-94893302" with three KCS items should return all candidates;
  if the operator answers "all", draftable candidates are drafted and blocked
  candidates report specific blockers without manual drafting.

tests:
  test_multi_issue_ticket_returns_all_candidates
  test_operator_all_drafts_each_candidate_once
  test_blocked_candidate_reports_specific_blocker_without_manual_draft
```

The code-review graph is an orientation/index layer, not a replacement for
reading code. A new agent may use it to identify module ownership, contract
edges, hard invariants, known risk areas, and recent review decisions before
reading the touched files and direct dependencies.

The graph should be git-aware and easy to invalidate:

```text
node.file = repository path
node.commit = commit sha
node.file_hash = sha256
node.valid_until_changed = true
```

Possible manual artifacts:

```text
specs/agent-context/code-review-graph.json
specs/agent-context/module-boundaries.md
specs/agent-context/review-checkpoints.md
```

Do not add graph update scripts before the manual code map and review protocol
are stable.

The graph should support both spec-first planning and post-coding review:

```text
before coding:
  spec / task intent
    -> affected graph nodes
    -> expected contracts, adjacent files, tests, and docs

after coding:
  git diff / changed files
    -> affected graph nodes
    -> review checklist, required regression tests, and boundary-risk checks
```

For spec-first design, each substantial spec should be able to name the graph
nodes it expects to touch. This lets the implementer see the relevant
ownership boundaries before editing code and makes it easier to detect a spec
that is too broad, crosses unrelated modules, or needs a staged plan.

For post-coding review, the reviewer should use the graph to map changed files
back to responsibilities and invariants. This is intended to catch architecture
drift such as a Desktop adapter taking over semantic extraction, a renderer
starting to make KCS decisions, or a submit tool accepting broad payloads. The
review still reads the changed code directly; the graph only narrows and
sharpens the review path.

The graph may record ownership and contract edges such as:

```text
desktop_draft_tool -> Desktop call-shape validation
desktop_semantic_review -> bounded Claude semantic fallback
CandidateSemanticExtraction -> evidence -> decision -> renderer
renderer / zendesk_markup_quality -> article HTML and style gates
```

It must not contain raw tickets, selected semantic-review excerpts, reviewer
bundles, provider payloads, credentials, or long duplicated summaries of source
files. Tests should fail when graph nodes reference deleted files or stale file
hashes. This keeps the graph useful for multi-agent orientation without turning
it into a second, stale documentation system.

Agent review tooling should come after the review criteria and minimal code map
exist. Do not automate an unstable process. A minimal code map should precede
the behavior-preserving codebase design refactor so refactor review can check
module ownership, contract edges, and known invariants before files move.

The future deployment slice means this:

```text
current local workflow:
Claude Desktop -> local MCPB extension -> local Python workflow

possible future managed workflow:
Claude Desktop -> internal remote MCP URL -> deployed Python workflow service
```

This would be infrastructure and managed-operator access work: auth, ACLs,
audit logs, health checks, deployment packaging, and controlled internal
service access.

It must not change the product trust model. Claude Desktop remains a control
surface. Python still owns validation, KCS decisions, rendering, bundle output,
and failure behavior. It must not bypass KCS core validation, add Zendesk
writes, add Help Center publication, or treat the local MCPB wrapper as a
production security boundary.

## Deferred: Platform-Specific Agent Skill Packaging

Tracked repository engineering-process docs are the canonical source for
engineering modes and workflow behavior.

Do not create platform-specific development-agent skill adapters yet. Do not
add `local-docs/agent-skills/`, adapter folders, skill compilers, or generated
prompt packages.

Review harnesses are not development harnesses. ChatGPT Pro review and Fable 5
review may consume compact review packets without requiring generated
development-agent skill packaging.

Reconsider platform-specific packaging only when all of these are true:

- there are at least two actively used development-agent harnesses;
- the same repo-local workflow is repeated across those harnesses;
- the source workflow in tracked engineering-process docs is stable;
- generated or adapted skill behavior can be validated;
- maintaining adapters is clearer than using `AGENTS.md`, playbooks, and
  official local tool entrypoints directly.

## Quality Gate Placement

- Add local tests and Ruff configuration as soon as package setup exists.
- Add CI only after the local command set is stable enough to avoid noisy PR failures.
- Add hook automation only after the team agrees which local development runtime is approved.
- Keep `--no-verify` unavailable as a normal workflow. Failed checks should be fixed or explicitly deferred.
