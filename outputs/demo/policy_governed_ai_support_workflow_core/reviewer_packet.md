 # Reviewer Packet: candidate-001

Packet status: showcase artifact, reviewer-only, no Zendesk write.

Recommended action: `flag_existing`
KCS readiness: ready for reviewer, not auto-publishable
Reuse status: explicit existing-article reference detected in clean-ticket evidence.
Live reuse/RAG search: not connected for this demo.
Online URL verification: not performed.
Source ticket: `ticket-94893302`
Existing public KB article: https://support.plesk.com/hc/en-us/articles/115001678209
Reviewer bundle: `~/Documents/KCS Authoring/local-data/reviewer-bundles/run-20260624T153244-eEJzhajb/candidate-001/reviewer_only.html`

## Why this output exists

The workflow found a reusable KCS item for an Apache startup failure caused by a missing or empty `SSLCACertificateFile` reference in Plesk-generated Apache configuration. The clean-ticket evidence and semantic candidate referenced an existing public KB article for the same `PPPM-5892` issue, so the Python workflow converted that explicit reference into a rule-based reuse match. The selected workflow action is `flag_existing`; the reviewer can then decide whether the existing article needs an update instead of creating a duplicate.

The output remains reviewer-only. Python owns the final action decision, validation state, bundle writing, and publish-safety flags. The AI-assisted step was limited to identifying candidate KCS items from the noisy clean ticket.

For this showcase run, reuse handling was based on explicit-reference detection rather than live RAG search. No online article verification or Claude web search was performed during this run.

Content provenance:

1. Python loaded the local clean-ticket text for `ticket-94893302`.
2. Python prepared bounded clean-ticket excerpts for semantic review.
3. Claude used only those bounded excerpts to identify KCS item candidates and returned `candidate_semantic_extraction_v1`.
4. Python validated that extraction, selected `candidate-001`, detected the explicit KB article reference, and chose `flag_existing`.
5. Python rendered `reviewer_only.html` from the accepted candidate evidence.
6. The SCR content below was summarized from that `reviewer_only.html`.

The existing KB article body was not fetched, read, or used as a source for this SCR content.

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
- https://support.plesk.com/hc/en-us/articles/115001678209

Flag reason:

The existing public article appears to cover the same issue identity. A new article would risk duplication. The reviewer should use the generated bundle to check whether the existing article needs coverage improvements for:

- the `plesk repair web` failure path;
- `SSLCACertificateFile` errors in webmail configuration files;
- the specific Apache configuration-generation failure evidence.

## Validation results

- Semantic review fallback completed.
- Candidate selection completed.
- Python selected `flag_existing`.
- Explicit existing-article reference was detected.
- Live reuse/RAG search performed: false.
- Online URL verification performed: false.
- Reviewer bundle was written.
- `kcs_ready=true`.
- `ready_for_reviewer=true`.
- `auto_publish_allowed=false`.
- `public_output_approved=false`.
- Zendesk write performed: false.

## Related candidates

Candidate `candidate-002`: Websites broken after network configuration change on Plesk server with DHCP-assigned IP

- Recommended action: `draft_only`
- Reuse search: skipped
- KCS readiness: not ready
- Reviewer bundle written: true
- Ready for KCS review: false
- Reviewer bundle: `~/Documents/KCS Authoring/local-data/reviewer-bundles/run-20260624T153246-2hJ-tUwC/candidate-002/reviewer_only.html`
- Note: draft exists for reviewer exploration, but it is not KCS-ready until reuse search and reviewer checks are completed.

Candidate `candidate-003`: Let's Encrypt timeout due to IPv6 firewall filtering ports 80 and 443

- Recommended action: blocked
- Blocker: `approved_summary_resolution_steps_incomplete`
- Required next step: add operator-confirmed resolution detail.
- Bundle written: false
- Note: the clean ticket identifies the likely cause, but the excerpts do not contain exact operator-confirmed firewall tool or command steps.

## Risks and manual review

- This packet is not public output and must not be published automatically.
- A reviewer must verify that the existing article is still the correct reuse target.
- A reviewer must confirm whether the generated flag notes represent article gaps or ticket-specific detail that should remain reviewer-only.
- Candidate `candidate-002` must not be treated as ready until reuse search is completed.
- Candidate `candidate-003` needs operator-confirmed firewall procedure details before a standalone draft can be generated.
