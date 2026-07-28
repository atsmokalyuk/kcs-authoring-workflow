# KCS-14.5 Local Langfuse Observability

Status: LF-0 local deployment and LF-1 synthetic export complete; auxiliary
live run accounting delivery authorized on 2026-07-28.

LF-0 was explicitly approved and completed on 2026-07-13. On 2026-07-28 the
operator explicitly authorized implementation of the auxiliary live `/draft`
run-accounting boundary. This is an operational observability delivery, not a
product feature slice. It does not authorize changing workflow behavior,
schemas, decisions, publication behavior, or adding a required Python
dependency.

## 2026-07-28 Auxiliary Delivery Boundary

The delivered boundary is intentionally split:

1. the central Desktop MCP adapter projects each relevant tool transition into
   a strict value-safe run report;
2. an optional local sink checkpoints that report under an ignored operator
   directory;
3. a separate command validates the report and exports metadata-only
   observations to loopback Langfuse;
4. an optional local Desktop-log classifier may close an otherwise incomplete
   report as `host_quota_exhausted`.

The runtime boundary records only closed stage/tool/outcome/debug codes, counts,
booleans, byte counts, durations, retry/correction counts, and a random
correlation SHA-256. It never places tool arguments, tool results, refs, ticket
text, excerpts, titles, URLs, prompts, generated prose, reviewer output, paths,
credentials, hostnames, or arbitrary metadata in the report.

The local sink and external exporter are disabled unless the operator supplies
their explicit local configuration. Sink/export failure is fail-open and may
not change a returned `McpToolResult`, raised adapter argument error, workflow
state, written authoring artifact, or process exit behavior.
The environment-created local sink uses a bounded non-blocking background
queue; filesystem latency is outside the workflow call path, and a newer
checkpoint may replace an older one under sustained queue pressure.

The MCP process cannot observe Claude Desktop token usage, hidden context,
stop reason, or remaining host quota. Therefore it must not infer
`host_quota_exhausted`. That outcome is allowed only when the external
Desktop-log classifier observes an allowlisted quota message; otherwise an
unfinished run remains `in_progress` or is explicitly closed as
`client_interruption`.

Acceptance evidence for this auxiliary delivery:

- telemetry disabled, healthy local sink, and failing sink return equivalent
  product results;
- report validation rejects extra fields, arbitrary codes, identifiers, paths,
  or content-bearing values;
- captured reports contain no test privacy canary;
- Langfuse export uses no input/output fields and accepts only an explicit
  loopback URL;
- authoring characterization tests pass without Langfuse or its SDK installed;
- packet, Desktop tool, candidate selection, renderer, reviewer-bundle,
  readiness, and publication contracts remain unchanged.

## Decision

Evaluate self-hosted Langfuse as an optional local observability backend in the
following order:

1. deploy and validate Langfuse independently of KCS;
2. connect only a fixed synthetic KCS-14 runtime rebaseline harness;
3. assess whether the traces provide concrete incident-analysis value;
4. add an optional product-facing telemetry port only after separate approval;
5. add limited high-level runtime spans only after another separate approval.

Langfuse must observe the workflow without participating in workflow decisions.
It must not become a required authoring dependency, source of truth, policy
authority, or storage surface for raw/private workflow content.

The first integration point is the synthetic rebaseline harness, not
`kcs_core`, the Desktop workflow, or general process/log ingestion.

## Why The Plan Changed

The KCS-14 runtime investigation established that the Python state machine and
the Claude Desktop model/control surface require separate evidence. A later
finding showed that the Claude Desktop system prompt used for at least one
runtime comparison was stale.

This changes the comparison contract:

- two runs are not input-equivalent when their effective system instructions
  differ, even if the clean ticket, bounded packet, MCPB package, and visible
  model name appear equal;
- a `4 candidates` versus `5 candidates` difference cannot be classified as
  model variability until system-instruction identity is equal or explicitly
  unavailable;
- MCP/Python instrumentation cannot read or reconstruct Claude Desktop's hidden
  system prompt;
- Langfuse cannot recover hidden reasoning or a historical hidden prompt;
- system-instruction identity must be supplied and verified by the rebaseline
  harness or operator-controlled profile, not inferred from MCP traffic.

The incident plan must therefore treat three instruction sources as distinct
control-surface identities:

1. Claude Desktop system-instruction profile;
2. installed MCPB/Cowork package and skill guidance;
3. deterministic Python-generated tool-result instruction text.

A stale, unknown, or mismatched identity makes a run unsuitable for causal
comparison. It does not block ordinary authoring.

## Goals

- Install and operate Langfuse locally and independently first.
- Preserve all current product and data-handling contracts.
- Support value-safe comparison of repeated synthetic Desktop/MCP runs.
- Identify the boundary at which two runs diverge:
  control-surface identity, packet construction, model proposal, Python
  validation, operator selection, or transport.
- Keep telemetry disabled by default and fail-open for normal authoring.
- Keep the experiment easy to remove.

