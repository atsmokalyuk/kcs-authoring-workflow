# Engineering Playbook

This directory contains generic engineering templates, checklists, and the
KCS-16 DDD catalog input for the later KCS-17 handoff. It is tracked so agents
and reviewers can use the same process artifacts from a fresh clone.

This is not an assembled or released Engineering Kit package. KCS-16 extracted
only independently eligible generic DDD rules into
[`ddd-universal-core.json`](ddd-universal-core.json) and retained every other
universal-core entry as non-authoritative advisory metadata. KCS-17 export
assembly, compatibility testing, role assignment, orchestration, integration
testing, and packaging remain separate and unstarted.

Only catalog entries with `authoritative=true` and
`kit_treatment=authoritative-extracted-beta` are rule authority. Field-evidence
candidates, standards-backed shadow entries, and reference-only entries must
not be loaded or presented as authoritative DDD rules.

Generic playbook files must not duplicate KCS-specific runtime, privacy,
publication, or packet-contract rules. They should reference project contract
documents under `docs/internal/` and project-specific planning decisions under
`docs/internal/engineering-process/`.
