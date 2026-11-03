# SPEC-046 owner authorization — alpha.6 publication, 2026-11-03

The owner (jayanez, founder) gave these decisions interactively in the Claude Code
coordinator session on 2026-11-03. They are summarised here from the coordinator's
decision note; the session transcript is not stored in the repository. This is an
authorization and decision record for the publication of plugin `0.1.0-alpha.6`. It is
not a scientific finding, a human usability rating or an independent technical review.

| # | Decision | Effect |
| --- | --- | --- |
| 1 | GitHub tracking: apply only the closed task issues for SPEC-046 T020/T021 and SPEC-047 T011/T012 (sub-issues of their parents, with the spec milestone mapping) and the text updates of SPEC-046 T018 and SPEC-047 T010; no other audit operation | Issues #1007, #1008, #1009 and #1010 created and closed; #699 and #607 text updated |
| 2 | Release PR for alpha.6: squash-merge without asking again if the full local suite shows no new failures against develop and CI is green | PR #1006 merged as `ce40f2b6` |
| 3 | Publish `0.1.0-alpha.6` unattended: build from a clean develop, commit `dist: Agent Braid 0.1.0-alpha.6 (source <sha>)` on `plugin-dist`, create annotated tag `agent-braid--v0.1.0-alpha.6` and push; abort on any hash or doctor failure | `plugin-dist` commit `78cc45a3`, tag object `6dac9956` |
| 4 | Record PR with the release record, evidence file and updated published pins, keeping alpha.5 as rollback target, with this authorization note; merge when green. Then update the plugin on the host, reconnect `/mcp` and verify `plugin-status` `pluginVersion` | This record; the host update and verification are not part of it |

## Limits

- The authorization covers publication of this plugin version only. It does not
  approve native host acceptance, an official directory submission, T014/T015
  candidacy work, any scientific claim, or any further release.
- Native host observation of alpha.6 is pending. The host update and the
  `pluginVersion` check are performed afterwards by the coordinator and are recorded
  separately.
- Real-use telemetry and transcripts were not consulted for this record. It cites no
  field use of alpha.6.
