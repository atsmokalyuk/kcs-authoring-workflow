# Spec-first Engineering Playbook: Clarifications

Use this file before implementation to remove ambiguity from a slice. Do not
start code work until the slice has a bounded goal, operator, allowed inputs,
forbidden inputs, output contract, and failure behavior.

Do not start architecture from a proposed implementation. First establish:

- the outcome the operator or user needs;
- the nominal behavior described by code or documentation;
- the operational behavior actually demonstrated by current evidence;
- the intended user entrypoint and interaction;
- the target behavior to confirm;
- the material facts and unknowns that can change the design.

Use these fact states:

- `confirmed`: supported by current tracked evidence or an operator decision;
- `provisional`: a bounded working assumption that still needs validation;
- `unknown`: no sufficient evidence or decision exists;
- `rejected`: evidence or an operator decision ruled it out.

Do not treat missing evidence as permission, success, an empty value, or a
default. Keep a complete unknown inventory in the slice plan. Ask the operator
only the smallest batch needed for the next decision. More than five material
questions before one decision is a signal to narrow the slice boundary.

## Design Uncertainty And Decision Readiness Protocol v0

This is an actor-neutral process contract. It does not define a Designer role,
runtime state service, prompt, tool registry, or multi-agent orchestration.

Trigger the protocol when:

- the operator says `not sure`, `iterate`, or equivalent;
- the operator agrees with the outcome but has not selected the behavior;
- the operator may lack evidence needed for the requested decision;
- a material UX, behavior, privacy, integration, maintenance, or failure-path
  unknown remains;
- an enabling slice succeeds but the parent design is not selected;
- two materially different options remain viable;
- new evidence invalidates a prior assumption;
- a proposed DDD transition has no exact approval record.

The operator is not required to diagnose the uncertainty. The acting agent
must first classify each unknown as:

- `repository-owned`: resolve from tracked contracts, code, tests, and history;
- `research-owned`: resolve through permitted external or reference research;
- `feasibility-owned`: resolve through an isolated, separately authorized
  experiment with a bounded evidence budget;
- `operator-owned`: preference, policy, risk, or material product trade-off.

Resolve the first three classes autonomously when permitted. Ask the operator
only at a material `operator-owned` fork or when the evidence budget reaches a
stop condition.

### Independent Approval Ledger

Keep three orthogonal state dimensions:

```text
Outcome agreement: unconfirmed | agreed | reopened | rejected
Design selection: open | uncertain | evidence_gathering |
  ready_for_operator_selection | selected | iterate | rejected
Delivery authorization: locked | authorization_requested | authorized | revoked
```

No value implies another. In particular:

- outcome agreement does not select a design;
- design selection does not authorize Delivery;
- feasibility evidence does not approve parent UX or integration;
- a recommendation cannot approve itself;
- silence, positive wording, or elapsed time cannot unlock Delivery.

Delivery may start only when the outcome is `agreed`, the design is `selected`,
Delivery is `authorized`, the Operator Decision Readiness packet is complete,
no material blocker remains, and a material slice's selected design,
authorization, acceptance gates, unchanged contracts, and stop conditions are
recorded in its tracked `slice-plans/` artifact.
Chat-only design is not a Delivery-ready record.

### Operator Decision Readiness Packet

Before asking the operator to select, iterate, reject, or authorize, show:

| Field | Required content |
| --- | --- |
| Decision | Exact decision requested now |
| Visible information | Evidence the operator will actually see, including relevant context needed to judge fit |
| Sufficiency | Why that information is enough for this decision and what it does not prove |
| Options | Materially viable choices, including defer or stop where applicable |
| Consequences | Operator workflow, cognitive load, behavior, maintenance, safety, and integration trade-offs |
| Uncertainty / failure path | Remaining unknowns, failed assumptions, and what happens if evidence is insufficient |
| Recommendation | Evidence-backed agent recommendation; never self-approval |

The agent may propose `ready_for_operator_selection`; only the operator may
select, iterate, reject, authorize Delivery, or revoke authorization.

### Evidence Methods And Stop Conditions

Choose the lightest sufficient method: repository analysis, reference research,
cognitive walkthrough, low-fidelity comparison, bounded operator trial,
isolated feasibility slice, or predeclared repeated model/RAG trial.
Escalate evidence fidelity only for an unknown the cheaper method cannot
resolve:

```text
static example or wireframe
  -> clickable fixture without product/runtime installation
  -> isolated component or protocol harness
  -> installed-host smoke
  -> production-like trial
```

Do not choose an installed extension, packaged client, service deployment, or
runtime restart merely to evaluate labels, layout, information density, or
decision flow. Use that heavier level only when the remaining decision depends
on the real host's rendering, lifecycle, permissions, navigation, or tool
routing. Record why each escalation is necessary and stop once the material
decision is ready.

When a material design depends on an unfamiliar interaction, an unproved host
UI capability, or an operator-comfort/cognitive-load judgment, the acting agent
must proactively offer the smallest safe pre-implementation UX evidence method.
Do not wait for the operator to request a prototype after production
implementation has started.

Use a fixture-only walkthrough, wireframe, click-through, or isolated UX smoke
when it can expose the real decision context and interaction at materially
lower cost than production implementation. Predeclare:

- the UX decision the operator will be able to make;
- the representative safe fixture and host/runtime condition;
- which interaction and information-density claims are exercised;
- what remains simulated or unproved;
- permitted presentation corrections and the evidence/time bound;
- the stop condition.

