# KCS-15 Style and Markup Parity Matrix

Status: KCS-15.0 evidence baseline. This document inventories requirements and
gaps; it does not approve runtime implementation.

Authoritative source index:
`docs/internal/kcs-sources/README.md`.

## Evidence vocabulary

- `confirmed`: supported by an authoritative source or directly observed in
  the current code/tests.
- `provisional`: plausible and supported by partial evidence, but still needs
  an operator or design decision.
- `unknown`: material evidence is missing.
- `rejected`: evidence shows the proposal should not be used.

Gate vocabulary:

- `deterministic`: exact contract, fixture, schema, or validator test.
- `bounded-model-trial`: fixed fixtures, model/configuration, sample count,
  invariants, threshold, corrections, overhead, false-positive review, and stop
  condition defined before execution.
- `named-human-review`: a named role reviews a fixed artifact against a fixed
  checklist.

## Current operational baseline

Observed at `4acb0b320b692a281abfe56b5e27f61d8f3d`:

- `src/kcs_core/renderer.py` renders reviewer-only SCR and Q&A Zendesk HTML,
  including `Applicable to`, ordered Resolution steps, a resolution container,
  entrypoint links, inline command/config shaping, and safety warnings.
- `src/kcs_adapters/zendesk_markup_quality.py` has deterministic findings for
  structure, completeness, safety, public-data leakage, language heuristics,
  GUI paths, source markup, media, and trigger use.
- `evals/kcs_markup_patterns_v1.jsonl` contains 14 compact markup patterns.
- Existing output is reviewer-only; there is no Zendesk write/publish path.
- This is nominal behavior proven by unit/functional tests. It is not proof
  that every source rule is covered or that model-mediated article quality is
  stable in operator use.

## Requirement inventory

