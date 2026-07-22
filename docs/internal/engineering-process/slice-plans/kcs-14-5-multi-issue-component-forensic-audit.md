# KCS-14.5 Multi-Issue Component Forensic Audit

Date: 2026-07-18

Status: evidence-only localization complete; atomic preservation and
model-neutral role ownership implemented; first installed runtime canary
localized a per-issue versus packet-terminal control-flow defect

## Purpose

Decompose the restored grouped `/draft` workflow into independently testable
boundaries and identify the first boundary that corrupts a complete
multi-issue input.

This audit changes no runtime, prompt, schema, validator, selector, workflow
state, tool surface, provider, persistence, renderer, or Langfuse behavior.
It uses only generic synthetic facts and value-safe structural results.

## Compared Inputs

The control case contains one complete technical identity. The multi-issue
case contains two independent identities with these symbolic facts:

```text
S1 -> C1 -> R1 -> V1
S2 -> C2 -> R2 -> V2
```

Every symptom, cause, resolution, and verification fact exists in the source.
The same two-issue semantics were measured with paragraph-grouped,
line-per-claim, blank-line-per-claim, fully flattened, explicit-label, and
recognized speaker-turn representations.

## Component Results

| Boundary | Evidence | Verdict |
| --- | --- | --- |
| Clean-ticket registration | Internal order and line breaks survive; only outer whitespace is removed. | Not the corrupting boundary. |
| Transcript segmentation | Equivalent semantics produce between one and ten segments depending on formatting. Paragraph grouping combines both identities by semantic field; fully flattened prose remains one segment without recognized turn markers. | Earliest structural divergence: representation-sensitive and not identity-atomic. |
| Excerpt selection | Equivalent semantics produce one, four, or seven excerpts. Some representations silently omit a required resolution even though the global twelve-excerpt cap is not reached. | First proven silent evidence loss. |
| Primary role assignment | Imperative steps are omitted or classified as symptom, fact, or question; the word `issue` triggers symptom classification; `check` inside a command triggers question classification. | First proven formal-role corruption. |
| Role index | When the primary role is already an issue role, it becomes the only indexed role even if the text serves another semantic function. The restored grouped projection does not enforce field-to-role compatibility; the rejected flat projector did. | Preserves the selector error and can mislead the model. |
| Model-visible grouped contract | The model still owns issue count, boundaries, source allocation, field classification, cause-resolution pairing, summaries, refs, and coverage proposals. | Cannot be evaluated fairly until the prepared packet is adequate. |
| Static correction | One correction is available only for selected mapped observation-shape, ref, count, packet-coverage, or coverage-enum errors. Generic proposal-shape errors remain terminal, while some field/role semantic misassignments are not detected by grouped validation at all. | Safe and bounded, but not recovery for this defect. |
| Python grouped validation | Validates packet shape, refs, packet-wide coverage, bounds, and safety. It does not validate each observation field against the cited excerpt role. | Rejects malformed packets; permissive for some semantic misassignments. |
| Python projection and workflow | Projection checks per-issue role presence, visibility, provenance, article shape, and required technical cause/resolution. Two complete independent valid issues produce two candidates in either order, with no blocked or unassigned evidence. If any schema-valid sibling is blocked during projection, the whole submit terminates before valid siblings reach selection. | Does not merge or silently drop issues; does not support partial selection after a sibling blocker. |
| Native selection and batch | Accepted projected issues reach native selection; order follows the submitted issue order. | Deterministic for a fixed accepted proposal. |
| Draft and reviewer bundle | The restored single-issue smoke generated one reviewer-only draft. | Downstream path is operational for complete evidence. |
| Safety and publication | Network and public output remain disabled. | Unchanged and working. |

## Exact Structural Comparison

