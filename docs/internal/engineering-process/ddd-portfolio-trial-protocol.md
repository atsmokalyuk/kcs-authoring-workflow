# DDD Portfolio Trial Protocol

Status: authoritative cross-project trial orchestration for the candidate
Discovery-Design-Delivery ruleset.

## Purpose

Ensure that external projects monitor the complete imported candidate
portfolio and field-test genuinely triggered rules through one consistent
protocol. This protocol complements the per-rule portability lifecycle in
`engineering-rule-portability.md`; it does not weaken its evidence gates or
make field evidence the only possible kit treatment.

The separate source-owned standards and universal-core disposition is recorded
in `ddd-universal-core-standards-crosswalk.md`. A standards-backed shadow or
reference-only kit treatment does not create historical trial evidence or move
a candidate on the portability ladder.

## Two Trial Levels

Each external project keeps one portfolio campaign and zero or more per-rule
Trial Contracts:

```text
portfolio campaign
  = monitors every imported rule and routes genuine triggers

per-rule Trial Contract
  = predeclares evidence for one exact rule formulation when its trigger exists
```

A campaign never makes every rule active. It prevents rules from disappearing
merely because a project did not create a contract before the first relevant
task.

## Canonical Local States

| State | Meaning |
| --- | --- |
| `monitored` | Imported rule is checked for a genuine trigger on material work |
| `proposed-local-trial` | Exact contract is prepared, but its trigger or evidence collection has not started |
| `active-local-trial` | Genuine trigger exists and predeclared evidence collection has started |
| `complete-local-trial` | Local evidence and a per-rule verdict are closed |
| `paused-local-trial` | Trigger existed, but a named blocker prevents further evidence collection |
| `not-applicable` | Reviewed project boundary excludes the rule, with rationale |
| `retrospective-evidence` | Real earlier use is preserved without claiming prospective activation |

These are external-project workflow states, not portability statuses.
`external-trial-active` and all later portability states remain source-owned.

## Campaign Manifest

Every external campaign records:

- campaign ID and state;
- exact source repository revision;
- project and feature classes;
- current-stage authority;
- all imported Rule IDs;
- per-rule local state and Trial Contract ID;
- evidence and feedback locations;
- privacy and provenance boundary;
- activation and closeout reviewer;
- confirmation that target-local state cannot change upstream status.

Every imported rule must remain visible as `monitored`, `not-applicable`,
`retrospective-evidence`, or through a Trial Contract state. Absence from the
campaign is an evidence-coverage defect.

## Per-Rule Activation Gate

Before changing one rule to `active-local-trial`, the external record must:

1. identify a genuine current material task and observable trigger;
2. name the exact Rule ID and source revision;
3. contain all nine External Trial Contract fields;
4. separate project-neutral invariant from the target-local binding;
5. declare required evidence before the remaining rule-owned decision or work;
6. name decision authority and failure or stop behavior;
7. mark earlier evidence as retrospective context;
8. begin collecting at least one declared evidence item.

Import, role assignment, general project activity, or possible future work is
not activation. Several rules may activate on one material task, but each keeps
its own contract, decision impact, overhead, false-positive assessment,
limitations, and verdict. Shared validation and provenance artifacts may be
referenced without duplicating their contents.

## Retrospective Admission

A completed or ongoing material use that predates this protocol may be retained
as `retrospective-evidence` when contemporaneous artifacts establish the task,
rule semantics exercised, decision impact, validation, and limitations.
Missing fields remain `unknown`; they are not reconstructed from chat.

Retrospective evidence cannot create a historical `active-local-trial` or
`external-trial-active` state. The source may use it in a later cross-project
and extraction-readiness review when contemporaneous records establish the
exact rule semantics, decision effect, validation, corrections, overhead,
false positives, and limitations across materially different contexts. The
absence of a prospective contract remains a limitation, but it is not an
automatic demand to repeat completed work. A new prospective trial is required
only when source review identifies a material unresolved applicability,
formulation, effect, or overhead question. Missing fields are never
reconstructed to satisfy this gate.

## Source-Owned Status Review

The authoritative source may move a candidate to `external-trial-active` only
after verifying an external `active-local-trial` contract and actual evidence
collection. The source records the project, contract ID, exact source revision,
feature class, evidence location, review date, limitations, and next gate.

Completion does not promote automatically. `cross-project-evidence-recorded`
requires the substantive evidence defined in `engineering-rule-portability.md`
and a source-owned review of decision impact, corrections, overhead, false
positives, and limitations across materially different contexts.

