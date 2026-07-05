# Spec-first Engineering Playbook: Test Plan

The test plan says what proves correctness before implementation starts.

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

## Slice: KCS reviewer packet generation

## Happy Path Tests

- Generates reviewer packet for `flag_existing`.
- Generates reviewer packet for draft-only output.
- Includes blocker summary for incomplete candidate.
- Includes manual review reminder.
- Includes safe bundle refs and hashes.

## Forbidden Path Tests

- Rejects or blocks raw private input.
- Rejects unsafe private path values.
- Rejects publish flags set to true.
- Rejects missing required readiness fields.
- Rejects ambiguous reuse/search provenance.

## Fail-closed Tests

- Missing evidence basis blocks packet readiness.
- Missing action blocks packet readiness.
- Unknown or unsupported action blocks packet readiness.
- Incomplete candidate produces blocker, not draft.

## Stability Tests

- Golden JSON fixture validates.
- Golden Markdown snapshot contains required sections.
- JSON schema or typed model rejects unexpected required-field drift.

## Suggested Commands

```bash
uv run pytest tests/kcs_core/test_reviewer_bundle.py -q
uv run pytest tests/kcs_core/test_renderer.py -q
uv run python -m json.tool outputs/demo/multi_candidate_reviewer_packet/reviewer_packet.json
git diff --check
```
