# Engineering Rule Portability

Status: authoritative portability lifecycle, candidate registry, and KCS-16
extraction dispositions.

Date: 2026-08-13

## Purpose

This document separates three questions that were previously easy to conflate:

1. What kind of engineering work does a rule govern?
2. How strongly is the rule enforced inside one repository?
3. How much evidence shows that the rule is portable across projects?

Recording a candidate does not authorize reusable extraction, shared
infrastructure, agent-role packaging, orchestration, or a runtime behavior
change.

## Rule Families

| Family | Question answered | Typical evidence |
| --- | --- | --- |
| Discovery | How do we understand an unfamiliar domain and the real user problem? | stakeholder answers, current-workflow model, domain constraints, baseline, bounded hypothesis, experiment result, correction log |
| Design | How do we turn confirmed understanding into a controlled system? | contracts, ownership, workflow, architecture options, acceptance criteria, unchanged boundaries |
| Delivery | How do we implement, validate, operate, and improve the system? | controlled slices, tests, evaluation, CI, observability, drift review, review packets, closeouts |

These families are sequential for a feature, but their rules mature
independently. A mature Delivery check does not compensate for missing
Discovery evidence, and a good Discovery question does not prove an
implementation safe.

## Two Independent Ladders

### Enforcement Ladder

The enforcement ladder describes strength inside one repository:

```text
review finding or note
  -> checklist or review gate
  -> deterministic test or tool where mechanically honest
  -> structural ownership/type boundary where practical
```

Judgment-based rules may remain permanent review gates. They are not weaker
merely because a deterministic check cannot assess them honestly. The
authoritative local promotion registry is
`docs/internal/engineering-process/promotion-candidates.md`.

### Portability Ladder

The portability ladder describes evidence across contexts:

```text
project-local
  -> portability candidate
  -> external trial active
  -> cross-project evidence recorded
  -> extraction review ready
  -> extracted beta
  -> role-integrated beta
  -> integration gate passed
  -> kit ready
```

Definitions:

- `project-local`: useful in one repository; portability is untested.
- `portability-candidate`: generic formulation appears possible, but a second
  context has not supplied enough auditable evidence.
- `external-trial-active`: another project or independent subsystem has a
  tracked record that names the rule ID and revision and is collecting the
  required evidence.
- `cross-project-evidence-recorded`: at least two materially different
  contexts show the rule changing decisions or preventing a failure, with
  overhead, corrections, and limitations recorded.
- `extraction-review-ready`: evidence is sufficient for the post-KCS-15
  retrospective to consider generic extraction. This is not extraction
  approval.
- `extracted-beta`: KCS-16b has produced a generic asset without importing
  project-specific contracts.
- `role-integrated-beta`: a separate personal agentic engineering kit project
  has assigned extracted assets to agent roles and composed their orchestration
  without claiming stable readiness.
- `integration-gate-passed`: the separate kit project has completed an
  end-to-end task from operator request through Discovery, Design, controlled
  implementation, review, evaluation/observability, and correction logging.
- `kit-ready`: after the integration gate, the separate kit project has stable
  triggers, role inputs/outputs, stop conditions, validation, documentation,
  and a versioned package. This repository does not own that package runtime.

An enforcement status never implies a portability status. A KCS-specific
freeze check may be deterministic but not portable. A portable Discovery
question may remain a human-review rule permanently.

## External Trial Contract Gate

A rule must not move to `external-trial-active` until the owning external
project or independent subsystem has a tracked Trial Contract for the exact
formulation being tested. This keeps the candidate registry compact while
making cross-project evidence comparable and attributable.

| Field | Required content |
| --- | --- |
| `Rule ID` | Exact `ENG-PORT-*` identifier from this registry |
| `Revision` | Rule-level revision when available; otherwise the KCS repository source commit that freezes the tested wording |
| `Stage` | Discovery, Design, or Delivery; must match the rule `Family` in this registry |
| `Trigger` | Observable condition under which the rule applies |
| `Invariant` | Project-neutral behavior, decision, or boundary the rule requires |
| `Owner / decision authority` | Human, agent role, platform, or combination responsible for applying the rule and deciding unresolved judgment |
| `Failure or stop behavior` | Required response when evidence is missing, the invariant fails, or authority is unavailable |
| `Required evidence` | Value-safe observations needed to evaluate effectiveness, corrections, overhead, false positives, and limitations |
| `Permitted enforcement type` | One or more honest levels from the enforcement ladder; judgment-only review gates are allowed |

The Trial Contract may remain in the external project's tracked evidence area.
The KCS registry records only its link or value-safe evidence summary when
reviewing a status change. The contract's Stage, Trigger, Invariant, authority,
and failure or stop semantics must remain project-neutral. A contract must:

- keep project bindings, thresholds, endpoints, identifiers, fixtures, domain
  data, and product behavior in a separate project binding or evidence record;
- describe required evidence by portable category and reference the local
  binding instead of embedding its project values;
- name both the rule ID and the exact revision or source commit;
- create a new revision reference when the tested formulation changes;
- preserve human judgment when deterministic enforcement would be dishonest.

Recording a Trial Contract does not promote a rule by itself. Promotion to
`external-trial-active` also requires that the external trial has actually
started collecting the evidence declared by that contract.

Portfolio-wide monitoring, consistent local states, retrospective admission,
and source-owned campaign review are defined in
`docs/internal/engineering-process/ddd-portfolio-trial-protocol.md`. That
protocol prevents fragmented project-specific activation while preserving this
per-rule evidence gate.

## Evidence Required From Another Project

A second-project mention is not evidence by itself. A value-safe tracked record
must identify:

- project and feature class;
- rule ID and version/formulation used;
- triggering task or condition;
- decision or behavior changed by the rule;
- validation or observed result;
- manual corrections and process overhead;
- false positives, failure modes, and project-specific assumptions;
- verdict: retain, revise, reject, or propose for extraction review.

External project records remain in their owning repositories. KCS-15 or the
post-KCS-15 retrospective may import only compact, value-safe evidence
summaries. Chat memory and untracked local drafts are not evidence for a status
change.

Project count is a minimum, not the decision rule. Two nearly identical
contexts may provide less portability evidence than one source project and one
materially different external domain.

## Roadmap Gates

| Stage | Allowed portability action | Forbidden action |
| --- | --- | --- |
| KCS-14.5, completed | Register candidates and retain local evidence from the incident and closeout | Treat closeout as extraction or role-packaging approval |
| KCS-15 | Field-test the process on feature-heavy work and collect auditable external evidence summaries | Treat use in another project as automatic proof |
| Post-KCS-15 retrospective | Classify rules as retain, revise, reject, project-specific, or extraction-review-ready | Skip unresolved corrections or incident findings |
| KCS-16a, if triggered | Stabilize rules that produced recurring corrections, ambiguity, or overhead | Package an unstable process |
| KCS-16b | Extract approved generic assets and preserve project-local contracts in their repositories | Copy KCS, support, privacy, or LED domain rules into generic assets |
| KCS-17 | Prepare the export manifest, compatibility boundary, evidence handoff, and initiation decision for a separate personal agentic engineering kit project | Implement or release the kit, own agent-role orchestration, or claim integration success inside the KCS repository |
| Separate kit project | Assign extracted assets to beta roles, implement orchestration, run the end-to-end integration gate, and package a stable kit only after the gate passes | Treat KCS-specific contracts as portable or publish a stable kit before integration evidence |

## Portfolio Coverage Gate

Individual rule maturity does not prove that the future kit covers the full
Discovery-Design-Delivery workflow. The matrix below is a capability inventory,
not a score and not a target for creating more rules. It prevents KCS-16b from
extracting a mature but incomplete subset without making the omitted work
visible.

The source-owned standards crosswalk and universal-core boundary are recorded
in `docs/internal/engineering-process/ddd-universal-core-standards-crosswalk.md`.
The active pre-KCS-16 cleanup and PR boundary is recorded in
`docs/internal/engineering-process/slice-plans/pre-kcs-16-ddd-portfolio-pr-readiness.md`.
That review finds the 28 candidates other than `ENG-PORT-DES-005` and
`ENG-PORT-DEL-005` sufficiently representative for the declared
Discovery-Design-controlled Delivery scope. The 28 form one core catalog with
different evidence strengths: field-evidence candidates, standards-backed
shadow rules, and reference-only guidance. This portfolio decision does not
promote any candidate or approve extraction.

The extraction gate below applies only to authoritative rule assets.
Standards-backed shadow and reference-only entries may be carried through
KCS-16/KCS-17 solely as visibly non-normative catalog descriptors; that is an
advisory packaging path, not extraction. They must not be loaded as rule
authority until their independent portability and extraction gates are met.

Company, domain, regulatory, platform, repository, delivery, and operations
requirements that fall outside the generic outcomes belong in target profiles
and adapters. A profile binds applicability, owners, thresholds, and local
policy; an adapter binds repositories, tools, APIs, runtimes, deployment, and
evidence collection. Neither may silently weaken a triggered core invariant or
change an upstream portability status.

Coverage status means:

- `covered`: one or more explicit rules and an accountable owner address the
  capability. This does not promote those rules on the portability ladder.
- `partial`: relevant rules or owners address only part of the capability.
- `gap`: no current rule or owner sufficiently addresses the capability.

Coverage does not measure cross-project evidence; that remains solely on the
portability ladder. The matrix records the current portfolio baseline and the
source-reviewed pre-KCS-16 disposition. A reviewed extraction disposition must
be one of:

- `covered-by-portable-rule`;
- `human-owned`;
- `platform-owned`;
- `project-specific`;
- `explicitly-out-of-kit-scope`;
- `evidence-gap`.

A capability does not need a new rule when a human, platform, project-specific
contract, or explicit scope boundary owns it more honestly. Updating this
matrix does not change any candidate's enforcement or portability status.

| Capability ID | Family | Required capability | Current coverage | Current owner and related candidates | Current disposition | Next evidence or disposition decision |
| --- | --- | --- | --- | --- | --- | --- |
| DDD-DISC-01 | Discovery | Identify the target user, desired outcome, current expensive gap, and cost of error | partial | Operator and Discovery workflow; `ENG-PORT-DISC-001`, `ENG-PORT-DISC-004` | framing: `covered-by-portable-rule`; value, priority, and error-cost judgment: `human-owned` | Extract the generic outcome/current-reality frame only; do not encode product value or priority decisions |
| DDD-DISC-02 | Discovery | Model the current workflow and separate confirmed, provisional, unknown, and rejected evidence | covered | Discovery workflow; `ENG-PORT-DISC-001`, `ENG-PORT-DISC-002`, `ENG-PORT-DISC-005`, `ENG-PORT-DISC-006` | `covered-by-portable-rule` | Extract only the minimal evidence-state and unknown-routing contract; project sources and labels remain local |
| DDD-DISC-03 | Discovery | Identify domain, data, physical, legal, privacy, and feasibility constraints before solution design | partial | Domain expert, operator, and Discovery workflow; `ENG-PORT-DISC-003`, `ENG-PORT-DEL-007` | identification discipline: `covered-by-portable-rule`; actual constraints and acceptable risk: `project-specific` and `human-owned` | Keep constraint discovery generic; never export domain, legal, privacy, or scientific policy values |
| DDD-DISC-04 | Discovery | Establish a measurable baseline, bounded hypothesis, controlled experiment, result, and correction log | covered | Discovery and evaluation workflow; `ENG-PORT-DISC-003` | `covered-by-portable-rule` | Rule selection still waits for the active LED experiment closeout; the capability itself has an owner and no gap |
| DDD-DISC-05 | Discovery | Ask the smallest material question batch and obtain explicit operator steering for unresolved decisions | covered | Operator and Discovery workflow; `ENG-PORT-DISC-004`, `ENG-PORT-DISC-005` | question selection/routing: `covered-by-portable-rule`; steering and material decisions: `human-owned` | Extract routing discipline only; operator decisions cannot be delegated to the kit |
| DDD-DES-01 | Design | Assign deterministic logic, AI proposals, human decisions, and side effects to explicit owners | covered | Designer and architecture review; `ENG-PORT-DES-004`, `ENG-PORT-DES-011` | ownership mapping: `covered-by-portable-rule`; material judgment and risk acceptance: `human-owned` | Preserve the rule that ownership does not validate AI content and cannot erase human residuals |
| DDD-DES-02 | Design | Declare changed and unchanged contracts, compatibility boundaries, and behavior-drift evidence | covered | Slice designer and reviewer; `ENG-PORT-DES-002`, `ENG-PORT-DES-003`, `ENG-PORT-DES-006` | declaration/review discipline: `covered-by-portable-rule`; concrete compatibility contracts: `project-specific` | Extract the artifact semantics after selected rules mature; keep product contracts in their repository |
| DDD-DES-03 | Design | Compare architecture options and model data, state, persistence, lifecycle, and failure trade-offs | partial | Designer and platform owner; `ENG-PORT-DES-005`, `ENG-PORT-DES-007`, `ENG-PORT-DES-009`, `ENG-PORT-DES-010` | option/authority record: `covered-by-portable-rule`; architecture selection: `human-owned`; state, persistence, and lifecycle mechanisms: `project-specific` | The kit may require a decision-ready comparison but must not choose architecture or prescribe storage/runtime mechanisms |
| DDD-DES-04 | Design | Map acceptance criteria, failure modes, and supported state transitions to deterministic, model, or human evidence gates | covered | Designer, evaluator, and reviewer; `ENG-PORT-DES-001`, `ENG-PORT-DES-008` | gate mapping: `covered-by-portable-rule`; residual judgment: `human-owned` | Active LED evidence must close before selecting DES-001 for extraction; human gates remain explicit |
| DDD-DES-05 | Design | Address privacy, security, reliability, performance, observability, and operator cognitive load at the selected boundary | partial | Security, privacy, platform, observability, and UX owners; `ENG-PORT-DES-011`, `ENG-PORT-DES-012`, `ENG-PORT-DEL-006`, `ENG-PORT-DEL-007` | privacy/security risk: `human-owned` and `project-specific`; reliability/performance/observability: `platform-owned` and `project-specific`; cognitive load: `human-owned` | Generic assets may route and expose these decisions; they must not contain product thresholds, controls, or platform implementations |
| DDD-DEL-01 | Delivery | Implement controlled slices through supported entrypoints with compact context and explicit handoffs | covered | Builder and repository workflow; `ENG-PORT-DEL-001`, `ENG-PORT-DEL-002`, `ENG-PORT-DEL-008` | bounded slice and authorization: `covered-by-portable-rule`; entrypoints: `project-specific`; handoff approval: `human-owned` | Extract generic bounded-slice/handoff semantics; commands and repository entrypoints remain local |
| DDD-DEL-02 | Delivery | Validate with tests, review, drift checks, residual risks, and maintainability evidence | covered | Builder and reviewer; `ENG-PORT-DEL-003`, `ENG-PORT-DEL-004`, `ENG-PORT-DEL-005` | review and residual-risk ownership: `human-owned`; tests and enforcement: `project-specific`; complexity metrics: `explicitly-out-of-kit-scope` until separately proven portable | Do not export KCS test suites, thresholds, or project-local complexity policy as generic rules |
| DDD-DEL-03 | Delivery | Evaluate model-mediated behavior with safe fixtures, declared trial conditions, observability, and provenance | covered | Evaluation and observability owner; `ENG-PORT-DEL-006`, `ENG-PORT-DEL-007`, `ENG-PORT-DEL-009`, `ENG-PORT-DEL-012` | evidence-level and claim boundary: `covered-by-portable-rule`; fixture privacy: `project-specific` and `human-owned`; runtime observability/provenance: `platform-owned` and `project-specific` | Extract only stable evidence/claim semantics; fixture contents, privacy decisions, tools, and observability systems remain local |
| DDD-DEL-04 | Delivery | Control build, deployment, migration, activation, rollback, and runtime feedback | partial | Platform and deployment owner; `ENG-PORT-DEL-009`, `ENG-PORT-DEL-011` | source/artifact traceability: `covered-by-portable-rule`; build/deployment/migration/activation/rollback/runtime operation: `platform-owned` and `project-specific` | KCS-16 extraction excludes operational implementations; the kit may preserve a handoff/preflight contract only |
| DDD-DEL-05 | Delivery | Convert corrections and repeated findings into reviewed promotions, portability evidence, extraction decisions, and integration feedback | partial | Retrospective, KCS-16 owner, and separate kit project; `ENG-PORT-DEL-003` and this registry | source promotion/extraction: `human-owned`; target feedback contract: `covered-by-portable-rule`; kit implementation/integration decisions: `explicitly-out-of-kit-scope` for this source | KCS-16 owns extraction; KCS-17 owns handoff; the separate kit project owns integration and later feedback |

