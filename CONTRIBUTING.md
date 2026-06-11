# Contributing

## Source of Truth

Before changing code or docs, read the relevant project documents:

- `docs/internal/kcs-authoring-mvp-data-handling-baseline.md`
- `docs/internal/kcs-core-pipeline-architecture-and-contracts.md`
- `docs/internal/kcs-authoring-mvp-feature-engineering.md`
- `docs/internal/kcs-authoring-mvp-jira-tracking.md`

`AGENTS.md` may exist locally for developer/agent behavior, but it is not a
tracked repository contract. If a prompt, implementation idea, or local note
conflicts with `docs/internal/`, follow `docs/internal/` and surface the
conflict.

## Development Model

Use short-lived task branches from `main`.

Recommended branch names:

```text
feature/PAUX-7084-core-packet-contracts
tech/PAUX-7084-fixture-validation-tests
docs/PAUX-7084-data-handling-baseline
bugfix/PAUX-7084-fix-contract-validation
```

Do not push directly to `main`. Use pull requests for non-trivial changes.

Remote branches should not be deleted after merge by default. Remote branch cleanup requires explicit maintainer/PM approval or a later documented retention policy.

## Commit Messages

Use WebPros-style commit prefixes with the Jira key when available:

```text
FEATURE PAUX-7084 Define core packet contracts
TECH PAUX-7084 Add fixture validation tests
BUGFIX PAUX-7084 Fix unsafe fixture rejection
DOCS PAUX-7084 Document repository workflow
```

If `DOCS` is not accepted by the target corporate convention, use `TECH` for documentation-only repository changes.

## Pull Requests

Every PR should state:

- Jira issue or subtask;
- scope;
- changed files;
- validation run;
- data/security notes;
- deferred items.

Keep PRs narrow and aligned with one Jira slice where practical.

## Data and Artifacts

Do not commit:

- raw Zendesk JSON or ticket comments;
- customer identifiers, live domains, IPs, hostnames, license IDs, private paths;
- credentials, tokens, keys, `.env` files;
- internal article chunks, vector values, raw query logs;
- runtime drafts, reviewer packets, caches, or generated local artifacts;
- local `AGENTS.md` or `.gitignore` files;
- `local-docs/`.

Fixtures must be synthetic or approved sanitized fixtures and must follow the Data Handling Baseline.

## Validation

Run the narrowest relevant local checks for the slice.

Expected progression:

- KCS-1: contract and fixture validation tests;
- KCS-2: safety/evidence gate tests;
- KCS-3: deterministic decision tests;
- KCS-4: renderer and Zendesk HTML tests;
- KCS-5: validation report and loop-state tests;
- KCS-6+: CLI/adapter-specific checks.

Do not add live Zendesk, Claude connector, or internal search tests before their dedicated slices.
