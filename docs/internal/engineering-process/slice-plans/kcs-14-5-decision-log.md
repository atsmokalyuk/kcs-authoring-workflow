# KCS-14.5 Decision Log

Date: 2026-07-19

Status: active change gate

## Purpose

This is the compact decision index for any further KCS-14.5 change. It does
not replace the detailed experiment records. Before changing runtime behavior,
the developer must check this log and identify:

1. the previously tested decision that the change preserves or supersedes;
2. new falsifiable evidence not already represented below;
3. the deterministic regression that proves the local failure;
4. the single installed canary outcome that will accept or reject the change.

If a proposal repeats a rejected mechanism without a new authority source or
new failure class, stop before implementation.

Detailed evidence remains in:

- `kcs-14-5-semantic-stabilization-aggregate-attempt-review.md`;
- `kcs-14-5-multi-issue-component-forensic-audit.md`;
- `kcs-14-5-local-langfuse-observability.md`;
- `kcs-14-5-contract-consolidation.md`.

The complete per-attempt and rejected-design archive remains in the retained
historical branch `feature/PAUX-7103-kcs-14.5-contract-consolidation`; it is not
part of the release documentation surface.

## Permanent Product Boundaries

| Decision | Status | Consequence |
| --- | --- | --- |
| The model proposes semantic observations and issue grouping. | Active | Python must not invent issue identity from regexes, chronology, ref overlap, or another model-output graph. |
| Non-summary observations are extractive and grounded in immutable selected excerpts. | Active | Symptoms and questions preserve original customer wording; commands, URLs, and resolution detail cannot be replaced by paraphrases. |
| Python owns schema validation, evidence admissibility, projection, candidate actions, selection state, KCS action, readiness, rendering, persistence, and batch accounting. | Active | Model output cannot bypass validation or choose workflow/KCS state. |
| Native one/subset/all candidate selection is the only normal operator-owned scope checkpoint. | Active | Do not restore boundary re-proposal, accept-scope, evidence-exclusion, or normal-path resolution questions. |
| Missing mandatory resolution evidence remains fail-closed. | Active | Do not improve yield by inventing or accepting unsupported procedures. |
| Reviewer artifacts remain local and reviewer-only. | Active | No public output, auto-publish, Zendesk write, Help Center write, or customer reply. |
| The KCS tool route remains the existing six-tool surface. | Active | No development MCP surface or workflow tool is added. |
| Langfuse is an external, optional, value-safe engineering observer. | Active | It receives only allowlisted counts, hashes, booleans, enums, and verdicts with null input/output; it never becomes a workflow layer. |
| The M4 change gate is scoped to KCS-14.5 semantic ownership, provider/evaluation, and incident control-surface work. | Active | Independently approved work outside those surfaces may proceed only when it leaves the retained incident safety contracts unchanged. |

## Experiment And Runtime Decisions

| Mechanism or decision | Evidence | Disposition |
| --- | --- | --- |
| Grouped `semantic_issue_proposal_v1` | Preserves the safe control path but produced different candidate identities and draft yields on unchanged-package real-ticket runs. | Active safe baseline only. No semantic-stability claim. |
| Operator boundary lifecycle | Added repeated questions and latency without resolving ambiguity. | Retired. Do not restore. |
| Identity-bearing source-ref overlap guard | Exact refs-only review showed zero triggers for the reviewed incorrect partition. | Falsified and retired. |
| Atomic observation/relation graph | Failed the first installed C3 submission after its one bounded correction. | Rejected and reverted. |
| Flat claim/direct-anchor ownership | Passed one identity, then failed the first two-identity C3 case before projection. | Rejected and reverted; inactive projector is research evidence only. |
| Lexical or speaker-side Python semantic ownership | Either lost facts or created non-discriminating multi-role evidence. | Rejected. Speaker metadata may constrain provenance, not derive issue identity. |
| Oversized-turn segmentation and speaker-context preservation | Repaired deterministic input corruption and improved basic yield. | Retained as data-integrity behavior, not semantic stabilization. |
| Model-neutral ordinary excerpt roles | Removed false deterministic semantic authority while keeping conservative reviewer-only visibility/origin. | Retained. |
| Per-issue evidence-shape disposition | Prevents one invalid issue from deleting valid siblings. | Retained. |
| Exact extractive grounding | Runtime audit found 16 of 17 non-summary observations paraphrased; paraphrases removed commands and changed outcomes. | Retained. Summary alone remains generative. |
| Explicit public resolution-reference preservation | Synthetic installed canary reached `flag_existing` without fetching article content or creating a duplicate. | Retained as a narrow reuse path. |
| KCS-14 closeout rollback | Same real-ticket route produced zero reviewer-only drafts and was not a comparable A/B because the client changed. | Not a demonstrated working-yield rollback target. Keep Git history; do not use as a known-good baseline. |
| M3 fixed synthetic stages | Medium, continuation, and complex fixed scenarios each reached their reviewed stable series. | Valid control-path evidence only. Does not prove routine real-ticket semantic stability or yield. |
| M4 boundary/control-surface deletion | Removed boundary questions and compatibility branches while retaining native selection and safety. | Retained. Real-ticket yield remained unaccepted. |

## Recent Runtime Recovery Decisions