| Representation | Segments | Excerpts | Structural outcome |
| --- | ---: | ---: | --- |
| Successful labeled single issue | 5 | 4 | S, C, and R correct; V classified as question; model still produced one complete issue. |
| Exact two-issue canary paragraphs | 6 | 4 | `[S1+S2]` symptom, `[C1+C2]` cause, `[R1+R2]` symptom, `[V1+V2]` question. |
| One claim per line | 10 | 7 | R2 omitted; S1 fact; R1 symptom; V1 question; V2 symptom. |
| Blank line between claims | 10 | 7 | Same result as one claim per line. |
| Fully flattened | 1 | 1 | All facts share one question excerpt. |
| Explicit S/C/R labels | 9 | 7 | S1/S2, C1/C2, and R1/R2 correct; V2 omitted. |
| Recognized customer/support turns | 8 | 7 | Speaker metadata correct; S2 omitted; resolution and verification roles still wrong. |

The exact failed two-issue flat canary returned:

- three `claim_source_role_incompatible` outcomes;
- two `claim_root_incomplete` outcomes.

The prepared structure is sufficient and count-consistent with that outcome:
two resolution claims could cite the shared symptom-role excerpt and one
verification claim could cite the shared question-role excerpt. Removing those
claims would leave both cause roots without a valid resolution. The exact
rejected submit payload was not retained, so the claim-to-excerpt mapping and
the semantic quality of the remaining proposal are not asserted as facts.

## Controlled Lexical Sensitivity Probe

The isolated probe used one recognized symptom segment, one recognized cause
segment, and one `ACTION_MARKER` segment. Within that controlled context,
equivalent executable resolution phrasing produced:

| Phrasing class | Selector outcome |
| --- | --- |
| imperative `run` | omitted |
| imperative `execute` | omitted |
| imperative `restart` | confirmed fact |
| imperative `enable` | customer question |
| `fixed by` | supported resolution |
| past-tense `restarted` | supported resolution |
| explicit `Resolution:` | supported resolution |
| explicit `Workaround:` | supported resolution |

The current tests use recognized speaker headers and keyword-rich phrases such
as `reports ... fails`, `confirmed root cause`, `fixed`, `resolved`, and
`restarted`. They prove behavior for the selector's vocabulary, not the
invariant that complete executable resolution evidence survives ordinary
paraphrasing and formatting.

## Hypothesis Ranking

### H1 — Pre-Model Packet Corruption

Confidence: high.

Segmentation and lexical role assignment alter evidence cardinality,
atomicity, and formal roles before the model call. This is directly reproduced
without a provider.

### H2 — Shared Coarse Refs Destabilize Identity

Confidence: high.

In the exact two-issue canary, every selected source ref spans both identities.
The model can reuse the same ref across grouped issues, but the refs no longer
provide independent identity evidence.

### H3 — Model-Owned Grouping Adds Residual Drift

Confidence: medium, not yet isolated.

The model still performs the semantic partition. Previous unchanged-package
runs produced different accepted partitions. Earlier M3 synthetic series also
show that the grouped model path can be stable on curated structured evidence.
What remains unisolated is model grouping on adequate, format-varied,
real-ticket-like multi-issue input after selector defects are removed.

### H4 — Python Projection Loses Valid Issues

Confidence: rejected.

Conditional on an already valid accepted proposal, direct and full MCP probes
preserve two independent issues in either order. Schema-valid issues that fail
projection are ledgered and terminate the whole submission explicitly rather
than being silently dropped; schema, ref, or packet-coverage errors terminate
before a projection ledger exists.

### H5 — Speaker Attribution Is the Primary Cause

Confidence: low.

Recognized speaker markers correct `speaker_kind` but do not correct evidence
loss or primary semantic roles. Speaker metadata is visible to the model but is
not used by deterministic role assignment or projection.

### H6 — Excerpt Cap or Absent Raw Source Evidence Causes the Failure

Confidence: rejected for the synthetic case.

All eight facts exist in the raw source before selection, and failure occurs
with only four to seven of twelve allowed excerpts. Selection can still make
required evidence absent from the model-visible packet; that is part of H1.

## Proposed First Falsification Gate

Before any model call or selector fix, define a synthetic atomic-input adequacy
probe:

