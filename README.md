# KCS Authoring Workflow

KCS Authoring Workflow helps a support engineer turn an approved, sanitized
support ticket into the right knowledge action:

- reuse an existing public article;
- update an existing article;
- draft a new article when nothing fits;
- stop when the ticket does not contain enough evidence.

The workflow is reviewer-only. It does not publish articles, write to Zendesk,
or send customer replies.

Some historical package names and paths still contain `kcs-authoring-mvp` for
compatibility.

## Current status

The local Claude Desktop workflow is implemented through KCS-15.2b2.

One representative, approved noisy ticket completed the full installed flow:
five separate KCS items were identified, selected by the operator, compared
with public articles, and routed to their appropriate outcomes. This proves
that the workflow is feasible. It does not yet prove repeated stability or
production readiness.

The next planned evaluation is KCS-15.2b3: three comparable installed runs
using the same ticket and value-safe local/Langfuse accounting. It will measure:

- whether the same KCS items and decisions survive repeated runs;
- whether clearly irrelevant public articles are shown;
- how much operator effort the comparison flow requires;
- where observable runtime time and model-visible bytes accumulate.

Enterprise rollout, automatic publication, and a host-specific in-chat app UI
remain deferred.

## What the operator experiences

The normal Desktop flow starts with:

```text
/draft <ticket_ref>
```

The workflow then:

1. identifies separately useful KCS items in the ticket;
2. asks the operator which items should continue;
3. searches eligible public Plesk Support articles for each selected item;
4. shows bounded ticket facts and public article evidence;
5. asks the operator to choose `reuse`, `update`, `none_fit`, or
   `need_more_evidence`;
6. drafts only items that were confirmed as `none_fit`;
7. writes reviewer-only local bundles for human review.

For a noisy ticket, the operator can select several independent items. The
workflow processes their comparisons in sequence and preserves completed
decisions if a later item is blocked.

If automatic item identification misses a meaningful issue, the operator may
describe the missing item during the selection step. The proposal still has to
pass the same evidence and safety validation as automatically identified
items.

## What KCS-15 added

### Style and article-quality parity

The repository now contains tracked Markdown copies of the approved KCS source
pack, with links back to the slowly changing authoritative Confluence pages.
Plesk-specific rules take priority over broader WebPros guidance.

The active source hierarchy is:

1. Plesk KCS Style Guide and Article Quality Criteria;
2. operator-owned KCS practices;
3. KCS Content Standard Checklist and Style Triggers;
4. broader WebPros guidance for cross-checking;
5. Article Simplification Guide for later polishing.

The rules are connected to deterministic policy tests and review gates where
mechanical enforcement is possible.

### Search before drafting

Each selected KCS item is compared with existing public Plesk Support
knowledge before a new article can be drafted.

Only eligible public KB/support articles may be offered as `reuse` or `update`
candidates. Manuals, release notes, changelogs, and incident notices are not
valid reuse candidates.

An article explicitly mentioned in the ticket receives priority only when the
ticket says it helped or resolved the issue, at least partially. A mere link or
mention is not evidence of usefulness.

### Operator-confirmed decisions

The model may summarize evidence and recommend an outcome, but Python owns:

- candidate eligibility;
- workflow state;
- accepted decision values;
- comparison ordering;
- drafting and readiness gates;
- reviewer-only and no-publish boundaries.

The operator makes the final reuse decision. A draft cannot be created before
that decision.

### Bounded public evidence

The RAG integration is an adapter, not workflow authority. The comparison
logic does not depend on whether search is hosted locally or later exposed
through an approved remote API.

Only bounded public article context is model-visible. If RAG is unavailable or
returns an invalid response, the workflow reports that search is unavailable
and stops the affected comparison instead of guessing.

### Optional run accounting

Installed runs can write value-safe local accounting reports containing only
closed codes, counts, durations, byte sizes, and random correlation hashes.
An external script can export those reports to a loopback-only Langfuse
instance.

Prompts, responses, ticket text, article excerpts, URLs, reviewer bundles, and
Desktop log text are not sent to Langfuse. Accounting is optional and fail-open
for normal authoring.

## Safety boundaries

The following remain unchanged:

- no Zendesk writes;
- no Help Center publication;
- no customer reply generation;
- no auto-publish;
- no raw ticket processing inside the runtime-independent core;
- no model-owned KCS decisions;
- no unvalidated provider output;
- reviewer bundles remain local and uncommitted.

The short design principle is:

```text
Code decides.
LLM drafts.
Validators block.
The operator confirms reuse.
```

## Product architecture

