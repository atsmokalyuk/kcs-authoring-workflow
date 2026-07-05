# Ousterhout Design Review Checklist

This is a project-specific design-review checklist derived from the local
`A Philosophy of Software Design` PDF. It is a paraphrased working checklist,
not a replacement for the book and not a runtime contract.

Use it for KCS-14 planning, refactor reviews, Fable 5 review packets, ChatGPT
Pro review packets, and Codex self-review before code movement.

Use this checklist as the primary lens for code map, design review, and
behavior-preserving refactor work. Use it as a supporting lens for documentation
ownership and test-backed refactor safety. For local tool command definitions,
CI/GitHub Actions details, agent runner automation, BDD syntax,
cloud/runtime deployment, or harness-specific implementation details, use this
checklist as a required design review lens, but not as the primary source of
implementation detail.

## Core Goal

Reduce complexity for future readers and maintainers.

Complexity shows up as:

- change amplification: small changes require edits in many places;
- cognitive load: developers must hold too much context to work safely;
- unknown unknowns: it is unclear what must be known or changed until bugs
  appear.

Complexity is mainly created by:

- unnecessary dependencies;
- obscurity;
- information leakage;
- shallow abstractions;
- special cases;
- vague names;
- unclear interfaces;
- unnecessary error paths.

## Continuous Design

- Treat design as continuous, not a one-time upfront phase.
- Design only the next bounded slice, then let implementation reveal hidden
  complexity.
- After each slice, evaluate what the code revealed and improve the design
  before the system grows around the problem.
- Prefer many small design investments over large speculative redesigns.
- Working code is not enough if it leaves avoidable complexity behind.
- Each slice should make the system at least slightly easier to understand or
  change.

## Strategic Programming

- Avoid shortcuts that complete the current task by increasing future
  complexity.
- Budget time for cleanup and design improvement during normal feature work.
- Treat technical debt as borrowed future time, not as a harmless local
  decision.
- When schedule pressure forces a tactical compromise, record the compromise
  and keep it isolated.

## Module Depth

- Prefer deep modules: small, simple interfaces with substantial useful
  behavior hidden behind them.
- Avoid shallow modules: interfaces that are nearly as complex as the
  implementation they wrap.
- A split is good only if it reduces what callers must know.
- A split is bad if it only moves code around and creates more interfaces.
- Use file/function/class size as a smell, not as a rule.
- Do not create classitis: many tiny classes/files with little behavior and
  many names to learn.
- A module is not deep if users must read its implementation to use it
  correctly.

## Deep Modules Over Classitis

Use this as a prominent review gate for KCS-14 code map and refactor work.

The problem is not small files, classes, or methods by themselves. The problem
is shallow abstractions: many small entities, each hiding little real
complexity, each adding an interface, and forcing readers to jump across many
files to understand one behavior.

Good splitting:

- makes ownership clearer;
- keeps or simplifies the external interface;
- hides a real design decision;
- reduces what callers must know;
- lets adjacent modules ignore more implementation detail.

Bad splitting:

- moves code around without hiding knowledge;
- creates builders, validators, formatters, accessors, mutators, or factories
  that are thin pass-through wrappers;
- turns one understandable behavior into many tiny interfaces;
- increases the number of names a reader must learn;
- makes behavior harder to trace even though each piece is short.

Ask:

- Did this split reduce what a caller must know?
- Did the external interface stay the same size or become simpler?
- Does the new module own a real design decision?
- Does the new class/file hide meaningful complexity?
- Would a future change have fewer places to touch?
- Are we splitting because ownership changed, or only because a file is large?
- Did we create more interfaces than behavior?
- Can each new module be understood independently?

KCS example:

- Splitting old Desktop MCP code into `desktop_tool_schemas`,
  `desktop_tool_results`, `desktop_semantic_review`, `desktop_ticket_ref`, and
  `desktop_reviewer_bundle` is justified when each module owns a real boundary:
  schemas, result shaping, semantic-review contract, clean-ticket storage, or
  bundle writing.
- Splitting semantic-review refs into many tiny builder/validator/formatter/
  accessor/mutator classes would be classitis if those classes only pass values
  around and force readers to follow one concept through many files.

## Interfaces

- Optimize interfaces for callers, not implementers.
- Prefer a simple interface even when that makes the implementation more
  complex.
- Design the common use case to be simple and obvious.
- Make informal interface rules explicit in docs, tests, comments, schemas, or
  review checklists.
- Do not hide important usage constraints behind a falsely simple API.
- Interface documentation should describe what users must know, not internal
  implementation mechanics.
- If interface docs must explain implementation details, the module is probably
  shallow or leaky.

## Information Hiding

- Hide design decisions inside one owner module when callers do not need to
  know them.
- Private fields/methods alone are not enough; public getters/setters can still
  leak internal state and make callers depend on it.
- Information is leaking when the same design decision is encoded in multiple
  modules.
