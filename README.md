# KCS Authoring Workflow

Local workflow for runtime-independent KCS Authoring.

Status: the local reviewer-only workflow through KCS-13 and KCS-14 engineering
hardening are implemented. KCS-14.5 semantic stabilization is closed without
accepting the strict multi-issue stability target: the simple-ticket route is
repeatable, but the reviewed noisy real-ticket route remained dependent on a
fresh model proposal and did not produce stable candidate/disposition results.
The retained route is model-proposed, Python-validated, operator-selected, and
reviewer-only. Further semantic schema expansion is frozen pending a design
with a new source of issue-scope authority. Enterprise/PAUX rollout remains
postponed. Some package IDs, environment variables, paths, and historical docs
still use `kcs-authoring-mvp` for compatibility. The original safety boundary
remains active: no Zendesk writes, no Help Center publication, no auto-publish,
compact default MCP output, and Python-owned validation, decision, rendering,
and bundle writing.

The atomic-relation and flat-claim schema experiments were rejected by their
installed viability gates and are not active runtime paths. The KCS-14.5
decision log and aggregate attempt review record the evidence and reopening
conditions so later work does not repeat those approaches.

Python baseline: 3.11. CI is deferred until the local command set is stable.

## Overview

The KCS Authoring Workflow helps support engineers prepare reviewer-ready KCS
output from approved or sanitized ticket evidence. It recommends a KCS action,
records the evidence basis, reports blockers, and prepares reviewer-only local
bundles without publishing or writing to Zendesk or Help Center.

The workflow focuses on KCS work after or near ticket resolution: deciding
whether knowledge should be reused, updated, created, flagged, split, skipped,
or blocked for review. The primary clean-ticket path is source-independent:
Zendesk cleanup, a web cleanup form, Claude Desktop sanitized attachment
registration, or another approved cleanup source should all produce the same
clean-ticket input shape before Python runs the KCS pipeline.

## Core Principle

```text
Code decides.
LLM drafts.
Validators block.
```

The core owns workflow decisions, validation, blockers, and readiness state.
Claude or another LLM may draft or review text only through bounded handoff
after the relevant contracts and gates exist.

## Demo Showcase

The primary portfolio/demo artifact is
[`showcase/demo-3/`](showcase/demo-3/). It demonstrates the current controlled
workflow on a noisy multi-candidate clean-ticket case:

- one candidate is flagged for an existing public KB article instead of
  creating a duplicate;
- one candidate produces a reviewer-only draft artifact;
- one candidate is blocked because the approved evidence does not contain
  operator-confirmed resolution steps.

Start with [`showcase/demo-3/README.md`](showcase/demo-3/README.md), then open:

- [`PROJECT_WALKTHROUGH.md`](showcase/demo-3/PROJECT_WALKTHROUGH.md) for the
  human-readable project walkthrough;
- [`reviewer_packet.md`](showcase/demo-3/reviewer_packet.md) and
  [`reviewer_packet.json`](showcase/demo-3/reviewer_packet.json) for the main
  reviewer packet;
- [`preview.html`](showcase/demo-3/preview.html) for the sanitized reviewer-only
  preview;
- [`kcs-authoring-architecture-diagram.pdf`](showcase/demo-3/kcs-authoring-architecture-diagram.pdf)
  for the architecture diagram and caption.

The demo artifacts are reviewer-only and public-safe. They do not imply a
Zendesk write, Help Center publication, auto-publish, live RAG/search, or
Claude-owned KCS decision.

## Current Scope

The implemented local workflow and engineering baseline follow the
KCS-0..KCS-14.5 roadmap tracked in
`docs/internal/kcs-authoring-mvp-jira-tracking.md` and
`docs/internal/kcs-desktop-authoring-refactor-plan.md`.

