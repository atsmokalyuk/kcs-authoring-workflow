# Engineering References And Grounding

Status: advisory grounding material. This document maps project rules to the
external sources that motivate them. It is not an authoritative contract
layer. If any source conflicts with repository contracts, tests, or the
policy kernel, the repository wins and the conflict may be surfaced as a
Behavior Change Request.

Suggested tracked home: `docs/internal/engineering-process/references.md`
(project-wide grounding). Generic reusable subsets may later move to
`engineering-playbook/` if a second project proves reuse.

Verification note: source titles, authors, and years are stated from
assistant/operator memory as of 2026. Exact URLs, editions, and document
versions should be verified before citing externally. Do not treat unverified
links as authoritative.

## How To Use This Document

- Before planning or reviewing a slice, check which grounding family applies.
- Use sources as design lenses and rationale, not as runtime rules.
- When a repo rule is challenged in review, cite the grounding family here
  instead of re-arguing from scratch.
- When a new rule is added without any grounding family, either add the
  grounding here or mark the rule as project-local convention.

## Grounding Families

### 1. Software Design And Refactoring

Primary lens for code map, design review, and behavior-preserving refactor
(KCS-14 slices 5-6). Local derived artifact:
`ousterhout-design-review-checklist.md`.

- John Ousterhout, "A Philosophy of Software Design" (2nd ed.).
  Grounds: deep modules over classitis; temporal decomposition ban;
  information hiding/leakage; pass-through methods; pull complexity downward;
  define errors out of existence; design it twice; comments as design
  knowledge; strategic vs tactical programming.
- Martin Fowler, "Refactoring: Improving the Design of Existing Code"
  (2nd ed., 2018).
  Grounds: definition of behavior-preserving change; small independent
  refactor steps; one ownership area per PR; bisectability expectations.
- Michael Feathers, "Working Effectively with Legacy Code" (2004).
  Grounds: characterization/behavior tests before code movement; seams;
  "tests before refactor" gate in Slice 3 -> Slice 6 ordering.
- Harry Percival, Bob Gregory, "Architecture Patterns with Python" (2020).
  Grounds: service layer, ports/adapters, core vs adapter split, test
  boundaries. Per KCS-14 plan, deferred as implementation-level reference
  until Slice 6 Aggregate Design Review diagnoses an `architecture_error`
  around core/adapters/tests boundaries. It is not activated by ordinary
  `map_error` or `process_error` findings. When activated, use the protocol in
  current behavior specification and `review-checkpoints.md` rather than
  applying book patterns broadly.

### 2. Agentic Engineering Practice

Primary lens for the policy kernel, agent workflow, context discipline, and
work modes (KCS-14 slices 1-2).

- Anthropic, "Building Effective Agents" (Dec 2024).
  Grounds: workflows vs agents distinction; deterministic orchestration owns
  control flow; "Code decides, LLM drafts, Validators block".
- Anthropic, "Claude Code: Best Practices for Agentic Coding" (2025).
  Grounds: short policy kernel file pattern (CLAUDE.md/AGENTS.md); explicit
  validation commands; human checkpoints; targeted context.
- Anthropic, "Effective Context Engineering for AI Agents" (2025).
  Grounds: prefer less context with higher authority; context reset instead
  of compaction; compact tool output budgets; avoid stale history.
- agents.md convention (open format, 2025; originated around OpenAI Codex).
  Grounds: repo-local agent policy file as the source of project-specific
  agent behavior.
- OpenAI, "A Practical Guide to Building Agents" (2025).
  Grounds: bounded tool surfaces; guardrails; human-in-the-loop escalation.
- Dex Horthy (HumanLayer), "12-Factor Agents" (2025).
  Grounds: own your context window; small bounded agents; tools as
  structured outputs; explicit control flow ownership.

#### Organization-Neutral Field Reference: Agentic Delivery Workflow Shapes

Status: advisory architecture input, normalized from an operator-provided
comparative field report in 2026. The source report was assembled from project
documentation, task records, review comments, and an observed output example.
Organization names, internal issue identifiers, private endpoints, personal
attribution, repository conventions, and team-specific delivery rules are
intentionally excluded here. The underlying evidence was not independently
reproduced in this repository.

The report compared three workflow shapes:

1. **Tracked task pipeline.** A staged workflow separates requirement
   extraction, planning, implementation, self-review, optional specialist
   checks, and issue-tracker synchronization. Its strongest feature is a
   human-readable plan produced before implementation. It had been exercised
   on several real tasks. Reported weaknesses included fixed overhead,
   occasional plans larger than the changes, and no explicit change boundary,
   affected-surface inventory, or unknown register.
2. **Interactive clarification and handoff.** An interactive clarification
   step gathers missing context, a handoff step normalizes it, and a final step
   produces a working specification. One reported real-task use produced a
   concise specification with few manual corrections. Reported weaknesses
   included required operator presence, transient artifacts that could become
   stale, and no explicit affected-surface or validation plan.
