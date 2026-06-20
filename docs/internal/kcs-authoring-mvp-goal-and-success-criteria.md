# KCS Authoring MVP - Goal and Success Criteria

Status note, 2026-06-20: this file records the original MVP product goal and
success criteria. The current implementation has moved beyond a minimal MVP
into the KCS Authoring Workflow: a production-shaped local workflow with
clean-ticket registration, `ticket_ref` drafting, compact MCP output, and local
reviewer bundles. Enterprise/PAUX rollout is postponed. The MVP criteria remain
the historical baseline and safety floor, not the ceiling for current
functionality.

## Purpose
The KCS Authoring MVP is part of the [AI Toolkit](https://webpros.atlassian.net/wiki/spaces/~vzhidkov/pages/6547308551/AI+Toolkit+for+ZenDesk) initiative. Its goal is to help support engineers turn solved support cases into reviewer-ready KCS outputs faster, with less mental effort, and without introducing unsafe automation.
This MVP focuses on the KCS workflow after or near ticket resolution: deciding whether knowledge should be reused, updated, created, flagged, or skipped.

## Product Goal
The KCS Authoring MVP should reduce the effort required for support engineers to prepare useful KCS output from solved tickets.
The goal is not only to save time. The goal is also to reduce the cognitive load of KCS work: engineers should not need to manually reconstruct the whole ticket history, search context, article fit, article structure, and quality rules from scratch every time.
The MVP should guide the engineer toward a clear KCS outcome:
- reuse an existing article;
- update an existing article;
- create a new article candidate;
- flag an article for improvement;
- split the case into several KCS candidates;
- decide that no article is needed;
- stop because evidence is insufficient or unsafe.
The final decision remains with the support engineer, KCS reviewer, or publisher.

## Why This Matters
KCS work often happens at the end of complex support work, when the engineer has already spent significant effort on investigation, troubleshooting, and customer communication.
If KCS authoring requires too much additional mental effort, it is easy to skip, postpone, or produce inconsistent output.
This MVP should make KCS work easier to complete during normal support flow by presenting the engineer with:
- the likely KCS action;
- the evidence behind the recommendation;
- existing article reuse/update opportunities;
- blockers and risks;
- reviewer-ready draft or update content.

## Alignment With AI Toolkit
This MVP supports the broader AI Toolkit goal: helping support engineers during day-to-day ticket work.
It specifically addresses the KCS update part of the support workflow:
- finding relevant existing knowledge;
- deciding whether a ticket adds reusable knowledge;
- preparing article candidates or update suggestions;
- reducing repetitive formatting and quality-check work;
- supporting reviewer and publisher decisions with structured evidence.

## MVP Success Criteria
The MVP is successful if a support engineer can start from approved/sanitized ticket evidence and receive a clear reviewer-ready KCS result.
A successful result should answer:
- What KCS action is recommended?
- Why is this action recommended?
- Which existing article, if any, should be reused or updated?
- What evidence supports the recommendation?
- What blockers or risks remain?
- What content is ready for reviewer evaluation?

## Product Success Signals

### Faster KCS preparation
Engineers can produce reviewer-ready KCS output faster than by manually writing and checking the article/update from scratch.

### Lower cognitive load
Engineers receive a structured recommendation instead of having to independently reconstruct the KCS decision path from the full ticket.

### Better consistency
KCS outputs follow the same decision logic, article structure, and quality expectations across different engineers and tickets.

### Safer workflow
The MVP does not expose raw ticket data unnecessarily and does not publish or update Zendesk/Help Center automatically.

### Human control
The system recommends, drafts, and validates. The engineer or reviewer still approves, changes, rejects, or publishes.

## Cost / Value Principle
The MVP should prove practical support value with the smallest reliable implementation.
Preferred approach:
- start with approved/sanitized fixtures;
- use read-only integrations only when needed;
- avoid custom hosting in the first slice;
- keep the workflow narrow;
- focus on reducing engineer effort and improving KCS consistency.

## Target Outcome
The target outcome is that an engineer can say:

> “The assistant helped me understand what KCS action is needed, showed the evidence and blockers, and gave me reviewer-ready content without forcing me to rebuild the whole ticket context manually.”
