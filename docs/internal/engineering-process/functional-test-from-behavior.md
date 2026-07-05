# Functional Test From Behavior

Status: authoritative KCS-14 Slice 3 test-process specification.

This document defines how accepted behavior becomes executable tests before
implementation where practical. It is an engineering workflow surface, not a
runtime product contract.

## Purpose

Functional tests protect behavior while the codebase is refactored or extended.
For KCS-14, the goal is not to add broad test machinery. The goal is to make
future changes safer by turning slice acceptance criteria into explicit,
reviewable pytest scenarios.

## Ownership

- Slice plans own the behavior intent and acceptance criteria.
- This file owns the repository convention for turning behavior into tests.
- `docs/internal/engineering-process/spec-first-engineering-playbook/` owns
  reusable planning templates and examples.
- `docs/internal/kcs-authoring-mvp-data-handling-baseline.md` owns fixture and
  data-handling safety rules.
- `tests/` owns executable behavior, contract, safety, and provenance checks.

## Default Test Shape

Use BDD-shaped pytest by default. Do not introduce a BDD framework unless
plain pytest no longer keeps scenarios readable.

```text
Given = state, fixture, or precondition
When  = action, function call, CLI command, or tool call
Then  = behavior, contract, safety, failure, or output assertion
```

Good functional tests should make the boundary visible:

- what behavior is being protected;
- what input is allowed;
- what input is forbidden;
- what output contract is stable;
- what failure mode is expected;
- which fixture or synthetic setup proves the case.

## Slice Test Planning

For each implementation slice, decide before coding:

- happy-path behavior that must work;
- forbidden-path behavior that must block or fail closed;
- boundary behavior that protects schemas, privacy, persistence, or tool
  interfaces;
- regression cases from known bugs or prior review findings;
- golden or structural checks needed to protect stable output;
- fixture class and provenance requirements.

## Behavior-To-Code Workflow

Use this sequence for behavior or refactor changes:

1. Behavior definition.
   Describe expected behavior as scenarios, not as a list of files to edit.
2. Functional test spec.
   Translate behavior into executable scenarios: input, expected tool calls or
   outputs, blockers, files written or not written, and invariants.
3. Test-first skeleton.
   Write failing tests before implementation when practical. If a test cannot
   run yet, commit the scenario as an explicit `xfail` or pending test only
   when the reason and removal condition are documented.
4. Implementation.
   Change code only until the agreed scenarios and relevant regression tests
   are green.
5. Review.
   Review the diff against the behavior spec, functional tests, unchanged
   contracts, and the code map when available. Before the code map exists,
   review against touched contracts and authoritative docs.

## Persistent Slice Specs

When a slice needs persistent behavior/test specs, keep them with the tracked
slice plan instead of leaving them only in chat. In this repository, use:

```text
docs/internal/engineering-process/slice-plans/<slice>/behavior.md
docs/internal/engineering-process/slice-plans/<slice>/functional-tests.md
tests/.../test_<slice>_behavior.py
```

If this workflow is later extracted into a reusable engineering-spec kit, the
generic equivalent may become:

```text
specs/<slice>/behavior.md
specs/<slice>/functional-tests.md
```

`behavior.md` should state operator-defined behavior in scenario terms. Do not
start from file names or implementation steps.

`functional-tests.md` should translate behavior into executable scenarios:

- input;
- expected tool calls or outputs;
- blockers;
- files written or not written;
- invariants;
- related pytest tests;
- affected code-map nodes when the code map exists.

Example:

```text
Behavior:
  If the operator drafts a clean ticket with three KCS items, the tool returns
  split_required with all three candidates.
  If the operator selects all candidates, the tool drafts every draftable
  candidate once and reports blocked candidates with specific blocker codes.

Functional tests:
  test_multi_issue_ticket_returns_all_candidates
  test_operator_all_drafts_each_candidate_once
  test_blocked_candidate_reports_specific_blocker_without_manual_draft

affected_graph_nodes:
  - desktop_semantic_review
  - desktop_operator_selection
  - desktop_draft_tool
  - desktop_tool_results
```

## Agent Reminder Gate

The operator may give a coding prompt as a list of files, modules, or desired
edits. For behavior or refactor work, the agent must not treat that file list
as the behavior spec.

Before coding, the agent should verify that the current task has:

- behavior stated in operator/user terms;
- allowed inputs and forbidden inputs;
- stable output or contract expectations;
- explicit failure behavior;
- acceptance scenarios or tests to add/update.

If these are missing and cannot be resolved from tracked repo docs, the agent
must ask for a compact behavior frame before implementation. This gate is not
needed for typo-only, formatting-only, or explicitly scoped documentation edits
that do not affect behavior or contracts.

If a slice is documentation-only or process-only, use policy tests only when
the rule is mechanically decidable. Keep judgment-only design questions in the
review checklist.

## Golden Evaluation Policy

Golden checks may protect stable output only through:

- synthetic fixtures;
- approved sanitized clean-ticket fixtures that follow the data-handling
  baseline;
- structural assertions;
- schema/hash assertions.

Golden checks in this slice must not expand into article presentation parity.
Domain output quality, article style, command markup, and source-doc parity
belong to KCS-15 unless they already protect an existing runtime contract.

## Fixture Tiers

Committed fixtures:

- must be portable from a clean clone;
- may be synthetic;
- may be derived from clean tickets only when sanitized, approved, and
  privacy-scanned;
- must not contain raw tickets, private logs, provider payloads, credentials,
  customer identifiers, live domains, IPs, hostnames, license IDs, private
  paths, or raw Zendesk JSON.

Local-ref fixtures:

- may refer to approved local clean-ticket artifacts;
- must be skip-if-absent so the suite remains portable;
- must not require a specific operator machine, local path, or runtime bundle
  to pass normal repository tests;
- must not commit raw clean-ticket text or local debug artifacts.

Committed clean-ticket-derived fixtures must carry explicit provenance. Use a
metadata object equivalent to:

```json
{
  "input_class": "approved_sanitized_fixture",
  "fixture_provenance": {
    "source_type": "clean_ticket",
    "approval_ref": "approved-local-note-or-ticket",
    "approved_on": "YYYY-MM-DD",
    "sanitized_by": "approved_cleanup_form_or_operator",
    "privacy_scan": "passed"
  }
}
```

## Forbidden-Path Tests

When a slice touches safety, data handling, packets, persistence, renderer
output, Desktop tools, reviewer bundles, or publication boundaries, include
forbidden-path tests where practical.

Examples:

- raw/private input is rejected;
- unknown source refs are rejected;
- unsafe output is not echoed into errors, logs, packets, or artifacts;
- `auto_publish_allowed=false` remains explicit;
- manual/freehand drafting remains blocked;
- missing evidence blocks instead of producing reviewer-ready output.

## Refactor Safety

Before a behavior-preserving refactor, identify the boundary being moved and
the tests that prove it remains stable.

Refactor tests should protect:

- public/runtime contracts;
- packet schemas and decision statuses;
- privacy and fail-closed behavior;
- Desktop/tool surface behavior;
- reviewer-bundle output rules;
- stable golden/structural output when already part of current behavior.

Do not change test assertions during a refactor unless the slice explicitly
marks a reviewed behavior change.
