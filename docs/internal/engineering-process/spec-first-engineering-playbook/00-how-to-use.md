# Spec-first Engineering Playbook: How To Use

This is a tracked development playbook for spec-first implementation slices.
It is not a runtime contract and does not replace product, architecture, or
data-handling documents.

Use it when the operator says:

```text
plan new slice
create implementation plan
создай план реализации фичи
```

## Workflow

1. Read `AGENTS.md`.
2. Read the relevant files in this directory.
3. Separate the requested outcome from any proposed solution. Record the
   current operational behavior, intended user entrypoint, and target behavior
   before proposing architecture.
4. Record material facts as `confirmed`, `provisional`, `unknown`, or
   `rejected`. Absence of evidence does not establish a default value.
5. Draft or update the slice spec before implementation.
6. Keep the complete inventory of material unknowns in the slice spec, but ask
   the operator only the smallest question batch needed for the next decision.
7. Record outcome agreement, design selection, and Delivery authorization as
   independent facts. Do not infer one from another.
8. Keep Delivery locked before changing runtime behavior, privacy boundaries,
   schemas/contracts, persistence, integrations, or public/reviewer output
   until the selected design has separate Delivery authorization.
9. Map every observable acceptance criterion to a deterministic gate, a
   bounded model trial, or a named human-review gate.
10. Implement only the selected and authorized slice.
11. Report changed files, unchanged contracts, validation run, and open risks.

If more than five material questions are required before the next decision,
narrow the feature boundary before asking them. This is a scope signal, not a
quota that permits hiding unresolved assumptions.

## Experimental And Model-Mediated Slices

Before running a process experiment or evaluating nondeterministic behavior,
predeclare:

- fixtures and provenance;
- trial count and fixed conditions;
- stable behavioral invariants;
- acceptable variance and success threshold;
- permitted corrections;
- acceptable operator/process overhead and false-positive rate;
- value-safe observations required for closeout.

A single successful run proves feasibility only. Close the experiment with an
evidence-based `expand`, `iterate`, or `stop` decision using baseline-to-result,
correction, overhead, false-positive, and drift evidence.

## Design Uncertainty And Decision Readiness

Use the role-neutral protocol in `01-clarifications.md` when the operator is
uncertain, the evidence visible to the operator may be insufficient, two
material options remain viable, or a DDD transition lacks an exact approval
record.

The stage-transition checkpoint must state:

- current DDD stage;
- outcome agreement state;
- design selection state;
- Delivery authorization state;
- exact next behavior change proposed;
- remaining material unknowns;
- evidence the operator will see for the next decision.

`select` means that a design was selected; it does not authorize Delivery.
`authorize_delivery` is a separate operator decision. A compound
`select_and_authorize_delivery` may record both facts only when the operator
explicitly grants both.

Phrases such as `go next`, `continue`, `looks good`, or agreement with the
benefit may continue work already inside an approved boundary. They do not by
themselves select a new design or authorize a new behavior-changing slice.

## Slice Planning Location

By default, slice plans are drafted in chat and confirmed by the operator before
implementation.

Use this playbook as the planning template, but do not overwrite the playbook
files for every slice.

If a slice plan needs to persist across sessions, save it under:

```text
docs/internal/engineering-process/slice-plans/
```

Example:

```text
docs/internal/engineering-process/slice-plans/
  kcs-14-style-markup-parity.md
```

Persistent slice plans are engineering artifacts. Commit them when they become
authoritative planning inputs for a reviewable slice; keep temporary personal
notes in `local-docs/`.

## Repository Boundary

These playbook files are dev-time engineering instructions. They are not
runtime artifacts.

Do not commit:

```text
local-docs/
local-data/
runtime reviewer bundles
raw clean tickets
old or unpromoted demo outputs
```

If a local runtime artifact is useful for tests or demo, manually distill it
into a safe fixture or approved showcase artifact first.