## Non-Goals

- Capturing Claude hidden chain-of-thought or hidden system-prompt content.
- Fixing candidate variability, timeouts, selection lifecycle, or prompt drift
  automatically.
- Making Langfuse authoritative for KCS decisions, tests, evaluation, or state.
- Adding OpenTelemetry auto-instrumentation, a collector, or a broad
  observability framework.
- Sending real ticket text, prompts, model prose, packets, or reviewer bundles
  to telemetry.
- Changing packet schemas, Desktop tool schemas, candidate selection,
  rendering, reviewer bundles, readiness, or publication behavior.
- Zendesk writes, Help Center publication, or customer replies.

## Preserved Contracts

- Python remains the deterministic workflow owner.
- Claude Desktop remains a runtime/control surface.
- LLM output and tool results remain untrusted inputs.
- Operator selection cannot be skipped.
- Manual/freehand drafting remains blocked where current contracts block it.
- `auto_publish_allowed=false` remains invariant.
- `public_output_approved=false` remains invariant.
- No Zendesk write, Help Center publication, or customer reply capability is
  added.
- Telemetry failure cannot change workflow decisions, returned results, written
  artifacts, or CLI/MCP exit behavior.
- Credentials and local configuration remain untracked.

## Current-State Findings

### Repository

- The package has no normal runtime dependencies and no existing Langfuse or
  OpenTelemetry dependency.
- The repository has no general `ObservabilityEvent` or JSONL observability
  writer. Existing JSONL files are evaluation/reference data and must not be
  misrepresented as a telemetry source of truth.
- CLI and MCP process output can contain packet, argument, result, or local
  artifact data. Blind log ingestion is not an acceptable integration.
- The useful existing seams are synthetic Desktop/MCP smoke entrypoints,
  `KcsDesktopMcpAdapter.call_tool`, and approved-summary pipeline hooks.
- At the time of this pre-closeout finding, runtime-incident changes overlapped
  Desktop adapter files. KCS-14.5 is now closed; any future integration work
  must still use a separate clean worktree and leave retained control-surface
  contracts unchanged.

### Local Deployment Prerequisites

The 2026-07-13 read-only preflight observed:

- Apple Silicon macOS with sufficient CPU and memory for a constrained local
  evaluation;
- approximately 27 GiB of free disk after approved cache cleanup;
- no available Docker/Compose runtime in `PATH`;
- no existing repository Docker or Compose configuration.

Recheck all values immediately before deployment. Twenty-five GiB is an
absolute experiment floor, not a safe long-term allowance. Prefer 40-50 GiB of
free space before pulling images and creating volumes.

### Official Langfuse Constraints To Reverify At Implementation Time

- Docker Compose is the supported simple local/VM evaluation path, but does not
  provide high availability, horizontal scaling, or built-in backups:
  <https://langfuse.com/self-hosting/deployment/docker-compose>.
- The current upstream Compose topology includes web, worker, PostgreSQL,
  ClickHouse, Redis, and MinIO:
  <https://github.com/langfuse/langfuse/blob/main/docker-compose.yml>.
- The upstream file must not be run unchanged for this experiment because its
  port bindings, default secrets, and floating image references require local
  hardening and version review.
- Self-hosted runtime networking does not require Internet access, and OSS
  application telemetry can be disabled:
  <https://langfuse.com/self-hosting/security/networking> and
  <https://langfuse.com/self-hosting/security/telemetry>.
- Langfuse accepts OTLP/HTTP, but its documentation recommends the Langfuse SDK
  for Python/JavaScript applications that do not already have an OTel setup:
  <https://langfuse.com/integrations/native/opentelemetry>.
- An isolated tracer provider is supported, but exact SDK and transitive
  dependency versions must be verified and pinned at slice start:
  <https://langfuse.com/docs/observability/sdk/advanced-features>.
- Server-side ingestion masking and automatic retention policies are
  Enterprise features. They cannot be used as the primary OSS safety boundary:
  <https://langfuse.com/self-hosting/security/data-masking> and
  <https://langfuse.com/self-hosting/license-key>.

## Recommended Architecture

```text
Claude Desktop / synthetic operator protocol
                  |
                  v
existing Desktop/MCP smoke entrypoint
                  |
                  +----> existing Python workflow and result
                  |
                  v
explicit value-safe projection
                  |
          optional synthetic sink
                  |
                  v
local Langfuse on 127.0.0.1
```

The projection is a strict typed allowlist, not an arbitrary metadata mapping.
The projection must be constructed before the Langfuse SDK sees an event.

For the synthetic pilot, the Langfuse client is a development/harness
dependency only. It is not added to the normal package dependency set and is
not imported by normal KCS runtime entrypoints.

If the pilot demonstrates value, a later product slice may add:

```text
TelemetrySink protocol
  |- NoopTelemetrySink (default)
  `- IsolatedLangfuseTelemetrySink (optional)
