# Spec-first Engineering Playbook: Test Plan

The test plan says what proves correctness before implementation starts.
Detailed repository rules for converting behavior into tests live in
`docs/internal/engineering-process/functional-test-from-behavior.md`.

## Test Categories

- Happy path.
- Forbidden input.
- Missing required field.
- Unsafe output echo.
- Fail-closed behavior.
- Schema stability.
- Regression fixture.

## BDD-shaped Pytest Convention

Use BDD-shaped pytest by default, not `pytest-bdd` or `.feature` files.

Write test names and comments so the behavior is readable as:

```text
Given = state, fixture, or precondition
When  = action, function call, or tool call
Then  = contract assertion, safety assertion, or output assertion
```

Example:

```python
def test_reviewer_packet_does_not_treat_explicit_reference_as_live_search():
    # Given: sanitized evidence contains an explicit public KB URL.
    evidence = _sanitized_ticket_with_public_kb_reference()

    # When: reviewer packet generation runs.
    packet = build_reviewer_packet(evidence)

    # Then: provenance is explicit-reference detection, not live search.
    assert packet["reuse_search"]["status"] == "explicit_reference_detected"
    assert packet["reuse_search"]["search_backend"] == "not_connected_for_demo"
    assert packet["reuse_search"]["public_url_verified_online"] is False
```

Use a dedicated BDD runner only when plain pytest no longer keeps scenarios
readable or when non-Python reviewers need shared `.feature` files.

## Slice Test Sections

Use these sections when drafting a slice-specific test plan:

- happy path tests;
- forbidden path tests;
- fail-closed tests;
- schema or contract stability tests;
- golden, structural, or hash checks;
- fixture provenance and privacy checks;
- commands to run from
  `docs/internal/engineering-process/tool-entrypoints.md`.

## Fixture Policy

Use synthetic fixtures by default. Committed clean-ticket-derived fixtures must
be sanitized, approved, privacy-scanned, portable, and marked with explicit
provenance. Local clean-ticket refs must be skip-if-absent and must not make the
suite machine-dependent.
