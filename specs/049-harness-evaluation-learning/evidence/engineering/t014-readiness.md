# SPEC-049 T014 readiness: native cohort, real arm C, library ablation (arm D)

Status: engineering assessment, 2026-11-16, base `5e963a31` (origin/develop). Nothing native ran; no record
here admits, authorizes or freezes anything (`executionAuthorization` false). Issue #1306.

## Verdict

**The native T014 cohort cannot run on the T008 path. It needs its own driver, workload builder, root launcher,
installer and sudoers rule, plus three owner decisions.** None of that exists yet. The offline arm-C path is
ready and reproducible. Arm D has no path, offline or native, and does not fit the D2 unit cap.

Upstream state on 2026-11-16 (HAR orchestrator): SPEC-048 T008 has **0 units left** (`t008-20261114c` used the
last one: `completed=False`, breach `paid-route`), so T008 needs a new founder decision before any T004
admission. The 2026-11-14 issuance becomes void when `fix/065-claude-system-events` merges; after the
re-qualification the T014 deadline is **30 days after the new issuance**, not 2026-12-14. Every date and pin
below that names the 2026-11-14 issuance moves to the new one. The native build and runs belong to the
native-chain session; this document is its hand-over.

| Piece | State |
| --- | --- |
| Offline arm C (contrastive proposer, R13 double) | Ready: 14 tests pass; `python3 -m tests.harness_t014_arm_c` reproduces signals `continued-past-drift`, `repeated-completed-steps` and arm-C candidate `6674a8da7aab284f456a9cefd551ebddbb6546873a809ad6a3db48fedca1f7d9` (resume-only guidance) |
| Offline arm D | Missing: `harness_evaluation.ARMS` is A/B/C and registration fixes `"library": "excluded"` |
| Native driver for case units | Missing |
| Native launcher / install | Missing: the T008 launcher cannot be reused (below) |
| SPEC-049/T004 admission record | Missing (owner) |
| T014 cohort terms and arm-C freeze | Missing (owner) |

## Why the T008 path does not carry T014

1. **Fixed workload.** `harness_hosts_native.unit_inputs` builds one hard-wired read-only unit
   (`UNIT_TASK`, one note, `guidance/main.md`, verifier `none-v1`). It has no case task, no arm guidance file,
   no oracle. T014 needs one manifest per (case, arm) carrying that arm's `guidance/checkpoint.md`, the case's
   visible task, its checkpoint/drift context, and the frozen `FixtureOracle`.
2. **No grading bridge.** `har_t008_unit.py` settles quota and containment only; nothing turns a native session
   into a `harness_verification.commit` + `verify_unit` row for `harness_evaluation.evaluate`.
3. **The launcher is bound to T008.** `scripts/har_t008_launch.sh` (frozen) hard-codes the driver path
   `repo-<short>/scripts/har_t008_unit.py`, the label `t008-YYYYMMDDx`, the publish directory
   `/Users/Shared/braid-t008-lab/`, and the driver caps the whole cohort at 4 units under the SPEC-048 founder
   record `founder-decisions-20261114.json`. The installed sudoers rule names only that launcher.
4. **Read-only host.** `harness_host_claude.ALLOWED_TOOLS` is `Glob, Grep, Read`; `Write`/`Edit`/`Bash` are
   denied. A native unit cannot write `out/result.txt`. The result must be taken from the final assistant
   message (the host stream records it as a `message` event) and graded in-process; only the verdict is
   published, never the text.

What *can* be reused unchanged: the qualified lab (braidlab `Background` session, `claude-2.1.292`, token file,
2026-11-14 issuance), `har_t009_attempt.preflight`, the `admit` checks pattern of `har_t008_unit.py`,
`harness_hosts_native.run_native_unit` (it takes any manifest/context), `HostQualificationRun` as the D2 gate,
`NativeClaudeTransport`, and the T005 units, rubric and oracles.

## Hard constraint: do not touch the qualification inputs

An issuance (the 2026-11-14 one expires 2026-12-14T18:42:10Z; its successor 30 days after issue) holds only
while these bytes stay unchanged:
environment-hash components `harness_containment_macos.py`, `harness_lab.py`, `harness_host_claude.py`,
`harness_transport_claude.py`, `harness_quota.py`, and the MDRV-04 guarded modules `harness_manifest.py`,
`harness_context.py`, `harness_observation.py`, `system_one.py`. New files under `scripts/` and a new module
under `agent_braid/` do not enter the hash. Any edit to the nine files above voids the issuance and forces a
SPEC-065 re-qualification. The re-qualification already pending for `fix/065-claude-system-events` is the
only window to change them (for example the unit cap); after that issuance they are frozen again.

Consequence: the D2 unit cap of 16 is enforced in `harness_quota.MAX_UNITS` and `harness_hosts.D2Caps`
(construction refuses any other value). **Raising the cap needs a founder decision plus a code change inside the
pending re-qualification**; once the new issuance exists it voids it again.

## Unit budget under D2 (at most 16 native units, 30 min each, EUR 0)

| Plan | Native units | Fits 16 |
| --- | --- | --- |
| Native arm-C round (`maxProbes` 4) + 5 holdout × A/B/C | 4 + 15 = 19 | No |
| P1: native arm-C round + 4 holdout × A/B/C (one case dropped before any outcome) | 4 + 12 = 16 | Yes, no slack |
| **P2: arm C frozen from the offline round + 5 holdout × A/B/C** | 15 | Yes, 1 spare |
| Any plan + arm D on the holdout | +5 | No |