### KCS-16b Extraction Readiness

KCS-16b must not start while a required capability remains unclassified or has
the final disposition `evidence-gap`. Before extraction:

1. Every matrix row has a reviewed final disposition, a short rationale, and
   the effect on the claimed kit scope. Composite rows must record separate
   dispositions for materially different named concerns; one umbrella
   disposition is insufficient.
2. Every rule selected for extraction independently satisfies the portability
   evidence and `extraction-review-ready` requirements above.
3. Discovery, Design, and Delivery each have explicit inputs, outputs, and
   human, agent, or platform ownership at their handoff boundaries.
4. The extraction scope states whether deployment and operations are included,
   platform-owned, project-specific, or explicitly out of kit scope.
5. Every selected asset records its kit treatment independently from its
   portability status: beta candidate, standards-backed shadow, or
   reference-only. Standards alignment alone must not be represented as
   cross-project evidence.

`partial` or `gap` coverage does not require framework growth and does not block
extraction after an honest non-rule disposition is approved. It blocks only
when the capability is required for the claimed kit scope and remains an
`evidence-gap`.

## Candidate Registry

Four entries remain at source-reviewed `external-trial-active` mappings to
exact LED or `plesk_support` contracts at source revision
`d1c6f6d1af8442ce704cf57c07a28ec4ed6aec66`. Twelve entries satisfied
`cross-project-evidence-recorded`, reached `extraction-review-ready`, passed
their KCS-16 extraction review, and are now `extracted-beta`: eight through the
source dispositions in `pre-kcs-16-ddd-evidence-review.md`,
`ENG-PORT-DEL-010` through `SR-DEL010-01`, and three from the committed
`plesk_support` GG-006 evidence through `SR-DISC006-01`, `SR-DES002-01`, and
`SR-DES011-01`. Their generic assets and the
non-authoritative 28-entry catalog boundary are recorded in
`engineering-playbook/ddd-universal-core.json`. Open external contracts remain
useful prospective evidence even when a rule has independently reached a later
source status; they do not complete or promote automatically.
LED D-213/Checkpoint 145 paused the three physical-result-dependent local
contracts because the authentic event and traceable evidence package are
absent. That local pause is recorded in `SR-LED-PAUSE-145`; it is not a failed
experiment, completed trial, demotion, promotion, or extraction decision.
The `plesk_support` GG-006 handoff is admitted from durable commit
`60acfecc401c8080483eaac11890082e175b0bc4` under `SR-PS-GG006-60ACF`.
Its two `retain` verdicts and one target-local `revise` verdict, together with
materially different KCS contexts, satisfy the independent portability gate.
All three exact contracts remain active for prospective evidence, while the
source statuses advance without changing upstream wording.
The full committed `plesk_support` campaign audit under
`SR-PS-CAMPAIGN-AUDIT-60ACF` also advances `ENG-PORT-DEL-007` from
`portability-candidate` to `external-trial-active` because its exact contract
genuinely began collecting safe no-send evidence. It remains advisory: the
per-rule cross-project verdict and complete effectiveness record are absent.