3. **Complexity-routed delivery.** A routing step varies planning and review
   effort by task materiality. The middle route uses planning, adversarial
   challenge, an explicit human checkpoint, implementation from a bounded
   handoff, and independent review; the highest-risk route stops for human-led
   technical framing. This shape directly addressed over-planning, but its
   implementation evidence was limited to a practitioner description. Its
   reported gaps included no affected-surface inventory, unknown ownership, or
   validation plan. A route that skips all gates for apparently trivial work
   is not accepted as a portable safety rule.

Portable architecture candidates from the comparison:

- separate clarification, design, Delivery, validation, and review concerns;
- scale ceremony by materiality and boundary impact rather than apply one
  fixed pipeline to every change;
- use adversarial plan review when a material design or integration risk
  triggers it;
- require a human decision checkpoint before material Delivery;
- hand implementation the smallest current authoritative context instead of
  relying on accumulated conversation history;
- keep planning artifacts only when they remain useful for authorization,
  implementation, or later review.

Required corrections before adopting any of the three shapes:

- declare changed and unchanged boundaries and affected surfaces;
- keep a material unknown inventory with resolution ownership;
- map acceptance criteria to deterministic checks, bounded trials, or named
  human-review gates;
- keep outcome agreement, design selection, and Delivery authorization as
  independent states;
- preserve explicit stop conditions and failure behavior;
- retain validation and safety gates for bounded leaf changes even when a
  separate tracked slice plan is not triggered.

Do not import from the examples:

- vendor-specific model assignments, command names, or tool integrations;
- issue-tracker status automation or automatic commit behavior;
- repository directory layouts, branch rules, or commit conventions;
- fixed numeric complexity levels or unvalidated routing thresholds;
- a rule that architectural decisions are recorded only above a complexity
  label;
- broad gate skipping based only on a task being described as trivial.

This reference may inform architecture selection for the separate agentic
engineering kit project after the KCS-17 handoff boundary. It does not define a
later slice, authorize implementation, prove cross-project portability, or
override the repository's Spec-First DDD, privacy, Git, validation, and review
contracts.

### 3. Untrusted Model Output And LLM Security

Primary lens for data boundaries, handoff contracts, and validation gates.
Applies to every slice that touches Claude-visible surfaces.

- OWASP Top 10 for LLM Applications (LLM01 Prompt Injection, LLM02 Insecure
  Output Handling, and related entries).
  Grounds: Claude/provider output is untrusted until validated; no unsafe
  input echo; bounded tool responses; forbidden-content scanning.
- Simon Willison, prompt injection corpus (2022-2025), including the
  dual-LLM pattern and the "lethal trifecta" framing.
  Grounds: never combine private data access, untrusted input, and external
  write/exfiltration paths; reviewer-only outputs; no auto-publish.
- Google DeepMind, "Defeating Prompt Injections by Design" (CaMeL, 2025).
  Grounds: deterministic code owns control flow and capabilities; LLM output
  is data, not instructions; Python-owned packet acceptance.

### 4. Deterministic Enforcement And Code Review At Scale

Primary lens for the enforcement ladder, blocking vs advisory split, and
Slice 7 tooling limits.

- Sadowski et al., "Lessons from Building Static Analysis Tools at Google"
  (CACM, 2018; Tricorder).
  Grounds: noisy blocking checks get ignored; advisory channel for
  heuristics; do not fake design judgment with blocking regex; fix-rate as
  the health metric for checks.
