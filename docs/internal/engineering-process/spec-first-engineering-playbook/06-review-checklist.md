# Spec-first Engineering Playbook: Review Checklist

Use this checklist for code, docs, contracts, and demo artifacts.

## General Review

- Does the diff match the stated slice?
- Are unrelated files untouched?
- Are generated/runtime/private artifacts excluded?
- Are contracts preserved or intentionally changed?
- Are tests added or updated where behavior changed?
- Does README or related documentation need an update?
- Does the change avoid unsupported version, model, command, or API claims?

## Review Severity

Classify findings as blockers or warnings.

Blockers:

- behavior regression;
- broken or unstable contract;
- missing test or fixture for changed behavior;
- unsafe data handling or unsafe input echo;
- raw/private/runtime artifact touch;
- README or docs claim that contradicts actual behavior;
- architecture drift that moves decisions out of deterministic Python code.

Warnings:

- naming/import cleanup;
- small documentation clarity issue;
- low-risk test gap with a clear follow-up;
- maintainability concern that does not change current behavior.

## Privacy Review

- No raw ticket bodies.
- No raw internal comments.
- No credentials, tokens, private endpoints, or private paths.
- No unapproved customer identifiers.
- No unsafe input echo in errors, logs, packets, or test fixtures.

## Runtime Review

- Does Python remain the deterministic owner?
- Does the slice fail closed?
- Are publish-safety flags explicit?
- Are unknown states blocked or reported?
- Are runtime payloads machine-stable?

## AI Boundary Review

- Did AI invent behavior outside the spec?
- Is any LLM output treated as untrusted input?
- Is semantic review bounded to candidate identification?
- Are KCS decisions made by code, not by the model?

## Documentation Review

- Does README remain accurate?
- Do docs describe implemented behavior, not desired future behavior?
- Are future slices labeled as future work?
- Are public/reviewer output claims consistent with `auto_publish_allowed=false`
  and reviewer-only boundaries?
- Are local-only process notes kept under `local-docs/`?

## Slice: KCS reviewer packet generation

- Does the packet satisfy acceptance criteria?
- Does it preserve the privacy boundary?
- Does it fail closed?
- Does it avoid unsafe input echo?
- Is output schema stable?
- Are happy and forbidden paths tested?
- Does the packet avoid overstating reuse/search?
- Does it clearly state reviewer-only status?
