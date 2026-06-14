# KCS Core Pipeline Review Notes

Status: internal engineering review log

Purpose: record review outcomes, fixed blockers, accepted boundaries, deferred
follow-ups, and validation evidence for KCS core pipeline slices. This document
does not replace the roadmap and does not add active implementation scope.

Do not store raw review transcripts, raw diffs, ticket data, customer data,
private identifiers, or generated runtime artifacts here.

## Review Note Format

For each KCS slice, record:

- date;
- scope;
- reviewer;
- result: accepted, fixed before merge, or deferred;
- key findings;
- fixed in PR;
- deferred follow-ups;
- validation evidence.

## KCS-1 Contracts Review

Date: 2026-06

Scope: packet contracts, safe fixtures, JSON payload helpers, package/test
baseline.

Reviewer: Codex + local engineering review.

Result: fixed before merge.

Key findings:

- KCS-1 must remain contract-only and must not implement safety, decision,
  renderer, Zendesk, Claude, MCP, or search adapter behavior.
- Public packet objects require explicit schema versions.
- Output packets must preserve `auto_publish_allowed=false`.
- Fixtures must be synthetic or approved sanitized fixtures only.
- Python 3.11 must be used for local development and validation.

Fixed in PR:

- Added schema-versioned packet contracts and fixture contract tests.
- Added Python quality gates and local validation commands.
- Added explicit rejection coverage for unsafe explicit
  `auto_publish_allowed=true`.
- Corrected misleading module wording so contract modules are not described as
  test-only modules.

Deferred:

- Evidence extraction, sanitizer implementation, reuse/search adapters, and
  runtime handoff remain future slices.

Validation evidence:

- `python -m pytest tests/kcs_core -q`
- `python -m ruff check .`
- `git diff --check`

## KCS-2 Safety And Evidence Readiness Review

Date: 2026-06

Scope: `safety.py`, `validation.py`, value-free blockers/warnings, sanitized
evidence readiness gate.

Reviewer: Codex + local engineering review.

Result: fixed before merge.

Key findings:

- KCS-2 must answer whether sanitized evidence is safe and ready enough to
  continue into deterministic KCS decision.
- KCS-2 must not choose KCS actions, render article output, parse Claude output,
  read Zendesk, call search, generate HTML, or mutate packets.
- Safety and evidence validation outputs must be value-free and log-safe.
- GUI cleanup form is a temporary MVP sanitizer/preprocessor lane, not core
  sanitizer implementation.

Fixed in PR:

- Added input class, visibility, sanitizer status, source-ref, private
  identifier, and unsafe-text safety gates.
- Added evidence readiness blockers and warnings without raw evidence values.
- Added tests for unsafe input, missing evidence, multi-issue/non-atomic
  evidence, warnings that do not block, immutability, and package exports.
- Clarified documentation so KCS-2 is safety and sanitized evidence readiness
  only.

Deferred:

- KCS action decision validation belongs to KCS-3.
- Reviewer packet and Zendesk HTML validation belong to KCS-4.
- Ready-for-reviewer loop state belongs to KCS-5.
- Cleanup form implementation and evidence package building remain later slices.

Validation evidence:

- `python -m pytest tests/kcs_core -q`
- `python -m ruff check .`
- `git diff --check`

## KCS-3 Decision Review

Date: 2026-06

Scope: deterministic KCS action decision core, identity rules, split item
decisions, override metadata.

Reviewer: Codex + local engineering review.

Result: fixed before merge.

Key findings:

- KCS-3 must recommend deterministic KCS actions from accepted normalized
  evidence and structured reuse/search results.
- KCS-3 must not render articles, generate Zendesk HTML, write local bundles,
  call Claude, read/write Zendesk, or implement CLI handoff.
- Search uses symptoms; issue identity uses the cause-resolution pair for
  technical SCR and question-answer pair for how-to Q&A.
- Multi-issue evidence should return top-level `split_required` with per-item
  decision cards, not a dead-end blocker.
- Operator override metadata may describe future reviewer-only draft
  eligibility, but must not change the deterministic recommendation.

Fixed in PR:

- Added deterministic decision matrix for reuse/update/create/flag/no-article/
  split/blocked actions.
- Added split item cards for multi-issue evidence.
- Added same-identity public vs internal article behavior:
  public same-identity changes recommend `flag_existing`, internal/not-public
  changes recommend `update_existing`.
- Added value-safe serialization tests and non-empty evidence basis tests for
  create/update decisions.
- Adjusted internal-only/public-not-safe override behavior so reviewer-only
  override metadata can be allowed while public output remains unapproved.

Fixed in follow-up bugfix:

- Hardened KCS-3 identity matching for explicit GUI/CLI delivery variants:
  canonical identity keys are preferred when available, and explicit delivery
  labels do not create separate KCS identities.
- Added tests proving that technical SCR identity remains article type plus
  cause-resolution, and how-to Q&A identity remains question-answer.
- Added tests for public/published same-identity content changes
  (`flag_existing`) and internal/not-public same-identity content changes
  (`update_existing`).
- Confirmed KCS-3 chooses action and target only; updated reviewer packet or
  Zendesk HTML content remains KCS-4 renderer behavior.

Deferred:

- GUI path preference for final public wording, and whether CLI steps are
  included when missing or materially better, belongs to renderer/content
  generation slices rather than the KCS-3 decision core.
- `reuse_existing` selected metadata as a renderer/decision consistency
  requirement remains a future KCS-3/KCS-4 alignment check.
- Renderer artifacts, local bundle writing, CLI handoff, Claude handoff, and
  Zendesk integration remain later slices.
- Persisting operator override request/status in local artifacts belongs to a
  future bundle/output slice.

Validation evidence:

- `python -m pytest tests/kcs_core/test_decision.py -vv`
- `python -m pytest tests/kcs_core -q`
- `python -m ruff check .`
- `python -m mypy src/kcs_core tests/kcs_core` when available
- `git diff --check`

## KCS-4 Renderer Review

Date: 2026-06

Scope: reviewer packet renderer and Zendesk HTML copy/paste artifact.

Reviewer: Codex + external patch review.

Result: fixed before merge.

Key findings:

- KCS-4 canonical machine output is `KcsReviewerPacket` JSON.
- Zendesk HTML is a reviewer copy/paste artifact for create/update candidates
  and reviewer-required `flag_existing` artifacts.
- `reuse_existing`, `no_article`, `blocked`, and top-level `split_required`
  must not produce public article HTML.
- Renderer must fail closed if an upstream decision is inconsistent or unsafe
  for public output.
- Reviewer-only/internal notes and reuse target metadata must stay separated
  from public article HTML.

Fixed in PR:

- Article-output actions now require `decision_ready`, empty blockers,
  non-`none` article type, no top-level split items, and
  `auto_publish_allowed=false`.
- Public HTML now requires exact public-safe visibility and
  `public_solution_safe=true` on the selected candidate.
- `update_existing` and `flag_existing` require selected reuse metadata.
- `flag_existing` is marked as reviewer-required in renderer status/warnings.
- Selected reuse metadata is kept out of `public_article_candidate` and exposed
  only as sanitized validation/report metadata.
- Public article text is HTML-escaped and bounded.
- Renderer rejects unsafe/private metadata shapes, unsafe blocker strings, and
  unbounded metadata/code values without echoing the offending value.
- Renderer rejects unsafe/private values in public article candidate text before
  Zendesk HTML generation, including email/domain/IP/license/ticket/private-path
  and secret-like values.
- Renderer metadata validation now rejects non-string keys, unsafe/private key
  labels, numeric metadata values, non-finite float values, and secret-like
  hyphenated metadata values such as token/secret/API-key markers.
- JSON payload helpers now enforce strict JSON serialization and convert
  serialization failures to `ContractValidationError`.
- JSON payload helpers now recursively reject non-string object keys before
  serialization so Python's encoder cannot coerce unsafe keys.
- Added integration coverage for `decide_kcs_action()` followed by
  `render_reviewer_packet()`.

Deferred:

- `reuse_existing` selected metadata as a renderer requirement remains a future
  KCS-3/KCS-4 alignment check.
