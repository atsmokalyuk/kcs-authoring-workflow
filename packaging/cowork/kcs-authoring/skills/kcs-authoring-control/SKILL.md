---
name: kcs-authoring-control
description: >
  Use this skill when the user asks to draft a KCS article from an approved
  sanitized summary with the local KCS Authoring MCP tool from Claude/Cowork.
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
call `kcs_draft_article` immediately with only `approved_summary_text`.
Despite the legacy field name, `approved_summary_text` must contain the
complete visible sanitized ticket/context, not Claude's condensed summary.
Do not summarize, rewrite, or omit visible symptoms, cause, resolution, config
paths, commands, services, platform facts, or other sanitized evidence before
the first tool call. Do not ask what kind of article the user wants; the
default is a reviewer-only KCS knowledge base article. Do not ask what
language to use; default to English unless the
operator explicitly requests another language. Do not ask the operator to
choose between reuse search and manual drafting before the first tool call;
call the tool and show its controlled status. Do not invent reuse/search
proof. If no explicit reuse/search proof is available, the tool marks reuse
search as skipped for the MVP and continues with reviewer-only drafting. Do
not pass uploaded filenames, local paths, Claude upload paths, structured
`item`, `item_candidates`, reference article bodies, or field aliases. Do not
write a manual draft if this tool fails.

The Desktop-visible primary input is intentionally thin:

- First call: `approved_summary_text`, optionally `debug` for explicit smoke
  compatibility.
- Selected-item continuation: `operator_selection_ref` and
  `operator_selected_item_ref`, optionally `debug`.

Do not provide `article_type`. Python owns semantic extraction and may use only
canonical values `technical_scr` or `howto_qa`.

Production semantic extraction is provider-owned inside Python. If the approved
provider is not configured and the tool returns
`semantic_extraction_provider_unavailable`, report that controlled status and
do not draft manually or ask Claude to infer `item`/`item_candidates`.

Default successful authoring results return compact safe status and local
reviewer bundle references. Show the returned `html_path`, `manifest_path`,
`debug_code`, readiness flags, and reuse-search status. Do not expect full
HTML in default output. If an explicit debug or smoke result includes
`reviewer_only_html`, show it in one fenced `html` block without converting it
to Markdown or rewriting it.

If the approved summary contains more than one semantic KCS item, the tool
returns `split_required`, `operator_selection_ref`, candidate cards, and an
`operator_choice_request`. Use a native single-choice popup when the client
provides one. After the operator chooses one item, call `kcs_draft_article`
again using exactly the chosen option's `submit_arguments`. If a native popup
is unavailable, present the same choices and still use the returned
`submit_arguments` exactly. Do not infer, rewrite, or enrich the selected-item
payload. Do not automatically retry the tool for each candidate and do not
write a manual draft.

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