## Portfolio Closeout And Export

Before extraction review, every rule receives a reviewed portfolio disposition:

- retain for another trial;
- cross-project evidence recorded;
- project-specific;
- human-owned;
- platform-owned;
- redundant;
- reject;
- explicitly outside kit scope;
- evidence gap.

The toolkit export contains only separately approved generic assets. A rule is
not exported merely because it was imported, monitored, locally mandatory, or
tested once. A standards-backed shadow asset must remain visibly distinct from
a field-evidence beta asset and cannot claim
`cross-project-evidence-recorded`. The selected set must still pass the
end-to-end integration gate owned by the separate toolkit project.

## Current Campaigns

| Campaign | Project class | Source revision under test | Local state | Formal rule states | Source status effect |
| --- | --- | --- | --- | --- | --- |
| `DDD-LED-CAMPAIGN-01` | Greenfield scientific feasibility and controlled physical evidence | `d1c6f6d1af8442ce704cf57c07a28ec4ed6aec66` | active monitoring; D-213/Checkpoint 145 preserve the eight-contract campaign and independently pause the three contracts blocked by the absent physical event | active: `ENG-PORT-DISC-002`; `ENG-PORT-DES-004`, `007`; `ENG-PORT-DEL-008`, `012`; paused: `ENG-PORT-DISC-003`; `ENG-PORT-DES-001`; `ENG-PORT-DEL-006` | the pause is not a failed experiment, local closeout, or upstream verdict; all source-owned portability statuses remain unchanged |
| `DDD-AIE-CAMPAIGN-01` | API engineering toolkit implementation and reference-project evaluation | `d1c6f6d1af8442ce704cf57c07a28ec4ed6aec66` | active monitoring of all 30; the Pack is adopted and no exact unfinished task is active | none; two future contracts are proposed; RP-B9 and `ENG-PORT-DEL-010` evidence are retrospective | target records change no status; source reviews in `pre-kcs-16-ddd-evidence-review.md` own later dispositions |
| `DDD-PS-CAMPAIGN-01` | Existing support-tool material integration and privacy-sensitive external feasibility | `d1c6f6d1af8442ce704cf57c07a28ec4ed6aec66` | active monitoring; GG-006 at `60acfecc401c8080483eaac11890082e175b0bc4` records pre-implementation rule evidence, while exact capability and Design approval remain blocked | active: `ENG-PORT-DISC-002`, `006`; `ENG-PORT-DES-001`, `002`, `007`, `011`; `ENG-PORT-DEL-008`; paused: `ENG-PORT-DEL-007` | local contracts remain active; source reviews independently promote `ENG-PORT-DISC-006`, `ENG-PORT-DES-002`, and `ENG-PORT-DES-011` without claiming operational closeout |
| `DDD-UT-CAMPAIGN-01` | Completed standalone engineering-Discovery investigation with bounded deterministic, agent-mediated, and hidden-holdout comparisons | `d1c6f6d1af8442ce704cf57c07a28ec4ed6aec66` | closed retrospective review under terminal decision 0077 | none; qualifying prior use is retrospective only | no automatic change; value-safe evidence is eligible for source review |

Target projects own their local bindings and evidence. This source owns the
campaign inventory, portability review, extraction decision, and export
boundary.

## Source-Owned Trial Intake

### SR-LED-PAUSE-145

- **Review date:** 2026-08-13.
- **Rules and revision:** `ENG-PORT-DISC-003`, `ENG-PORT-DES-001`, and
  `ENG-PORT-DEL-006` at
  `d1c6f6d1af8442ce704cf57c07a28ec4ed6aec66`.
- **External identity and evidence:** LED reports `Git unavailable`; D-213,
  Checkpoint 145, the eight-contract validator, and the value-safe packet at
  `LED/docs/internal/portability-evidence/kcs-source-review-packet-checkpoint-145.md`
  consistently record the local state transition. The source independently
  confirmed the exact eight-contract revision with the LED structural
  validator.
- **Observed blocker:** no traceable physical sample identity, manufacture
  record, instrument and measurement context, observed coordinates,
  measurement-file references, or named measurement and chief-technologist
  review exists. No synthetic, fixture, blank-form, or deterministic result
  was admitted as the physical outcome.
- **Local disposition:** `ETC-LED-DISC-003-r1`, `ETC-LED-DES-001-r1`, and
  `ETC-LED-DEL-006-r1` are independently `paused-local-trial`; the other five
  LED contracts remain active. The absence of the event is not a physical
  `FAIL`, a completed local trial, or a per-rule verdict.