```

The product-facing interface must contain only typed, value-safe operations. It
must not expose generic `dict[str, object]` metadata or Langfuse trace objects.

## Integration Option Assessment

| Option | Product-code change | Coupling / leakage | Local overhead | Failure isolation | Testability | Incident usefulness | Removal cost | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| External adapter around synthetic workflow entrypoints | none initially | low with strict projection | low | high | high | high for KCS-14 rebaseline | very low | recommended first |
| Optional telemetry port with no-op | small adapter changes | low | low-medium | high | high | high after pilot | low | recommended later |
| Process/log ingestion | none | high; output can contain content and local refs | medium | medium | low | low/incomplete | low | reject |
| Explicit high-level stage spans | small targeted runtime changes | low through typed port | medium | high | high | high | low | defer until approved |
| Raw OpenTelemetry exporter | adapter-only | medium; implicit resources and attribute mapping require control | medium | high | high | medium | medium | defer; no existing OTel estate |
| OTel Collector | no core change | additional framework and configuration surface | high | high | medium | no current added value | medium | reject for initial experiment |
| Direct Langfuse SDK calls from workflow modules | medium | high vendor coupling | medium | medium | high | high | medium-high | reject |

## Control-Surface Identity Model

Every accepted synthetic Desktop run must record a value-safe identity record:

```text
source_commit
source_dirty_state
installed_mcpb_build_hash
registry_cache_ok
package_guidance_profile_id
tool_surface_profile_id
system_instruction_profile_id
system_prompt_state = current | stale | unknown
conversation_fresh
client_profile
model_profile
synthetic_user_prompt_fixture_id
synthetic_user_prompt_fixture_version
packet_schema_version
tool_instruction_profile_id
run_index
```

Rules:

- Profile IDs are repo-owned or operator-approved enums, never copied prompt
  text.
- Use `unknown` instead of guessing an unavailable model/client/profile value.
- A hidden system prompt cannot be hashed by the MCP server because the server
  does not receive it.
- If the profile is maintained outside the repository, the operator-controlled
  local profile supplies only a stable approved ID/version to the harness.
- Updating the system prompt requires a new conversation before a comparable
  run. An old conversation may retain stale context even after package files
  change.
- Package guidance identity, system-prompt identity, and deterministic
  tool-result instruction identity remain separate fields.

## Trace Model

One trace represents one bounded synthetic workflow execution.

```text
kcs.synthetic_desktop_run
|- control_surface.preflight
|- clean_ticket.register             (when required)
|- semantic_review.prepare           (when required)
|- semantic_review.submit            (when required)
|- candidate_inventory.observe
|- operator_selection.observe        (when required)
|- candidate_attempt.observe         (one per selected candidate)
`- workflow.complete
```

The initial trace records only metadata and classifications. It does not set
Langfuse input/output, generation prompt/completion, or automatic decorator
capture fields.

Recommended safe observations:

- run correlation hash generated from a random per-run nonce;
- fixed synthetic scenario ID/version and run index;
- workflow stage and canonical tool-name enum;
- ordered tool-call index;
- packet schema/profile version;
- `same_packet_as_baseline` boolean/unknown;
- `same_instruction_profile` boolean/unknown;
- candidate, selected-item, origin, and artifact counts;
- operator action kind;
- batch outcome and success/failure category;
- allowlisted blocker/debug code;
- retry count;
- duration in milliseconds or an approved duration bucket;
- safe deterministic check results and human review score enums;
- transport gap/timeout/disconnect classification.

## Data And Privacy Field Matrix

### Allowed By Default

- telemetry schema version;
- random run correlation hash that is not derived from a ticket or product ref;
- synthetic scenario ID/version;
- source commit/package/build hash for repo-owned artifacts;
- fixed runtime-surface, stage, tool, and operator-action enums;
- bounded integer counts;
- approved outcome, blocker, debug, and failure enums;
- duration and retry count;
- `registry_cache_ok` and other boolean preflight facts;
- `system_prompt_state` as `current`, `stale`, or `unknown`;
- allowlisted system/package/tool instruction profile IDs;
- allowlisted model/client profiles or `unknown`;
- `conversation_fresh`;
- `auto_publish_allowed=false` and `public_output_approved=false` when useful
  for a safety assertion.

### Allowed Only After Sanitization, Normalization, Hashing, Or Separate Approval

- deterministic tool-result instruction hash after replacing random refs,
  timestamps, and local paths;
- hash of a repo-public system-instruction profile;
- full synthetic input/output in a separate synthetic-only Langfuse project;
- HMAC-based private packet equivalence using a local untracked key;
- exception type mapped to a small failure enum;
- package release identifiers that contain no local path or user identity;
- exact model/client string mapped through an approved enum table.

The initial pilot exports booleans such as `same_packet_as_baseline` rather than
live packet digests. Cross-run HMAC correlation is deferred because it adds a
persistent correlation surface and requires explicit approval.

### Forbidden