The KCS-13 semantic-review fallback has been consolidated through KCS-14.5.
The Desktop route exposes one observation-based issue-proposal contract,
deterministic Python validation and audit, native operator selection, and
reviewer-only drafting. The internal legacy candidate parser remains only for
the approved-summary provider and explicit LF-1 comparison tooling; it is not a
second Claude-visible workflow.

KCS-14 engineering/process/codebase hardening is closed. It preserved the
implemented runtime workflow while reducing ambiguity for future AI-assisted
engineering. The post-closeout test-suite maintainability batches changed only
the Desktop characterization safety net and its tracked closeout records; they
did not change source, packaging, tool schemas, or runtime behavior.

KCS-14.5 did not establish stable semantic ownership for noisy multi-issue
tickets. Reopening that problem requires a separately reviewed behavior-change
design with a new authority source, such as upstream structured issue scope or
operator-provided scope at workflow entry. It may not weaken evidence gates or
add another prompt-correction workflow. The retained M4 gate is scoped to that
semantic/control-surface workstream. Independently approved `KCS-15`
style/markup slices may proceed when their diff does not touch the frozen
incident surfaces. Managed deployment, production rollout, and additional
integrations remain separately deferred.

Resolution steps must remain evidence-grounded. If the ticket gives the
resolution outcome or a high-level resolution description but does not include
the exact executable procedure needed to apply and verify it, the workflow
should block with `approved_summary_resolution_steps_incomplete` instead of
inventing implementation details. The operator may add operator-confirmed
resolution detail and rerun the same pipeline.

Batch results report retryable blockers without asking the operator to choose
one or confirm leaving already blocked candidates blocked. A retry resumes only
after the operator independently supplies exact confirmed resolution or
workaround steps.

Implemented code slices:

```text
KCS-1: core packet contracts and safe fixtures
KCS-2: safety and evidence readiness gates for sanitized normalized evidence
KCS-3: deterministic KCS action decision core
KCS-4: reviewer packet renderer and Zendesk HTML output
KCS-5: validation report and ready-for-reviewer loop state
KCS-6: CLI entrypoint for local verification
KCS-7: evidence package builder for approved sanitized structured input
KCS-8: Zendesk read-only ingest boundary for local cleanup handoff
KCS-9a: semantic KCS item identification contract
KCS-9b: bounded Claude/provider handoff contract
KCS-9c: reviewer-only draft generation contract and artifact writer
KCS-10: local reviewer bundle writer for audit/debug artifacts
KCS-11: live-capable Claude/provider adapter for bounded smoke tests
KCS-12: Claude Desktop MCP validator/control adapter and MCPB package
KCS-13: controlled semantic-review fallback for complex/noisy clean tickets
KCS-14: engineering process and codebase design hardening
```

KCS-2 is implemented as local `safety.py` and `validation.py` gates. It returns
value-free blockers/warnings for sanitized evidence readiness and does not make
KCS action decisions, render articles, read Zendesk, call search, or hand off
to Claude.

KCS-3 is implemented as local `decision.py` logic. It consumes accepted
evidence plus structured reuse/search results and returns a
`KcsActionDecisionPacket` without reading Zendesk, calling search, rendering
articles, or handing off to Claude. Multi-issue evidence returns top-level
`split_required` with preliminary per-candidate decision items instead of a
combined article draft. KCS-3 may expose future-safe reviewer-only override
metadata, but it does not generate override drafts.
For same-identity article changes, KCS-3 distinguishes public articles
(`flag_existing`) from internal/not-public articles (`update_existing`) but
does not generate updated HTML content.
Explicit GUI/CLI delivery variants are treated as the same reusable issue when
the structured KCS identity resolves to the same cause-resolution or
question-answer pair.
Future local review bundle slices must persist any requested override status in
packet/artifact metadata while preserving the original recommendation and
`auto_publish_allowed=false`.

