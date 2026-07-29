# Operator-Owned KCS Practices

Status: high-authority operator-owned inventory for KCS-15. The operator has
confirmed the authority class; imported candidate rules remain provisional
until individually approved or independently confirmed by a canonical source.

## Confirmed operator decisions

| ID | Decision | Status |
| --- | --- | --- |
| `OP-SOURCE-001` | Canonical Confluence/public URLs are the source of truth. Repository Markdown files are reviewable snapshots; downloaded local files are not authoritative. | confirmed |
| `OP-SOURCE-002` | The Plesk-specific Style Guide is normative for Plesk behavior. The broader WebPros Style Guide is a cross-check; Plesk-specific rules take precedence. | confirmed |
| `OP-SOURCE-003` | Article Quality Criteria outrank the Article Simplification Guide; the latter is supporting polish guidance. | confirmed |
| `OP-RAG-001` | The local public RAG implementation in `plesk_support` is mature enough to reuse through a proper adapter. Its integration timing is separate from style parity and does not block it. | confirmed |
| `OP-AUTH-001` | Operator practices are a separate high-authority KCS rule set. Material conflicts are surfaced to the operator rather than silently resolved. | confirmed |
| `OP-GATE-001` | KCS-14.5 is closed. Its retained semantic/control-surface contracts remain frozen and require a separate behavior-change design to reopen. Independently approved work outside those surfaces may proceed when it leaves them unchanged. | confirmed |

## Portable practice candidates

The following candidates are present in the mature `plesk_support` rule set
and overlap with one or more canonical sources. They are inventory, not an
authorization to change behavior.

| ID | Candidate practice | Evidence status |
| --- | --- | --- |
| `OP-KCS-001` | Search/reuse is performed before create/update; search may use symptoms, but technical article identity is article type plus supported cause-resolution pair. | provisional |
| `OP-KCS-002` | One article covers one atomic customer-reported issue or question; incidental investigation findings are evidence, not separate articles by default. | provisional |
| `OP-KCS-003` | Public Symptoms contain sanitized, customer-verifiable observations needed to recognize the case, without unrelated investigation narrative. | confirmed by canonical sources |
| `OP-KCS-004` | Cause is concise, supported, and free of resolution actions; an unknown cause is not invented merely to fill the section. | provisional; source conflict exists for cause optionality |
| `OP-KCS-005` | Resolution is linear, complete, safe, and starts with the real entrypoint; required reusable procedures are linked in the exact step. | confirmed by canonical sources |
| `OP-KCS-006` | GUI is primary when available. Equivalent CLI can follow separately; optional/advanced/fallback material can be collapsed, but required steps stay visible. | confirmed by canonical sources |
| `OP-KCS-007` | Risky changes receive backup, rollback, access-impact, or downtime preparation before the action. Complex custom mitigations require an explicit public/internal reviewer decision. | confirmed in part; custom-mitigation boundary provisional |
| `OP-KCS-008` | A maintained source-control script may replace many non-interactive commands when it reduces effort; scripts are not article attachments. | confirmed by current Article Quality Criteria |
| `OP-KCS-009` | Public wording is concise, neutral, product-safe, and search-friendly; unsupported certainty and customer-specific framing are removed. | confirmed in part; subjective cases need human/model evaluation |
| `OP-KCS-010` | Golden examples are operator-approved compact metadata/short-pattern references, not copied full article bodies. | provisional |

## Unknowns retained for later decisions

- Whether a Plesk technical SCR article may omit Cause when the cause is
  unknown but the workaround is supported.
- Whether all technical Symptoms must be an ordered list, or whether this is a
  current renderer convention rather than a canonical requirement.
- Which conditional branches are acceptable when collapsing or splitting them
  would reduce clarity or safety.
- The approved initial set of public golden articles and the exact rule each is
  allowed to demonstrate.
- The controlled tag taxonomy and which tag checks can be deterministic.

Only the smallest relevant subset of these unknowns should be presented to the
operator for the next behavior slice.
