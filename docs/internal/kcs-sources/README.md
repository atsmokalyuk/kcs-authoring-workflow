# KCS Source Pack

Status: authoritative source index for KCS-15 discovery and design.

This directory keeps reviewable Markdown snapshots of the KCS authoring
sources used by this repository. The linked canonical pages remain the source
of truth. Downloaded `.doc`, `.txt`, and `.pptx` exports are evidence used to
build the snapshots; they are not committed and are not authoritative.

## Authority and precedence

Mandatory repository privacy, security, data-handling, and no-publish
contracts always apply. Within the KCS authoring domain:

1. `AUTH-MANDATORY`: mandatory repository privacy, security, data-handling,
   and no-publish contracts always apply;
2. `AUTH-OPERATOR`: operator-owned KCS practices have high authority for operator workflow and
   article-quality decisions;
3. `AUTH-PLESK-STYLE`: the Plesk KCS Style Guide and public Plesk Style Triggers are normative for
   Plesk-specific style and markup;
4. `AUTH-AQ`: KCS Article Quality Criteria are normative for article-quality
   acceptance;
5. `AUTH-WEBPROS`: the broader WebPros KCS Style Guide is a cross-brand normative cross-check;
   Plesk-specific rules win for Plesk behavior;
6. `AUTH-SIMPLIFICATION`: the Article Simplification Guide supports polishing and has lower priority
   than Article Quality Criteria;
7. `AUTH-EXAMPLES`: the best-practices slide deck supplies examples and historical context, not
   independent normative rules.

Do not silently resolve a material conflict. Record it in the parity matrix and
route it to the operator. Absence of a rule in one source does not revoke a
rule from a higher-authority source.

## Source inventory

| Source | Canonical location | Tracked snapshot | Role |
| --- | --- | --- | --- |
| Plesk KCS Style Guide | <https://webpros.atlassian.net/wiki/spaces/SOLUS/pages/3649045319/KCS+Style+Guide> | `docs/internal/kcs-sources/kcs-style-guide-plesk.md` | Plesk-specific normative |
| WebPros KCS Style Guide | <https://webpros.atlassian.net/wiki/spaces/CX/pages/3156902448/KCS+Style+Guide> | `docs/internal/kcs-sources/kcs-style-guide-webpros.md` | Cross-brand normative cross-check |
| KCS Article Quality Criteria | <https://webpros.atlassian.net/wiki/spaces/CX/pages/5422743564/KCS+Article+Quality+Criteria> | `docs/internal/kcs-sources/article-quality-criteria.md` | Normative quality criteria |
| Article Quality examples locator | <https://webpros.atlassian.net/wiki/spaces/CX/pages/3156902730/Article+Quality+criteria#Examples> | `docs/internal/kcs-sources/kb-articles-best-practices-examples.md` | Supporting examples |
| KCS Content Standard Checklist | <https://webpros.atlassian.net/wiki/spaces/CX/pages/5375295653/The+KCS+Content+Standard+Checklist> | `docs/internal/kcs-sources/kcs-content-standard-checklist.md` | Normative public-content/privacy checklist |
| Article Simplification Guide | <https://webpros.atlassian.net/wiki/spaces/CX/pages/3156902677/Article+simplification+guide> | `docs/internal/kcs-sources/article-simplification-guide.md` | Supporting polish guidance |
| Plesk KCS Style Triggers | <https://support.plesk.com/hc/en-us/articles/12378148057495-KCS-Style-triggers> | `docs/internal/kcs-sources/kcs-style-triggers.md` | Plesk-specific normative trigger reference |
| Operator KCS practices | operator-owned | `docs/internal/kcs-sources/operator-kcs-practices.md` | High-authority local rule inventory |

## Snapshot policy

- Each snapshot records its canonical URL, capture date, export filename, and
  SHA-256.
- Binary exports, images, attachments, and local download paths are not
  tracked.
- Images omitted from a snapshot must not be inferred from surrounding text.
- Refresh the affected snapshot before a behavior change when the canonical
  page has changed, its export hash differs, or the operator reports an update.
- A refresh changes evidence only. Runtime behavior still requires its own
  approved slice and acceptance gates.

The current agent environment cannot directly read the authenticated
Confluence pages. This is an access limitation, not evidence that the pages are
missing or unchanged.
