# KCS Post-Pilot Deployment Notes

Status: post-pilot consideration / deferred planning

## Purpose

Record a possible post-pilot deployment and user-experience direction without
changing the current KCS implementation roadmap.

This note is not an MVP commitment and does not move browser UI, packaging,
deployment, or Claude handoff work into the active KCS-4 or KCS-5 slices.

## Stable Governed Core

After pilot, the KCS core pipeline should remain stable, versioned, and
governed. Engineers should not need to modify core logic for daily use.

The controlled core includes:

- safety checks;
- evidence validation;
- deterministic decision logic;
- renderer rules;
- public/internal separation;
- operator override rules;
- `auto_publish_allowed=false`;
- approved JSON contracts.

Changes to this layer should go through the normal corporate review process and
contract/versioning rules.

## Customizable Input And Output Layers

Engineers may customize adapter and UI layers around the approved core
contracts, not the core safety or decision logic.

Examples of customizable layers:

- input preparation forms;
- Zendesk import adapter;
- local browser viewer;
- reviewer packet display;
- Zendesk HTML preview;
- copy/paste helpers;
- personal layout or display preferences;
- local workflow shortcuts.

These layers should consume and produce approved packet contracts, such as
`KcsReviewerPacket` JSON, instead of changing safety gates, evidence readiness,
decision rules, renderer rules, or publication invariants.

## Local Browser Viewer

A local browser viewer may be useful after pilot as a debugging and inspection
workflow improvement. It is not the default production review surface while
Claude chat can show the reviewer output directly.

Possible model:

- the pipeline produces `KcsReviewerPacket` JSON;
- a local viewer reads the JSON;
- the browser shows recommended action, reviewer notes, evidence basis,
  warnings, metadata, and Zendesk HTML preview;
- the engineer reviews and copy/pastes output without manually browsing output
  files.

This is not KCS-4 scope unless explicitly approved later. KCS-4 remains the
reviewer packet renderer and Zendesk HTML copy/paste artifact slice.
The current roadmap keeps the browser view behind the local bundle writer and
live Claude provider smoke tests. Implement it only if real ticket or pilot
review shows that Claude chat output is not enough for efficient debugging.

## Packaging And Code Protection

Locally running Python code cannot be truly encrypted as a strong protection
boundary. Practical deployment controls can reduce accidental modification and
make rollout easier, but they do not provide strong IP or security isolation.

Possible practical controls:

- internal versioned Python package;
- private package registry;
- signed release artifact;
- compiled or obfuscated distribution;
- checksums and version validation;
- controlled release process.

These controls may be useful after pilot, but they are not part of the current
MVP implementation scope.

## Stronger Future Control Model

If stronger control over core logic is required later, the better model is to
run the KCS core as an internal service or API.

In that model:

- core code stays server-side;
- engineers use only approved UI/API surfaces;
- adapter and display layers remain outside the governed core;
- release and access controls are enforced centrally.

This is a future option, not current MVP scope.

## Out Of Scope For Current KCS-4/KCS-5

This note does not change the current implementation roadmap.

Out of scope for current KCS-4/KCS-5:

- packaging or obfuscation implementation;
- browser viewer implementation;
- internal service/API deployment;
- engineer plugin or customization framework;
- Claude handoff changes;
- Zendesk write or publish integration.

Current roadmap boundaries remain unchanged:

- KCS-4: reviewer packet renderer and Zendesk HTML copy/paste artifact;
- KCS-5: validation report / ready-for-reviewer loop state;
- KCS-7: evidence package builder and extraction contract work;
- KCS-9: bounded Claude-assisted extraction/handoff if approved and
  smoke-testable.

## Future Intranet Remote MCP Option

The local Claude Desktop MCPB package is the development and local smoke path.
It starts a stdio MCP server from a local repository checkout through `uv`.

A later managed operator path can instead expose the same safe
validator/control tool facade through an internal remote MCP service:

```text
Claude Desktop
  -> custom remote MCP connector URL
  -> approved intranet MCP endpoint
  -> deployed KCS adapter/service
  -> deterministic KCS core packets and validators
```

This would remove the requirement for every operator machine to have a local
repository checkout and local `uv` runtime. It also moves auth, ACLs, audit,
health checks, deployment packaging, and network routing into a governed
service slice.

This is not part of the current local MCPB implementation and should not change
KCS core ownership: code still decides, validators still block, Claude output
remains untrusted, and no Zendesk writes, Help Center publication, customer
replies, or auto-publish are introduced by the transport.

## PM Summary

Post-pilot direction: keep the KCS core stable, versioned, and governed; allow
engineers to customize input/output experience around approved JSON contracts.
Local packaging can reduce accidental modification but is not a strong
encryption boundary. If stronger control is needed later, move the core behind
an internal service/API or approved intranet remote MCP service.