- Local review bundle writing, file paths, compact CLI/chat index, browser
  viewer, Claude handoff, Zendesk ingest, Zendesk writes, and Help Center
  publication remain out of KCS-4 scope.
- Post-pilot deployment and UX packaging are tracked separately as deferred
  planning notes.

Validation evidence:

- `.venv/bin/python -m pytest tests/kcs_core/test_renderer.py tests/kcs_core/test_json_payload.py -vv`
- `.venv/bin/python -m pytest tests/kcs_core -q`
- `.venv/bin/python -m ruff check src/kcs_core tests/kcs_core`
- `git diff --check`

Current validation result for the KCS-4 branch:

- renderer/json payload targeted tests: 67 passed;
- full KCS core tests: 177 passed;
- Ruff: all checks passed;
- diff whitespace check: passed.

## KCS-5 Validation Report And Loop State Review

Date: 2026-06

Scope: standalone validation report and ready-for-reviewer loop state.

Reviewer: Codex local engineering review and `gpt-5.3-codex-spark`.

Result: fixed before merge.

Key findings:

- KCS-5 must combine existing KCS-2 evidence validation, KCS-3 decision, and
  KCS-4 renderer outputs into a compact readiness report.
- KCS-5 must not implement CLI, local bundle writing, Claude handoff, Zendesk
  ingest, Zendesk writes, Help Center publication, or customer reply behavior.
- Report output must stay value-safe: blockers/warnings/checks are code-like,
  and hashes may identify generated reviewer artifacts without embedding full
  reviewer packet or Zendesk HTML bodies.
- Portable `plesk_support` reference is limited to the loop-report pattern:
  `ok`, readiness state, value-free blockers/warnings, required next step, and
  stable hashes.

Fixed in PR:

- Added standalone `kcs_validation_report_packet_v1`.
- Added deterministic readiness states: `ready_for_reviewer`, `blocked`,
  `draft_required`, and `review_blocked`.
- Added required-next-step codes for evidence fixes, reuse/search checks,
  renderer output generation, reviewer packet fixes, and split-item review.
- Added compact evidence, decision, and renderer summaries without raw evidence
  or full rendered article bodies.
- Added deterministic hashes for reviewer packet JSON and Zendesk HTML when
  present.
- Added report invariant checks so `ok` and `ready_for_reviewer` must match
  the `ready_for_reviewer` state.
- Added fail-closed handling for malformed renderer validation report code
  lists instead of silently dropping non-string blockers.
- Added focused tests for ready, blocked, draft-required, review-blocked,
  split-required, value-safe, malformed renderer report, no-mutation, and
  export paths.

Deferred:

- CLI entrypoint and compact run index belong to KCS-6.
- CLI summary/index should stay compact and must not print full reviewer
  packet bodies, full Zendesk HTML, raw ticket text, raw search snippets, or
  redaction maps.
- Local review bundle writer remains a future output slice. When implemented,
  it must persist operator override request/status metadata and keep public
  article artifacts separate from internal reviewer notes.
- Browser viewer remains a future UX slice. It should read approved packet
  JSON and must not bypass KCS-2/KCS-5 gates or introduce new raw-data display
  paths.
- Local review bundle writing, browser viewer, and override artifact
  persistence remain future output/bundle slices.
- Evidence package building and semantic extraction remain KCS-7+.
- Claude semantic extraction and Claude handoff remain later dedicated slices.
  Claude output remains untrusted and validators must rerun after any
  extraction or draft generation.
- Zendesk ingest/write integration remains out of KCS-5. Read-only ingest,
  writes, and Help Center publication require separate approved adapters and
  boundary tests.
- Operator override persistence on disk must record the override fact without
  replacing the original deterministic recommendation.
- New decision behaviors beyond the current action enum require a dedicated
  decision-scope change and tests; do not smuggle new action behavior into
  readiness, renderer, or bundle layers.
- Content style and link catalog improvements belong to renderer/content
  quality slices; they should not weaken deterministic safety or readiness
  gates.
- Centralized reusable safe-code and safe-metadata helpers across KCS-3,
  KCS-4, and KCS-5 remain a cleanup branch candidate. Until then, local helper
  behavior must stay covered by fail-closed regression tests.
