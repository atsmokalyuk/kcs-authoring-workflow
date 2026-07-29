# KCS-15.2b2 Phase C: In-Chat Operator Surface

Status: host-blocked and deferred. The bounded implementation remains useful
behind a valid tool entry, but the installed Claude Desktop client exposes no
supported operator-controlled launcher for the first transition. The direct
local controller remains the deterministic KCS-15.2b2 entrypoint.

## Production recovery decision

The installed in-chat Phase C overlay is not an accepted production path.
Live trials showed that it can render before a valid pending selection exists,
lose in-memory pending state across a connector restart, and leave Claude free
to create an article through host file actions after the KCS call is blocked.
The resulting experience does not satisfy the requested outcome.

Recovery therefore restores the last proven text-based Desktop workflow while
retaining the completed comparison backend and deterministic local controller:

- do not package or advertise the Phase C App resource, App-only tools, or
  App-specific selection interception in the production connector;
- retain Python-owned item detection, opaque selection refs, bounded reuse
  comparison, operator-confirmed outcomes, and fail-closed drafting;
- retain the existing compact text choice/reuse results as the Desktop
  fallback, with no claim that generic chat must invoke or obey them;
- keep the fixture UI and Phase C source as design evidence only until a host
  provides an operator-controlled launcher and a permission boundary that
  excludes alternative draft-capable actions;
- do not begin title, markup, or other style-parity Delivery until the restored
  article workflow passes a fresh end-to-end smoke.

Recovery acceptance gates:

| Acceptance criterion | Gate |
| --- | --- |
| The recovery package contains no Phase C resource, App-only tool, or UI metadata. | deterministic package-content and tool-surface tests |
| A two-issue ticket returns both bounded KCS items before any draft. | deterministic transport test and fresh installed-host smoke |
| The operator can select one or more returned items through the proven text contract. | deterministic selection-ref tests and installed-host smoke |
| Each selected item reaches reuse comparison before drafting. | deterministic sequential comparison tests and installed-host smoke |
| `reuse`, `update`, and `need_more_evidence` do not create a new draft; `none_fit` may continue only for that item. | deterministic outcome matrix |
| The connector restart/stale-ref case fails closed and tells the operator to restart the KCS workflow; it never treats stale chat state as an operator choice. | deterministic stale-state regression test |
| Generic Claude chat remains explicitly best-effort and outside the deterministic enforcement claim. | design/behavior-drift review |

Stop condition: if a fresh installed-host smoke again bypasses the KCS tool or
uses an alternative host drafting action, record the host bypass and stop.
Do not patch prompts or add another in-chat UI layer. The supported
deterministic product entrypoint remains the local controller until the host
contract changes.

Recovery evidence on 2026-07-24:

- the installed recovery package contained only the seven production text
  tools and no Phase C resource or App-only tool;
- `/draft ticket-2a5274b2bdcd` returned two KCS items, accepted both text
  selections, completed two sequential reuse comparisons, and wrote two
  reviewer bundles after two operator-confirmed `none_fit` outcomes;
- this confirms that the core text workflow does not depend on the deferred
  Phase C UI;
- the final Claude response omitted the first bundle from its summary. The
  source correction is owned by the Phase B tool-result handoff, not by Phase C
  UI code, and requires one installed-client repetition before recovery
  closeout;
- Phase C remains host-blocked and deferred.

Parent plan:
`docs/internal/engineering-process/slice-plans/kcs-15-2b2-operator-confirmed-comparison-workflow.md`.

## Requested outcome

Let the operator decide what KCS knowledge to reuse or draft without leaving
the Claude conversation, without reading long comparison evidence in chat, and
without allowing a model to invent the operator's selection.

The surface should reduce avoidable drafting and operator cognitive load. It
must not introduce a second product workflow, local browser application, or
Claude-owned KCS decision.

## Operational baseline

Confirmed:

- the Python workflow already identifies bounded KCS items, supports one item
  or a selected list of up to five, and compares selected items sequentially;
- the Python workflow already accepts exactly `reuse`, `update`, `none_fit`, or
  `need_more_evidence` for one pending reuse comparison;