| Checkpoint | Runtime evidence | Decision |
| --- | --- | --- |
| `4ee000a` exact semantic evidence | Exact observations survive proposal validation and projection. | Retain. Do not restore paraphrased non-summary fields. |
| `4257147` bounded projected titles | Long model summaries no longer fail renderer title bounds. | Retain. Full summary remains available separately. |
| `18dc8d8` valid sibling preservation | Invalid issue evidence no longer suppresses valid siblings. | Retain. |
| `8286ad7` model-neutral evidence | Ordinary noisy-ticket roles no longer pretend to be deterministic semantic truth. | Retain. |
| `276966b` semantic runtime contract alignment | Missing empty `answer_evidence`, JSON-object-string transport, and symptomless technical siblings are handled at their owning boundaries. | Retain. |
| `dc157d3` proposal wire canonicalization | The live model's object/string transport, omitted empty fields, and string summary reach native candidate selection while strict core validation remains unchanged. | Retain. |
| Current authoring recovery batch | The latest live run reached native selection, then one candidate failed resolution completeness and another failed reviewer HTML quality. Local reproduction showed narrative resolution observations were treated as mandatory numbered steps, and a grounded public URL with `fix` context missed the existing-article matcher. | Provisional until review/commit/install/canary. Separate executable steps from complete exact resolution evidence; recognize only allowlisted URL plus grounded existing/fix context; keep bare URLs and missing procedures blocked. |
| Current batch diagnostics | The batch envelope discarded the value-safe renderer blocker and omitted aggregate selected/attempted/completed/blocker counters. | Provisional until review/commit. Preserve closed blocker kinds and bounded integer counters only; never include ticket values, titles, refs, paths, or HTML. |
| `5b35ce0` installed real-ticket canary | Semantic review reached native selection with two selectable and two evidence-blocked items. Selecting all ended with two `reviewer_html_quality_blocked` outcomes and zero drafts. Installed code contained the new counters and blocker propagation, but Claude-visible batch text omitted them. | Semantic/selection recovery accepted for this run; authoring yield not accepted. Repair only the existing value-safe batch text projection before diagnosing the renderer. Do not change semantic ownership or renderer rules without the closed blocker kinds. |
| `955ce3a` installed diagnostic canary | Semantic review reached four candidates and native all-selection. The batch attempted three: issue 1 blocked on `cause_contains_resolution_action` plus `transcript_placeholder_in_public_body`; issue 2 blocked on `cause_contains_resolution_action`; issue 3 stopped on `approved_summary_evidence_build_failed`; issue 4 was not attempted. Counters were selected 4, attempted 3, completed 2, terminal blocked 3, workflow stopped 1, drafts 0. | Text diagnostics accepted. Semantic/selection path is not the current failure owner. Keep all three downstream failures separate: mixed-purpose exact cause blocks, public-body placeholder handling, and evidence-builder validation. Do not alter renderer rules until the originating field shape is confirmed; do not alter semantic identity. |

## No-Loop Rules

Do not implement any of the following from KCS-14.5 evidence alone:

1. another issue/relation/claim/root/anchor schema over the same excerpts;
2. another merge/split prompt patch or model-instruction wording experiment
   presented as semantic architecture;
3. another ref-overlap, candidate-count, chronology, or lexical-role heuristic
   presented as issue identity;
4. another operator boundary, evidence-exclusion, retry-strategy, or
   operator-authored-resolution checkpoint in the normal route;
5. weaker grounding, completeness, safety, privacy, reviewer-only, no-publish,
   or no-customer-reply validation to increase draft count;
6. another unchanged-package real-ticket run after the first failure at the
   same stage;
7. Langfuse, a new tool, more tracing, or a code graph as a semantic fix;
8. reconstructing historical runtime payloads or outcomes from chat,
   screenshots, summaries, or memory.

Allowed recovery work must be deterministic and downstream of an already
accepted semantic proposal:

- preserve exact evidence already present;
- repair transport/schema normalization without weakening the strict core;
- correct projection between distinct existing field meanings;
- correct an existing deterministic reuse/decision rule using grounded values;
- preserve value-safe blocker/counter diagnostics;
- repair renderer behavior only after the exact closed blocker is reproduced.

## Change Gate

Every further runtime change must add one row below before implementation or
before commit when the evidence is discovered during forensics.

| Field | Required value |
| --- | --- |
| Failure stage | One existing stage and exact closed debug/blocker code. |
| New evidence | Deterministic reproduction or one fresh installed runtime outcome. |
| Prior decision checked | Link or row name from this log. |
| Intended change | One owning component and one behavior delta. |
| Stable contracts | Explicit list of unchanged safety/control boundaries. |
| Regression | Named deterministic test that fails before and passes after. |
| Canary | One fresh installed attempt with a predefined pass/fail result. |
| Stop condition | First mismatch, new blocker class, unsafe output, or workflow/control drift. |

## Current Next Gate

The current authoring recovery batch may proceed only if review confirms:

- full exact resolution evidence remains preserved;
- only executable/informational observations become numbered resolution
  steps when at least one such observation exists;
- a bare or unrelated URL still fails standalone completeness;
- an allowlisted public article URL plus grounded existing/fix context reaches
  deterministic existing-article review;
- renderer quality rules are not weakened;
- batch diagnostics contain only closed blocker strings and bounded counts;
- tool count, native selection, ordered candidate accounting, reviewer-only
  storage, no-publish, and no-customer-reply boundaries are unchanged.

## Current Change Record

| Field | Current authoring recovery batch |
| --- | --- |
| Failure stage | Existing `input_validation` / `approved_summary_resolution_steps_incomplete`; existing `renderer` / `reviewer_html_quality_blocked`. |
| New evidence | The accepted live proposal reached native selection. A local projection reproduction showed that narrative resolution blocks were counted as numbered procedural steps. A local exact-value probe showed that an allowlisted public support URL explicitly described as the fix did not reach reuse review. |
| Prior decision checked | `Exact extractive grounding`, `Explicit public resolution-reference preservation`, and `Current batch diagnostics`. |
| Intended change | `desktop_semantic_candidates.py` separates procedural steps from full exact resolution blocks; `desktop_authoring_pipeline.py` recognizes only an explicit same-observation article relation; `desktop_draft_batch.py` preserves closed blockers and aggregate counters. |
| Stable contracts | Model semantic ownership; strict Python validation; native candidate selection; fail-closed missing evidence; reviewer-only local storage; no publish/customer reply/network fetch; six-tool surface; value-safe Langfuse export. |
| Regression | `test_projection_separates_resolution_narrative_from_executable_steps`; `test_projected_grounded_fix_reference_uses_existing_article_review`; both unrelated-fix URL negative tests; stopped-batch counter assertions. |
| Canary | One fresh installed real-ticket attempt. Accept only native selection followed by a draft or explicit existing-article review for an evidence-complete candidate, with exact blocks preserved and value-safe counters present. |
| Stop condition | First new blocker class, false existing-article match, missing exact block, unsafe output, operator boundary question, or workflow/control drift. |