KCS-4 is implemented as local `renderer.py` logic. It turns accepted evidence
and KCS-3 decisions into canonical `KcsReviewerPacket` output and generates
Zendesk source HTML only for create/update candidates or reviewer-required
`flag_existing` artifacts. It does not write local review bundles, call Claude,
read or write Zendesk, publish Help Center content, or generate customer
replies.

KCS-5 is implemented as local `readiness.py` logic. It combines evidence,
decision, and renderer outcomes into a standalone `KcsValidationReportPacket`
with value-safe blockers/warnings, required next step, and
`ready_for_reviewer` loop state. It does not write local bundles, call Claude,
read or write Zendesk, publish Help Center content, or generate customer
replies.

KCS-6 is implemented as local `cli.py` verification logic for deterministic
synthetic or approved sanitized packet fixtures. It does not require Zendesk,
Claude, MCP, search-adapter, or publish credentials.

KCS-7 is implemented as local `evidence_builder.py` and `sanitizer.py` logic.
It accepts only approved/sanitized structured evidence exports and returns
`NormalizedTicketEvidencePacket` output for downstream KCS gates. It does not
read raw tickets, perform semantic extraction, call Claude, use live Zendesk,
or change decision, renderer, readiness, or CLI behavior.

KCS-8 is implemented as local `zendesk_ingest.py` logic. It accepts an injected
read-only `ZendeskSourceClient` for approved allowlisted ticket refs and returns
a safe cleanup handoff manifest for raw/pre-cleanup Zendesk snapshots. It does
not convert raw Zendesk ticket bodies into evidence, call KCS-7 on raw payloads,
download attachment bodies, list/search/bulk export tickets, call Claude, write
Zendesk, publish Help Center content, or generate customer replies. Production
deployment is expected to use an approved internal service endpoint behind the
source-client protocol; local/dev may use an MCP-backed source client, but no
MCP path, service endpoint, Zendesk token, URL, or secret is hardcoded in KCS
core.

KCS-9a is implemented as local `semantic_extraction.py` contract and validation
logic. It accepts bounded semantic item-identification output from a future
approved extractor/provider, validates it as untrusted input, and normalizes it
into the existing KCS-7 approved evidence export path. It may classify item
boundaries, product relation, supportability hints, article type hints, and
visibility hints. It does not return KCS action recommendations, call Claude,
perform online EOL lookup, draft text, render reviewer packets, write Zendesk,
or publish Help Center content.

KCS-9b is implemented as local `claude_handoff.py` contract and validation
logic. It builds compact safe reviewer-assist handoff requests from existing
deterministic decision/readiness outputs and validates provider responses as
untrusted data. It supports fake-provider tests only, accepts safe logical
artifact refs instead of raw local paths, preserves original deterministic
metadata, and keeps `auto_publish_allowed=false` and
`public_output_approved=false`. It does not generate drafts, include full
reviewer packet bodies or full Zendesk HTML, write files, call live Claude/API,
implement MCP/service transport, or change KCS decisions.

KCS-9c is implemented as local `claude_draft.py` contract and validation
logic. It consumes validated KCS-9b-style bounded handoff context for eligible
article-output paths, validates untrusted provider draft proposals, and writes
reviewer-only draft artifacts through Python-owned code. Draft artifacts keep
`auto_publish_allowed=false` and `public_output_approved=false`; provider
output cannot decide KCS actions, write files directly, publish content,
generate customer replies, or replace KCS-4 deterministic renderer output.

KCS-10 is implemented as local `reviewer_bundle.py` writing logic. It collects
existing validated KCS packets and optional KCS-9b/KCS-9c artifacts into a
fixed local reviewer bundle with a safe manifest/index. The bundle is a
file-based audit/debug/regression artifact, not the production chat review UI.
Production may render a safe chat summary from the same validated packet data.
KCS-10 does not write Zendesk, publish Help Center content, generate customer
replies, call live Claude/provider APIs, or change KCS decision, renderer, or
readiness behavior.