Recommendation: **P2**. It keeps the whole frozen holdout and spends no units on a round whose candidate set
is three closed-catalog edits. Cost: arm C was selected on the double, so the record must say "arm C selected
offline on synthetic-control probes, evaluated natively". P1 is the alternative if the owner wants native
selection evidence; it loses one holdout case (continuity has only one, so drop a coordination case).

Arm D: record **infeasible in this window** (no implementation path, every lesson needs a human activation
record under `harness_experience`, and it does not fit the cap). Whether the 16-unit cap also counts the
SPEC-048 T008 units is not stated in the D2 record; the owner must say so (if it does, only 12 remain and P2
no longer fits).

## Quota and time per unit (estimate)

Measured so far, Haiku read-only on the qualified lab: T008 unit f 41 s, unit g 49 s, quota delta 0 on the
usage card; T009 attempt c delta 0. A T014 unit reads a guidance file, the task and a checkpoint note with up to
8 turns, so estimate:

| Per unit | Estimate | D2 limit |
| --- | --- | --- |
| Wall | 1–4 min | 30 min (unit marked interrupted, stays in the denominator) |
| 5-hour window | 0–1 % | at most 10 % per session; start only below 90 % |
| Weekly window | 0–1 % | cohort at most 15 %; stop above 80 % |
| Owner time | about 4 min (two usage cards, each at most 5 minutes old, plus the run) | — |

P2 cohort: 15 units, about 1 hour of owner time plus about 20 minutes setup; worst case 15 % weekly, which is the
cap, so a stop is possible and is evidence, not a failure. The cohort can be split across labels (the unit
ledger counts across labels, as in T008). Model: Haiku, the only model the lab has observed.

## Proposed engineering (not written: it changes the owner install)

1. `agent_braid/harness_t014_native.py` (new, outside the hash): per (case, arm) manifest and context from the
   T005 units and arm files, read-only tools, the case task as the visible prompt; turns the final message into
   the `out/result.txt` bytes and commits/grades them; never publishes assistant text.
2. `scripts/har_t014_cohort.py`: sibling of `har_t008_unit.py`; `--dry-run` and `--founder-go`; pins the
   2026-11-14 issuance, the T004 admission record and the T014 terms record by SHA-256; runs the registered
   Latin-square order; usage card before and after each unit; ledger `t014-units.json`, cap 16 (or the owner's
   lower number); writes the `evaluate` report with `verdictEligible` false and costs unknown where unobserved.
3. `scripts/har_t014_launch.sh` + `scripts/har_t014_install.sh` + `/etc/sudoers.d/braid-t014` (`check` only):
   sibling of the T008 launcher with helpers kept byte-identical by a test, label `t014-YYYYMMDDx`, publishes to
   `/Users/Shared/braid-t014-lab/`, same lab lock.
4. Tests with doubles: workload ↔ `verify_containment` values, grading bridge, cap/ledger, launcher helper
   identity; then a security delta review of the launcher and installer before install.

Estimated 2–3 PRs plus the review. It can be built now, in parallel with the T008 decision and the
re-qualification, without touching any frozen file; the pins go in once the new issuance exists.

## Owner steps once built (one command each)

Preconditions as in the T008 packet: braidlab logged out of any graphical session; start the 5-hour window first
(one own Claude message) so the card shows a fixed reset time; if the config directory holds more than 64
entries, run `/Users/Shared/t008-config-reset.sh` first.

1. Install (Terminal.app, your account): `bash ~/t014-install.sh` (the orchestrator renders it from the merge
   commit and gives you its SHA-256, as in T008 step 1).
2. Check (orchestrator, passwordless): `sudo -n /usr/local/libexec/braid/t014-launch.sh check t014-YYYYMMDDx`.
3. Run (Terminal.app, your password, type the usage cards): `sudo /usr/local/libexec/braid/t014-launch.sh run t014-YYYYMMDDx`.

New for the owner compared to T008: one more installer, one more sudoers rule (`braid-t014`, check only), and
three decisions:

- **T004 admission**: exact source (T005 roster freeze), candidates A/B/C, containment (2026-11-14 issuance),
  host/model route (Claude, Haiku, subscription), cash EUR 0.
- **T014 terms**: plan P2 or P1, arm D infeasible, whether T008 units count toward the 16, window end
  (must finish before the new issuance expires, 30 days after it is issued).
- **Arm-C freeze**: register candidate `6674a8da…f7d9` (resume-from-checkpoint only) as T014 arm C. Prepared
  here only; it is registered for T014 only after the orchestrator and the native-chain session are told.

Before all three: a new SPEC-048 T008 founder decision (0 units left) and a qualified Claude verdict.

## What T014 will and will not measure

Even if every unit runs, the native cohort is one lineage (L1) with 5 holdout cases: descriptive only under D3.
Read-only sessions answer a described checkpoint task, so the continuity stratum measures guidance-following on
a described checkpoint, not real long-task recovery. The frozen fixture oracles grade only "steps done / none
repeated"; six endpoints stay pending on this roster (`interventions`, `rework`, `interrupted-recovery`,
`conflict-precision-recall`, `false-safe-admissions`, `useful-parallelism`). Under owner decision D7 the most
likely outcome is an inconclusive T014, which closes harness as experimental. That is a valid result; nothing
here should be tuned to avoid it.