- When information leaks, either merge the closely related modules or extract a
  deeper owner with a simpler interface.
- Do not replace back-door leakage with a new interface that exposes the same
  details.
- Partial hiding is still useful when uncommon details are kept off the common
  path.

## Temporal Decomposition

- Do not split modules merely by execution order: read, process, write,
  prepare, submit, continue.
- Split by ownership of knowledge and design decisions.
- If the same schema, validation rule, blocker behavior, or format rule appears
  in several temporal files, the design is leaking information.
- Workflow/orchestration may describe temporal flow, but core rules should live
  in ownership modules.

## Ownership Over Time Order

Use this as a prominent review gate for KCS-14 code map and refactor work.

Do not split modules by workflow chronology when the same knowledge must be
shared across the steps. Keep schemas, validation rules, blocker behavior,
state ownership, and data-shape ownership in the module that owns the concept.

Ask:

- Is this file named after a workflow step or a knowledge owner?
- Does a `prepare` / `submit` / `continue` / `write` split duplicate the same
  schema or blocker knowledge?
- If this contract changes, how many modules must change?
- Should these steps remain in one ownership module while workflow
  orchestration stays outside?
- Which module owns the informal interface rules?
- Which adjacent modules must not know those rules?

KCS example:

- `desktop_semantic_review` should own semantic-review state, selected excerpt
  packets, allowed `source_refs`, submit validation, and semantic-review
  blocker behavior.
- Desktop draft/tool orchestration may call prepare/submit/continue flow, but
  it must not own candidate schema interpretation, source-ref validation,
  article drafting, or semantic-review blocker policy.

## Generality And Specialization

- Prefer general-purpose interfaces that cover current needs without being tied
  to one incident, product case, or ticket shape.
- Keep specialized rules in the layer that owns that specialization.
- Replace families of special-purpose methods with one general mechanism when
  the common behavior is real.
- Do not over-generalize: the API must still be easy for current use cases.
- Eliminate special cases when the normal design can handle them cleanly.
- Special cases that remain should be localized and tested.

## Layers

- Adjacent layers should provide different abstractions.
- Pass-through methods are a red flag unless they add real dispatch,
  translation, policy, validation, or boundary value.
- Pass-through variables force intermediate layers to know irrelevant details;
  consolidate shared state behind a proper context or owner when needed.
- Decorator/wrapper classes are often shallow; use them only when they provide
  a real interface translation or deep added behavior.
- Do not add a layer unless it removes more complexity than it introduces.

## Pull Complexity Downward

- A module usually has more users than maintainers, so it is often better for
  the module implementation to absorb complexity than to push it to callers.
- Pull complexity down only when it belongs to the module's responsibility,
  simplifies callers, and simplifies the module interface.
- Avoid making callers choose policies or configuration values that the module
  can determine safely.

## Better Together Or Apart

Keep code together when:

- the pieces share a design decision or data format;
- users usually need both pieces together;
- one piece cannot be understood without the other;
- combining them enables a simpler interface.

Split code apart when:

- one part owns a separate design decision;
- the split hides knowledge behind a simpler interface;
- the split removes duplication without creating a complex signature;
- callers can use each part independently.

Do not extract one-line helpers or tiny classes unless the new name captures a
real abstraction.

## Error Design

- Reduce the number of places where errors must be handled.
- Define error cases out of existence when a normal behavior can cover the
  condition safely.
- Mask low-level exceptions inside the module when callers do not need the
  details.
- Aggregate related failures at a boundary when one handler can report a safe,
  useful result.
- Expose failures when callers need the information to act correctly.
- Error behavior is part of the interface; many errors make a module shallower.
- Fail closed with explicit safe blocker codes for data, privacy, contract, and
  workflow violations.

## Design It Twice

- For major boundaries, sketch at least two plausible designs before choosing.
- Compare alternatives by caller simplicity, generality, information hiding,
  testability, and failure behavior.
- If neither alternative is good, use their weaknesses to design a third.
- Use this especially before adding new modules, schemas, adapters, or
  review/tooling surfaces.

## Comments And Documentation

- Comments should capture design knowledge that code cannot express.
- Do not repeat what the code already says.
- Document abstractions, invariants, preconditions, side effects, return
  meanings, failure modes, and caller obligations.
- Separate interface documentation from implementation documentation.
- Implementation comments should explain non-obvious intent or rationale, not
  narrate obvious statements.
- Cross-module design decisions need a discoverable home; do not leave them
  only in commit messages or chat.
- Write interface comments and contract notes early enough that they influence
  the design.
- If a simple complete comment is hard to write, the design may be unclear.

## Naming

- Treat naming as design, not polish.
- Names should create a correct mental model without reading implementation.
- Prefer precise, consistent names over short vague names.
- A vague name is a design bug when readers must guess the concept.
- Use the same name for the same concept everywhere and different names for
  different concepts.
- Rename aggressively when a name hides meaning or invites misuse.

## Modifying Existing Code

