# KCS Authoring Tool Surface

The plugin exposes one local stdio MCP server named `kcs-authoring`.

Claude Desktop operator-visible tools:

- `kcs_draft_article`

For approved sanitized support-ticket prompts like "draft an article",
"draft me an article", "write an article", "create a KB article", or
equivalent non-English requests such as `напиши статью` or
`me escreva um artigo`, route to `kcs_draft_article` immediately. Do not ask
the operator to choose a generic article type first; the default is a
reviewer-only KCS knowledge base article.
Do not ask what language to use; default article language is English unless the
operator explicitly requests another language.
Do not ask the operator to choose between reuse search and manual drafting
before the first tool call; call the tool and show its controlled status.
Do not invent reuse/search proof; if proof is absent, the tool marks reuse
search as skipped for the MVP and continues with reviewer-only drafting.
Pass the complete visible sanitized ticket/context in `approved_summary_text`;
despite the legacy field name, do not summarize, condense, rewrite, or omit
visible symptoms, cause, resolution, config paths, commands, services, platform
facts, or other sanitized evidence before the first tool call. Do not pass
article type, upload filenames, local paths, Claude upload paths, structured
`item`, `item_candidates`, reference article bodies, or field aliases. Python
owns semantic extraction and may use only canonical KCS values: `technical_scr`
or `howto_qa`.

Production semantic extraction is provider-owned inside Python. If the approved
provider is not configured, `kcs_draft_article` returns
`semantic_extraction_provider_unavailable`; report that controlled status and
do not draft manually or construct `item` / `item_candidates` in Claude.

If the ticket contains more than one semantic KCS item, the tool returns
`split_required`, `operator_selection_ref`, candidate cards, and an
`operator_choice_request`; do not merge multiple article scopes into one draft.
Use a native single-choice popup when the client provides one. After the
operator chooses one item, call the tool again using exactly the chosen
option's `submit_arguments`. If a native popup is unavailable, present the same
choices and still use the returned `submit_arguments` exactly. Do not infer,
rewrite, or enrich the selection payload.

Low-level KCS-9b/KCS-9c packet validators, policy/readiness/smoke tools,
pipeline status tools, and authoring sub-tools are internal development tools.
They are intentionally hidden from the Claude Desktop operator-facing tool
list because the supported ticket-summary workflow must go through
`kcs_draft_article`.

Default successful authoring results include compact safe status and local
reviewer bundle references, not full HTML. For article-draft requests, show the
returned `html_path`, `manifest_path`, `debug_code`, readiness flags, and
reuse-search status. Full `reviewer_only_html` may appear only in explicit
debug or smoke compatibility mode; if present, show it in one fenced `html`
block without converting or rewriting it.

The draft tool writes local reviewer bundles under
`local-data/reviewer-bundles/`. It does not perform network calls, Zendesk
writes, Help Center publication, or customer replies.
