# Spec-first Engineering Playbook: Review Checklist

Use this checklist for code, docs, contracts, and demo artifacts.

## General Review

- Does the diff match the stated slice?
- Does the material review packet name an `Active Slice Plan` under
  `docs/internal/engineering-process/slice-plans/`?
- Does the plan authorize the exact changed Delivery phase, cover the diff and
  acceptance gates, and leave every listed locked phase untouched?
- Was the requested outcome separated from the proposed solution before
  architecture was selected?
- Does the plan distinguish nominal behavior from demonstrated operational
  behavior and identify the intended entrypoint/UX?
- Are material facts marked as confirmed, provisional, unknown, or rejected?
- Was only the smallest material question batch presented to the operator?
- Did the agent resolve repository-, research-, and feasibility-owned unknowns
  before asking the operator to diagnose uncertainty?
- If an existing runtime/API is required, was its exact endpoint, mode,
  response shape, and operating condition proven by fresh evidence or a
  bounded pre-implementation smoke rather than a fixture or adjacent endpoint?
- Are outcome agreement, design selection, and Delivery authorization recorded
  independently?
- If an operator decision was requested, were the exact decision, visible
  information, sufficiency, options, consequences, and uncertainty/failure path
  present?
- Are unrelated files untouched?
- Are generated/runtime/private artifacts excluded?
- Are contracts preserved or intentionally changed?
- Are tests added or updated where behavior changed?
- Does every observable acceptance criterion map to a deterministic,
  bounded-model, or named human-review gate?
- Does README or related documentation need an update?
- Does the change avoid unsupported version, model, command, or API claims?

## Compact Ousterhout Review Gate

Trigger this gate before closeout for a material implementation, refactor,
deployment, or integration change, including a new/moved module or service,
cross-module dependency, public/internal interface, ownership boundary,
persistence or failure boundary, deployment topology, material abstraction, or
material internal algorithm/control-flow complexity.

A small leaf behavior correction may record `not triggered` only when it adds
or moves none of those boundaries and does not materially change internal
complexity. File size or a `src/` path alone is a smell, not proof that the gate
triggered. A large internal change is reviewed even when its external interface
remains stable.

For `reviewed`, record the full form:

```text
Ousterhout gate: reviewed
Trigger:
Complexity hidden:
Owner and what it must not know:
Interface depth and caller cognitive load:
Information leakage and change amplification:
Complexity removed, moved, or added:
Residual design risk:
Verdict: pass | revise | reject
```

For a valid leaf exception, record only:

```text
Ousterhout gate: not triggered
Not-triggered reason: small leaf change; no material boundary, abstraction,
  algorithm, control-flow, or internal-complexity change
```

If triggered, a missing record or unresolved `revise` / `reject` verdict is a
review blocker. This is a named human-review gate. Policy tests may enforce the
record shape but must not claim to judge module depth or design quality.

## Review Severity

Classify findings as blockers or warnings.

Blockers:

- missing or nonexistent Active Slice Plan for a material change;
- implementation outside the selected boundary or inside a still-locked
  Delivery phase;
- behavior regression;
- broken or unstable contract;
- missing test or fixture for changed behavior;
- unsafe data handling or unsafe input echo;
- raw/private/runtime artifact touch;
- README or docs claim that contradicts actual behavior;
- architecture drift that moves decisions out of deterministic Python code;
- Delivery started while outcome, design, readiness, or authorization remained
  unconfirmed;
- design selection was treated as Delivery authorization;
- an enabling-slice success was treated as parent UX or integration approval;
- substantial implementation started before an unproved exact runtime/API
  dependency received its bounded operational feasibility check;
- an operator decision was requested without the context needed to judge fit;
- a triggered Ousterhout review is missing or has an unresolved `revise` /
  `reject` verdict.

Warnings:

- naming/import cleanup;
- small documentation clarity issue;
- low-risk test gap with a clear follow-up;
- maintainability concern that does not change current behavior.

## Privacy Review

- No raw ticket bodies.
- No raw internal comments.
- No credentials, tokens, private endpoints, or private paths.
- No unapproved customer identifiers.
- No unsafe input echo in errors, logs, packets, or test fixtures.

## Runtime Review

- Does Python remain the deterministic owner?
- Does the slice fail closed?
- Are publish-safety flags explicit?
- Are unknown states blocked or reported?
- Are runtime payloads machine-stable?

## AI Boundary Review

- Did AI invent behavior outside the spec?
- Is any LLM output treated as untrusted input?
- Is semantic review bounded to candidate identification?
- Are KCS decisions made by code, not by the model?
- For model-mediated acceptance, were fixtures, `N`, conditions, invariants,
  threshold, corrections, overhead, and stop conditions declared before the
  trial?
- Are results evaluated by stable behavior rather than exact model wording?

## Discovery Failure Signals

Treat these as findings requiring the design to return to clarification:

- architecture was proposed before target behavior was confirmed;
- nominal code or documentation behavior was treated as operational proof;
- an unknown was silently converted into a default or permission;
- the operator received the complete domain question inventory instead of the
  smallest next decision batch;
- more than five material questions are needed without narrowing the slice;
- the operator was asked to diagnose uncertainty that repository analysis,
  permitted research, or a bounded feasibility check could resolve;
- `go next`, positive wording, feasibility success, or a recommendation was
  treated as approval for a new behavior-changing slice.

These are judgment-based review signals. Do not add a deterministic blocker
that claims to infer them from prose.

## Documentation Review

- Does README remain accurate?
- Do docs describe implemented behavior, not desired future behavior?
- Are future slices labeled as future work?
- Are public/reviewer output claims consistent with `auto_publish_allowed=false`
  and reviewer-only boundaries?
- Are local-only process notes kept under `local-docs/`?

## Slice: KCS reviewer packet generation

- Does the packet satisfy acceptance criteria?
- Does it preserve the privacy boundary?
- Does it fail closed?
- Does it avoid unsafe input echo?
- Is output schema stable?
- Are happy and forbidden paths tested?
- Does the packet avoid overstating reuse/search?
- Does it clearly state reviewer-only status?