```text
registered clean text
-> segments
-> selected excerpts
-> formal role index
```

For the two independent identities, require:

1. S1, S2, C1, C2, R1, R2, V1, and V2 are all retained;
2. every fact occurs exactly once;
3. every fact has an atomically referenceable excerpt;
4. no required identity can be represented only by an excerpt shared with the
   other identity;
5. symptoms are admissible as reported symptoms;
6. causes are admissible as supported causes;
7. resolutions are admissible as supported resolutions;
8. verification is admissible as supported resolution or confirmed fact;
9. any omission is explicit in a bounded omission ledger;
10. paragraph, line-per-claim, flattened, and recognized-turn representations
    satisfy the same semantic inventory invariants.

The symbolic S/C/R/V inventory is a test-author oracle for controlled synthetic
inputs, not new runtime semantic authority over arbitrary prose. The proposed
omission ledger and representation-invariance requirements are hypotheses
requiring approval; this gate does not authorize another lexical runtime
classifier. The current selector fails the proposed gate before the model call.

### Executable Diagnostic Checkpoint

The approved measurement step is now executable in:

```text
tests/kcs_adapters/test_semantic_review_input_adequacy.py
```

The test contains one curated keyword control and separately measures atomic
inventory preservation and model-neutral evidence roles across five
representations of the same ordinary two-issue semantic inventory. Before the
role-ownership slice, normal pytest kept the known debt visible as:

```text
11 passed, 5 xfailed
```

The explicit diagnostic command exposed the five lexical-role failures as:

```text
uv run pytest tests/kcs_adapters/test_semantic_review_input_adequacy.py \
  --runxfail -q --tb=short
```

Pre-change result:

```text
5 failed, 11 passed
```

Those failure classes were:

- all five representations fail formal-role admissibility;
- line-per-claim, blank-line-per-claim, and recognized-turn resolution evidence
  receives an incompatible formal role;
- paragraph-grouped and fully flattened evidence now preserve atomic refs but
  still assign incompatible roles to ordinary resolution phrasing.

After the model-neutral role slice, the same file reports:

```text
16 passed
```

All five representations retain the same atomic inventory while ordinary
model-visible refs use `unclassified_evidence`. The lexical selector still
ranks the bounded inventory internally; it no longer asserts free-prose
semantic roles to the model or grouped projector.

### Isolated Strategy Falsification

Three preparation strategies were prototyped outside tracked runtime code and
measured against the same eight-fact oracle plus three negative diagnostic
actions that must not become supported resolutions.

| Strategy | Atomic inventory across five representations | Expected roles | Negative resolution false positives | Verdict |
| --- | --- | --- | ---: | --- |
| Pre-change current selector | Three of five representations are atomic | Six of eight ordinary facts in four representations; zero of eight when flattened | 0/3 | Baseline defect. |
| Preserve every sentence atom, keep current roles | Eight of eight facts in all five representations | Six of eight in every representation | 0/3 | Necessary representation fix; not a role fix. |
| Atomic preservation plus a narrow completed-action regex | Eight of eight facts in all five representations | Eight of eight in every representation | 2/3 | Rejected: positive success is bought with false resolution authority. |
| Atomic preservation plus broad speaker-side roles | Eight of eight facts in all five representations | Eight of eight in every representation, but all eight atoms become multi-role ambiguous | 3/3 | Rejected: role validation becomes non-discriminating. |

The comparison separates two defects:

1. representation-sensitive segmentation and selection;
2. semantic-role ownership and admissibility.

The smallest supported next implementation candidate is bounded atomic evidence
preservation only. It must retain the existing byte/excerpt limits, safety
checks, source ordering, and reviewer-only visibility. It must not claim to
solve role semantics or add an imperative/action regex.

The role problem remains a separate architecture decision. No tested lexical
or broad-role variant satisfied both the positive role oracle and the negative
resolution controls. The exploratory prototypes are not tracked runtime
components.

#### Value-Safe Reproduction Definition

