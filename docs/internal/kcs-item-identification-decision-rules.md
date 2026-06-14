# KCS Item Identification - Decision Rules

## Purpose

Define how KCS-9a semantic item identification should classify candidate KCS
items before the deterministic KCS decision engine runs.

This document is about item identification only. It does not change KCS action
decision ownership.

```text
Claude or another bounded extractor may suggest what the ticket is about.
Python validates the structured output.
decision.py decides the KCS action.
```

## Ownership Boundary

KCS-9a may propose structured candidate fields from approved sanitized or clean
context. It must not decide whether to reuse, update, create, flag, block, or
publish.

Claude/extractor may suggest:

- item boundaries;
- product relation;
- supportability hints;
- candidate item status;
- article type hint;
- public/internal visibility hint;
- missing evidence hints.

Python owns:

- schema validation;
- privacy/safety validation;
- supportability and product-relevance normalization;
- conversion into accepted evidence;
- KCS action decision;
- renderer/readiness validation.

## Input Context Requirements

KCS-9a semantic identification should receive a sanitized but meaningful
conversation context. The cleanup/preparation layer should preserve chronology
instead of collapsing the ticket into disconnected facts.

The sanitizer/context builder should remove only explicit noise and unsafe
values. Relevant context from the customer/support exchange must stay in the
sanitized data so the extractor can understand the issue, what was checked,
what changed over time, and whether the customer confirmed a result.

Recommended safe input shape:

```text
case_ref
source_refs[]
sanitized_turns[]:
  turn_index
  role = customer | support | internal_note | system
  visibility
  text
known_safe_facts[]
explicit_status_mentions[]
operator_notes[]
```

The context must preserve:

- turn order;
- role-level speaker information;
- customer symptom or question;
- relevant troubleshooting context exchanged with the customer;
- support checks and findings;
- support answer, workaround, or resolution;
- customer confirmation or unresolved status;
- explicit EOL/unsupported mentions when present in sanitized input.

The context must not contain:

- message transport metadata, duplicated quoted mail noise, email footers, or
  signatures unless they contain KCS-relevant facts;
- raw Zendesk JSON or raw ticket comments;
- customer names, emails, live domains, IPs, hostnames, license IDs, raw ticket
  IDs, private paths, credentials, tokens, or secrets;
- attachment bodies or attachment URLs;
- raw internal comments as-is.

This context is not canonical evidence. It is untrusted semantic input that
must be validated and normalized before the KCS decision engine sees anything.

## Core Fields

Each candidate item should carry these classification fields.

```text
product_relation:
  plesk_owned
  plesk_shipped_or_bundled_component
  plesk_extension_catalog
  plesk_managed_process_or_service
  non_plesk_owned_but_support_provided_solution
  generic_third_party
  customer_environment_specific
  eol_or_unsupported_only
  unclear

supportability:
  supported
  unsupported
  eol_only
  unclear

supportability_basis:
  explicit_input_mention
  not_checked

kcs_item_status:
  candidate_allowed
  internal_only_candidate
  no_article
  blocked_need_more_evidence
```

Do not use a binary `plesk_related: true/false` field. The enum keeps important
support nuances visible.

## Product Relation Rules

Treat an item as Plesk/WebPros-related when the affected area is:

- Plesk product behavior, GUI, CLI, API, service, package, extension, backup,
  mail, web, DNS, panel, updater, or installer;
- a component shipped, bundled, built, patched, configured, or managed by
  Plesk;
- a Plesk extension catalog item, even when the next support action is vendor
  or developer contact;
- a managed service or process in Plesk support scope;
- integration behavior where a Plesk configuration or control path is relevant;
- a non-Plesk-owned layer where Support provided a concrete reusable
  diagnostic, workaround, or solution.

Do not classify a component as `generic_third_party` only because its upstream
origin is third party. If Plesk ships, bundles, manages, patches, or exposes it
through the extension catalog, use the more specific Plesk-related relation.

## No-Article Identification Rules

Use `kcs_item_status = no_article` when the item is not reusable product
knowledge, for example:

- the question is not product or brand related;
- Support only gave a generic third-party recommendation or vendor link;
- the issue is website source-code specific;
- the issue is provider, network, operating-system, or application-layer only
  and not configurable or controlled by Plesk;
