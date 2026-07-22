# Module Boundaries

Status: authoritative KCS-14 Slice 5 orientation layer.

This document explains the human-readable ownership boundaries behind
`code-review-graph.json`. It is a review and orientation aid, not a runtime
contract and not a replacement for reading source code.

Use this file before KCS-14 refactor work to decide which ownership area is in
scope, which adjacent contracts must be preserved, and which tests should be
checked before moving code.

## Boundary Principles

- Split by ownership of knowledge, not by execution order.
- Prefer deep modules with small stable interfaces.
- A split is useful only when it reduces what callers must know.
- Do not create helper/class layers that only pass values through.
- Keep rules in the module that owns the concept; workflows may call those
  modules at different times without duplicating their knowledge.

## Ownership Areas

### Desktop MCP Tool Surface

Owns Desktop-visible tool registration, input schemas, and compact result
shaping.

Must not know how KCS decisions are made, how semantic candidates are validated,
or how reviewer bundles are written.

Review when touching:

- `src/kcs_adapters/mcp_desktop.py`
- `src/kcs_adapters/desktop_tool_schemas.py`
- `src/kcs_adapters/desktop_tool_results.py`
- `src/kcs_adapters/desktop_mcp_adapter.py`
- `src/kcs_adapters/desktop_authoring_tools.py`
- `src/kcs_adapters/desktop_control_tools.py`
- `src/kcs_adapters/desktop_tool_descriptors.py`
- `src/kcs_adapters/desktop_tool_names.py`

Risk: schema drift changes Desktop behavior even when core runtime code is
unchanged.

### Desktop Protocol And Transport

Owns JSON-RPC framing, stdio transport, protocol payload conversion, and MCP
result envelope helpers.

Must not own KCS workflow decisions, tool schema business rules,
semantic-review validation, or provider calls.

Review when touching:

- `src/kcs_adapters/desktop_jsonrpc.py`
- `src/kcs_adapters/desktop_protocol.py`
- `src/kcs_adapters/desktop_stdio_transport.py`
- `src/kcs_adapters/desktop_payload.py`
- `src/kcs_adapters/desktop_mcp_results.py`

Risk: protocol envelope changes can look like cleanup while changing Desktop
behavior.

### Clean Ticket Storage

Owns `ticket_ref` lookup, approved clean-ticket metadata, and safe local store
access.

Must not own semantic decisions, article rendering, reviewer bundle writing, or
provider credential material.

Review when touching:

- `src/kcs_adapters/desktop_ticket_ref.py`
- `src/kcs_adapters/desktop_clean_ticket_metadata.py`

Risk: ref validation drift can expose local files or make fixtures
machine-dependent.

### Provider And Handoff Boundary

Owns Claude provider adapter boundaries, approved-summary semantic extraction
adapter behavior, and draft/handoff helper surfaces.

Must not own trusted KCS decisions, packet acceptance, publication behavior, or
Desktop transport.

Review when touching:

- `src/kcs_adapters/claude_provider.py`
- `src/kcs_adapters/approved_summary_semantic.py`
- `src/kcs_core/claude_draft.py`
- `src/kcs_core/claude_handoff.py`

Risk: provider convenience helpers can accidentally become decision owners or
leak runtime-only material into serializable packets.

### Controlled Semantic Review Fallback

Owns semantic-review state, bounded selected-excerpt packets, submit
validation, and allowed `source_refs`.

Must not own drafted article bodies, final KCS action decisions, reviewer
bundle writing, or provider trust.

Review when touching:

- `src/kcs_adapters/desktop_semantic_review.py`
- `src/kcs_adapters/desktop_semantic_candidates.py`
- `src/kcs_adapters/desktop_semantic_providers.py`
- `src/kcs_core/semantic_extraction.py`

Risk: splitting prepare/submit/continue code by time order can leak the same
schema and blocker rules across multiple files.

### Desktop Draft Workflow

Owns orchestration from Desktop request to validated workflow result, including
operator selection state and semantic provider handoff.

Must not own clean-ticket storage rules, semantic-review schema internals, core
decision rules, renderer policy, or publication.

Review when touching:

- `src/kcs_adapters/desktop_draft_tool.py`
- `src/kcs_adapters/desktop_workflow.py`
- `src/kcs_adapters/desktop_operator_selection.py`
- `src/kcs_adapters/desktop_authoring_pipeline.py`
- `src/kcs_adapters/desktop_draft_arguments.py`
- `src/kcs_adapters/desktop_draft_output.py`
- `src/kcs_adapters/desktop_workflow_results.py`
- `src/kcs_adapters/desktop_workflow_status.py`

Risk: orchestration can accidentally absorb rules that should stay in deeper
owner modules.

### Packet Validation And KCS Decisions

Owns KCS packet models, validation, safety checks, deterministic action
recommendation, and blocker codes.

Must not own Desktop transport, provider calls, renderer presentation details,
or local bundle paths.

Review when touching:

- `src/kcs_core/models.py`
- `src/kcs_core/validation.py`
- `src/kcs_core/safety.py`
- `src/kcs_core/decision.py`
- `src/kcs_core/evidence_builder.py`
- `src/kcs_core/sanitizer.py`

