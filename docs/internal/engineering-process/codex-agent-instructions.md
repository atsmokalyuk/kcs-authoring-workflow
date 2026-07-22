# Codex Agent Local Instructions

## Working Modes

Choose the smallest mode that fits the operator request. Do not turn a small
mechanical edit into a full planning exercise unless the operator asks for it.

### Architect / Planning Mode

Use this mode when the operator asks to plan a feature or slice, including:

```text
plan new slice
create implementation plan
создай план реализации фичи
```

Required behavior:

- Do not code immediately.
- Read `docs/internal/engineering-process/spec-first-engineering-playbook/`.
- Read `docs/internal/engineering-process/feature-engineering-playbook.md`.
- Draft or update the slice spec with:
  - goal;
  - user / operator;
  - allowed inputs;
  - forbidden inputs;
  - output contract;
  - failure behavior;
  - tests / evals;
  - acceptance criteria;
  - review checklist.
- Ask concise questions for material unknowns.
- Wait for operator confirmation before changing runtime behavior, data
  handling, privacy boundaries, schemas/contracts, persistence, integrations,
  or public/reviewer output.

### Builder / Implementation Mode

Use this mode after the slice is agreed or when the task is a direct
implementation request with clear scope.

- Implement the smallest safe slice.
- Preserve existing contracts unless the operator explicitly authorizes a
  contract change.
- Follow existing style, naming, typing, and test patterns.
- Add or update tests/fixtures before claiming behavior is supported.
- Keep adapters outside the core and keep Python as the deterministic owner of
  validation, decisions, rendering, persistence, and failure behavior.
- Avoid unrelated cleanup, broad refactors, dependency churn, or prompt
  framework additions.

### Bugfix / Forensic Mode

Use this mode for defects, unexpected behavior, failing checks, or suspicious
workflow output.

- Reproduce the issue or define the failing case first.
- Gather evidence before patching.
- Fix the root cause only.
- Do not rename variables, clean up unrelated code, or broaden the patch while
  investigating.
- Keep a regression test or fixture in the codebase when practical.
- If a test is not practical, document the manual reproduction and validation
  result.

### Reviewer Mode

Use the configured review subagent:

```text
gpt-5.3-codex-spark
```

The review must distinguish blockers from warnings.

Blockers include behavior regressions, unsafe data handling, broken contracts,
missing tests for changed behavior, private artifact touches, and README/docs
claims that contradict actual behavior.

Warnings include naming cleanup, small doc clarity issues, low-risk test gaps,
or follow-up hardening that does not block the current slice.

For security-sensitive, privacy-sensitive, hosted/local-boundary, or
cross-module architecture changes, run a deeper review pass focused on policy,
privacy, data boundaries, and architecture drift.

Use
`docs/internal/engineering-process/spec-first-engineering-playbook/06-review-checklist.md`
for the general review checklist.

### Documentation Mode

Use this mode for README, docs, showcase docs, and process guidance.

- Keep docs aligned with actual behavior.
- Do not claim unsupported behavior, live search, production deployment,
  Zendesk writes, Help Center publication, auto-publish, or model-owned
  decisions unless implemented and approved in the product docs.
- Update docs when operator behavior, architecture, safety boundaries,
  contracts, validation workflow, or public/reviewer output changes.
- Do not update docs for purely internal refactors unless the documented
  behavior or operator path changed.
- Keep personal/private engineering notes under `local-docs/`; do not move
  them into tracked product docs unless they become authoritative process,
  contract, review, or test evidence.

## Version Awareness

Do not invent dependency, tool, model, API, or command versions from training
memory.

Before changing versions, model names, APIs, external commands, or dependency
constraints, inspect local sources first:

- project config such as `pyproject.toml`;
- lock or pin files, if present;
- local docs and README;
- existing implementation and tests;
- installed command help or version output when local tooling provides it.

If a version cannot be verified from local context, leave an explicit note
instead of silently choosing a guessed or possibly outdated value.

## Before Every Commit

- If present, reread the local-only
  `local-docs/engineering-process/implementation-mistake-log.md`.
- Check the staged or intended diff against relevant tracked process docs and,
  when present, the local mistake-log preflight checklist.
- Run tests with the project Python baseline, currently Python 3.11.
- Run Ruff linting/format checks when the project tooling is present.
- Run `git diff --check`.
- Inspect `git diff --cached --name-status`.
- Run a `gpt-5.3-codex-spark` review pass on the staged or intended diff.
- Do not commit until required review findings are fixed or explicitly deferred.
- Do not use `git commit --no-verify` or bypass project checks. Fix the check or document a maintainer-approved deferral.

## Before Pre-Merge Review Or Merge

- Reread the review notes for the slice type before running the pre-merge
  `gpt-5.3-codex-spark` reviewer.
- For core runtime changes, use `docs/internal/kcs-core-pipeline-review-notes.md`.
- For KCS-14 process, documentation, code-map, or review-tooling changes, use
  `docs/internal/engineering-process/`.
- Check the current diff against the relevant fixed blockers, deferred items,
  and future-development notes recorded in that review log.
- Before merging or fast-forwarding a merged PR locally, reread
  the relevant review notes again and confirm no current-slice blocker from the
  review log remains unresolved.

## Review Routing

Use `gpt-5.3-codex-spark` as the default reviewer before commits.

The review must check at minimum:

- diff sanity and unintended file touches;
- missing or insufficient tests;
- naming and import cleanup;
- typo and doc-contract consistency;
- forbidden-file or private-artifact touches;
- Python 3.11 validation for implementation changes;
- whether the change respects the current slice allowlist;
- whether portability documents were checked when adapting known work.

For documentation changes, also check:

- coherence with existing project docs;
- whether the changed document is still current;
- whether related docs or README references need updates;
- whether terminology and scope match the active product/engineering plan.

## AI-Assisted Code Quality Gates

- Treat agent instructions as guidance and deterministic tests/lint as enforcement.
- Keep safety, decision, validation, renderer, and adapter functions small and easy to test.
- If Ruff reports McCabe complexity (`C901`), split the function instead of adding more branching.
- Do not add broad abstractions to silence complexity checks; prefer small named helpers with focused tests.
- If a quality gate is not available yet for the current KCS slice, note the deferred gate in the PR or local implementation notes.
