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
these MCP tools:

- `kcs_register_clean_ticket`
- `kcs_draft_ticket`
- `kcs_draft_article`
- `kcs_prepare_semantic_review`
- `kcs_submit_semantic_review`
- `support_get_behavior_instructions`

Use only these KCS Authoring tools for this workflow. If a legacy instruction
requires `support_get_behavior_instructions`, call it at most once, use its
returned route, and immediately continue `/draft` with the KCS Authoring tools.
Do not report it as missing or wait on Plesk Support Assistant Local.

If the user asks to draft an article, draft me an article, write an article,
create a KB article, or equivalent non-English requests such as `напиши статью`
or `me escreva um artigo` from an approved sanitized support ticket summary,
call `kcs_draft_ticket` immediately when a trusted source has saved the cleaned
ticket transcript under
`local-data/approved-summaries/<ticket_ref>/clean.ticket.txt`. If no ref is
available for an operator-provided sanitized attachment or paste, automatically
first call `kcs_register_clean_ticket` with the complete visible sanitized
transcript in `clean_ticket_text`, then call the returned `next_arguments`
exactly. Do not wait for the operator to ask for registration explicitly. For
short chat-provided sanitized text, use `kcs_draft_article` with
`approved_summary_text` only when no clean-ticket registration is needed.
Despite the legacy field name, `approved_summary_text` must contain the visible
text from the operator-provided sanitized ticket/context, not Claude's
condensed summary. Do not summarize, rewrite, redact labeled sections, or omit
visible symptoms, cause, resolution, config paths, commands, services, platform
facts, or other sanitized evidence before the first tool call. Do not ask what
kind of article the user wants; the default is a reviewer-only KCS knowledge
base article. Do not ask what language to use; default to English unless the
operator explicitly requests another language. Do not ask the operator to
choose between reuse search and manual drafting before the first tool call;
call the tool and show its controlled status. Do not invent reuse/search proof.
If no explicit reuse/search proof is available, the tool marks reuse search as
skipped for the MVP and continues with reviewer-only drafting. Do not pass
uploaded filenames, local paths, Claude upload paths, structured `item`,
`item_candidates`, reference article bodies, or field aliases. If the operator
says the content is not sanitized or approved, stop and ask for sanitized input
instead of calling the tool. A Claude Desktop file card is not a filesystem
path: do not inspect upload directories, and do not ask the operator to
re-upload while visible file text is available. If no visible file text is
available, report `file_content_unavailable` and do not write a manual draft.
Do not write a manual draft if this tool fails.

If the tool returns `approved_summary_resolution_steps_incomplete`, treat the
blocker as valid when the ticket gives the resolution outcome or a high-level
resolution description but does not include the exact executable procedure
needed to apply and verify it. Do not invent missing implementation details.
The operator may provide operator-confirmed resolution detail and rerun the
same pipeline; that added detail is approved evidence, not a manual/freehand
draft.

After a batch, report retryable blockers declaratively. Do not ask the operator
to choose a retryable candidate or confirm leaving already blocked candidates
blocked. Preserve them in the returned ledger; resume one only when the
operator later supplies exact confirmed resolution or workaround steps.

When a resolution uses a Plesk panel screen, use a concrete navigation path from
the Plesk home page, for example `Plesk > Domains > example.com > Hosting
Settings`. The renderer/style gate expects such GUI paths to be bold in Zendesk
HTML.

The Desktop-visible primary input is intentionally thin:

- Optional registration call: `clean_ticket_text`, optionally `ticket_ref` and
  `debug`.
- Draft first call: `ticket_ref` or `approved_summary_text`, optionally `debug`
  for explicit smoke compatibility.
- Selected-item continuation: `operator_selection_ref` and
  `operator_selected_item_ref`, optionally `debug`.

Do not provide `article_type`. Python owns semantic proposal acceptance,
validation, projection, and article-type derivation and may use only canonical
values `technical_scr` or `howto_qa`.

Production semantic extraction is provider-owned inside Python. If the approved
provider is not configured and the tool returns
`semantic_extraction_no_candidates`, report that controlled status and
do not draft manually or ask Claude to infer `item`/`item_candidates`.

Default successful authoring results return compact safe status and local
reviewer bundle references. Tool-generated reviewer-only Zendesk HTML is written
to the returned `html_path`; use that bundle HTML as the article draft and do
not create a separate freehand draft. Inline `reviewer_only_html` may appear
only in explicit debug or smoke compatibility mode; if present, show it in one
fenced `html` block without converting or rewriting it.

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

If `kcs_draft_article` returns
`workflow_state=semantic_review_required`, call
`kcs_prepare_semantic_review` with the returned `semantic_review_ref`. That
tool returns a bounded Claude-visible semantic-review packet with
`selected_excerpts` only. Use it only to propose source-grounded observations,
atomic issue boundaries, and explicit coverage records for
`semantic_issue_proposal_v1`; do not draft article prose, choose a KCS action,
produce HTML, or pass `item` / `item_candidates` payloads through
`kcs_draft_article`. Then call `kcs_submit_semantic_review` with the same
`semantic_review_ref` and the strict `semantic_issue_proposal_v1` object.

If multiple candidates pass Python validation, present the native candidate
selection and wait for the operator. Submit only its exact `submit_arguments`.
Unassigned evidence remains in the outcome ledger and must never create a
separate operator checkpoint.

During semantic review, use only bounded excerpts and return only the exact
fields requested by the current packet. Python validates the submission; the
operator selects scope; Python owns the final KCS action. Do not choose for the
operator, draft manually, or publish.

Do not try to construct KCS-9b or KCS-9c packet schemas manually from chat.

If the tools are not visible in the active session, tell the user that the KCS
Authoring plugin is installed but its MCP tools are not loaded into this chat,
then ask them to enable or reload the KCS Authoring plugin/tool access for the
current session.

## Boundaries

Only operator-provided sanitized or approved ticket text may be sent to the KCS
tools. Do not use the tool on unsanitized Zendesk exports, credentials, local
private paths, or unapproved evidence.

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
- `kcs_prepare_semantic_review` only as the bounded follow-up when
  `kcs_draft_article` returns `workflow_state=semantic_review_required`.
- `kcs_submit_semantic_review` only to submit strict semantic item
  identification grounded in the returned selected excerpt refs.

Do not call low-level KCS-9b/KCS-9c packet validators, policy summary, smoke,
pipeline, or authoring sub-tools from Claude Desktop. They are internal
development tools and are intentionally hidden from the operator-facing tool
list.

Keep user-facing output brief and concrete. Report only compact safe metadata,
not raw packet bodies.