The implementation is split into a runtime-independent core and adapters:

```text
src/kcs_core/          deterministic packets, decisions, validation, rendering
src/kcs_adapters/      Desktop, RAG, provider, storage, and observability edges
tests/kcs_core/        core contracts and behavior
tests/kcs_adapters/    installed/runtime boundary behavior
```

The development history is intentionally not repeated here. Detailed slice
status and design evidence live in:

- [`engineering-roadmap.md`](docs/internal/engineering-process/engineering-roadmap.md)
- [`kcs-authoring-mvp-feature-engineering.md`](docs/internal/kcs-authoring-mvp-feature-engineering.md)
- [`kcs-authoring-mvp-jira-tracking.md`](docs/internal/kcs-authoring-mvp-jira-tracking.md)
- [`slice-plans/`](docs/internal/engineering-process/slice-plans/)

## Local setup

Requirements:

- Python 3.11;
- Git;
- `uv` or a Python 3.11 virtual environment.

Using `uv`:

```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e '.[dev]'
```

Using standard Python:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e '.[dev]'
```

Run the full local checks:

```bash
python -m pytest -q
ruff check src tests scripts
```

## Operator-controlled local entrypoint

For an existing approved local ticket reference:

```bash
uv run kcs-controlled-draft <ticket_ref>
```

This command enters the comparison workflow directly, displays bounded ticket
facts and eligible article evidence, and reads the operator decision from an
interactive terminal menu.

Use a write-incapable preflight to prove search and rendering without accepting
a decision:

```bash
uv run kcs-controlled-draft --preflight <ticket_ref>
```

Only operator-confirmed `none_fit` can continue to reviewer-only drafting.

## Claude Desktop extension

Build the MCPB package:

```bash
uv run python scripts/build_kcs_mcpb.py
```

Install or replace the local package:

```bash
uv run python scripts/install_kcs_mcpb.py
```

Then reload/restart Claude Desktop and run the installed stdio smoke:

```bash
uv run python scripts/smoke_kcs_mcpb_stdio.py
```

The smoke checks the same wrapper used by Desktop, tool schemas, installed
artifact identity, controlled comparison transitions, and reviewer-only bundle
behavior. It does not prove the quality of a live model run.

For a manual Desktop smoke, print a synthetic prompt and its verifier command:

```bash
uv run python scripts/smoke_claude_desktop_ui_prompt.py \
  --print-manual-prompt \
  --prompt-kind raw-ticket \
  --copy-manual-prompt
```

The prompt is exposed only after the source, built package, installed files,
Desktop registry, and live RAG capability pass their preflights.

## Optional Langfuse accounting

Enable local reports by setting an ignored output directory:

```bash
KCS_DRAFT_RUN_ACCOUNTING=local-json \
KCS_DRAFT_RUN_REPORT_DIR=.runtime/kcs-draft-runs \
uv run kcs-desktop-mcp
```

Export one validated report to an already configured loopback Langfuse
instance:

```bash
uv run --python 3.11 --with langfuse==4.7.0 \
  python scripts/kcs14_langfuse_draft_run.py \
  --report <value-safe-report.json>
```

Langfuse is not a runtime dependency. The exporter requires explicit loopback
configuration and rejects report fields outside the closed safe schema.

## Data handling

Use only synthetic or approved sanitized fixtures and ticket snapshots.

Do not commit:

- raw Zendesk JSON or comments;
- customer identifiers;
- credentials or private endpoints;
- internal article chunks or vector values;
- raw query logs or Desktop logs;
- generated drafts, reviewer bundles, or runtime accounting files.

The authoritative policy is
[`kcs-authoring-mvp-data-handling-baseline.md`](docs/internal/kcs-authoring-mvp-data-handling-baseline.md).

## KCS source documents

Tracked working copies and authority links live under
[`docs/internal/kcs-sources/`](docs/internal/kcs-sources/).

Start with:

- [`README.md`](docs/internal/kcs-sources/README.md)
- [`kcs-style-guide-plesk.md`](docs/internal/kcs-sources/kcs-style-guide-plesk.md)
- [`article-quality-criteria.md`](docs/internal/kcs-sources/article-quality-criteria.md)
- [`operator-kcs-practices.md`](docs/internal/kcs-sources/operator-kcs-practices.md)

## Engineering commands

The supported local command index is
[`tool-entrypoints.md`](docs/internal/engineering-process/tool-entrypoints.md).

See [`CONTRIBUTING.md`](CONTRIBUTING.md) and
[`git-policy.md`](docs/internal/engineering-process/git-policy.md) for branch,
commit, review, and data-safety rules.
