# SPEC-068 owner authorization — alpha.7 publication, 2026-11-04

The owner (jayanez, founder) gave these decisions interactively in chat with the
coordinator session on 2026-11-04 (earlier ones on 2026-11-03). They are recorded here as
the owner's decisions relayed by the coordinator; the session transcript is not stored in
the repository, and the short Spanish phrases are quoted from the coordinator's relay.
This is an authorization and decision record for the publication of plugin
`0.1.0-alpha.7`. It is not a scientific finding, a human usability rating or an
independent technical review.

| # | Date | Decision | Effect |
| --- | --- | --- | --- |
| 1 | 2026-11-03 | ADR 0037 accepted (D14) | Status recorded in #1030 |
| 2 | 2026-11-03 | Conditional authorization (D16): T010 without contradiction, green CI, a final explicit owner yes | Conditions listed in the readiness record |
| 3 | 2026-11-04 | Leave `install.sh --host all` and `--host opencode` behaviour as is until alpha.7 is published | Resolved by the publication |
| 4 | 2026-11-04 | Run runbook step 9 (T010 row 21 as a post-publication smoke) | Row 21 observed after publication |
| 5 | 2026-11-04 | Publish with T010 rows 22 (Linux) and 23 (session `_meta` identifier) as declared limits | Listed under "Not observed" in the release record |
| 6 | 2026-11-04 | F2 and F3 fixed in #1030; F1 later (issue #1080, known limit in the notes) | F1 stays a known limit |
| 7 | 2026-11-04 | Final decision on publishing: "Sí, publicar" | Build and publication from `0eb75d84` |
| 8 | 2026-11-04 | `plugin-dist` root README diff: "Aprobado" | Hand-edited README in `8f19b1b7` |
| 9 | 2026-11-04 | Tag and push: "Sí, push y tag" | Annotated tag `agent-braid--v0.1.0-alpha.7`, pushed without force |

## Authorization table (as filled in the readiness record)

| Field | Value |
| --- | --- |
| Decision | Publish `0.1.0-alpha.7` ("Sí, publicar") |
| Date | 2026-11-04 |
| Source commit authorized | `0eb75d84b6ad5cbe156b5d0c4ff967833f416205` |
| T010 interactive rows reviewed, contradictions found | Rows 01-13 and 15-20 observed (owner ran 16-20 interactively); row 14 contradicted the observed candidate and was fixed in #1030 (`96f30b7c`, not re-observed); row 21 observed after publication; rows 22-23 unobserved and accepted as declared limits |
| CI result on the release PR | `validate` aggregate green on head `4405c898` |
| Scope | `plugin-dist` commit `8f19b1b7`, annotated tag `agent-braid--v0.1.0-alpha.7`, record PR |
| Excluded | native host acceptance, official directory submissions, any further release, any scientific claim |

## Limits

- The authorization covers publication of this plugin version only. It does not approve
  native host acceptance in Claude Code or Codex, an official directory submission, any
  further release or any scientific claim.
- Native host observation of alpha.7 in Claude Code and Codex is not part of this record.
- Real-use telemetry and transcripts were not consulted for this record. It cites no field
  use of alpha.7.