| ID | Family | Candidate rule | Local enforcement/evidence | Portability status | Next evidence gate |
| --- | --- | --- | --- | --- | --- |
| ENG-PORT-DISC-001 | Discovery | Separate requested outcome and operational reality from a proposed solution before architecture | KCS framing, the corrected `plesk_support` pilot, Understanding Tool terminal problem/solution separation, and AI Engineer RP-B9 provide materially different evidence under `SR-DISC001-01` | extracted-beta | KCS-16 extracted the generic rule; prospective evidence may refine it but is not a formal repeat-work prerequisite |
| ENG-PORT-DISC-002 | Discovery | For every material claim used in a decision, record whether current evidence makes it confirmed, provisional, unknown, or rejected. The state records evidence sufficiency only: it does not grant decision authority, and absent evidence remains unknown rather than becoming a default. If a required state cannot be supported, narrow or stop the dependent decision. | KCS incident causality, Understanding Tool label/correction evidence, AI Engineer RP-B9, and active LED contract are reviewed in `SR-DISC002-01` | extracted-beta | KCS-16a retained the minimal four-state invariant, separated evidence state from authority, and excluded Understanding Tool's local taxonomy |
| ENG-PORT-DISC-003 | Discovery | Complete the chain stakeholder answers -> workflow model -> data/domain constraints -> measurable baseline -> bounded hypothesis -> controlled experiment -> result/correction log | LED contract `ETC-LED-DISC-003-r1` is `paused-local-trial` under `SR-LED-PAUSE-145`; the authorized physical event and traceable result package are absent | external-trial-active | Resume only with the exact authorized sample identity and proposal linkage, manufacture and instrument records, authentic coordinates and local file references, named review, and effort when known; then close corrections, false positives, limitations, and local verdict |
| ENG-PORT-DISC-004 | Discovery | Ask the smallest material question batch needed for the next decision, not the entire domain inventory | KCS clarification mode limits unresolved material questions | portability-candidate | Track the rule ID/revision and record stakeholder burden and follow-up count in LED and `plesk_support` |
| ENG-PORT-DISC-005 | Discovery | The operator approves or steers autonomous evidence gathering; the agent classifies uncertainty and resolves repository-, research-, and feasibility-owned questions before asking operator-owned questions | KCS-15.1 transition closeout and Design Uncertainty protocol v0 | portability-candidate | Field-test whether the classification reduces avoidable operator diagnosis and questions without hiding material forks |
| ENG-PORT-DISC-006 | Discovery | Before finalizing a design or starting substantial implementation that depends on an existing runtime/API, prove the exact endpoint, mode, response shape, and operating condition with fresh evidence or one bounded safe smoke; neighboring paths and fixtures are nominal evidence only | KCS-15.2b1 exact-path correction and `plesk_support` GG-006 nominal-evidence stop establish materially different decision effects under `SR-DISC006-01` | extracted-beta | KCS-16 extracted the prove-or-stop invariant; the active external exact-operation smoke remains prospective capability evidence, not a repeat-work prerequisite |
| ENG-PORT-DES-001 | Design | Map each observable acceptance criterion to a deterministic gate, bounded model trial, or named human-review gate before implementation. For a branching or stateful workflow, enumerate and gate the supported outcome-by-context transition matrix; testing every outcome in isolation plus one happy-path sequence is insufficient. | KCS functional-test convention and policy anchors; LED contract `ETC-LED-DES-001-r1` is `paused-local-trial` under `SR-LED-PAUSE-145`; its predeclared map cannot select a branch without the authentic observation | external-trial-active | Resume with the exact authorized physical evidence package and named review; then close acceptance-map corrections, test/review burden, false confidence, limitations, and local verdict |
| ENG-PORT-DES-002 | Design | State contracts intended to change and contracts required to remain unchanged before a material slice | KCS material plan/review boundaries and the `plesk_support` GG-006 no-egress authority conflict establish materially different decision effects under `SR-DES002-01` | extracted-beta | KCS-16 extracted the generic changed/unchanged boundary; concrete policies and contracts remain target-owned, and the active external closeout remains prospective evidence |
| ENG-PORT-DES-003 | Design | For behavior-preserving work, record old -> new and new -> old behavior mapping with evidence | `KCS14-PROMO-008` is implemented as a review/policy anchor | portability-candidate | Track the rule ID/revision on a non-KCS behavior-preserving change and record overhead |
| ENG-PORT-DES-004 | Design | Assign deterministic processing, AI proposals, validation, material decisions, and side effects to explicit owners. Ownership identifies responsibility and decision authority; it does not validate content. AI output remains untrusted until the required deterministic validation or named human judgment accepts it. If validation or decision authority is missing, stop or narrow the dependent action. | KCS, Understanding Tool, AI Engineer, and active LED ownership evidence are reviewed in `SR-DES004-01`; the evidence also shows ownership does not eliminate false AI claims | extracted-beta | KCS-16a separated ownership and decision authority from content validation before extraction |
| ENG-PORT-DES-005 | Design | Review changes by ownership boundary and use aggregate review to distinguish map, process, and architecture errors | KCS code-review graph and aggregate review protocol | project-local | Apply to a bounded cross-module refactor in another repository and measure boundary corrections and review overhead |
| ENG-PORT-DES-006 | Design | A behavior-preserving touch to a frozen contract area requires explicit unchanged-contract, characterization, and residual-risk evidence | `KCS14-PROMO-010` is a checklist item | portability-candidate | Track the rule ID/revision on a frozen or compatibility-sensitive surface outside KCS and determine which evidence fields are generic |
| ENG-PORT-DES-007 | Design | Track outcome agreement, design selection, and Delivery authorization independently; no state implies another | KCS transition correction, Understanding Tool terminal stops, AI Engineer role/adoption gates, and active external contracts are reviewed in `SR-DES007-01` | extracted-beta | KCS-16 extracted the generic rule; open contracts may refine overhead and false-positive evidence later |
| ENG-PORT-DES-008 | Design | Before an operator decision, show the exact decision, visible information, sufficiency, options, consequences, and uncertainty/failure path | KCS-15.1 follow-on article-fit discussion exposed missing ticket context in the proposed operator view | portability-candidate | Field-test decision-readiness completeness and whether the operator requests previously unseen evidence |
| ENG-PORT-DES-009 | Design | A material implementation, refactor, deployment, or integration closes with a compact Ousterhout review record; a small leaf change may use a two-field `not triggered` form only when boundaries and material internal complexity remain unchanged | `KCS14-PROMO-014` implements the local review gate and record-shape anchor | portability-candidate | Record trigger accuracy, leaf exceptions, design corrections, reviewer overhead, and false positives across KCS-15 and one materially different project |
| ENG-PORT-DES-010 | Design | Before Delivery begins for material work, keep a durable authoritative design record containing the selected boundary, independent approval states, acceptance gates, unchanged contracts, and stop conditions; review resolves that record and checks the authorized phase against the change. A mechanical leaf change may rely on an existing tracked contract only when it changes no material ownership, interface, dependency, persistence, failure, deployment, or internal-complexity boundary and the reviewer records that basis. Missing authority or an unsupported leaf exception keeps Delivery locked. | KCS chat-only correction, Understanding Tool tracked experiment authority, and AI Engineer evidence/adoption traceability are reviewed in `SR-DES010-01` | extracted-beta | KCS-16a made materiality explicit and retained a verifiable leaf exception before extraction |
| ENG-PORT-DES-011 | Design | For every claimed end-to-end invariant, map each supported user/system entrypoint to the first deterministic enforcement gate and prove that no prohibited outcome can occur before or around that gate. Inventory direct model responses and alternative host tools that can produce the same outcome; a guarded connector does not enforce the invariant when the model can bypass it through a generic file, browser, shell, messaging, or artifact action. A model-controlled tool call is optional behavior, not enforcement. A user-controlled prompt/command may improve routing but remains model-mediated unless it directly invokes the deterministic owner. If reachability cannot be guaranteed, restrict the supported entrypoint or label the behavior best-effort and obtain explicit approval for the weaker contract. | KCS-15.2b2 host/tool bypasses and `plesk_support` GG-006 application/CLI bypasses establish materially different decision effects under `SR-DES011-01`; the current wording already required both corrections | extracted-beta | KCS-16 extracted the generic reachability and claim-narrowing invariant; target entrypoints, enforcement mechanisms, and future runtime proof remain adapter-owned |
| ENG-PORT-DES-012 | Design | When a material design depends on an unfamiliar interaction, unproved host UI capability, or operator-comfort/cognitive-load judgment, the agent proactively offers the smallest safe pre-implementation UX evidence and escalates fidelity only for an unknown the cheaper level cannot resolve: static/wireframe -> install-free clickable fixture -> isolated component/protocol harness -> installed-host smoke -> production-like trial. Packaging, activation, restart, or deployment is reserved for real host rendering, lifecycle, permissions, navigation, or routing claims. The evidence method declares the decision claim, fixture/condition, exercised interaction, simulated limits, corrections, evidence budget, escalation reason, and stop condition. Success informs design selection or iteration but does not select production design, authorize Delivery, or prove repeated-use comfort. | KCS-15.2b2 Phase C would have implemented a standalone operator UI and evaluated comfort afterward until the operator requested earlier UX evidence; its first in-chat evaluation then required a separate MCPB, registry, activation, restart, and lifecycle debugging before basic layout comfort could be judged. The Design Uncertainty protocol, feature playbook, review checklist, and policy anchor now require proactive but proportional pre-implementation UX evidence. | portability-candidate | Track late UX corrections avoided, evidence level selected, escalation reasons, prototype and installed-host overhead, smoke-to-production drift, false-positive triggers, skipped-smoke reasons, and operator decision speed across KCS-15 and one materially different product interaction |
| ENG-PORT-DEL-001 | Delivery | Use supported repo-local tool entrypoints instead of ad hoc commands | `KCS14-PROMO-003` is implemented by policy and liveness checks | portability-candidate | Compare command errors and manual correction count in another repository with an explicit entrypoint index |
| ENG-PORT-DEL-002 | Delivery | Start each material batch from a compact current-state frame and emit a visible checkpoint after commits and aggregate reviews | KCS agent workflow and process-gap policy anchor | portability-candidate | Track the rule ID/revision and record context-reset frequency, stale-assumption corrections, and operator overhead externally |
| ENG-PORT-DEL-003 | Delivery | Repeated review findings move through note -> checklist -> test/tool/structural boundary only when enforcement is honest | KCS promotion registry; promotions 001-008 are implemented or in advisory probation, while 009-010 remain checklist-level | portability-candidate | Import value-safe evidence showing whether external projects produced, rejected, or revised candidates |
| ENG-PORT-DEL-004 | Delivery | Every material behavior/refactor slice closes with explicit drift checks and residual review-only risks | `KCS14-PROMO-008`, review protocol, and focused policy tests | portability-candidate | Track the rule ID/revision in a non-KCS material slice and compare detected drift, false positives, and overhead |
| ENG-PORT-DEL-005 | Delivery | Complexity and coupling sensors remain advisory until stable evidence supports a narrow blocking delta rule | `KCS14-PROMO-005` is probation-advisory; `KCS14-PROMO-007` anchors full delta reporting | project-local | Collect multiple non-KCS refactor deltas and determine whether the metric changed decisions rather than rewarding helper growth |
| ENG-PORT-DEL-006 | Delivery | Nondeterministic or model-mediated acceptance predeclares fixtures, trial count, conditions, thresholds, variance, and safe observability | KCS-14.5 closeout distinguishes deterministic Python proof from Desktop/model interpretation; LED contract `ETC-LED-DEL-006-r1` is `paused-local-trial` under `SR-LED-PAUSE-145`; its count, conditions, gate, provenance, and stop behavior remain frozen | external-trial-active | Resume with the exact authorized physical evidence package and named review; fixtures remain insufficient. Then close uncertainty handling, corrections, overhead, false positives, limitations, and local verdict |
| ENG-PORT-DEL-007 | Delivery | Synthetic or sanitized fixtures carry provenance and privacy evidence before use | `KCS14-PROMO-004` is implemented as a policy test; `plesk_support` contract `ETC-PS-DEL-007-r1` genuinely stopped an approved synthetic fixture before send under `SR-PS-CAMPAIGN-AUDIT-60ACF` because the exact destination-purpose and privacy boundary remained unresolved | external-trial-active | Resume only with approved destination and purpose plus exact project/subscription and retention evidence; independently record the per-rule verdict, corrections, overhead, false positives, and limitations before cross-project review |
| ENG-PORT-DEL-008 | Delivery | An isolated adapter, spike, prototype, or experiment proves only its bounded feasibility claim; parent UX selection and integration authorization remain separate and locked | KCS bounded adapter, Understanding Tool terminal experiment disposition, and active LED/`plesk_support` contracts are reviewed in `SR-DEL008-01` | extracted-beta | KCS-16 extracted the generic rule with a compact evidence and parent-boundary record |
| ENG-PORT-DEL-009 | Delivery | Before an installed-client/model/operator trial, prove one current provenance-and-capability chain from source revision through built artifact, installed files/cache, explicit enabled/activation state, reloaded client process, effective required configuration at the terminal consuming process, and every dependency service's observed process/config-data identity plus exact required capability on the same live instances. Configuration declared in a shell, launcher, service manager, manifest, registry, parent process, or synthetic wrapper is nominal evidence until a value-safe effective-config or derived-effect preflight proves propagation on the current terminal process. Discovery, allowlisting, installability, or parent-process configuration does not prove activation or propagation; evidence from another worktree/process/deployment does not transfer, and a generic health endpoint cannot substitute for exact capability or provenance. | The first KCS-15.2b2 attempt used a July 21 extension instead of the July 23 implementation; after reinstall, the exact-article flow still reached the old `plesk_support` runtime from another checkout, whose generic status/search paths were healthy but whose live process lacked `/api/article-snippets`. The Phase C UX smoke was later present in the Claude registry and passed `can_install`, but the client did not launch it because its separate `Claude Extensions Settings` activation file was absent. The PAUX-7103 accounting trial passed source and installed-wrapper smokes and had values declared through `launchctl`, but Claude Desktop sanitized or failed to propagate them to the terminal MCPB connector, so the completed real-ticket run produced no trace. The local gate now distinguishes artifact identity, registry presence, activation state, post-reload process start, terminal effective configuration, and exact live capability. | portability-candidate | Track stale client/service detections, missing activation/config propagation states, avoided operator retries and unobserved trials, cross-repo revision mismatches, capability/effective-config probe false positives, identity-check overhead, and applicability to a materially different packaged or deployed system |
| ENG-PORT-DEL-010 | Delivery | When duplicate, re-entrant, retried, or rejected submission to a stateful or side-effecting path could repeat a side effect or corrupt the identity or lifecycle of a logical operation, define and test outcome-level behavior before relying on the path operationally: one logical action produces at most one side effect; an exact duplicate receives the same stable outcome or a deterministic no-op; a conflicting or stale submission cannot alter or consume a different current operation; and a rejected submission that changed no state preserves any still-valid operation unless an identity or lifecycle conflict is established. The deterministic owner normalizes equivalent accepted inputs and owns any mechanism and retention bounds. Stateless or side-effect-free paths need no retry mechanism when the applicability review records that the invariant cannot be violated. Instructions to submit once and one successful run are not duplicate-safety evidence. | KCS runtime corrections and AI Engineer `DDD-RETRO-AIE-DEL010-01` establish cross-project value under `SR-DEL010-01`, including avoided unsupported API mechanisms | extracted-beta | KCS-16a expressed applicability and retry safety as mechanism-neutral outcomes; `DDD-AIE-DEL010-02` remains prospective runtime evidence |
| ENG-PORT-DEL-011 | Delivery | A material repository slice is not delivered or eligible to authorize the next material slice until its intended diff is isolated from unrelated/deferred work, reviewed and validated in that isolated state, committed or explicitly given an operator-approved no-commit/defer disposition, and its built/installed evidence is traceable to the committed content. Pre-commit or mixed-worktree smokes remain provisional feasibility evidence. | KCS mixed/uncommitted closeout evidence and AI Engineer durable RP/adoption provenance are reviewed in `SR-DEL011-01`; the lost RP-B3 packet remains an explicit limitation | extracted-beta | KCS-16 extracted the generic rule and retained the approved no-commit/defer path |
| ENG-PORT-DEL-012 | Delivery | Before closing work with a claim about a named incident, noisy input, deployment failure, or parent operational outcome, map the claim to the smallest safe evidence level capable of proving it. Fixtures and synthetic smokes may prove contracts, mechanics, safety, wiring, or feasibility. A representative or real operational gate is required only when the completion claim depends on that level; it is not a default for every change. When target policy requires an approved sanitized representative case, that binding remains target-owned. If the required gate is unavailable, unsafe, deferred, or fails, narrow the completion claim and keep the stronger outcome open. | KCS synthetic-to-representative correction, Understanding Tool hidden representative gates, and active LED physical-case evidence are reviewed in `SR-DEL012-01` | extracted-beta | KCS-16a made evidence proportional to the claim and avoided a default production-trial requirement before extraction |

## Registry Maintenance

- Add a candidate only when its generic formulation and source evidence can be
  stated without copying a project-specific product rule.
- Update portability status only from tracked evidence, never from chat
  recollection, untracked drafts, or reviewer confidence.
- Preserve rejected and project-specific entries with the reason; do not make
  the registry a success-only list.
- KCS-14.5 closeout evidence may support new candidates but cannot mark them
  extracted.
- KCS-15 closeout must review this registry together with
  `docs/internal/engineering-process/promotion-candidates.md`.
- KCS-16b owns extraction decisions. KCS-17 owns the handoff and initiation
  boundary. The separate kit project owns agent roles, orchestration, the
  integration gate, and stable packaging.