KCS-11 is implemented as adapter-layer `kcs_adapters.claude_provider`
smoke logic outside `kcs_core`. It validates safe provider configuration,
builds value-safe preflight and attempt packets, and submits validated
KCS-9b/KCS-9c request packets through an injected fake or direct HTTP provider
client. Runtime endpoint and credential material is kept out of serializable
packets and smoke results. Provider output remains untrusted and is accepted
only after existing KCS-9b/KCS-9c validators pass. KCS-11 does not write files,
implement MCP or internal service transports, change KCS decisions, publish
content, write Zendesk, or generate customer replies.

KCS-12 is implemented as adapter-layer `kcs_adapters.mcp_desktop` stdio MCP
logic outside `kcs_core`, plus a reproducible Claude Desktop MCPB package
source under `packaging/claude-desktop/`. The default Claude Desktop surface
exposes `kcs_draft_ticket` for `/draft <ticket_ref>`,
`kcs_register_clean_ticket` for sanitized attachment/long-paste registration,
`kcs_draft_article` for short inline text or operator selection continuation,
and bounded semantic-review prepare/submit tools. Python owns semantic
proposal acceptance and audit, workflow state, validation, KCS decisions, rendering, local
reviewer bundle writing, and output safety. Default successful results return
compact status plus local bundle refs and hashes; full
`reviewer_only_html` is returned only in explicit debug/smoke compatibility
mode. KCS-12 does not read raw tickets, call Claude/provider APIs, expose MCP
resources/prompts, change KCS decisions, publish content, write Zendesk, or
generate customer replies.

KCS-13 is implemented as controlled semantic-review fallback behavior for
complex/noisy approved clean tickets. Python first attempts deterministic item
identification. If the ticket is likely KCS-relevant but low-confidence,
Python returns `semantic_review_required` with a bounded next-tool contract.
Claude Desktop may inspect only bounded sanitized excerpts and propose
source-grounded observations and issue boundaries in
`semantic_issue_proposal_v1`. Python validates and projects that untrusted
proposal, preserves unassigned evidence in the audit ledger, produces native
candidate selection for multiple draftable issues, decides split/single/block,
renders reviewer-only output, and writes any bundle. The bounded
`candidate_semantic_extraction_v1` parser remains a compatibility island for
the approved-summary provider and comparison tooling, not a normal alternative
Desktop route. KCS-13 does not let Claude draft freehand articles, decide KCS
actions, bypass validation, publish content, write Zendesk, or expose raw
tickets.

Local smoke accounting is implemented as adapter-layer
`kcs_adapters.smoke_accounting` and the `kcs-smoke-account` console script. It
reads an operator-provided Claude Desktop/MCP transcript or log file and returns
a value-safe JSON estimate of observed transcript size, approximate token
count, estimated Sonnet-style cost proxy, tool-call count, failure markers, and
manual-fallback markers. It does not provide exact provider billing usage,
read raw tickets, call providers, write artifacts, or log transcript content.
Exact billing requires provider API usage fields from a direct API transport.

Longer-term managed deployment may replace the local MCPB stdio wrapper with
an intranet remote MCP service. In that model Claude Desktop would connect to
an approved internal MCP endpoint through a custom remote connector URL, while
auth, ACLs, audit, health checks, and deployment packaging live outside the
deterministic KCS core. That is a future service slice, not the KCS-12 local
Desktop extension.

KCS-1 through KCS-7 do not require live Zendesk access, Zendesk tokens, Claude
connector setup, or `kcs-search-mcp` access. KCS-8 introduces the read-only
Zendesk source boundary only. KCS-9a introduces a provider protocol and local
validation/normalization boundary only. KCS-9b introduces the bounded
reviewer-assist handoff contract only. KCS-9c introduces reviewer-only draft
contracts and local artifact writing only. KCS-10 introduces local reviewer
bundle writing only. KCS-11 introduces a live-capable provider adapter package
and bounded smoke layer only. KCS-12 introduces the Claude Desktop MCP
validator/control surface and installable local MCPB package only. KCS-13
introduces the controlled semantic-review fallback only. Real-ticket smoke,
production transport rollout, remote MCP/internal service implementation,
broad adapter/client integration, and KCS-15 style/markup parity are frozen
deferred work unless a future approved slice reopens development.

