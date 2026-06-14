# KCS-9b Bounded Claude Handoff Plan

Status: future implementation planning / implement before KCS-9c draft
generation.

KCS-9b defines the safe provider handoff boundary. It does not generate article
drafts, write files, call a live Claude API, implement MCP/service transport, or
change deterministic KCS decisions.

## Goal

Create strict request/response packet contracts for bounded reviewer-assist
handoff:

```text
KCS-3 decision summary
  + KCS-5 readiness summary
  + compact safe context
  + optional safe artifact refs
  -> KCS-9b handoff request
  -> fake or approved provider response
  -> Python validation
  -> reviewer-assist notes only
```

KCS-9b may be implemented before a local bundle writer because it uses compact
safe summaries and optional artifact refs. It must not compensate for missing
artifacts by embedding full reviewer packets, full Zendesk HTML, raw evidence
basis, or internal notes.

## Planned Contracts

KCS-9b should define:

- `KcsClaudeHandoffRequestPacket`;
- `KcsClaudeHandoffResponsePacket`;
- `ClaudeHandoffProvider` protocol for fake-provider tests.

The request packet should include:

- `schema_version = "kcs_claude_handoff_request_v1"`;
- `handoff_ref`;
- `case_ref`;
- `item_ref`;
- `handoff_purpose = "reviewer_assist_notes"`;
- `provider_profile`;
- immutable original metadata:
  - `original_recommended_action`;
  - `original_article_type`;
  - `original_decision_status`;
  - `original_readiness_state`;
  - optional decision/readiness summary hash;
- fixed safety flags:
  - `auto_publish_allowed=false`;
  - `public_output_approved=false`;
  - `provider_may_decide_action=false`;
  - `provider_may_generate_draft_body=false`;
  - `include_full_reviewer_packet_body=false`;
  - `include_full_zendesk_html=false`;
- bounded `safe_context`;
- copied operator override metadata;
- safe `artifact_refs`.

The response packet should include:

- `schema_version = "kcs_claude_handoff_response_v1"`;
- `handoff_ref`;
- `provider_status`;
- `provider_error_code`;
- bounded `reviewer_assist_notes`;
- structured safe comment codes;
- optional exact echo of `original_*` fields for correlation;
- fixed safety flags:
  - `auto_publish_allowed=false`;
  - `public_output_approved=false`;
  - `contains_article_draft=false`.

The response must not contain draft article body, Zendesk HTML, customer reply
text, KCS action decisions, or publication approval.

## Allowed Keys And Provider Profile

KCS-9b request and response validation must use allowed keys only at every
nested object level:

- request root;
- `safe_context`;
- operator override metadata;
- `artifact_refs`;
- response root;
- structured response comments.

Unknown keys fail closed without echoing the raw key or value. This prevents
fields such as `raw_note`, `zendesk_source_html`, `evidence_basis`,
`absolute_path`, or `draft_body` from slipping through under otherwise safe
objects.

`provider_profile` is safe metadata only. It is not a transport selector,
authentication selector, endpoint, command path, model prompt, or safety-policy
override.

Allowed initial values:

- `fake_provider`;
- `approved_provider`.

`provider_profile` must reject URLs, filesystem paths, inline credentials,
tokens, command strings, and arbitrary provider-specific endpoint details.
Changing `provider_profile` must not change validation, safety rules, allowed
fields, or publication flags.

## Original Action Metadata Versus Provider Action Output

KCS-9b must distinguish deterministic original metadata from provider-owned
decision output.

Allowed fields:

- `original_recommended_action`;
- `original_article_type`;
- `original_decision_status`;
- `original_readiness_state`;
- exact provider echo of `original_*` fields, verified against the request.

Forbidden provider-owned fields:

- `recommended_action`;
- `proposed_action`;
- `kcs_action`;
- `action_decision`;
- `decision`;
- `should_create`;
- `should_update`;
- `should_flag`;
- any non-`original_*` field whose value is a KCS action enum.

Validation must allow `original_recommended_action="create_candidate"` in the
request and exact response echo. It must reject
`recommended_action="create_candidate"` or mismatched
`original_recommended_action="flag_existing"` in the response.

## Safe Context And Bounds

`safe_context` should contain compact values only:

- `title_hint`;
- `article_type`;
- `status_codes`;
- `reason_codes`;
- `blocker_codes`;
- `warning_codes`;
- `short_public_safe_summary`;
- `reviewer_only_reason_codes`.