The exploratory comparison used the same tracked eight-fact synthetic
inventory and five representation builders as
`test_semantic_review_input_adequacy.py`.

The atomic prototype:

1. normalized line breaks to spaces;
2. split after `.`, `?`, or `!` followed by whitespace;
3. retained every non-empty sentence as one ordered atom;
4. classified each atom independently with the current selector;
5. used `confirmed_fact` only when the current selector did not select the
   atom.

The narrow completed-action prototype then replaced the atom role with
`supported_resolution` when this exact case-insensitive pattern matched:

```text
\bSupport ran\b.*\bto (?:activate|enable|restart|restore)\b
```

The broad speaker-side prototype assigned:

- `reported_symptom` plus `confirmed_fact` to atoms containing
  `Customer reports`;
- `supported_cause`, `supported_resolution`, and `confirmed_fact` to atoms
  containing `Support`.

This makes both customer atoms and all six support atoms multi-role, for eight
ambiguous atoms in total.

The three negative controls were:

```text
Support ran D1 to check dependency alpha status.
Support ran D2 to activate temporary trace logging.
Support ran D3 to restore diagnostic visibility.
```

A false positive was counted when the resulting role list for one of these
three atoms contained `supported_resolution`. The measured false-positive
counts were:

```text
current selector: 0
atomic plus current roles: 0
atomic plus completed-action regex: 2
atomic plus broad speaker-side roles: 3
```

These prototypes measure strategy behavior only. They do not define a safe
production sentence splitter: a runtime implementation still needs explicit
byte/excerpt bounds and must preserve commands, URLs, ordering, provenance,
and safety behavior.

### Atomic Preservation Runtime Slice

Goal:

- make already bounded semantic-review preparation representation-tolerant by
  exposing independently referenceable sentence atoms before ranking.

Allowed behavior change:

- split each existing transcript segment at the repository's existing
  whitespace-delimited sentence boundary;
- preserve the source order of the resulting atoms;
- inherit the parent segment's `speaker_kind` for every child atom;
- continue to apply the existing excerpt-count, byte, sanitizer, selection,
  deduplication, and reviewer-only visibility rules.

Forbidden behavior change:

- no new semantic-role regex or action classifier;
- no prompt, provider, proposal, projection, operator, draft, publication, or
  Langfuse change;
- no strict `Symptoms` / `Cause` / `Resolution` input requirement;
- no claim that formal-role admissibility is fixed.

Acceptance:

1. paragraph-grouped and fully flattened two-issue evidence becomes
   identity-atomic;
2. line-per-claim, blank-line-per-claim, and recognized-turn preservation
   remains green;
3. child atoms retain source order;
4. multiple atoms split from one recognized speaker turn retain that speaker;
5. punctuation inside inline quoted commands and inline backtick spans does
   not split evidence;
6. child atoms in two-section and three-section explicit labeled input inherit
   their section's existing formal role;
7. unsafe evidence does not consume the bounded selection quota before the
   existing sanitizer rejects it;
8. a late allowlisted public support resolution reference retains its existing
   reserved priority before the excerpt-count cap;
9. the five role-admissibility scenarios remain tracked separately as known
   debt;
10. all existing bounds, privacy, safety, tool-surface, and publication checks
   remain green.

Implementation result:

- `_segment_records()` now exposes sentence atoms before the existing
  selector ranks them;
- child atoms inherit the parent `speaker_kind` and remain in source order;
- inline quoted shell/Python fragments stay intact through the real selector
  path;
- child atoms in existing explicit sections inherit the section role without
  changing the role regexes, including input with exactly two sections;
- unsafe segments are removed before applying the existing excerpt-count cap,
  so rejected evidence does not reduce the usable bounded packet;
- the existing allowlisted public support resolution reference remains
  reserved before the excerpt-count cap, including when it appears after more
  than twelve labeled atoms;
- paragraph-grouped and fully flattened preservation scenarios are green;
- the characterization that previously required one multi-role fact excerpt
  now requires six atomic S/C/R refs for two projected issues;