| ID | Requirement | Authority | Evidence | Current baseline | Gap / decision | Candidate gate |
| --- | --- | --- | --- | --- | --- | --- |
| `STYLE-001` | Plesk technical article structure is Title, Applicable to, Symptoms, Cause, Resolution, plus labels outside the body. | Plesk Style Guide | confirmed | SCR renderer emits Applicable to/Symptoms/Cause/Resolution when fields are available. | Title is rendered as `h1`; labels/taxonomy are not owned by the reviewer HTML contract. Cause optionality conflicts with broader guide. | deterministic structure fixtures; named-human-review for taxonomy |
| `STYLE-002` | How-to article uses singular Question and Answer; a technical error is not recast as how-to. | Plesk/WebPros Style Guides | confirmed | Q&A renderer exists; core article-type decision is typed. | Need result-level fixtures showing technical-error inputs never become Q&A merely because a procedural answer exists. | deterministic |
| `STYLE-003` | Security alert structure is Situation, Impact, Call to Action. | AQ example deck | provisional | No dedicated security-alert article type. | Feature boundary and product need are unknown; not required for first parity slice. | named-human-review before design |
| `TITLE-001` | Specific Plesk/customer-visible issue, then colon and visible error/detail when available; no trailing period or unnecessary brackets/quotes. | Plesk Style Guide, AQ | confirmed | Generic-title and missing-detail findings exist; renderer removes some cause/solution clauses. | Exact punctuation/length parity is incomplete; title quality also has semantic aspects. | deterministic for syntax; bounded-model-trial for semantic specificity |
| `TITLE-002` | Cause analysis stays out of the title. | operator practice candidate, portable Plesk rules | provisional | Renderer strips selected `caused by`/solution clauses. | Current heuristic coverage and false positives are unmeasured. | bounded-model-trial plus deterministic regression fixtures |
| `ENV-001` | Platform/environment is mandatory and must not claim unverified broad scope. | Plesk Style Guide, portable rules | confirmed | Applicable-to missing/broad-scope findings exist. | Controlled label catalog is absent; exact label value remains reviewer-owned. | deterministic presence/scope; named-human-review for label value |
| `SYM-001` | Symptoms are precise, customer-visible, sanitized, unique, and exclude excessive troubleshooting internals. | AQ, example deck | confirmed | Leakage/transcript checks and GUI-path checks exist. | Semantic relevance and duplication cannot be fully determined by regex. | deterministic leakage invariants; bounded-model-trial and named-human-review for relevance |
| `SYM-002` | Technical Symptoms must use an ordered list. | current local renderer/validator | provisional | Validator blocks a non-`ol` Symptoms body. | Canonical sources prescribe structure but do not clearly require an ordered list for every single symptom. | named-human-review: operator before preserving as blocker |
| `CAUSE-001` | Cause is concise, supported, and separate from resolution actions. | AQ, Plesk Style Guide, portable rules | confirmed | Wordiness, action-in-cause, and cause-chain findings exist. | Semantic support cannot be proved from rendered HTML alone. | deterministic syntax; bounded-model-trial on evidence-linked fixtures |
| `CAUSE-002` | A technical SCR may omit Cause when unknown but a supported workaround exists. | WebPros guide/portable rules | provisional | Renderer omits empty Cause; Plesk guide describes three SCR sections. | Material source conflict. | named-human-review: operator |
| `RES-001` | Resolution is linear, complete, applicable, and action-focused. | AQ, simplification guide, operator candidates | confirmed | Ordered steps, concrete-detail, no-delegation, branch, and explanation findings exist. | Some branch detection is heuristic and current AQ wording says no if/else. Legitimate safety-dependent branches need a rule. | deterministic core invariants; bounded-model-trial for completeness/branch clarity |
| `RES-002` | Start with the real access/entrypoint and link maintained reusable procedures in the exact step. | simplification guide, portable rules | confirmed | SSH/RDP/Plesk login insertion and canonical-link findings exist. | Need fixtures for when an entrypoint is genuinely unnecessary. | deterministic |
| `RES-003` | GUI is primary when available; CLI is secondary/advanced and separated from equivalent GUI steps. | AQ, simplification guide, operator candidates | confirmed | GUI path checks and GUI-first pattern guidance exist. | Renderer does not generically synthesize equivalent GUI/CLI tabs from structured alternatives. | deterministic structural fixture; named-human-review for equivalence |
| `RES-004` | Required steps stay visible; optional, advanced, manual, or fallback detail may be collapsed. | Plesk Style Guide, portable rules | confirmed | Hidden-essential-step blockers and optional-path warnings exist. | Current validator accepts two markup families; canonical-output choice is unresolved. | deterministic |
| `RES-005` | Risky/service-impacting actions receive warning, backup, rollback, or downtime preparation first. | Content Standard, simplification guide, operator candidates | confirmed | Risky-step blockers and renderer safety warnings exist. | Current risky-action vocabulary is not exhaustive; generic generated warning may be too weak for some actions. | deterministic fixtures; named-human-review for risk adequacy |
| `RES-006` | Many non-interactive commands may become a maintained source-control script when that reduces effort; no article attachment. | current AQ | confirmed | Portable rule exists; current runtime has no script recommendation contract. | Decide whether this is a reviewer finding, not renderer behavior. | deterministic threshold proposal plus named-human-review |
| `LINK-001` | Avoid hub/Related Articles collections; each link directly supports a step, answer, or prerequisite. | AQ, example deck | confirmed | Related Articles warning and known-how-to link rules exist. | Relevance of arbitrary links is semantic. | deterministic forbidden section; bounded-model-trial for link relevance |
| `LANG-001` | Simple, neutral, readable, product-safe language; avoid misspellings, passive/complex grammar, personal framing, and diminishing wording. | AQ, checklist, simplification guide | confirmed | Small deterministic language heuristics exist. | Full language quality is model/human-mediated; regex expansion risks false positives. | bounded-model-trial plus named-human-review |
| `ACTUAL-001` | Public knowledge must be current and have a resolution/workaround/allowed ETA; obsolete or unresolved material remains internal. | AQ | confirmed | Core blocks unsupported candidates; no live article-actuality adapter exists. | Requires public metadata/search evidence and publication-state ownership. | deterministic packet invariants; named-human-review |
| `IDENTITY-001` | Search is symptom-oriented; reuse/update identity is article type plus cause-resolution or question-answer identity. | tracked feature docs, operator candidate | confirmed | Typed `ReuseSearchResultsPacket` and core decision contract exist. | Local RAG result metadata does not by itself prove semantic identity. | deterministic adapter/packet tests; named-human-review for uncertain identity |
| `TAG-001` | Tags reflect OS, platform, Plesk version, component, or extension scope. | Plesk Style Guide, AQ | confirmed | Applicable-to values exist, but no controlled tag catalog/output contract. | Taxonomy and ownership unknown. | named-human-review until catalog exists |
| `DATA-001` | Public content uses approved placeholder ranges/names and excludes credentials, customer identifiers, private paths, and sensitive commands. | Content Standard and repo data policy | confirmed | Public-text and metadata safety checks exist. | Keep repository data policy authoritative where stricter; add only source-backed gaps. | deterministic |
| `NAME-001` | Product names are correct; database articles use `MySQL/MariaDB` unless specifically MySQL Community Server. | Content Standard | confirmed | No complete deterministic naming catalog observed in current renderer/quality module. | Needs bounded exact substitutions and exception fixtures. | deterministic |
| `MARKUP-001` | Linux commands use `# ` trigger; Windows CMD uses `C:\> `; PowerShell uses `PS `. A space follows each trigger. | Plesk Style Triggers | confirmed | Renderer recognizes several trigger lines; pattern pack has Linux/CMD/PowerShell examples. | Exact spacing and automatic trigger selection need consolidated fixtures. | deterministic |
| `MARKUP-002` | MySQL input uses `MYSQL_LIN: ` or `MYSQL_WIN: `. | Plesk Style Triggers | confirmed | Quality regex recognizes these as non-step trigger lines; no dedicated pattern entries. | Missing explicit approved snippets and platform-selection fixtures. | deterministic |
| `MARKUP-003` | Plesk messages use `PLESK_ERROR:`, `PLESK_WARN:`, or `PLESK_INFO:` according to UI presentation. `PLESK_INFO` includes white/gray Plesk errors and messages. | Plesk Style Guide/Triggers | confirmed | KCS-15.1 removes lexical reclassification of `PLESK_INFO` and aligns compact guidance with source meaning. | Automatic trigger selection remains out of scope because rendered source lacks UI-presentation evidence. | deterministic source fixtures |
| `MARKUP-004` | Configuration/log/output text uses `CONFIG_TEXT: ` when a more specific trigger does not apply. | Plesk Style Triggers | confirmed | Renderer and pattern pack support CONFIG_TEXT. | Current pattern guidance overgroups exact Plesk messages; precedence needs fixtures. | deterministic |
| `MARKUP-005` | Warnings and notes use `Warning: ` and `Note: ` before relevant content. | Plesk Style Triggers | confirmed | Pattern and safety checks exist. | `Important:` is a local extension, not in the supplied Plesk trigger list. | deterministic; document extension or reject it |
| `MARKUP-006` | Resizable images use approved class and meaningful alternative text. | Style Guides/Triggers | confirmed | Quality check enforces `class="resizable"`; pattern includes alt text. | Alt-text quality and public accessibility remain human/integration checks. | deterministic presence; named-human-review/accessibility smoke |
| `MARKUP-007` | Prefer tabs for equivalent alternatives; use approved tab markup with exactly one default tab. | Plesk Style Guide | confirmed | Pattern pack contains both compact legacy tabs and canonical style-guide tabs; validator accepts known shapes. | Choose canonical emitted shape while deciding whether legacy input remains accepted. The supplied Plesk page itself shows `tabs-content` in the example but says `tabs-contents` in prose. | deterministic plus named-human-review for wrapper spelling |
| `MARKUP-008` | Accordion uses approved markup and only hides optional detail. | Plesk Style Guide | confirmed | Two accepted shapes exist with hidden-essential blockers. | Same canonical-output/legacy-input decision as tabs. | deterministic |
| `MARKUP-009` | Output that should not be selected can use `<span class="unselectable">`. | Plesk Style Triggers | confirmed | No explicit pattern entry or validator rule observed. | Add only if a concrete renderer use case is approved. | deterministic |
| `MARKUP-010` | Complex tables use the approved `table100` wrapper. | Plesk Style Guide/Triggers | confirmed | Pattern and wrapper findings exist. | Need a golden valid/invalid table fixture tied to source spelling. | deterministic |
| `MARKUP-011` | `<div class="internaldata">` is a presentation marker, not a privacy/security boundary; hidden content can still be exposed. | Plesk Style Triggers and repo output policy | confirmed | Validator uses it for reviewer-only detail and removes it from public Resolution checks. | Any public delivery path must strip/block internal content independently. | deterministic forbidden-output test |
| `MARKUP-012` | Approved horizontal separator markup may separate alternatives instead of prose `OR`. | Plesk Style Triggers, example deck | confirmed | No explicit pattern entry or validator rule observed. | Need exact use boundary; do not replace logical prose automatically. | deterministic snippet; named-human-review for appropriateness |
| `EXAMPLE-001` | Golden examples are selected from approved public articles and scoped to specific patterns, without copying full bodies. | tracked KCS-15 plan, portable candidate set | confirmed | A 27-item primary candidate list exists in `plesk_support`; no KCS-15 approved set is tracked here. | Operator must approve the first compact example set and allowed uses. | named-human-review: operator |

