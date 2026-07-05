# KCS-14 Slice 0 Migration Table

Use this table during documentation ownership cleanup to prove that constraints
were moved, referenced, or intentionally left unchanged instead of silently
deleted.

Status values:

- `pending`: not reconciled yet;
- `moved`: authoritative text moved to the new owner;
- `referenced`: source now points to the authoritative owner;
- `unchanged`: text remains in place because that file is the correct owner.

## Constraint Migration

| Constraint or decision | Old / current location | Target owner | Status |
| --- | --- | --- | --- |
| KCS-14 means Engineering and Codebase Design Hardening | README, Jira tracking, feature-engineering docs, local playbooks | `docs/internal/engineering-process/kcs-14-planning-decisions.md`, README, Jira tracking | pending |
| KCS-15 means deferred KCS Style and Markup Parity | README, Jira tracking, feature-engineering docs, historical refactor plan | `docs/internal/engineering-process/kcs-14-planning-decisions.md`, Jira tracking, active roadmap | pending |
| Narrow reopening of frozen development for KCS-14 only | README | README, planning decisions | pending |
| PAUX-7083 historical / PAUX-7103 hardening mapping | Jira tracking | `docs/internal/kcs-authoring-mvp-jira-tracking.md` | pending |
| Runtime behavior remains frozen during KCS-14 docs/process work | README, architecture/contracts, planning docs | architecture/contracts docs and KCS-14 planning decisions | pending |
| Python owns validation, decisions, rendering, bundle writing, and output safety | README, architecture/contracts, technical design | architecture/contracts and technical design | pending |
| Claude/provider output remains untrusted | README, architecture/contracts, technical design | architecture/contracts and technical design | pending |
| `ticket_ref` clean-ticket pipeline remains primary | README, technical design, Desktop refactor docs | technical design and README | pending |
| Manual/freehand drafting remains blocked | README, Desktop refactor docs, tests | architecture/contracts and technical design | pending |
| Local reviewer bundles remain local artifacts | README, data-handling baseline, reviewer-bundle docs | data-handling baseline and technical design | pending |
| `auto_publish_allowed=false` and `public_output_approved=false` remain stable | README, packet contracts, tests | architecture/contracts and packet contracts | pending |
| `approved_summary_resolution_steps_incomplete` prevents invented resolution details | README, tests, renderer/readiness behavior | architecture/contracts or technical design; README may reference | pending |
| Forbidden artifact/leak list | workflow drafts, review checklist, boundary questions, roadmap | data-handling baseline as canonical owner; process docs reference | pending |
| Agent-operable workflow is detailed process below AGENTS.md | local workflow draft, AGENTS.md | tracked engineering-process workflow doc after Slice 1 | pending |
| Official tool entrypoints are command-surface docs, not runtime behavior | roadmap, KCS-14 plan | tracked tool-entrypoints doc after Slice 2 | pending |
| Code map is advisory orientation before refactor | roadmap, KCS-14 plan | tracked engineering-process code-map artifact after Slice 5 | pending |
| Slice 6 refactor freeze list | Fable review, chat, planning decisions | `docs/internal/engineering-process/kcs-14-planning-decisions.md` | pending |
| Clean-ticket golden fixtures are sanitized/approved or local-ref skip-if-absent | planning decisions, data-handling baseline | planning decisions and future test-process doc | pending |
| Enforcement ladder for prose-to-check promotion | Fable review, chat | `docs/internal/engineering-process/kcs-14-planning-decisions.md` | pending |
| Expected deterministic checks by slice | Fable review, chat, planning decisions | `docs/internal/engineering-process/kcs-14-planning-decisions.md` and future slice-specific docs/tests | pending |
| Slice closeout measurement is value-safe process metadata, not runtime observability | Fable review, chat, roadmap disposition | `docs/internal/engineering-process/kcs-14-planning-decisions.md` | pending |
| Closeout records have a tracked destination | Fable review, planning decisions | `docs/internal/engineering-process/kcs-14-review-notes.md` | pending |
| Recurring review findings use one four-way classification | Fable review, planning decisions, local workflow draft | `docs/internal/engineering-process/kcs-14-planning-decisions.md` | pending |
| Slice 4 review packet checks require a file-based packet format | Fable review, planning decisions | future tracked review-context protocol doc | pending |
| Slice 1 unsupported-harness check covers active docs | Fable review, planning decisions | future Slice 1 process-baseline check | pending |

## Expanded Touched-List To Check

- `README.md`
- `AGENTS.md`
- `docs/internal/kcs-authoring-mvp-jira-tracking.md`
- `docs/internal/kcs-authoring-mvp-feature-engineering.md`
- `docs/internal/kcs-authoring-mvp-data-handling-baseline.md`
- `docs/internal/kcs-core-pipeline-architecture-and-contracts.md`
- `docs/internal/kcs-core-pipeline-technical-design.md`
- `docs/internal/kcs-desktop-authoring-refactor-plan.md`
- `docs/internal/kcs-core-pipeline-review-notes.md`
- `CONTRIBUTING.md`
- `engineering-playbook/`
- `local-docs/engineering-process/`

Slice 0 review evidence should include the final version of this table and the
grep output used to prove that active KCS-14/KCS-15 references are reconciled.
