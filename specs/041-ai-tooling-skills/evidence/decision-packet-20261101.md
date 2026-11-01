<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Decision packet: guided real use for deferred SPEC-041 and SPEC-043 tasks

**Date:** 2026-11-01. **Status:** input to an owner decision. This packet reopens,
ticks or closes nothing. Reopening a deferred task needs a new owner decision. The
"Observed against criterion" column records observations, not acceptance.

## What was run

On 2026-11-01 the owner chose to generate guided real use. The use ran in one Claude
Code conversation, split into a parent session and a fork. The fork existed only because
the host did not list the runtime tools again after the registry changed. The plugin
package was `0.1.0-alpha.4` (`candidateVersion 0.1.0a1`, Claude Code `2.1.309`).

- **Workspace.** The work used a throwaway Git repository that the owner owns. The owner
  selected the setup preview (`b6ae1f21…`, runtime enabled, separate grant store), and it
  was registered from that preview. The other registered workspaces were not used.
  Telemetry consent stayed `local`, unchanged.
- **Authority.** The owner issued all five grants in their own terminal. The model issued
  none and received only grant ids. The plugin exposes no tool that issues grants.
- **Interruptions.** Interruptions and expired grants were produced on purpose in the
  scratch repository. They are real runtime transitions, not fixtures.

## Receipts

| File | Content |
|---|---|
| [`guided-journey-20261101.json`](guided-journey-20261101.json) | the two sessions' extractor events (the same as the 043 journeys for those hashes), **reviewer annotations** (`observation` fields, read from the tool results, not extractor output), operator actions, CLI steps and telemetry day rows |
| [`observational-receipts-20261101.json`](observational-receipts-20261101.json) | refreshed C1/C2/C3 scan of every source (same extractor, sha256 `738e1168…`) |
| [`../../043-ai-tooling-journey/evidence/observational-journeys-20261101.json`](../../043-ai-tooling-journey/evidence/observational-journeys-20261101.json) | refreshed per-session journeys |

Sources consulted, per [REAL_USE_EVIDENCE.md](../../../docs/development/REAL_USE_EVIDENCE.md):

| Source | Result |
|---|---|
| Claude Code transcripts | 2,929 files scanned, 670 with Agent Braid events; this journey is in sessions `ad5e6e3b4b96` and `c265b8060198` |
| Codex sessions | skills listed in context in 8 sessions; no use; nothing new since 2026-10-31 |
| SPEC-047 telemetry (`telemetry report`, bundled CLI) | 2026-11-01 MCP calls: `analyze-work` 2 ok / 1 refused, `prepare` 1 ok, `execute` 1 ok / 2 refused, `status` 3 ok, `verify` 2 ok / 1 refused, `recover` 1 ok / 1 refused. No CLI rows that day: the read-only `analyze-git` fallback ran with telemetry off, its default. The `verify` refused while the server was busy does not appear |
| Evidence, coordination, identity stores | present; last modified on or before 2026-10-17; 2 unreadable files in the evidence store; not usage of this journey |
| Runtime state | 3 files from 2026-10-14/15; not usage |
| Plugin registry and results | 4 workspaces; 36 result files, all from 2026-11-01 |

## Mapping against the reopen criteria

Reopen criteria are from the
[2026-10-31 owner decision](../../044-ai-tooling-evaluation/owner-decision-20261031-m45-closure.md).

| Task | Reopen criterion | Observed against criterion (not a decision) | Basis and limits |
|---|---|---|---|
| SPEC-041 T001 | all five skills loaded at recorded versions, per `procedure_portable_bundle` | **partly observed** | in Claude Code, `analyze`, `plan`, `execute`, `recover` and `evidence` loaded at `0.1.0-alpha.4`, each with a content digest. The procedure also requires both hosts and an unavailable counterpart. Codex only listed the skills and never loaded them, and the listings carry no version |
| SPEC-041 T003 | one session with `plan`, `prepare`, disclosed order and missing authority | **criterion observed** | session `ad5e…`: `plan` skill, then MCP `prepare` ok with a verified plan. The session disclosed the order (wave `[a,b]`, serial publication a→b) and the missing operator grant. The disclosure text is in the transcript and is not committed |
| SPEC-041 T004 | C1–C3 `execute` on a granted exact batch, with a refusal for a wrong or expired grant | **criterion observed** | an unissued grant was refused before any run was allocated. An owner grant ran to `verified-completed`, and the independent `verify` succeeded. Reusing the consumed grant was refused. The expired 1-second grant was refused through the bundled CLI, not MCP |
| SPEC-041 T005 | C1–C3 for an interrupted or mismatched run, with a refusal counterpart | **criterion observed** | a real interrupted run reached `verified-prefix` with 0 operations done. MCP `recover` (resume, new owner grant) brought it to `verified-completed`, and `verify` succeeded. `recover` on a completed run with a consumed grant was refused |
| SPEC-041 T006 | C1–C3 for verified, failed and inconclusive records | **partly observed** | the verified record was read with hash checks and exported. A run killed before allocation reported `no-private-run` with its history not established; it was read, hash-checked and exported. Treating it as the inconclusive case is an interpretation for the owner. Refused records were explained as text, and their export was refused. No runtime *failed* record was produced; refusal is not failure |
| SPEC-041 T007 | a missing-capability session with a read-only fallback | **criterion observed** | the `execute` skill was loaded while MCP `execute` was not advertised. It refused, and the documented read-only `analyze-git` CLI was used instead |
| SPEC-041 T008 | untrusted text asking for grants, secrets or false success, refused deterministically | **partly observed** | a committed file asked for a grant, secrets, a wider root and a false success. Analysis treated it as data and repeated nothing. Only one deterministic refusal was recorded: the tool refused the wider root as outside the configured source root. The grant, secret and false-success requests were declined by the model, which is not deterministic. The model issued no grant and claimed no false success. Claude Code only |
| SPEC-041 T009, T010 | T004–T008 closed, then candidate freeze, gates and a decision | **not observed** | no frozen candidate is bound to this evidence |
| SPEC-043 T001 | one session (or an owned synthetic journey) covering install, analysis, plan, grant refusal, execute, verify, recovery and export | **partly observed** | analysis, plan, grant refusal, execute, verify, recovery and export were all observed. They span a parent session and its fork in one conversation. Install itself was earlier; this journey shows only setup and registration. The owner decides whether the fork counts as one session and whether setup with registration stands in for install |
| SPEC-043 T003 | plan with `prepare`, order and exact missing authority explained, then execution refused | **observed across the parent and fork** | `plan` and `prepare` in `ad5e…`. The refused execution without a grant is in fork `c265…`. A refusal without MCP `execute` is also in `ad5e…`, but it came before the plan. Same one-session question as T001 |
| SPEC-043 T008 | both hosts: onboarding, diagnostics, raw-evidence access, rendering fallback | **not observed** | Claude Code showed setup, the `plugin-status` and `workspaces` diagnostics, raw-evidence resources and the formatter's refusal on incomplete results. No host rendering fallback was observed. **Codex not observed; pending the owner** |
| SPEC-043 T009, T010 | T001–T008 closed, then gates, freeze and decision | **not observed** | depends on T008 and a frozen candidate |

## Boundaries

This is observational evidence of real use, not a preregistered evaluation. There is
one owner, one host and one scratch repository, and the order of steps was guided. It
supports no comparison, utility or speed-up claim. It is not bound to a frozen
candidate. It establishes no clean-room reproduction, registered cohort, human
evaluation or founder acceptance. Counts are deduplicated by tool-use id. Two `verify`
refusals were caller errors (concurrent admission, malformed plan copy), and they are
recorded as returned.