## Non-goals

- No Zendesk writes.
- No Help Center publication.
- No customer reply generation.
- No raw ticket processing inside the KCS core.
- No Claude-owned KCS decision logic.
- No auto-publish.

## Repository Structure

Current repository structure:

```text
kcs-authoring-mvp/
|-- README.md
|-- CONTRIBUTING.md
|-- .github/
|   `-- pull_request_template.md
|-- docs/
|   `-- internal/
|       |-- kcs-authoring-mvp-goal-and-success-criteria.md
|       |-- kcs-authoring-mvp-data-handling-baseline.md
|       |-- kcs-core-pipeline-architecture-and-contracts.md
|       |-- kcs-core-pipeline-technical-design.md
|       |-- kcs-authoring-mvp-feature-engineering.md
|       `-- kcs-authoring-mvp-jira-tracking.md
|-- src/
|   |-- kcs_adapters/
|   `-- kcs_core/
`-- tests/
    |-- kcs_adapters/
    `-- kcs_core/
```

The Python packages separate runtime-independent core from runtime adapters:

```text
src/kcs_core/          # Runtime-independent Python core
src/kcs_adapters/      # Runtime adapter boundaries and smoke clients
tests/kcs_core/        # Contract, fixture, gate, and decision tests
tests/kcs_adapters/    # Adapter-boundary tests
```

Machine-specific notes, ignore rules, and runtime artifacts must stay outside
the repository.

## Getting Started

### Prerequisites

- Python 3.11
- Git
- Access to `github.com/atsmokalyuk/kcs-authoring-workflow`
- Access to historical PAUX/Jira context only when working on migrated
  enterprise-tracking documents

### Setup

Create a Python 3.11 environment before installing the package. Do not use a
system or Conda `python` unless it resolves to Python 3.11.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e '.[dev]'
```

If Python 3.11 is managed through `uv`, the equivalent local setup is:

```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e '.[dev]'
```

### Running Tests

After installing the dev extra in a Python 3.11 environment:

```bash
python -m pytest tests/kcs_core -q
```

One-shot check without activating a virtual environment:

```bash
uv run --python 3.11 --extra dev python -m pytest tests/kcs_core -q
```

### Running the Tool

KCS-6 adds a local verification CLI for synthetic or approved sanitized packet
fixtures. It does not require Zendesk, Claude, MCP, search-adapter, or publish
credentials.

```bash
python -m kcs_core.cli validate-evidence \
  --input tests/kcs_core/cli_fixtures/003_create_candidate/evidence_packet.json \
  --json

python -m kcs_core.cli decide \
  --input tests/kcs_core/cli_fixtures/003_create_candidate/evidence_packet.json \
  --reuse-results tests/kcs_core/cli_fixtures/003_create_candidate/reuse_results.json \
  --json

python -m kcs_core.cli run \
  --input tests/kcs_core/cli_fixtures/003_create_candidate/evidence_packet.json \
  --reuse-results tests/kcs_core/cli_fixtures/003_create_candidate/reuse_results.json \
  --json