- the installed Claude Desktop client `1.24012.1` advertises
  `io.modelcontextprotocol/ui` with
  `text/html;profile=mcp-app`;
- the same live client does not advertise MCP elicitation, so a native
  selection popup is not an operationally available contract;
- MCP Apps can render inside supported MCP hosts, call app-only tools, open
  links through the host, and receive `structuredContent` that is not added to
  model context;
- generic Claude chat can still bypass a model-visible starting tool. It
  remains outside the deterministic entrypoint claim.
- generic Claude chat can also use host-provided file create/read actions and
  produce a draft artifact without invoking any KCS tool; an inline App cannot
  enforce a global no-draft invariant while alternative draft-capable host
  tools remain model-controlled.

Provisional:

- one inline MCP App can make both bounded KCS-item selection and sequential
  reuse comparison comfortable;
- expandable UI-only facts remove the need for a local facts file;
- the current Claude host supports the required app lifecycle, server-tool
  calls, link opening, and usable inline sizing in practice.

Unknown:

- the exact rendered layout and host-provided display modes in the installed
  client;
- operator comfort with item density, facts disclosure, candidate cards, and
  sequential decisions;
- whether the current client opens public links in its built-in browser or
  delegates to the system browser;
- whether a future direct host launcher can remove the remaining
  model-controlled first transition and bind the session to a tool boundary
  that excludes alternative draft-capable actions before operator outcome.

Rejected:

- action selection in a standalone or loopback local browser;
- a local web server, new product backend, native GUI framework, or local facts
  file for Phase C;
- treating `native_choice_popup_preferred` as proof that a popup exists;
- copying long facts into model-visible text merely to render them;
- implementing the production UI before a fixture-only host smoke.
- treating successful App rendering as proof that generic chat cannot answer
  or create a file outside the KCS workflow.

## Corrected target UX

The normal conversation remains compact.

1. A model-visible KCS start tool returns only a short safe status plus an MCP
   App view.
2. The inline view lists identified KCS items with a few compact facts.
3. When two to five items exist, the operator may select a bounded subset; the
   backend retains the existing selected refs and processes them sequentially.
4. For the current item, the view shows one to three eligible public article
   cards with titles, public links, bounded excerpts, and expandable accepted
   ticket facts.
5. The operator chooses `reuse`, `update`, `none_fit`, or
   `need_more_evidence`. `reuse` and `update` bind to one displayed article.
6. The app calls an app-only confirmation tool. The model cannot call or alter
   that choice.
7. The view advances to the next selected item or displays the safe terminal
   result.

Long accepted facts and article excerpts use UI-only `structuredContent`.
Compact model-visible `content` may contain only the current state, item
labels, safe public links, and the instruction not to draft manually.

## Ownership

Python continues to own extraction, candidate bounds, pending refs and TTL,
article eligibility, action mapping, authoring continuation, validation, and
failure behavior.

The MCP App owns presentation and direct operator interaction only. Its
server-tool calls reuse existing Python state and accept opaque refs plus
closed-enum selections.

The operator owns selected KCS items and every reuse outcome.

Claude may explain compact model-visible state but does not own item selection,
candidate identity, confirmation, draft continuation, or the app-only tool.

## Portability boundary

The product workflow and Python controller remain host-independent. The UI is
implemented against the official MCP Apps extension rather than Claude-private
APIs. Host capability negotiation selects:

- MCP App view when `io.modelcontextprotocol/ui` is available;
- existing bounded text result otherwise, with no claim of native selection or
  deterministic in-chat operator provenance.

Claude-specific build/install/reload and UI smoke procedures remain adapter
readiness evidence, not core contracts.

## End-to-end enforcement reachability

```text
generic chat prompt
  -> model-controlled routing
     -> KCS start tool (best-effort)
        -> Python comparison gate
        -> MCP App view
        -> operator click
        -> app-only Python confirmation tool
        -> deterministic outcome and optional none_fit authoring
     -> direct answer or host file tool (uncontrolled bypass)
```

