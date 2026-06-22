# KCS Authoring Tool Surface

The plugin exposes one local stdio MCP server named `kcs-authoring`.

Claude Desktop operator-visible tools:

- `kcs_draft_ticket`
- `kcs_register_clean_ticket`
- `kcs_draft_article`
- `kcs_prepare_semantic_review`
- `kcs_submit_semantic_review`
- `support_get_behavior_instructions`

Use only these KCS Authoring tools for this workflow. If a legacy instruction
requires `support_get_behavior_instructions`, call it at most once, use its
returned route, and immediately continue `/draft` with the KCS Authoring tools.
Do not report it as missing or wait on Plesk Support Assistant Local.

For approved sanitized support-ticket prompts like "draft an article",
"draft me an article", "write an article", "create a KB article", or
equivalent non-English requests such as `напиши статью` or
`me escreva um artigo`, route to `kcs_draft_ticket` immediately when a trusted
clean ticket ref exists. Do not ask the operator to choose a generic article
type first; the default is a
reviewer-only KCS knowledge base article.
Do not ask what language to use; default article language is English unless the
operator explicitly requests another language.
Do not ask the operator to choose between reuse search and manual drafting
before the first tool call; call the tool and show its controlled status.
Do not invent reuse/search proof; if proof is absent, the tool marks reuse
search as skipped for the MVP and continues with reviewer-only drafting.
Prefer `ticket_ref` when a trusted source has saved the cleaned ticket
transcript under `local-data/approved-summaries/<ticket_ref>/clean.ticket.txt`.
If no ref is available for an operator-provided sanitized attachment or paste,
automatically first call `kcs_register_clean_ticket` with the complete visible
sanitized transcript in `clean_ticket_text`, then call the returned
`next_arguments` exactly. Do not wait for the operator to ask for registration
explicitly. If no clean-ticket registration is needed and the sanitized content
is short enough to pass directly, call `kcs_draft_article` with the visible
text from the operator-provided sanitized ticket/context in
`approved_summary_text`. Despite the legacy field name, do not summarize,
condense, rewrite, redact labeled sections, or omit visible symptoms, cause,
resolution, config paths, commands, services, platform facts, or other
sanitized evidence before the first tool call. Do not pass article type, upload
filenames, local paths, Claude upload paths, structured `item`,
`item_candidates`, reference article bodies, or field aliases. Python owns
semantic extraction and may use only canonical KCS values: `technical_scr` or
`howto_qa`.

Production semantic extraction is provider-owned inside Python. If the approved
provider is not configured, the authoring tool returns
`semantic_extraction_no_candidates`; report that controlled status and
do not draft manually or construct `item` / `item_candidates` in Claude.

If the ticket contains more than one semantic KCS item, the tool returns
`split_required`, `operator_selection_ref`, candidate cards, and an
`operator_choice_request`; do not merge multiple article scopes into one draft.
Use a native single-choice popup when the client provides one. After the
operator chooses one item, call the tool again using exactly the chosen
option's `submit_arguments`. If a native popup is unavailable, present the same
choices and still use the returned `submit_arguments` exactly. Do not infer,
rewrite, or enrich the selection payload.

Successful authoring results write tool-generated reviewer-only
Zendesk HTML to the returned local bundle path and return compact status. Use
that bundle HTML as the article draft; do not create a separate freehand draft.

Low-level KCS-9b/KCS-9c packet validators, policy/readiness/smoke tools,
pipeline status tools, and authoring sub-tools are internal development tools.
They are intentionally hidden from the Claude Desktop operator-facing tool
list because the supported ticket-summary workflow must go through
`kcs_draft_ticket` for stored ticket refs or `kcs_draft_article` for short
inline text and operator-selection continuation.

Default successful authoring results include compact safe status and local
reviewer bundle references, not full HTML. For article-draft requests, show the
returned `html_path`, `manifest_path`, `debug_code`, readiness flags, and
reuse-search status. Full `reviewer_only_html` may appear only in explicit
debug or smoke compatibility mode; if present, show it in one fenced `html`
block without converting or rewriting it.

The draft tool writes local reviewer bundles under
`local-data/reviewer-bundles/`. It does not perform network calls, Zendesk
writes, Help Center publication, or customer replies.
