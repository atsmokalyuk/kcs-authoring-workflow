---
name: kcs-authoring-control
description: >
  Use this skill when the user asks to draft a KCS article from an approved
  sanitized summary or local approved ticket reference with the local KCS
  Authoring MCP tool from Claude/Cowork.
metadata:
  version: "0.1.0"
  author: "KCS Authoring MVP"
---

# KCS Authoring Control

Use the local KCS Authoring MCP tool for reviewer-only KCS article drafting.

## Required First Step

Before explaining that tools are unavailable, check the active tool list for
this MCP tool:

- `kcs_draft_article`

If the user asks to draft an article, draft me an article, write an article,
create a KB article, or equivalent non-English requests such as `напиши статью`
or `me escreva um artigo` from an approved sanitized support ticket summary,
call `kcs_draft_article` with `debug: true`. Do not ask what kind of article
the user wants; the default is a reviewer-only KCS knowledge
base article. Do not ask what language to use; default to English unless the
operator explicitly requests another language. Do not ask the operator to
choose between reuse search and manual drafting before the first tool call;
call the tool and show its controlled status. Do not invent reuse/search
proof. If no explicit reuse/search proof is available, the tool marks reuse
search as skipped for the MVP and continues with reviewer-only drafting. Use
`ticket_ref` when the user provides a local approved ticket reference. Use
`approved_summary_text` plus structured supported evidence when the user pasted
or attached an approved sanitized summary. Do not write a manual draft if this
tool fails.

If you provide `article_type`, use only canonical values:

- `technical_scr`
- `howto_qa`

When `kcs_draft_article` succeeds and returns `reviewer_only_html`, show that
field as the primary article output in one fenced `html` block. Do not convert
it into Markdown, do not rewrite the HTML manually, and do not omit the HTML
when the operator asked to draft an article. Show compact status metadata after
the HTML.

If the user provides an approved sanitized support summary in chat or as an
attachment, call `kcs_draft_article` with `debug: true`. Extract a single
structured `item` from the approved summary with:

- `title`
- `article_type`
- `symptoms`
- `confirmed_facts`
- `supported_cause`
- `supported_resolution_or_workaround`
- `resolution_steps`
- `applicable_to`
- `environment`

If the approved summary contains more than one semantic KCS item, pass
`item_candidates` instead of combining them into one article. The tool should
return `split_required`. When it does, stop the current drafting attempt:
show the candidate items and ask the operator to choose one item or provide
separate approved summaries. Do not automatically retry `kcs_draft_article`
for each candidate and do not write a manual draft.

If the tool returns `pipeline_ok: false`, report the returned `failure_stage`
and `debug_code` instead of guessing KCS-9b or KCS-9c packet schemas.

Do not try to construct KCS-9b or KCS-9c packet schemas manually from chat.

If the tools are not visible in the active session, tell the user that the KCS
Authoring plugin is installed but its MCP tools are not loaded into this chat,
then ask them to enable or reload the KCS Authoring plugin/tool access for the
current session.

## Boundaries

Do not send raw Zendesk payloads, raw comments, internal notes, attachments,
customer replies, credentials, local private paths, or full evidence basis to
the KCS tools.

Do not claim publication readiness from these tools. The MVP keeps:

- `auto_publish_allowed=false`
- `public_output_approved=false`
- no Zendesk writes
- no Help Center publication
- no customer replies

## Tool Usage

Use:

- `kcs_draft_article` as the primary operator-facing wrapper for normal
  "draft article" prompts.

Do not call low-level KCS-9b/KCS-9c packet validators, policy summary, smoke,
pipeline, or authoring sub-tools from Claude Desktop. They are internal
development tools and are intentionally hidden from the operator-facing tool
list.

Keep user-facing output brief and concrete. Report only compact safe metadata,
not raw packet bodies.