- **Corrections and limitations:** two stale LED binding filenames were
  corrected without changing the experiment, gate, rule formulation, or
  authority boundary. Physical behavior, decision impact after observation,
  stakeholder effort, and each final
  `retain/revise/reject/propose-for-extraction-review` verdict remain unknown.
- **Source disposition:** retain `external-trial-active` for all three exact
  rules. A paused external workflow state does not silently demote or promote
  the source-owned portability status, and this intake provides no extraction
  authority.
- **Resume gate:** require the already authorized item's identity and frozen
  proposal linkage; manufacture record and deviations; instrument, context,
  and measurement provenance; authentic observed coordinates and local file
  references; named measurement and chief-technologist review; and effort when
  known. A different item, input, condition, criterion, or contract revision
  requires a new or revised prospective contract rather than closure of r1.

### SR-PS-GG006-60ACF

- **Review date:** 2026-08-13.
- **Rules and source formulation:** `ENG-PORT-DISC-006`,
  `ENG-PORT-DES-002`, and `ENG-PORT-DES-011` at
  `d1c6f6d1af8442ce704cf57c07a28ec4ed6aec66`.
- **External identity and evidence:** `plesk_support` commit
  `60acfecc401c8080483eaac11890082e175b0bc4` durably contains the three exact
  contracts, detailed GG-006 record, corrected Design map, value-safe source
  packet, and structural policy test. The detailed record describes the
  inspected parent snapshot `73234ca9`; the enclosing evidence commit is
  independently verified here and does not rewrite that recorded baseline.
- **Validation:** the source reran the committed structural evidence test and
  observed `5 passed`. The external handoff also records `75 passed, 102
  subtests passed` for its focused suite. Three unrelated untracked local files
  are outside the evidence commit and were not admitted.
- **`ENG-PORT-DISC-006` disposition:** `retain`. Exact output-validation
  capability remains `UNKNOWN`; generic health, imported schema, fixture, and
  catalog evidence do not prove the required operation. The dependent Design
  and egress remain stopped.
- **`ENG-PORT-DES-002` disposition:** `retain`. The trial found a concrete
  conflict between the proposed narrow egress and the current no-egress
  authority before implementation, while the declared adjacent contracts
  remained unchanged.
- **`ENG-PORT-DES-011` disposition:** accept the local `revise` decision for
  the target Design, not for the upstream formulation. Executable direct
  finalization and manual-backfill paths bypass the proposed semantic-review
  dependency, so the target claim was correctly narrowed to a future
  server-bound main-finalization gate covering both write targets. The current
  generic rule already requires supported-entrypoint mapping and claim
  restriction when reachability is not guaranteed; no KCS-16a wording change
  is justified by this intake.
- **Initial source disposition:** retain `external-trial-active` while checking
  whether incomplete local contracts blocked promotion. Operator review then
  identified that all three rules materially helped, and the source re-read the
  authoritative gate: local completion is not required when substantive
  cross-project evidence is already recorded. The independent promotion
  decisions are in `SR-DISC006-01`, `SR-DES002-01`, and `SR-DES011-01` below.
- **Prospective local gates:** `ENG-PORT-DISC-006` still requires the configured staging
  target and project, confirmed blocking output-PII subscription, and one
  bounded smoke of the exact output-validation operation. `ENG-PORT-DES-002`
  requires the final authorized Design disposition and independent local
  closeout after the changed/unchanged boundary is resolved.
  `ENG-PORT-DES-011` requires approval and closeout of the corrected
  entrypoint/gate map, with final overhead, false-positive, limitation, and
  verdict evidence. Any future runtime-enforcement claim requires its own
  proportional proof.

### SR-PS-CAMPAIGN-AUDIT-60ACF

- **Review date and authority:** 2026-08-13; operator-authorized source audit
  of the complete `DDD-PS-CAMPAIGN-01` snapshot in `plesk_support` commit
  `60acfecc401c8080483eaac11890082e175b0bc4`.
- **Already extracted rules:** `ENG-PORT-DISC-001`, `ENG-PORT-DISC-002`,
  `ENG-PORT-DES-004`, `ENG-PORT-DES-007`, and `ENG-PORT-DEL-008` receive
  prospective usefulness or limitation evidence only. Nothing in GG-006
  contradicts their wording, source reviews, authority boundaries, or open
  limitations, so no status or formulation change is required.