Risk: validation or decision drift can silently change behavior while a change
is described as refactor-only.

### CLI, Ingest, And Readiness

Owns CLI entrypoint behavior, JSON payload loading, Zendesk ingest helpers,
readiness checks, and safe error surfaces.

Must not own Desktop-specific state, provider trust decisions, renderer
presentation policy, or reviewer bundle writing.

Review when touching:

- `src/kcs_core/cli.py`
- `src/kcs_core/json_payload.py`
- `src/kcs_core/zendesk_ingest.py`
- `src/kcs_core/readiness.py`
- `src/kcs_core/errors.py`

Risk: CLI and ingest helpers can bypass the same validators used by Desktop if
they grow their own acceptance logic.

### Renderer And Current Style Gates

Owns reviewer packet rendering, Zendesk HTML rendering, and current
markup-quality checks.

Must not own KCS-15 style/markup parity expansion, action decisions,
semantic-review validation, or Desktop transport.

Review when touching:

- `src/kcs_core/renderer.py`
- `src/kcs_adapters/zendesk_markup_quality.py`
- `src/kcs_adapters/kcs_markup_patterns.py`
- `src/kcs_adapters/kcs_article_style_refs.py`

Risk: formatting cleanup can accidentally become deferred KCS-15 behavior work.

### Reviewer Bundle Output

Owns local reviewer bundle writing, bundle manifest shape, relative artifact
references, and hashes.

Must not own KCS decisions, Desktop tool schemas, Zendesk publication, customer
reply generation, or provider trust.

Review when touching:

- `src/kcs_adapters/desktop_reviewer_bundle.py`
- `src/kcs_core/reviewer_bundle.py`
- `src/kcs_adapters/desktop_reviewer_preview.py`

Risk: path or manifest drift can expose private local details or make bundle
writing look like publication behavior.

### Smoke And Log Tooling

Owns value-safe smoke accounting, Desktop log checks, and MCPB stdio smoke
entrypoints.

Must not own runtime KCS decisions, provider output validation, reviewer bundle
content, or raw transcript storage.

Review when touching:

- `src/kcs_adapters/smoke_accounting.py`
- `src/kcs_adapters/desktop_contract_smoke.py`
- `scripts/check_claude_kcs_desktop_log.py`
- `scripts/smoke_kcs_mcpb_stdio.py`
- `scripts/smoke_claude_desktop_ui_prompt.py`

Risk: local Desktop state can be mistaken for deterministic validation if the
manual/local-runtime boundary is unclear.

### Packaging And Install Tooling

Owns Claude Desktop MCPB package source, Cowork plugin package source, package
build scripts, and install-time package validation.

Must not own runtime KCS decisions, Desktop workflow state, provider output
validation, or article rendering policy.

Review when touching:

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

Risk: package sources can alter shipped tool behavior without touching Python
runtime source files.

### Package Import Surface

Owns package import markers and package-level public import expectations.

Must not own runtime behavior, KCS decisions, Desktop behavior, or provider
behavior.

Review when touching:

- `src/kcs_adapters/__init__.py`
- `src/kcs_core/__init__.py`

Risk: package-level exports can create implicit coupling between otherwise
separate ownership areas.

### Synthetic Rebaseline Observability

Owns value-safe synthetic rebaseline record validation and metadata-only export
to the separately managed loopback Langfuse service.

Must not own runtime KCS decisions, model invocation, Desktop control flow,
provider response content, raw ticket or excerpt storage, reviewer bundles, or
publication behavior. Langfuse availability must not become a product runtime
dependency.

Review when touching:

- `scripts/rebaseline_semantic_issue_projection.py`
- `scripts/kcs14_langfuse_rebaseline.py`
- `evals/kcs14_langfuse_control_surface_profile.example.json`
- `tests/kcs_adapters/test_semantic_projection_rebaseline.py`
- `tests/kcs_adapters/test_kcs14_langfuse_rebaseline.py`

Risk: observability metadata can become a side channel for private input or be
mistaken for causal evidence when the control-surface profile is not comparable.

### Engineering Policy Tests

Owns KCS-14 deterministic policy checks, documentation/process guardrail
tests, and code-review graph coverage checks.

Must not own runtime KCS behavior, Desktop behavior, packet schemas, or
provider behavior.

Review when touching:

- `tests/policy/test_code_review_graph_policy.py`
- `tests/policy/test_functional_test_policy.py`
- `tests/policy/test_kcs14_docs_policy.py`
- `tests/policy/test_review_context_policy.py`
- `tests/policy/test_tool_entrypoints.py`

Risk: process checks can become brittle wording tests or be mistaken for
runtime validation.

## How To Use This During Refactor

Before refactor:

1. Identify affected graph nodes from `code-review-graph.json`.
2. Read this boundary note for those nodes.
3. Read the touched files and direct dependencies.
4. Identify related tests and unchanged contracts.
5. Confirm the behavior/test frame exists before moving code.

After refactor:

1. Map changed files back to graph nodes.
2. Confirm the node's `must_not_own` list did not become false.
3. Confirm stable output and failure contracts did not change.
4. Run related tests and policy checks.
5. Update graph hashes only if the code-map change is intentionally part of
   the same reviewed slice.