- raw/private ticket text and clean-ticket content;
- selected excerpts, search text, chunks, snippets, vectors, or RAG content;
- system prompts, user prompts, prompt templates, or generated model prose;
- raw provider payloads, model responses, token streams, or tool arguments;
- full tool results, packets, candidate/article titles, or article content;
- reviewer packets, reviewer bundles, Markdown, HTML, or rendered artifacts;
- ticket, case, item, selection, semantic-review, handoff, customer, or thread
  identifiers;
- raw domains, URLs, IP addresses, hostnames, usernames, license IDs, or local
  filesystem paths;
- secrets, credentials, API keys, auth headers, cookies, or redaction maps;
- exception messages, tracebacks, log lines, process commands, environment
  dumps, or host/process OpenTelemetry resource attributes;
- Langfuse `input`, `output`, prompt, or completion fields for live workflows.

Client-side masking is defense in depth only. The strict projection must ensure
that forbidden data never reaches the SDK or OTLP exporter. Server-side masking
is not accepted as the primary boundary because it processes data after the
ingestion path has already received it.

## Docker Compose Deployment Plan

### Proposed Files

```text
ops/langfuse/compose.yaml
ops/langfuse/.env.example
ops/langfuse/README.md
```

The actual `ops/langfuse/.env` remains ignored and contains all credentials.
The Compose file should record the exact upstream source commit used for the
initial adaptation and pin reviewed image versions/digests.

### Services

- `langfuse-web`;
- `langfuse-worker`;
- PostgreSQL;
- ClickHouse;
- Redis;
- MinIO.
- a no-secret local TCP gateway that reuses the pinned `langfuse-web` image.

KCS is not a service in this Compose project. There is no `depends_on` or
shared lifecycle between Langfuse and authoring.

### Network And Ports

- publish only `127.0.0.1:3000:3000` from the local gateway for the web/API
  surface;
- do not publish worker, PostgreSQL, ClickHouse, Redis, or MinIO ports;
- do not publish MinIO media ports because the initial trace model has no
  media/input/output payloads;
- keep Langfuse web, worker, and all storage services on a dedicated internal
  network;
- allow only the no-secret, read-only gateway to join a second access bridge;
  the gateway forwards raw TCP only to fixed `langfuse-web:3000` and exists
  because Colima/Docker Engine 29 does not publish a port from an
  internal-only network;
- validate host access and denied container egress instead of assuming the
  Docker network configuration is sufficient;
- image pulls occur before the runtime egress-denial test and must not include
  KCS telemetry data.

### Security Configuration

- replace every upstream default secret;
- require secrets rather than providing insecure fallback values;
- set `TELEMETRY_ENABLED=false` on all Langfuse application containers;
- do not configure an Enterprise license, SMTP, OAuth, external LLM/provider
  connection, Cloud export, batch export, or sharing;
- disable signup after the initial local administrator is created, or use an
  approved headless initialization profile;
- keep credentials in the ignored `.env`, never in tracked Compose or docs;
- validate that the future KCS exporter accepts only an explicit loopback URL
  and never falls back to Langfuse Cloud.

### Health Checks

- web health with database availability required;
- web readiness endpoint;
- worker health endpoint;
- PostgreSQL, ClickHouse, Redis, and MinIO service checks;
- startup fails visibly when a required storage service is unhealthy.

### Resources

Initial constrained local profile:

- 4 CPUs;
- 10-12 GiB Docker memory;
- on-demand startup;
- at least 25 GiB free disk before image pull as a hard floor;
- at least 15 GiB free after pull/start as the running safety floor;
- 40-50 GiB free disk preferred;
- stop the experiment on sustained macOS memory pressure or low disk.

Record idle and one-synthetic-run CPU, memory, and volume consumption in the
deployment closeout. Do not increase Docker allocation silently if the initial
profile is insufficient.

### Startup, Shutdown, Upgrade, Backup, And Deletion

Startup:

```text
validate compose -> pull pinned images -> start detached -> wait for health ->
verify UI/auth/API -> record resources
```

Normal shutdown uses `docker compose down` without `-v`.

Persistence proof:

1. create a synthetic-only project and marker trace;
2. stop with `docker compose down`;
3. restart;
4. verify that project and trace remain;
5. verify that no new external destination was contacted.

Upgrade:

1. stop ingestion;
2. take a cold backup if retained data matters;
3. review upstream migration notes and the next exact image set;
4. update one pinned set in a reviewable diff;
5. start and rerun health, persistence, privacy, and egress checks.

The initial synthetic experiment is disposable. If retained evidence becomes
important, backup PostgreSQL, ClickHouse, and MinIO consistently before an
upgrade. Redis may be included in the cold snapshot for consistency even though
it is not the authoritative trace store.

Automatic OSS retention must not be assumed. Until a verified supported
retention feature exists for the selected edition/version, use a disposable
synthetic project and explicit project/volume deletion. `docker compose down
-v` is destructive and requires separate operator approval.

