# KCS-14 Slice 9 Target 2: Semantic Review Fallback Audit

Status: design audit complete; narrow submit-validation extraction implemented.

## Scope

Graph node:

- `semantic_review_fallback`

Reviewed files:

- `src/kcs_adapters/desktop_semantic_review.py`
- `src/kcs_adapters/desktop_semantic_candidates.py`
- `src/kcs_adapters/desktop_semantic_providers.py`
- `src/kcs_core/semantic_extraction.py`

Related tests:

- `tests/kcs_adapters/test_desktop_semantic_candidates.py`
- `tests/kcs_adapters/test_approved_summary_semantic.py`
- `tests/kcs_core/test_semantic_extraction.py`
- `tests/kcs_adapters/test_mcp_desktop.py`

No runtime code was changed in this audit.

## Entry Question

Does semantic-review knowledge live in the right owner, or are schema,
source-ref, and blocker rules leaking between workflow, provider, and core
modules?

## Complexity Sensor

Command:

```bash
uv run python scripts/measure_complexity.py --paths src/kcs_adapters/desktop_semantic_review.py src/kcs_adapters/desktop_semantic_candidates.py src/kcs_adapters/desktop_semantic_providers.py src/kcs_core/semantic_extraction.py
```

Summary:

```text
files_scanned: 4
functions_total: 123
cc_average: 3.4
max_cc: 12
high_complexity_functions: 10
mi_average: 18.67
import_edges: 3
public_defs: 45
all_exports: 28
```

Top hotspots:

```text
src/kcs_core/semantic_extraction.py:462:_validate_eol_rules: cc=12
src/kcs_adapters/desktop_semantic_candidates.py:322:_applicable_to_from_environment: cc=9
src/kcs_adapters/desktop_semantic_providers.py:124:FixtureSemanticExtractionProvider: cc=9
src/kcs_adapters/desktop_semantic_review.py:765:_ensure_plain_string_submit_arrays: cc=9
src/kcs_adapters/desktop_semantic_review.py:832:_ensure_submit_environment_values: cc=9
src/kcs_core/semantic_extraction.py:571:_overall_visibility: cc=9
src/kcs_adapters/desktop_semantic_candidates.py:223:_attach_semantic_lists: cc=8
src/kcs_adapters/desktop_semantic_providers.py:127:FixtureSemanticExtractionProvider.propose_candidates: cc=8
src/kcs_core/semantic_extraction.py:231:CandidateSemanticExtraction.__post_init__: cc=8
src/kcs_core/semantic_extraction.py:493:_validate_product_relation_rules: cc=8
```

Interpretation:

- the node has real surface area but is not a raw cyclomatic-complexity
  hotspot;
- measured complexity is spread across schema validation, Desktop submit
  validation, fixture support, and Desktop conversion rules;
- source movement must be justified by ownership and information hiding, not
  by file size alone.

## Ownership Assessment

Current ownership is mostly coherent:

- `semantic_extraction.py` owns `candidate_semantic_extraction_v1`, semantic
  candidate dataclasses, enum rules, validation, provider-call validation, and
  normalized evidence export.
- `desktop_semantic_candidates.py` owns conversion from validated semantic
  items to Desktop candidate/outcome structures.
- `desktop_semantic_providers.py` owns explicit provider selection, approved
  summary provider routing, provider context safety, and fixture provider
  behavior.
- `desktop_semantic_review.py` owns pending semantic-review state, bounded
  excerpt selection, Claude-visible semantic-review packet shape, submit
  payload validation, source-ref coverage checks, and value-safe debug-code
  mapping.

The main design pressure is concentrated in `desktop_semantic_review.py`. It
currently hides the full controlled fallback from callers, but it also groups
several independent knowledge clusters in one file:

- packet shape and instruction text;
- pending review state;
- selected excerpt scoring and byte bounds;
- submit payload preflight and forbidden-value scanning;
- core semantic-extraction error-to-debug-code mapping;
- source-ref and excerpt coverage enforcement.