- role regexes, role-index rules, packet schemas, provider/model contracts,
  Python projection, operator workflow, and publication behavior are
  unchanged.

Frozen-path protocol:

- behavior change intended: yes, limited to pre-model evidence atomicity;
- touched frozen path:
  `src/kcs_adapters/desktop_semantic_review.py`;
- affected graph node: `semantic_review_fallback`;
- graph file hash updated;
- the pre-commit frozen-path dirty check is expected to remain red until the
  reviewed implementation commit and must be rerun after commit;
- residual review risk: punctuation-based sentence boundaries can split
  abbreviations or multi-sentence context differently outside protected quoted
  spans, while the existing excerpt and byte caps can still omit evidence from
  larger tickets;
- multiline fenced blocks are still segmented by the existing line/chunk
  preparation before atomization and are not covered by this inline-code
  preservation contract.

### Pre-Slice Free-Prose Role Assignment Component Audit

Before the model-neutral role slice, the runtime had three different uses of
the excerpt role index:

1. preparation assigns one primary role with explicit-label rules or lexical
   regex scoring;
2. the model receives that role as part of the bounded excerpt;
3. grouped Python projection requires at least one issue role in the union of
   an issue's refs, but does not validate each observation field against the
   cited ref's role.

The inactive flat-claim projector differs at step 3: it validates every claim
kind against the cited source role. This difference explains why a grouped
per-field mismatch can pass when another cited ref supplies an issue role,
while the same mismatch deterministically blocks a flat claim. Grouped
projection still blocks when the issue-wide role union contains no issue role.

A value-safe synthetic probe used one complete technical issue with symptom,
cause, and resolution refs and compared only the immutable role index:

| Projection path | Resolution ref role | Result |
| --- | --- | --- |
| pre-slice grouped proposal | `supported_resolution` | one selectable issue |
| pre-slice grouped proposal | `customer_question` | one selectable issue |
| pre-slice grouped proposal | every ref `confirmed_fact` | blocked: `source_role_missing` |
| inactive flat claims | `supported_resolution` | one selectable issue |
| inactive flat claims | `customer_question` | blocked: `claim_source_role_incompatible`, then `claim_root_incomplete` |
| inactive flat claims | `confirmed_fact` | one selectable issue |

The pre-slice result localized a contradictory middle state:

- the grouped role index was not strict enough to reject a field-to-role
  mismatch;
- it was still authoritative enough to reject an otherwise complete proposal
  whose refs are all neutral;
- its primary roles were model-visible and could therefore bias the semantic
  proposal even when grouped projection does not enforce them per field.

Recognized `Client` / `Support` turn markers improve speaker attribution but do
not resolve this contradiction. Existing explicit semantic section labels are
deterministically readable, but sanitized clean-ticket approval alone does not
prove that the labels are semantically correct. They become authoritative only
when a contracted upstream producer or operator intentionally asserts those
fields. Requiring that assertion for all clean tickets would be a new upstream
input contract, not a selector implementation detail.

#### Role-Ownership Alternatives

The audit leaves two endpoint authority choices and one hybrid:

1. **Structured upstream authority.** Require a contracted cleanup producer or
   operator to assert explicit symptom/question, cause, resolution/answer, and
   verification sections. Python can inherit those declared roles and keep
   strict role validation. This is the strongest deterministic option, but
   changes the clean-ticket input contract and assigns semantic responsibility
   upstream.
2. **Model semantic authority over neutral evidence.** Stop presenting lexical
   guesses as formal roles and validate model observations by immutable refs,
   bounds, coverage, safety, and workflow rules. This removes contradictory
   Python hints but does not create a new source of stable issue identity; the
   aggregate no-loop finding still applies.
3. **Declared/heuristic hybrid.** Record whether a role was intentionally
   declared by a contracted producer or heuristically inferred. Strict
   field-to-role validation applies only to declared roles; heuristic or
   unlabeled evidence remains advisory or neutral and model-owned. This does
   not add a third semantic authority, but it requires role-origin metadata and
   a reviewed contract/migration boundary.

