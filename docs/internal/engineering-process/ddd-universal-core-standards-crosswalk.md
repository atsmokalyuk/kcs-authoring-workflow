# DDD Universal Core Standards Crosswalk

Status: authoritative source-owned portfolio boundary and KCS-16 disposition
record for the later KCS-17 handoff. This record does not start KCS-17, assign
kit roles, implement orchestration, or claim kit readiness.

Date: 2026-08-13

## Decision

The generic Engineering Kit portfolio is a 28-rule universal-core catalog:
every current `ENG-PORT-*` candidate except `ENG-PORT-DES-005` and
`ENG-PORT-DEL-005`.

KCS-16 materialized that boundary as one machine-readable catalog:
`engineering-playbook/ddd-universal-core.json`. The catalog keeps portability
status, catalog lane, kit treatment, and authority independent so later tooling
cannot infer authority merely from membership in the universal core.

The 28 rules provide sufficient capability coverage for the declared kit
scope:

```text
Discovery -> Design -> controlled Delivery -> review/evidence -> handoff
```

Sufficient coverage does not mean that every rule has the same authority or
portability maturity. The catalog contains three operational strengths:

| Core lane | Rules | Intended kit treatment |
| --- | --- | --- |
| Field-evidence lane | `ENG-PORT-DISC-001`, `ENG-PORT-DISC-002`, `ENG-PORT-DISC-006`, `ENG-PORT-DES-001`, `ENG-PORT-DES-002`, `ENG-PORT-DES-004`, `ENG-PORT-DES-007`, `ENG-PORT-DES-010`, `ENG-PORT-DES-011`, `ENG-PORT-DEL-006`, `ENG-PORT-DEL-008`, `ENG-PORT-DEL-010`, `ENG-PORT-DEL-011`, `ENG-PORT-DEL-012` | Twelve independently ready rules are authoritative `extracted-beta`; `ENG-PORT-DES-001` and `ENG-PORT-DEL-006` remain non-authoritative field-evidence candidates until their existing per-rule gates close |
| Standards-backed shadow lane | `ENG-PORT-DISC-003`, `ENG-PORT-DES-003`, `ENG-PORT-DES-006`, `ENG-PORT-DES-008`, `ENG-PORT-DES-012`, `ENG-PORT-DEL-003`, `ENG-PORT-DEL-004`, `ENG-PORT-DEL-007`, `ENG-PORT-DEL-009` | KCS-16 may carry a neutralized descriptor only as non-normative shadow catalog metadata; it is not an extracted rule. Shadow evaluation must collect applicability, corrections, overhead, false positives, and limitations |
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

The KCS-16 extraction gate remained unchanged: only a rule that independently
reached `extraction-review-ready` could become an authoritative extracted beta
asset. Carrying a non-ready field-evidence, shadow, or reference descriptor in
the 28-entry catalog is a separate, non-extracted advisory packaging path.
KCS-17 must preserve that distinction in the export manifest, and the later
kit must not load any advisory treatment as rule authority.

## KCS-16 Disposition

KCS-16a stabilized the five evidence-triggered formulations:

- `ENG-PORT-DISC-002`: minimal evidence states remain separate from decision
  authority;
- `ENG-PORT-DES-004`: ownership identifies responsibility and authority but
  does not validate AI content;
- `ENG-PORT-DES-010`: the durable design record applies to material work and a
  reviewer-verifiable mechanical leaf exception remains available;
- `ENG-PORT-DEL-010`: duplicate and re-entrant safety is expressed as
  applicability and outcome invariants without mandating an API, storage, or
  replay mechanism;
- `ENG-PORT-DEL-012`: evidence level is proportional to the completion claim,
  and a production trial is not the default.

KCS-16b approved authoritative `extracted-beta` treatment for exactly:

- `ENG-PORT-DISC-001`, `ENG-PORT-DISC-002`, `ENG-PORT-DISC-006`;
- `ENG-PORT-DES-002`, `ENG-PORT-DES-004`, `ENG-PORT-DES-007`,
  `ENG-PORT-DES-010`, `ENG-PORT-DES-011`;
