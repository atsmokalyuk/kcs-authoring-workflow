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
- For every claimed end-to-end invariant, does the design map each supported
  entrypoint through user/app/model-controlled transitions to the first deterministic
  gate and identify every pre-gate or bypass path, including direct model
  responses and alternative host tools that can produce the same prohibited
  outcome?
- Is a model-controlled tool call treated as optional routing rather than as
  enforcement, and is any user-controlled prompt/command still classified as
  model-mediated unless it directly invokes the deterministic owner?
- Are material facts marked as confirmed, provisional, unknown, or rejected?
- Was only the smallest material question batch presented to the operator?
- Did the agent resolve repository-, research-, and feasibility-owned unknowns
  before asking the operator to diagnose uncertainty?
- When interaction, host UI capability, operator comfort, or cognitive load was
  materially uncertain, did the agent proactively offer the smallest safe
  fixture-only walkthrough or UX smoke before production implementation?
- Did UX evidence start at the cheapest fidelity that could answer the
  decision, with packaging, activation, restart, deployment, or installed-host
  work used only for a remaining host-dependent claim?
- If that UX evidence method was skipped, is there current evidence that the
  interaction is unchanged and proven, or small, familiar, reversible, and
  free of material comfort/host-capability uncertainty?
- If an existing runtime/API is required, was its exact endpoint, mode,
  response shape, and operating condition proven by fresh evidence or a
  bounded pre-implementation smoke rather than a fixture or adjacent endpoint?
- Before an installed-client/model/operator trial, was current source matched
  to the built artifact, installed files, client registry/cache, explicit
  enabled/activation state, reloaded runtime, every dependency service's
  observed process/revision and config-data identity, its exact required
  capability on the same live instance, and the deterministic installed-runtime
  preflight?
- For every stateful or side-effecting continuation, is duplicate/re-entrant
  submission behavior explicit and deterministic: one side effect, stable
  replay/no-op behavior, bounded replay state, conflicting replay rejection,
  and no stale ref consuming a newer pending operation?
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
- If the slice claims to resolve a parent incident, noisy input, or real
  operational failure, does the plan name the approved sanitized
  representative case and evidence level required to prove that outcome?
- Are fixture, synthetic feasibility, representative-case, and real
  operational evidence classified separately, without using synthetic success
  to close a stronger operational claim?
- Before Delivery closeout, is the intended diff isolated and committed (or
  explicitly deferred with operator approval), and is built/installed evidence
  traceable to that committed content?
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
- an end-to-end invariant whose supported entrypoint can produce a prohibited outcome
  before or around its first deterministic gate;
- a model-controlled tool call, prompt instruction, or successful model run
  was treated as proof that the deterministic enforcement path is mandatory;
- Delivery started while outcome, design, readiness, or authorization remained
  unconfirmed;
- design selection was treated as Delivery authorization;
- an enabling-slice success was treated as parent UX or integration approval;
- substantial implementation started before an unproved exact runtime/API
  dependency received its bounded operational feasibility check;
- an installed-client/model/operator trial was handed to the operator before
  source, built artifact, installed files/cache, explicit enabled/activation
  state, reloaded runtime, and deterministic installed-runtime preflight had
  matching identity evidence;
- operational evidence from a different dependency worktree, process,
  deployment, or earlier runtime instance was treated as proof for the current
  integration trial, or a generic health endpoint was treated as exact
  capability/provenance evidence;
- a stateful or side-effecting continuation can be submitted twice by the
  client/model and either repeat the side effect or invalidate a newer pending
  operation because no deterministic duplicate/replay contract was tested;
- a slice motivated by a named real operational failure was closed from
  fixture or synthetic feasibility evidence without the planned approved
  sanitized representative-case gate, or without narrowing the completion
  claim;
- a material repository slice was declared delivered or used to start the
  next material slice while its intended diff remained uncommitted, mixed with
  deferred work, or its installed artifact was not traceable to the committed
  content;
- an operator decision was requested without the context needed to judge fit;
- production UI implementation started while a materially unfamiliar
  interaction, host UI capability, operator-comfort, or cognitive-load unknown
  could have been resolved by a smaller fixture-only walkthrough or UX smoke;
- a successful UX smoke was treated as production design selection, Delivery
  authorization, or repeated-use comfort evidence;
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
