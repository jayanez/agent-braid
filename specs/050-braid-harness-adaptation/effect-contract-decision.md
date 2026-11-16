# SPEC-050 T004: E3/E4 effect-contract decision packet (2026-11-16)

Status: prepared for the owner, not decided. Nothing here adopts a contract, changes
containment, or grants anything; `executionAuthorization` stays false.

## Why a decision is needed

T004 (`agent_braid/harness_tools.py`) is partial. The offline part merged in #1272:
allowlisted tool contracts, typed inputs and outputs, a positive read inventory, private
`out/` writes, a bounded runner, a mandatory independent checker, and teardown (E0–E2).
The acceptance also asks for **bounded subprocess and network effects**. The contract
(`contracts/interface.md` §8, row C5) blocks them until two things exist:

1. a SPEC-048/T008 verdict, and
2. an **adopted E3 effect contract**.

The owner decisions of 2026-11-13 (D2) keep that block. This packet prepares item 2.

| Level | Meaning | Today |
|---|---|---|
| E0–E2 | inert text, bounded reads, writes to a private destination | offline, admitted (ADR 0027) |
| E3 | child process or deterministic helper execution | blocked |
| E4 | network or provider/model session | blocked (admission, zero-spend route, quota gate) |

## What is fixed in every option

- E4 stays blocked. A helper never opens a network connection or a model session. Native
  model sessions stay with the SPEC-048/049 cohort paths and their own gates.
- A helper only runs **inside the SPEC-065 qualified containment** (the dedicated `braidlab`
  user, deny-default `sandbox-exec`, exec allow-list NC-8, rlimits). It never runs in the
  operator account and never from an MCP tool.
- Helpers are pinned by SHA-256, root-owned, and never registered globally (§9 exclusion).
- Every helper run has a timeout, CPU/RSS/disk caps, writes only to its private `out/`, and
  is graded by a distinct checker, as in the offline runner.

### Environment detail

The containment allows exec only for literal, allow-listed paths. A compile probe proves that
`/usr/bin/false` is denied, and the 2026-11-16 T008 run reported `exec-denied` for 71 of 71
non-listed paths. Adding a helper means adding its path and hash to that allow-list. The
allow-list is part of the qualified profile, so **any E3 adoption that actually runs a helper
needs a SPEC-065 re-qualification.** The standing rule FD-20261114-STANDING (valid until HAR.1
closes or 2027-01-31) can make that re-qualification light: the change must be reviewed code
with a security re-check GO, and the attempt must come out 32/32 with all 4 effects enforced,
Δ0 quota and no new residuals.

Example: a `diff`-style comparison helper at `/usr/local/libexec/braid/helpers/cmp-<hash>`.
Under option B it is written into the contract, but no `braidlab` run may exec it until a
re-qualified profile lists it. Under option C it is listed in the profile now, and the next
re-qualification attempt carries it.

## Options

### A. No E3 in this release: close T004 with an explicit scope limit

T004 closes as "offline E0–E2 only; E3/E4 not adopted", and C5 stays blocked in the capability
report and in the HAR.3 closure scope.

- Pros: no containment change and no extra re-qualification, so the critical path
  (065 → 048 T008 → 049 T004/T014) stays untouched.
- Cons: subprocess helpers are not operational. "All HAR features operational" then excludes C5.
- Undo: reopen through a later versioned amendment (option B or C).

### B. Adopt the E3 contract now, qualify after T014 (Recommended)

Write and adopt the E3 contract now: allow-list by hash, caps, timeout, no network, private
`out/`, a distinct checker, and refusal codes. Implement the subprocess adapter in
`harness_tools.py` and test it against deterministic doubles only. After the T014 cohort has
run, a separate SPEC-065 re-qualification adds the pinned helpers to the exec allow-list. It is
light if the standing rule applies. After that, one contained helper run is the T004 evidence.

- Pros: the critical path is not touched (no profile change before T014). The code and contract
  are ready, and C5 can become operational before the release.
- Cons: one more re-qualification and an owner `run` after T014. If it slips past 2027-01-31,
  the standing rule no longer applies and the full process does.
- Undo: withdraw the adoption record before the re-qualification. Nothing native will have
  depended on it.

### C. Adopt now and batch the helper allow-list into the re-qualification already pending

A re-qualification is already coming: branch `fix/065-claude-system-events` edits
`harness_host_claude.py`, an environment-hash input. Add the pinned helpers to the same attempt.

- Pros: a single re-qualification for both changes. C5 is operational earliest.
- Cons: it enlarges a re-qualification that sits on the critical path. A failing helper probe
  would delay T008 and T014. It also needs agreement with the session that owns the native chain.
- Undo: hard once issued. Removing helpers needs another re-qualification.

## Recommendation

**B.** It keeps native risk off the critical path, keeps C5 achievable for this release, and
lets the standing rule make the extra re-qualification cheap. C saves one re-qualification but
puts the cohort deadline at risk. A is the fallback if T014 comes out negative or inconclusive
(D7 would close the harness as experimental anyway).

## After the decision

- The orchestrator records the answer verbatim in `owner-decisions-<date>.md`.
- For B or C: amend `contracts/interface.md` §8 (C5 row) and §7 (E3 row) through a versioned
  amendment. The offline-adapter PR follows, and the containment change is coordinated with
  the native-chain session.
- For A: update `capability-report.md` and the T004 entry, and record the limit for the HAR.3
  closure.
