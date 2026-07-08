# Test Suite Maintainability Aggregate Review: Batches 3-4

## Status

Aggregate review complete.

## Scope

Batches reviewed:

- Batch 3: semantic-review packet characterization
- Batch 4: initialize lifecycle characterization

Changed test file:

- `tests/kcs_adapters/test_mcp_desktop.py`

Runtime source files:

- none

## Aggregate Findings

- Both batches followed reverse freeze: no `src/` files changed.
- Both batches split independent assertion groups into private test helpers.
- Full Desktop characterization file passed after each batch.
- Graph/freeze policy checks passed.
- Ruff passed for the touched test file.
- No assertion was intentionally removed or weakened.

## Complexity Signals

Before Batch 3:

```text
max_cc: 41
cc_average: 7.35
high_complexity_functions: 88
```

After Batch 4:

```text
max_cc: 32
cc_average: 6.93
high_complexity_functions: 88
```

Overall since this branch started:

```text
max_cc: 56 -> 32
cc_average: 8.04 -> 6.93
```

Interpretation:

- the largest characterization tests are substantially easier to inspect;
- high-complexity count did not drop yet because the suite still contains many
  broad scenario tests;
- further work should continue only with explicit scenario-level questions, not
  broad file mining.

## Triage

`map_error`:

- no

`process_error`:

- no

`architecture_error`:

- no

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- full `tests/kcs_adapters/test_mcp_desktop.py` passed;
- graph/freeze policy checks passed;
- Ruff passed for the touched test file.

Reviewed drift risks:

- prompt/instruction term checks remain all-term inclusions;
- forbidden terms remain explicit exclusions;
- semantic-review sentinel exclusion remains checked against full packet text;
- no source code changed.

Review-only drift risks:

- future scenario-builder extraction should be reviewed carefully so it does
  not hide workflow ordering or weaken exact payload assertions.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Promotion And Demotion Scan

Promotion candidates:

- none new.

Demotion candidates:

- none.

## Outcome

Pause after this aggregate checkpoint.

Next candidate, if explicitly approved:

- `test_draft_article_primary_selection_uses_pending_provider_candidate`

Reason to pause:

- this branch already reduced the file max from `cc=56` to `cc=32`;
- the next hotspot is a workflow scenario and should start with a fresh compact
  behavior frame.
