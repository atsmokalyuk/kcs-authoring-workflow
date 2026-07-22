# KCS-15.0 Authoritative Style-Parity Baseline

Status: approved documentation/evidence slice; runtime implementation is not
approved by this plan.

## Requested outcome

Give KCS-15 a stable, reviewable requirements baseline so the operator can see
which style, markup, article-quality, example, and operator-practice rules are
already implemented, which conflict, and which need a later decision.

The requested outcome is not a renderer rewrite, a new workflow stage, or RAG
integration. Those are possible later solutions and need separate approval.

## Operational baseline

- Base commit: `4acb0b320b692a281abfe56b5e27f61d8f3d` (merged KCS-14.5 baseline).
- KCS-14.5 retains an M4 blocker. While it is active, KCS-15 runtime
  implementation is forbidden; planning/evidence work must not modify incident
  contracts or artifacts.
- The current core renders reviewer-only SCR and Q&A Zendesk HTML.
- The current quality adapter deterministically checks structure, safety,
  public-data leakage, selected language rules, GUI paths, and known markup.
- The current markup registry has 14 patterns.
- Unit/functional tests establish nominal behavior. They do not establish full
  parity with the newly supplied canonical sources or stable operator outcomes.
- Authenticated Confluence pages are not directly readable in this agent
  environment. Operator-supplied exports provide the snapshot evidence; their
  canonical URLs remain the source of truth.

## Target operator experience

The operator can open one tracked source index and one parity matrix to answer:

1. Which canonical source owns this rule?
2. Is the rule confirmed, provisional, unknown, or rejected?
3. What does the current runtime do?
4. Is there a conflict or behavior gap?
5. Which deterministic, bounded-model-trial, or named-human-review gate would
   approve a change?

No end-user or Desktop workflow changes in this slice.

## Proposed solution

- Track URL-backed Markdown snapshots for the supplied source documents.
- Track SHA-256 and capture provenance without committing downloaded binaries,
  screenshots, or local paths.
- Record explicit source precedence and refresh rules.
- Keep operator-owned KCS practices as a high-authority inventory with per-rule
  evidence status.
- Record the slide deck as supporting example evidence, including the current
  AQ rule that supersedes its historical script-attachment advice.
- Map the full source inventory to current runtime behavior and future gates.
- Add a narrow policy test for source-pack completeness and binary exclusion.

This uses the existing spec-first and feature-engineering workflow. It does not
create another process/workflow layer.

## In scope

- canonical URL/source inventory;
- Markdown snapshots of six supplied document/text sources;
- Markdown summary of the supplied 19-slide example deck;
- source authority/precedence and refresh policy;
- operator-practice inventory;
- style/markup/article-quality parity matrix;
- explicit RAG placement finding;
- acceptance-to-gate mapping and deterministic policy test.

## Out of scope

- changes under `src/`, `evals/`, runtime fixtures, schemas, or adapters;
- changes to KCS-14.5 incident decisions/artifacts;
- RAG adapter implementation or data access;
- model calls or model-quality claims;
- selection/approval of public golden articles;
- optional operator-confirmed drafting scopes UX;
- Zendesk read/write or publication behavior;
- branch push, merge, deployment, or release claims.

## Source authority

The authority model and canonical URLs live in
`docs/internal/kcs-sources/README.md`.

Key decisions:

- URLs are source of truth; snapshots are review aids.
- Plesk-specific rules win over broader WebPros rules for Plesk output.
- AQ criteria outrank simplification/polish guidance.
- Operator practices are high authority, but imported candidates remain
  provisional until the operator approves them or a canonical source confirms
  them.
- Repository privacy/security/data contracts remain mandatory.

## Acceptance-to-gate mapping

| Acceptance criterion | Gate | Evidence |
| --- | --- | --- |
| Every operator-approved canonical URL is present in the source index and the corresponding snapshot. | deterministic | policy test checks URL literals and files |
| Every supplied export snapshot records capture date, export filename, SHA-256, and non-authoritative status. | deterministic | policy test checks metadata fields/hash format |
| No `.doc`, `.docx`, `.ppt`, `.pptx`, downloaded image, or local Downloads path is tracked in the source pack. | deterministic | policy test scans suffixes/content; Git diff review |
| Plesk/WebPros precedence, AQ-over-simplification, operator authority, and URL-over-snapshot rules are explicit. | deterministic | required statements in source index/operator practice file |
| The parity matrix uses only confirmed/provisional/unknown/rejected evidence states and one of the three approved gate classes. | deterministic | policy test plus document review |
| Current baseline, known drift, full feature inventory, dependencies, RAG placement, and slice ordering are recorded. | named-human-review: technical lead/operator | review this plan and parity matrix |
| The slide deck is treated as supporting/beta evidence and its obsolete script-attachment instruction is marked superseded. | deterministic | required deck-summary statements |
| No runtime behavior or public/reviewer contract changes. | deterministic | `git diff --name-only` allowlist and existing policy test suite |
| No model quality/stability claim is made. | deterministic | no model run; closeout review |

No bounded model trial is appropriate for this documentation-only slice.

## Full unknown inventory

- Cause optionality for a Plesk technical SCR when the supported workaround is
  known but root cause is not.
- Whether ordered-list Symptoms are canonical or a local renderer convention.
- Acceptable conditional/branching exceptions.
- Canonical emitted tabs/accordion markup versus accepted legacy input.
- Exact use cases for `unselectable` and horizontal separators.
- Controlled tag taxonomy and its owner.
- Initial operator-approved public golden example set and permitted uses.
- Whether security-alert article type is needed by this product.
- Which operator-practice candidates become individually confirmed.
- Exact local RAG integration slice boundary, data source configuration,
  freshness/readiness evidence, and identity-review UX.
- Whether optional drafting-scope confirmation reduces or increases operator
  cognitive load in the actual Desktop entrypoint.

These unknowns are retained here but should be asked in small decision batches
only when they block the next approved slice.

## Dependencies and blockers

- Runtime KCS-15 work remains blocked by the retained KCS-14.5 M4 rule.
- The first deterministic parity correction requires operator approval of a
  separate behavior slice.
- Cause/Symptoms/branching behavior changes require the corresponding operator
  decisions before implementation.
- Model-mediated quality requires approved golden fixtures and a bounded trial
  contract before architecture or prompting changes.
- RAG does not block style parity. It needs its own adapter/data/security/
  readiness decision before integration and should precede reuse-aware model
  evaluation.

## Behavior-drift check

Changed behavior: none.

Stable contracts:

- core packet schemas and decisions;
- reviewer packet and Zendesk HTML behavior;
- Desktop/MCP entrypoints and output boundaries;
- persistence and bundle layout;
- privacy/data-handling gates;
- no-write/no-publish boundary;
- KCS-14.5 incident decisions and artifacts.

Review-only drift risks:

- a snapshot can become stale while the canonical page changes;
- a normalized text snapshot omits source images and formatting details;
- the source hierarchy can be misread as silently resolving a rule conflict;
- the parity matrix can be mistaken for runtime approval.

The source index, metadata, conflict labels, and explicit runtime gate mitigate
these risks.

## Next recommended slice

After the M4 gate and explicit operator approval, the smallest behavior slice
is deterministic Plesk trigger parity:

1. correct `PLESK_INFO` semantics against source fixtures;
2. add compact fixtures for missing source-backed trigger cases;
3. preserve all packet, reviewer, Desktop, persistence, and publish contracts;
4. stop before broader article semantics, RAG, model trials, or drafting-scope
   UX.

This slice removes one confirmed false blocker and gives the operator immediate
markup-review value with a small, deterministic change surface.
