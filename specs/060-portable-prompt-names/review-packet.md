# SPEC-060 T001: owner review packet

Prepared for the owner's review of the portable MCP prompt names contract
(`agent-braid-tooling/v0.2`). This file records no decision, creates no review
record, ticks no task and does not freeze anything. It is a reading aid.

## 1. What to read, in order

1. [contracts/interface-delta.md](contracts/interface-delta.md): the object under
   review. The prompt table (section 2), the capabilities resource (3), the
   deprecated-alias exception and removal criterion (4), the plugin facade (5) and
   compatibility, migration and rollback (6).
2. [../../docs/adr/0031-portable-prompt-names.md](../../docs/adr/0031-portable-prompt-names.md):
   the decision, alternatives and consequences, and the bounded exception to the
   ADR 0030 alias rule.
3. [release-notes-0.1.0a2.md](release-notes-0.1.0a2.md): what a user of the
   portable server would be told, including the deprecation and removal contract.
   These notes are prepared text, not published.
4. [evidence/release-readiness.md](evidence/release-readiness.md): versions,
   changed and unchanged surfaces, migration and rollback fixtures, and the explicit
   "Not verified" list. Read with [evidence/pr-profile-result.md](evidence/pr-profile-result.md)
   for the three failures that also fail on clean `develop`.
5. Optional: [spec.md](spec.md) (REQ-001 to REQ-011),
   [plan.md](plan.md#human-review-and-unresolved-decisions) and
   [tasks.md](tasks.md).

## 2. Decisions OD-1 to OD-8, as already decided

All were decided by the owner on 2026-10-25 and are recorded in plan.md and
spec.md. They are listed here so the review can confirm them, not reopen them
unless the owner chooses to.

| ID | Recorded decision |
|---|---|
| OD-1 | Scope B: version the surface only. `envelopeSchemaVersion` stays `agent-braid-tooling/v0.1`; tool envelopes, output schemas and provenance are unchanged. |
| OD-2 | Alias window of 2 releases, removal in `agent-braid-tooling/v0.3`, owner re-decision if 180 days pass without the second release. |
| OD-3 | Carrier is Python package `0.1.0a2`; no plugin release and no plugin schema bump. |
| OD-4 | Aliases are listed in `prompts/list` and marked deprecated (not hidden). |
| OD-5 | Document not registering the portable server under key `agent-braid` next to the plugin, and observe the collision in T009; no installer change. |
| OD-6 | SPEC-054 files stay untouched; SPEC-060 points to them. |
| OD-7 | Number SPEC-060 (not 055). ADR 0031. |
| OD-8 | ADR 0031 Accepted; T002-T008 authorized; T009 observation, T010 release decision, tagging and publication remain separate owner decisions. |

## 3. Implemented, inferred and unobserved

Implemented and merged into `develop` (verified with `gh pr view`):

- #746 specification and ADR 0031 (docs).
- #752 T002-T006: canonical and alias prompts, surface-version constant,
  capabilities `envelopeSchemaVersion` and `deprecatedPrompts`, plugin facade
  stripping, regression of telemetry, install, hosts and the System One verifier.
- #750 T007: English documentation.
- #754 T008, T010: release preparation for `0.1.0a2`, migration and rollback
  fixtures, v0.2 verifier, release notes and readiness record.

Inferred, not observed:

- Claude Code listing the prompts as `/agent-braid:analyze (MCP)` rests on the
  SPEC-054 documentation research; the display of the new names has not been seen.
- That a portable server under the key `agent-braid` next to the native plugin
  produces a confusable `/agent-braid:analyze` pair is inferred from naming rules.
- Codex listing no MCP prompts rests on the cited upstream status, not on a test of
  this candidate.
- The migration and rollback fixtures reduce the candidate registry to the v0.1
  roster. They do not install an earlier wheel.

Unobserved or pending:

- T009 native observation in Claude Code (alone and next to the plugin) and the
  Codex record is pending and needs an owner-run or separately authorized session.
- Package `0.1.0a2` is NOT published: no tag, wheel, sdist, upload or GitHub
  release. No wheel was built (no `setuptools` or `build` in the evaluation
  environment) and the verifiers were not run against an installed wheel.
- The native plugin was not rebuilt and stays `0.1.0-alpha.4`.
- The release channel for portable users is not established by the repository.
- Local `--profile pr` exited 1 at `full-tests` on three process-group tests that
  also fail on clean `develop` in that environment; the stages after `full-tests`
  did not run locally. GitHub CI was green on the head before the record.
- T011 (alias removal under `v0.3`) is deferred by design: it needs T010, two
  published window releases and a separate owner removal decision.
- T001 itself (this review) is open.

## 4. Questions for the owner

1. Verdict on the contract delta and ADR 0031: accept, or changes-requested (name
   the sections)?
2. Confirm OD-1 to OD-8 as recorded, or name any to reopen. Is the exception to the
   no-duplicate-invocation rule acceptable as bounded (portable prompts only,
   never tools, skills, resources, the plugin or the server key)?
3. Is a window counted in releases (2) with a 180-day owner re-decision the right
   removal contract, given that prompt use is unmeasured and cannot be a criterion?
4. Is the key-collision handling (document, observe in T009, no installer change)
   adequate if T009 shows the portable prompt and the plugin skill can be confused?
   What outcome of T009 would change the answer?
5. Should the release channel for the portable package be decided before T010, or
   is that left to the release decision?
6. Should the three pre-existing `test_git_counterexamples` failures be tracked
   separately before a release decision?

## 5. What an acceptance does and does not authorize

An acceptance of T001 would confirm that the specification, contract delta and
ADR 0031 are adequate for REQ-001, REQ-002 and REQ-007 (SC-001, SC-002, SC-007).
It would not:

- release, tag, build for distribution or publish package `0.1.0a2`, or rebuild
  the native plugin;
- replace T009 native observation or the separate release decision;
- authorize T011 alias removal or extend the alias window;
- change tool names, envelopes, resource URIs, the plugin, the installer default
  key or any SPEC-054 file;
- make any scientific claim; the work is engineering only and changes no effects,
  authority, analysis results or evidence.

Approval would bind the exact commit reviewed; any later change to the contract or
ADR needs a new review. Ticking T001, freezing and recording the review happen
later, from a clean merged candidate, and are not done by this packet.