Phase C makes selection and confirmation deterministic after the app is
rendered. It does not make the initial tool mandatory and cannot disable
alternative host file actions. A future deterministic in-host design therefore
requires both an operator-controlled launcher and a host/session permission
boundary that excludes draft-capable alternatives before the KCS outcome. The
existing direct controller remains the deterministic no-model entrypoint.

## Fixture-only UX smoke contract

Claim:

The installed Claude client can render a useful in-chat KCS selection and
reuse-comparison prototype whose long evidence stays UI-only and whose
operator actions are delivered through app-only tool calls.

Fixture and provenance:

- synthetic, public-safe, committed-code-independent fixture embedded in a
  separate temporary extension;
- three synthetic KCS items;
- two selectable items and one intentionally excluded item;
- three public Plesk Support article links and bounded synthetic excerpts;
- no ticket refs, customer data, RAG calls, private paths, or reviewer output.

Fixed conditions:

- installed Claude Desktop `1.24012.1`;
- client must advertise `io.modelcontextprotocol/ui`;
- separate extension name `KCS Reuse UX Smoke`;
- one fresh chat after install/reload;
- selected model identity recorded but model wording is not evaluated.

Invariants:

- view renders inside Claude;
- item selection supports a bounded subset;
- comparison is sequential;
- long facts are available without appearing in model-visible tool text;
- public article links are clickable;
- `reuse`/`update` require one displayed article;
- all four outcomes are available;
- submit updates only fixture state;
- no files, drafts, bundles, RAG, Zendesk, or publication behavior.

Success threshold:

- one complete operator walkthrough with no critical interaction blocker;
- this proves UX and MCP Apps feasibility only, not repeated comfort,
  production integration, model routing, or recommendation stability.

Permitted corrections:

- layout, labels, density, expansion behavior, and button placement;
- no production workflow/schema/persistence changes.

Stop condition:

- missing app rendering or server-tool capability;
- unsafe model-visible long evidence;
- action ambiguity;
- requirement for a local web server, credentials, production data, or core
  contract change.

## Acceptance-to-gate mapping for the smoke

| Criterion | Gate |
| --- | --- |
| The extension exposes only fixture-only smoke tools and UI resources. | deterministic package/stdio inspection |
| Long facts are absent from model-visible `content` and present in UI-only `structuredContent`. | deterministic JSON-RPC smoke |
| Item and outcome controls enforce the declared bounds in the prototype. | deterministic fixture-state tests plus operator walkthrough |
| The installed client renders the app and routes one app-only action. | bounded installed-client UX smoke |
| No KCS production source, state, RAG, draft, bundle, or write path is called. | diff/package review and temporary-extension isolation |
| The operator can judge comfort before production design selection. | named operator human-review gate |

## Selected production slice

Confirmed by the operator on 2026-07-23:

- use one in-chat MCP App for bounded item selection and sequential reuse
  comparison;
- keep a short item summary visible and accepted facts collapsed by default;
- show only deterministic Python-owned article metadata and excerpts; the UI
  must not invent coverage claims or recommendations;
- keep public article titles as host-opened links;
- submit item and outcome choices through app-only tools while retaining the
  existing model-visible text flow as a fallback;
- reuse the official MCP Apps lifecycle and interaction shell proven by the
  fixture smoke, but do not copy fixture data or its independent state engine.

Production Delivery may add:

- one static packaged MCP App resource;
- one read-only app-only state tool;
- one app-only closed-action tool;
- MCP Apps resource metadata on existing tools that can reach an operator
  selection or comparison;
- deterministic packaging, protocol, state, action, and UI-boundary tests.

Unchanged contracts:

- extraction, candidate generation, refs, TTL, bounds, article eligibility,
  outcome semantics, authoring, reviewer output, and failure behavior remain
  Python-owned;
- the existing item-selection and reuse-comparison model tools and their
  non-App fallback remain valid;
- no RAG/provider, persistence, publication, Zendesk write, customer reply, or
  KCS-15.2b3 model/retrieval/repeated-use change is authorized.

Provisional presentation details:

- exact labels, fact density, expansion affordance, and candidate-card spacing
  may be corrected after the first installed production smoke;
- such corrections must not change action meaning, evidence bounds, or
  ownership.

## Production acceptance-to-gate mapping

| Criterion | Gate |
| --- | --- |
| All pending KCS items appear before article comparison. | deterministic state-projection test |
| The operator can select one to five existing Python-owned item refs. | deterministic app-action/ref/bounds tests |
| Every selected item receives its own sequential public-article comparison. | existing workflow sequence tests plus app state-transition tests |
| Only reusable public KCS articles appear as candidates. | existing core/provider eligibility tests; UI consumes the validated cards unchanged |
| Accepted facts and excerpts stay out of model-visible app-tool text. | deterministic tool-result boundary test and resource review |
| Operator actions contain only opaque refs and closed enums. | deterministic schema and negative action tests |
| MCP App tools are hidden from the model and existing text fallback remains. | deterministic `tools/list` metadata and descriptor tests |
| The installed production package renders and advances one real sanitized workflow. | named operator installed-client smoke; pending |
| Source, generated UI, and installed package identities agree. | source-hash, MCPB package, installer, and installed-runtime preflight gates |

## Production Delivery checkpoint

2026-07-23 implementation:

- added one self-contained MCP App resource using the official MCP Apps SDK;
- reused only the fixture smoke's proven lifecycle, host-theme, link-opening,
  timeout, and app-to-server call patterns;
- fixture data and the fixture-owned workflow engine were not copied;
- added one read-only app-only state tool and one app-only closed-action tool;
- both tools project or continue the existing in-memory Python workflow;
- existing item extraction, refs, TTL, comparison evidence, outcome semantics,
  authoring, reviewer output, and text fallback remain unchanged;
- tracked UI source and generated HTML are bound by a deterministic SHA-256
  source-identity test;
- focused protocol, state, action, resource, and packaging tests pass.

Behavior drift verdict:

- intentional: Desktop `tools/list` now includes two app-only tools with
  `visibility=["app"]`; relevant model tools reference one MCP App resource;
  `resources/list`/`resources/read` expose that static resource;
- unchanged: model-visible tool names, input/output behavior, comparison
  decisions, fallback text workflow, RAG/provider contracts, persistence,
  publication, Zendesk, and customer-reply boundaries;
- review-only risk: actual host rendering and one production state transition
  remain unproved until a rebuilt package is installed and Claude Desktop is
  reloaded.

Ousterhout closeout:

- deep module: the UI sees one bounded state projection and one closed action;
  Python hides extraction, selection, comparison, authoring, and failure
  complexity;
- information hiding: the browser bundle owns no refs, TTL, candidate
  eligibility, workflow state, or recommendation logic;
- interface: two app-only tools and one static resource are the smallest
  host-interactive boundary that supports both UX stages;
- generality: the surface uses the portable MCP Apps protocol and no
  Claude-private API; Claude-specific install/reload remains readiness work;
- complexity/red flags: the generated self-contained HTML is about 350 KB.
  The build dependency audit reports a moderate Windows `serve-static`
  advisory in a transitive Node server package, but that server code is absent
  from the shipped browser artifact and no HTTP server is introduced. Recheck
  on SDK upgrades; do not claim the dependency tree is vulnerability-free.

Closeout status:

- deterministic Delivery evidence: complete;
- installed production MCPB identity/reload/interaction smoke: pending;
- repeated comfort or stability: deferred to KCS-15.2b3 and not implied by one
  installed smoke.

Validation record:

- focused operator-surface/protocol/package suite: `256 passed`;
- aggregate adapters/core/policy suite: `1601 passed, 1 skipped, 1 failed`;
- the one aggregate failure is the pre-commit
  `test_frozen_contract_paths_have_no_uncommitted_diff` check. It reports three
  frozen files already modified by the broader uncommitted KCS-15.2 branch;
  all seven content/shape freeze snapshots pass, and Phase C adds no field or
  tool to the frozen descriptor/schema snapshot;
