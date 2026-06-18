# KCS-9c Claude-Assisted Reviewer Draft Generation Plan

Status: future implementation planning / current KCS-9c branch plan.

KCS-9c is the first planned slice where Claude or another approved bounded
provider may propose reviewer-only draft wording. The provider output remains
untrusted. Python owns validation, artifact writing, readiness reporting, and
publication safety.

This plan is aligned with `docs/internal/kcs-core-pipeline-review-notes.md`.
It intentionally carries forward the deferred KCS-5/KCS-9b risks around local
artifact writing, provider boundaries, action authority, and style validation.

## Portable Reference Notes

The local `plesk_support` project is reference material only. KCS-9c may reuse
these portable ideas, not copy project-specific code or data:

- runtime-independent typed packet contracts;
- schema-versioned JSON payloads;
- value-free validation failures;
- strict safe review-bundle boundaries;
- explicit draft eligibility before drafting;
- no automatic customer reply generation;
- principle: code decides, LLM drafts, validators block;
- reviewer-assist style feedback is advisory, not authority.

Do not import local paths, `.private/**`, `.knowledge/**`, generated drafts,
review bundles, ticket data, RAG chunks, credentials, or `plesk_support`
package names.

## Relationship To KCS-9b

KCS-9b exists first as a strict handoff contract:

- compact safe request context;
- optional artifact refs/hashes;
- no full reviewer packet body;
- no full Zendesk HTML body;
- no raw ticket, raw comments, attachments, credentials, or private values;
- no provider-owned KCS action decision;
- no draft generation;
- no file writing;
- `auto_publish_allowed=false`;
- `public_output_approved=false`.

KCS-9c consumes only validated KCS-9b-style bounded context. It must not create
a shortcut that passes raw evidence, full reviewer packets, full Zendesk HTML,
or full evidence basis to Claude.

KCS-9b artifact refs are safe logical refs by default, not raw local filesystem
paths. KCS-9c may use those refs for local operator workflows, but
provider-visible packets must not include absolute paths or file bodies.

Local artifact writing is Python-owned. Claude must never write files directly.
If a local bundle/reviewer artifact writer is not available before KCS-9c, it
must be implemented before or as the first adjacent sub-step of KCS-9c.

## Relationship To KCS-9a And KCS-9a-Prep

KCS-9a identifies semantic KCS item candidates only. It does not draft article
text and does not decide final KCS actions.

KCS-9a-prep remains a deferred chronology-preserving sanitized conversation
context builder. KCS-9c must not implement transcript cleanup, live raw Zendesk
cleanup, or broad semantic sanitization as a side effect of draft generation.

If KCS-9c needs semantic context, it must come from an approved safe packet or
artifact ref produced by earlier validated stages.

## Goal

Allow an approved provider to propose draft wording for reviewer use while
preserving existing KCS core authority:

```text
KCS-3 decision
  -> KCS-4 renderer/reviewer packet
  -> KCS-5 readiness
  -> KCS-9b bounded handoff request
  -> KCS-9c provider proposes draft wording
  -> Python validates draft response
  -> Python writes reviewer-only draft artifact
  -> optional style judge feedback
  -> human reviewer
```

The draft is never auto-published and never treated as publication-ready by
provider output alone.

## Draft Eligibility

KCS-9c draft requests are allowed only for deterministic article-output paths
that already have validated bounded handoff context and draft eligibility:

- `create_candidate`;
- `update_existing`;
- `flag_existing`.

Internal-only reviewer draft generation is allowed only when deterministic
metadata explicitly marks reviewer-only draft eligibility and the resulting
draft remains `public_output_approved=false`.

KCS-9c must reject draft requests for:

- `reuse_existing`;
- `no_article`;
- `blocked`;
- `split_required`;
- readiness states that require fixing evidence, fixing the reviewer packet,
  rendering missing output, or reviewing split items.

If the operator needs reviewer-assist notes for `reuse_existing`,
`no_article`, `blocked`, or split cases, that remains KCS-9b-style assistance,
not KCS-9c article draft generation.

## Planned Contracts

KCS-9c should define contracts separate from KCS-9b:

- `KcsClaudeDraftRequestPacket`;
- `KcsClaudeDraftResponsePacket`;
- `KcsReviewerOnlyDraftArtifact`.

The request packet should include:

- `schema_version`;
- `handoff_ref`;
- `case_ref`;
- `item_ref`;
- original deterministic metadata:
  - `original_recommended_action`;
  - `original_article_type`;
  - `original_decision_status`;
  - `original_readiness_state`;
- immutable safety flags:
  - `auto_publish_allowed=false`;
  - `public_output_approved=false`;
  - `provider_may_decide_action=false`;
- compact safe drafting context:
  - title hint;
  - article type;
  - bounded symptoms/question summary;
  - bounded cause/answer/resolution summary when public-safe;
  - blocker/warning/reason codes;
  - reviewer-only reason codes;
  - operator override metadata;
- optional artifact refs:
  - reviewer packet hash/ref;
  - Zendesk HTML hash/ref;
  - no file bodies.