### Value-Safe Batch Text Projection Follow-up

| Field | Diagnostic projection follow-up |
| --- | --- |
| Failure stage | Existing Desktop result shaping after `reviewer_html_quality_blocked`; closed renderer blockers and aggregate counters were present in Python structures but absent from Claude-visible text. |
| New evidence | The installed `5b35ce0` canary returned only the general per-candidate debug code. Inspection confirmed the installed package contains the structured counter/blocker code while `_draft_article_batch_tool_result_text` omits those fields and `_followup_metadata` drops per-candidate blocker lists. |
| Prior decision checked | `Current batch diagnostics` and the `5b35ce0` installed real-ticket canary row. |
| Intended change | `desktop_tool_results.py` exposes existing closed counters and blockers in compact batch text; `desktop_draft_batch.py` carries existing blocker lists into follow-up cards. |
| Stable contracts | No semantic, candidate, validation, renderer, retry, storage, network, publish, or customer-reply behavior changes. No raw values, titles, refs, paths, or HTML are added to diagnostics. |
| Regression | Batch result text contains the six integer counters, top-level closed blocker list, and per-candidate closed blocker kinds while retaining the terminal no-follow-up instruction. |
| Canary | One fresh installed attempt at the same real-ticket route. Accept diagnostics only if exact closed blocker kinds and counters are visible without raw content. |
| Stop condition | Any content-bearing field, evidence text, title, path, source ref, HTML, new operator question, or changed candidate/workflow outcome. |

### Reviewer-Only Quality-Debt Recovery

| Field | Reviewer-only quality-debt recovery |
| --- | --- |
| Failure stage | Existing `renderer` / `reviewer_html_quality_blocked`, with closed blockers `cause_contains_resolution_action` and `transcript_placeholder_in_public_body`. |
| New evidence | The installed `955ce3a` canary reached native all-selection, then the first two evidence-complete candidates were rejected only because exact semantic observations were rendered directly into article sections. Git history localizes that direct projection to `3ffe109`; the renderer quality rules predate it. The registered clean ticket contains bounded redaction placeholders, while the evidence safety gate separately blocks unsafe identifiers. |
| Prior decision checked | `Exact extractive grounding`, `M4 boundary/control-surface deletion`, `955ce3a installed diagnostic canary`, and the no-loop prohibition on weakening safety or grounding. |
| Intended change | `desktop_draft_output.py` and `desktop_workflow.py` treat only the two named, sanitized, reviewer-remediable quality findings as reviewer-only draft debt. The local bundle is written with `kcs_ready=false`, `ready_for_reviewer=false`, `recommended_action=draft_only`, and the closed blockers preserved. Every other quality blocker remains terminal. |
| Stable contracts | Exact evidence; model semantic ownership; Python validation and rendering; native candidate selection; unsafe-input blocking; missing-section and other renderer blockers; reviewer-only local storage; no publish/customer reply/network; six-tool surface; value-safe Langfuse export. |
| Regression | A cause/action or redaction-placeholder quality finding writes a local reviewer-only bundle and remains not KCS-ready; a missing required section and every non-allowlisted blocker still write nothing and remain `reviewer_html_quality_blocked`. |
| Canary | One fresh installed real-ticket attempt. Accept only if issue 1 and/or issue 2 produce reviewer-only bundles with the exact quality blockers retained, no public approval, and no new operator checkpoint. |
| Stop condition | Any unsafe value reaches a bundle, any non-allowlisted quality blocker writes a bundle, a draft is marked KCS-ready, candidate identity changes, or a new blocker class appears. |

Installed canary verdict for `aa99e8f`: accepted. The ordinary
the reviewed noisy multi-issue route reached native selection. Selecting all produced
two local reviewer-only drafts: one retained
`transcript_placeholder_in_public_body`, the other retained
`cause_contains_resolution_action`; both also retained
`reuse_search_not_checked`. Both remained not KCS-ready and no public output
was approved. A third candidate remained blocked on the already isolated
`approved_summary_evidence_build_failed` path. This closes the renderer
quality-debt recovery without authorizing another semantic or renderer change.

The next possible recovery is a separate upstream safety slice. Local
value-safe inspection found non-documentation IPv6 values in the registered
clean ticket: registration sanitization accepted them, while normalized
evidence safety rejected them later. Do not change that path until its own
change record defines whether the owner is ticket redaction, clean-ticket
registration, or per-candidate safety disposition.

### Candidate-Local Safety Disposition

| Field | Candidate-local safety disposition |
| --- | --- |
| Failure stage | Existing `evidence_builder` / `approved_summary_evidence_build_failed` for a candidate whose normalized packet fails the existing evidence safety gate. |
| New evidence | The accepted `aa99e8f` canary generated two reviewer-only drafts, then stopped before the next sibling when the third candidate contained non-documentation IPv6. The ticket's cleanup-form metadata declared `confirmed_no_pii=true` and `scan_clean=true`; local value-safe inspection found 12 non-documentation IPv6 values. Registration sanitization does not detect IPv6, while `validate_evidence_safety` does. |
| Prior decision checked | `Valid sibling preservation`, `Exact extractive grounding`, `Missing mandatory resolution evidence remains fail-closed`, and the accepted reviewer-only recovery. |
| Intended change | Give the existing evidence-builder safety rejection a typed candidate-local path. The Desktop pipeline reports the existing closed `approved_summary_safety_blocked` code, which is already a terminal candidate disposition, so the sequential batch continues to later siblings. Generic builder/contract failures remain `workflow_stopped`. |
| Stable contracts | The unsafe candidate remains blocked; no unsafe value is logged, rendered, stored, or exported; exact evidence and semantic identity are unchanged; no retry/operator checkpoint is added; reviewer-only, no-network, no-publish, and six-tool boundaries remain unchanged. |
| Regression | A non-documentation IPv6 candidate returns `approved_summary_safety_blocked`; in an all-selection batch it is `completed_blocked` and the next safe sibling is attempted. A non-safety evidence-builder failure remains `approved_summary_evidence_build_failed` and stops the batch. |
| Canary | One fresh installed attempt. Accept only if the IPv6 candidate remains blocked with no bundle while the later sibling is attempted, and no private value appears in diagnostics. |
| Stop condition | Any unsafe bundle/write, changed candidate identity, generic build failure treated as candidate-local, new operator question, or changed publication/network behavior. |