- code-review graph policy: `9 passed`;
- Ruff on touched Python: passed;
- source-wrapper MCPB stdio smoke: `ok=true`, `tool_surface_ok=true`,
  `tool_count=9`;
- MCPB build: passed; local package SHA-256
  `78c75acbcf2e1aaebbdaa7a356c7b2c38496dc51ffda6ee142c0407676533918`;
- `git diff --check`: passed.

## UX smoke execution checkpoint

2026-07-23:

- the separate `KCS Reuse UX Smoke` package was built with exactly
  `manifest.json`, `README.md`, and `server/index.js`;
- deterministic stdio verification passed for MCP Apps capability declaration,
  UI resource delivery, app-only action visibility, bounded item selection,
  candidate-bound `reuse`/`update`, sequential progression, and terminal
  outcomes;
- model-visible tool text excluded the long fixture facts while
  `structuredContent` retained them for the UI;
- a dry-run install verified exact file copies and registry identity;
- the temporary package was installed beside the production KCS Authoring
  extension with package SHA-256
  `71ecaf3840311f46c2b42348c694d9524ca738f5d803e618d5fa419d5a4beca7`;
- installed-client reload, rendering, link-opening, app-only action routing,
  and operator comfort remain pending. Production Delivery remains locked.

First installed-client attempt:

- Claude discovered both registry entries and the remote `can_install` check
  accepted the smoke package;
- Claude launched only the production KCS Authoring server, and the fresh chat
  correctly reported that `kcs_preview_reuse_ux` was unavailable;
- the missing link was the separate per-extension activation state under
  `Claude Extensions Settings`; registry presence and `can_install: true` did
  not imply `isEnabled: true`;
- the fixture installer now creates the explicit activation file, its dry run
  passed, and the installed smoke has `isEnabled: true`;
- a second client reload and exact tool/rendering probe remain required. The
  failed first attempt is packaging/readiness evidence, not UX evidence.

Second installed-client attempt:

- after activation, Claude discovered and called
  `KCS Reuse UX Smoke:kcs_preview_reuse_ux`;
- the host fetched the UI resource and rendered its static frame, while the
  server returned the tool result without an MCP error;
- the view remained at `Connecting to fixture smoke...`; no item controls or
  app-only action appeared;
- therefore extension discovery, activation, tool invocation, server response,
  and UI-resource rendering are confirmed, but the interactive MCP App
  lifecycle and target UX remain unproved;
- the temporary view used a hand-written `postMessage` lifecycle. It is being
  replaced by the official `@modelcontextprotocol/ext-apps` `App` client, with
  handlers registered before `connect()` and bounded errors for handshake and
  initial-result timeouts;
- this correction changes only the isolated fixture smoke. Production KCS
  Authoring remains untouched and Production Delivery remains locked.

Process learning:

- a separate MCPB was disproportionately heavy for early layout and
  decision-flow evaluation because it added packaging, registry, activation,
  restart, and host-lifecycle work;
- future UX evidence should begin with an install-free static or clickable
  fixture, then use one installed-host smoke only for the residual claims that
  genuinely depend on Claude rendering, navigation, lifecycle, or app-only
  tool routing;
- the current installed smoke remains useful for those residual host claims,
  but it is not the default prototype pattern.

Corrected temporary package:

- fixture package `0.0.2` uses the official
  `@modelcontextprotocol/ext-apps` client bundled into one self-contained HTML
  resource;
- deterministic fixture verification passed after the correction;
- handshake and initial-result waits are bounded and show an explicit safe
  error instead of an indefinite spinner;
- package SHA-256 is
  `bd1aed0e447351a6467bdeb6eeda405cadd3073336003dbdf8f105814ddff1ba`;
- the installed registry records `0.0.2` with the same hash and retains
  `isEnabled: true`;
- a fresh client reload and operator walkthrough remain required. No live UX
  success is claimed yet.

Third installed-client checkpoint:

- package `0.0.2` completed the official MCP Apps handshake and rendered a
  bounded error instead of hanging;
- Claude delivered an initial tool-result notification without usable
  `structuredContent`, so the item-selection UI still did not render;