The operator evaluates fit, comfort, and trade-offs from the evidence; the
operator is not required to invent the test method. A successful UX smoke may
move Design to selection or iteration. It does not select the production
design, authorize production Delivery, or prove repeated-use comfort. Record a
skip only when the interaction is materially unchanged and already proven, or
when the choice is small, familiar, reversible, and has no meaningful
cognitive-load or host-capability uncertainty.

When a design depends on an existing runtime, service, tool, or API, identify
the exact endpoint, mode, request, response shape, and operating condition that
the slice needs. Before finalizing the dependent design or starting substantial
implementation, either cite fresh tracked evidence for that exact path or run
one bounded safe operational smoke. A fixture, documented schema, SDK type,
adjacent endpoint, or earlier smoke under different conditions is nominal
evidence, not operational proof.

Predeclare the smoke's feasibility claim, safe input, fixed bounds, expected
shape/invariants, allowed side effects, failure handling, and stop condition.
One successful smoke proves only that bounded path is feasible. Stability,
quality, and production readiness require their own acceptance gates.

Stop evidence work when the operator has enough information for the material
decision, the next unknown is operator-owned, the evidence budget is exhausted,
repeated trials add no decision-relevant information, a non-negotiable blocker
appears, or the operator pauses or rejects the work.

A small reversible implementation choice inside an already authorized slice
does not require this protocol. State the default and continue when its cost of
error is low and it cannot change behavior or approved contracts.

## Slice Template

```markdown
# Slice: <name>

## Goal
What are we building?

## Requested outcome
What user or operator result is needed, independent of a proposed solution?

## Current operational reality
What behavior is actually demonstrated? What is only nominal or documented?

## Intended entrypoint and UX
Where does the user start and what interaction should they experience?

## Target behavior
What behavior must be confirmed before architecture is proposed?

## Fact register
Which material facts are confirmed, provisional, unknown, or rejected?

## Complete unknown inventory
What remains unknown, including questions not yet issued to the operator?

## Next material question batch
What is the smallest set of questions needed for the next decision?

## Approval ledger
Outcome agreement: unconfirmed / agreed / reopened / rejected
Design selection: open / uncertain / evidence_gathering /
  ready_for_operator_selection / selected / iterate / rejected
Delivery authorization: locked / authorization_requested / authorized / revoked

## Operator Decision Readiness
Decision:
Visible information:
Sufficiency and limits:
Options:
Consequences:
Uncertainty / failure path:
Recommendation:

## User / operator
Who uses this?

## Allowed inputs
What data may enter?

## Forbidden inputs
What must never enter?

## Output contract
What must be produced?

## Failure behavior
How should it fail closed?

## Tests / evals
What proves correctness?

## Acceptance criteria
What must be true before merge?

## Proposed solution
Only after target behavior is confirmed: what implementation is proposed?

## Review checklist
What should reviewer verify?
```

## Slice: KCS reviewer packet generation

## Goal

Produce reviewer-only KCS packets from accepted, sanitized workflow outputs.
The packet must explain the recommended KCS action, evidence basis, validation
state, blockers, risks, and manual review boundary.

## User / operator

- Support engineer preparing KCS output.
- KCS reviewer checking whether the output is ready for review.
- Technical lead auditing the workflow behavior.

## Allowed inputs

- Sanitized clean-ticket evidence.
- Validated semantic extraction output.
- Deterministic KCS action decision.
- Renderer output.
- Readiness validation report.
- Local reviewer bundle metadata.
- Explicit existing-article references detected from sanitized evidence.

## Forbidden inputs

- Raw Zendesk ticket bodies.
- Raw internal comments.
- Credentials, tokens, private endpoints, private paths.
- Unsanitized customer identifiers.
- Existing public KB article body unless fetched by an approved read-only
  adapter and explicitly marked as source evidence.
- LLM-generated article prose that bypasses Python validation.

## Output contract

The packet must include:

- `candidate_kcs_action`
- reviewer readiness state
- bundle manifest or bundle reference
- evidence basis
- reuse/search or reuse-evidence provenance
- draft, update, flag, no-article, or blocker content summary
- blockers
- risks
- related candidate outcomes
- manual review reminder
- `auto_publish_allowed=false`
- `public_output_approved=false`

## Failure behavior

Fail closed when:

- required packet fields are missing;
- unsafe values are detected;
- provenance is ambiguous;
- reuse/search state is overstated;
- candidate evidence is incomplete;
- output would imply publish readiness.

## Tests / evals

- Golden reviewer packet fixture.
- JSON schema or typed model validation.
- Tests for missing required fields.
- Tests for unsafe input echo blocking.
- Tests for `flag_existing`, `draft_only`, and blocked candidates.
- Tests proving no Zendesk write and no auto-publish.

## Acceptance criteria

- Reviewer packet is machine-readable and human-readable.
- Output is reviewer-only.
- Public output is not approved.
- Auto-publish is disabled.
- Provenance is explicit.
- Failure states are actionable and safe.

## Review checklist

- Does the packet satisfy the output contract?
- Does it preserve the privacy boundary?
- Does it fail closed?
- Does it avoid unsafe input echo?
- Is the output schema stable?
- Are happy and forbidden paths covered by tests?
- Did AI invent behavior outside the spec?