## Proposed Integration Boundary And Ownership

### Synthetic Rebaseline Slice

Candidate files, subject to review before creation:

```text
scripts/kcs14_langfuse_rebaseline.py
evals/kcs14_runtime_rebaseline_v1.jsonl
tests/kcs_adapters/test_kcs14_langfuse_rebaseline.py
docs/internal/engineering-process/tool-entrypoints.md
docs/internal/engineering-process/code-review-graph.json
docs/internal/engineering-process/module-boundaries.md
```

The scenario file contains only commit-safe synthetic cases and versioned
operator actions. Exact M1-M3 behavior must be defined before implementation;
the instrumentation must not invent those expectations.

Relevant ownership nodes:

- `smoke_log_tooling`: synthetic Desktop/MCP execution and value-safe run
  accounting;
- `packaging_and_install_tooling`: installed MCPB, registry cache, package
  guidance, and build identity;
- `engineering_policy_tests`: dependency, path, egress, and forbidden-content
  guards;
- `desktop_tool_surface`: later only, if root MCP tracing is approved;
- `desktop_draft_workflow`: later only, if stage tracing is approved.

The initial wrapper must not turn smoke tooling into an architecture decision
owner. It observes and classifies runs against a reviewed scenario/profile
contract.

### Later Optional Product Adapter

Candidate files only after separate approval:

```text
src/kcs_adapters/workflow_telemetry.py
src/kcs_adapters/langfuse_telemetry.py
tests/kcs_adapters/test_workflow_telemetry.py
tests/kcs_adapters/test_langfuse_telemetry.py
```

Potential narrow existing seams:

- `src/kcs_adapters/desktop_mcp_adapter.py` for one root workflow boundary;
- approved-summary pipeline hooks for explicit high-level stage observations;
- `src/kcs_adapters/mcp_desktop.py` only for optional configuration wiring.

Do not initially touch `desktop_draft_tool.py` or other retained KCS-14.5
control-surface files.
Do not touch `src/kcs_core`.

## Behavior And Failure-Mode Specification

### Normal Authoring

These states must produce identical business behavior:

```text
telemetry disabled
telemetry enabled and healthy
telemetry enabled and unavailable
telemetry enabled with wrong authentication
telemetry enabled and timing out
telemetry projection rejected
telemetry queue full
```

Only trace presence may differ.

Telemetry must not:

- change a decision, blocker, candidate count, selection state, readiness flag,
  returned schema, result text, exit code, or artifact;
- introduce a network wait on the workflow critical path;
- expose a stack trace or unsafe error message;
- add telemetry fields to MCP results or packet schemas;
- require a shutdown flush before returning a workflow result.

Unsafe telemetry input fails closed for telemetry: drop the event. Product
execution remains fail-open and continues.

Missing optional dependency, invalid configuration, or a non-loopback endpoint
selects the no-op sink. There is no fallback to a cloud endpoint.

### Synthetic Rebaseline

The synthetic harness may be stricter than ordinary authoring because it owns
evidence quality, not product decisions:

- stale/unknown control-surface identity produces
  `control_surface_identity_invalid`;
- such a run may be preserved as a non-comparable enum-only observation, but it
  cannot be counted as causal rebaseline evidence;
- Langfuse export failure does not change the underlying workflow result, but
  the run is marked `telemetry_export_unavailable` and is not accepted as proof
  that trace capture works;
- a timeout before any MCP call is classified as a client/transport gap, not a
  Python workflow failure;
- safety violations block the rebaseline gate regardless of majority behavior.

## Functional And Characterization Test Plan

### Deployment Tests

- Compose renders with no insecure default secret.
- Only loopback web/API is reachable from the host.
- Storage and worker ports are not exposed.
- Every service becomes healthy.
- UI login and authenticated API smoke pass.
- A marker trace survives normal shutdown/restart.
- OSS application telemetry is disabled.
- Runtime egress probe reports no unexpected destination.
- arm64 images run natively without emulation unless explicitly approved.
- Idle and synthetic-run resource use remain within the agreed profile.

### Projection And Privacy Tests

- Only declared fields and enums are accepted.
- Unknown keys, nested arbitrary mappings, strings in count fields, and
  unbounded labels are rejected.
- Ticket text, prompts, candidate titles, HTML, paths, URLs, domains, IPs,
  secrets, tracebacks, and tool arguments/results are rejected.
- Captured SDK/OTLP requests contain only the field allowlist.
- A synthetic canary is absent from Langfuse metadata unless full synthetic
  I/O was separately approved for the synthetic-only project.
- Credentials never appear in `repr`, error text, logs, or captured requests.
- Host/process/command OpenTelemetry resource attributes are absent.

### Control-Surface Identity Tests

- current profile plus fresh conversation is accepted;
- stale profile is classified and excluded from comparison;
- unknown profile is not silently treated as current;
- package hash mismatch and registry-cache mismatch invalidate the run;
- system, package, user-prompt fixture, and tool-result instruction identities
  remain separate;