`KcsClaudeDraftRequestPacket` must use strict JSON, allowed keys only at root
and nested levels, bounded fields, safe refs/hashes only, and value-safe
errors. It must reject raw/private values, full reviewer packet bodies, full
Zendesk HTML bodies, full `evidence_basis`, raw/internal comments, attachment
URLs/bodies, credentials, absolute paths, and provider-owned action fields.

The response packet should use structured fields, not one free-form article
blob:

- `schema_version`;
- `handoff_ref`;
- `draft_status`;
- `article_type`;
- `title`;
- `applicable_to`;
- `sections`;
- `zendesk_source_html`, if generated;
- `reviewer_notes`;
- `unsupported_claims_present`;
- `internal_only_content_present`;
- `auto_publish_allowed=false`;
- `public_output_approved=false`.

Provider responses may echo `original_*` fields for correlation only when they
exactly match the request. Provider responses must not contain provider-owned
KCS action fields such as `recommended_action`, `proposed_action`,
`kcs_action`, `action_decision`, `decision`, `should_create`,
`should_update`, or `should_flag`. Any non-`original_*` field whose value is a
KCS action enum such as `reuse_existing`, `update_existing`,
`create_candidate`, `flag_existing`, `split_required`, `no_article`, or
`blocked` is invalid.

KCS-9c Zendesk HTML, if generated, is reviewer-only provider draft output. It
does not replace KCS-4 deterministic renderer output, does not become
publication-ready, and may only be written by Python into a reviewer-only draft
artifact after validation.

Provider exceptions and invalid provider responses must become value-safe
failed draft responses or `ContractValidationError`s without raw exception
chains. Provider exception text must never appear in errors, artifacts, logs, or
reviewer output. Malformed provider output must not write a draft artifact.

## Required Python Validation

Python validators must treat the draft response as untrusted and enforce:

- strict JSON shape;
- allowed keys only;
- bounded field lengths;
- article type matches the original deterministic article type;
- required sections by article type;
- public/internal separation;
- no raw ticket data;
- no raw internal comments;
- no attachment bodies or URLs;
- no credentials, tokens, private paths, live domains, IPs, hostnames, license
  IDs, emails, or raw ticket IDs;
- no unsupported claims in public draft content;
- no provider-owned KCS action decision fields or action-like output values;
- no customer-reply-like fields or sections such as `customer_reply`,
  `reply_to_customer`, `agent_reply`, `email_reply`, or `ticket_response`;
- `auto_publish_allowed=false`;
- `public_output_approved=false`;
- reviewer-only status preserved.

If `unsupported_claims_present=true`, the response is not accepted as a usable
draft body. Python may produce a reviewer-only validation artifact with blocker
code `unsupported_claims_present`, but it must not write usable Zendesk draft
HTML. Unsupported factual claims are blockers, not style warnings, and the
style judge cannot override them.

Technical/SCR drafts must include:

- title;
- Applicable to;
- Symptoms;
- Cause, if supported;
- Resolution;
- optional Additional information.

How-to drafts must include:

- title;
- Applicable to, when scope matters;
- Question;
- Answer.

Provider-owned draft HTML must be validated as an allowlisted reviewer-only
subset. Allowed tags are:

- `h1`, `h2`, `h3`;
- `p`;
- `ol`, `ul`, `li`;
- `strong`, `em`;
- `code`, `pre`;
- `br`;
- `a`.

Allowed attributes:

- `href` on `a` only;
- only approved safe refs or explicitly approved public documentation URLs when
  the implementation chooses to allow links.

Default link policy is no external URLs. Public documentation URLs are allowed
only after an explicit allowlist validator exists.

Draft HTML must be bounded and parseable.

Provider-owned draft HTML must reject:

- `<script>` and `<style>`;
- SVG;
- `<iframe>`, `<form>`, `<input>`, `<img>`;
- event-handler attributes such as `onerror`;
- inline `style`;
- `class` and `id` unless a later validator explicitly approves a safe subset;
- data URLs;
- unapproved external URLs;
- unknown tags or unknown attributes;
- malformed HTML;
- public `<h2>Environment</h2>`;
- customer-reply-like sections;
- internal-only facts outside reviewer-only notes or internal-only wrappers;
- unsafe raw values.

## KCS Style Compliance Model

KCS Style Guide compliance must be layered:

```text
prompt constraints
  + structured draft schema
  + deterministic Python validators
  + optional style judge feedback
  + human review
```

The provider prompt can instruct Claude to follow the KCS Content Standard and
Style Guide, but the prompt is not an enforcement layer.

Python validators enforce hard structural and safety rules:

- technical articles use Symptoms/Cause/Resolution;
- how-to articles use Question/Answer;
- title is specific;
- Applicable to is present when scope matters;
- no public Environment section;
- GUI-first steps when a GUI path is explicitly available;
- CLI/advanced steps are separated after GUI path when applicable;
- Resolution/Answer steps are atomic ordered steps;
- Resolution/Answer steps must be executable from the article when the ticket
  history contains the operational details: each step should say not only what
  to do, but how to do it with the relevant UI path, command, file path,
  linked prerequisite article, or verification action. A draft is incomplete if
  a reviewer or customer must perform an additional search to discover the
  command, path, or product navigation needed to apply the resolution.
