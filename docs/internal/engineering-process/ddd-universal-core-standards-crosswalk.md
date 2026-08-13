# DDD Universal Core Standards Crosswalk

Status: authoritative source-owned portfolio boundary and planning input for
KCS-16 extraction and the later KCS-17 handoff. This record does not start
KCS-16 or KCS-17, change a rule's portability status, or approve extraction.

Date: 2026-08-13

## Decision

The generic Engineering Kit portfolio is a 28-rule universal-core catalog:
every current `ENG-PORT-*` candidate except `ENG-PORT-DES-005` and
`ENG-PORT-DEL-005`.

The 28 rules provide sufficient capability coverage for the declared kit
scope:

```text
Discovery -> Design -> controlled Delivery -> review/evidence -> handoff
```

Sufficient coverage does not mean that every rule has the same authority or
portability maturity. The catalog contains three operational strengths:

| Core lane | Rules | Intended kit treatment |
| --- | --- | --- |
| Field-evidence lane | `ENG-PORT-DISC-001`, `ENG-PORT-DISC-002`, `ENG-PORT-DES-001`, `ENG-PORT-DES-004`, `ENG-PORT-DES-007`, `ENG-PORT-DES-010`, `ENG-PORT-DEL-006`, `ENG-PORT-DEL-008`, `ENG-PORT-DEL-010`, `ENG-PORT-DEL-011`, `ENG-PORT-DEL-012` | Eligible for authoritative beta extraction only after the existing per-rule KCS-16 gate; current source status remains authoritative |
| Standards-backed shadow lane | `ENG-PORT-DISC-003`, `ENG-PORT-DISC-006`, `ENG-PORT-DES-002`, `ENG-PORT-DES-003`, `ENG-PORT-DES-006`, `ENG-PORT-DES-008`, `ENG-PORT-DES-011`, `ENG-PORT-DES-012`, `ENG-PORT-DEL-003`, `ENG-PORT-DEL-004`, `ENG-PORT-DEL-007`, `ENG-PORT-DEL-009` | KCS-16 may carry a neutralized descriptor only as non-normative shadow catalog metadata; it is not an extracted rule. Shadow evaluation must collect applicability, corrections, overhead, false positives, and limitations |
| Reference-only lane | `ENG-PORT-DISC-004`, `ENG-PORT-DISC-005`, `ENG-PORT-DES-009`, `ENG-PORT-DEL-001`, `ENG-PORT-DEL-002` | Optional non-normative catalog guidance; it is not an extracted rule or authoritative gate and does not imply standards conformance or field validation |

The two excluded rules remain source-visible but outside the generic core:

- `ENG-PORT-DES-005`: the current ownership-boundary and aggregate-review
  mechanism is project-local;
- `ENG-PORT-DEL-005`: the current complexity and coupling sensor policy is
  project-local.

Their exclusion does not create a required-capability gap. Review ownership,
validation, residual risk, and maintainability outcomes are already represented
elsewhere in the portfolio; the two excluded mechanisms may be supplied by a
project profile if a target context needs them.

The KCS-16 extraction gate remains unchanged: only a rule that independently
reaches `extraction-review-ready` may become an authoritative extracted beta
asset. Carrying a shadow or reference descriptor in the 28-entry catalog is a
separate, non-extracted advisory packaging path. KCS-17 must preserve that
distinction in the export manifest, and the later kit must not load either
advisory lane as rule authority.

## External Standards Verdict

The crosswalk used primary standards and public authoritative framework
material as evidence of general relevance, not as evidence that the exact KCS
wording has already worked in another project.

