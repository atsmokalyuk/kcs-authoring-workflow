# KCS-14 Slice 8 Review Node: Packaging And Install Tooling

## Status

Review-only complete.

## Scope

Graph node:

- `packaging_and_install_tooling`

Reviewed files:

- `scripts/build_kcs_mcpb.py`
- `scripts/install_kcs_mcpb.py`
- `scripts/build_kcs_cowork_plugin.py`
- `packaging/claude-desktop/kcs-authoring-mvp-validator-control/README.md`
- `packaging/claude-desktop/kcs-authoring-mvp-validator-control/manifest.json`
- `packaging/claude-desktop/kcs-authoring-mvp-validator-control/server/index.js`
- `packaging/cowork/kcs-authoring/.claude-plugin/plugin.json`
- `packaging/cowork/kcs-authoring/.mcp.json`
- `packaging/cowork/kcs-authoring/README.md`
- `packaging/cowork/kcs-authoring/skills/kcs-authoring-control/SKILL.md`
- `packaging/cowork/kcs-authoring/skills/kcs-authoring-control/references/tool-surface.md`
- `tests/kcs_adapters/test_mcpb_package.py`
- `tests/kcs_adapters/test_cowork_plugin_package.py`
- `tests/policy/test_tool_entrypoints.py`

No packaging or runtime code was changed.

## Ownership Assessment

The node owns local package/build/install surfaces:

- Claude Desktop MCPB source package;
- Cowork plugin package source;
- build scripts;
- install-time package validation;
- package skill/tool guidance shipped with local adapters.

The current split is acceptable:

- `build_kcs_mcpb.py` owns MCPB archive construction and package-member allow
  rules.
- `install_kcs_mcpb.py` owns local Claude Desktop extension install behavior
  and registry update side effects.
- `build_kcs_cowork_plugin.py` owns Cowork plugin archive construction and
  manifest/config validation.
- package manifests, README files, skill text, and tool-surface references own
  platform-specific operator guidance for packaged local runtimes.
- tests anchor the shipped tool names, no-secret/no-user-config constraints,
  package shape, wrapper launch behavior, and plugin guidance boundaries.

## Must Not Own

This node must not own:

- runtime KCS decisions;
- Desktop workflow state;
- provider output validation;
- article rendering policy.

The reviewed files mostly respect those boundaries. The packaged skill text
does contain detailed workflow instructions, but as shipped product guidance
rather than source runtime behavior.

## Ousterhout Lens

- Information hiding: build and install scripts hide package validation details
  behind explicit command entrypoints.
- Deep modules: the Node wrapper hides runtime discovery and local environment
  setup behind the MCPB package entrypoint.
- Change amplification: package text can drift from repo-approved tool
  entrypoints and runtime contracts even when `src/` is untouched.
- Source-of-truth drift risk: packaged skill guidance duplicates some runtime
  workflow rules from tracked docs and tool contracts. This is an existing
  product packaging requirement, but it should remain review-visible.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- no packaging, script, or source files changed in this review
- related tests cover MCPB manifest tool surface, no user config/secrets,
  Node wrapper runtime discovery, package file allow-lists, install package
  validation, Cowork plugin manifest/config, and skill boundary text

Reviewed drift risks:

- packaging does not add credential or secret requirements.
- packaged tool surface matches the supported Desktop control surface.
- install tooling validates package shape before local side effects.
- plugin skill text keeps no-publish/no-customer-reply boundaries visible.

Review-only drift risks:

- package skill and tool-surface text are intentionally detailed and can drift
  from tracked repo docs. Future packaging edits should compare those files
  against `tool-entrypoints.md`, Desktop tool snapshots, and runtime contract
  docs.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Refactor Decision

Do not refactor this node now.

Future work should be scoped as one of these explicit questions:

- Should package skill text be generated or checked against a smaller tracked
  source to reduce source-of-truth drift?
- Should install-time local side effects get a separate dry-run/check command?
- Should Cowork plugin package guidance be reduced after the packaged workflow
  stabilizes?

These are packaging/process questions, not runtime refactor questions.

## Promotion And Demotion Candidates

- Promotion candidates: none.
- Demotion candidates: none.

Review finding to watch:

- packaged skill/tool-surface guidance may become a future alignment check if
  repeated packaging edits require manual comparison against tracked contracts.

## Next Recommended Nodes

Aggregate this pair before opening deferred-risk nodes.