## Confirmed source conflicts and drift

1. KCS-15.1 resolves the confirmed `PLESK_INFO` drift: error-like vocabulary no
   longer overrides the source-valid white/gray presentation trigger. Automatic
   trigger selection remains intentionally unimplemented without presentation
   evidence.
2. The Plesk-specific guide describes three SCR sections; the broader WebPros
   guide and portable operator rules allow Cause to be absent. Cause optionality
   remains an operator decision.
3. The current validator makes ordered-list Symptoms a blocker. The supplied
   sources require customer-visible Symptoms and standard structure but do not
   clearly make `<ol>` mandatory for every case.
4. The runtime accepts compact legacy and style-guide tabs/accordion shapes.
   Compatibility may be intentional, but the canonical emitted shape is not
   yet decided.
5. The historical example deck says to attach scripts. The current AQ snapshot
   explicitly supersedes that advice with maintained engineering source
   control.
6. The Plesk Style Guide tab example uses `tabs-content`, while its explanatory
   note says `tabs-contents`. Current patterns use the singular form; source
   clarification or operator review is required before treating the spelling
   as a blocker.

## RAG placement decision

KCS-15.2 owns RAG-assisted reuse because search/reuse is part of producing a
good KCS outcome before drafting. It remains outside KCS core and does not
block independent style-parity work.