- package `0.0.3` now performs one read-only app-to-server preview call after
  connection when the initial notification has no state. This is the same host
  proxy path required by later app-only selection actions;
- deterministic verification passed and the installed registry records
  package SHA-256
  `df54d404b495731911f5ffdc2191985550ace055840934e126ea72548e7ee6c4`;
- one fresh client reload is the final permitted correction for this temporary
  MCPB. If the direct call still does not return usable fixture state, stop the
  installed-host prototype and return to lighter Design evidence rather than
  expanding the test extension.

## First production installed-client routing trial

2026-07-23, Claude Desktop `1.24012.1`, Sonnet 5 Medium:

- source, built MCPB, installed extension, enabled connector, client reload,
  installed-wrapper tool surface, live RAG readiness, and exact article
  capability were confirmed before the trial;
- the operator submitted one synthetic sanitized prompt containing two
  separately searchable KCS items;
- Claude returned one manually composed article containing both issues;
- the active `KCS Authoring` log recorded no tool call after the prompt;
- therefore the operator surface was never opened and no Python item boundary,
  reuse comparison, or operator-selection gate was reached.

Verdict:

- installed package and dependency readiness: confirmed;
- natural-language model routing into the KCS workflow: failed once;
- production MCP App rendering and interaction: still unproved;
- this failure does not indicate a UI or Python workflow defect because neither
  executed.

Permitted correction:

- strengthen the existing initialize, tool-description, and package discovery
  text so every inline KCS/Plesk KB drafting request names
  `kcs_draft_article` as the mandatory first tool, requires the complete
  sanitized text for multi-item boundary detection, and forbids composing the
  article directly in chat;
- preserve all tool names, schemas, Python behavior, UI behavior, data
  boundaries, and operator-owned decisions;
- rebuild, reinstall, reload, and repeat the same single synthetic Sonnet 5
  trial.

Interpretation limit:

- a corrected successful run would prove one feasible routing instance, not
  deterministic enforcement or stability;
- generic Claude chat remains model-mediated. If the same bounded retry still
  bypasses the tool, stop prompt/descriptor tuning and either accept a
  best-effort entrypoint explicitly or design a user/app-controlled direct
  launcher.

Second production installed-client checkpoint:

- with only production `KCS Authoring` enabled, Sonnet 5 routed the same
  synthetic prompt to `kcs_draft_article`;
- Python identified two separate KCS items and returned the existing
  split-required fallback;
- Claude Desktop fetched the MCP App resource, but the app's first read-only
  state call failed with JSON-RPC `-32602 Invalid tool arguments`;
- transport evidence showed the model-owned tool call succeeded before the
  app-owned call failed, so routing is feasible once and the remaining blocker
  is App-to-server protocol compatibility;
- root cause: the host proxy may attach MCP request `_meta` to `tools/call`,
  while the local transport allowed only `name` and `arguments`;
- bounded correction: accept object-valued request `_meta`, ignore it at the
  adapter boundary, reject non-object metadata, and prove it is not forwarded
  or reflected. Tool schemas, app actions, workflow state, and data boundaries
  remain unchanged.

Third production installed-client checkpoint:

- package `0.2.2` accepted the App proxy call and all observed tool calls
  completed without JSON-RPC errors;
- the comparison candidates and coverage assessment were operationally useful;
- however Sonnet 5 called `kcs_draft_article` with both item refs about
  1.5 seconds after the app state became available, before an operator click,
  then continued to the first reuse comparison;
- therefore the model bypassed the operator-owned item-selection gate even
  though the MCP App path was available.

Required correction:

- when the initialized client advertises
  `io.modelcontextprotocol/ui` with the MCP App HTML profile, reject
  model-visible `kcs_draft_article` calls containing item-selection refs and
  retain the pending Python state for the app-only action;
- the app-only `kcs_submit_operator_surface_action` continues through the
  existing Python controller and remains the only item-selection authority on
  that host;
- when MCP Apps are not advertised, preserve the existing model-mediated text
  fallback without claiming deterministic operator provenance;
