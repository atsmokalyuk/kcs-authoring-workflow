# KCS-14 Planning Decisions

## Purpose

This document records the pre-implementation decisions for KCS-14 so the first
implementation slice starts from repository context instead of chat history.

KCS-14 is not "make docs and code nicer". KCS-14 is "reduce ambiguity for
future AI-assisted engineering while preserving runtime behavior".

This is a planning decision record. It does not change runtime behavior,
packet contracts, Desktop behavior, privacy boundaries, publication behavior,
or reviewer-bundle behavior.

## Active Numbering

Forward-looking repository documents should use this numbering:

- KCS-14: Engineering and Codebase Design Hardening.
- KCS-15: KCS Authoring Quality through source style/markup parity, approved
  examples, and assisted reuse, active through independently approved slices.
  KCS-15.1 PLESK_INFO trigger parity is complete. KCS-15.2 owns
  RAG-assisted reuse: KCS-15.2a adapter/readiness is complete, while KCS-15.2b
  operator comparison remains design-open and Delivery-locked. KCS-15.3 and
  KCS-15.4 retain the remaining deterministic and model-mediated style/quality
  inventory.

Historical files may mention the older KCS-14 style/markup framing only when
the text is clearly historical. Active README, roadmap, Jira-tracking,
playbook, and policy-kernel references must not leave an unmarked
"KCS-14 = style/markup parity" interpretation.

Slice 0 evidence must include a grep check for `KCS-14` and `KCS-15` across
active README, docs, and playbook files.

## External Tracking Boundary

Codex may update repository files. Jira and Confluence records require
operator or maintainer action.

The repository tracking document should record the local mapping:

- PAUX-7083: historical pipeline prototype and completed KCS-0..KCS-13 work.
- PAUX-7103: engineering and codebase design hardening umbrella, if confirmed
  by the operator.

If external Jira rollout is postponed, the repo should record the exception
instead of pretending external tracking was updated.

## Tracked Homes

KCS-14 authoritative process artifacts must be tracked. `local-docs/` is
developer-local and ignored by Git today, so it cannot remain the only home for
authoritative KCS-14 rules.

Proposed tracked homes:

- `AGENTS.md`: short non-negotiable policy kernel and compact entrypoint index.
- `docs/internal/engineering-process/`: project-specific engineering process,
  KCS-14 slice plans, review notes, tool-entrypoint docs, and planning
  decisions.
- `engineering-playbook/`: project-local generic templates and checklists.
  This is not a package and does not authorize extracting an
  `engineering-spec-kit`.
- `docs/internal/`: runtime, data-handling, architecture, Jira-tracking, and
  project-specific contract documents.

Local-only homes:

- `local-docs/`: personal notes, temporary drafts, learning notes, Fable
  packets, experiments, and local-only implementation notes.

Generic playbook files must not duplicate KCS-specific invariants. They should
reference the project-specific contract documents and freeze lists instead.

## Reopening Scope

The README should record a narrow reopening:

```text
Development is reopened only for KCS-14 engineering/process/codebase hardening.
Runtime feature work, KCS-15 style parity, production rollout, Zendesk writes,
Help Center publication, and auto-publish remain frozen or deferred.
```

This reopening does not authorize runtime feature work.

## Roadmap-Only Feature Disposition

- Structured workflow observability is out of KCS-14 if it means runtime or
  product transition records. Manual review metadata and checkpoint summaries
  are allowed as process artifacts.
- Golden-case evaluation is allowed for synthetic fixtures and approved
  clean-ticket fixtures that are safe under the data-handling baseline.
- Agent loop and tool output budgets belong in the agent-operable engineering
  workflow, not runtime code.
- Code-review graph scripts are deferred until the manual code map and review
  protocol are stable.
- Reusable design/spec infrastructure extraction is deferred until after
  KCS-14 has been field-tested on behavior-preserving refactor work and
  KCS-15 has tested the same process on feature-heavy style/markup work. A
  post-KCS-15 retrospective should decide whether KCS-16a is needed for
  engineering-process stabilization before any extraction.
- KCS-16b may extract reusable engineering infrastructure only after the
  process is stable and a second project or independent subsystem proves
  portability. It is not automatic: it starts only if the retrospective shows
  that the same templates, review packets, tool entrypoints, and gates worked
  across both refactor-heavy and feature-heavy slices with less manual
  correction.
