# KCS Authoring Workflow MCPB

This directory is the source for the Claude Desktop MCPB package.

The technical package ID remains `kcs-authoring-mvp-validator-control` for
installed-extension compatibility, but the human-facing workflow is no longer a
minimal MVP. It is the Claude Desktop adapter for the local KCS Authoring
Workflow: clean-ticket registration, `ticket_ref` drafting, Python-owned
semantic extraction and validation, compact default output, and local reviewer
bundles.

The extension starts the bundled `kcs-desktop-mcp` stdio server through an
autodetected local runtime: `uv` first, then `python3.11` / `python3` fallback.
The operator does not configure a KCS repository path, Claude CLI/Code, an API
key, or a semantic-provider schema in Desktop. KCS-15.2b2 additionally requires
the existing loopback-only `plesk_support` public RAG runtime to be running and
ready on `127.0.0.1:8768`. In Claude Desktop the extension
exposes one primary non-destructive operator tool for reviewer-only KCS article
drafting from approved sanitized summaries. Successful primary drafts may write
reviewer-only bundle files under `local-data/reviewer-bundles/`.

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

Install the generated MCPB in Claude Desktop, enable the extension, then start a
new Claude Desktop chat.

Live draft-run accounting is optional. To capture value-safe diagnostic
checkpoints from an installed extension, select a local directory in the
extension's **Draft run accounting directory** setting. Leaving the setting
unset preserves normal authoring behavior and creates no accounting files.

Before drafting, start or verify the existing public RAG runtime from its
`plesk_support` checkout:

```bash
.venv/bin/plesk-knowledge runtime up \
  --knowledge-root .knowledge \
  --host 127.0.0.1 \
  --port 8768 \
  --operator-ui-host 127.0.0.1 \
  --operator-ui-port 8767 \
  --json

.venv/bin/plesk-knowledge runtime smoke \
  --host 127.0.0.1 \
  --port 8768 \
  --warm-if-cold \
  --reload-stale \
  --json
```

The smoke must report the runtime, vector index, and keyword index ready.
`reuse_comparison_blocked` with
`comparison_provider_not_ready`, `comparison_provider_unavailable`, or
`comparison_provider_invalid_response` is a fail-closed readiness result:
restore the public runtime and restart comparison; do not draft manually.

For normal operator prompts such as "draft an article", "draft me an article",
or "write a KB article" with a pasted or attached approved sanitized summary,
Claude Desktop should use the clean-ticket registration tool first when no
`ticket_ref` exists yet:

```text
kcs_register_clean_ticket
```

Then Claude Desktop should use:

```text
kcs_draft_article
```

For production-like long tickets, prefer an opaque `ticket_ref` that points to a
cleaned ticket transcript prepared by a trusted source. The canonical file
layout inside the configured clean-ticket store is:

```text
local-data/approved-summaries/<ticket_ref>/clean.ticket.txt
local-data/approved-summaries/<ticket_ref>/clean.ticket.meta.json
```

Installed MCPB runs read those machine-readable clean ticket files from
`~/Library/Application Support/KCS Authoring` by default, including dev installs
that override `repository_root` to point at a source checkout. Source/dev runs
may use a different root only by explicitly setting
`KCS_AUTHORING_MVP_APPROVED_TICKET_STORE_ROOT`. External cleanup forms should
write the same layout under the Application Support root and show the exact
`<ticket_ref>` directory name to the operator. The metadata file binds
`clean.ticket.txt` by SHA-256 and is required before the Claude-visible
semantic-review fallback can return bounded selected excerpts.

Claude Desktop must pass only the opaque ref, for example:

```json
{"ticket_ref": "monitoring-001"}
```

If the operator provided a sanitized attachment or paste but no `ticket_ref`,
Claude Desktop should automatically first call `kcs_register_clean_ticket` with
the complete visible sanitized transcript in `clean_ticket_text`; the operator
does not need to ask for registration explicitly. The registration result
returns `next_arguments`; Claude Desktop must call `kcs_draft_article` with
those exact `next_arguments`.

If `kcs_draft_article` returns `workflow_state=semantic_review_required`,
Claude Desktop should call `kcs_prepare_semantic_review` with the returned
`semantic_review_ref`. That tool returns selected excerpts only, capped for
semantic item identification. It does not return the full ticket and must not
be used for freehand drafting. Claude Desktop should then call
`kcs_submit_semantic_review` with only the same `semantic_review_ref` and a
strict `semantic_issue_proposal_v1` object grounded in the returned excerpt
refs. Do not submit article prose, HTML, `recommended_action`, `item`,
`item_candidates`, raw ticket text, local paths, or publication flags. If
multiple candidates pass Python validation, wait for the native candidate
selection and submit only its exact `submit_arguments`. Unassigned evidence
remains in the outcome ledger and never creates a separate operator checkpoint.

If a draft entrypoint returns `result_kind=reuse_comparison_required`, no draft
or reviewer bundle has been created. Claude Desktop must compare only the
returned accepted ticket facts and bounded cited public excerpts, present one
concise coverage/gap recommendation, and ask exactly one operator question
using the returned `reuse`, `update`, `none_fit`, and `need_more_evidence`
outcomes. Only after the operator answers may it call
`kcs_confirm_reuse_comparison`. That call contains only `comparison_ref`,
`outcome`, and one displayed `candidate_ref` for `reuse` or `update`;
`none_fit` and `need_more_evidence` omit the candidate ref. Evidence, URLs,
recommendations, drafts, HTML, and free-form text are forbidden submit fields.
Multi-item selections repeat this gate sequentially for at most five
operator-selected issues.

