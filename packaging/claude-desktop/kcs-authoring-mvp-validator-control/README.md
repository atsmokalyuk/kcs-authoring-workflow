# KCS Authoring MCPB

This directory is the source for the Claude Desktop MCPB package.

The extension starts the repository-local `kcs-desktop-mcp` stdio server
through `uv`. In Claude Desktop it exposes one primary non-destructive operator
tool for reviewer-only KCS article drafting from approved sanitized summaries.
Successful primary drafts may write reviewer-only bundle files under
`local-data/reviewer-bundles/`.

Build:

```bash
python scripts/build_kcs_mcpb.py
```

Build and replace the locally installed Claude Desktop extension:

```bash
python scripts/install_kcs_mcpb.py
```

Run the deterministic installed-wrapper smoke without opening Claude Desktop:

```bash
uv run python scripts/smoke_kcs_mcpb_stdio.py
```

Output:

```text
dist/kcs-authoring-mvp-validator-control.mcpb
```

Install the generated MCPB in Claude Desktop, configure the local repository
root, enable the extension, then start a new Claude Desktop chat.

For normal operator prompts such as "draft an article", "draft me an article",
or "write a KB article" with a pasted or attached approved sanitized summary,
Claude Desktop should use:

```text
kcs_draft_article
```

It accepts chat-provided `approved_summary_text` as the primary first-call
input. Despite the legacy field name, Claude Desktop must read attached
sanitized text and pass the complete visible sanitized content as
`approved_summary_text`; it must not summarize, condense, rewrite, or omit
symptoms, cause, resolution, config paths, commands, services, platform facts,
or other visible sanitized evidence. It must not pass uploaded filenames, local
paths, Claude upload paths, structured `item`, `item_candidates`, reference
article bodies, or field aliases.

Python owns semantic extraction, workflow state, validation, KCS decisions,
rendering, and output safety. If the tool returns `split_required`, treat that
result as terminal for the current turn: show the Python-returned candidate
items in a native Claude Desktop choice popup when the client provides one and
wait for the operator to choose one item. Do not automatically call the tool
again for each candidate. If a native popup is not available, the tool result
text includes the same
candidate choices and exact `submit_arguments`; present those choices to the
operator and use the selected option's returned
`operator_choice_request.options[*].submit_arguments` as the deterministic
fallback for the next tool call. Do not infer or rewrite the selection payload.

Semantic extraction is provider-owned inside Python. Production Desktop
sessions require an approved semantic provider configuration; when that
provider is absent, the tool returns the controlled
`semantic_extraction_provider_unavailable` status instead of drafting manually.
Deterministic smoke tests may explicitly enable the fixture-only provider for
synthetic labeled, narrative, raw-ticket-shaped, and split-selection cases.
That fixture is not production semantic extraction.

After the operator chooses one candidate, the next `kcs_draft_article` call
must pass only `operator_selection_ref` and `operator_selected_item_ref`.

Default successful authoring results return compact safe status plus local
reviewer bundle references. Full `reviewer_only_html` is returned only when
`debug=true` is used for explicit debug/smoke compatibility; otherwise the HTML
is written to the local bundle path returned as `html_path`.

If semantic extraction provider support is unavailable, show the controlled
`semantic_extraction_provider_unavailable` status instead of drafting manually.

The active refactor target is tracked in:

```text
docs/internal/kcs-desktop-authoring-refactor-plan.md
```

Repository-local ticket references are an internal/backward-compatible path,
not the Claude Desktop attachment workflow. They read only repository-local
approved sanitized summary JSON from:

```text
local-data/approved-summaries/<ticket_ref>.json
```

It does not read Zendesk. The ticket reference must already point to approved
cleanup-form output or another approved sanitized summary source.

The default article kind for an approved sanitized support-ticket summary is a
reviewer-only KCS knowledge base article. Claude should not ask the operator to
choose between blog post, incident report, customer-facing article, or other
generic writing formats before calling the tool.

If an `article_type` is provided, use only canonical KCS values:
`technical_scr` or `howto_qa`.

Do not invent reuse/search proof. If explicit reuse/search proof is not
available, this MVP marks reuse search as skipped and continues with
reviewer-only drafting.

The tool returns compact reviewer-only draft/status metadata:

```text
article_type
bundle_ref
manifest_path
html_path
recommended_action
reuse_search_status
```

For article-draft prompts, Claude should show compact status metadata and any
safe refs/paths returned by the tool. Full HTML is written to the local
reviewer bundle and is not part of the default Desktop-visible structured
response unless `debug: true` is used for smoke/debug compatibility. Draft
output is reviewer-only and is never publication approved by the extension.

For chat smoke tests, pass
`approved_summary_text` plus explicit supported cause/resolution evidence.
This extension does not perform live reuse search. If `reuse_search_checked`
is absent or false, the result includes `reuse_search_status=skipped` and a
`reuse_search_skipped` quality warning.
Pass `debug: true` during manual smoke to receive value-safe `failure_stage`
and `debug_code` fields when validation fails.
The tool may write reviewer-only bundle files under
`local-data/reviewer-bundles/`. It does not publish, write Zendesk, or read raw
tickets.
Internal diagnostic tools are available only when the stdio server is started
in internal/canonical mode; they are not part of the default Claude Desktop
operator surface.

The package does not embed raw tickets, fixtures, local paths, credentials,
provider configuration, or generated artifacts.
