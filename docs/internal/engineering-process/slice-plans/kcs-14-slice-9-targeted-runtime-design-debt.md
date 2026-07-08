# KCS-14 Slice 9: Targeted Runtime Design Debt Reduction

Status: planned.

## Purpose

Slice 9 exists because the operator does not want to carry avoidable
Ousterhout-style technical debt into KCS-15.

Slice 8 completed graph coverage, but graph coverage is not the same as
runtime code quality completion. Slice 9 is a targeted behavior-preserving
design-debt pass over the most critical KCS authoring runtime/core areas.

This is not a whole-repository cleanup pass.

## Goal

Reduce the highest-risk runtime/core design debt before user-visible KCS-15
style/markup work, while preserving the proven KCS authoring workflow.

Primary review lens:

- information hiding;
- ownership of knowledge;
- deep modules;
- reduced coupling and change amplification;
- avoidance of temporal decomposition;
- avoidance of shallow helpers, pass-through wrappers, and classitis.

## Non-Goals

Slice 9 must not:

- refactor every mapped file;
- use file size or cyclomatic complexity alone as a target selector;
- change runtime behavior;
- change packet schemas;
- change Desktop/tool schemas;
- change privacy, fail-closed, reviewer-bundle, publication, or customer-reply
  boundaries;
- open KCS-15 style/markup parity behavior;
- refactor frozen `tests/kcs_adapters/test_mcp_desktop.py`;
- extract reusable process or agent-skill packaging work.

## Candidate Runtime/Core Targets

### 1. Packet Validation And KCS Decisions

Graph node:

- `packet_validation_decision`

Files:

- `src/kcs_core/models.py`
- `src/kcs_core/validation.py`
- `src/kcs_core/safety.py`
- `src/kcs_core/decision.py`
- `src/kcs_core/evidence_builder.py`
- `src/kcs_core/sanitizer.py`

Why critical:

- owns KCS packet models, validation, safety checks, deterministic action
  recommendation, and blocker codes;
- has many contract edges;
- decision/blocker drift would be real runtime behavior drift.

Slice 9 entry question:

- Is validation/safety/decision knowledge duplicated or leaking across these
  files in a way that increases change amplification for KCS-15?

Allowed work:

- ownership review and design note first;
- behavior-preserving extraction only if it reduces what callers must know;
- characterization tests before movement if a boundary is touched.

Stop conditions:

- any packet schema field change;
- any status/blocker/reason-code behavior change;
- any privacy or fail-closed weakening.

### 2. Controlled Semantic Review Fallback

Graph node:

- `semantic_review_fallback`

Files:

- `src/kcs_adapters/desktop_semantic_review.py`
- `src/kcs_adapters/desktop_semantic_candidates.py`
- `src/kcs_adapters/desktop_semantic_providers.py`
- `src/kcs_core/semantic_extraction.py`

Why critical:

- owns bounded semantic-review state, source-ref rules, and
  `candidate_semantic_extraction_v1` validation;
- bridges Desktop workflow, provider output, and core packet validation;
- temporal decomposition would be especially harmful here.

Slice 9 entry question:

- Does semantic-review knowledge live in the right owner, or are schema,
  source-ref, and blocker rules leaking between workflow, provider, and core
  modules?

Allowed work:

- design audit first;
- targeted behavior-preserving refactor only around duplicated ownership or
  validation leakage;
- focused tests for unknown source refs, article HTML rejection, Markdown draft
  rejection, bounded excerpts, and blocked submit behavior.

Stop conditions:

- provider output gains decision authority;
- selected excerpts become broader or leak into artifacts;
- manual/freehand drafting path opens.

### 3. Reviewer Bundle Output

Graph node:

- `reviewer_bundle_output`

Files:

- `src/kcs_adapters/desktop_reviewer_bundle.py`
- `src/kcs_core/reviewer_bundle.py`
- `src/kcs_adapters/desktop_reviewer_preview.py`

Why critical:

- owns local reviewer bundle writing, manifest shape, relative refs, and hashes;
- privacy/path drift can expose local details;
- bundle writing must never become publication or customer-reply behavior.

Slice 9 entry question:

- Are bundle pathing, manifest, preview, and hash rules owned in one clear
  boundary, or do callers need to understand too much of the output internals?

Allowed work:

- behavior-preserving ownership cleanup if it reduces caller knowledge;
- focused tests for relative/value-safe paths, manifest shape, hashes,
  no-publication, and no customer reply.

Stop conditions:

