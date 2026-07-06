# KCS-14 Process Gap Audit

Status: active process-gap tracker for KCS-14.

Purpose: record planned process behavior that is not yet consistently executed
or enforced, then decide whether to fix it now, defer it, or reject it.

## Current Gaps

| Gap | Planned source | Current status | Action |
| --- | --- | --- | --- |
| Context window management before material batches | `agent-operable-engineering-workflow.md`; KCS-14 Slice 1 process baseline | Partially practiced, but not previously a required per-batch gate | Fixed by adding `Context Window Check` to workflow and short kernel rule in `AGENTS.md`. |
| Review model routing names unavailable default reviewer | `AGENTS.md` review routing | `gpt-5.3-codex-spark` is named in repo policy, but the current subagent tool did not expose that model name; current review used inherited subagent defaults | Open. Needs either tool availability alignment or a documented fallback rule before relying on the exact model name as an enforceable process contract. |
| File-based review packet vs closeout substitute | `review-context-protocol.md` | Local per-batch review has used closeout/refactor log instead of a separate review-packet file | Acceptable for tiny/local checkpoints under current protocol, but material external review should still use file-based packets. Re-check before Fable/ChatGPT review. |
| Aggregate design review | Slice 6 methodology | Not due yet; only one refactor batch completed after freeze baseline | Required after Batch 2 or earlier trigger. |
| Reusable extraction | KCS-16 deferred extraction | Not started | Correctly deferred until KCS-14/KCS-15 evidence exists. |

## Review Rule

Before starting each new material batch, check this audit. If a listed gap
affects the batch, either fix it first, explicitly defer it in the batch frame,
or stop for operator approval.