- KCS-17 is the handoff and initiation boundary for a separate personal
  agentic engineering kit project after reusable extraction is stable and
  useful outside the immediate KCS workflow. KCS-17 may define the export
  manifest, compatibility boundary, and evidence handoff, but it does not own
  agent roles, orchestration, the integration gate, or stable kit packaging.
  The separate project integrates extracted assets into beta roles, runs the
  end-to-end gate, and packages a stable kit only after that gate passes.
  Choose its architecture after KCS-14/KCS-15 field results and a current
  review of agentic-engineering tooling. KCS-14 should stabilize repo-native
  practice first, not create a premature shared package.

Golden-case evaluation for KCS-14 must stay within existing behavior
contracts: action decision, split/single/block behavior, evidence grounding,
blocker behavior, and no invented resolution details. KCS style, markup
parity, and domain-output-quality hardening belong to KCS-15 unless a later
approved behavior-change slice says otherwise.

Clean-ticket-derived fixtures need a two-level model:

- committed sanitized fixtures: portable, approved, privacy-scanned,
  commit-safe test cases;
- local-ref fixtures: approved local clean-ticket references that are skipped
  when absent and must not make the suite machine-dependent.

## Enforcement Ladder

KCS-14 should reduce prose-only rules over time. Each rule belongs at the
cheapest layer that can enforce it honestly:

```text
1. structural: violation is impossible by structure, types, or ownership
2. deterministic: violation fails a local test, script, or check
3. review gate: violation needs human/design judgment
4. measurement: violation is a trend across slices
```

Mechanically decidable rules should migrate down to deterministic checks as
soon as the rule is stable enough. Judgment-based design questions stay in
review packets and Ousterhout-style review; do not fake design quality with a
blocking regex.

Blocking vs advisory line:

- runtime invariants, packet contracts, privacy boundaries, fixture
  provenance, forbidden content, path existence, freeze-list contracts, and
  schema/tool-surface hashes may block;
- naming/style conventions and design smells may lint or route to deeper
  review;
- deep-module quality, ownership-vs-temporal decomposition, and "does this
  reduce what callers must know" remain review judgments;
- recurring process failures are measured as slice metadata, not product
  runtime observability.

Any review finding that recurs twice should be classified as one of:

- deterministic check candidate;
- structural boundary candidate;
- advisory review tripwire;
- measurement-only signal.

Do not add an upfront policy-test framework. Each slice should add only the
small checks needed to lock in that slice's own outcome.

## Slice 0 Acceptance

Slice 0 is documentation ownership cleanup. Its first task is to record and
apply these decisions in tracked repository documents.

Required evidence:

- numbering reconciliation for KCS-14/KCS-15;
- grep check for unmarked active `KCS-14` style/markup references;
- tracked-home decision applied to authoritative process artifacts;
- README narrow reopening text;
- PAUX-7083 / PAUX-7103 ownership mapping or documented external-tracking
  exception;
- roadmap trimmed to future ordering and pointers rather than duplicated
  contracts/process rules;
- migration table: constraint, old location, new location, status
  `moved` / `referenced` / `unchanged`;
- migration decisions recorded in this document and preserved in Git history;
- expanded touched-list for README, AGENTS, Jira tracking, feature engineering,
  playbooks, architecture/contracts docs, and any old roadmap/refactor docs
  that still carry active KCS-14 meaning.
- first deterministic checks planned for Slice 0:
  - numbering/history grep check for active `KCS-14` style/markup references;
  - doc-reference validator for paths cited by `AGENTS.md` and tracked process
    docs.

Slice 0 must not change runtime behavior, packet contracts, Desktop behavior,
privacy boundaries, fail-closed behavior, local reviewer-bundle behavior, or
`auto_publish_allowed=false`.

## Inter-Slice Gates

- 0 to 1: migration table complete, numbering reconciled, README reopening
  recorded, roadmap future-oriented, authoritative tracked homes selected,
  numbering/history check planned or added, and doc-reference validation
  planned or added.
- 1 to 2: workflow doc authoritative, `AGENTS.md` / workflow / Codex
  instructions have no contradictions, supported harness list is accurate, a
  harness-list grep check is planned or added for active docs, and slice
  closeout metadata format exists.
