# KCS-15.1 `PLESK_INFO` Trigger Parity

Status: completed on 2026-07-22 at commit `666e5ca`.

## Requested outcome

A reviewer-ready article that uses `PLESK_INFO` for a white/gray Plesk error or
message must not be blocked merely because its text contains words such as
`error`, `failed`, `denied`, or an HTTP error code.

## Operational baseline

- The Plesk Style Guide and Style Triggers define `PLESK_ERROR` for pink Plesk
  errors, `PLESK_WARN` for yellow warnings, and `PLESK_INFO` for white/gray
  Plesk errors and messages.
- `src/kcs_adapters/zendesk_markup_quality.py` currently infers presentation
  class from lexical content and emits blocker
  `plesk_info_used_for_error_message` for error-like `PLESK_INFO` text.
- `evals/kcs_markup_patterns_v1.jsonl` repeats the informational-only rule.
- The validator receives rendered source text, not the original Plesk UI
  background/presentation metadata. It cannot reliably infer the correct
  trigger from error vocabulary.

## Target operator experience

The operator may use the source-defined `PLESK_INFO` trigger for a white/gray
Plesk error without receiving a false markup blocker. All unrelated quality,
safety, privacy, structure, and readiness findings remain unchanged.

## Approved behavior change

- Remove lexical reclassification of `PLESK_INFO` content.
- Remove the `plesk_info_used_for_error_message` blocker.
- Align compact pattern guidance with the source definition.
- Add a focused regression fixture using source-valid error-like
  `PLESK_INFO` content.
- Preserve the existing 14-pattern registry shape in this slice.

## Out of scope

- automatic choice among `PLESK_ERROR`, `PLESK_WARN`, and `PLESK_INFO`;
- new packet or UI-presentation metadata;
- missing MySQL, unselectable, splitter, or other markup patterns;
- renderer changes;
- title, Symptoms, Cause, Resolution, language, or tagging parity;
- RAG integration;
- semantic ownership, provider/evaluation, candidate scope, Desktop/MCP,
  package guidance, or KCS-14.5 incident behavior;
- model trials or installed Desktop canaries.

## Acceptance-to-gate mapping

| Acceptance criterion | Gate |
| --- | --- |
| Error-like `PLESK_INFO` content produces no `plesk_info_used_for_error_message` finding. | deterministic focused regression |
| Removing the false blocker does not remove unrelated findings from the existing composite style fixture. | deterministic unit test |
| Pattern guidance states that `PLESK_INFO` covers white/gray Plesk errors and messages. | deterministic pattern-registry test |
| No source, test, package, or contract in the scoped KCS-14.5 incident workstream changes. | deterministic staged-diff review |
| Full repository tests, Ruff on touched Python, and `git diff --check` pass. | deterministic local validation |

No model trial or human content-quality gate is needed because the changed rule
is exact, source-backed, and locally testable.

## Unchanged contracts

- packet and schema versions;
- renderer HTML shape;
- finding/report schema and all remaining finding IDs;
- Desktop/MCP tool names, arguments, results, and workflow states;
- persistence and reviewer bundle layout;
- privacy, evidence, safety, and readiness blockers;
- reviewer-only, no-write, no-publish, and no-customer-reply boundaries;
- KCS-14.5 semantic ownership and native selection behavior.

## Stop condition

Stop and return to design if the change requires UI-presentation metadata, a
new schema, automatic trigger inference, renderer output changes, or any touch
to the retained KCS-14.5 incident control surface.

## Closeout

KCS-15.1 made the approved deterministic change: the lexical
`PLESK_INFO` blocker was removed, compact source guidance was corrected, and
focused fixtures protect the source-defined white/gray error or message case.
No model stability, automatic trigger selection, RAG behavior, or drafting UX
claim was promoted.

Discovery, Design, and Delivery were all exercised for this bounded slice. The
slice itself had a confirmed outcome, selected behavior, deterministic gates,
explicit unchanged contracts, and operator authorization to implement.

### Follow-on transition evidence

The process failure occurred after KCS-15.1, not inside its runtime change:

- `go next` was interpreted too broadly even though it did not identify or
  authorize the next behavior-changing slice;
- the operator could not judge whether an article fit the ticket when the
  proposed view showed the article without the relevant ticket context;
- KCS-15.2a adapter feasibility did not select the KCS-15.2b operator
  comparison UX or authorize parent integration;
- the optional operator-confirmed drafting-scope idea remained a proposed
  design question, not the definition of all KCS-15 work.

These observations justify the local role-neutral protocol and further field
evidence. One transition does not establish cross-project portability or a
dedicated Designer role.

### Rule evidence

| Rule | Evidence from the transition | Verdict |
| --- | --- | --- |
| `ENG-PORT-DISC-005` | The operator clarified that the agent should research autonomously and present a result for approval or steering, rather than ask the operator to diagnose uncertainty. | field-test |
| `ENG-PORT-DES-007` | Outcome agreement, next-design selection, and Delivery authorization were not preserved as separate facts after `go next`. | retain locally and field-test |
| `ENG-PORT-DES-008` | Article-only presentation omitted relevant ticket context required for an informed fit/update decision. | retain locally and field-test |
| `ENG-PORT-DEL-008` | Adapter readiness answered a feasibility question but could not approve the parent operator flow or integration. | retain locally and apply to KCS-15.2 |

The protocol change affects development governance only. It does not reopen the
completed `PLESK_INFO` behavior or authorize follow-on runtime work.
