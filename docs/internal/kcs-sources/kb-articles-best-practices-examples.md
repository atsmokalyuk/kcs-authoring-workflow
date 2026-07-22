# KB Articles Best-Practices Example Pack

Status: reviewable Markdown snapshot of supporting examples. This deck is not
an independent source of truth; current canonical KCS pages and operator-owned
practices take precedence.

- Canonical parent/examples locator:
  <https://webpros.atlassian.net/wiki/spaces/CX/pages/3156902730/Article+Quality+criteria#Examples>
- Authority ID: `AUTH-EXAMPLES`.
- Source role: visual examples and historical rationale for Article Quality
  Criteria.
- Captured: 2026-07-22 from the operator-provided slide deck.
- Export filename: `KB_articles_best_practices_guide.pptx` (not tracked).
- Export SHA-256:
  `e7ab27b5fe047089e654a04acc2d28189294012577d6a07d376054af4f4e108d`.
- Slide count: 19.
- Lifecycle in source: `beta`.
- Superseded example: slide 9 attachment advice is superseded by the
  `AUTH-AQ` source-control rule.

The deck calls itself beta and says its rules may change. Slide screenshots and
the binary deck are intentionally omitted.

## Example inventory

| Slides | Topic | Evidence supplied |
| --- | --- | --- |
| 2 | Scope | Publishing legitimacy, ease of use, layout, and KB lifecycle; practices were researched with successful KCS publishers. |
| 3-5 | Publishing legitimacy | Public articles need a resolution, workaround, or allowed ETA; obsolete public knowledge becomes internal; generic third-party knowledge should point to a precise official source. |
| 6 | Linear solution | Symptom, supported Cause, and corresponding Resolution should form a straightforward path without confusing branches. |
| 7 | Media | Screenshots or short video can help when they directly match the resolution context. |
| 8 | GUI first | GUI is the primary path when available; CLI follows as advanced/collapsed content. |
| 9 | Scripting | A maintained script can replace many commands when it reduces operator effort. The slide's instruction to attach scripts is superseded by current Article Quality Criteria, which requires engineering source control. |
| 10 | Language | Avoid misspellings, passive voice, and complex grammar that is hard for non-native readers. |
| 11 | Title | Use a specific, search-oriented Plesk title and add a visible error where useful. |
| 12 | Links | Avoid hub-like cross-link collections; every link needs direct case context and purpose. |
| 13 | Structure | Technical articles use Symptoms/Cause/Resolution; how-to articles use singular Question/Answer; security alerts use Situation/Impact/Call to Action. |
| 14-15 | Symptoms | Keep Symptoms precise, customer-visible, unique, and free from excessive troubleshooting internals or duplicates. |
| 16 | Layout | Use consistent list hierarchy and the approved horizontal separator rather than prose `OR`. |
| 17 | Tags | Tags reflect the correct OS and Plesk version; broader tags may be appropriate when multiple versions share one resolution. |
| 18 | Lifecycle | Rework high-reuse internal knowledge for publication; internalize low-reuse/high-NSAT public knowledge until improved; request colleague review. |

## Use in KCS-15

These slides can support a named human-review gate and help select compact
golden examples. They cannot by themselves define deterministic runtime rules.
Any example that contains commands, customer data, obsolete UI, or publication
advice must be revalidated against the current canonical pages and repository
safety contracts.
