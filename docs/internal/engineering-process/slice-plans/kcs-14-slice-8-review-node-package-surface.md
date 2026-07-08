# KCS-14 Slice 8 Review Node: Package Surface

## Status

Review-only complete.

## Scope

Graph node:

- `package_surface`

Reviewed files:

- `src/kcs_adapters/__init__.py`
- `src/kcs_core/__init__.py`

Related tests listed by the graph:

- `tests/kcs_adapters/test_desktop_mcp_adapter.py`
- `tests/kcs_adapters/test_cowork_plugin_package.py`
- `tests/kcs_core/test_cli.py`

No runtime code was changed.

## Ownership Assessment

The node owns package-level import compatibility:

- package import markers;
- core public import expectations;
- adapter public import expectations;
- side-effect-light package initialization.

The current surface is intentionally small. It acts as an import contract for
tests, package consumers, and compatibility paths, not as a place for runtime
workflow logic.

## Must Not Own

This node must not own:

- runtime behavior;
- KCS decisions;
- Desktop workflow behavior;
- provider behavior;
- renderer or style policy.

The reviewed files respect those boundaries.

## Ousterhout Lens

- Interface simplicity: the package surface is a small compatibility interface
  over deeper implementation modules.
- Information hiding: callers should not need to know internal file placement
  for stable public imports.
- Shallow abstraction risk: moving imports or adding wrapper exports without an
  import-contract goal would increase compatibility work without reducing
  caller knowledge.
- Change amplification: package import changes can trigger broad test and
  packaging churn even when runtime behavior is unchanged.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- no source files changed in this review
- related tests cover package import expectations and package/plugin
  compatibility surfaces

Reviewed drift risks:

- package imports remain side-effect-light;
- public imports remain compatibility surface, not runtime behavior owners;
- lazy adapter exports must not hide provider, Desktop, or publication changes.

Review-only drift risks:

- import-surface changes can appear harmless but break downstream package users;
  any future package-surface edit needs an explicit import-contract question.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Refactor Decision

Do not refactor this node now.

Future work should require a narrow ownership question, such as:

- Which public imports are intentional compatibility contracts?
- Can any compatibility reexports be retired with explicit migration evidence?
- Should package import tests snapshot the public surface more directly?

No current blocker justifies code movement.

## Promotion And Demotion Candidates

- Promotion candidates: none.
- Demotion candidates: none.

## Next Recommended Node

Review `renderer_style_gates`.