The raw IPv6 leak itself belongs to the external cleanup-form scanner and is
not repaired by this repository change.

#### Installed Canary Result

The fresh installed real-ticket attempt reached native selection with two
draft-eligible candidates. Selecting both produced two reviewer-only drafts;
neither was KCS-ready or public-output approved. This passes the multi-issue
selection, sequential batch, reviewer-only, and no-publish checks.

The attempt is inconclusive for candidate-local IPv6 continuation because the
semantic projection did not expose the IPv6 item or a later sibling as
draft-eligible candidates. A follow-up installed stdio attempt using the
fixture semantic provider is not comparable: that provider substitutes fixed
candidate content, so the supplied IPv6 did not reach the evidence safety
gate. No unsafe value was written to its reviewer artifacts. Do not repeat
either attempt as proof of the candidate-local safety canary; retain the
deterministic regression evidence and move the raw leak to the external
cleanup-form owner.

#### Reviewer Artifact Grounding Check

The two reviewer-only artifacts from the accepted installed attempt were
compared locally with the external cleanup form's clean ticket without
reproducing ticket text. The first artifact contained two symptom blocks and
the second contained 21 meaningful nested symptom/error text chunks; every
block or chunk was an exact substring of the clean ticket. Both cause sections
were exact-grounded. Neither artifact contained IPv6. One of two resolution
items in each artifact was exact-grounded; the other was renderer-composed and
remains reviewer-only under the recorded checks. This evidence does not justify
another symptom-grounding guard or prompt change.

#### Pre-KCS-14 Golden Candidate Comparison

The installed N=2 report must not be described as a two-candidate result.
It exposed two **draftable/selectable** items and three additional
`needs_more_evidence` semantic outcomes. The pre-KCS-14 golden reviewer packet
records three issue identities: Apache configuration failure from a missing
`SSLCACertificateFile`, network/IP-change broken bindings, and Let's Encrypt
failure from IPv6 firewall filtering. All three identities remain present in
N=2; the first two are selectable and the third remains blocked, matching the
golden disposition.

N=2 additionally separated IP-interface errors and a permissions scan finding
as blocked semantic outcomes. This is possible over-splitting, not golden
candidate loss. Do not count N=2 as stable by comparing only the two native
selection options, and do not start N=3 until the extra blocked outcomes are
classified as legitimate separate issues, coverage-only material, or
fragments of the golden network/IP candidate.

The subsequent operator-reviewed redacted-ticket audit supersedes the
provisional classification above. The flattened transcript contains six
independent cause/resolution or question/answer identities. It also contains
an explicit ticket-fork instruction and copied or continued investigation
history, but the clean-ticket artifact and metadata do not preserve
comment-level current-ticket, parent-ticket, or fork-ticket provenance.
Therefore six is a transcript-level identity count, not a proven
current-ticket-owned candidate count.

The pre-KCS-14 showcase packet contains three identities and the current
projection contains five outcomes, but neither count is a valid exhaustive
golden until their ticket-ownership scope is proven equal. The current
projection still shows boundary defects: it merges independent chains while
promoting an IP-interface error and stale scan state that belong to an existing
chain. Registrar/HTTP observations without a supported resolution and
status/escalation messages remain coverage-only.

Do not encode three, five, or six as a runtime heuristic or ticket-specific
tracked fixture expectation. The next representation decision belongs to the
external cleanup/Zendesk preparation boundary: preserve comment-level source
ticket provenance or intentionally produce one ticket-owned evidence stream.
Only after that input contract exists can a candidate-count canary compare
golden and current projections. Model semantic ownership and Python
validation/projection ownership remain unchanged.

The operator subsequently supplied the ticket-level Zendesk summary that
defines the intended canary scope across the forked history. That approved
summary resolves the provenance ambiguity for this canary and supports five
independent issue identities. The three-item pre-KCS-14 output is a valid
core/showcase subset but is not an exhaustive semantic golden. Two additional
identities are present: one network-resolution outcome with incomplete
procedure evidence and one permissions-repair outcome with an explicit
supported action.

For the current N=2 evidence, the count of five is therefore not itself a
regression. The remaining audit target is boundary correctness: each of the
five outcomes must map to one independent cause/resolution chain, interface/IP
errors must remain evidence of the network-binding chain rather than a sixth
identity, and non-article observations remain coverage-only. This
ticket-specific expectation belongs in the decision record only; do not put
ticket subject values or a fixed candidate-count rule into runtime code or
tracked fixtures.

#### N=2 Diagnostic-Fragment Boundary Evidence

The exact refs-only projection of the accepted N=2 proposal showed five issues
and no pairwise overlap among their cause and resolution source refs. One
blocked issue contained cause evidence but no resolution evidence; operator
review classified it as an intermediate diagnostic of another issue rather
than an independent unresolved customer problem. The retired identity-overlap
guard would therefore trigger zero times and remains falsified.

This evidence localizes the defect to model-owned final partitioning. The
model-visible boundary contract now requires a final pairwise check before
submission: group evidence by independently searchable problem or question and
its linked resolution outcome; attach diagnostic or repair output to its parent
only when it is part of the same causal chain and has no independent issue
identity; keep an independent unresolved customer problem separate even
without resolution evidence. Distinct issues must not be merged merely to
complete an evidence shape.

