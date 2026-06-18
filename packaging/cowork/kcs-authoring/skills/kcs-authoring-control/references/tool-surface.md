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
If an `article_type` is provided, use only canonical KCS values:
`technical_scr` or `howto_qa`.

For chat-provided summaries, pass one structured `item`. If the ticket contains
more than one semantic KCS item, pass `item_candidates` and let the tool return
`split_required`; do not merge multiple article scopes into one draft. Treat
`split_required` as terminal for the current turn: show candidate items and ask
the operator to choose one item or provide separate approved summaries. Do not
automatically call the tool again for each candidate.

Low-level KCS-9b/KCS-9c packet validators, policy/readiness/smoke tools,
pipeline status tools, and authoring sub-tools are internal development tools.
They are intentionally hidden from the Claude Desktop operator-facing tool
list because the supported ticket-summary workflow must go through
`kcs_draft_article`.

Successful authoring results include `reviewer_only_html`. For article-draft
requests, show that field as the primary copy/paste Zendesk source in one
fenced `html` block, then show compact status. Do not convert the reviewer HTML
into Markdown or manually rewrite article sections.

The tool is read-only. It does not perform network calls, provider calls, file
writes, Zendesk writes, Help Center publication, or customer replies. When a
local `ticket_ref` is used, the server reads only repository-local approved
sanitized summary JSON and does not read Zendesk.
