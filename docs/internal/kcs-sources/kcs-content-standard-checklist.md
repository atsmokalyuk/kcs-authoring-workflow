# The KCS Content Standard Checklist

Status: reviewable Markdown snapshot; the canonical Confluence page is the
source of truth.

- Canonical source:
  <https://webpros.atlassian.net/wiki/spaces/CX/pages/5375295653/The+KCS+Content+Standard+Checklist>
- Source role: normative public-content, privacy, naming, and safety checklist.
- Captured: 2026-07-22 from the operator-provided export.
- Export filename: `The+KCS+Content+Standard+Checklist.doc` (not tracked).
- Export SHA-256:
  `2a4372d1cc5168d24695f25e22472817ad08bc5177c203d3dd8687c4da528886`.

When this snapshot and the canonical page differ, use the canonical page and
refresh this file before changing runtime behavior.

## Introduction

KCS articles are visible to the general public. Their content must follow the
strict GDPR standard used by WebPros.

## Sanitization

The following data must not appear in KCS articles and must be replaced with
safe examples.

| Information | Use instead |
| --- | --- |
| Passwords | `password` |
| Local IPv4 address | `192.0.2.2` |
| Public IPv4 address | `203.0.113.2` |
| IPv6 address | `2001:db8:f61:a1ff:0:0:0:80` |
| Server hostname in shell output | `[root@vz ~]#`, or a generic hostname appropriate to the service, such as `ns` or `sql` |
| Email address | `john.doe@example.com` |
| Domain or live-environment URL | `example.com`, `example.net`, or `example.org` |
| Subdomain | `one.example.com` or `two.example.com` |
| DNS record | The same safe IP/domain examples |
| Personal name | `John Doe` |
| Telephone number | `+00000000` |
| Plesk license number | `PLSK.01234567.0000` |
| Extension license number | `EXT.01234567.0000` |
| Container ID | `101` |
| Virtual-machine name | `test_vm` |

## Product names

Represent product and feature names correctly for branding, trademark, and
legal accuracy. Verify the current spelling when it is uncertain.

## Additional checks

- Do not include content that presents WebPros brands negatively.
- Do not include commands that can reveal sensitive information.
- Include rollback steps for important server changes when a rollback is
  available, using the applicable style triggers.
- Use the Plesk Style Triggers reference for Plesk articles:
  <https://support.plesk.com/hc/en-us/articles/12378148057495-KCS-Style-triggers>.
- Put a downtime warning before actions that may make a service unavailable.
- In database-related titles and bodies, use `MySQL/MariaDB` instead of only
  `MySQL`.
- If the article is specifically about MySQL Community Server, use the exact
  name `MySQL Community Server`.
