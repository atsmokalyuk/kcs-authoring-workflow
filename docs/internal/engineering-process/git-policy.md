# Git Policy

## Purpose

Define lightweight Git rules for the `kcs-authoring-mvp` PAUX project.

The project is small, but it handles AI-assisted workflow logic, KCS evidence packets, Zendesk-derived data boundaries, and future corporate adapters. Git history must therefore stay reviewable, traceable, and free of sensitive artifacts.

This policy is local project guidance. Corporate WebPros policy wins if there is a conflict.

`local-docs/` is a developer-local guidance layer and must not be committed to the project repository. The repository `.gitignore` must keep `local-docs/` ignored.

## Repository Model

Use a simple GitHub Enterprise model:

```text
main
  <- pull request from short-lived task branch
```

Rules:

- `main` is the default branch.
- Do not push directly to `main` except for explicitly approved emergency repository maintenance.
- Do not use long-lived `develop`, `next`, or integration branches unless the project grows and this policy is revised.
- Use short-lived task branches for all implementation and documentation changes.
- Prefer one Jira subtask or one coherent engineering slice per branch.

## Branch Naming

Branch names should include the work type and Jira key when available.

Recommended patterns:

```text
feature/PAUX-7084-core-packet-contracts
tech/PAUX-7084-fixture-validation-tests
docs/PAUX-7084-data-handling-baseline
bugfix/PAUX-7084-fix-contract-validation
spike/PAUX-7084-search-adapter-experiment
```

Branch types:

- `feature/`: new user-visible or workflow-visible capability.
- `tech/`: internal refactor, tests, package setup, CI, or tooling.
- `docs/`: documentation-only changes.
- `bugfix/`: defect fix.
- `spike/`: temporary research. A spike branch should not be merged as production code without cleanup and a normal PR.

Keep branches small enough to review. If a branch grows beyond one Jira slice, split it.

## Commit Rules

Commits should be small, coherent, and signed when corporate GitHub requires or supports it.

Use WebPros-style commit prefixes with the Jira key:

```text
FEATURE PAUX-7084 Define core packet contracts
TECH PAUX-7084 Add fixture validation tests
BUGFIX PAUX-7084 Fix unsafe fixture rejection
DOCS PAUX-7084 Document Git policy
```

If `DOCS` is not accepted by the target corporate convention, use `TECH` for documentation-only repository changes.

Commit guidelines:

- One commit should represent one logical change.
- Do not mix unrelated docs, tests, refactors, and behavior changes in the same commit.
- Do not commit fixup/noise commits to `main`; squash or clean them before merge if needed.
- Do not rewrite branch history after review has started unless reviewers know why.
- Never commit secrets, credentials, tokens, `.env` contents, raw ticket data, or generated runtime artifacts.
- Do not bypass repository hooks or checks with `git commit --no-verify` unless the maintainer/PM explicitly approves an exceptional emergency path. Normal failed checks must be fixed or documented as deferred before commit.

## Pull Requests

All non-trivial changes should go through PR review, even when the same person is developer and technical lead.

A PR should include:

```text
Jira:
Scope:
Changed files:
Validation run:
Data/security notes:
Deferred items:
```

PR rules:

- Link the Jira/PAUX issue.
- Keep the diff reviewable.
- State whether contracts changed or remained unchanged.
- State whether data-handling boundaries changed or remained unchanged.
- Include local validation commands and results.
- Note if no docs update was needed and why.
- For AI-assisted code, treat output as normal code: tests, review, and security/data checks still apply.

## Merge Strategy

Prefer squash merge for this project.

Rationale:

- keeps `main` history clean;
- maps one merged commit to one PR/Jira slice;
- works well for a small project with one primary developer.

The squash commit message should follow the same commit format:

```text
FEATURE PAUX-7084 Define core packet contracts
```

Use regular merge commits only if there is a clear reason to preserve a carefully structured branch history.

## Remote Branch Retention

Do not delete remote branches after merge by default.

Rationale:

- this is a small audit-sensitive PAUX/MVP project;
- remote branches help preserve development context while Jira/PR/process rules are still stabilizing;
- accidental branch deletion makes it harder to inspect historical implementation slices.

Rules:

- Disable automatic remote branch deletion after merge unless a later repository policy explicitly enables it.
- Do not run `git push origin --delete <branch>` for merged remote branches unless the maintainer/PM explicitly approves it.
- Do not bulk-delete stale remote branches during normal development.
- Local branches may be deleted after merge only after confirming there is no unpushed work and no active review/debug need.
- If remote branch cleanup becomes necessary later, document the retention policy first and perform cleanup as an explicit maintenance task.

## Main Branch Protection

When the repository is hosted on GitHub Enterprise, configure `main` to require:

- pull request before merge;
- at least one approval, if practical for the team setup;
- required status checks once CI exists;
- signed commits, if corporate policy requires it;
- no force-push;
- no branch deletion by non-maintainers;
- no automatic remote branch deletion after merge unless a documented retention
  policy allows it.

For a one-developer prototype, review may be lightweight, but branch protection and traceability should still be used when available.

## Jira Traceability

Every non-trivial PR should map to a Jira issue or subtask.

Traceability chain:

```text
Jira issue
  -> branch name
  -> commits
  -> PR
  -> validation/checks
  -> merge
```

Keep Jira lightweight:

- one issue per vertical slice or documentation slice;
- avoid one issue per tiny commit;
- update Jira with the PR link when the PR is opened or merged;
- keep acceptance criteria aligned with the PR scope.

## Sensitive Data and Runtime Artifacts

Do not commit:

- Zendesk raw JSON;
- full ticket comments;
- raw internal comments;
- customer identifiers;
- live domains, IPs, hostnames, license IDs, private paths;
- credentials, tokens, keys, certificates, `.env` files;
- local RAG indexes, vectors, chunks, downloaded corpora, raw query logs;
- generated draft articles or reviewer packets from normal runtime use;
- Claude prompts/outputs containing ticket-derived evidence;
- build outputs, virtualenvs, caches, or local IDE state.

Allowed test data must follow `docs/internal/kcs-authoring-mvp-data-handling-baseline.md`.

Fixtures may be committed only when they are synthetic or approved sanitized fixtures and pass the project fixture safety expectations.

## `.gitignore` Expectations

The repository should ignore at least:

```text
# Python
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/

# Virtual environments
.venv/
venv/

# Build artifacts
build/
dist/
*.egg-info/

# Local config and secrets
.env
.env.*
*.pem
*.key
*.crt
*.p12
id_rsa*
known_hosts

# Runtime/cache artifacts
.cache/
.runtime/
artifacts/runtime/
rag-cache/
vector-cache/

# OS/IDE
.DS_Store
.idea/
.vscode/
```

If the project intentionally tracks a generated artifact, document why and how to regenerate it.

## Dependency Files

Use a simple Python dependency strategy at first.

Recommended for MVP:

- `pyproject.toml` for package metadata/tool config;
- a lock file if the chosen tool creates one and it is approved for the repo;
- no committed virtualenvs or local package caches.

Dependency and packaging decisions should be documented in README or local engineering docs once code starts.

## Security Checks

When CI exists, start with:

- tests;
- formatting/linting;
- Python complexity checks for safety, decision, validation, renderer, and adapter code;
- secret scanning, such as Gitleaks or GitHub secret scanning;
- dependency vulnerability checks when dependency baseline exists.

A secret finding should fail CI, not only warn.

If a secret is committed:

1. Revoke or rotate it first.
2. Remove it from the repo and history if required.
3. Notify the appropriate security channel according to corporate process.

## AI-Assisted Development

AI tools may help with coding, review, and docs only within approved corporate usage rules.

Rules:

- Do not paste raw Zendesk data, confidential data, secrets, customer identifiers, or internal-only evidence into unapproved AI tools.
- Do not treat AI-generated code as trusted by default.
- Review AI-generated code for correctness, security, data handling, and project contract alignment.
- PRs that use AI assistance still need tests and validation evidence.

## Local Developer Checklist

Before opening a PR:

- branch name includes Jira key when available;
- commits are coherent and signed if required;
- no secrets or runtime artifacts are staged;
- fixtures follow the Data Handling Baseline;
- relevant tests/checks were run;
- docs are updated or no-doc rationale is included;
- PR description includes Jira, scope, validation, data/security notes, and deferred items.