- **`ENG-PORT-DES-001`:** retain `external-trial-active`. Its exact prospective
  contract and acceptance map exist, but the committed snapshot does not
  attribute a separate per-rule decision effect, correction, overhead, false
  confidence, limitations, and local verdict. Those fields must not be inferred
  from shared campaign records or the three-rule GG-006 packet.
- **`ENG-PORT-DEL-007`:** advance from `portability-candidate` to
  `external-trial-active`. `ETC-PS-DEL-007-r1` names the exact source revision,
  trigger, generic invariant, authority, stop behavior, required evidence, and
  enforcement type. Evidence collection genuinely began: the approved
  synthetic fixture was withheld before send because destination purpose,
  project/subscription, and retention/capability evidence remained unresolved,
  and the contract is explicitly `paused-local-trial` at that safe no-send
  baseline.
- **`ENG-PORT-DEL-007` limitations and next gate:** the fixture was not sent,
  no external privacy or runtime result exists, shared campaign checkpoints do
  not provide an independent per-rule verdict or complete corrections,
  overhead, false-positive, and limitation record, and standards alignment is
  not promotion evidence. Resume only within an approved destination and
  purpose boundary with exact project/subscription and retention evidence;
  independently close the per-rule fields before any
  `cross-project-evidence-recorded` review.
- **Other rules:** `ENG-PORT-DISC-004` remains retrospective reference guidance
  with timing and burden unknown. All monitored rules remain at their current
  source statuses because monitoring or possible future applicability is not a
  triggered exact trial. `ENG-PORT-DES-005` and `ENG-PORT-DEL-005` remain
  project-local and outside the universal core.
- **Source boundary:** this audit neither changes external local states nor
  claims implementation, exact runtime capability, fixture acceptance, local
  completion, or KCS-17 authorization.

## Source-Reviewed Cross-Project Evidence

The authoritative pre-KCS-16 intake and per-rule source dispositions are in
`docs/internal/engineering-process/pre-kcs-16-ddd-evidence-review.md`.
The following reviews establish cross-project evidence and move exact rules to
`extraction-review-ready`: `SR-DISC001-01`, `SR-DISC002-01`,
`SR-DES004-01`, `SR-DES007-01`, `SR-DES010-01`, `SR-DEL008-01`,
`SR-DEL011-01`, `SR-DEL012-01`, `SR-DISC006-01`, `SR-DES002-01`, and
`SR-DES011-01`. The status permits KCS-16 consideration; it does not approve
extraction or skip a triggered KCS-16a stabilization.

### SR-DISC006-01

- **Review date and revision:** 2026-08-13;
  `ENG-PORT-DISC-006` at
  `d1c6f6d1af8442ce704cf57c07a28ec4ed6aec66`.
- **KCS context:** KCS-15.2b1 corrected a dependent design after the assumed
  exact runtime path was absent; a neighboring capability could not substitute
  for the required operation.
- **External context:** `plesk_support` GG-006 stopped Design and egress when
  generic health, imported schema, and catalog evidence could not prove the
  exact output-validation operation in its configured operating condition.
- **Material effect and difference:** one context corrected a stale exact-path
  assumption after integration work; the other prevented substantial work
  before implementation while external configuration and capability remained
  unknown. Both exercised the same prove-or-stop invariant through different
  products and lifecycle points.
- **Corrections, overhead, and false positives:** KCS required an endpoint and
  planning correction. GG-006 required one presence/configuration audit,
  schema-versus-runtime classification, and source review; duration is unknown
  and zero false positives were observed. It avoided an unsafe fixture send and
  nominal-evidence promotion.
- **Limitations:** the external exact operation remains unexecuted, target
  configuration and subscription are absent, and no runtime usefulness beyond
  the stop decision is claimed.
- **Source disposition:** `extraction-review-ready`, then KCS-16
  `extracted-beta`. The open exact-path smoke remains prospective refinement,
  not a prerequisite to repeat the already observed cross-project decision
  effect.

### SR-DES002-01

- **Review date and revision:** 2026-08-13; `ENG-PORT-DES-002` at
  `d1c6f6d1af8442ce704cf57c07a28ec4ed6aec66`.
- **KCS context:** KCS material slice plans and staged review declare intended
  changes, locked phases, and unchanged product/data boundaries. In KCS-16 the
  contract kept KCS-17 assembly, external repositories, runtime behavior, and
  project-local rules outside the authorized diff.
- **External context:** `plesk_support` GG-006 declared a narrow egress and
  main-path change plus adjacent unchanged workflows, then found the current
  no-egress authority directly conflicted with that intended change before
  implementation.
