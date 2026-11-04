# SPEC-065: security re-check of the T009 process-accounting edit

**Not a qualification.** No record is issued, no effect is qualified, nothing native is authorized;
`executionAuthorization` stays `false`. Self re-check by the implementing agent (not independent); the
orchestrator's re-check is owed. Nothing native was run.

| Item | Value |
|---|---|
| Date | 2026-11-04 |
| Cause | `t009-selfcheck2-20261104.md` |
| Branch / base | `har/065-t009-accounting-eperm`, `origin/develop` `a7369672` |
| Scope | `agent_braid/harness_containment_macos.py`: `_libsystem` (sysctl prototype), constants, `_kinfo`, `_task_resident` (was `_pidinfo`), `_user_processes`, `_process_links`, `_resident_bytes`, `_unreadable_tasks`, `_Lineage`, `_resource_limit`, `_sweep`, the `finally` block of `_supervise`. `scripts/har_t009_attempt.py`: `_NOISE`, `refusal_evidence`, `self_check` |
| Not touched | the SBPL allow-list (#1049), `cli.py`, `ownership.py`, `harness_transport_claude.py`, `harness_quota.py`, probes, `harness_lab.py`, docs/STATUS.md, ROADMAP.md, SPEC_MILESTONE_INDEX.md, CONSTITUTION.md |
| Verdict | **GO**, with the residuals below. Required fixes: none |
| Hashes | Backend module sha256 `c45235ff...04ea` -> `957e2463ac1151640a1617f0d141e5c3fb6e585fa4ecf910ca79710c30d69bb1`. Environment hash moves. Catalog hash does not move (`842f47fc18b843d81cf866478a0b895b29be0d81b5b5b29d0fd648da2ff8599b`). Profiles unchanged |

## Line by line

1. **`_kinfo`.** Read-only process-table query of one pid; it takes no task port and cannot affect the
   process. Offsets 0 (`p_starttime` timeval), 36 (`p_stat`), 40 (`p_pid`), 560 (`e_ppid`), 564 (`e_pgid`) of the
   648-byte record; `p_pid` is compared with the request and the size must be exactly 648, so a layout
   change fails closed rather than misreading. A unit test compares the real table with `os.getppid`,
   `os.getpgrp`. `ESRCH`/empty is the only "gone". **GO.**
2. **Strict part unchanged.** `_task_resident` keeps the old rule: `ESRCH` gone; live exited-unreaped
   (`SZOMB`, now read from `_kinfo`) gone; anything else live and unreadable raises
   `process-accounting-failed` with errno and flavor. It is now called only for the child and members, so a
   member whose memory cannot be read still refuses the run (tests: unit and run level). **GO.**
3. **Classification (`_Lineage`).** Member = the child, or parent in earlier members, or group led by the
   child/an earlier member. Orphans reparented to launchd keep the group, so a plain double fork is caught
   (killed, `escapedProcesses` > 0, run unsettled). A vanished or pid-reused process reads as unrelated: it is
   gone or not ours. If a process cannot be read at all, `_kinfo` raises: fail closed as before. **GO.**
4. **Sweep and watchdog.** Unrelated new processes are no longer killed, counted or measured. This removes a
   hazard (killing a GUI session's own agents) and the false refusals. **GO**, with the residuals below.
5. **Evidence.** `unrelatedProcesses`, `unreadableProcesses` are counts; the driver prints them only
   when `type(value) is int` and |value| <= 1000. `_unreadable_tasks` only counts `EPERM`; failures are
   swallowed and never change the verdict. **GO.**

## Escape reasoning and residuals

- **PROC-ESC-1 (new, accepted).** A descendant that calls `setsid`/`setpgid` and is reparented to launchd
  before a poll saw it with a member parent, or that starts and exits between two polls, is classified
  unrelated: not killed, not counted, not measured. Before this edit the sweep killed it as "any new process
  of the user". Mitigations in place: the polls (`_POLL_SECONDS`), `RLIMIT_NPROC` sized from the baseline plus
  the descendants limit, the group and parent chains, and the profile. Not closed: the process outlives the
  run and the measurement stays "settled". Evaluated option: `responsibility_get_pid_responsible_for_pid`
  (private SPI in libSystem; observed to answer for same-uid processes from an ordinary account: a child
  inherits its parent's responsible pid, pid 1 answers -1). It would separate "inherited from the supervisor"
  from "launchd agent" without task access, but it is undocumented SPI, unverified in the braidlab session and
  not needed for this unblock; recommended as a follow-up only if the noise counts or the PROC probes make
  PROC-ESC-1 matter. A kernel `e_sess` comparison was also considered; it is a kernel pointer and adds nothing
  over the group for a child started with `start_new_session`.
- **XPC / launchd spawn.** A process asking launchd to spawn work (ppid 1, own group) would read as unrelated.
  The profile denies every `mach-lookup` for the child, so it cannot reach launchd or any XPC service; the
  `launch` allow-list (#1049) adds none. This stays a profile property to keep in every future allow-list
  re-check.
- **PROC-ESC-2.** Membership by bare pid in `_pids`: a dead member's pid reused by an unrelated process makes
  that process's children read as members; they would be killed by pid. Window is one run, same user, the
  child's own pids; the start time is checked for the classified process but not for its parent. Accepted.
- **ACC-1.** `_kinfo` offsets are fixed for the 648-byte layout of macOS on arm64 and x86_64; any other size
  fails closed.
- **ACC-2.** A member whose `proc_pidinfo` TASKINFO fails with `EPERM` (for example a platform binary as
  fixture interpreter) still refuses the run, as before; the next self-check shows whether that happens.
- Carried: SYS-01 to SYS-03, DRV-04, 07, 08, 09, 11, 13, 15, MDRV-01 to MDRV-04.