- Future branches should classify reviewer findings as current-slice blocker,
  same-slice small fix, future pipeline risk, or architecture idea before
  implementing them.

Validation evidence:

- `.venv/bin/python -m pytest tests/kcs_core/test_readiness.py -vv`:
  17 passed.
- `.venv/bin/python -m pytest tests/kcs_core -q`: 204 passed.
- `.venv/bin/python -m ruff check src/kcs_core tests/kcs_core`: all checks
  passed.
- `git diff --check`: passed.

## KCS-7 Evidence Package Builder Review

Date: 2026-06

Scope: evidence package builder for approved/sanitized structured JSON input.

Reviewer: Codex local engineering review and external patch review.

Result: fixed before merge.

Key findings:

- KCS-7 must build `NormalizedTicketEvidencePacket` from approved/sanitized
  structured input only.
- KCS-7 must not process raw Zendesk tickets, call Claude/LLMs, perform
  semantic extraction from free text, run reuse/search, make KCS decisions,
  render reviewer packets, write local bundles, or use live Zendesk APIs.
- The builder boundary must reject unsupported fields, raw/private markers,
  nested raw numeric IDs, non-strict JSON values, unsafe candidate refs, and
  unsafe sanitizer report content without echoing offending values.
- `case_ref` must come from the function argument, not from export payload data.

Fixed in PR:

- Added `evidence_builder.py` and `sanitizer.py` for approved structured
  evidence export normalization.
- Added policy controls for `assume_sanitized` and
  `allow_internal_reviewer_only`, both fail-closed by default.
- Added allowlist checks for top-level export fields and issue candidate
  fields.
- Added strict JSON-shape validation for nested objects before packet
  construction: string keys only, finite numeric values only, and no non-JSON
  runtime objects.
- Added nested raw-ID detection for keys such as `requester_id`, `user_id`,
  `organization_id`, `external_id`, and generic `*_id` / `*-id` fields while
  preserving safe opaque `candidate_id`.
- Added explicit rejection for non-string `candidate_id` values instead of
  coercing booleans, nulls, or numbers into safe-looking strings.
- Added tests for approved export builds, approved sanitized samples,
  operator-sanitized summaries, single-candidate promotion, multi-issue
  preservation, downstream pipeline consumption, malformed schema, unknown
  fields, unsafe candidate/source-ref values, sanitizer failures, strict JSON
  violations, internal-only policy handling, and package-root exports.
- Updated README to reflect KCS-6 and KCS-7 implementation status.

Deferred:

- Consider adding a neutral public alias such as
  `build_evidence_packet_from_approved_export` if `zendesk_export` naming
  becomes misleading for non-Zendesk approved structured inputs. Keep current
  names stable unless a contract change is explicitly approved.
- Schema-specific validation for `environment`, `visibility_summary`, and
  `sanitizer_report` can be tightened in a follow-up branch if approved export
  schemas need stronger field-level contracts.
- The current builder intentionally allows small normalization conveniences,
  such as string-to-list handling in shared normalizers. If approved export
  schema strictness needs to match packet JSON exactly, add a follow-up branch
  to reject scalar list fields and null list elements explicitly.
- Centralize shared raw-boundary, safe-ref, safe-code, and safe-metadata
  helpers across KCS-3 through KCS-7 to reduce drift between `safety.py`,
  `cli.py`, `renderer.py`, `readiness.py`, and `sanitizer.py`.
- Public RAG/article metadata input, semantic extraction, cleanup-form
  continuation, Zendesk read-only ingest, Claude-assisted extraction, local
  bundle writing, browser viewer, operator override persistence, Zendesk
  writes, and Help Center publication remain future slices.

Validation evidence:

- `PYTHONPATH=src .venv/bin/python -m pytest tests/kcs_core/test_evidence_builder.py -vv`:
  33 passed.
- `PYTHONPATH=src .venv/bin/python -m pytest tests/kcs_core -q`:
  349 passed.
- `PYTHONPATH=src .venv/bin/python -m ruff check src/kcs_core tests/kcs_core`:
  all checks passed.
- `git diff --check`: passed.
