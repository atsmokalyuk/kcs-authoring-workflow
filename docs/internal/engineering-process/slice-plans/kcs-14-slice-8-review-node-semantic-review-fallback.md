# KCS-14 Slice 8 Review Node: Semantic Review Fallback

## Status

Review-only complete.

## Scope

Graph node:

- `semantic_review_fallback`

Reviewed files:

- `src/kcs_adapters/desktop_semantic_review.py`
- `src/kcs_adapters/desktop_semantic_candidates.py`
- `src/kcs_adapters/desktop_semantic_providers.py`
- `src/kcs_core/semantic_extraction.py`

Related frozen characterization coverage:

- `tests/kcs_adapters/test_mcp_desktop.py`

No runtime code was changed.

## Ownership Assessment

The node owns the controlled semantic-review fallback:

- bounded semantic-review packet and pending state;
- selected excerpt refs;
- `candidate_semantic_extraction_v1` submit validation;
- provider boundary for untrusted semantic candidate proposals;
- conversion from validated semantic candidates into Desktop draft candidates.

The current split is acceptable:

- `desktop_semantic_review.py` owns pending semantic-review state, packet
  preparation, submit-shape validation, forbidden submit values, source-ref
  checks, excerpt coverage, and bounded payload limits.
- `semantic_extraction.py` owns the core candidate extraction schema and typed
  value validation.
- `desktop_semantic_candidates.py` owns conversion from validated semantic
  items into Desktop candidate records.
- `desktop_semantic_providers.py` owns provider selection and the safe provider
  boundary.

This is an ownership split by semantic-review contract, schema, provider
boundary, and Desktop candidate conversion. It should not be split by workflow
time steps.

## Must Not Own

This node must not own:

- drafted article bodies;
- final KCS action decisions;
- reviewer bundle writing;
- provider trust.

The reviewed files preserve that separation.

## Ousterhout Lens

- Information hiding: `desktop_semantic_review.py` is intentionally deep; it
  keeps prepare/submit/source-ref/forbidden-value rules together so callers do
  not need to know the semantic-review submit contract.
- Deep modules: the public surface is small relative to the validation rules it
  hides.
- Temporal decomposition risk: splitting the file into prepare/submit/continue
  modules would likely leak `candidate_semantic_extraction_v1`, source-ref, and
  blocker knowledge across files.
- Change amplification: submit validation changes require broad safety and
  Desktop characterization tests, so small helper movement has poor payoff.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- no source files changed in this review
- related tests cover core semantic extraction, Desktop semantic candidates,
  approved-summary semantic extraction, and frozen Desktop semantic-review
  characterization

Reviewed drift risks:

- Claude/provider output remains untrusted until Python validation.
- selected excerpts stay bounded.
- unknown source refs are rejected.
- article HTML, Markdown drafts, forbidden fields, local paths, and oversized
  submit payloads remain blocked.
- provider selection remains explicit and safe by default.

Review-only drift risks:

- `desktop_semantic_review.py` is large, but its size is currently tied to a
  cohesive trust-boundary contract. Any split needs a narrower design question
  and must prove it reduces caller knowledge without scattering validation
  rules.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Refactor Decision

Do not refactor this node now.

Future refactor should require a narrow ownership question, such as:

- Can submit-shape validation be made clearer without separating it from
  source-ref and forbidden-value validation?
- Should provider selection remain in the Desktop adapter or move behind a
  smaller provider registry boundary?

Neither question is urgent without repeated review friction or validation
failures.

## Promotion And Demotion Candidates

- Promotion candidates: none.
- Demotion candidates: none.

## Next Recommended Node

Review `packet_validation_decision`.