No proposal schema, Python semantic heuristic, overlap rule, lexical rule,
candidate-count rule, operator checkpoint, or compatibility path is added.
Accept the next installed canary only if the diagnostic fragment remains
evidence of its parent issue while genuinely independent incomplete issues
remain blocked outcomes and native selection remains the only operator
checkpoint.

#### Installed N=3 Boundary Result

A fresh installed run on commit `d2f70f5` reached native selection without a
boundary checkpoint. It exposed three selectable issues and one independent
incomplete outcome. The previously separated diagnostic fragment was no longer
reported as its own issue. This passes the narrow diagnostic-fragment boundary
check and preserves the intended blocked disposition for incomplete material.

The broader ticket-scoped boundary check is not yet stable. One selectable
issue still combined an earlier resolved network/name-resolution chain with a
later invalid-address/bindings chain that the approved ticket-level summary
defines as independent. Two selected items produced reviewer-only drafts; a
third remained blocked by the existing candidate-local safety gate. No public
output or operator recovery question was produced.

Record this run as a partial, non-promotable canary result. Do not add another
wording-only contract change from the presentation summary. The next evidence
step is to inspect the exact accepted N=3 proposal and the prepared excerpt
roles/provenance for the merged issue. If the separable resolution outcomes
were absent from model input, the defect belongs to preparation or cleanup
representation. If both were present and independently grounded, the defect
remains in model-owned partitioning and requires a reviewed task-shape change,
not a Python lexical, chronology, overlap, or candidate-count heuristic.

No Langfuse export is authorized for this run: it does not have a matching
canonical rebaseline record and its overall ticket-scoped verdict is not
passing.

#### N=3 Prepared-Evidence Ownership Result

The exact accepted N=3 proposal and the locally reproduced prepared packet
falsify the model-boundary diagnosis for the remaining merge. The selected
packet contained isolated sentences chosen by Python ranking rather than the
complete original Client/Support blocks. In two material support turns, the
selected sentence omitted adjacent cause and resolution detail from the same
original turn. A separate supported cause/resolution turn was also displaced
by the twelve-excerpt selection limit. The model therefore did not receive the
complete evidence needed to partition the independent chains.

The owner is semantic-review preparation, not model partitioning or Python
projection. Do not add another boundary prompt, lexical identity rule,
candidate-count rule, overlap heuristic, or operator checkpoint for this
failure.

For recognized Client/Support transcripts, preserve each original turn as one
bounded block, splitting only when the per-block byte bound requires it. When
the complete inventory fits the packet bounds, pass every block to the model
in source order without semantic ranking. The model-visible role remains
`unclassified_evidence`; speaker-side metadata remains deterministic. Increase
the opaque source-ref bound from 24 to 48 while retaining the existing
per-block, total packet, observation, issue-count, reviewer-only, no-network,
and no-publish bounds. Non-transcript structured text retains the existing
twelve-excerpt ranked fallback. A recognized transcript that does not fit the
complete-inventory bounds blocks during preparation; it must not fall back to
semantic ranking. Internal-support turns remain excluded from model-visible
input under the existing data-handling baseline.

The value-safe local reproduction now produces 28 source blocks totaling
20,317 UTF-8 bytes and preserves every audited cause/resolution fragment. This
is deterministic pre-model evidence only, not an installed runtime verdict.
The next installed canary must verify native candidate selection, correct
separation of the independently searchable chains, preservation of incomplete
items as blocked outcomes, and absence of new operator checkpoints. No
Langfuse export is authorized before that canary passes the existing comparable
runtime gate.

#### Installed Complete-Turn Canary N=1

The fresh installed run on `860952f` reached native candidate selection through
the ordinary short `/draft` command. It produced five semantic outcomes, with
two reviewer-only drafts and three evidence-incomplete blocked outcomes. The
previously merged network and address-assignment chains were separated. The
diagnostic address-not-found fragment remained evidence of its parent chain
rather than becoming an additional issue. Native candidate selection was the
only operator checkpoint; no evidence-exclusion, boundary-reproposal, or
resolution-detail question was shown.

Local reviewer-artifact inspection confirmed that the address-assignment draft
contains its own cause/resolution chain. The later reviewer draft treats an
old scan result as context before the current permission finding and supported
repair action; it does not claim that the permission state caused the earlier
binding failure. Both artifacts remain not KCS-ready, reuse-unchecked,
reviewer-only, and not approved for public output.

Record N=1 as a boundary pass and a usability warning. The operator reported
the ordinary run as long and heavy. The preparation packet contained 28
eligible external speaker blocks totaling 20,317 UTF-8 bytes; no reliable
end-to-end duration was emitted by the tool route, so do not invent a latency
number. Do not recover speed by restoring semantic Python pruning or omitting
original customer/support blocks. N=2 must use a fresh chat with the same
installed package and the same short command. Langfuse export remains deferred
until the comparable runtime gate is complete.

#### Complete-Turn Canary N=2 Pre-Handoff Invalid

The fresh N=2 run again produced five semantic outcomes and preserved the
accepted issue boundaries: the network-resolution and address-assignment
chains remained separate, and the address-not-found diagnostic remained
evidence of its parent rather than becoming a sixth issue. Candidate
disposition was not stable. N=1 produced two reviewer-only drafts, while N=2
produced one; the later permissions candidate changed from reviewer-only draft
to `approved_summary_safety_blocked`.

The exact retained semantic proposal for the changed candidate contained no
email, non-example domain, URL, private user path, license ID, raw ticket ID,
secret assignment, non-documentation IPv4, or non-documentation IPv6 in its
summary or evidence observations. Some exact observations contained bounded
redaction placeholders, which are renderer quality debt rather than unsafe raw
values. The internal Python-projected draft candidate was not present in the
retained tool transcript, so the candidate-local safety result must not be
attributed to a model field by inference.

Independent local pre-handoff inspection found that the cleanup-form artifact
accepted as `scan_clean=true` still contained compressed
non-documentation IPv6 values. The cleanup scanner used an uncompressed-only
IPv6 regular expression, while the downstream KCS safety gate used IP address
parsing. Complete-turn preparation therefore sent an input to the model that
violated the existing clean-ticket data contract before downstream safety
could block it.