- the item is too vague and has no reusable symptom, error, evidence, answer,
  or resolution;
- the issue cannot be reproduced and no specific reusable error exists;
- the customer fixed it themselves and Support did not provide reusable steps;
- the item is unresolved and has no answer, workaround, ETA, or supported
  resolution;
- the item is EOL-only and not part of a supported migration, upgrade,
  conversion, restore, transfer, or transition path.

## Non-Plesk But Support Added Reusable Value

Do not immediately reject non-Plesk-owned layers when Support provided reusable
value.

```text
product_relation = non_plesk_owned_but_support_provided_solution
default kcs_item_status = internal_only_candidate
```

Public candidate status is allowed only when product-context rules clearly
support it and the evidence is public-safe.

Examples of reusable value:

- scoped diagnostic steps;
- Plesk-side exclusion checks;
- safe workaround in a Plesk-controlled path;
- reviewer note that prevents repeated investigation.

## EOL Mention Rule

KCS-9a does not perform live online EOL lookup in this MVP rule set.

If approved sanitized input explicitly says that the affected product, operating
system, extension, package, or software component is EOL, unsupported, or
end-of-life, mark:

```text
supportability = eol_only or unsupported
supportability_basis = explicit_input_mention
```

Then apply the role of the EOL subject:

```text
eol_role:
  affected_runtime
  source_for_migration_or_upgrade
  historical_context
  unclear
```

Default rule:

```text
explicit EOL mention
  + eol_role = affected_runtime
  + no supported migration/upgrade/transition path
  -> kcs_item_status = no_article
```

Exception:

```text
explicit EOL mention
  + eol_role = source_for_migration_or_upgrade
  + supported target/current path exists
  -> kcs_item_status = candidate_allowed
```

If the EOL role is unclear:

```text
kcs_item_status = blocked_need_more_evidence
```

Do not infer EOL from version numbers by model memory. If the input mentions a
version but does not say it is EOL, mark supportability as `unclear` and require
a future supportability check.

## Search vs Identity

Search uses symptoms and visible context:

```text
symptoms
visible errors
product area
component
version
resolution keywords
```

KCS issue identity uses:

```text
technical_scr:
  article type + cause-resolution pair

howto_qa:
  question-answer pair
```

Symptoms may differ across tickets while the underlying cause-resolution pair is
the same. Same symptoms do not prove the same article.

## Minimal Identification Decision Rule

Use this order during item identification:

```text
if unsafe/private:
  blocked_need_more_evidence

elif multiple customer-reported issues/questions:
  keep separate atomic candidates

elif not product/brand related and only generic third-party guidance:
  no_article

elif Plesk-shipped/bundled/extension/managed:
  candidate_allowed

elif non-Plesk-owned but Support provided reusable diagnostic/solution:
  internal_only_candidate

elif unresolved or no supported answer/resolution/workaround/ETA:
  blocked_need_more_evidence or no_article

elif explicit EOL mention and affected runtime has no supported transition path:
  no_article

elif explicit EOL mention and item is about supported migration/upgrade path:
  candidate_allowed

else:
  candidate_allowed or blocked_need_more_evidence
```

## Forbidden Output

KCS-9a candidate identification must not return KCS actions:

```text
reuse_existing
update_existing
create_candidate
flag_existing
split_required
blocked
```

It must also not return:

- raw Zendesk JSON;
- raw ticket comments;
- raw internal comments;
- attachment bodies or attachment URLs;
- credentials, tokens, keys, or secrets;
- customer names, email addresses, live domains, IPs, hostnames, license IDs, or
  private paths;
- generated article body or Zendesk HTML.

## Test Expectations

KCS-9a tests should cover:

- Plesk-owned item becomes `candidate_allowed`;
- Plesk-shipped third-party component is not `generic_third_party`;
- generic third-party with only vendor/general advice becomes `no_article`;
- customer-environment-specific item becomes `no_article`;
- non-Plesk-owned item with reusable support value becomes
  `internal_only_candidate`;
- unresolved item becomes `blocked_need_more_evidence`;
- explicit EOL affected runtime becomes `no_article`;
- explicit EOL source for migration/upgrade becomes `candidate_allowed`;
- version-only EOL inference is not accepted;
- unsafe/private values fail without echoing raw values;
- candidate output does not contain final KCS actions.
