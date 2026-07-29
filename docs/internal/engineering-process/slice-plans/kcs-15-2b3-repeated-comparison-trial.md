# KCS-15.2b3 Repeated Comparison Trial

Status: Design selected; Delivery locked. The operator agreed on 2026-07-29
that repeated stability, operator comfort, false positives, and Langfuse
accounting belong here rather than blocking KCS-15.2b2 closeout.

## Requested outcome

Determine whether the completed KCS-15.2b2 operator-confirmed comparison
workflow is repeatable on the approved sanitized super-noisy ticket, and
identify where model, RAG, host, or tool-boundary overhead accumulates without
exposing ticket or article content to observability.

## Current operational reality

Confirmed:

- KCS-15.2b2 completed one installed Desktop run across all five accepted KCS
  items and all five reuse decisions.
- That run proves representative feasibility, not repeated stability.
- Existing optional draft-run accounting records only closed codes, counts,
  durations, byte sizes, retry/correction counts, and random correlation
  hashes.
- The external exporter validates that report before sending metadata-only
  observations to loopback Langfuse.
- Normal authoring remains fail-open when accounting or Langfuse is absent.

Provisional:

- three comparable completed runs are enough for an initial descriptive
  stability verdict;
- the existing accounting fields are sufficient to locate the dominant
  observable tool-boundary overhead.

Unknown:

- stability of the five accepted item identities and comparison progression;
- repeated retrieval and recommendation consistency;
- correction and operator overhead across comparable runs;
- whether host quota interrupts the bounded evidence budget;
- which observable workflow stage contributes the most duration and
  model-visible bytes.

Rejected:

- keeping KCS-15.2b2 open until repeated stability is proven;
- adding prompt, workflow, RAG, or authoring changes during the counted series;
- storing raw ticket, article, prompt, response, or Desktop-log content in
  reports or Langfuse.

## Intended entrypoint and UX

The operator starts each run through the supported installed Claude Desktop
entrypoint:

```text
/draft ticket-94893302
```

The same approved sanitized ticket snapshot is used. The operator selects all
five accepted items. The prior decisions are the comparison baseline:

```text
none_fit, reuse, reuse, update, none_fit
```

Wording may vary. The operator still decides from the visible evidence and
must not force the baseline when the candidates or evidence differ. A justified
different decision is recorded as trial drift and stops the current revision.
The five issue identities, evidence boundaries, candidate eligibility, and
deterministic outcomes may not drift silently.

## Selected trial boundary

- Trial count: `N=3` accepted comparable runs.
- Maximum attempts: 5.
- Host-quota interruptions: recorded as `host_quota_exhausted`, do not count
  toward `N=3`, and stop the trial after two such interruptions.
- Fixed conditions: same approved sanitized ticket hash, installed source and
  artifact identity, Claude Desktop client build, selected `Sonnet 5` model
  with `Medium` mode, active public-RAG capability, tool schemas, and accounting
  configuration.
- No implementation, prompt, fixture, provider, ranking, or threshold changes
  between counted runs.
- Each counted run must produce one schema-valid local accounting report and
  one metadata-only loopback Langfuse trace.

Changing a fixed condition starts a new trial revision; results from different
revisions are not combined.

## User / operator

- KCS operator evaluating repeated comparison fit and comfort.
- Technical lead reviewing value-safe stability and bottleneck evidence.

## Allowed inputs

- the existing approved sanitized `ticket-94893302` snapshot and safe hash;
- bounded public Plesk Support/KB comparison evidence;
- current value-safe installed-runtime and RAG preflight results;
- closed-schema local draft-run accounting reports;
- operator enum decisions and comfort closeout.

## Forbidden inputs

- raw or newly downloaded ticket content in tracked artifacts or telemetry;
- prompt, response, article, excerpt, Desktop-log, or reviewer-bundle content
  in Langfuse;
- credentials, private endpoints, customer identifiers, or local private paths;
- unapproved changes to the fixed trial conditions during a counted series.

## Output contract

The trial produces an ignored local ledger plus a tracked aggregate closeout
containing only conditions, hashes, counts, durations, byte sizes, closed
codes, invariant results, operator comfort enums, and the final
`expand`/`iterate`/`stop` verdict. It produces no new runtime schema or
customer-facing output.

## Failure behavior

Accounting and Langfuse remain fail-open for normal product behavior. For this
trial only, a missing/invalid report or trace makes the attempt non-countable.
Any content leak, stale identity, non-loopback exporter, critical invariant
failure, or required product correction stops the current revision.

## Operator Decision Readiness

Decision: separate repeated stability from KCS-15.2b2 and use an `N=3`
fixed-ticket trial with existing value-safe Langfuse accounting.

Visible information: one installed representative run completed all five
comparison decisions; existing accounting can expose closed transition
counts, durations, bytes, correction counts, and terminal classifications but
cannot expose hidden model turns.

Sufficiency and limits: enough to select a bounded descriptive trial; not
enough to define a performance SLA or cross-ticket quality claim.

Options considered: keep b2 open for three runs; close b2 and omit stability
evidence; close b2 and create b3. The operator selected the third option.

Consequences: at most five installed attempts and three counted runs; no
runtime behavior change; operator supplies repeated comparison decisions and a
comfort enum.