Adding a more elaborate regex, chronology heuristic, relation graph, or
separate NLP classifier over the same excerpts is not a third authority source.
No runtime role change is authorized by this evidence-only checkpoint.

#### Neutral-Evidence Safety Probe

The model-authority endpoint was tested without changing runtime code. The
probe made all ordinary runtime refs untrusted, reviewer-only
`confirmed_fact`, then supplied the one issue-role bit needed only to bypass
the current aggregate `source_role_missing` gate. All later grouped-projection
checks therefore ran unchanged.

| Synthetic scenario | Result after simulated aggregate-role bypass |
| --- | --- |
| complete technical issue | one selectable issue |
| technical issue missing resolution evidence | blocked: `evidence_shape_invalid` |
| context-only issue | blocked: `evidence_shape_invalid` |
| complete Q&A issue | one selectable issue |
| untrusted evidence marked public | blocked: `untrusted_provenance_visibility` |
| neutral fact proposed as `ticket_metadata` coverage | coverage rejected as `coverage_role_incompatible`; ref remains unassigned |

This probe does not prove model semantic stability. It shows only that the
aggregate lexical issue-role requirement can be removed or broadened without
removing the tested completeness, visibility, or coverage gates.

A model-authority implementation candidate must still:

- preserve deterministic non-issue roles used by the closed coverage matrix;
- block an issue composed only of deterministic non-issue evidence;
- present ordinary noisy-ticket evidence as neutral rather than as a guessed
  symptom, question, cause, or resolution;
- retain lexical scoring only as an internal bounded-selection hint;
- keep proposal shape, refs, coverage, visibility, provenance, completeness,
  operator selection, reviewer-only output, and publication gates unchanged;
- make no semantic-stability claim until installed real-runtime canaries pass.

### Model-Neutral Role Runtime Slice

Goal:

- make the active grouped contract reflect its actual ownership split: the
  model proposes semantics; Python validates immutable evidence and policy.

Allowed behavior change:

- keep lexical symptom/question/cause/resolution scoring as an internal
  bounded-selection hint only;
- expose ordinary selected evidence as `unclassified_evidence`;
- preserve closed deterministic non-issue roles for coverage validation;
- allow a complete grouped issue whose admissible evidence-role union contains
  `unclassified_evidence`;
- retain `source_role_missing` when the union contains only deterministic
  non-issue roles.

Forbidden behavior change:

- no prompt, provider, proposal schema, tool schema, correction, operator
  checkpoint, renderer, publication, or Langfuse change;
- no weakening of required technical cause/resolution or Q&A answer evidence;
- no public visibility or customer-reported origin from untrusted runtime
  evidence;
- no field repair, semantic fallback, manual drafting, or candidate
  suppression;
- no semantic-stability claim before installed runtime evidence.

Implementation result:

- ordinary selected excerpts and the immutable role index now expose only
  `unclassified_evidence`;
- `internal_workflow_note`, `ticket_metadata`, `formatting_artifact`, and
  `duplicate_excerpt` remain deterministic non-issue roles;
- grouped projection treats `unclassified_evidence` as issue-bearing evidence
  while preserving the non-issue-only blocker;
- complete neutral technical and Q&A proposals project;
- missing-resolution and context-only proposals remain
  `evidence_shape_invalid`; with complete sibling issues they remain in the
  outcome ledger as `blocked_need_more_evidence` instead of terminating the
  sibling candidates;
- untrusted public visibility remains blocked;
- neutral evidence cannot satisfy deterministic metadata coverage;
- atomic refs, speaker metadata, ordering, bounds, safety, operator selection,
  reviewer-only output, and no-publication contracts are unchanged.

Residual risk:

- the model remains the semantic partition owner, so candidate identity can
  still vary across live runs;
- lexical ranking can still omit lower-ranked atoms when the existing bounds
  are exceeded;