- When touching existing code, try to improve the design locally.
- Avoid repeated minimal patches that add special cases and dependencies.
- Keep design information near the code or authoritative doc it affects.
- If a commit message contains future-critical reasoning, move or reference that
  reasoning in code comments or docs.
- Finished changes should leave the system close to how it would look if the
  new requirement had been considered from the beginning.

## Consistency And Obviousness

- Similar things should be done similarly; different things should be visibly
  different.
- Consistency gives cognitive leverage across the codebase.
- Do not introduce a new convention only because it feels locally better.
- Code is obvious when a reader's first guess about behavior is correct.
- Avoid generic containers and generic names when a typed structure with
  meaningful field names would make the concept clear.
- Document event-driven or indirect invocation paths so readers know when code
  runs.

## Inheritance And Composition

- Interface inheritance can create useful shared abstractions.
- Implementation inheritance easily creates hidden dependencies between parent
  and child classes.
- Prefer composition when shared behavior can live in a helper/service without
  forcing a shared state hierarchy.
- If implementation inheritance is used, keep parent state owned by the parent
  and avoid child classes depending on parent internals.

## Iterative Development

- Iteration is useful when each step improves or adds abstractions.
- Iteration is harmful when it only accumulates features and temporary
  workarounds.
- The increment of durable work should often be an abstraction, contract, or
  boundary, not only a visible feature.

## Tests

- Tests are design infrastructure because they make refactoring safe.
- Behavior tests should protect important boundaries before code movement.
- Unit tests are useful because they locate logic failures precisely.
- Integration/system tests prove parts work together but are less precise for
  refactor safety.
- Writing tests first is most valuable for bug fixes and explicit behavior
  contracts; do not let test-by-test implementation replace design thinking.

## Design Patterns

- Use known patterns when they fit the problem naturally.
- Do not force a pattern when a direct design is cleaner.
- A pattern that adds layers, pass-through methods, or exposed state without
  hiding complexity is not helping.

## Performance

- Do not add complexity for assumed performance wins.
- Measure before and after optimization.
- Prefer fundamental fixes: better algorithms, data structures, caching, or
  architecture.
- Keep the common path short and clean.
- Move rare special cases off the common path.
- Keep performance complexity only when it gives measured value or is clearly
  required by known constraints.

## Deciding What Matters

- Good design separates important concepts from details.
- Important concepts should be visible, central, clearly named, and consistent.
- Unimportant details should be hidden, localized, automated, or kept out of
  interfaces.
- Look for leverage: a concept matters if understanding it helps explain many
  behaviors.
- Minimize the number of things that matter to callers.
- If unsure what matters, state a hypothesis, build a small slice around it,
  observe the result, and revise.

## KCS-14 Review For

- source-of-truth drift across roadmap, architecture docs, playbooks, README,
  and slice plans;
- information leakage between modules;
- shallow abstractions, classitis, pass-through modules, or pass-through
  methods;
- temporal decomposition where workflow steps are split by execution order
  instead of ownership of knowledge;
- unclear ownership boundaries;
- contract drift hidden inside documentation cleanup or refactor work;
- missing behavior tests before refactoring risky boundaries;
- local-only process leaking into product or runtime docs;
- runtime behavior changes hidden inside docs, process, or codebase refactor
  slices.

## KCS Contracts To Preserve

- packet contracts unless an approved behavior-change slice says otherwise;
- privacy boundaries;
- fail-closed behavior;
- Claude Desktop control-surface behavior;
- Python-owned validation, decisions, rendering, bundle output, and failure
  behavior;
- no Zendesk writes, no Help Center publication, and no customer reply
  generation;
- `auto_publish_allowed=false`;
- existing test expectations unless intentionally updated with review.

## KCS-Specific Red Flags

- Desktop adapter starts owning semantic extraction, KCS action decisions,
  rendering, or bundle policy;
- renderer starts making KCS decisions;
- semantic-review submit path accepts broad payloads, drafts, HTML, or copied
  ticket text;
- review tooling stores raw tickets, selected excerpts, reviewer bundles,
  credentials, provider payloads, or private paths;
- code map duplicates long source summaries instead of indexing ownership and
  contracts;
- doc cleanup deletes active constraints instead of moving or referencing them;
- refactor splits semantic review rules, packet schema, and blocker behavior
  across several temporal files;
- new helper classes hide no knowledge and only increase names/interfaces.

## Reviewer Questions

- Is the slice small enough to review independently?
- Are behavior, contracts, failure behavior, and tests defined before code?
- What complexity is being hidden?
- What should this module not know?
- Does this change reduce what future developers must know?
- Does each module hide the right complexity?
- Is the interface simpler than the implementation?
- Did we move knowledge to one owner or duplicate it?
- Are we splitting by ownership, not by execution order?
- Does the caller need fewer details after this change?
- Did the refactor remove complexity or only move it?
- Are behavior tests protecting the changed boundary?
- What risk should be checked before the next slice starts?