- Winters, Manshreck, Wright, "Software Engineering at Google" (2020).
  Grounds: shift-left; a rule without a check does not exist ("Beyonce
  rule"); policy-as-code culture; small reviewable changes.
- pre-commit framework; Open Policy Agent / conftest (practice-level
  references).
  Grounds: policy as data plus deterministic check; local gates before
  commit; freeze-list style path checks.
- Ruff, Radon, McCabe complexity, pytest (project toolchain references).
  Grounds: complexity threshold 7 for AI-assisted code; Radon as advisory
  complexity/maintainability sensor; lint as enforcement; BDD-shaped pytest as
  the default test convention.

### 5. Spec-First And Behavior-Driven Development

Primary lens for slice planning, acceptance criteria, and
functional-test-from-behavior (KCS-14 slice 3).

- Dan North, "Introducing BDD" (2006).
  Grounds: Given/When/Then as behavior language; acceptance criteria become
  executable scenarios.
- GitHub Spec Kit (2025); Amazon Kiro (2025).
  Grounds: spec -> tests -> implementation workflow as current industry
  direction; spec artifacts as first-class inputs to agents. Used as trend
  confirmation, not as tooling to adopt.

### 6. Process Measurement And Improvement

Primary lens for slice closeout metadata and the prose-to-check promotion
rule.

- Forsgren, Humble, Kim, "Accelerate" (2018) and DORA research program.
  Grounds: measure the process with lagging indicators; small batch sizes;
  the closeout record (retry buckets, blocker codes, checks added) is a
  value-safe reduction of this approach.
- Lean/kaizen and andon practice (general operations literature; no single
  canonical citation).
  Grounds: repeated agent retries are a process-defect signal; recurring
  review findings escalate to deterministic checks or structural boundaries.
  Marked as synthesis: no direct agentic-engineering citation exists.

### 7. Risk Management, Oversight, And Autonomy Gating

Primary lens for promotion gates, autonomy gate, and approval/change control.

- NIST AI Risk Management Framework (AI RMF 1.0) and Generative AI Profile
  (NIST AI 600-1, 2024).
  Grounds: staged risk expansion; human oversight; map/measure/manage risk
  before widening scope; synthetic -> sanitized -> approved promotion path.
- ISO/IEC 42001 (AI management systems, 2023).
  Grounds: documented approval and change control for boundary expansion;
  auditable process artifacts.

### 8. KCS Domain Grounding

Primary lens for active KCS-15 style/markup parity and for existing
decision/identity rules. KCS-15 remains out of KCS-14 scope and proceeds only
through independently approved behavior slices.

- Consortium for Service Innovation, KCS v6 Practices Guide.
  Grounds: knowledge capture in the workflow; reuse before create; article
  quality; evolve loop remains human-owned.
- Source KCS Style Guide, Article Quality Criteria, Content Standard, and
  supporting examples indexed in `docs/internal/kcs-sources/README.md`.
  Grounds: article structure, markup, and style parity targets.
- Local `plesk_support` prototype (reference-only per portability policy).
  Grounds: proven workflow-first architecture, typed packets, deterministic
  gates. Use only through
  `docs/internal/portability/portability-from-plesk-support.md`.

## Rule-To-Source Mapping

| Repo rule / artifact | Grounding family | Primary sources |
|---|---|---|
| `AGENTS.md` short policy kernel + layered docs | 2 | Anthropic best practices; agents.md convention |
| Prefer less context with higher authority; context reset | 2 | Anthropic context engineering |
| Code decides / LLM drafts / Validators block | 2, 3 | Anthropic agents; CaMeL |
| Claude output untrusted until validated; no unsafe echo | 3 | OWASP LLM Top 10; Willison |
| No auto-publish; reviewer-only outputs; no write paths | 3, 7 | Willison (lethal trifecta); NIST AI RMF |
| Promotion gates: synthetic -> sanitized -> approved | 7 | NIST AI RMF; ISO/IEC 42001 |
| Autonomy gate; stop/ask conditions | 2, 7 | OpenAI guide; NIST AI RMF |
| Spec-first slice planning; acceptance criteria | 5 | Dan North; Spec Kit/Kiro trend |
| BDD-shaped pytest; golden fixtures; forbidden-path tests | 5, 1 | Dan North; Feathers |
| Behavior tests before refactor (Slice 3 before 6) | 1 | Feathers; Fowler |
| Deep modules; no classitis; ownership over time order | 1 | Ousterhout |
| One ownership area per refactor PR; bisectability | 1 | Fowler |
| Enforcement ladder; blocking vs advisory split | 4 | Tricorder; SWE at Google |
| Rule without a check does not exist (promotion rule) | 4, 6 | SWE at Google; kaizen synthesis |
| Recurring finding twice -> check/boundary candidate | 6, 4 | Kaizen synthesis; Tricorder |
| Slice closeout metadata (value-safe enums) | 6 | Accelerate/DORA |
| Complexity threshold 7; Ruff gates | 4 | Project toolchain; SWE at Google |
| Freeze-list diff and schema-hash checks | 4 | Policy-as-code practice |
| Retry loops as process-defect signal | 6 | Kaizen/andon synthesis |
| KCS action/identity rules; KCS-15 article quality | 8 | KCS v6; source style guide |

## Known Gaps And Honest Caveats

- No unified "agentic engineering" standard exists as of early 2026. This
  document aggregates vendor guidance, security frameworks, and classical
  engineering literature applied to agents.
- Entries marked "synthesis" have no single canonical citation; they are
  transfers from adjacent disciplines and should be treated as project
  convention with rationale, not as cited industry standard.
- Roughly two thirds of the grounded rules are classical engineering
  (contracts, fail-closed, fixtures, small slices) applied to a high-entropy
  executor. Their grounding predates agents; this is expected and is a
  strength, not a gap.
- Sources evolve quickly (2024-2026 vendor guidance especially). Re-verify
  before external citation; update this file when a grounding source is
  superseded.

## Maintenance Rules

- Advisory only: this file never overrides contracts, tests, the policy
  kernel, or the data-handling baseline.
- Update triggers: a new process rule lands without grounding; a cited
  source is superseded; a synthesis entry gains a real citation; KCS-15
  reactivates family 8.
- Do not copy long excerpts from any source into this repository; reference
  by title and section only.
- Keep this file out of the authoritative-layers list in `AGENTS.md`.