N=2 is not a comparable runtime canary and N=3 must not run on that artifact.
The recovery owner is the input boundary:

1. the cleanup-form redactor and residual scanner must recognize compressed,
   mapped, and scoped IPv6 using validated address parsing;
2. KCS clean-ticket registration must reject residual IPv6 before storage and
   semantic handoff even when cleanup metadata claims a clean scan;
3. regenerate the local clean artifact through the repaired cleanup form;
4. restart the comparable runtime sequence at N=1 with the ordinary short
   command.

Do not change semantic ownership, issue-count expectations, projection,
renderer policy, candidate safety disposition, operator checkpoints, or
Langfuse export in response to this invalid canary. The specific N=2
candidate-local safety code remains diagnostically unresolved unless it
reappears on a newly generated pre-handoff-safe artifact.

#### Regenerated-Input Canary N=1 Semantic-Submit Failure

The first run on the regenerated, hash-bound cleanup-form artifact passed the
clean-ticket metadata and input-safety boundary and prepared the complete
28-block external-speaker inventory. It did not reach native candidate
selection. The first semantic submission was rejected for a forbidden local
reference. Claude then made a second submit against the same review ref even
though the first result offered no bounded correction; the second call returned
`semantic_review_unavailable` because terminal submission failure had already
cleared pending state.

Local value-safe reproduction found no local/workstation reference in any of
the 28 selected excerpt blocks. Therefore the rejected reference was not
required by model-visible ticket evidence. Treat this as two distinct failures:

1. the model-produced proposal crossed the observation-only submission
   boundary by adding a local/workstation reference not present in the prepared
   evidence;
2. the agent ignored the terminal no-correction result and issued a prohibited
   second submit.

This is a failed comparable N=1, not a transient backend outage. Do not restart
the end-to-end canary or alter input cleanup, semantic ownership, issue
boundaries, projection, renderer policy, candidate disposition, or Langfuse
export in response. The next work is component-local: make the packet task
explicitly forbid inferred local/workstation and tool-artifact references, make
terminal submission results expose no recovery action, and add regression tests
for both contracts. Repeat N=1 only after those component checks and installed
package smoke pass.

#### Regenerated-Input Canary N=1 Terminal Stop and Source-Heading Conflict

The first installed run after the terminal-result fix stopped after one rejected
semantic submission. It did not retry the consumed review reference, report a
transient backend outage, or offer an operator recovery choice. Record the
terminal/no-retry behavior as passed.

The submission was rejected with
`semantic_review_forbidden_html_or_markdown`. A value-safe local scan of the 28
prepared external-speaker blocks found three blocks that match only the generic
Markdown-heading detector. None matched the fence, HTML, blockquote,
configuration-comment, shell-prompt, or local/workstation-reference detectors.
The preparation contract requires original source blocks and the semantic
submission contract requires extractive observation text, but the generic
submit guard rejected those source headings before extractive grounding ran.

Treat this as a deterministic preparation/submission contract conflict, not a
new model-boundary failure. The narrow correction is to permit heading syntax
only in source-grounded semantic observation `text` fields. Generated summaries
and every non-semantic caller retain the generic heading prohibition. Fences,
HTML, blockquotes, local paths, and forbidden control fields remain blocked in
all semantic fields. The existing extractive-grounding validator must still
reject an invented heading that is absent from its referenced approved block.

Do not start another installed canary until focused semantic-submit tests, the
full deterministic suite, package rebuild/install, and source/installed stdio
smoke pass. Do not change input cleanup, semantic ownership, issue boundaries,
projection, renderer policy, candidate disposition, or Langfuse export for this
failure.

#### Regenerated-Input Canary N=1 After Submit-Contract Fixes

The fresh installed run on `09ab84f` completed the normal semantic-review and
batch route from the ordinary short command. It produced five semantic
outcomes, one reviewer-only draft, and four evidence-incomplete deferred
outcomes. It did not stop on local-reference or source-heading validation, did
not consume the review ref through a terminal retry, and did not surface a
boundary-reproposal or evidence-exclusion checkpoint.

The five-outcome partition matches the approved canary scope recorded above.
No additional diagnostic-only identity was surfaced. Record this as a pass for
the semantic-submit path, accepted issue-boundary count, Python-owned batch
continuation, and terminal/no-retry behavior. It is only N=1 and does not prove
stable per-candidate disposition.

The generated artifact manifest reports `draft_only_reuse_search_missing`,
`reuse_search_status=skipped`, `kcs_ready=false`,
`ready_for_reviewer=false`, and `public_output_approved=false`. The artifact is
therefore reviewer-only and must not be promoted as KCS-ready or public output.

Run N=2 and N=3 in fresh chats with the same installed package and the same
short command. Do not change code, prompts, input cleanup, semantic ownership,
projection, renderer policy, or candidate disposition between those runs. The
stability verdict requires the same five-outcome boundary partition, no extra
operator checkpoint, and compatible terminal/deferred/draft dispositions.
Langfuse comparable export remains deferred until that gate is complete.

#### Regenerated-Input Canary N=2 Pre-Route Ref Normalization Failure

The fresh N=2 chat did not enter the authoring pipeline. The client reported
that the clean ticket was absent under a numeric ref. Local adapter lookup
confirmed that the canonical prefixed ref and its hash-bound metadata were
present and valid, while the stripped numeric ref returned
`approved_ticket_summary_not_found`. N=2 is therefore invalid as a semantic or
disposition canary and must not be compared with N=1.

Treat this as a Desktop handoff compatibility defect. The operator command
already supplied the canonical prefixed ref, but the client normalized it
before the tool call. Preserve the explicit model instruction to copy refs
exactly. Add a deterministic adapter fallback only for a bare numeric ref when
the exact bare ref is absent and the corresponding canonical `ticket-<number>`
artifact exists. Exact refs retain precedence; arbitrary aliases are not
invented.