- commands, paths, log files, and errors use approved formatting conventions.

The style judge loop is optional reviewer-assist feedback, not authority:

- it may report style issues;
- it cannot approve publication;
- it cannot override validator blockers;
- it cannot change deterministic KCS action or readiness state;
- every accepted style finding should be applied or rejected with reason by the
  reviewer/operator workflow.

The human reviewer remains the final decision-maker.

## Artifact Writing Boundary

Reviewer-only draft artifacts are local review artifacts, not KCS-4 reviewer
packets and not KCS-5 readiness reports.

Before KCS-9c can merge, either:

1. the Python-owned reviewer-only draft artifact writer contract is implemented
   and tested in KCS-9c; or
2. KCS-9c is explicitly split into a contract-only slice with no artifact
   writing, followed by a writer slice.

A KCS-9c implementation that accepts provider draft content and writes
artifacts must not defer the writer contract.

The writer must:

- be Python-owned;
- write only after request/response validation passes;
- keep public draft body separate from reviewer-only notes;
- mark artifacts with `reviewer_only=true`;
- mark `auto_publish_allowed=false`;
- mark `public_output_approved=false`;
- preserve deterministic original action/readiness metadata;
- store provider output as untrusted reviewer-only content;
- avoid raw local paths in provider-visible packets;
- reject overwrite/path traversal/symlink hazards if writing to disk;
- use safe permissions for written files.

The writer must not:

- write raw Zendesk snapshots;
- write raw comments or internal notes;
- write redaction maps;
- write provider prompts/responses containing private values;
- publish to Zendesk or Help Center;
- replace KCS-4 renderer output.

## Out Of Scope For KCS-9c

- raw Zendesk payloads to Claude;
- raw internal comments to Claude;
- attachment processing or upload;
- live Zendesk writes;
- Help Center draft, update, or publish actions;
- customer reply generation;
- Claude-owned KCS action decisions;
- Claude-owned readiness or publication approval;
- production rollout;
- MCP server or internal service implementation unless a later slice explicitly
  approves the adapter work;
- KCS-9a-prep sanitizer implementation;
- deterministic online supportability/EOL lookup.

## Required Tests Before Merge

KCS-9c must include tests for:

- draft request can be built only from validated KCS-9b bounded context;
- `create_candidate`, `update_existing`, and `flag_existing` eligible states
  can create draft requests;
- `reuse_existing`, `no_article`, `blocked`, `split_required`, and non-ready
  readiness states reject draft requests;
- internal-only draft requests require explicit reviewer-only eligibility and
  keep `public_output_approved=false`;
- draft request excludes raw ticket data, full reviewer packet body, full
  Zendesk HTML, and full evidence basis by default;
- draft request with unknown nested keys, absolute artifact paths, non-string
  keys, `NaN`, `Infinity`, raw values, or byte-size overflow is rejected;
- provider failure is value-safe and does not preserve raw exception cause;
- provider exception text containing private values is not echoed;
- provider returns non-object or malformed output and no draft artifact is
  written;
- provider response with unexpected fields is rejected;
- provider response with action decision fields is rejected;
- provider response with customer-reply fields or sections is rejected;
- provider response with exact `original_recommended_action` echo is accepted;
- provider response with mismatched `original_recommended_action` is rejected;
- provider response with mismatched article type is rejected;
- provider response with `auto_publish_allowed=true` is rejected;
- provider response with `public_output_approved=true` is rejected;
- provider response with `unsupported_claims_present=true` is rejected as a
  usable draft or converted to blocked reviewer-only validation output;
- technical draft without Symptoms/Cause/Resolution is rejected;
- how-to draft without Question/Answer is rejected;
- public Environment section is rejected;
- reviewer notes are separate from public draft body;
- unsafe HTML, unknown HTML tags/attributes, iframe/form/img/data URLs,
  malformed HTML, and unapproved external URLs are rejected;
- raw/private values are rejected without echo;
- Python writes the reviewer-only draft artifact;
- draft artifact has `reviewer_only=true`;
- draft artifact has `auto_publish_allowed=false`;
- draft artifact has `public_output_approved=false`;
- draft artifact preserves original deterministic action/readiness metadata;
- artifact write rejects overwrite, path traversal, and symlink targets;
- draft artifact is not accepted as a KCS-4 reviewer packet or KCS-5 readiness
  output;
- provider cannot write files;
- optional style judge feedback cannot approve publication or override Python
  validator blockers.

## Deferred Follow-Ups

- optional style judge packet/result/disposition workflow;
- live Claude provider adapter and smoke tests;
- internal service/API or MCP adapter implementation;
- richer content-standard checks after pilot evidence shows which style issues
  recur;
- shared safe-code, safe-ref, safe-metadata, and raw-boundary helpers across
  KCS-3 through KCS-9.
