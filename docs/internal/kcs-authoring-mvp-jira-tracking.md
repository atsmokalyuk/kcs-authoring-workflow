# KCS Authoring MVP - Jira Tracking

## Purpose
This page links the product and architecture documents to the Jira implementation work.

## Parent Work Items

- Historical parent PAUX: [PAUX-7083 - Implement KCS Core Pipeline Prototype for KCS Authoring MVP](https://webpros.atlassian.net/browse/PAUX-7083)
  owns the completed KCS-0..KCS-13 local pipeline/prototype history.
- Current hardening umbrella: PAUX-7103, pending/subject to external tracker
  confirmation, owns KCS-14 engineering and codebase design hardening.

External Jira and Confluence records require operator or maintainer action.
When external rollout is postponed, this repository records the local mapping
instead of implying that external tracking was updated.

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
- KCS-13 Controlled semantic review fallback for complex/noisy approved clean
  tickets
- KCS-14 Engineering and Codebase Design Hardening: documentation ownership,
  spec-first process baseline, local tool entrypoints, functional test
  conventions, compact review protocol, minimal code map, behavior-preserving
  codebase refactor, and review/agent tooling after the manual protocol is
  stable
- KCS-15 KCS Authoring Quality through source style/markup parity, Article
  Quality criteria, KCS practices, approved examples, assisted reuse, and
  portable `plesk_support` rules; active through independently approved
  behavior slices and remains outside KCS-14 scope
  - KCS-15.1 PLESK_INFO trigger parity: complete
  - KCS-15.2 RAG-assisted reuse
    - KCS-15.2a Local Public RAG Adapter: complete; loopback readiness and
      metadata-only candidate retrieval only
    - KCS-15.2b1 Bounded Public Comparison Evidence: complete;
      provider-neutral contract, common acceptance gate, and local
      `/api/snippets` projection only
    - KCS-15.2b2 Operator-Confirmed Comparison Workflow: Phase A exact
      public-article context is complete and the deterministic local
      controlled-comparison implementation is committed; operational closeout
      remains open because the approved sanitized super-noisy canary reaches
      all five comparison decisions in current-source replay. The reviewed
      correction is committed, installed, reloaded, and passes
      installed-wrapper/runtime preflights; the final installed Desktop
      super-noisy canary and separate `none_fit` authoring-quality gates remain
      open. Phase C in-chat UI is host-blocked and deferred pending a
      host-owned direct launcher
    - KCS-15.2b3 Repeated Comparison Trial: planned after b2 with a separately
      approved fixture/trial contract
  - KCS-15.3 Deterministic structure/title/entrypoint/safety/naming parity:
    planned, independently approvable from KCS-15.2b
  - KCS-15.4 Approved examples and bounded model-mediated quality trials:
    planned after its fixtures and trial contract are approved
- Future deployment slice: intranet remote MCP service deployment for managed operator
  use, connected from Claude Desktop through a custom remote connector URL
  rather than the local MCPB stdio wrapper

## Source Documents
- Product brief: [KCS Authoring MVP - Goal and Success Criteria](https://webpros.atlassian.net/wiki/spaces/~atsmokalyuk/pages/6687424547/KCS+Authoring+MVP+-+Goal+and+Success+Criteria)
- Data handling baseline: [KCS Authoring MVP - Data Handling Baseline](https://webpros.atlassian.net/wiki/spaces/~atsmokalyuk/pages/6684377098/KCS+Authoring+MVP+-+Data+Handling+Baseline)
- Architecture and contracts: [KCS Core Pipeline - Architecture and Contracts](https://webpros.atlassian.net/wiki/spaces/~atsmokalyuk/pages/6683918381/KCS+Core+Pipeline+-+Architecture+and+Contracts)
- Technical design: `docs/internal/kcs-core-pipeline-technical-design.md`
- Feature engineering approach: `docs/internal/kcs-authoring-mvp-feature-engineering.md`
- KCS-14 planning decisions:
  `docs/internal/engineering-process/kcs-14-planning-decisions.md`

## Rule
Confluence pages define product goal, data handling, and architecture. Jira tracks execution, subtasks, PR scope, and acceptance criteria.