Uncertainty / failure path: host quota, missing trace, or any product defect
stops the revision instead of triggering an inline fix.

Recommendation: run b3 only after the current installed accounting and
loopback Langfuse preflight are proven together.

## Behavioral invariants

Every counted run must:

- reach native selection with the same five accepted issue identities;
- preserve the selected five-item batch through all five comparison decisions;
- show only eligible Plesk Support/KB reuse candidates;
- keep manuals, release notes, changelogs, incident notices, and other
  ineligible pages out of reuse/update candidates;
- preserve exact helpful/partially-helpful article priority only when the
  ticket says the article helped or resolved the issue;
- create no draft before its comparison decision;
- preserve `reuse`, `update`, `none_fit`, and `need_more_evidence` ownership in
  deterministic Python;
- tolerate existing downstream content-evidence or draft-quality blockers
  without misclassifying them as comparison/RAG failures;
- keep reviewer-only, no-write, and no-publish boundaries unchanged.

## Langfuse and local-report evidence

For each accepted run, compare only existing value-safe fields:

- terminal outcome and source;
- transition count and batch outcome category;
- selected, attempted, completed, retryable-blocked, and stopped item counts;
- total and per-transition duration;
- request, result, and model-visible byte counts;
- candidate and excerpt counts;
- retry and semantic-correction counts;
- RAG availability and network-call booleans;
- closed debug and success-classification codes.

The aggregate closeout reports:

- per-stage duration and model-visible-byte distribution;
- the slowest observable stage in each run;
- cross-run variance for counts, corrections, and durations;
- host quota or RAG availability interruptions;
- unexpected repeated questions or operator actions;
- false-positive candidate or recommendation findings.

This instrumentation observes MCP transitions, not hidden model turns.
Comparison-stage duration includes the existing high-level tool boundary and
is not claimed as provider-only RAG latency.

## Threshold and verdict

Pass threshold:

- 3/3 accepted runs satisfy every critical behavioral invariant;
- 3/3 emit schema-valid local reports and metadata-only Langfuse traces;
- zero ineligible reuse/update candidates;
- zero unsupported claims that an article helped or resolved the issue;
- zero lost, duplicated, or reordered deterministic comparison decisions;
- no more than one bounded semantic correction per accepted run;
- no repeated or unnecessary operator question caused by lost workflow state;
- operator records no run as `uncomfortable`.

Operator overhead limit:

- at most one item-selection action and five comparison decisions per run;
- at most two additional evidence confirmations when an existing downstream
  authoring gate requires them.

Closeout verdict:

- `expand`: threshold met; proceed without changing KCS-15.2b2;
- `iterate`: one bounded, evidence-backed correction is identified;
- `stop`: critical invariant fails, corrections cycle, two host-quota
  interruptions occur, or the five-attempt budget is exhausted.

## Permitted corrections

No product or prompt correction is permitted inside the counted series.
Operator choices and an existing bounded semantic correction are normal trial
inputs. A product defect, RAG contract mismatch, stale runtime, or accounting
gap stops the current revision and produces an `iterate` or `stop` verdict.

## Acceptance-to-gate mapping

| Acceptance criterion | Gate |
| --- | --- |
| Fixed runtime, model, ticket, RAG, tool, and accounting identities are current before every attempt. | deterministic installed-runtime preflight and value-safe trial ledger |
| Five accepted items and all five comparison decisions survive every counted run. | bounded-model trial, `N=3`, plus deterministic accounting counts |
| Candidate eligibility and helpful-article priority do not produce false positives. | bounded-model trial plus named operator review |
| Operator overhead stays within the declared bound and no run is uncomfortable. | named operator review using enum-only closeout |
| Every counted run has a valid local report and metadata-only Langfuse trace. | deterministic report validation and exporter result |
| Observability cannot change authoring behavior and exposes no content. | existing fail-open equivalence, privacy canary, and metadata-schema tests |
| Repeated stability claims remain separate from KCS-15.2b2 feasibility. | documentation and closeout review |

## Unchanged contracts

- No packet, tool, provider, RAG, comparison, authoring, renderer, reviewer,
  storage, Zendesk, or publication schema changes.
- Python remains the deterministic decision owner.
- `auto_publish_allowed=false` and `public_output_approved=false`.
- Langfuse and its SDK remain optional and outside the product runtime.
- Phase C host UI remains deferred.

## Complete unknown inventory

- Whether three comparable accepted runs fit within the current host quota.
- Whether the current operator-comfort enum needs a later richer UX study.
- Whether duration variance from only three runs is sufficient for a later
  performance hypothesis.
- Whether a materially different representative ticket is required after this
  fixed-ticket stability trial.

These unknowns do not reopen KCS-15.2b2.

## Approval ledger

```text
Outcome agreement: agreed 2026-07-29
Design selection: selected; N=3 fixed-ticket installed trial with existing value-safe Langfuse accounting
Delivery authorization: locked; planning and KCS-15.2b2 closeout authorized, live repeated trial not started
```

## Stop conditions

Stop before the first counted run if source/artifact/runtime, RAG capability,
ticket hash, model/client, or effective accounting configuration is not proven.
Stop during the series on the first critical invariant failure, any content
leak, an unavailable accounting report, a non-loopback exporter target, a
required product correction, two host-quota interruptions, or five total
attempts.
