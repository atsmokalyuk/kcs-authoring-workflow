# Engineering Rule Portability

Status: authoritative pre-extraction lifecycle and candidate registry.

Date: 2026-07-22

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

## Candidate Registry

No current entry has an auditable `external-trial-active` evidence mapping or a
higher portability status. External trials and local drafts may exist, but they
must name the matching `ENG-PORT-*` rule revision in a tracked owning-project
record before promotion.

| ID | Family | Candidate rule | Local enforcement/evidence | Portability status | Next evidence gate |
| --- | --- | --- | --- | --- | --- |
| ENG-PORT-DISC-001 | Discovery | Separate requested outcome and operational reality from a proposed solution before architecture | KCS spec-first workflow and incident investigation use explicit current-state and unknown-evidence frames | portability-candidate | Track the rule ID/revision in the `plesk_support` material-feature trial and record whether solution-first proposals and late corrections decrease |
| ENG-PORT-DISC-002 | Discovery | Record facts as confirmed, provisional, unknown, or rejected; absence of evidence is not a default | KCS incident causality keeps unknown classifications explicit | portability-candidate | Track the rule ID/revision in the LED stakeholder-answer cycle and record incorrect assumptions prevented or corrected |
| ENG-PORT-DISC-003 | Discovery | Complete the chain stakeholder answers -> workflow model -> data/domain constraints -> measurable baseline -> bounded hypothesis -> controlled experiment -> result/correction log | Discovery chain is defined in the LED feasibility pack; no end-to-end result exists | portability-candidate | Run the first approved LED controlled experiment and record the correction log |
| ENG-PORT-DISC-004 | Discovery | Ask the smallest material question batch needed for the next decision, not the entire domain inventory | KCS clarification mode limits unresolved material questions | portability-candidate | Track the rule ID/revision and record stakeholder burden and follow-up count in LED and `plesk_support` |
| ENG-PORT-DISC-005 | Discovery | The operator approves or steers autonomous evidence gathering; the agent classifies uncertainty and resolves repository-, research-, and feasibility-owned questions before asking operator-owned questions | KCS-15.1 transition closeout and Design Uncertainty protocol v0 | portability-candidate | Field-test whether the classification reduces avoidable operator diagnosis and questions without hiding material forks |
| ENG-PORT-DISC-006 | Discovery | Before finalizing a design or starting substantial implementation that depends on an existing runtime/API, prove the exact endpoint, mode, response shape, and operating condition with fresh evidence or one bounded safe smoke; neighboring paths and fixtures are nominal evidence only | KCS-15.2b1 `/api/snippets` planning correction and bounded live smoke | portability-candidate | Track avoided late integration corrections, smoke overhead, false positives, and exact-path evidence reuse across KCS-15 and one materially different project |
| ENG-PORT-DES-001 | Design | Map each observable acceptance criterion to a deterministic gate, bounded model trial, or named human-review gate before implementation. For a branching or stateful workflow, enumerate and gate the supported outcome-by-context transition matrix; testing every outcome in isolation plus one happy-path sequence is insufficient. | KCS functional-test convention and policy anchors; the KCS-15.2b2 canary exposed that `need_more_evidence` passed as a single-item outcome while its batch-continuation transition remained untested and stopped the remaining items | portability-candidate | Track the rule ID/revision in one `plesk_support` feature slice and one KCS-15 feature slice with acceptance-to-gate evidence, including transition-matrix omissions and test overhead |
| ENG-PORT-DES-002 | Design | State contracts intended to change and contracts required to remain unchanged before a material slice | KCS slice plans, review packets, and freeze policy | portability-candidate | Compare unchanged-contract corrections and drift findings in a tracked external trial and KCS-15 |
| ENG-PORT-DES-003 | Design | For behavior-preserving work, record old -> new and new -> old behavior mapping with evidence | `KCS14-PROMO-008` is implemented as a review/policy anchor | portability-candidate | Track the rule ID/revision on a non-KCS behavior-preserving change and record overhead |
| ENG-PORT-DES-004 | Design | Assign deterministic algorithms, AI proposals, and human decisions to explicit owners; AI output remains untrusted until validated | KCS runtime architecture and packet validation enforce this locally | portability-candidate | Record a materially different ownership decision in a tracked `plesk_support` or LED trial without copying KCS-specific contracts |
| ENG-PORT-DES-005 | Design | Review changes by ownership boundary and use aggregate review to distinguish map, process, and architecture errors | KCS code-review graph and aggregate review protocol | project-local | Apply to a bounded cross-module refactor in another repository and measure boundary corrections and review overhead |
| ENG-PORT-DES-006 | Design | A behavior-preserving touch to a frozen contract area requires explicit unchanged-contract, characterization, and residual-risk evidence | `KCS14-PROMO-010` is a checklist item | portability-candidate | Track the rule ID/revision on a frozen or compatibility-sensitive surface outside KCS and determine which evidence fields are generic |
| ENG-PORT-DES-007 | Design | Track outcome agreement, design selection, and Delivery authorization independently; no state implies another | KCS-15.1 follow-on transition exposed ambiguous continuation wording; protocol v0 now keeps a three-part approval ledger | portability-candidate | Record unauthorized-transition attempts, late corrections, and operator overhead across KCS-15 material decisions |
| ENG-PORT-DES-008 | Design | Before an operator decision, show the exact decision, visible information, sufficiency, options, consequences, and uncertainty/failure path | KCS-15.1 follow-on article-fit discussion exposed missing ticket context in the proposed operator view | portability-candidate | Field-test decision-readiness completeness and whether the operator requests previously unseen evidence |
| ENG-PORT-DES-009 | Design | A material implementation, refactor, deployment, or integration closes with a compact Ousterhout review record; a small leaf change may use a two-field `not triggered` form only when boundaries and material internal complexity remain unchanged | `KCS14-PROMO-014` implements the local review gate and record-shape anchor | portability-candidate | Record trigger accuracy, leaf exceptions, design corrections, reviewer overhead, and false positives across KCS-15 and one materially different project |
| ENG-PORT-DES-010 | Design | Before Delivery begins, every material feature/slice has a tracked authoritative design artifact containing the selected boundary, approval ledger, acceptance gates, unchanged contracts, and stop conditions; every material review packet resolves that artifact and checks the authorized phase against the diff; chat is only the decision surface | KCS-15.2b2 design would have remained chat-only until the operator explicitly requested persistence; the local playbook, Active Slice Plan review handoff, and policy tests now connect Design to Delivery review | portability-candidate | Track missing-context prevention, unauthorized/locked-phase findings, plan-update overhead, stale-plan corrections, and small-leaf false positives across KCS-15 and one materially different project |
| ENG-PORT-DES-011 | Design | For every claimed end-to-end invariant, map each supported user/system entrypoint to the first deterministic enforcement gate and prove that no prohibited outcome can occur before or around that gate. Inventory direct model responses and alternative host tools that can produce the same outcome; a guarded connector does not enforce the invariant when the model can bypass it through a generic file, browser, shell, messaging, or artifact action. A model-controlled tool call is optional behavior, not enforcement. A user-controlled prompt/command may improve routing but remains model-mediated unless it directly invokes the deterministic owner. If reachability cannot be guaranteed, restrict the supported entrypoint or label the behavior best-effort and obtain explicit approval for the weaker contract. | KCS-15.2b2 first produced a manual article with zero KCS tool calls and later created a combined Markdown draft through Claude's host file actions after the KCS surface failed closed. The Python gate worked only inside the connector and could not govern alternate model-controlled paths, so the end-to-end claim was invalid and Phase B returned to Design. The local playbook/review gate now requires entrypoint-to-enforcement and alternative-tool mapping before Delivery. | portability-candidate | Track direct-answer and alternate-tool bypasses prevented, false confidence corrections, mapping overhead, prompt/command false positives, host-permission boundary changes, and architecture changes in KCS-15 plus one materially different agentic tool integration |
| ENG-PORT-DES-012 | Design | When a material design depends on an unfamiliar interaction, unproved host UI capability, or operator-comfort/cognitive-load judgment, the agent proactively offers the smallest safe pre-implementation UX evidence and escalates fidelity only for an unknown the cheaper level cannot resolve: static/wireframe -> install-free clickable fixture -> isolated component/protocol harness -> installed-host smoke -> production-like trial. Packaging, activation, restart, or deployment is reserved for real host rendering, lifecycle, permissions, navigation, or routing claims. The evidence method declares the decision claim, fixture/condition, exercised interaction, simulated limits, corrections, evidence budget, escalation reason, and stop condition. Success informs design selection or iteration but does not select production design, authorize Delivery, or prove repeated-use comfort. | KCS-15.2b2 Phase C would have implemented a standalone operator UI and evaluated comfort afterward until the operator requested earlier UX evidence; its first in-chat evaluation then required a separate MCPB, registry, activation, restart, and lifecycle debugging before basic layout comfort could be judged. The Design Uncertainty protocol, feature playbook, review checklist, and policy anchor now require proactive but proportional pre-implementation UX evidence. | portability-candidate | Track late UX corrections avoided, evidence level selected, escalation reasons, prototype and installed-host overhead, smoke-to-production drift, false-positive triggers, skipped-smoke reasons, and operator decision speed across KCS-15 and one materially different product interaction |
| ENG-PORT-DEL-001 | Delivery | Use supported repo-local tool entrypoints instead of ad hoc commands | `KCS14-PROMO-003` is implemented by policy and liveness checks | portability-candidate | Compare command errors and manual correction count in another repository with an explicit entrypoint index |
| ENG-PORT-DEL-002 | Delivery | Start each material batch from a compact current-state frame and emit a visible checkpoint after commits and aggregate reviews | KCS agent workflow and process-gap policy anchor | portability-candidate | Track the rule ID/revision and record context-reset frequency, stale-assumption corrections, and operator overhead externally |
| ENG-PORT-DEL-003 | Delivery | Repeated review findings move through note -> checklist -> test/tool/structural boundary only when enforcement is honest | KCS promotion registry; promotions 001-008 are implemented or in advisory probation, while 009-010 remain checklist-level | portability-candidate | Import value-safe evidence showing whether external projects produced, rejected, or revised candidates |
| ENG-PORT-DEL-004 | Delivery | Every material behavior/refactor slice closes with explicit drift checks and residual review-only risks | `KCS14-PROMO-008`, review protocol, and focused policy tests | portability-candidate | Track the rule ID/revision in a non-KCS material slice and compare detected drift, false positives, and overhead |
| ENG-PORT-DEL-005 | Delivery | Complexity and coupling sensors remain advisory until stable evidence supports a narrow blocking delta rule | `KCS14-PROMO-005` is probation-advisory; `KCS14-PROMO-007` anchors full delta reporting | project-local | Collect multiple non-KCS refactor deltas and determine whether the metric changed decisions rather than rewarding helper growth |
| ENG-PORT-DEL-006 | Delivery | Nondeterministic or model-mediated acceptance predeclares fixtures, trial count, conditions, thresholds, variance, and safe observability | KCS-14.5 closeout distinguishes deterministic Python proof from Desktop/model interpretation | portability-candidate | Track the rule ID/revision and compare completed KCS-14.5 evidence with a bounded model-mediated trial externally |
| ENG-PORT-DEL-007 | Delivery | Synthetic or sanitized fixtures carry provenance and privacy evidence before use | `KCS14-PROMO-004` is implemented as a policy test | portability-candidate | Track the rule ID/revision and compare fixture acceptance and correction evidence externally without importing private data |
| ENG-PORT-DEL-008 | Delivery | An isolated adapter, spike, prototype, or experiment proves only its bounded feasibility claim; parent UX selection and integration authorization remain separate and locked | KCS-15.2a proves a bounded local public RAG adapter while its closeout leaves KCS-15.2b design open and Delivery locked | portability-candidate | Evaluate KCS-15.2b through a separate decision-readiness and Delivery gate; record any inherited-approval attempt, correction, and overhead |
| ENG-PORT-DEL-009 | Delivery | Before an installed-client/model/operator trial, prove one current provenance-and-capability chain from source revision through built artifact, installed files/cache, explicit enabled/activation state, reloaded client process, and every dependency service's observed process/config-data identity plus exact required capability on the same live instances; discovery, allowlisting, or installability does not prove activation; evidence from another worktree/process/deployment does not transfer, and a generic health endpoint cannot substitute for exact capability or provenance | The first KCS-15.2b2 attempt used a July 21 extension instead of the July 23 implementation; after reinstall, the exact-article flow still reached the old `plesk_support` runtime from another checkout, whose generic status/search paths were healthy but whose live process lacked `/api/article-snippets`. The Phase C UX smoke was later present in the Claude registry and passed `can_install`, but the client did not launch it because its separate `Claude Extensions Settings` activation file was absent. The local gate now distinguishes artifact identity, registry presence, activation state, post-reload process start, and exact live capability. | portability-candidate | Track stale client/service detections, missing activation states, avoided operator retries, cross-repo revision mismatches, capability-probe false positives, identity-check overhead, and applicability to a materially different packaged or deployed system |
| ENG-PORT-DEL-010 | Delivery | Every stateful or side-effecting tool/API continuation used by a model, client, worker, or retrying transport defines and tests duplicate, re-entrant, and rejected-submission behavior before operational trials: one logical action produces at most one side effect; an exact duplicate receives a stable replay or deterministic no-op; replay state is bounded by ref/idempotency ownership and TTL; a conflicting replay remains invalid; a rejected payload that has not changed state preserves its still-valid pending operation unless it proves an identity/lifecycle conflict; and a stale prior ref cannot consume a newer unrelated pending operation. Equivalent accepted call shapes are normalized by the deterministic owner. Prompt instructions to call once and one successful single-call run are not retry-safety evidence. | In the KCS-15.2b2 installed text-recovery smoke, Sonnet 5 submitted the same operator-confirmed `none_fit` twice before the first tool result returned. The first call generated the reviewer bundle and advanced to item two; the stale duplicate then invalidated the new pending comparison and caused a false batch-stop message. A later real-ticket canary submitted non-canonical `non_fit`; the rejection consumed the comparison, so the operator's corrected `none_fit` could not continue. The bounded local corrections retain one ephemeral completed-comparison replay record, return the same Python result for an equivalent duplicate without another draft, reject changed outcomes/candidates, preserve newer pending comparisons, and preserve a current pending comparison across a pre-side-effect shape rejection. | portability-candidate | Track duplicate/re-entrant calls, rejected-submission corrections, prevented duplicate writes, replay-cache bounds, conflicting-replay behavior, false positives, and implementation overhead in another model/tool or asynchronous job integration |
| ENG-PORT-DEL-011 | Delivery | A material repository slice is not delivered or eligible to authorize the next material slice until its intended diff is isolated from unrelated/deferred work, reviewed and validated in that isolated state, committed or explicitly given an operator-approved no-commit/defer disposition, and its built/installed evidence is traceable to the committed content. Pre-commit or mixed-worktree smokes remain provisional feasibility evidence. | KCS-15.2b2 passed focused tests, package identity checks, and installed Desktop smokes from an isolated package snapshot, but its accepted source and process batches remained mixed and uncommitted while the work was described as complete and the next slice was discussed. The local closeout gate now separates useful pre-commit feedback from repository delivery and Git traceability. | portability-candidate | Track premature-closeout findings, staged-boundary corrections, artifact-to-commit mismatches, rebuild overhead, approved no-commit dispositions, and applicability in another repository with deployment artifacts |
| ENG-PORT-DEL-012 | Delivery | Before closing a slice that claims to resolve a named incident, noisy input, deployment failure, or parent operational outcome, map that outcome to a safe representative case and the evidence level required by the claim. Fixtures and synthetic installed smokes may prove contracts, mechanics, safety, wiring, or feasibility; they cannot substitute for the approved sanitized representative-case or real operational gate. If that gate is unavailable, unsafe, deferred, or fails, narrow the completion claim and keep the parent outcome open. | KCS-15.2b2 exercised its two-item selection and reuse workflow on constructed synthetic ticket data, but did not run the approved sanitized super-noisy KCS-14.5 case whose failure motivated the operational recovery. The mechanism is feasible; resolution of the parent real-ticket outcome remains unproven. The local plan and review gate now require explicit parent-outcome coverage rather than counting additional synthetic successes. | portability-candidate | Track synthetic-to-representative escapes, late failures found, evidence cost, privacy-safe canary preparation, narrowed claims, and false-positive triggers across one later KCS slice and a materially different incident-driven feature |

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
