# KCS Authoring MVP

Internal WebPros PAUX prototype for a runtime-independent KCS Authoring core.

Status: early implementation. Python baseline: 3.11. CI is deferred until the
local command set is stable.

## Overview

The KCS Authoring MVP helps support engineers prepare reviewer-ready KCS output
from approved or sanitized ticket evidence. It recommends a KCS action, records
the evidence basis, reports blockers, and prepares reviewer-ready packets
without publishing or writing to Zendesk or Help Center.

The MVP focuses on the KCS workflow after or near ticket resolution: deciding
whether knowledge should be reused, updated, created, flagged, split, skipped,
or blocked for review.

## Core Principle

```text
Code decides.
LLM drafts.
Validators block.
```

The core owns workflow decisions, validation, blockers, and readiness state.
Claude or another LLM may draft or review text only through bounded handoff
after the relevant contracts and gates exist.

## Current Scope

Initial development follows the KCS-0..KCS-11 roadmap in
`docs/internal/kcs-authoring-mvp-jira-tracking.md`.

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

KCS-1 through KCS-7 do not require live Zendesk access, Zendesk tokens, Claude
connector setup, or `kcs-search-mcp` access. KCS-8 introduces the read-only
Zendesk source boundary only. KCS-9a introduces a provider protocol and local
validation/normalization boundary only. KCS-9b introduces the bounded
reviewer-assist handoff contract only. KCS-9c introduces reviewer-only draft
contracts and local artifact writing only. KCS-10 introduces local reviewer
bundle writing only. KCS-11 introduces a live-capable provider adapter package
and bounded smoke layer only. Production transport rollout, MCP/internal
service implementation, and broad adapter/client integration remain later
slices.

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
- Access to the WebPros GitHub Enterprise repository
- Access to the relevant Jira PAUX work items

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
- keep `auto_publish_allowed=false` in MVP outputs.

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

## Ownership

- Maintainer / implementation lead: Alex Tsmokalyuk
- Parent Jira item: PAUX-7083
- Current implementation subtask: KCS-11 Live Claude Provider Adapter

Update this section when the PM owner, reviewer, Slack channel, or GitHub
CODEOWNERS are finalized.

## Visibility

Internal - WebPros confidential. Do not share repository contents, fixtures,
packets, logs, or generated artifacts outside approved WebPros channels.