- changing any identity prevents an `identical_run` classification;
- updating a profile requires a fresh-conversation marker.

### Failure-Isolation And Equivalence Tests

Run the same synthetic workflow with:

```text
no-op sink
fake successful sink
connection refused
authentication failure
timeout
SDK exception
queue full
bounded flush failure
```

Assert equality for:

- returned result and result kind;
- workflow state and blocker/debug codes;
- packet/tool schemas;
- candidate and selection behavior;
- reviewer-bundle hashes and write decisions;
- readiness/publication flags;
- CLI/MCP exit behavior;
- normal runtime latency budget.

### M1-M3 Rebaseline

- define exact synthetic inputs, system/package/tool instruction profile IDs,
  model/client profiles, and operator actions;
- run at least three times per scenario/profile as an initial descriptive
  sample;
- record all runs, not only the majority result;
- compare packet equivalence, candidate inventory, candidate origin counts,
  Python dispositions, operator action, outcome, and transport status;
- treat any selection bypass, freehand draft, unauthorized write,
  publication/privacy violation, or Python-validation bypass as a blocking
  failure;
- do not interpret a majority as a safety pass.

## Implementation Slices

### LF-0: Local Deployment Only

Deliverables:

```text
ops/langfuse/compose.yaml
ops/langfuse/.env.example
ops/langfuse/README.md
```

Scope:

- install/choose Docker runtime only after operator approval;
- deploy the six Langfuse services plus the local gateway independently;
- harden loopback, secrets, application telemetry, auth, and egress;
- verify health, UI/API, persistence, resource use, and cleanup procedure;
- create only a synthetic project/marker;
- no KCS code or Python dependency changes.

Stop after the deployment report and obtain review before LF-1.

### LF-1: External Synthetic Rebaseline Adapter

Scope:

- version M1-M3 synthetic scenarios and operator actions;
- define the control-surface identity profile contract;
- add the strict value-safe projection;
- use a pinned isolated Langfuse client only in the harness;
- keep automatic input/output capture disabled;
- run synthetic-only traces;
- demonstrate one useful comparison without product instrumentation.

Stop for privacy/usefulness review.

### LF-2: Isolated Optional Integration Adapter

Scope:

- add a typed telemetry port and no-op implementation;
- keep the default runtime dependency-free and disabled;
- add a lazy optional isolated Langfuse implementation;
- validate loopback endpoint, bounded queue/timeout, and safe projection;
- do not wire it into normal authoring yet.

Stop for architecture/failure-isolation review.

### LF-3: Limited Product Instrumentation

Scope, only after separate approval:

- one root observation around a bounded MCP workflow;
- explicit high-level stage observations only where existing seams allow them;
- safe counts, durations, outcomes, and blocker/debug enums;
- no core imports, automatic instrumentation, or content fields;
- no change to packet/tool/result schemas.

Stop for behavior-drift, privacy, and architecture review.

### LF-4: Validation And Closeout

- rerun enabled/disabled/unavailable/wrong-auth/slow cases;
- run privacy canary and captured-request scan;
- run focused and full characterization tests;
- verify byte/structure-equivalent product outputs and artifact hashes;
- update supported tool entrypoints, module boundaries, and review graph;
- perform deeper privacy/data-boundary/architecture review;
- document retained data, deletion, backup, and experiment removal;
- decide whether the experiment continues or is removed.

## Exact Stop/Go Criteria

### GO For LF-0

- Docker Desktop or another approved Docker/Compose runtime is selected and
  explicitly approved for installation/start;
- free disk is at least 25 GiB before image pull, with 40-50 GiB preferred;
- exact arm64-compatible images and versions/digests are reviewed;
- loopback/egress/auth/secrets configuration is reviewed;
- no KCS product file or Python dependency is included in the slice;
- a deployment-only closeout format is agreed.

### STOP LF-0

- image architecture requires unapproved emulation;
- disk headroom is below 25 GiB before image pull or below 15 GiB after
  pull/start;
- container egress cannot be tested or constrained;
- upstream default secrets remain;
- UI, storage, or MinIO is exposed beyond loopback/internal networking;
- persistence/deletion behavior is not understood.

### GO For LF-1

- LF-0 health, persistence, locality, auth, egress, and resource checks pass;
- exact M1-M3 synthetic scenarios are reviewed and versioned;
- system-prompt owner, profile ID/version, and current/stale/unknown semantics
  are approved;
- package/registry/tool-instruction identities are available;
- full synthetic I/O is either separately approved or remains disabled;
- captured-request privacy test passes;
- the work occurs in a clean, separate worktree/branch.

### STOP LF-1

- system-instruction identity is unknown for a run presented as comparable;
- the adapter needs raw Desktop logs, tool arguments/results, or ticket-derived
  content;
