# Demo 3 Showcase Packet

This folder contains a sanitized public-safe showcase packet for the KCS
Authoring workflow core.

Demo 3 is the primary showcase because it demonstrates controlled workflow
behavior on a noisy multi-issue clean ticket:

- `candidate-001`: `flag_existing` because an existing public KB article is the likely reuse target.
- `candidate-002`: `draft_only` because reuse search was skipped.
- `candidate-003`: blocked because operator-confirmed resolution details are incomplete.

The packet is reviewer-only. It is not Help Center content, not a Zendesk write,
not an auto-publication request, and not a customer reply.

## Files

| File | Purpose |
| --- | --- |
| `PROJECT_WALKTHROUGH.md` | End-to-end project walkthrough for reviewers |
| `KCS_Authoring_Workflow_Walkthrough.pdf` | PDF walkthrough export |
| `KCS_Authoring_Workflow_Walkthrough_clean.pdf` | Clean PDF walkthrough export |
| `reviewer_packet.md` | Human-readable reviewer packet |
| `reviewer_packet.json` | Structured packet artifact |
| `preview.html` | Sanitized reviewer-only preview for the primary candidate |
| `architecture.mmd` | Mermaid architecture diagram source |
| `kcs-authoring-architecture-diagram.pdf` | Architecture diagram and caption |
| `kcs-authoring-architecture-diagram.png` | Rendered architecture diagram preview |
| `create_article_reviewer_packet.md` | Earlier create-article reviewer packet snapshot |
| `create_article_reviewer_packet.json` | Earlier create-article structured packet snapshot |

## Data Boundary

The internal demo flow can use approved sanitized real tickets. Public showcase
material uses synthetic or anonymized ticket references only.

Use public examples such as:

```text
/draft ticket-1234567
```

Do not add real ticket IDs, customer domains, hostnames, emails, operator names,
private paths, internal URLs, customer-identifying timestamps, raw ticket text,
or raw internal/Rovo context to this folder.
