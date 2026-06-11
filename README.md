# KCS Authoring MVP

Internal WebPros PAUX prototype for a runtime-independent KCS Authoring core.

Status: planning / documentation baseline. Python baseline: 3.11. CI, package
metadata, and runnable commands will be added with the first code slice.

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

First code slice:

```text
KCS-1: core packet contracts and safe fixtures
```

KCS-1 does not require live Zendesk access, Zendesk tokens, Claude connector
setup, or `kcs-search-mcp` access.

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
`-- docs/
    `-- internal/
        |-- kcs-authoring-mvp-goal-and-success-criteria.md
        |-- kcs-authoring-mvp-data-handling-baseline.md
        |-- kcs-core-pipeline-architecture-and-contracts.md
        |-- kcs-core-pipeline-technical-design.md
        |-- kcs-authoring-mvp-feature-engineering.md
        `-- kcs-authoring-mvp-jira-tracking.md
```

Planned code structure starts in KCS-1:

```text
src/kcs_core/       # Runtime-independent Python core
tests/kcs_core/     # Contract, fixture, gate, decision, renderer tests
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

There is no installable package yet. Package metadata and dependencies will be
introduced with the first code slice.

Expected local setup once Python code is added:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e '.[dev]'
```

If the project chooses another approved dependency tool, update this section in
the same PR that introduces it.

### Running Tests

There are no tests yet because the repository currently contains the planning
and contract baseline only.

Expected command once KCS-1 tests are added:

```bash
pytest
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
- First implementation subtask: PAUX-7084 / KCS-0 baseline, followed by KCS-1
  packet contracts and fixtures

Update this section when the PM owner, reviewer, Slack channel, or GitHub
CODEOWNERS are finalized.

## Visibility

Internal - WebPros confidential. Do not share repository contents, fixtures,
packets, logs, or generated artifacts outside approved WebPros channels.