Do not change the clean-ticket producer, stored artifact, semantic ownership,
issue boundaries, projection, renderer policy, candidate disposition, or
Langfuse export. Restart N=2 only after focused ref-resolution tests, the full
deterministic suite, package rebuild/install, and source/installed stdio smoke
pass.

#### Regenerated-Input Canary N=2 After Ref-Resolution Fix

The fresh installed run on `ee29940` entered the normal authoring route and
completed the Python-owned batch without an extra operator checkpoint. The
pre-route compatibility defect is therefore closed.

The semantic stability gate failed. N=1 produced five outcomes with one
reviewer-only draft and four deferred outcomes. N=2 produced four outcomes
with one reviewer-only draft, one deferred outcome, and two terminal blocked
outcomes. One expected pair of independently searchable identities was merged,
and a previously evidence-incomplete identity changed to draft disposition.
Selection, fail-closed handling, reviewer-only output, and publication safety
remained intact, but candidate identity and per-candidate disposition did not.

Reject stability at N=2. Do not run N=3 on the unchanged package, do not export
this pair as comparable Langfuse runtime outcomes, and do not add another
prompt-only merge/split rule. The next investigation must localize the
model-visible semantic ownership boundary and compare the accepted proposals
before deterministic projection and rendering. Any successor change requires
its own falsification gate and a newly installed package.

#### N=2 Accepted-Proposal Ownership Localization

The exact value-safe projection of the accepted N=2 submission contained four
model-created issues. All four were projected as selectable draft candidates
before the downstream authoring gates ran. The merged identity was already
present in the submitted proposal: one issue owned two disjoint supported
cause/resolution source groups that represent independently searchable
outcomes. Python did not merge two accepted issues after submission.

The active boundary contract already says to split different supported
cause/resolution pairs and not to merge distinct issues merely to complete an
evidence shape. Do not add another equivalent prompt rule or a deterministic
post-proposal semantic split.

A local value-safe preparation audit found a model-visible speaker block of
5,903 bytes containing 41 original paragraphs and evidence from multiple issue
threads. The same packet can therefore preserve exact customer wording while
still presenting an overly broad ownership unit. This is a contributing input
granularity defect, not proof that source-block size alone caused the model
variance: the same installed packet produced a different partition at N=1.

Naive byte-bound reduction is rejected as the next change. Tested bounds
increased the packet from 28 excerpts to 30-41 excerpts and did not reduce the
number of multi-thread chunks. A paragraph-preserving prototype reduced mixed
chunks more effectively but approached the active 48-excerpt cap at its narrowest
bound. It remains an inactive hypothesis.

The only authorized successor investigation is an offline, paragraph-
preserving preparation falsification that retains exact contiguous source text
and inherited speaker ownership. It must define excerpt-count headroom,
byte-for-byte coverage, speaker retention, and multi-thread-block reduction
before any Desktop runtime activation. Candidate projection, disposition,
renderer policy, operator checkpoints, and Langfuse export remain unchanged.

#### Paragraph-Preserving Preparation Falsification Result

The offline paragraph-preserving hypothesis is rejected before runtime code.
The active source-ref cap is 48. A 500-byte target produced 63 chunks and a
750-byte target produced 49, so both exceed the active contract. A 1,000-byte
target fit at 42 chunks but retained three multi-thread chunks and increased
the model-visible inventory from 28 to 42. A 1,500-byte target fit at 34 chunks
but retained the same aggregate multi-thread count as the current packet.
Speaker ownership and byte coverage stayed intact in the prototype.

Only two approved local artifacts matched the recognized transcript shape, so
the store audit does not provide broader generalization evidence. More
importantly, oversized-turn sentence segmentation and continuation-speaker
preservation were already installed and failed the unchanged-package semantic
stability gate. Paragraph grouping is another representation of the same
evidence, not a new semantic authority source.

Do not implement or install paragraph chunking, another source-ref topology
guard, or another unchanged-package canary from this result. The experimental
runtime/test diff was removed uncommitted and the worktree returned to the
recorded grouped baseline.

#### Component Audit Architecture Verdict

For a fixed accepted proposal, Python validation, projection, native
selection, batch accounting, evidence building, decision, renderer, and
reviewer-only writes are deterministic. They do not merge or split submitted
issues. Downstream completeness, safety, reuse, and renderer blockers affect
candidate disposition after identity exists; they do not explain the N=2
identity merge.

The current model-visible contract assigns issue count, grouping, field
assignment, and cause/resolution pairing to a fresh LLM call. The contract
already contains the required split rule, yet N=1 and N=2 produced different
accepted partitions from the same approved input and installed package. Python
cannot distinguish an incorrectly merged pair from a legitimate compound
cause or multi-step repair because the accepted packet contains no independent
semantic authority.

The current requirements cannot jointly guarantee stable issue identity:

1. a fresh nondeterministic model call exclusively owns semantic boundaries;
2. Python must not infer or repair semantic identity;
3. the operator must not receive a boundary-review checkpoint;
4. no authoritative structured issue scope exists upstream;
5. repeated runs must return the same candidate identities and dispositions.

No further KCS-14.5 runtime implementation is authorized under all five
constraints. Reopening requires a behavior-change design that names a genuinely
new authority source: authoritative structured upstream issue scope, explicit
operator scope at workflow entry, or deterministic existing-knowledge
identity. Caching or replaying the first model proposal can provide runtime
idempotency but does not prove semantic correctness and must not be reported as
semantic stabilization. A historical rollback also remains unproven and is
not a known-good comparison endpoint.

#### Real-Ticket Complexity Falsification And Selection-Handoff Incident

An unchanged installed package completed three fresh-chat runs for a sanitized
single-issue canary. Every run produced one reviewer-only `technical_scr` draft
with `recommended_action=draft_only`, reuse search skipped, KCS readiness false,
and public output prohibited. No semantic-boundary, schema-correction, or
operator-selection loop appeared. This is evidence that the ordinary
real-ticket authoring route is not generally broken. It does not prove
multi-issue semantic stability or reuse behavior.