| External source | Universal-core outcomes supported | Important boundary |
| --- | --- | --- |
| [ISO/IEC/IEEE 12207:2026](https://www.iso.org/standard/90219.html) | stakeholder involvement; context; iterative life-cycle processes; definition, control, and improvement of software processes | Does not prescribe a particular life-cycle method, artifact format, or local workflow |
| [ISO/IEC/IEEE 29148:2018](https://www.iso.org/standard/72089.html) | requirements engineering throughout the life cycle and requirements-related information items | A revision is under development; public material does not support clause-level conformance claims |
| [ISO/IEC 25010:2023](https://www.iso.org/standard/78176.html) | quality requirements, design and test objectives, acceptance criteria, and product-quality measures | Supplies a quality model, not the kit's operational procedure |
| [ISO 9241-210:2019](https://www.iso.org/standard/77520.html) and [ISO 9241-220:2019](https://www.iso.org/standard/63462.html) | human-centred analysis, design, evaluation, and improvement throughout the interactive-system life cycle | Support the HCD outcome, not the source-specific prototype-fidelity ladder |
| [NIST AI RMF 1.0 Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) | context and assumptions, role clarity, human oversight, TEVV, decision readiness, residual risk, and continual improvement | Voluntary outcomes are not an ordered checklist and do not validate a particular agent workflow |
| [NIST SSDF 1.1](https://csrc.nist.gov/pubs/sp/800/218/final) | risk-based secure development, review and testing, issue records, provenance, root-cause feedback, and process correction | Security-focused and outcome-oriented; implementation mechanisms remain contextual |
| [NIST SP 800-160 Vol. 1 Rev. 1](https://csrc.nist.gov/pubs/sp/800/160/v1/r1/final) | evaluatable, always-invoked, tamper-resistant, non-bypassable enforcement for material system constraints | The strict enforcement model applies when a deterministic security, privacy, safety, or equivalent invariant is claimed |
| [NIST Privacy Framework](https://www.nist.gov/privacy-framework) | privacy-risk governance, data-processing visibility, provenance, lineage, and ongoing privacy-risk re-evaluation and privacy-posture review | Does not select a target project's privacy values, lawful basis, retention, or access policy |
| [NIST SP 800-188](https://csrc.nist.gov/pubs/sp/800/188/final) | terminology and privacy/utility evaluation considerations for de-identified and synthetic data | Does not prove that a specific fixture is private or representative |
| [SPDX Build Profile](https://spdx.dev/learn/areas-of-interest/build/) and [SLSA provenance](https://slsa.dev/spec/v1.2/provenance) | traceability from source and build inputs to produced artifacts | Build provenance alone does not prove installed activation, effective runtime configuration, or live capability |

The resulting claim is deliberately bounded:

> The 28-rule catalog is sufficiently representative for the declared
> Discovery-Design-controlled Delivery Engineering Kit scope. It is not a
> complete implementation of ISO/IEC/IEEE software or system life-cycle
> standards and makes no certification or clause-level conformance claim.

The public ISO descriptions are sufficient for an outcome-level portfolio
crosswalk. Any later claim of conformance to exact ISO clauses requires an
authorized review of the full licensed text and a separate conformance record.

## Standards-Backed Shadow Dispositions

External backing supports the generic outcome. It does not promote a rule to
`cross-project-evidence-recorded` or `extraction-review-ready`.

| Rule | Primary external source outcome | Standards-backed outcome | Required neutralization before shadow catalog packaging |
| --- | --- | --- | --- |
| `ENG-PORT-DISC-003` | ISO/IEC/IEEE 12207 stakeholder/context and process-improvement lifecycle; AI RMF `MAP 1.1`, `MAP 2.3`, `MEASURE 2.1`–`2.3` | connect stakeholder context, requirements and constraints to measurable evaluation and correction | Do not require a controlled experiment for every Discovery question; require the smallest evidence method adequate for the material unknown |
| `ENG-PORT-DISC-006` | AI RMF `MEASURE 2.3`, `MEASURE 2.5`; SSDF `PW.8.2` | verify a material external capability in conditions relevant to the intended design | Keep endpoints, modes and smoke commands in a target adapter or binding |
| `ENG-PORT-DES-002` | ISO/IEC/IEEE 29148 requirements information throughout the lifecycle; SSDF `PW.1.2` design and risk decision records | identify, control and evaluate intended changes against the existing baseline | Keep concrete changed and unchanged product contracts in the target project |
| `ENG-PORT-DES-003` | ISO/IEC 25010 quality and acceptance evaluation; SSDF `PW.8.2` regression testing and recorded results | demonstrate behavior preservation with traceable evidence | Require a bidirectional old/new map only when both directions materially apply |
| `ENG-PORT-DES-006` | ISO/IEC/IEEE 12207 control of lifecycle processes; SSDF `PW.7`, `PW.8` and residual-issue handling | characterize compatibility-sensitive unchanged behavior and residual risk before change closure | Replace the local `frozen contract` term with a project-neutral compatibility-sensitive or declared-unchanged boundary |
| `ENG-PORT-DES-008` | AI RMF `MAP 2.2`, `MANAGE 1.1`, `MANAGE 1.3`, `MANAGE 1.4` | make a material human decision ready with context, options, consequences, uncertainty and residual risk | Keep UI layout, approver identity and product risk acceptance in the profile |
| `ENG-PORT-DES-011` | NIST SP 800-160 essential design criteria: non-bypassable, evaluatable, always invoked, tamper-resistant | ensure a claimed deterministic invariant is evaluatable and cannot be bypassed through supported entrypoints | Trigger strict reachability proof only for a material deterministic security, privacy, safety or equivalent invariant; keep host-tool inventories in adapters |
| `ENG-PORT-DES-012` | ISO 9241-210 lifecycle HCD activities; ISO 9241-220 HCD analysis, design and evaluation outcomes | collect proportional human-centred evidence before committing to a material interaction design | Keep the exact fidelity ladder as optional reference guidance |
| `ENG-PORT-DEL-003` | SSDF `RV.3.2`, `RV.3.4` root-cause pattern analysis and SDLC correction | use recurring root causes and findings to improve process or tooling | Keep the exact note-to-checklist-to-tool ladder as an optional implementation pattern |
| `ENG-PORT-DEL-004` | SSDF `PW.7`, `PW.8`; AI RMF `MANAGE 1.4` | close a material change with validation, drift review and explicit residual risk | Keep project test suites, thresholds and review tooling local |
| `ENG-PORT-DEL-007` | Privacy Framework `CM.AW-P6` provenance/lineage; NIST SP 800-188 privacy/utility evaluation considerations | establish provenance and privacy suitability for sensitive, sanitized or derived fixtures | Keep data classification, lawful use, allowed fixture content and fixture-level privacy proof in the target profile |
| `ENG-PORT-DEL-009` | SSDF `PS.3.1`, `PS.3.2`; SPDX Build Profile; SLSA provenance | prove current source/build/artifact identity before relying on an installed trial | Installed activation, effective configuration, live capability, client files, service identities, and host-specific preflight remain reference/profile/adapter technique until separately supported |

`ENG-PORT-DES-009` remains reference-only. ISO lifecycle improvement and SSDF
review/root-cause outcomes support review in general, but they do not establish
the source rule's universal mandatory post-change architecture/maintainability
gate or its named Ousterhout record.

## Profile And Adapter Boundary

The universal core owns project-neutral process invariants, evidence states,
stage authority, handoffs, and claim boundaries. Target-specific requirements
are composed around it through profiles and adapters, following the same
separation used by the API Engineering Kit.

A **profile** may supply:

- company governance, approval roles, risk tolerance and escalation routes;
- domain, legal, regulatory, privacy, security and safety obligations;
- architecture, data, persistence, observability, reliability and performance
  requirements;
- delivery model, repository policy, release gates and operational ownership;
- applicability and materiality bindings for core rules;
- product-specific acceptance thresholds and human decision authority.

An **adapter** may supply:

- repository commands and supported tool entrypoints;
- API, provider, runtime, client, deployment and observability integration;
- conversion between generic core records and local schemas or trackers;
- deterministic enforcement and evidence collection available in that
  environment;
- value-safe pointers to local evidence without copying restricted data into
  the generic kit.

Profiles and adapters must not:

- silently weaken or bypass a triggered core invariant;
- change a core rule's portability or evidence status;
- present company policy as a universal standard;
- embed secrets, private data, proprietary endpoints or product thresholds in
  the core;
- treat successful adapter wiring as proof of the parent product outcome;
- claim ISO, NIST or other conformance merely because the core contains a
  standards crosswalk.

A profile may mark a rule not applicable only with the target context, owner
and rationale recorded. A reference-only rule may be enabled as a local gate,
but that local enforcement does not strengthen its upstream authority without
the existing source-owned evidence review.

## Downstream Ownership

- KCS-16 owns wording stabilization, extraction selection and generic asset
  creation.
- KCS-17 owns the export manifest, evidence-strength metadata, compatibility
  boundary and handoff to the separate Engineering Kit project.
- The separate Engineering Kit project owns profile and adapter interfaces,
  role composition, integration trials and package readiness.
- A target project or company owns its profile values, adapters, local policy,
  operational controls and risk acceptance.

This boundary permits the kit to remain stable while learning from different
companies and project types without expanding the universal core for every
local requirement.