```

The CLI prints deterministic JSON and keeps `auto_publish_allowed=false`.

## Data Handling

Follow `docs/internal/kcs-authoring-mvp-data-handling-baseline.md`.

By default:

- use synthetic or approved sanitized fixtures;
- do not commit raw Zendesk JSON, full comments, customer identifiers,
  credentials, internal article chunks, vector values, raw query logs, or
  runtime artifacts;
- run safety/evidence gates before decision, drafting, rendering, or handoff;
- keep `auto_publish_allowed=false` in all local workflow outputs.

## Source Documents

Project source-of-truth documents live under `docs/internal/`:

- `docs/internal/kcs-authoring-mvp-goal-and-success-criteria.md`
- `docs/internal/kcs-authoring-mvp-data-handling-baseline.md`
- `docs/internal/kcs-core-pipeline-architecture-and-contracts.md`
- `docs/internal/kcs-core-pipeline-technical-design.md`
- `docs/internal/kcs-authoring-mvp-feature-engineering.md`
- `docs/internal/kcs-authoring-mvp-jira-tracking.md`

## Development

See `CONTRIBUTING.md` for branch naming, commit message format, PR process,
data/security rules, and validation expectations.

### Claude Desktop MCPB

Build the local Claude Desktop extension package:

```bash
python scripts/build_kcs_mcpb.py
```

The generated package is written to:

```text
dist/kcs-authoring-mvp-validator-control.mcpb
```

Install this MCPB in Claude Desktop, enable the extension, and start a new
chat. The package embeds the local Python workflow source and starts
`kcs-desktop-mcp` through an autodetected local runtime (`uv` first, then
`python3.11` / `python3` fallback) without requiring a configured repository
path, Claude CLI/Code, an API key, or a semantic-provider setting. It exposes
compact operator tools for clean-ticket registration and article drafting.
Successful primary article drafts may write reviewer-only bundle files under
`local-data/reviewer-bundles/`; the tool still does not publish content or
write Zendesk.

For local development after MCPB or adapter fixes, rebuild and replace the
installed Claude Desktop extension in one step:

```bash
python scripts/install_kcs_mcpb.py
```

The installer updates both the unpacked extension files under Claude
Extensions and Claude Desktop's `extensions-installations.json` registry cache.
This matters because Claude reads tool descriptions from that cache; if it is
stale, Desktop can keep showing the old wide `item` / `item_candidates` schema
even when the unpacked MCPB files are current. After reinstalling, restart
Claude Desktop or reload the extension before running the next UI smoke.

Run the deterministic stdio smoke against the installed MCPB wrapper before
opening Claude Desktop:

```bash
uv run python scripts/smoke_kcs_mcpb_stdio.py
```

This smoke launches the same Node wrapper used by Claude Desktop with the
fixture-only semantic provider explicitly enabled. It verifies the visible thin
`kcs_draft_article` tool surface, Claude Desktop registry cache alignment when
using the installed wrapper, controlled no-candidate, invalid-selection, and
invalid mixed-call statuses, plus fixture labeled-summary, narrative-summary,
raw-ticket, and live raw-ticket-shaped draft paths that write local reviewer
bundles and return debug-only `reviewer_only_html`. It also runs a stateful
split -> selected-draft flow in one MCP process using
`operator_choice_request.options[*].submit_arguments` and verifies that the
split result includes deterministic operator-facing fallback text for cases
where Claude Desktop does not render a native choice popup.
For the installed wrapper, expect `registry_cache_checked=true` and
`registry_cache_ok=true`. It does not validate Claude Desktop model rendering,
but it verifies the server-side choice contract, cache alignment, and bundle
artifacts without manual UI work.

The Desktop authoring refactor target and delivery slices are tracked in
`docs/internal/kcs-desktop-authoring-refactor-plan.md`.

After restarting Claude Desktop, verify that the live Desktop log reflects the
same thin tool surface:

```bash
uv run python scripts/check_claude_kcs_desktop_log.py
```

Pass `--since <UTC ISO timestamp>` when checking a specific restart window.
The check is value-safe: it reports only booleans, the latest matching
`tools/list` timestamp, a compact client capability summary, and a log
filename. If `client_capabilities.elicitation_declared=false`, Claude Desktop
has not advertised MCP-native elicitation for that session, so split selection
relies on the returned `operator_choice_request` and deterministic fallback
text.

Before running an end-to-end Claude Desktop UI prompt smoke, check whether
macOS is allowing Codex.app to drive the UI:

```bash
uv run python scripts/smoke_claude_desktop_ui_prompt.py --check-accessibility
```

If that preflight passes, a GUI automation smoke can be attempted with:

```bash
uv run python scripts/smoke_claude_desktop_ui_prompt.py --send --prompt-kind single
```

This UI smoke sends a synthetic sanitized article prompt and then verifies the
fresh Claude MCP log for a `kcs_draft_article` call and result. It is separate
from the deterministic stdio smoke because it depends on macOS GUI automation
permissions. If it returns
`send_error_code=codex_accessibility_permission_required`, macOS is blocking
Codex.app from controlling the computer through Accessibility; grant that
permission in System Settings before using the GUI smoke. The script fails
fast for this state and writes a diagnostic screenshot path instead of hanging
or retrying blindly.

The GUI-send path is best-effort because Claude Desktop rate limits and macOS
focus behavior are outside the MCP server contract. For the preferred manual UI
smoke, print a synthetic prompt plus the matching follow-up verifier command:

```bash
uv run python scripts/smoke_claude_desktop_ui_prompt.py \
  --print-manual-prompt \
  --prompt-kind raw-ticket \
  --copy-manual-prompt
