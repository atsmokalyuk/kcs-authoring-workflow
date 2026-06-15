# KCS Authoring MVP - Jira Tracking

## Purpose
This page links the product and architecture documents to the Jira implementation work.

## Parent Work Item
- Parent PAUX: [PAUX-7083 - Implement KCS Core Pipeline Prototype for KCS Authoring MVP](https://webpros.atlassian.net/browse/PAUX-7083)

## Implementation Subtasks
- KCS-0 Data handling baseline and implementation scope
- KCS-1 Core packet contracts and fixtures
- KCS-2 Safety and evidence validation gates
- KCS-3 KCS action decision engine
- KCS-4 Reviewer packet renderer and Zendesk HTML output
- KCS-5 Validation report and ready_for_reviewer loop state
- KCS-6 CLI entrypoint for local verification
- KCS-7 Evidence package builder from approved fixtures/exported tickets
- KCS-8 Zendesk read-only ingest adapter; requires adapter readiness checks before approved ticket use
- KCS-9 Claude Enterprise/Desktop bounded handoff; requires client integration readiness before pilot use
  - KCS-9a Semantic KCS item identification from approved sanitized context
  - KCS-9b Bounded reviewer-assist handoff contract from compact safe packets
- KCS-9c Reviewer-only draft generation from validated handoff packets
- KCS-10 Local reviewer bundle writer for deterministic audit/debug artifacts
- KCS-11 Live Claude provider adapter for real provider smoke tests
- KCS-12 Claude Desktop MCP validator/control adapter and MCPB package
- KCS-13 Pilot with approved tickets and reviewer feedback
- KCS-14 / future: intranet remote MCP service deployment for managed operator
  use, connected from Claude Desktop through a custom remote connector URL
  rather than the local MCPB stdio wrapper

## Source Documents
- Product brief: [KCS Authoring MVP - Goal and Success Criteria](https://webpros.atlassian.net/wiki/spaces/~atsmokalyuk/pages/6687424547/KCS+Authoring+MVP+-+Goal+and+Success+Criteria)
- Data handling baseline: [KCS Authoring MVP - Data Handling Baseline](https://webpros.atlassian.net/wiki/spaces/~atsmokalyuk/pages/6684377098/KCS+Authoring+MVP+-+Data+Handling+Baseline)
- Architecture and contracts: [KCS Core Pipeline - Architecture and Contracts](https://webpros.atlassian.net/wiki/spaces/~atsmokalyuk/pages/6683918381/KCS+Core+Pipeline+-+Architecture+and+Contracts)
- Technical design: `docs/internal/kcs-core-pipeline-technical-design.md`
- Feature engineering approach: `docs/internal/kcs-authoring-mvp-feature-engineering.md`

## Rule
Confluence pages define product goal, data handling, and architecture. Jira tracks execution, subtasks, PR scope, and acceptance criteria.