KCS-15.2 is split by the decision each slice can prove:

1. `KCS-15.2a` — the completed loopback adapter proves bounded public-metadata
   readiness and search feasibility. Search hits do not prove cause-resolution,
   question-answer identity, article fit, or actuality.
2. `KCS-15.2b` — the operator-facing comparison must determine what ticket
   context, candidate/article information, alternatives, and consequences are
   visible at the correct workflow moment. Its design is open and Delivery is
   locked.

This placement keeps style parity independent while ensuring later
reuse-aware drafting or article-actuality decisions do not rely on a workflow
that never searched reusable public knowledge.

## Proposed KCS-15 slice order

1. `KCS-15.0` — this source pack, precedence model, parity matrix, and gate
   map. Operator benefit: future behavior changes become reviewable against a
   stable evidence baseline.
2. `KCS-15.1` — deterministic trigger/markup parity, starting with
   `PLESK_INFO` meaning and missing source-backed trigger fixtures. Operator
   benefit: removes known false blockers and makes source HTML more predictable.
3. `KCS-15.2a` — safe loopback metadata-only RAG adapter and readiness boundary,
   now complete. Operator benefit: the system can obtain bounded public reuse
   candidates without letting search own identity.
4. `KCS-15.2b` — operator-facing reuse comparison, only after decision-ready UX
   evidence shows the relevant ticket context together with enough candidate or
   article information to judge reuse/update/create. Delivery remains locked.
5. `KCS-15.3` — deterministic structure, title, entrypoint, safety, and naming
   parity after resolving the Cause/Symptoms decisions. Operator benefit:
   fewer mechanical corrections in reviewer handoff.
6. `KCS-15.4` — approved public golden examples and bounded model trials for
   semantic completeness, language, and relevance. Operator benefit: measured
   drafting quality instead of growing regex heuristics.
7. Optional operator-confirmed drafting scopes substage only after its own UX
   approval. Operator benefit must exceed the cognitive cost of another
   confirmation step; it is not the definition of KCS-15.

KCS-14.5 is closed. Its retained semantic ownership, provider/evaluation, and
incident control-surface contracts remain frozen. Reopening those surfaces
requires a separate behavior-change design; independently approved KCS-15 work
may proceed when it leaves those surfaces and their safety contracts unchanged.