- do not change item refs, selection semantics, comparison behavior, candidate
  evidence, authoring, persistence, or publication boundaries.

Fourth production installed-client checkpoint:

- package `0.2.3` retained the App-only item-selection authority and rejected
  model-supplied item selections on App-capable hosts;
- in the next Sonnet 5 Medium trial, Claude did not route the request through
  the visible KCS workflow. It classified the sanitized ticket as an injection
  attempt, composed one combined article directly, and created a Markdown file;
- no model `kcs_draft_article` route or operator-owned item-selection gate was
  visible in the trial. App lifecycle/state traffic does not establish that
  the model entered the authoring workflow;
- the resulting article is a smoke artifact, not an accepted KCS product
  output.

Final generic-chat verdict:

- downstream Python and App gates can protect operator decisions only after
  the host enters the KCS workflow;
- prompt, initialize-instruction, and tool-description changes cannot
  deterministically prevent the host model from bypassing that entrypoint;
- the recorded retry stop condition is met. Do not continue descriptor or
  prompt tuning for deterministic enforcement;
- keep the `0.2.3` downstream gate because it remains useful after a valid
  entry, but do not claim that generic chat is the supported enforcing
  entrypoint.

## Direct-launch capability discovery closeout

Confirmed for Claude Desktop `1.24012.1`:

- the live initialize contract advertises MCP App HTML rendering but not MCP
  elicitation or another direct-launch capability;
- connector toggles and tool-access modes control whether tools are available
  to Claude; they do not directly invoke a selected tool;
- MCP prompts, plugin skills/commands, and chat text produce model input and
  therefore remain model-mediated;
- MCP Apps support direct operator actions only after an App has been rendered
  from a tool result. They cannot own the earlier decision to invoke that first
  tool;
- Anthropic's interactive-connector guidance says the interface appears when
  Claude determines that it is relevant after a conversation request;
- the MCP tools specification defines tools as model-controlled and leaves any
  direct user invocation UI to the host. The installed host exposes no such
  documented or negotiated UI.

Sources checked on 2026-07-23:

- `https://support.claude.com/en/articles/13454812-use-interactive-connectors-in-claude`
- `https://support.claude.com/en/articles/13730515-manage-claude-s-tool-access`
- `https://modelcontextprotocol.io/specification/2025-06-18/server/tools`

Design verdict:

- a deterministic in-chat entrypoint is infeasible with the currently exposed
  host contract;
- Phase C is deferred until the host adds a user-controlled tool/App launcher
  or an equivalent capability that can be operationally proved;
- `kcs-controlled-draft <ticket_ref>` remains the supported deterministic
  entrypoint because it invokes the comparison-only Python gate directly;
- generic chat may remain available only as an explicitly best-effort path and
  is not accepted for the no-draft-before-comparison invariant;
- do not add a standalone browser, native GUI framework, automation around
  Claude's UI, or further prompt/descriptor tuning;
- do not discard the downstream App/Python protections. They remain valid
  integration code for a future host-controlled entrypoint, but they do not
  close Phase C today.

## Approval ledger

```text
Requested outcome: agreed
Standalone/loopback browser action UI: rejected by operator
Corrected in-chat outcome: agreed
Native popup: provisional preference, operationally unavailable in current client
Fixture-only MCP App UX smoke: selected and Delivery authorized by operator
Fixture-only MCP App UX: accepted by operator
Production MCP App design: selected
Production bounded operator-surface Delivery: authorized by operator
Direct operator-controlled Claude launcher: unavailable in current host contract
Phase C final status: host-blocked and deferred
KCS-15.2b3: locked
```

## Stop conditions

Return to Design if the smoke or later implementation requires:

- model-owned item/outcome/candidate selection;
- raw/private ticket input or internal article content;
- credentials, non-local transport, persistence, or a hosted service;
- a standalone browser, native GUI framework, or duplicated workflow engine;
- changes to core/RAG/provider contracts or comparison evidence bounds;
- automatic update, publication, Zendesk write, or customer reply;
- treating one smoke as production UX or stability evidence.
