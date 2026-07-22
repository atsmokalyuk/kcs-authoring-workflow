# KCS-14.5 Semantic Stabilization Aggregate Attempt Review

Date: 2026-07-18

Status: final attempt review; semantic redesign frozen

Follow-up component localization:

- `docs/internal/engineering-process/slice-plans/kcs-14-5-multi-issue-component-forensic-audit.md`

Active compact change gate:

- `docs/internal/engineering-process/slice-plans/kcs-14-5-decision-log.md`

## Decision

The semantic-stabilization attempts did not establish stable candidate identity
or useful drafting yield for multi-issue real tickets. The verified grouped
runtime is restored as the safe baseline, but it is not promoted as a stable
semantic authoring path.

No further prompt patch, model-visible schema rearrangement, deterministic
overlap guard, unchanged-package canary series, or operator boundary workflow
is authorized from this workstream.

The permanent safety and control contracts remain successful and active:

- six existing KCS tools;
- bounded typed packets and immutable source grounding;
- Python validation, projection, selection state, KCS action, readiness, and
  writes;
- native candidate selection as the only operator-owned scope checkpoint;
- complete ordered candidate accounting;
- reviewer-only local artifacts;
- no freehand drafting, network fetch, Zendesk write, Help Center publication,
  automatic publication, or customer reply.

## Attempt Ledger

| Attempt | Hypothesis | Runtime evidence | Disposition |
| --- | --- | --- | --- |
| Grouped issue proposal with Python validation and projection | A bounded grouped proposal plus deterministic validation would make the model-proposed partition stable enough for native selection. | Control and safety behavior remained stable, but fixed-reference candidate counts changed from four to five and reviewer-only draft counts ranged from zero to two. After transcript context recovery, two unchanged-package runs still returned candidate counts `[5, 4]` and draft counts `[2, 1]`. | Retain only as the verified safe baseline. Do not claim semantic stability. |
| Boundary re-proposal, accept/exclude actions, and evidence-exclusion checkpoints | Bounded operator adjudication would correct uncertain partitions without manual drafting. | The checkpoints added latency and repeated the same ambiguity. Removing them improved the control surface without reducing safety. | Retired. Do not restore operator boundary questions. |
| Identity-bearing overlap guard on the grouped proposal | Pairwise source-ref overlap could detect incorrect model partitions deterministically. | Exact refs-only review showed that the reviewed incorrect partition did not contain the identity-bearing overlap required to trip the guard. | Falsified and retired. Do not replace it with another overlap heuristic derived from the same refs. |
| Atomic observation and relation packet | Removing model-created issues and projecting identities from atomic relations would transfer semantic ownership to Python. | The first installed C3 submission failed after its bounded correction and never reached viable candidate projection. | Rejected and reverted. Do not reintroduce a relation graph without a new source of semantic authority. |
| Oversized-turn segmentation and speaker-context preservation | Better evidence segmentation and preserved speaker provenance would remove input corruption that caused candidate drift. | Both corrections repaired real data-integrity defects and improved basic drafting yield, but candidate identity and per-candidate disposition still changed across unchanged-package runs. | Retain the data-integrity fixes. Do not represent them as semantic stabilization. |
| Explicit public resolution-reference preservation | Keeping an already approved public resolution reference inside bounded evidence would restore the deterministic reuse path. | The installed synthetic canary reached `flag_existing`, checked reuse, prevented a duplicate, performed no network call, and approved no public output. | Retain as a narrow successful capability. It does not generalize to semantic partitioning or missing resolution evidence. |
| Flat claim ownership with direct anchors | Flat claims and one direct owner anchor would reduce model responsibility enough for Python to create stable issue identities. | One complete technical identity produced one reviewer-only draft. The next C3 scenario with two clear independent identities failed before candidate projection with two `claim_root_incomplete` and three `claim_source_role_incompatible` outcomes and no bounded correction path. | Rejected at C3 and reverted. Keep the inactive pure projector only as research evidence. |

## Aggregate Findings

### What Worked

The system consistently enforced its safety floor. Across successful,
retryable, terminal, and invalid semantic outcomes:

- no model result bypassed Python validation;
- selected candidates were accounted for in order;
- missing mandatory resolution evidence remained fail-closed;
- no public output, customer reply, or automatic publication was authorized;
- explicit existing-article reuse could succeed without copying or fetching
  article content;
- transcript segmentation and speaker preservation fixed deterministic input
  corruption;
- value-safe Langfuse metadata made comparable outcome drift visible without
  adding a workflow layer or exporting ticket values.

### What Did Not Work

None of the tested model-visible decomposition contracts made multi-issue
identity stable:

- grouped proposals let the model choose `issues[]`;
- atomic relations moved the same semantic decision into relation construction;
- flat claims moved it into claim atomization, root selection, direct anchors,
  and formal source-role compatibility.

Python can validate a proposed semantic structure and deterministically project
from an accepted structure. It cannot derive the correct issue identity merely
by rearranging untrusted model fields when no independent semantic authority is
available.

Deterministic tests proved schema, projection, accounting, privacy, and safety
behavior. They did not prove that a live model would produce a valid or stable
semantic structure. Passing tests and installed stdio smoke are therefore
necessary implementation gates, not runtime semantic-promotion evidence.

Mandatory resolution validation is not the cause of identity drift. It exposes
evidence gaps after a candidate exists. Weakening it would increase drafting
yield by allowing unsupported procedures and is not an acceptable recovery.

## No-Loop Rules

The following work is closed unless a new architecture review presents
falsifiable evidence that is not already represented in this ledger:

1. another merge/split instruction or prompt correction;
2. another model-visible issue, observation, relation, claim, root, or anchor
   schema whose only semantic input is the same bounded excerpts;
3. another source-ref overlap, chronology, lexical-role, or candidate-count
   guard presented as semantic ownership;
4. restoration of boundary re-proposal, evidence-exclusion, accept-scope, or
   operator-authored resolution questions as normal workflow checkpoints;
5. more runs of an unchanged package after the first identity or yield
   mismatch;
6. weakening resolution, provenance, privacy, reviewer-only, no-publish, or
   no-customer-reply validation to improve yield;
7. treating Langfuse, additional tracing, or a new MCP tool as a semantic
   workflow fix;
8. treating the historical closeout package as a known-good yield rollback
   target.

A future semantic architecture must introduce a genuinely different source of
authority, such as operator-provided issue scope at workflow entry,
authoritative structured ticket fields, or deterministic existing-knowledge
identity. Reformatting the model's interpretation of the same excerpts is not
a new authority source.

## Supported Baseline

The restored grouped route supports only bounded claims:

- a complete clear issue may produce a reviewer-only draft;
- an explicit approved public reference may reach deterministic existing-
  article review;
- multi-issue candidate proposals remain model-proposed, Python-validated, and
  operator-selected, with no stability or useful-yield claim;
- incomplete or unsupported candidates remain deferred or terminal.

Routine real-ticket use remains unaccepted. Basic drafting recovery may improve
deterministic evidence preservation or an already proven decision path, but it
must not reopen semantic promotion implicitly.

### Post-Restoration Basic Smoke

One fresh installed live-model smoke after grouped restoration:

- registered one complete synthetic technical issue;
- prepared four bounded excerpts;
- accepted one grouped semantic issue containing symptom, cause, resolution,
  and verification evidence;
- generated one reviewer-only draft;
- ended as `draft_only` with `draft_only_reuse_search_missing`;
- kept public output and network calls disabled.

This falsifies the theory that registration, Desktop transport, semantic-review
submission, Python validation, downstream drafting, or reviewer-bundle writing
is globally broken. The observed instability is conditional on multi-issue
decomposition and interleaved evidence before candidate projection. No further
basic-path repair is authorized from this smoke.

## Reopening Gate

Before any new semantic implementation:

1. write a separate behavior-change design;
2. name the new semantic authority source;
3. state why it is not equivalent to grouped issues, atomic relations, flat
   claims, or overlap heuristics;
4. define a first-run falsification scenario with at least two independent
   identities;
5. define rollback before installation;
6. require zero operator boundary questions and the unchanged six-tool route;
7. stop after the first identity mismatch, invalid terminal submission, or
   zero-yield result required by the gate.

C4 stability and any semantic promotion remain unauthorized.