```

Paste and send the clipboard text in Claude Desktop, or send the raw text
written to the returned `manual_prompt_path`, then run the returned
`follow_up_command`. The verifier checks the fresh MCP log window without
driving the UI. It is equivalent to:

```bash
uv run python scripts/smoke_claude_desktop_ui_prompt.py \
  --since 2026-06-18T23:45:00Z \
  --assume-sent \
  --prompt-kind raw-ticket
```

Use `--prompt-kind raw-ticket` for the primary Claude Desktop MVP smoke because
it exercises a pasted approved sanitized ticket transcript rather than a neat
field-labeled packet. In current local workflow testing, prefer the
`ticket_ref` path for production-like long tickets because it avoids pushing
large transcripts through chat. Use `--prompt-kind single` for a strict labeled
one-item smoke, `--prompt-kind split` for a split-required manual smoke window,
or `--prompt-kind narrative` to cover approved summaries shaped as `Summary` /
`Investigation` / `Resolution` instead of strict field labels.

### Claude/Cowork Plugin

Build the local Claude/Cowork plugin package:

```bash
python scripts/build_kcs_cowork_plugin.py
```

The generated package is written to:

```text
dist/kcs-authoring.plugin
```

This plugin adds a `kcs-authoring-control` skill and references the local
`kcs-desktop-mcp` server through `.mcp.json`. It is the preferred local
chat/Cowork surface when Claude Desktop Extensions are installed but their MCP
tools are not loaded into the active chat.

## Ownership

- Maintainer / implementation lead: Alex Tsmokalyuk
- Historical parent Jira item: PAUX-7083
- Current hardening umbrella: PAUX-7103, pending/subject to external tracker
  confirmation
- Last completed runtime experiment: KCS-14.5 Semantic Stabilization and
  Contract Consolidation (strict multi-issue stability target not accepted)
- Last completed engineering slice: KCS-14 Engineering and Codebase Design
  Hardening, including the post-closeout characterization-suite
  maintainability pass
- Active runtime hardening slice: KCS-15 KCS Style and Markup Parity
- Last completed KCS-15 slice: KCS-15.1 `PLESK_INFO` trigger parity
- Current implementation subtask: RAG-1 loopback local-public search adapter;
  Desktop integration, article identity, and semantic expansion remain frozen

Update this section when the PM owner, reviewer, Slack channel, or GitHub
CODEOWNERS are finalized.

## Visibility

Private local product repository. Do not commit or share raw tickets, private
customer identifiers, credentials, logs with ticket-derived text, generated
runtime artifacts, reviewer bundles, or other sensitive support material.