Initial deterministic bounds:

- `title_hint <= 160` characters;
- `short_public_safe_summary <= 1200` characters;
- each reviewer-assist note `<= 600` characters;
- max reviewer-assist notes: `10`;
- max reason, blocker, warning, or status codes per list: `50`;
- max serialized request size: `32 KB`;
- max serialized response size: `16 KB`.

Oversized values must fail closed without echoing the raw value.

## Artifact References

Artifact refs are safe logical refs by default, not raw local filesystem paths.

Suggested shape:

```json
{
  "reviewer_packet_sha256": "",
  "zendesk_source_sha256": "",
  "reviewer_packet_ref": "",
  "zendesk_source_ref": ""
}
```

Rules:

- hashes are empty or 64 lowercase hex;
- refs are opaque safe strings such as `artifact-reviewer-packet-001`;
- empty refs are valid before bundle writer exists;
- file bodies are never embedded;
- absolute paths such as `/Users/...` or `/tmp/customer...` are rejected from
  provider-visible packets;
- if local paths are supported later, they are local-only operator metadata and
  must be represented as bounded safe refs before provider handoff.

## Response Status And Error Codes

Allowed `provider_status` values:

- `accepted`;
- `failed`;
- `rejected`.

Allowed `provider_error_code` values:

- `none`;
- `provider_failed`;
- `provider_timeout`;
- `provider_rejected_context`;
- `provider_response_invalid`;
- `unsafe_context_blocked`.

Rules:

- `provider_status=accepted` requires `provider_error_code=none`;
- `provider_status in failed,rejected` requires a non-`none` error code;
- failed or rejected responses must not include draft body, Zendesk HTML, raw
  provider messages, or raw exception text;
- provider exceptions are converted to safe failed responses or
  `ContractValidationError` with no raw exception chain.

## Out Of Scope For KCS-9b

- live Claude/API calls;
- MCP server or internal service implementation;
- auth, endpoint, deployment, or network ACL handling;
- article draft generation;
- Zendesk HTML generation;
- local file writing;
- bundle writer implementation;
- KCS action decision changes;
- renderer/readiness changes;
- Zendesk writes, Help Center publication, or customer replies.

## Required Tests Before Merge

KCS-9b implementation must test:

- request builds from synthetic KCS decision/readiness summaries;
- request works with empty artifact refs;
- request accepts `provider_profile=fake_provider`;
- request rejects URL, path, token, or credential-like `provider_profile`;
- request accepts `original_recommended_action=create_candidate`;
- request preserves `auto_publish_allowed=false`;
- request preserves `public_output_approved=false`;
- request rejects `auto_publish_allowed=true`;
- request rejects `public_output_approved=true`;
- request rejects full reviewer packet body;
- request rejects full Zendesk HTML;
- request rejects full evidence basis;
- request rejects raw/internal notes unless converted to safe codes;
- request rejects unknown nested keys such as `safe_context.raw_note`;
- request rejects unknown artifact keys such as `artifact_refs.absolute_path`;
- request rejects raw ticket/private-looking values;
- request rejects attachment URLs/bodies;
- request rejects credentials, tokens, private paths, domains, IPs, hostnames,
  license IDs, and raw ticket IDs;
- request rejects absolute local artifact paths;
- request accepts safe opaque artifact refs and hashes;
- request field limits and serialized size limits are enforced;
- response accepts exact `original_recommended_action` echo;
- response rejects unknown nested keys without echo;
- response rejects `recommended_action=create_candidate`;
- response rejects `proposed_action=reuse_existing`;
- response rejects `draft_body`;
- response rejects mismatched `original_recommended_action`;
- response rejects draft article body and Zendesk HTML;
- response rejects unknown provider status or error code;
- response enforces accepted/failed/rejected error-code invariants;
- provider exception with raw private message returns a value-safe failure;
- strict JSON serialization rejects non-string keys, `NaN`, and `Infinity`;
- fake provider is sufficient and no Claude/API/MCP/network access is required.

## Deferred Follow-Ups

- local bundle/reviewer artifact writer before or at the start of KCS-9c;
- KCS-9c Claude-assisted reviewer-only draft generation;
- optional style judge loop;
- live approved provider adapter and smoke tests;
- internal service/API or MCP adapter implementation.