- `ENG-PORT-DEL-008`, `ENG-PORT-DEL-010`, `ENG-PORT-DEL-011`, and
  `ENG-PORT-DEL-012`.

The later three decisions are supported by `plesk_support` commit
`60acfecc401c8080483eaac11890082e175b0bc4` plus materially different KCS
contexts under `SR-DISC006-01`, `SR-DES002-01`, and `SR-DES011-01`. Their
active local contracts remain prospective evidence; local completion is not
claimed or required to repeat the observed decision effect.

`ENG-PORT-DES-001` and `ENG-PORT-DEL-006` retain
`external-trial-active` and advisory field-evidence treatment because their
result-dependent LED contracts remain open. The nine shadow and five
reference-only entries retain advisory treatment. No standards disposition or
catalog membership promoted a rule; the three new authoritative decisions use
independent field evidence only.

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
| `ENG-PORT-DES-003` | ISO/IEC 25010 quality and acceptance evaluation; SSDF `PW.8.2` regression testing and recorded results | demonstrate behavior preservation with traceable evidence | Require a bidirectional old/new map only when both directions materially apply |
| `ENG-PORT-DES-006` | ISO/IEC/IEEE 12207 control of lifecycle processes; SSDF `PW.7`, `PW.8` and residual-issue handling | characterize compatibility-sensitive unchanged behavior and residual risk before change closure | Replace the local `frozen contract` term with a project-neutral compatibility-sensitive or declared-unchanged boundary |
| `ENG-PORT-DES-008` | AI RMF `MAP 2.2`, `MANAGE 1.1`, `MANAGE 1.3`, `MANAGE 1.4` | make a material human decision ready with context, options, consequences, uncertainty and residual risk | Keep UI layout, approver identity and product risk acceptance in the profile |
| `ENG-PORT-DES-012` | ISO 9241-210 lifecycle HCD activities; ISO 9241-220 HCD analysis, design and evaluation outcomes | collect proportional human-centred evidence before committing to a material interaction design | Keep the exact fidelity ladder as optional reference guidance |
| `ENG-PORT-DEL-003` | SSDF `RV.3.2`, `RV.3.4` root-cause pattern analysis and SDLC correction | use recurring root causes and findings to improve process or tooling | Keep the exact note-to-checklist-to-tool ladder as an optional implementation pattern |
| `ENG-PORT-DEL-004` | SSDF `PW.7`, `PW.8`; AI RMF `MANAGE 1.4` | close a material change with validation, drift review and explicit residual risk | Keep project test suites, thresholds and review tooling local |
| `ENG-PORT-DEL-007` | Privacy Framework `CM.AW-P6` provenance/lineage; NIST SP 800-188 privacy/utility evaluation considerations | establish provenance and privacy suitability for sensitive, sanitized or derived fixtures | Keep data classification, lawful use, allowed fixture content and fixture-level privacy proof in the target profile |
| `ENG-PORT-DEL-009` | SSDF `PS.3.1`, `PS.3.2`; SPDX Build Profile; SLSA provenance | prove current source/build/artifact identity before relying on an installed trial | Installed activation, effective configuration, live capability, client files, service identities, and host-specific preflight remain reference/profile/adapter technique until separately supported |

The prior standards alignment for `ENG-PORT-DISC-006`, `ENG-PORT-DES-002`,
and `ENG-PORT-DES-011` remains bounded to the same generic outcomes and adapter
limitations recorded in the pre-promotion crosswalk. It neither caused nor
strengthened their promotion; the authoritative treatment comes only from the
source-owned cross-project evidence reviews named above.

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

- KCS-16 completed wording stabilization, extraction selection and generic
  catalog asset creation in `engineering-playbook/ddd-universal-core.json`.
- KCS-17 owns the export manifest, evidence-strength metadata, compatibility
  boundary and handoff to the separate Engineering Kit project.
- The separate Engineering Kit project owns profile and adapter interfaces,
  role composition, integration trials and package readiness.
- A target project or company owns its profile values, adapters, local policy,
  operational controls and risk acceptance.

This boundary permits the kit to remain stable while learning from different
companies and project types without expanding the universal core for every
local requirement.
