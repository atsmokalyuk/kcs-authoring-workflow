# KCS Authoring MCPB

This directory is the source for the Claude Desktop MCPB package.

The extension starts the repository-local `kcs-desktop-mcp` stdio server
through `uv`. In Claude Desktop it exposes one primary read-only operator tool
for reviewer-only KCS article drafting from approved sanitized summaries or
local approved ticket references.

Build:

```bash
python scripts/build_kcs_mcpb.py
```

Output:

```text
dist/kcs-authoring-mvp-validator-control.mcpb
```

Install the generated MCPB in Claude Desktop, configure the local repository
root, enable the extension, then start a new Claude Desktop chat.

For normal operator prompts such as "draft an article", "draft me an article",
"write a KB article", or "draft article for ticket `<ticket_ref>`", Claude
Desktop should use:

```text
kcs_draft_article
```

It accepts either a local approved `ticket_ref` or chat-provided
`approved_summary_text` with one structured supported `item`. If the summary
contains multiple semantic KCS items, pass `item_candidates`; the tool returns
`split_required` instead of merging scopes. Treat `split_required` as terminal
for the current turn: show the candidate items and ask the operator to choose
one item or provide separate approved summaries. Do not automatically call the
tool again for each candidate. Local ticket
references read only repository-local approved sanitized summary JSON from:

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

The tool returns a compact reviewer-only KCS draft/status packet:

```text
should_be_kcs_article
atomic_item
article_type
recommended_action
reviewer_only_draft
reviewer_only_html
quality_gaps
```

For article-draft prompts, Claude should display `reviewer_only_html` as the
primary copy/paste Zendesk source in one fenced `html` block, then show compact
status metadata. The draft HTML is reviewer-only and is never publication
approved by the extension.

For chat smoke tests, pass
`approved_summary_text` plus explicit supported cause/resolution evidence.
This extension does not perform live reuse search. If `reuse_search_checked`
is absent or false, the result includes `reuse_search_status=skipped` and a
`reuse_search_skipped` quality warning.
Pass `debug: true` during manual smoke to receive value-safe `failure_stage`
and `debug_code` fields when validation fails.
The tool does not write files, call a provider, publish, or read raw tickets.
Internal diagnostic tools are available only when the stdio server is started
in internal/canonical mode; they are not part of the default Claude Desktop
operator surface.

The package does not embed raw tickets, fixtures, local paths, credentials,
provider configuration, or generated artifacts.