- **Material effect and difference:** one context bounded an authoritative
  ruleset extraction across repository and phase boundaries; the other stopped
  a privacy-sensitive integration because its target policy contradicted the
  proposed change. Both made the changed/unchanged contract operational rather
  than documentary.
- **Corrections, overhead, and false positives:** KCS used one durable plan,
  deterministic scope checks, and staged review. GG-006 retained an explicit
  policy-and-test change and rejected a broader exception; review duration is
  unknown and zero false positives were observed.
- **Limitations:** final external Design authority, implementation drift, and
  measured reviewer minutes remain open; concrete policy values and product
  contracts remain target-owned.
- **Source disposition:** `extraction-review-ready`, then KCS-16
  `extracted-beta`. The active external contract may still measure downstream
  drift and overhead without blocking the portable boundary already shown.

### SR-DES011-01

- **Review date and revision:** 2026-08-13; `ENG-PORT-DES-011` at
  `d1c6f6d1af8442ce704cf57c07a28ec4ed6aec66`.
- **KCS context:** KCS-15.2b2 exposed alternate host actions that could bypass
  a guarded connector, forcing the claimed privacy enforcement boundary to be
  narrowed instead of treating model routing as deterministic enforcement.
- **External context:** `plesk_support` GG-006 mapped supported entrypoints and
  found executable direct-finalization and manual-backfill paths that bypassed
  the proposed semantic-review dependency; the target Design was narrowed to a
  future server-bound gate covering both supported write targets.
- **Material effect and difference:** one context spans host/model/tool routes;
  the other spans application API, workflow, and CLI write paths. Each found a
  materially different bypass and changed the supported claim before Delivery.
- **Corrections, overhead, and false positives:** both contexts required an
  entrypoint inventory and Design correction. GG-006 used a source call-graph
  review and focused tests; duration is unknown and its two bypasses were
  executable supported paths, with zero known false positives.
- **Limitations:** no future server gate or corporate runtime capability is
  proven; adapter-owned entrypoints and enforcement mechanisms remain local.
- **Wording review:** the current generic formulation already requires mapping
  supported entrypoints, treating model-controlled behavior as non-enforcement,
  and restricting a claim when reachability is not guaranteed. The new evidence
  requires no wording change.
- **Source disposition:** `extraction-review-ready`, then KCS-16
  `extracted-beta`. Future enforcement proof remains proportional prospective
  evidence rather than a prerequisite for extracting the demonstrated Design
  invariant.

### SR-DEL010-01

- **Review date:** 2026-08-12.
- **Rule and revision:** `ENG-PORT-DEL-010` at
  `d1c6f6d1af8442ce704cf57c07a28ec4ed6aec66`.
- **Source context:** the KCS installed text-recovery workflow exposed duplicate
  model submissions, stale-reference interference, and rejected-shape state
  loss. The bounded correction defined deterministic replay/no-op, conflict,
  pending-operation preservation, and ref ownership behavior with focused
  tests. Historical timing is not isolated and remains unknown.
- **External context:** AI Engineer record `DDD-RETRO-AIE-DEL010-01` applies the
  same generic retry/replay/idempotency invariant to API-contract evaluation.
  It retained material concurrency/retry unknowns while preventing unsupported
  ETag, precondition, idempotency-key, replay-cache, and TTL requirements.
- **Material difference:** one context corrects a stateful model/tool runtime
  after duplicate and rejected submissions; the other constrains a toolkit
  evaluating API mechanisms without selecting product policy.
- **Corrections and overhead:** KCS required bounded runtime/state corrections
  and tests. AI Engineer required compact applicability matrices, later
  compensating revalidation after loss of the original RP-B3 packet, and human
  provenance disposition; historical minutes/cost were not reconstructed.
- **False positives avoided:** the API context did not impose mutation
  mechanisms on retrieval operations or manufacture absent retry guarantees;
  the KCS context did not turn prompts into deterministic retry enforcement.
- **Limitations:** the external use was retrospective, PUT runtime retry and
  concurrency behavior was not executed, the original RP-B3 packet remains
  lost, and no prospective `DDD-AIE-DEL010-02` evidence exists yet.
- **Source disposition:** `extraction-review-ready`; the review first satisfies
  `cross-project-evidence-recorded` and then finds the evidence sufficient for
  KCS-16 consideration under the retrospective-admission rule above.
- **Next gate:** retain the prospective AI Engineer contract for unresolved
  runtime applicability evidence, and use KCS-16a to confirm
  mechanism-neutral wording before any extraction decision. No repeated trial
  is required solely to recreate a prospective timestamp.