- 2 to 3: official commands are current, deterministic vs manual checks are
  classified, command evidence is captured, and the cheapest deterministic
  entrypoints have liveness checks where practical.
- 3 to 4: contract-to-test inventory exists for risky boundaries, forbidden
  paths are covered, fixture provenance policy is documented, and committed
  clean-ticket-derived fixtures have approval/provenance plus privacy-scan
  checks.
- 4 to 5: at least one compact review packet has been used and the verdict is
  recorded; a file-based review packet format exists; review packet shape and
  forbidden-content checks are planned or added.
- 5 to 6: code map reviewed, staleness check defined, refactor target list and
  freeze list published.
- 6 to 7: two consecutive review cycles used the manual protocol without
  protocol edits before automation starts; recurring review findings are
  classified as deterministic-check candidates, advisory review tripwires, or
  measurement-only signals.

## Expected Checks By Slice

- Slice 0: numbering/history grep check; doc-reference validator; migration
  table review evidence.
- Slice 1: unsupported-harness grep check for active docs, including ensuring
  Claude Code is not described as an active engineering harness.
- Slice 2: tool-entrypoint liveness checks for the cheapest deterministic
  commands; deterministic/manual command classification.
- Slice 3: fixture provenance checks, privacy scan for committed clean-ticket
  fixtures, and skip-if-absent behavior for local-ref fixtures.
- Slice 4: review packet shape validator and forbidden-content check.
- Slice 5: code-map stale file/hash check.
- Slice 6: freeze-list diff check and schema/tool-surface hash checks; design
  quality remains review-gated, not regex-blocked.
- Slice 7: automate only checks that survived manual use; keep advisory
  design tripwires non-blocking unless promoted by explicit review.

## Post-Slice 6 Sequence

After Slice 6 closeout, do not continue refactor batches by mining remaining
large files or measured hotspots. The next default KCS-14 step is Slice 7
review/agent tooling because Slice 6 produced a promotion backlog that should
be converted into stable review support before opening more refactor work.

Slice 7 scope should start from promoted evidence, including:

- old-vs-new behavior equivalence support for behavior-preserving refactors;
- closeout shape validation where the manual closeout format has stabilized;
- full complexity/coupling/interface delta reporting when a closeout cites the
  complexity sensor;
- checklist-level contract-term/spec-table extraction guidance;
- any small targeted tests accepted from external review, such as alias
  precedence, when they protect existing behavior.

Parked refactor follow-ups are separate operator-approved slices, not normal
Batch 23 work:

- `src/kcs_core/errors.py`: first handle as a small ownership/map question.
  It may end as a module-boundary or graph update without code movement.
- `tests/kcs_adapters/test_mcp_desktop.py`: may be reopened only as an
  explicit characterization-suite maintainability slice. While this safety net
  is being refactored, do not change related source files in the same commit.
- `src/kcs_adapters/approved_summary_semantic.py`: remains deferred under the
  provider-handoff boundary. Do not open it for complexity cleanup unless a
  later approved design question changes that boundary.

This sequence preserves the KCS-14 outcome contract: convert proven manual
findings into durable checks before taking on additional refactor risk.

## Post-Slice 7 And Slice 8 Sequence

Slice 8 was added as a review-only code-review graph coverage closeout after
Slice 7 converted the Slice 6 promotion backlog into stable review support.

Slice 8 purpose:

- verify that remaining graph nodes have an explicit coverage disposition;
- avoid continuing refactor by large-file or hotspot mining;
- record which nodes are covered by Slice 6 evidence, which are reviewed
  without code movement, and which stay deferred;
- classify `map_error`, `process_error`, and `architecture_error` before final
  KCS-14 closeout.

Slice 8 coverage disposition:

- `smoke_log_tooling`: covered by Slice 6 refactor evidence, aggregate reviews,
  and external review; no separate Slice 8 pass required.
- remaining graph nodes: covered by Slice 8 review-only node notes and
  aggregate reviews.

Slice 8 found no `architecture_error`; Architecture Patterns with Python was
not activated. External review said KCS-14 could close after closure-record
fixes, but the operator chose to reduce the highest-risk runtime/core design
debt before KCS-15 instead of closing immediately.

## Slice 9 Targeted Runtime Design Debt Decision