That grouping is safer than temporal decomposition by `prepare` / `submit` /
`continue`, but it is now dense enough that future changes can become hard to
review.

## Ousterhout Assessment

### Deep Modules

`semantic_extraction.py` is a deep module: callers get a small stable API for
validating and normalizing untrusted semantic extraction, while schema and enum
rules stay inside the module.

`desktop_semantic_review.py` is also deep from the caller perspective, but it
is becoming internally broad. Its public API is still reasonable:

- `new_pending_semantic_review()`;
- `prepared_pending_semantic_review()`;
- `semantic_review_packet()`;
- `selected_semantic_review_excerpts()`;
- `semantic_review_extraction_from_submission()`.

The problem is internal review cost, not caller-facing API size.

### Information Hiding

The important trust boundary remains hidden:

- provider output remains untrusted;
- Python validates candidate semantic extraction;
- unknown source refs, omitted selected excerpts, HTML/Markdown draft content,
  local paths, oversized payloads, invalid environment metadata, and broad item
  payloads are rejected before the workflow continues.

However, submit-validation knowledge is spread across many private helpers and
constant groups in `desktop_semantic_review.py`. That area has its own coherent
design decision: what a Claude semantic-review submission is allowed to contain
before core schema validation accepts it.

### Temporal Decomposition

Do not split this node by runtime phase:

- `prepare_semantic_review`;
- `submit_semantic_review`;
- `continue_after_semantic_review`.

That would leak semantic-review schema, allowed source-ref, and blocker rules
across multiple modules.

If code is split, it should be by ownership of knowledge. The strongest
candidate is submit validation, not workflow phase.

### Shallow Abstraction / Classitis Risk

Avoid extracting small classes such as `SemanticReviewPacketBuilder`,
`SemanticReviewSubmitValidator`, or `SemanticReviewDebugCodeMapper` unless they
hide a real stable interface.

A single private module for submit-validation helpers could reduce local
review cost without increasing the public surface. Multiple micro-modules would
likely create classitis and pass-through wrappers.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- no source files changed;
- focused tests cover Desktop candidate conversion, semantic extraction schema
  validation, approved-summary semantic extraction, and many frozen Desktop
  semantic-review prepare/submit paths;
- `tests/kcs_adapters/test_mcp_desktop.py` covers source refs, excerpt
  coverage, article draft rejection, structured resolution-step rejection,
  missing required fields, invalid article types, too many candidates, local
  path rejection, environment retry, safe placeholders, config text, HTML
  rejection, and oversized payloads.

Reviewed drift risks:

- submit debug codes must remain byte-for-byte stable from the operator's
  perspective;
- selected excerpt bounds and source refs must remain stable;
- packet schema, packet hash behavior, allowed source refs, and submit tool
  argument shape must remain stable;
- provider output must stay untrusted until Python validation;
- candidate conversion must not start making final KCS decisions.

Review-only drift risks:

- moving packet instruction text could accidentally change Claude-visible
  guidance and should be avoided unless KCS-15 explicitly scopes it;
- moving excerpt selection could change which selected excerpts are sent to the
  semantic review surface;
- moving submit validation could preserve tests while making debug-code
  ownership less obvious unless the new module has one narrow purpose.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Decision

Keep `semantic_extraction.py`, `desktop_semantic_candidates.py`, and
`desktop_semantic_providers.py` unchanged in this Slice 9 target.

Reason:

- their current boundaries are ownership-based;
- related tests are focused and meaningful;
- measured complexity is acceptable for the contract density;
- extracting fixture/provider or candidate-conversion details would add
  interfaces without reducing what callers need to know.

Opened and implemented one narrow source-refactor candidate:

- extract submit-validation implementation details from
  `desktop_semantic_review.py` into a private adapter module, while preserving
  the existing public API and all debug-code behavior.

Candidate owner:

- `desktop_semantic_review_submission.py`

Candidate contents:

- forbidden submit key/value scanning;
- plain-string array enforcement;
- submit payload and text byte bounds;
- submit environment allow-list enforcement;
- candidate-count limit;
- source-ref subset and excerpt coverage checks;
- core semantic-extraction error-to-debug-code mapping.

Do not move:

- `PendingSemanticReview`;
- `new_pending_semantic_review()`;
- `prepared_pending_semantic_review()`;
- `semantic_review_packet()`;
- selected excerpt selection/scoring;
- public `semantic_review_extraction_from_submission()` API.

The extraction is private to the adapter package and imported only by
`desktop_semantic_review.py`. A private compatibility shim remains in
`desktop_semantic_review.py` for frozen characterization tests that import the
old helper path.

## Required Source-Refactor Drift Mapping

The source batch explicitly maps:

```text
old _ensure_bounded_submit_payload
  -> new submit-validation helper
  -> same semantic_review_submission_invalid / semantic_review_submission_too_large behavior

old _ensure_plain_string_submit_arrays
  -> new submit-validation helper
  -> same semantic_review_plain_string_arrays_required behavior

old _ensure_no_forbidden_submit_values / mapping / string helpers
  -> new submit-validation helpers
  -> same forbidden_field, forbidden_html_or_markdown, local_ref_blocked behavior

old _semantic_extraction_shape_debug_code and item/top-level helpers
  -> new submit-validation helpers
  -> same debug-code mapping

old _ensure_submit_environment_values
  -> new submit-validation helper
  -> same environment allow-list behavior and retry path

old source-ref / excerpt-coverage helpers
  -> new submit-validation helpers
  -> same source_refs_invalid and excerpt_coverage_incomplete behavior
```

Every new helper must map back to one of those old behavior elements. New
behavior in this source batch is a blocker.

## Required Tests If Source Batch Opens

Minimum focused validation:

```bash
uv run pytest tests/kcs_adapters/test_desktop_semantic_candidates.py tests/kcs_core/test_semantic_extraction.py tests/kcs_adapters/test_approved_summary_semantic.py -q
uv run pytest tests/kcs_adapters/test_mcp_desktop.py -q
uv run pytest tests/policy -q
git diff --check
```

`tests/kcs_adapters/test_mcp_desktop.py` is frozen characterization coverage.
Do not edit its assertions in the same source-refactor batch.

Actual validation:

```text
uv run ruff check src/kcs_adapters/desktop_semantic_review.py src/kcs_adapters/desktop_semantic_review_submission.py
uv run pytest tests/kcs_adapters/test_mcp_desktop.py -q
uv run pytest tests/kcs_adapters/test_desktop_semantic_candidates.py tests/kcs_core/test_semantic_extraction.py tests/kcs_adapters/test_approved_summary_semantic.py -q
uv run pytest tests/policy/test_code_review_graph_policy.py -q
```

The broader freeze-path policy test remains a commit-boundary caveat for this
batch because `desktop_semantic_review.py` is a frozen contract path. The diff
does not change the contract, and the frozen Desktop characterization suite
passed without assertion edits.

## Parked Follow-Ups

Only reopen broader semantic-review design if one of these triggers appears:

- KCS-15 requires repeated changes to packet instruction text;
- submit-validation debug-code rules change in more than one feature slice;
- selected excerpt coverage becomes a feature surface;
- provider output starts needing additional trust-boundary checks;
- aggregate review records repeated `semantic_review_fallback` ownership
  conflicts.

Possible future narrow questions:

- Should packet instruction text become data to make KCS-15 style/markup
  changes easier to review?
- Should selected excerpt selection become its own owner if excerpt coverage
  behavior changes?
- Should provider fixture behavior move closer to tests if fixture-only
  branches continue to grow?

None of these should be opened now without behavior examples.

## Promotion And Demotion Candidates

- Promotion candidates: none.
- Demotion candidates: none.

## Next Decision

The next Slice 9 step should be one of:

1. run staged-diff review for this source-refactor batch;
2. commit the Target 2 checkpoint if review is clean;
3. proceed to `reviewer_bundle_output`.
