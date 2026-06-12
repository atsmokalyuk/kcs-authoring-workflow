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
Future local review bundle slices must persist any requested override status in
packet/artifact metadata while preserving the original recommendation and
`auto_publish_allowed=false`.

KCS-1 through KCS-3 do not require live Zendesk access, Zendesk tokens, Claude
connector setup, or `kcs-search-mcp` access.
Reviewer packet and Zendesk HTML validation belong to later slices.

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

There is no CLI/runtime entrypoint yet. CLI work is planned for KCS-6 after
packet contracts, gates, decision logic, renderer behavior, and validation
state exist.

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
- Current implementation subtask: PAUX-7092 / KCS-3 KCS Action Decision
  Engine

Update this section when the PM owner, reviewer, Slack channel, or GitHub
CODEOWNERS are finalized.

## Visibility

Internal - WebPros confidential. Do not share repository contents, fixtures,
packets, logs, or generated artifacts outside approved WebPros channels.
