# DDD Portfolio Trial Protocol

Status: authoritative cross-project trial orchestration for the candidate
Discovery-Design-Delivery ruleset.

## Purpose

Ensure that external projects field-test the complete candidate portfolio
through one consistent protocol before generic extraction or toolkit export.
This protocol complements the per-rule portability lifecycle in
`engineering-rule-portability.md`; it does not weaken its evidence gates.

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
`external-trial-active` state. The source may use it as supporting evidence in
a later cross-project review, but retrospective evidence alone cannot make a
rule `extraction-review-ready`.

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
tested once. The extracted set must still pass the end-to-end integration gate
owned by the separate toolkit project.

## Current Campaigns

| Campaign | Project class | Source revision under test | Local state | Formal active rules | Source status effect |
| --- | --- | --- | --- | --- | --- |
| `DDD-LED-CAMPAIGN-01` | Greenfield scientific feasibility and controlled physical evidence | `d1c6f6d1af8442ce704cf57c07a28ec4ed6aec66` | active monitoring | `ENG-PORT-DISC-002`, `003`; `ENG-PORT-DES-001`, `004`, `007`; `ENG-PORT-DEL-006`, `008`, `012` | source-reviewed `external-trial-active` |
| `DDD-AIE-CAMPAIGN-01` | API engineering toolkit implementation and reference-project evaluation | `d1c6f6d1af8442ce704cf57c07a28ec4ed6aec66` | active monitoring of all 30; no exact unfinished task trigger at baseline | none; two future contracts are proposed and `ENG-PORT-DEL-010` has retrospective evidence | `ENG-PORT-DEL-010` separately source-reviewed to `cross-project-evidence-recorded` by `SR-DEL010-01`; no other automatic change |
| `DDD-PS-CAMPAIGN-01` | Existing support-tool material integration and privacy-sensitive external feasibility | `d1c6f6d1af8442ce704cf57c07a28ec4ed6aec66` | active monitoring; implementation not started and an external capability blocker remains | `ENG-PORT-DISC-002`, `006`; `ENG-PORT-DES-001`, `002`, `007`, `011`; `ENG-PORT-DEL-008`; `ENG-PORT-DEL-007` is paused | source-reviewed active contracts affect exact rules only; no automatic completion or cross-project promotion |
| `DDD-UT-CAMPAIGN-01` | Completed standalone engineering-Discovery investigation with bounded deterministic, agent-mediated, and hidden-holdout comparisons | `d1c6f6d1af8442ce704cf57c07a28ec4ed6aec66` | closed retrospective review under terminal decision 0077 | none; qualifying prior use is retrospective only | no automatic change; value-safe evidence is eligible for source review |

Target projects own their local bindings and evidence. This source owns the
campaign inventory, portability review, extraction decision, and export
boundary.

## Source-Reviewed Cross-Project Evidence

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
- **Source disposition:** `cross-project-evidence-recorded`.
- **Next gate:** retain the prospective AI Engineer contract and obtain one
  source-reviewed closeout with rule-owned overhead/correction measurements
  before any `extraction-review-ready` decision. This retrospective review
  cannot satisfy that later gate by itself.