Slice 9 is a targeted Ousterhout-style design-debt pass over critical runtime
KCS authoring core areas before KCS-15.

Slice 9 is not a whole-repository cleanup pass. It exists because graph
coverage and a targeted Slice 6 refactor do not prove that the most involved
runtime/core files are clean enough for feature-heavy KCS-15 work.

The completed target disposition is summarized in
`docs/internal/engineering-process/slice-plans/kcs-14-final-closeout.md`.

Default target order:

1. `packet_validation_decision`;
2. `semantic_review_fallback`;
3. `reviewer_bundle_output`;
4. `renderer_style_gates`, only for behavior-preserving pre-KCS-15 readiness;
5. `provider_handoff_boundary`, design note first and code only with explicit
   behavior examples.

Slice 9 must still preserve all frozen runtime contracts. It may end some
targets with "no code movement" when the review finds that behavior risk is
higher than the design-debt payoff.

## Slice Closeout Measurement

KCS-14 may use value-safe closeout metadata to see whether the process is
improving. This is not runtime workflow observability.

Material release conclusions live in
`docs/internal/engineering-process/slice-plans/kcs-14-final-closeout.md`.
Intermediate batch evidence remains available in Git history and should not be
copied into new tracked journals.

Closeout records should be enum/count/path based and avoid raw tickets,
private payloads, excerpts, reviewer bundles, provider payloads, credentials,
and customer identifiers.

Useful fields:

- slice id;
- review route;
- validation result;
- retry count bucket;
- recurring blocker codes;
- review blocker count;
- deterministic checks added;
- findings promoted to future checks;
- deferred risks.

## Slice 6 Refactor Boundaries

Initial candidate ownership areas:

- provider smoke and log tooling;
- tool surface and MCP result shaping;
- clean-ticket `ticket_ref` storage and metadata;
- semantic review state and submit validation;
- packet validation, readiness, and safety gates;
- reviewer bundle writing;
- renderer and reviewer output boundaries, behavior-preserving only.

Prefer lower blast-radius adapter and smoke/log areas before safety gates,
validation gates, renderer behavior, or output boundaries.

Starting freeze list:

- packet `schema_version` families;
- blocker, warning, `required_next_step`, and `state` enums;
- safety gate input and visibility classes;
- Desktop tool schemas and compact output behavior;
- `semantic_issue_proposal_v1` acceptance rules and the bounded
  `candidate_semantic_extraction_v1` compatibility island;
- `clean_ticket_sha256` metadata binding;
- local reviewer-bundle pathing;
- compact-default vs debug-only `reviewer_only_html`;
- `auto_publish_allowed=false`;
- `public_output_approved=false`;
- `ticket_ref` primary path;
- manual/freehand drafting remains blocked.

Any refactor PR that changes a frozen contract must stop and become an explicit
behavior-change proposal.

Behavior-preserving implementation touches to frozen-path files must follow
the `KCS14-PROMO-010` protocol: unchanged contract stated, focused
characterization tests passed, graph hash updated when needed, broad freeze
diff gate rerun after commit, and residual review-only drift risks recorded.
Contract changes still stop and require an explicit behavior-change proposal.

## Runtime Control-Surface Incident Reopening

KCS-14 has a bounded M4 closeout for the runtime control-surface incident
discovered after the historical final closeout. The historical closeout remains
evidence of the tested Python-visible contracts; it must not be rewritten as
though the incident was already known.

The incident's repeated semantic-scope fixes crossed the aggregate design
threshold and were classified as `architecture_error` inside the semantic
issue ownership boundary. The operator approved the replacement design, M0-M3
are complete, and M4 has a bounded closeout. The full incident plan and design
review remain in the retained historical branch
`feature/PAUX-7103-kcs-14.5-contract-consolidation`; the release tree keeps the
compact decision log, aggregate attempt review, forensic audit, and contract
consolidation closeout.

The proposal uses incident-local migration steps `M0` through `M4`; they do not
renumber the global KCS-14 slices. The retained legacy provider/evaluation
blocker is owned by `desktop_draft_workflow/provider boundary` with review-by
`2026-08-13`. It does not restore a Claude-visible legacy schema or authorize a
parallel workflow.

