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

Initial development follows the KCS-0..KCS-10 roadmap in
`docs/internal/kcs-authoring-mvp-jira-tracking.md`.

Implemented code slices:

```text
KCS-1: core packet contracts and safe fixtures
KCS-2: safety and evidence readiness gates for sanitized normalized evidence
KCS-3: deterministic KCS action decision core
KCS-4: reviewer packet renderer and Zendesk HTML output
KCS-5: validation report and ready-for-reviewer loop state
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

KCS-1 through KCS-5 do not require live Zendesk access, Zendesk tokens, Claude
connector setup, or `kcs-search-mcp` access. Bundle writing, CLI handoff,
Claude handoff, and adapter/client integration belong to later slices.

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
|   `-- kcs_core/
`-- tests/
    `-- kcs_core/
```

The Python package contains runtime-independent KCS core contracts and gates:

```text
src/kcs_core/       # Runtime-independent Python core
tests/kcs_core/     # Contract, fixture, gate, and decision tests
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
- Current implementation subtask: KCS-5 Validation Report and Ready-for-Reviewer
  Loop State

Update this section when the PM owner, reviewer, Slack channel, or GitHub
CODEOWNERS are finalized.

## Visibility

Internal - WebPros confidential. Do not share repository contents, fixtures,
packets, logs, or generated artifacts outside approved WebPros channels.
