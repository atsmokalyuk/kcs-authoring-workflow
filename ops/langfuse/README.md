# Local Langfuse Operations

This Compose project runs Langfuse independently of KCS. It contains no KCS
service, product dependency, ticket data, or runtime instrumentation.

## Prerequisites

- Apple Silicon macOS;
- Colima, Docker CLI, and Docker Compose;
- at least 25 GiB free disk before pulling images; 40-50 GiB preferred;
- 4 Colima CPUs and 12 GiB memory for the initial local evaluation.

The deployment uses Langfuse `v3.212.0`. All six image references are pinned to
the linux/arm64 manifest digests verified on 2026-07-13. Upgrade the set only
after reviewing current Langfuse migration notes and rerunning the complete
deployment validation.

## Local Secrets

Copy `.env.example` to `.env`, then populate every empty secret locally. Use
URL-safe random values because the PostgreSQL password is embedded in an
internal connection URL. Recommended forms:

```bash
openssl rand -hex 32
```

Requirements:

- `ENCRYPTION_KEY` is exactly 64 hexadecimal characters;
- project API keys use local values with `lf_pk_` and `lf_sk_` prefixes;
- `.env` is ignored and must never be committed or pasted into review output;
- the initialization email is the reserved local value
  `operator@localhost.invalid`, not a real operator address.

## Commands

The Homebrew Compose installation is available as the standalone
`docker-compose` command. Run commands from the repository root:

```bash
PATH="/opt/homebrew/bin:$PATH" docker-compose \
  --env-file ops/langfuse/.env \
  -f ops/langfuse/compose.yaml config

PATH="/opt/homebrew/bin:$PATH" docker-compose \
  --env-file ops/langfuse/.env \
  -f ops/langfuse/compose.yaml up -d

PATH="/opt/homebrew/bin:$PATH" docker-compose \
  --env-file ops/langfuse/.env \
  -f ops/langfuse/compose.yaml ps

PATH="/opt/homebrew/bin:$PATH" docker-compose \
  --env-file ops/langfuse/.env \
  -f ops/langfuse/compose.yaml down
```

Normal shutdown does not use `-v`; named volumes must survive restart.

`docker-compose down -v` deletes all local Langfuse data and requires explicit
operator approval.

## Exposure And Egress

- UI/API: `http://127.0.0.1:3000` only;
- worker and storage services: internal Docker network only;
- Langfuse application telemetry: disabled on web and worker;
- signup: disabled after headless initialization;
- SMTP, OAuth, Enterprise features, external model providers, sharing, and
  batch export: not configured;
- internal MinIO media storage is configured because it is part of the
  Langfuse topology, but LF-0 sends no media or content payloads;
- Langfuse web, worker, and storage network: Docker-internal with no Internet
  egress;
- localhost gateway: a no-secret, read-only TCP forwarder using the same
  digest-pinned Langfuse image; it alone joins the access bridge and publishes
  `127.0.0.1:3000` because Colima cannot publish directly from an internal-only
  network;
- the gateway forwards only to the fixed internal `langfuse-web:3000`
  destination and is subject to an explicit egress validation.

Image pulls require Internet access before containers start. No KCS telemetry
or workflow data exists during LF-0.

## Health And Persistence

Validate:

```text
GET http://127.0.0.1:3000/api/public/health?failIfDatabaseUnavailable=true
GET http://127.0.0.1:3000/api/public/ready
```

The worker health endpoint is checked inside its container. Compose health also
covers PostgreSQL, ClickHouse, Redis, and MinIO.

Persistence proof:

1. create or verify the headless synthetic project;
2. add only a synthetic marker trace after LF-1 is approved;
3. run normal `down`, then `up -d`;
4. verify project and credentials remain;
5. do not ingest real KCS data during LF-0.

## Backup, Upgrade, And Retention

The LF-0 synthetic deployment is disposable and has no required backup. If
later traces become important, take a consistent cold backup of PostgreSQL,
ClickHouse, and MinIO before upgrades; include Redis in the stopped snapshot
for operational consistency.

Do not assume automatic retention in the selected OSS deployment. Use a
disposable synthetic project and explicit project or volume deletion until a
reviewed retention mechanism is approved.