External Fable 5 architecture review on 2026-07-12 returned `approve with
changes`. Its pre-M0 specification blockers were incorporated into the
proposal: new-schema discoverability/corrections, explicit parser ownership,
mixed-worktree separation evidence, the M0-M2 operational suppression window,
and bounded re-proposal state. The operator subsequently approved the migration;
the review verdict alone did not authorize runtime implementation.

The bounded boundary re-proposal and the remaining accept/exclude boundary
lifecycle were retired during M4 simplification after real-ticket canaries
showed that they added latency and repeated ambiguity without improving the
final scope decision. Native candidate selection is now the only human scope
checkpoint. Deterministic evidence, provenance, and visibility blockers remain
fail-closed.

KCS-14.5 semantic stabilization is closed unsuccessfully. A reversible
rollback audit found no demonstrated working runtime target:

- the current M4 package reached native selection and accounted for five
  candidates, but produced zero reviewer-only drafts;
- the fixed KCS-14 closeout state `c51ca35` produced three semantic outcomes
  and zero reviewer-only drafts;
- the model/client changed between those runs, so they are not a strict
  quantitative A/B series, but the closeout baseline is still falsified as a
  known-good yield rollback target;
- the current M4 package was restored because it retains the smaller control
  surface and unchanged safety floor.

Do not continue this workstream with another merge/split prompt patch, semantic
schema generation, unchanged real-ticket canary series, or weaker mandatory
resolution validation. Reopening requires a separate behavior-change design
whose primary capability is obtaining or explicitly recording confirmed
resolution evidence before article drafting. Blocked evidence may support a
reviewer work item, but it must not be represented as an article draft or
KCS-ready content.

The completed explicit-reference recovery slice preserves an approved public
support-article reference through the
existing bounded evidence and reuse path. It adds no fetch, search, tool,
workflow state, or general resolution-validation bypass. The reviewed runtime
implementation, rebuilt install, and final synthetic installed canary are
complete. The canary reached the native `flag_existing` result with checked
reuse, duplicate prevention, no network calls, and no public output.

This recovery result does not reopen or reverse the unsuccessful KCS-14.5
semantic-stabilization verdict. It proves only the generic explicit-reference
reuse path; real-ticket semantic partition stability and candidates without
grounded resolution evidence remain unpromoted.

The final cross-attempt decision and no-loop rules are recorded in:

- `docs/internal/engineering-process/slice-plans/kcs-14-5-semantic-stabilization-aggregate-attempt-review.md`.

The compact decision index that must be checked before any further KCS-14.5
runtime change is:

- `docs/internal/engineering-process/slice-plans/kcs-14-5-decision-log.md`.

It consolidates retained, rejected, falsified, and provisional decisions
without replacing their detailed evidence records. A new change must name the
prior decision it preserves or supersedes, add a deterministic regression, and
define one installed canary stop condition.

The later flat claim-ownership canary passed one complete single-identity
scenario and failed its first two-identity scenario before candidate
projection. The active switch was reverted and the verified grouped package
was restored. This closes schema rearrangement as a recovery strategy: a future
semantic design must introduce a new authority source rather than another
model interpretation of the same bounded excerpts.

KCS-14.5 is closed. Its retained legacy provider/evaluation and semantic
control-surface boundary remains frozen. Reopening requires a separate
behavior-change design. Independently approved KCS-15 slices may proceed when
they leave that boundary and its safety contracts unchanged.

While the retained boundary remains frozen:

- do not commit new runtime incident candidates as refactor-only;
- do not mix runtime incident changes into the test-suite-maintainability
  branch;
- do not change incident control-surface code, tests, package guidance, or
  contracts from a KCS-15 style/markup slice;
- require a separate behavior-change design to reopen semantic ownership,
  provider, evaluation, or candidate-scope behavior;
- allow an explicitly approved KCS-15 slice only after its diff
  proves that the scoped incident surfaces remain untouched.

## Review Routing

Material documentation and process changes need review.

Material means a change to authoritative docs, contract wording, acceptance
criteria, ownership maps, process routing, data-handling rules, or review
requirements. Typo-only or formatting-only edits are not material.

Review verdicts for KCS-14 process and documentation slices should live under
`docs/internal/engineering-process/`. Core-pipeline review notes should be used
only when a KCS-14 slice touches core runtime boundaries.
