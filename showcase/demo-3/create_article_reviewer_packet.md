# Reviewer Packet: candidate-001

Recommended action: `flag_existing`
KCS readiness: ready for reviewer, not auto-publishable
Reuse search: checked
Source ticket: `ticket-94893302`
Reviewer bundle: `~/Documents/KCS Authoring/local-data/reviewer-bundles/run-20260624T153244-eEJzhajb/candidate-001/reviewer_only.html`

## Why this output exists

The workflow found a reusable KCS item for an Apache startup failure caused by a missing or empty `SSLCACertificateFile` reference in Plesk-generated Apache configuration. Reuse search matched an existing public article, so the correct action is to flag or update the existing article instead of creating a duplicate.

The output remains reviewer-only. Python owns the final action decision, validation state, bundle writing, and publish-safety flags. The AI-assisted step was limited to identifying candidate KCS items from the noisy clean ticket.

## Evidence basis

Title:

Apache fails to start with SSLCACertificateFile does not exist or is empty error in Plesk

Applicable to:

- Plesk for Linux

Symptoms:

- Apache fails to start with an `AH00526` syntax error in Plesk-generated Apache configuration.
- The error references `SSLCACertificateFile` under `/usr/local/psa/var/certificates/`, where the file does not exist or is empty.
- All websites show the default Apache page.
- `plesk repair web` fails during web server reconfiguration.
- Apache configuration generation fails with a `Template_Exception` from the Plesk webserver template writer.

Supported cause:

Plesk bug `PPPM-5892` causes broken Apache configuration files that reference a missing or empty SSL CA certificate file.

Resolution evidence:

- Confirm Apache service failure with `systemctl status httpd`.
- Check Apache configuration syntax with `/usr/local/psa/admin/bin/apache-config -t`.
- Verify the referenced certificate file is missing or empty under `/usr/local/psa/var/certificates/`.
- Apply the existing public article guidance for `PPPM-5892`.
- Run `plesk repair web` after applying the fix.
- Start Apache and verify service status.

## Existing article / flag reason

Selected existing article:

- `kb-115001678209`

Flag reason:

The existing public article appears to cover the same issue identity. A new article would risk duplication. The reviewer should use the generated bundle to check whether the existing article needs coverage improvements for:

- the `plesk repair web` failure path;
- `SSLCACertificateFile` errors in webmail configuration files;
- the specific Apache configuration-generation failure evidence.

## Validation results

- Semantic review fallback completed.
- Candidate selection completed.
- Python selected `flag_existing`.
- Reuse search was checked.
- Reviewer bundle was written.
- `kcs_ready=true`.
- `ready_for_reviewer=true`.
- `auto_publish_allowed=false`.
- `public_output_approved=false`.

## Related candidates

Candidate `candidate-002`: Websites broken after network configuration change on Plesk server with DHCP-assigned IP

- Recommended action: `draft_only`
- Reuse search: skipped
- KCS readiness: not ready
- Reviewer bundle: `~/Documents/KCS Authoring/local-data/reviewer-bundles/run-20260624T153246-2hJ-tUwC/candidate-002/reviewer_only.html`
- Note: draft exists for reviewer exploration, but it is not KCS-ready until reuse search and reviewer checks are completed.

Candidate `candidate-003`: Let's Encrypt timeout due to IPv6 firewall filtering ports 80 and 443

- Recommended action: blocked
- Blocker: `approved_summary_resolution_steps_incomplete`
- Bundle written: false
- Note: the clean ticket identifies the likely cause, but the excerpts do not contain exact operator-confirmed firewall tool or command steps.

## Risks and manual review

- This packet is not public output and must not be published automatically.
- A reviewer must verify that the existing article is still the correct reuse target.
- A reviewer must confirm whether the generated flag notes represent article gaps or ticket-specific detail that should remain reviewer-only.
- Candidate `candidate-002` must not be treated as ready until reuse search is completed.
- Candidate `candidate-003` needs operator-confirmed firewall procedure details before a standalone draft can be generated.