- an arbitrary metadata dictionary reaches the SDK;
- non-loopback/cloud endpoint fallback exists;
- trace capture changes the synthetic workflow outcome.

### GO For Product Instrumentation

- the synthetic adapter identifies a concrete divergence boundary or otherwise
  demonstrates useful incident-analysis value;
- control-surface identity makes comparable runs reproducible;
- telemetry disabled/healthy/failing equivalence tests pass;
- privacy canary and captured-request scans pass;
- normal authoring remains functional without the optional dependency;
- latency and failure-isolation budgets pass with Langfuse unavailable;
- all active runtime-incident changes are resolved or isolated in a clean
  worktree;
- the exact product instrumentation slice receives explicit operator approval.

### STOP Product Instrumentation

- product code must send raw prompts, packets, results, identifiers, paths, or
  model prose to be useful;
- instrumentation changes a schema, decision, state transition, output, write,
  readiness, or publication behavior;
- automatic instrumentation captures host/process/argument data;
- Langfuse or its SDK becomes required for authoring;
- retention/deletion is not defined;
- the experiment has not demonstrated enough value to justify the coupling.

## Open Operator Decisions

1. Which source was stale: Claude Project/system instructions, another Claude
   Desktop profile, Cowork skill guidance, or a different control surface?
2. Who owns the system-instruction profile and its version identifier?
3. May a repo-safe descriptor contain the prompt profile ID/version while the
   prompt text stays in ignored local configuration?
4. May the synthetic-only Langfuse project store full synthetic packet/output,
   or must LF-1 remain metadata-only?
5. Docker Desktop or another approved Docker/Compose runtime?
6. Proceed with approximately 27 GiB free, or first raise the reserve to
   40-50 GiB?
7. Use disposable OSS projects/manual deletion, or evaluate licensed automatic
   retention?
8. Is cross-run HMAC correlation for later live metadata justified, or should
   telemetry receive only equality booleans?
9. Use `spike/PAUX-7103-local-langfuse-observability` or the repository's
   standard `feature/` branch prefix?
10. What evidence threshold proves sufficient value to proceed beyond LF-1?

Recommended value threshold for question 10:

- at least one fixed synthetic comparison shows where two runs first diverge;
- zero forbidden-content findings;
- no product behavior or latency regression when Langfuse is unavailable;
- an operator can answer the incident question faster from the trace than from
  the existing value-safe run summary alone.

## Review Routing

LF-0 requires operations, privacy/local-boundary, and Compose review.

LF-1 and later slices require:

- diff sanity and unintended-file review;
- behavior and failure-mode review;
- privacy/data-boundary review;
- module ownership and review-graph update review;
- KCS-14 runtime incident compatibility review;
- deeper architecture/privacy review before any product instrumentation.

No slice may be described as behavior-preserving without explicit equivalence
evidence for disabled, healthy, and failing telemetry states.

## Closeout Requirements

Every completed slice reports:

1. changed files;
2. unchanged contracts;
3. validation run;
4. resource usage when applicable;
5. services, ports, networks, volumes, and security configuration;
6. retained data and cleanup commands;
7. open risks and deferred items;
8. the next explicit approval gate.

## LF-0 Closeout

LF-0 deployed Langfuse 3.212.0 locally through the tracked Compose topology in
`ops/langfuse/compose.yaml`. The deployment contains Langfuse web and worker,
PostgreSQL, ClickHouse, Redis, MinIO, and the no-secret loopback gateway.

Evidence:

- all seven services reached healthy state;
- health and readiness endpoints returned success;
- the UI was reachable only at `http://127.0.0.1:3000`;
- web, worker, and storage services had no host-published ports;
- application telemetry and batch export were disabled;
- external connection attempts from web and worker were blocked;
- one local organization, synthetic project, and local user were initialized;
- normal `down` followed by `up -d` preserved the initialized records;
- existing KCS tests passed while Langfuse was stopped, confirming that LF-0
  did not become an authoring dependency.

Resource evidence at closeout:

- approximately 2.0-2.45 GiB aggregate container memory;
- approximately 143 MiB persistent volume data after initialization;
- approximately 22 GiB host disk remained free, above the 15 GiB post-start
  stop floor but requiring monitoring before further image pulls.

Changed surfaces:

- local Compose operations and documentation only;
- populated `ops/langfuse/.env` remains ignored and was not copied into this
  branch;
- no `src/`, product package, Python dependency, packet, Desktop tool,
  selection, renderer, reviewer-bundle, readiness, privacy, or publication
  contract changed.

LF-0 permits LF-1 synthetic metadata-only evaluation. It does not authorize
LF-2, LF-3, real-ticket telemetry, automatic instrumentation, dashboards, or
product runtime coupling.

## 2026-07-28 Auxiliary Live Accounting Implementation Checkpoint

Status: source implementation, installed-package validation, and one bounded
Desktop attempt complete in the isolated
`feature/PAUX-7103-langfuse-live-run-accounting` worktree. The model-mediated
attempt stopped before the first MCP call, so no workflow trace was produced.