It must not pass uploaded filenames, local paths, Claude upload paths,
structured `item`, `item_candidates`, reference article bodies, or field
aliases.

A Claude Desktop file card is not a filesystem path. Claude Desktop must not
inspect upload directories or ask the operator to re-upload while visible file
text is available. If no visible file text is available, it should report
`file_content_unavailable` and must not draft manually.

For short chat-provided sanitized text, Claude Desktop may pass
`approved_summary_text`. Despite the legacy field name, that value must contain
the visible sanitized content as-is; Claude must not summarize, condense,
rewrite, redact labeled sections, or omit symptoms, cause, resolution, config
paths, commands, services, platform facts, or other visible sanitized evidence.

Python owns semantic proposal acceptance and audit, workflow state, validation,
KCS decisions, rendering, and output safety. The model-proposed issue partition
remains untrusted; Python blocks undeclared overlap in identity-bearing evidence.
The workflow does not branch on Claude Desktop
Free vs Enterprise; client capabilities are observed from the MCP initialize
message, and the same tool contract is used for both. If the tool returns
`split_required`, treat that result as terminal for the current turn: show the
Python-returned candidate items in a native Claude Desktop choice popup when the
client provides one and wait for the operator to choose one item. Do not
automatically call the tool again for each candidate. If a native popup is not
available, the tool result text includes the same candidate choices and exact
`submit_arguments`; present those choices to the operator and use the selected
option's returned
`operator_choice_request.options[*].submit_arguments` as the deterministic
fallback for the next tool call. Do not infer or rewrite the selection payload.

Semantic extraction is provider-owned inside Python. The default Desktop path
uses local approved-summary semantic extraction and does not require Claude
CLI/Code or an API key, so it can be smoke-tested from Claude Desktop Free or
Enterprise Desktop. If no semantic candidate can be extracted from the approved
summary, the tool returns the controlled `semantic_extraction_no_candidates`
status instead of drafting manually.
Deterministic smoke tests may explicitly enable the fixture-only provider for
synthetic labeled, narrative, raw-ticket-shaped, and split-selection cases.
That fixture is not production semantic extraction.

After the operator chooses one candidate, the next `kcs_draft_article` call
must pass only `operator_selection_ref` and `operator_selected_item_ref`.

Default successful authoring results return compact safe status and local
reviewer bundle references. Reviewer-only Zendesk HTML is written to the local
bundle path returned as `html_path`. Installed MCPB runs write human-reviewable
bundles under `~/Documents/KCS Authoring` and return that location as
`bundle_storage_hint`; resolve `html_path` below that directory. Source/dev runs
without that hint keep using the project-local `local-data/reviewer-bundles`
directory.

If semantic extraction cannot identify a supported candidate from the approved
summary, show the controlled `semantic_extraction_no_candidates` status instead
of drafting manually.

Successful `kcs_draft_article` results write tool-generated reviewer-only
Zendesk HTML to the returned local bundle path. Use that bundle HTML as the
article draft; do not create a separate freehand draft. Inline
`reviewer_only_html` is returned only for explicit debug/smoke compatibility.

The active refactor target is tracked in:

```text
docs/internal/kcs-desktop-authoring-refactor-plan.md
```

Configured clean-ticket references are the source-independent production path.
Zendesk export cleanup, web GUI cleanup, and Claude attachment preparation
should all produce the same clean ticket file under:

```text
local-data/approved-summaries/<ticket_ref>/clean.ticket.txt
```

The adapter also accepts the older approved sanitized summary JSON format from:

```text
local-data/approved-summaries/<ticket_ref>.json
```

It does not read Zendesk directly. The ticket reference must already point to
approved cleanup-form output or another approved sanitized source.

The default article kind for an approved sanitized support-ticket summary is a
reviewer-only KCS knowledge base article. Claude should not ask the operator to
choose between blog post, incident report, customer-facing article, or other
generic writing formats before calling the tool.

If an `article_type` is provided, use only canonical KCS values:
`technical_scr` or `howto_qa`.

Do not invent reuse/search proof. If explicit reuse/search proof is not
available, the local workflow marks reuse search as skipped and
continues with reviewer-only drafting.

Do not invent missing resolution implementation details. If a ticket gives the
resolution outcome or a high-level resolution description but does not include
the exact executable procedure needed to apply and verify it, the pipeline may
block with `approved_summary_resolution_steps_incomplete`. That blocker is
expected. An operator can add verified resolution detail and rerun the workflow;
Claude must not infer the missing procedure.

After a batch, retryable blockers are declarative ledger outcomes. Claude must
not ask the operator to choose one or confirm leaving already blocked
candidates blocked. A candidate is resumed only after the operator later
supplies exact confirmed resolution or workaround steps.

The tool returns compact reviewer-only draft/status metadata:

```text
article_type
bundle_ref
bundle_storage_hint
bundle_storage_ref
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
Claude must not render its own Markdown article from that status.

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

The package embeds only the local Python workflow source needed by the MCP
server. It does not embed raw tickets, fixtures, private local paths,
credentials, provider configuration, or generated artifacts.