A separate sanitized real-tone canary reached semantic review and
separated one draft-eligible item from an evidence-incomplete item. The exact
structured result contained the two `semantic_item_outcomes`, but contained no
`item_candidates`, `operator_choice_request`, `next_tool`, or `next_arguments`.
The client nevertheless invented an operator-selection checkpoint and then
made invalid follow-up calls. Do not classify this as a semantic-boundary or
Python selection-handoff failure and do not retry the ticket to obtain a
different proposal.

The installed adapter files and the current worktree files were byte-identical
for the draft tool, selection helper, tool schema, ticket-ref adapter, and tool
result renderer. The failure is therefore not explained by a stale installed
package. The primary incident is client misinterpretation of a diagnostic
semantic-outcome ledger as an actionable choice. Static contract inspection
also found two secondary deterministic inconsistencies that amplified the
invented recovery path:

1. `kcs_draft_article` runtime selection requires
   `operator_selection_ref` together with exactly one of
   `operator_selected_item_ref` or `operator_selected_item_refs`, but its MCP
   input schema permits either field to be submitted alone. The failed client
   sequence exercised both invalid partial shapes.
2. Clean-ticket registration and related recovery prose direct the client to
   call `kcs_draft_article` with `ticket_ref`, while the published
   `kcs_draft_article` input schema does not expose `ticket_ref`; the dedicated
   `/draft <ticket_ref>` tool is `kcs_draft_ticket`.

The configured clean-ticket storage hint is also included in the registration
result. Treat whether that local hint belongs in model-visible registration
status as a separate data-boundary review; it did not cause the invented
selection checkpoint.

Any correction must first make the terminal authoring presentation explicit:
`semantic_item_outcomes` are a diagnostic ledger and cannot authorize another
tool call; operator selection exists only when the result carries the native
choice contract. Add an executable result-presentation test for one
draft-eligible outcome plus one evidence-incomplete outcome. Secondary
hardening may then require every advertised selection/recovery payload to be
accepted unchanged by its advertised tool. Do not change semantic extraction,
source blocks, issue projection, candidate disposition, or Langfuse export for
this incident.

The first correction is implemented locally in the tool-result presentation
layer. A terminal blocked `draft_article_authoring` result with no next action
now states that no operator selection or further tool action exists and that
`semantic_item_outcomes` are diagnostic only. Structured content, authoring
decisions, semantic outcomes, safety gates, and publication state are
unchanged. The exact incident shape is covered by a regression test; the full
Desktop MCP adapter test file passes. Package rebuild/install and one fresh
real-tone canary remain required before runtime promotion.

#### Real-Tone Canary After Terminal-Presentation Fix

The rebuilt package passed the installed stdio smoke and the fresh real-tone
run demonstrated that the presentation correction works: after the native
batch completed with terminal blockers, the client stated that no operator
action was available and did not invent another selection or recovery call.

The semantic stability gate nevertheless failed on the second fresh model
call. Before the presentation fix, the accepted result classified one item as
`candidate_allowed` and one as `blocked_need_more_evidence`; no native choice
contract existed. With unchanged semantic code and the same approved input,
the next run surfaced both identities as selectable candidates and allowed an
`all` batch. Downstream Python authoring blocked both candidates and preserved
the no-publish boundary, but the selectable/blocked semantic disposition had
already changed before authoring.

Stop this canary at N=2. Do not run N=3 and do not add another semantic prompt,
projection, completeness, or renderer patch. Combined with the three stable
single-issue real-ticket runs, this narrows the supported behavior: noisy
single-issue authoring is stable in the observed sample, while real multi-issue
classification remains nondeterministic even when the ticket is not the
original extreme-complexity canary. Raw ticket length alone is not the failure
condition; ambiguous multi-issue semantic ownership remains the active limit.

#### Contract Consolidation After The Stability No-Go

KCS-14.5 contract consolidation is part of closing KCS-14.5, not a new KCS-15
feature. A wholesale rollback to KCS-14 closeout remains disallowed because
that revision was not proven as a comparable working runtime and would discard
retained data-integrity, sibling-preservation, grounding, safety, and terminal
presentation fixes.

The first consolidation batch retires `semantic_claim_ownership_v1` from
production code. The flat claim/direct-anchor experiment is already recorded
as rejected and reverted, its projector has no runtime or packaging caller,
and its tests exercise only that inactive contract. The experiment design,
canary verdict, aggregate review, and Git history remain available as research
evidence. The freeze rule that rejects claim ownership on the active semantic
submit surface remains active.

This deletion does not authorize removal of the grouped
`semantic_issue_proposal_v1` path, legacy compatibility payloads, shadow
comparison tools, Langfuse diagnostics, or incident characterizations. Those
surfaces require a separate consumer and reachability inventory before any
later deletion batch.

The C2 inventory found one additional inactive compatibility seam:
`ApprovedSemanticExtractionClient` and `ApprovedSemanticExtractionProvider`.
No environment route, runtime caller, packaged consumer, script, or test
constructs either object; the only consumers were their own exports from
`desktop_semantic_providers` and aliases in `desktop_workflow`. They were a
future external-provider placeholder and are retired in C3. The active local
approved-summary provider, fixture provider, unavailable-provider behavior,
provider environment values, and core `SemanticExtractionProvider` protocol
remain unchanged. Any future external provider must be introduced as a new
reviewed adapter slice rather than preserved as unused production scaffolding.

The final production-symbol audit removed three private helpers with no source,
script, package, or test caller: `_batch_followup_group_line`,
`_string_array_schema`, and
`_validate_validation_report_metadata_string`. Helpers called by active code or
an explicit incident characterization remain. This establishes the safe
consolidation boundary: no additional production deletion is authorized by the
current reachability evidence. Rebaseline/Langfuse retirement, legacy provider
contract removal, selection compatibility changes, or characterization-test
removal each require their own later behavior or tooling decision.