Implemented surfaces:

- strict typed live report and observation projection;
- optional env-created local JSON sink with atomic file replacement;
- bounded non-blocking background persistence queue;
- one central MCP dispatch hook around the five relevant workflow tools;
- external loopback-only Langfuse exporter using the already reviewed pinned
  SDK version;
- optional run-scoped Desktop-log classifier for the exact Claude Desktop Free
  quota category;
- privacy canaries, fail-open equivalence, batch accounting, real-SDK
  metadata-only capture, tool-liveness, ownership, and regression tests.

Preserved surfaces:

- packet, Desktop tool input/output, and provider schemas;
- semantic projection, candidate selection, reuse decisions, deterministic
  checks, rendering, reviewer bundles, readiness, and publication behavior;
- `auto_publish_allowed=false` and `public_output_approved=false`;
- the dependency-free product runtime;
- normal authoring when Langfuse, its SDK, local report configuration, or the
  local report directory is unavailable.

Validation evidence:

- full default suite: `1665 passed, 2 skipped`;
- pinned Langfuse 4.7.0 real-SDK metadata capture plus existing synthetic
  exporter suite: `60 passed`;
- Desktop adapter and stdio characterization subset: `218 passed`;
- engineering docs, review graph, tool entrypoints, and review protocol:
  `38 passed`;
- full `src tests scripts` Ruff check: passed;
- diff whitespace check: passed;
- touched integration complexity: maximum cyclomatic complexity `7`, with no
  function above the configured threshold;
- installed MCPB stdio smoke passed all 17 checks after the Node wrapper was
  corrected to forward the two optional accounting environment values;
- installed accounting smoke produced three schema-valid, hash-named reports
  containing nine observed transitions and no searched content canaries;
- Claude Desktop was restarted with local accounting enabled and the installed
  package loaded;
- the real `ticket-94893302` attempt produced no local report and no KCS MCP
  tool call; the contemporaneous Desktop web log recorded a generic completion
  `network error`, while the operator surface reported a usage limit;
- no live Langfuse project write was performed because the host had 14 GiB
  free, below the tracked 15 GiB post-start stop floor.

Interpretation limits:

- `transition_count` counts observed relevant MCP tool calls, not hidden model
  turns;
- `model_visible_bytes` is the serialized deterministic model-visible
  `content` projection at the accounting boundary, not `structuredContent`,
  the full hidden Desktop context, or an exact token count;
- the duration of `item.reuse_search_comparison` is a high-level tool-boundary
  duration, not a separately measured provider-only RAG duration;
- host quota classification requires a run-scoped log capture containing the
  allowlisted Claude Desktop Free marker;
- an operator-visible limit before the first MCP call cannot be classified from
  the accounting report because no run exists yet; a generic Desktop
  `network error` is not sufficient evidence to relabel it as
  `host_quota_exhausted`;
- a sudden process termination may leave the latest persisted checkpoint
  `in_progress`; the external classifier is the only component allowed to
  close it as `host_quota_exhausted`.

Ousterhout gate: reviewed

Trigger: new auxiliary module, persistence/failure boundary, cross-module
adapter hook, and external SDK integration.

Complexity hidden: exact allowlist projection, content-free report
serialization, atomic/background persistence, strict external validation,
loopback enforcement, and metadata-only Langfuse span creation.

Owner and what it must not know: `kcs_adapters` live accounting owns only
observation projection and must not know or decide KCS semantics, retain
workflow content, call Langfuse, or inspect Desktop logs. The external script
owns report validation/export and must not affect workflow execution.

Interface depth and caller cognitive load: the Desktop adapter has one optional
accounting collaborator and one post-dispatch call; normal callers configure
nothing. Operators enable two local environment values and export one exact
report through one documented command.

Information leakage and change amplification: the runtime-to-accounting edge
passes existing arguments/results only for immediate size/count projection;
neither is retained. Langfuse sees the closed report only. Adding a new safe
field requires coordinated dataclass, validator, exporter, and privacy-test
changes by design.

Complexity removed, moved, or added: the Langfuse SDK, auth, network, Desktop
log parsing, and host terminal classification stay outside product runtime.
Added source/script functions remain at or below the configured cyclomatic
complexity threshold.

Residual design risk: the stdio transport is currently sequential and the
accounting state intentionally models one active `/draft` per process. A future
concurrent transport would require an explicit safe correlation carrier before
this state holder could be reused. Background queue pressure may replace an
older checkpoint with a newer snapshot. The external exporter rejects more
than 200 observations, while the optional runtime checkpoint itself does not
truncate a pathological tool loop; adding runtime truncation requires a
separate accounting-schema decision rather than silently losing terminal
state. Pre-MCP host failures require an external, explicitly run-scoped attempt
envelope if they must become machine-classifiable; adding such an envelope is a
separate observability design decision, not a reason to expand the KCS runtime
workflow.

Verdict: pass
