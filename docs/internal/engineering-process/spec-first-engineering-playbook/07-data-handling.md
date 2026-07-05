# Spec-first Engineering Playbook: Data Handling

Data handling must be explicit before code changes begin.

## Allowed Data Classes

- Synthetic fixtures.
- Approved sanitized clean-ticket evidence.
- Validated packet metadata.
- Safe hashes and local bundle refs.
- Public support URLs when explicitly present in sanitized evidence.

## Forbidden Data Classes

- Raw Zendesk exports.
- Raw ticket comments.
- Internal notes.
- Customer identifiers.
- Credentials, tokens, keys, certificates.
- Private endpoints.
- Private local paths.
- Raw Rovo/internal output.
- Runtime reviewer bundles unless explicitly approved for local-only use.

## Hosted vs Local Boundary

Hosted agents may use only:

- sanitized fixtures;
- approved safe snapshots;
- explicitly provided public-safe examples.

Local-only artifacts must stay local unless the operator approves a safe export.

## Slice: KCS reviewer packet generation

Reviewer packets may contain:

- safe ticket refs;
- candidate refs;
- action names;
- evidence summaries;
- blocker codes;
- validation flags;
- safe public support article URLs;
- bundle refs and hashes.

Reviewer packets must not contain:

- raw ticket text;
- raw transcript blocks;
- raw internal output;
- credentials;
- private paths;
- unapproved article body content.

If provenance is unclear, the packet must say so and fail closed.
