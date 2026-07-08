# KCS-14 Slice 9 Target 6: Provider Runtime Config Validation

## Status

Implementation complete; staged-diff review required before commit.

## Scope

Graph node:

- `provider_handoff_boundary`

Changed file:

- `src/kcs_adapters/claude_provider.py`

Graph metadata:

- `docs/internal/engineering-process/code-review-graph.json`

Related focused tests:

- `tests/kcs_adapters/test_claude_provider.py`

## Entry Question

Can `DirectHttpRuntimeConfig.__post_init__()` be split into private validation
predicates while preserving runtime-only endpoint/credential boundaries?

## Finding

`DirectHttpRuntimeConfig.__post_init__()` was the provider target max
complexity point after Target 5. It mixed endpoint URL validation, runtime API
key validation, model normalization, and response-size validation in one
dataclass hook.

The code is private runtime configuration validation. It is a good
behavior-preserving refactor target because the public dataclass fields,
`repr`, serialized provider config, preflight report, and provider smoke
behavior are already covered by focused tests.

## Decision

Extract private validators:

- `_ensure_safe_runtime_endpoint_url()`
- `_ensure_safe_runtime_api_key()`
- `_ensure_safe_runtime_max_response_bytes()`

Keep `DirectHttpRuntimeConfig.__post_init__()` as the orchestration point that
validates runtime-only values and normalizes the model reference.

## Ousterhout Lens

- Information hiding: endpoint, API-key, and byte-limit validation details now
  have named owners.
- Deep module: all runtime-config validation remains inside `claude_provider.py`;
  no public API or new module was introduced.
- Change amplification: future endpoint or credential validation changes should
  touch one predicate family.
- Avoid classitis: the split is private functions, not new classes or adapter
  layers.
- Boundary discipline: runtime endpoint and credential data still never enter
  serializable packets.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- focused provider tests passed;
- unsafe endpoint URL rejection tests passed;
- unsafe model reference rejection tests passed;
- API-key header-injection rejection test passed;
- config serialization/preflight secret-redaction test passed;
- Ruff passed for the touched source and related tests;
- complexity sensor recorded before/after shape.

Old-to-new mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| endpoint type/control-character/URL-shape validation | `_ensure_safe_runtime_endpoint_url()` | Provider runtime endpoint tests passed. |
| API-key non-empty/header-injection validation | `_ensure_safe_runtime_api_key()` | API-key rejection test passed. |
| model ref normalization | unchanged `_safe_config_ref()` call in `__post_init__()` | model rejection tests passed. |
| max response byte type/range validation | `_ensure_safe_runtime_max_response_bytes()` | provider tests passed. |
| value-safe runtime `repr` | unchanged `DirectHttpRuntimeConfig.__repr__()` | config/preflight redaction test passed. |

Review-only drift risks:

- none identified beyond staged-diff review of direct condition equivalence.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Complexity Evidence

Provider target before Target 6:

```text
functions_total: 244
max_cc: 19
high_complexity_functions: 11
import_edges: 3
public_defs: 50
```

Provider target after Target 6:

```text
functions_total: 247
max_cc: 14
high_complexity_functions: 10
import_edges: 3
public_defs: 50
```

For `claude_provider.py` after Target 6:

```text
functions_total: 85
max_cc: 11
high_complexity_functions: 1
import_edges: 0
public_defs: 22
```

The target max is no longer provider runtime config. It is now approved-summary
domain extraction behavior.

## Contracts Preserved

- provider output remains untrusted;
- Python validators still own packet acceptance;
- runtime endpoint and credential material stay out of serializable packets;
- `DirectHttpRuntimeConfig` fields and `repr` behavior unchanged;
- provider config/preflight serializable shapes unchanged;
- packet schemas unchanged;
- Desktop/tool schema behavior unchanged;
- privacy and fail-closed boundaries unchanged;
- reviewer-bundle/publication/customer-reply boundaries unchanged.

## Promotion And Demotion Candidates

- Promotion candidates: none new.
- Demotion candidates: none.

## Deferred Risks

- Remaining provider target max complexity is domain extraction behavior in
  `approved_summary_semantic.py`; do not split it further without explicit
  behavior examples.
- Endpoint validation remains one private high-complexity predicate at `cc=11`,
  which is acceptable because it owns a single validation family.

## Next Recommended Action

Run full provider-boundary focused tests and graph/freeze policy checks, then
perform an aggregate review for Targets 5-6 before starting another provider
batch.