- returned paths become absolute/private;
- bundle output becomes publishable/customer-facing;
- artifact writing happens before validated decisions allow it.

### 4. Renderer Output Gates Before KCS-15

Graph node:

- `renderer_style_gates`

Files:

- `src/kcs_core/renderer.py`
- `src/kcs_adapters/zendesk_markup_quality.py`
- `src/kcs_adapters/kcs_markup_patterns.py`
- `src/kcs_adapters/kcs_article_style_refs.py`

Why critical:

- KCS-15 will likely touch renderer/output behavior;
- current renderer code must be understandable enough to change safely;
- formatting cleanup can accidentally become behavior/style parity work.

Slice 9 entry question:

- Is there behavior-preserving test-harness or ownership cleanup needed before
  KCS-15, without changing renderer output?

Allowed work:

- test harness or helper ownership cleanup only if output stays identical;
- old-to-new renderer output mapping and golden/structural tests;
- no KCS-15 source-doc parity changes.

Stop conditions:

- HTML output changes without explicit KCS-15 behavior approval;
- new style/markup rules are introduced;
- renderer starts owning KCS decisions or semantic validation.

### 5. Provider Handoff Boundary

Graph node:

- `provider_handoff_boundary`

Files:

- `src/kcs_adapters/claude_provider.py`
- `src/kcs_adapters/approved_summary_semantic.py`
- `src/kcs_core/claude_draft.py`
- `src/kcs_core/claude_handoff.py`

Why critical:

- includes the current top runtime complexity hotspot:
  `approved_summary_semantic.py`;
- owns provider smoke, handoff, and draft packet helper surfaces;
- provider output must remain untrusted.

Slice 9 entry question:

- Is there a narrow provider-boundary design-debt fix that improves ownership
  without changing domain extraction behavior or provider trust boundaries?

Allowed work:

- design note first;
- refactor only if behavior examples and validator tests prove no output or
  trust-boundary drift;
- prefer documentation/ownership clarification if the risk is mainly domain
  behavior ambiguity.

Stop conditions:

- provider output can decide, render, publish, or write artifacts;
- runtime endpoints or credentials enter serializable packets;
- approved-summary extraction changes article content decisions without
  explicit behavior approval.

## Prioritization

Default Slice 9 order:

1. `packet_validation_decision`: highest runtime contract density.
2. `semantic_review_fallback`: highest workflow/provider/core boundary risk.
3. `reviewer_bundle_output`: local artifact/privacy boundary.
4. `renderer_style_gates`: only if KCS-15 needs pre-feature cleanup.
5. `provider_handoff_boundary`: design note first; code refactor only with
   explicit behavior examples.

This order may change if the first Slice 9 design audit finds a clearer,
lower-risk payoff elsewhere.

## Required Workflow For Each Target

Before code movement:

1. Declare the graph node and target files.
2. Answer the boundary questions.
3. Identify exact Ousterhout debt:
   - duplicated knowledge;
   - information leakage;
   - temporal decomposition;
   - shallow helper/class sprawl;
   - unclear owner of a design decision;
   - excessive caller knowledge.
4. List old behavior that must map to new code.
5. List related tests and any missing characterization tests.
6. Run freeze/snapshot/policy checks.
7. Decide whether the target is:
   - no action;
   - docs/graph ownership clarification;
   - behavior-preserving refactor;
   - deferred because it is behavior work.

After code movement:

1. Record behavior drift mapping.
2. Run focused tests.
3. Run policy/freeze/graph checks.
4. Record complexity sensor delta if the batch claims complexity reduction.
5. Record promotion/demotion candidates.
6. Run staged-diff review before commit.

## Acceptance Criteria

Slice 9 is successful if:

- the highest-risk runtime/core targets receive design-debt review;
- only targets with concrete ownership debt are refactored;
- behavior-preserving refactors have drift mapping and focused tests;
- no packet/schema/Desktop/privacy/publication/customer-reply contract changes;
- remaining debt is recorded with a specific future trigger, not hidden;
- KCS-15 can start with known renderer/output risks and pre-feature gates.

Slice 9 is not required to make every runtime file smaller.

## Review Checkpoint

After each target:

- local staged-diff review.

After two targets or any high-risk target:

- aggregate review.

Before closing Slice 9:

- external review checkpoint if any source code changed under
  `packet_validation_decision`, `semantic_review_fallback`,
  `reviewer_bundle_output`, `renderer_style_gates`, or
  `provider_handoff_boundary`.