- a schema-valid but semantically wrong model field assignment cannot be
  corrected by an independent semantic authority that the system does not
  possess.

### Installed Model-Neutral Canary Localization

The package built from source commit `8286ad7` has SHA-256
`9e4122f99c507c428811f7ec4a8ee4ff157588d6251f8c8a94772486ab57cd9a`.
Source and installed-wrapper stdio smoke each passed all 17 checks, the
installed registry cache matched, and the six-tool surface remained unchanged.
The pre-install MCP child was stopped before the fresh run.

One fresh minimal `/draft` run reached grouped semantic projection and then
terminated with `semantic_issue_boundary_ambiguous` and
`evidence_shape_invalid`. No draft or reviewer bundle was produced. The model
response described multiple distinct issue proposals, including at least one
without sufficient resolution evidence. No ticket identifier, issue title,
ticket content, source ref, local path, or reviewer-bundle identifier is
retained here or exported to Langfuse.

Forensic localization found that projection already preserved complete issues
and blocked proposals in separate collections, and the downstream candidate
builder already accepted both collections. The workflow boundary nevertheless
raised a packet-terminal error whenever any blocked proposal existed. Thus one
issue-local draftability failure hid complete siblings before normal authoring.

The bounded correction changes no semantic interpretation and adds no prompt,
schema, tool, or workflow layer:

- `evidence_shape_invalid` remains fail-closed for the affected issue;
- when complete sibling issues exist, the invalid issue is recorded as
  `blocked_need_more_evidence` and siblings continue through normal authoring,
  with native selection when multiple complete siblings remain;
- when every issue is invalid, the packet remains terminal;
- deterministic non-issue-role, provenance, visibility, and unsafe blockers
  remain packet-terminal.

### Per-Issue Evidence-Shape Disposition Review

Changed runtime behavior:

- an issue-local `evidence_shape_invalid` no longer terminalizes a packet that
  also contains at least one complete issue;
- the incomplete issue is preserved as `blocked_need_more_evidence`;
- one complete sibling continues through single-candidate authoring;
- multiple complete siblings continue to native candidate selection in their
  original relative order.

Unchanged contracts:

- an all-incomplete packet remains terminal;
- deterministic non-issue-role, provenance, visibility, and unsafe blockers
  remain packet-terminal;
- prompts, proposal and tool schemas, provider routing, reuse, renderer,
  reviewer-only output, publication gates, and Langfuse export are unchanged.

Validation:

- focused semantic, MCP, workflow, draft, batch, result, and submission tests:
  339 passed;
- full suite excluding the intentionally dirty-worktree freeze check:
  1396 passed, 1 skipped, 1 deselected;
- policy suite excluding that same freeze check: 53 passed, 1 deselected;
- Ruff and `git diff --check`: passed;
- focused architecture, safety, privacy, and behavior-drift review: GO.

The production graph hashes were refreshed for the two changed runtime modules.
No new mechanically enforceable promotion candidate was found beyond the
direct single-sibling, multi-sibling, all-invalid, and packet-safety regression
tests added or retained in this slice.

### Installed Per-Issue Canary and Renderer Localization

The package built from source commit `18dc8d8` has SHA-256
`6a35c55ee264b24c2be3e852acc89e74d7c723fdaad20733ec1d10b89b3561d2`.
Source and installed-wrapper stdio smoke each passed all 17 checks, the
installed registry cache matched, and the six-tool surface remained unchanged.
The pre-install MCP child was stopped before the fresh run.

One fresh minimal `/draft` run reached native selection with three complete
candidates. The operator selected all three. Two candidates reached authoring
and terminated with `approved_summary_renderer_bounds_failed`; one remained
`blocked_retryable` with `approved_summary_resolution_steps_incomplete`. No
draft or reviewer bundle was produced. This proves the per-issue continuation
correction in the installed runtime and localizes the remaining failure below
semantic projection.

Component isolation reproduced the two terminal outcomes with a synthetic
grouped issue whose model-owned summary exceeded the renderer title bound:

- evidence construction, validation, and decision passed;
- the grouped adapter had copied the full semantic summary into `title`;
- the renderer correctly rejected the unbounded title;
- the retryable incomplete-resolution outcome is separate and remains
  unchanged.

The bounded correction preserves the full semantic summary and derives a short
deterministic title before candidate display and rendering. It does not widen
renderer limits or change semantic interpretation, prompts, schemas, tools,
provider routing, resolution completeness, safety, publication, or Langfuse.

Validation:

- focused semantic, MCP, workflow, draft, batch, result, submission, and
  renderer tests: 429 passed;
- full suite excluding the intentionally dirty-worktree freeze check:
  1398 passed, 1 skipped, 1 deselected;
- policy suite excluding that same freeze check: 53 passed, 1 deselected;
- Ruff and `git diff --check`: passed;
- focused architecture, safety, privacy, renderer-policy, and behavior-drift
  review: GO.

The explicit 180-character derived-title bound duplicates the renderer contract
rather than exporting a new shared constant. The end-to-end renderer regression
is the drift guard; introducing a new shared policy surface is deferred unless
the limits actually diverge.

### Exact-Build Repeat Matrix

Two fresh runs used the same installed package built from `4257147`.

| Candidate slot | Run 1 | Run 2 |
| --- | --- | --- |
| A | `completed_draft` | `blocked_retryable` |
| B | `completed_draft` | `flag_existing` |
| C | `blocked_retryable` | `blocked_retryable` |

Both runs preserved three candidates, reached native selection, processed the
operator's all-candidates choice, avoided packet-terminal and workflow-stop
states, and kept public output disabled. The repeat therefore passes candidate
preservation and safety invariants but fails the per-candidate disposition
stability gate. A third end-to-end repetition was stopped.

Source tracing localizes both changed dispositions to model-produced observation
text:

- executable-resolution validation reads the observation text, not the
  immutable referenced excerpt value;
- explicit existing-article recognition searches that same observation text
  for the public support URL and its context;
- both downstream components are deterministic for a fixed candidate packet.

The next theory is therefore an ownership refinement, not a new semantic owner:
the model continues to assign evidence to semantic fields, while Python accepts
canonical evidence values only through verifiable extractive grounding against
the immutable referenced excerpts. Model-owned issue summaries remain
generative. No implementation is authorized by this audit entry alone.

### Subsequent Ownership Decision

The operator subsequently authorized the ownership refinement. Runtime
characterization found 17 non-summary observations: one was exact-grounded and
16 were paraphrased. The paraphrases removed executable detail from downstream
resolution/verification checks and changed per-candidate dispositions across
identical-build repetitions.

The accepted contract is:

- the model owns issue grouping, semantic-field assignment, and generative
  `summary`;
- every other observation must preserve an exact, whitespace-normalized
  fragment from one referenced immutable excerpt;
- explicit customer/support speaker labels constrain symptoms and question,
  while `unknown` remains admissible and is not inferred by Python;
- Python returns only a closed value-safe code and one bounded correction; it
  does not echo or reconstruct ticket text;
- tool surface, operator selection, renderer bounds, reuse policy, readiness,
  reviewer-only output, and publish prohibition remain unchanged.

## Interpretation

The successful labeled single-issue smoke proves the downstream workflow, not
general clean-ticket preparation. The repository describes raw sanitized
transcript as the primary Desktop smoke and strict labels as a separate
single-item smoke. Requiring all operators or cleanup sources to produce
strict S/C/R labels would therefore be a product input-contract change, not a
valid explanation of current behavior.

No new Claude canary is useful until the input-adequacy boundary can be
measured independently. A future selector change, if authorized, must be
tested against semantic inventory invariants and paraphrase/format variation,
not exact keyword snapshots.

## Deferred

- any further selector, regex, segmentation, prompt, or schema change;
- one fresh installed canary for the extractive-grounding correction;
- authenticated speaker provenance;
- omission-ledger implementation;
- semantic promotion or real-ticket stability claims.
