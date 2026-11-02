# SPEC-065: delta security review of the T008 fixes (#957, #959, #966), before T009

**This review is not a qualification.** It issues no record, qualifies no effect, authorizes no native
session, probe or account setup, and changes no code. `executionAuthorization` stays `false`.
Verifying that the T008 findings were fixed does not show that the profile enforces anything: that is
decided only by the T009 live attempt and the T010 human issuance. Every statement about macOS sandbox
behavior below is a *hypothesis* until T009 observes it.

## Record

| Item | Value |
|---|---|
| Date | 2026-11-02 |
| Task | SPEC-065 delta review required by `probe-catalog-review.md` (hand-off item 4) and by founder record LP-1 (`founder-decisions-20261102b.json`), before T009 |
| Reviewed commit | `7485b66a7d2392adc9002c56ec73f01f09c81a68` (current `origin/develop`). The reviewed code is the merge of #957 (`ca3084b6`), #959 (`608ee655`) and #966 (`6d6d8de9`); nothing after #966 touches the two files |
| Reviewer | A derived docs-and-closer track session (Claude Sonnet 5.5), distinct from the sessions that wrote T005/T006/T007 and from the T008 reviewer. Independent in session and context, **not** a human review and not a different model family. The founder may still want a human or second-family pass of the items marked blocking |
| Method | Static adversarial review of the current files in full (not only the diffs), reading of the three evidence files of the fix tracks and the founder records, reading of the unit tests, and one pure-Python check that renders the three SBPL profiles from a synthetic policy and diffs them (string rendering only). The two modules' unit tests were run: 267 tests, OK, 1 skipped (`unittest tests.test_harness_containment_macos tests.test_harness_qualification_probes`). Nothing native ran: no `sandbox-exec`, no `claude`, no dedicated account, no live probe, no uncontained control, no network. Code is cited as `B:line` (`agent_braid/harness_containment_macos.py`) and `P:line` (`agent_braid/harness_qualification_probes.py`) at the reviewed commit |

### Files reviewed (SHA-256 at the reviewed commit)

| File | SHA-256 |
|---|---|
| `agent_braid/harness_containment_macos.py` (1383 lines) | `6c7f90db7264351f2c018b7ab242a143649e6a5b6126fe0c648e5b06efbbcb80` |
| `agent_braid/harness_qualification_probes.py` (2490 lines) | `51e2d7eaf06f6a52d07f8c515f46802642d33e4f7660bf2c94126b62fb514002` |
| `agent_braid/harness_transport_claude.py` (read for the session path) | `e98c4db0e279b0a07a90a94d7c2f9a519e29dbdc0ca23c9b123dc3dc043fa19e` |
| `agent_braid/harness_host_claude.py` (read for `ENV_DENY`, `SUBSCRIPTION_KEY_SOURCES`) | `e31df98faaf998b023961daad4577c206fca0f622e156c27624952d7d739267b` |
| `tests/test_harness_containment_macos.py` | `81c7a104027e06019fcd07a27e0e122e7a8cce805bb26949490d089db4c629a8` |
| `tests/test_harness_qualification_probes.py` | `4046cac6ec6f917f9f5519fdfc2beae6340399118ee7cbdd2fc0ecc2b4526718` |
| `specs/065-native-claude-containment/evidence/probe-catalog-review.md` | `9abc938f3e3ac96038f65b1e221579fab7f6f1a86d856bab89e19477212c7d8e` |
| `.../evidence/t005-review-fixes.json` | `40e1761d9b8270b85ea1003c3b0d5bba1c67ef71601a79fb3def11d23893ddcb` |
| `.../evidence/t007-review-fixes.json` | `d4f4d8a228a636bd2bd2eec31fe46afb8fa4513009912a1a8baa742b3e7c29bb` |
| `.../evidence/t005-t007-integration.json` | `096249fc011c1819ef60ce07cb4befce43d71694b133dc3a670adbaa4525a1ee` |
| `.../evidence/founder-decisions-20261031.json` | `9aa51097b838c255ca92ecfb6f93a9fcea373d31c8a73ea6d45e635ae45e692e` |
| `.../evidence/founder-decisions-20261102.json` | `65b7ab68a907d0107372d3c27ee53bb8ac5f7139343d12f536e67ea69e1c5314` |
| `.../evidence/founder-decisions-20261102b.json` | `cf57bdf1f9ee052cc563e708fcfeb773b688a4089fa11c64e9bd8e36b05a1c91` |
| `specs/065-native-claude-containment/contracts/containment-qualification.md` | `8dda4230c0281c595d803529363a6bd5e34251adade65369a0797193902715ce` |
| `docs/adr/0035-native-claude-laboratory-containment.md` | `eab193465ad4bad971893a779ef5a9709f206aac6a3a660b3f5ded4c60f8b147` |

The two source hashes equal the ones recorded in `t005-t007-integration.json`. The catalog hash computed
by importing the probes module (no helper runs at import) is
`e8597c7fbe1749bc40c552996dbeed03a8a2e14f8990452823985f65f3d4b47a`, also equal to that record.

## Summary

34 original findings: 21 fixed, 7 partial, 1 not fixed, 2 closed by founder decision without code, 3
residual or informational and unchanged. 16 new findings: 0 critical, 0 high, 6 medium, 10 low.
Dispositions of the new findings: 7 fix-before-T009 (4 of them blocking), 2 needs-founder-decision, 7
residual.

None of the new findings is a demonstrated escape: nothing native ran. The fixes are, on the whole,
careful and fail closed. The points that matter before T009:

- **DRV-01 / DRV-02** are two places where the documented single entry point can report a pass
  without the observation its name promises (NET-05-CLI sees the backend's own pre-session tunnels;
  the real-path PROC-05 attempt silently stays in the arena by default).
- **DRV-05** leaves the transport (which builds the Claude argv) outside the environment hash.
  Because any backend edit stales the T009 bundle, all backend edits should land before T009.
- **The launch-probe profile is exactly the accepted delta** (verified by rendering, by the checker's
  negative cases and by reading both; see "Launch-probe delta"). No new SBPL rule is broader than
  NC-1..NC-11 and F5.
- Several new attempts have **controls that have never run**, and one failed control in a probe
  blocks the whole effect (DRV-09). This is availability risk for T009, not a false-pass risk.

### What looks sound (so the findings are read in proportion)

- The SBPL profile is still deny-default with no `mach-lookup`, `iokit`, `sysctl`, `ipc-*`,
  `network-bind`, `network-inbound`, UDP, raw or Unix-socket rule. The only rule changes since the T008
  commit narrow it (`subpath run_root` metadata became two literals, B:319-321) or add the accepted
  `launch-probe` entry. The test that asserts the
  negative set (`PolicyTests.test_profile_is_deny_default_and_deterministic`, `tests/test_harness_containment_macos.py:174`) still holds.
- Qualification, host qualification, OS window, account, mechanism hash, pinned executables, workspace
  modes, environment hash and expiry are re-verified before every run (B:1006-1041); the compile check
  now has a positive case (B:1069-1093); leftovers refuse the next run (B:1118).
- The probes module has no code path that builds, signs or writes a qualification record: its only
  writers are `write_bundle` (five evidence files, `P:2364-2394`), the session-count file
  (`P:2194-2203`) and arena planting that is removed on close (`P:1275-1285`, `P:1532-1542`).
  `summarize` hard-codes `qualificationRecordWritten: False` and `executionAuthorization: False`
  (`P:990`); `write_bundle` repeats the latter (`P:2385`).
- The pass rule remains monotone toward `allowed`: a denial needs a working control, an observed
  escape is never hidden by a failed control (`P:905-929`), tripwires only escalate (`P:2083`,
  `P:2105`), and any refusal, executor failure or missing output yields `inconclusive`, never
  `denied` (`P:2068-2072`, `P:2293-2295`).

## Launch-probe delta (founder record LP-1)

Rendered with a synthetic policy (pure string rendering) and diffed against `launch`:

- line `process-exec`: gains `(literal <interpreter>)` only;
- line `file-read* file-map-executable`: gains `(subpath <interpreter_root>)` and `(literal <interpreter>)`;
- line `file-read-metadata`: gains literals for the ancestor directories of the interpreter and of
  `interpreter_root` that `launch` did not already list;
- every other line is byte-identical, including the `config_dir` read/write line, the network line,
  the `DENIED` line and the environment (`child_environment` is equal, asserted by
  `test_launch_probe_is_launch_plus_exactly_the_interpreter_literal`).

`launch_probe_delta_is_interpreter_only` (P:1614-1647) enforces this per differing line: items may only
be added, only the three allowed kinds of line may differ, added items are limited to the interpreter
literal, `interpreter_root` and its ancestors, no item may be added twice, and the non-item text of each
line must be identical. I confirmed with the rendered profiles that it returns `True` for the real
delta and `False` when an extra `(allow mach-lookup ...)` line is appended or when an extra
`(subpath "/Users")` is added to the read line. `ContainedExecutor` calls it before every launch-probe
helper run (P:1675-1683, P:1692); the environment hash binds all three profile hashes (B:383) and
`ENTRIES` includes the new entry (B:97).

Two observations, neither a deviation from LP-1: `file-map-executable` is on the same rule line as the
read of `interpreter_root`, so the interpreter prefix is also map-executable (the `fixture` profile has
the same); and the check is enforced in the probes module and by unit test, not inside the backend
(`run_launch_probe`, B:1153-1160, renders whatever `render` returns). The profile therefore matches the
accepted delta, and the value of `interpreter_root` becomes policy-critical (DRV-12).

## Per-RV verification

Status: **fixed** (the disposition's substance is in the code and holds under adversarial reading),
**partial**, **not fixed**, **decision** (closed by a founder record, no code expected), **residual**
(accepted or informational, unchanged). References are to the reviewed commit.

| RV | Status | Evidence |
|---|---|---|
| RV-01 swept leaver judged as escape | **fixed** | Backend: `_sweep` returns `(escaped, surviving)`; `surviving` is re-measured after the last round and covers the 40-iteration exhaustion (B:1359-1383); `RunAccounting.escaped_processes`/`surviving_processes`/`escaped_descendants` (B:819-840); `settled` stays strict (B:1318). Judge: `swept_settled` and `_survival_state` read `surviving_processes` (P:1797-1819), the independent nonce scan and `(pid, start)` diff can only escalate (P:2073-2081). A backend that does not report counts falls back to the strict flag. Tests: `test_a_swept_leaver_is_counted_apart_from_a_survivor...` (containment tests:864) |
| RV-02 PROC-08 cancel half | **fixed** | `run_probe(..., cancel=)` and `run_launch_probe(..., cancel=)` (B:1144-1160), `Event` type check (B:1164-1166), `ProbeResult.cancelled` (B:852, B:1178). Driver `_cancel` (P:2130-2190) denies only with begin marker, backend `cancelled`, no survivor from backend, scan and process diff, and an available table. Authors' residual confirmed: the begin marker precedes the fork (P:710), so a very early cancel could read `denied` with no leaver; with a 1 s delay after the nonce is first seen this is improbable (residual, noted in `t005-t007-integration.json`) |
| RV-03 NET-05-CLI | **partial** | Proxy side fixed: thread-safe counters (B:607-608, B:618-624), `unexpectedDirect` counted at B:705 and B:673, per-target tunnel counts at B:730-731, `egress_counters()` (B:968), per-run delta in the result (B:1239, B:1319). Verdict `_egress_verdict` (P:1034-1053) is sound for the violation signals. But the "no tunnel at all stays inconclusive" guard is defeated in the integrated path: see DRV-01 |
| RV-04 fixture-only probes | **fixed** | `launch-probe` entry (B:97, B:289-328), `run_launch_probe`, `contained-launch` rows for every helper probe (P:78, P:2045-2058), `judge_probe` requires both rows and lets an escape in either win (P:932-953), NC-11 subset runs both profiles and refuses on disagreement (P:2436-2440), delta checker (P:1614-1647) |
| RV-05 `gaierror` read as denied | **fixed** | `_classify` makes name-resolution failure `inconclusive` unless `dns=True` (P:143-154); NET-01 uses a runner-owned loopback listener and a public literal with the by-name attempt as tripwire (P:430-434); NET-05 `direct-allowed-host` uses the runner-resolved literal (P:458, P:2016-2019) |
| RV-06 FS-06 non-discriminating | **fixed** (simplified) | Descriptor inventory over fds 3..1023, any open one is a leak (P:252-261, P:412); the control passes a descriptor (`Arena.inherit_fd`, P:1514-1518, P:1575). `/dev/ptmx` and `/dev/fd/0` counted, `/dev/tty` and an in-candidate FIFO are notes (P:415-418). The F_GETPATH identity check for fds 0/1/2 proposed in T008 was not built; the weaker form still discriminates |
| RV-07 FS-07 masked by exec allow-list | **fixed** (names unverified) | Three mach lookups replace `mdfind`, which is now a tripwire (P:420-429). Whether `com.apple.Spotlight` exists as a mach name is unverified: see DRV-09 |
| RV-08 mach/IOKit/shm/sysctl coverage | **partial** | Mach sweep over runner-enumerated launchd names with a "needs at least one explicit refusal" rule (P:243-249, P:1216-1231, P:2021-2028), `tccd`, sysctl x2, `proc_listpids`, POSIX/SysV shm, POSIX semaphore (P:607-707). Missing: `IOServiceOpen` (the attempt is a registry lookup, DRV-08), kqueue (accepted residual). `launchctl print` output shape is a hypothesis (authors say so) |
| RV-09 FS boundary and macOS primitives | **partial** | Adjacent decoys, alias paths, rename/link out, copy/clone in, chmod/chflags/xattr, own-tree hard link, real LaunchAgents path (P:306-331, P:335-398, P:603-604, P:1287-1310). Gaps: `adjacent-run-dir` and `adjacent-run-root` are the same path in the real layout, and `/Volumes/<boot volume>` is not tried; `adjacent-interpreter-root` may be denied by file permissions rather than the profile (DRV-04) |
| RV-10 network breadth and proxy parsing | **fixed** | RFC 1918, link-local v4/v6, multicast, `0.0.0.0`, v4-mapped tripwires, host LAN listener (P:435-455); seven proxy-parsing cases against a live `EgressProxy` with a recording upstream, a sanity request that guards the observation, and the permissive relay as control (P:1836-1934). The "LAN address at the proxy port" case is not attempted, but the proxy binds loopback only (B:629-636), so there is no listener to reach |
| RV-11 PROC-07 ptrace, task_for_pid, supervisor | **fixed** | `kill(getppid(), 0)` (P:694-695), PT_ATTACH/PT_DETACH on the sibling, counted (P:635-644, constants 10/11 are correct for macOS), `task_for_pid` as tripwire (P:645-650, P:706). Controls unverified: DRV-09 |
| RV-12 cooperative survivor scan | **fixed** | `(pid, lstart)` diff of the runner user's table before/after (P:1723-1736, P:2062-2081), unattributed processes escalate but are not killed unless `kill_table_diff`; an unavailable table makes a contained survivor probe `inconclusive` (P:2084-2086) |
| RV-13 limit attribution, memory sampled | **partial** (by design) | `limitExceeded`, `timedOut`, `outputTruncated` recorded in the row (P:2110-2111); memory denials need `limit_exceeded == "memory"` (P:91, P:2087-2090) which the backend now supplies (B:829-839, B:1353); fast-burst allocation added (P:570-575). Memory remains a 50 ms sampled watchdog (B:1341-1357): the burst attempt can complete between polls and read `allowed`, so it may be flaky (see DRV-07) |
| RV-14 runner/judge/arena and component hashes | **partial** | T007 half fixed: `runnerSha256` in the catalog document (P:871-872), `probe_catalog_sha256` derived from the probes module and rejected if different (B:207-213, B:240-244), `make_f4_probe_runner` and `make_qualification_runner` refuse unless the policy binds it (P:2427, P:2480), `_environment_document` checks it (P:2311). T005 half not done: `_component_hashes` still hashes only backend, `harness_lab`, `harness_host_claude` (B:361-364): DRV-05 |
| RV-15 NC-10 stop rule and quotas | **fixed** | pre/post readings via `read_quota` (P:1151-1165), `settle_probe` with the 2 % cap (`harness_quota.PROBE_MAX_FIVE_HOUR = 2`), stop persisted atomically, missing or stale reading stops, unreadable counter file means budget spent, count survives a retry in the same directory (P:2194-2268), cap of 3 enforced per directory (P:2224-2228). Omitting `read_quota` stops after the first session and the transport's own admission also needs a pre-reading |
| RV-16 dedicated account not verified | **fixed** (code) | `_account_facts` refuses wheel/admin (gid 0/80, primary or supplementary), the console user, and a home that is not an owned directory with mode 0700 (B:112, B:434-445, B:1021-1022); `AccountFacts` enter the environment hash (B:381-382, B:1036). Runbook sentence is wrong: DRV-12 |
| RV-17 credential exfiltration route | **decision** | Accepted residual, `founder-decisions-20261102.json`. ADR 0035 residual text (`docs/adr/0035...:111-118`) still says only that allowed endpoints can carry data to Anthropic; the founder record carries the bound and the 30-day revisit (DRV-12) |
| RV-18 session-state purge and persistence | **not fixed** | Deferred to T009 observation by design. The interim measure from T008 (a hash listing of `config_dir` before and after each session in the bundle) is not implemented either (no code reads `config_dir` except `credential_values`): DRV-16 |
| RV-19 disk and file-count bound | **fixed** (per decision) | `LIMITS` 2 GiB / 100,000 (B:87-89), `_DiskGuard` over candidate and per-run TMPDIR, blocks x 512, each inode once, every entry counted, symlinks not followed, unlistable or unsearchable counts as over (B:876-915), polled with memory (B:918-925, B:1352), natural-exit recheck (B:1308-1309), refusal `disk-limit-exceeded` (B:1325). Coverage gaps: DRV-06, DRV-07 |
| RV-20 metadata and read rules | **partial** | `subpath run_root` metadata replaced by literals for `run_root` and the `RUNDIR` param (B:319-321). `SYSTEM_READ` not trimmed (needs the T009 trace; accepted residual) |
| RV-21 keychain and mach route | **decision** | Own keychain, closed list of services, T009 observes which, any addition needs a record, a catalog extension and a delta review. No profile change was made, which is consistent: the profile still has no `mach-lookup` |
| RV-22 ancestor ownership | **fixed** | `_shared_ancestor` requires every ancestor, up to and including `/`, to be owned by root or the effective (dedicated) uid and not group/other-writable (sticky root-owned directories allowed) (B:146-163); `_trusted_file` also requires a regular file, `realpath == path`, owner root or dedicated, no shared-write bit, and the pinned hash (B:195-201), applied to every executable of the entry (B:1029-1030). Tested with a mocked third-party owner (containment tests:344-352). Remaining window: DRV-13 |
| RV-23 compile check cannot tell denied from failed | **fixed** | After exit 71 for `/usr/bin/false`, an allow-listed command must exit 0 (fixture: interpreter on an empty program; launch and launch-probe: pinned `claude --version`) else `self-check-failed` (B:1069-1093, B:282-287). Expect this to be the first thing that fails at T009 if the profile has to grow; that is a real refusal |
| RV-24 secret scanning and environment document | **fixed** | Allow-list schema for `environment.json` with no path or account name (P:2298-2312), token-shape and long-run scan over all five files (P:2318-2327, P:2379-2387), credential leaf values from `config_dir` feed the scan list (P:2338-2361, P:2276-2279). Wiring default: DRV-03; privacy: DRV-11 |
| RV-25 CRED-04 tautology | **fixed** | A non-`ENV_DENY` dummy variable is set in the supervisor's environment around every contained helper call and listed in `env_names` (P:1374, P:1942-1954, P:2065-2066); the child environment is built from scratch (B:330-341) |
| RV-26 any non-200 counted as denial | **fixed** | `_verdict` returns denied only for an explicit `HTTP/1.1 403` (P:264-268, used by `tunnel` and `tls`) |
| RV-27 attempt discovery by regex | **fixed** | `_validate_catalog` compares every call site with the declared names (P:94, P:842-845); `raw-socket` is a tripwire (P:473) |
| RV-28 synthetic session controls | **residual** | Unchanged and still accurate. The literal `apiKeySource` is still bucketed to `other` outside `{none, oauth}` (P:2244-2245): DRV-14 |
| RV-29 proxy robustness | **fixed** | Dead accept loop outside `close()` sets `_failed` (B:652-659), `healthy` (B:614-616), refused at the next pre-session and restarted on the following attempt (B:1119-1123); SNI-as-defence-in-depth documented in the class docstring (B:578-580) |
| RV-30 cleanup tolerates undeletable | **fixed** | `_remove_tree` clears BSD flags and directory modes as the owner and retries, `shutil.rmtree` does not follow links (B:166-192); `cleanupFailed` recorded (B:1320); `_leftovers` refuses the next run, and candidate directories cannot start with `run-`/`compile-` (B:1062-1067, B:1046-1048). Consequence accepted by the authors: a child can cause a persistent refusal until an operator cleans up |
| RV-31 post-run consumers of the candidate | **residual** | Out of scope here; the hand-off to SPEC-049 readers stands |
| RV-32 sweep treats every new process as an escape | **fixed** (as counters) | `_Lineage` splits descendants from unattributed (B:855-873, B:1283-1286); both keep `settled` false. A per-user daemon started by launchd during a run would still read as an escape, which fails closed (flaky, not unsafe) |
| RV-33 evidence and naming drift | **partial** | New hashes recorded (`t005-review-fixes.json`, `t005-t007-integration.json`). The stale sentence at `harness_host_claude.py:47` ("until T008 observes the real values") is still there (DRV-12) |
| RV-34 recorded residuals | **residual** | Unchanged; DRV-06/07/13 add to them |

Counts: fixed 21 (01, 02, 04, 05, 06, 07, 10, 11, 12, 15, 16, 19, 22, 23, 24, 25, 26, 27, 29, 30, 32),
partial 7 (03, 08, 09, 13, 14, 20, 33), not fixed 1 (18), decision 2 (17, 21), residual 3 (28, 31, 34).

## New attempts of #959: do the controls discriminate?

The control for a helper probe is the same helper run uncontained, as the dedicated user, in a synthetic
arena; a denial counts only if the control's attempt of the same name is `allowed`
(`P:918-919`). So a control that cannot succeed makes the whole probe `inconclusive` (all-or-nothing).
`LiveControlTests` (P tests:1135-1148) executed uncontained controls only for FS-01..06, CRED-01/03/04 and
PROC-01; **no control of any attempt below has run**, which `t007-review-fixes.json` states.

| Attempt | Contained signal | Control and discrimination | Risk |
|---|---|---|---|
| `signal-supervisor` (P:694-695) | `kill(getppid(), 0)`; the parent is the supervisor, outside the sandbox, `signal` allows `same-sandbox` only (B:312) | Uncontained: parent is the runner, same uid, signal 0 succeeds | Discriminates; the best of the new attempts |
| `ptrace-sibling` (P:635-644) | PT_ATTACH on the sibling; EPERM/EACCES is denied | Same uid, uncontained | The pinned interpreter may be hardened-runtime or otherwise non-attachable on macOS 27 (hypothesis); then the control fails and PROC-07 stays `inconclusive`. Counted, not a tripwire, as T008 asked. Not a false-pass risk |
| `task-for-pid` (P:645-650) | tripwire | None needed: success contained escalates, a refusal means nothing | Sound as a tripwire |
| `mach-tccd` (P:618) | mach lookup, status 1100 means denied (P:233-240) | Uncontained lookup succeeds only if the per-user `com.apple.tccd` exists in the dedicated user's session | Depends on the supervisor running in the dedicated user's own login (Aqua) session; from `sudo -u` or ssh the bootstrap may differ (hypothesis): DRV-09 |
| Spotlight: `com.apple.metadata.mds`, `...mdwrite`, `com.apple.Spotlight` (P:425-427) | same mapping | `mds` is a system service; `mdwrite` is plausible; `com.apple.Spotlight` may not be a registered name (hypothesis). One missing name leaves FS-07, and therefore the filesystem effect, `inconclusive` | DRV-09 |
| `mach-sweep` (P:243-249, P:619) | any status 0 is allowed; denial needs at least one 1100; unknown names (1102) alone prove nothing | Same loop uncontained must find successes; an empty enumeration is `inconclusive` | Good design. `launchctl print` output shape is a hypothesis; up to 2000 lookups, no message is sent to any service |
| `iokit-service` (P:608-615, P:620) | `IOServiceGetMatchingService`, returns 0 when refused | Uncontained returns a service | It is a registry lookup, not `IOServiceOpen` (the operation the profile omits). If the sandbox does not gate registry lookups, it reads `allowed` with no real escape and the process effect would show `not-enforced`: DRV-08 |
| `sysctl-proc-all`, `sysctl-hw`, `list-pids` (P:651-673) | errno from `ctypes.get_errno` of `use_errno` libraries; EPERM/EACCES is denied | Uncontained succeeds | `proc_listpids` may set no errno when refused, which reads `inconclusive` (fail closed); `hw.memsize` may be readable under any profile (DRV-08) |
| `shm-posix`, `sem-posix`, `shm-sysv` (P:674-693) | OSError errno | Uncontained succeeds; names are 15 characters, inside the 31-character macOS limit | Discriminating. The SysV segment is removed with `shmctl` |
| `launchctl-exec` (P:605) | exec denied by the exec allow-list | `launchctl list` succeeds uncontained | Discriminates for the allow-list; it does not test `launchctl submit` over XPC (covered by the mach sweep) |
| `tcp-lan-listener`, `tcp-unspecified`, v4-mapped (P:448-455) | connect to runner-owned listeners | Uncontained connects | Discriminating; needs a LAN address (else `inconclusive`) |

## New findings

Severity: **Medium** = a pass or a fail that does not mean what it says, or a gap against a founder
decision. **Low** = hardening, hygiene or an availability risk. No critical or high finding. Dispositions:
`fix-before-T009`, `residual`, `needs-founder-decision`. "Blocking" marks the items I would not start T009
without.

**DRV-01 (Medium, fix-before-T009, blocking): the NET-05-CLI observation includes the backend's own
pre-session tunnels, so "no CLI traffic" cannot read `inconclusive`.**
Location: `P:1148-1168` (taps at `P:1152` and `P:1165`), `P:1034-1053`; backend `B:1201`,
`B:1239`, `B:1319-1335`; F4 NET-06 at `P:2422-2440`.
`native_session_driver` reads the proxy counters before `transport.version()` and after
`transport.run()`. Each of those launches runs the full pre-session check first (B:1201), and the NC-11
subset includes NET-06, which opens a real CONNECT tunnel to `api.anthropic.com:443` through the same
proxy, once per profile (the contained `fixture` leg and the `launch-probe` leg). The delta therefore
contains at least four `allowed:api.anthropic.com:443` tunnels before the CLI sends a byte, and
`_egress_verdict` returns `denied` as soon as the targets are allowed and the counts agree. The
backend already captures the correct window (`egress_before` is read after the pre-session, B:1239) and
returns it as `ContainedHostRun.egress`, which `harness_transport_claude._finish` passes through
(`harness_transport_claude.py:256`, except on the route-unverified kill path). The violation signals
(`unexpectedDirect`, a non-allowed target) remain valid, so this is a vacuous pass, not an undetected
escape; but it is the vacuity RV-03 asked to remove. The unit tests use a double that returns the
counters of the session only (`tests/test_harness_qualification_probes.py:995-1009`).
Fix: take the session's egress from the run's own delta (`getattr(run, "egress", None)`), fall back to
`None` (inconclusive) when it is absent, and add a test where the pre-session tunnels are present and the
CLI made none.

**DRV-02 (Medium, fix-before-T009, blocking): the documented entry point defaults to no real-path
evidence for PROC-05 and the own-tree hard link, and the row does not say so.**
Location: `P:2451-2453` (`real_home=None`), `P:2488`, `P:1343-1347`, `P:2058`; the test that asserts the
default is `tests/test_harness_qualification_probes.py:2176-2180`.
`make_qualification_runner` is described as the one entry point whose omitted inputs "make the probes
that need it `inconclusive` (never a pass)". For `real_home` that is not true: with `None` the arena
keeps `real_launch_agents` and `own_file` inside itself (`P:1343-1347`), the contained attempt is denied
there because the arena is outside the write set, the control passes in the same arena, and PROC-05
`real-launch-agent` and FS-02 `hardlink-own-tree` read as passes without touching a real path. The row
records `layout` as `real`/`synthetic`/`none` (`P:2123`) but nothing about the home. Fix: default
`real_home` to `home_directory()` (the runner is the dedicated account), or refuse a pass for those
attempts unless the row records `realHome: true`.

**DRV-03 (Low, fix-before-T009, recommended): the credential-literal scan is unwired by default.**
Location: `P:2452`, `P:2489`, `P:2276-2279`, `P:2338-2361`.
`read_credentials` defaults to `lambda: ()`, so with the default the leak scan has only the token shapes
and the arena markers. The docstring ("every optional input is fail-closed") is not accurate for this
one. No path was found by which helper or session content reaches the bundle (helpers emit outcome and
errno only, `P:134-136`, `P:157-159`; session stdout is never persisted), so this is a depth defence.
Fix: default to `credential_values(policy.config_dir)`, or make `run()` refuse with
`credential-scan-unavailable` when no source is wired.

**DRV-04 (Low, residual): two adjacent-decoy attempts do not test what they are named for.**
Location: `P:1305-1308`, `P:319`, `P:1296-1299`.
(a) In the real layout the candidate is directly below `run_root`, so `candidate.parent` and `run_root`
are the same directory and `adjacent-run-dir` and `adjacent-run-root` write the same path
(`P:1306-1307`); the actual `run-XXXX` directory (whose parent of `TMPDIR` an over-broad rule would
expose) is never tried. The child could reach it as `dirname($TMPDIR)`. (b) `adjacent-interpreter-root`
writes into `interpreter_root`; T005 recommends a root-owned install, so file permissions deny the write
before the profile does, while the synthetic control is writable. Impact is low (a profile grant on a
path that file permissions already forbid is not exploitable). Disposition: residual; at the next
catalog edit use `dirname($TMPDIR)` for (a) and record a `dacDenied` note for (b).

**DRV-05 (Medium, fix-before-T009, blocking): the Claude transport and the quota module are still
outside the environment hash.**
Location: `B:361-364`, `B:394`.
RV-14's T005 half is open. The transport builds the Claude argv and pins the build
(`harness_transport_claude.py:174-190`, `:226-237`); an edit to it changes effective policy but not the
environment hash, so a recorded qualification would stay valid. The probes module is bound through the
catalog hash (the lazy-imported `CATALOG_SHA256` includes `runnerSha256`), which is sufficient for it.
Fix: add `harness_transport_claude.py` and `harness_quota.py` to `_component_hashes` (read by path).
This changes the backend hash, so it must land **before** T009 together with the other backend edits;
NC-9's trigger list does not name the transport, so this is a hardening beyond the decisions rather than
a new rule.

**DRV-06 (Medium, needs-founder-decision): the 2 GiB / 100,000-file bound does not cover `config_dir`
and no live probe tests it.**
Location: `B:1240`, `B:876-915`, `P:581-590`, `P:437` (PROC-03 `file-count` is `limit_note`).
The founder decision measures "the candidate directory plus TMPDIR", and that is exactly what is
implemented. In `launch` the child can also write unlimited files to `config_dir` (read/write by design),
subject only to the 64 MiB per-file limit, so the volume-filling concern behind RV-19 remains for the one
tree that matters most in a live session. Separately, the catalog never exercises the new bound: the
`file-count` attempt creates 20,000 files and is informational (`P:581-584`), so the `process` effect can
read `enforced` with the disk bound untested live, while the contract lists "file-count (disk exhaustion)"
under PROC-03. Options for the founder: (a) also measure growth of `config_dir` against the session
start, (b) accept it as a recorded residual until the purge exists (RV-18), (c) add a counted attempt
that crosses a reduced bound in a probe-only configuration. I recommend (b) for T009 and (a) with the
purge.

**DRV-07 (Low, residual): the disk, memory and wall watchdogs are polled thresholds, not quotas.**
Location: `B:1341-1357`, `B:918-925`, `B:876-915`.
Each poll lists processes and then scans up to 100,000 entries with a `stat` each; as the tree grows the
poll interval grows with it, so a child can slow the memory watchdog by first creating many files, and
can overshoot a bound by what it writes during one poll plus one scan. A directory is fully listed
before its entries are counted, so one huge directory is read into memory before the bound trips.
`st_blocks` does not count extended-attribute or resource-fork payload (hypothesis: a child with
`file-write*` can store data there, and `RLIMIT_FSIZE` does not apply to `setxattr`). The memory-burst
attempt can therefore be flaky (`allowed` by a timing race). All of these fail toward a hard stop or an
`allowed`, not toward an undetected pass. Disposition: residual; record in ADR 0035's residual list.

**DRV-08 (Low, residual): the IOKit and `hw.memsize` attempts may report `allowed` for benign reasons.**
Location: `P:608-615`, `P:659-666`.
`IOServiceGetMatchingService(IOService)` is a registry lookup, not an `IOServiceOpen`; `hw.memsize` is a
benign read that some profiles permit by default. If the sandbox does not gate either, the contained row
is `allowed`, the process effect reads `not-enforced`, and the profile cannot be changed to satisfy it.
That fails closed but would waste the attempt. Disposition: residual; if T009 shows this, the founder
should decide whether to demote them to informational or open a catalog extension, not widen the profile.

**DRV-09 (Medium, residual and T009 prerequisite): controls never run, session-dependent, and
all-or-nothing.**
Location: `P:918-919`, `P:425-427`, `P:618`, `P:635-644`, `P tests:1144-1145`.
See the control table. Any single control that cannot succeed (an unregistered mach name, a non-attachable
interpreter, a per-user service absent from a non-GUI session) leaves the probe, and so the effect,
`inconclusive`; fixing it after the fact changes the catalog hash and restarts the attempt. Mach and
pasteboard controls (existing CRED-07, PROC-06) have the same dependency. Disposition: residual, with two
prerequisites for the T009 runbook: run the supervisor inside the dedicated user's own login session, not
via `sudo -u` from the operator's session, and expect and record failed controls as findings. A
controls-only dry run in uncontained mode would remove most of this uncertainty; it executes native code
(mach lookups, `ptrace`, shared memory) so it needs the founder's explicit go and is not part of this
review.

**DRV-10 (Low, needs-founder-decision, acknowledgement): NC-11's subset now runs twice per launch with
changed attempts, and the F4 runner has a knob that disables the second leg.**
Location: `P:2416-2442` (`launch_profile=True` default), `P:430-434`, `P:2490` (`runner_options`).
NC-11 names five probe ids; RV-04 and RV-05 changed what NET-01 attempts (loopback listener, public
literal, by-name as tripwire) and the pre-session check now runs each probe under `fixture` and
`launch-probe`. T008 said the founder should be told; LP-1 accepted only the launch-probe deviation.
`launch_profile=False` and `runner_options` override can weaken the check. Request: one line in the next
founder record acknowledging the NC-11 reading; the knob should not be passed in T009.

**DRV-11 (Low, residual): absolute local paths can reach the bundle on an escape.**
Location: `P:1499` (`extra_outside` in `changed`), `P:2114`, `P:2124`.
Only when an escape occurred, `changedOutside` lists absolute paths (account home, run root, config
parent), and PROC-06 rows list launchd service names of the dedicated user. Both pass the secret scan.
Review the bundle for local identifiers before committing it (as RV-24 already says).

**DRV-12 (Low, fix-before-T009 as documentation, blocking for the runbook): runbook and ADR
statements are wrong or stale.**
Location: `t005-review-fixes.json` (RV-16 runbook), `harness_host_claude.py:47`, ADR 0035 lines 111-118.
(a) "The code location unreadable by that account" cannot be satisfied: the supervisor must run as the
dedicated account (B:1020), so it must be able to read the code, the interpreter and the pinned binary.
The right requirement is a root-owned, non-operator-private install the dedicated account can read but
not write, and no read access for it to the operator's home. (b) `interpreter_root` is readable (and
map-executable) in `fixture` and `launch-probe`, so it must be a minimal prefix, never a repository or a
home directory; the policy only demands three path components (B:267-268). (c) `_account_facts` does not
see sudoers-by-name, ACL grants or groups such as `_developer`; the runbook should say so. (d) ADR 0035
does not yet carry the RV-17 route (credential sent to Anthropic with an attacker-supplied key) or the
RV-19 values. (e) Stale sentence at `harness_host_claude.py:47`.

**DRV-13 (Low, residual): hash-to-exec window and ACLs.**
Location: `B:146-163`, `B:195-201`.
Dedicated-user-owned ancestors are trusted, so a same-uid actor outside the sandbox can still swap a
pinned binary between the hash check and the exec (the transport re-hashes, `harness_transport_claude.py:174-181`);
POSIX modes are inspected, ACLs and file flags are not. A root-owned install is the stronger form (RV-22's
stated alternative). Residual.

**DRV-14 (Low, fix-before-T009, recommended): the real `apiKeySource` value is thrown away.**
Location: `P:2244-2245`, `harness_host_claude.py:47-48`.
The row records the label only when it is in `{none, oauth}`, else `other`. T009 exists to observe the
real values (RV-28); if the CLI reports something else, CRED-05 reads `allowed` and the bundle cannot
say what it was, which would cost another of the three live sessions. The label is not a secret; record
it when it matches a short `[A-Za-z0-9._-]{1,40}` pattern.

**DRV-15 (Low, residual): the egress verdict compares with the module constant, not the policy.**
Location: `P:1049` (`_mac.ALLOWED_ENDPOINTS`) against `B:271-273` (`policy.endpoints`).
After the OAuth refresh hosts are observed and added to `refresh_endpoints`, legitimate tunnels to them
would read as `allowed` (an escape). Fail closed; fix when `refresh_endpoints` is first set.

**DRV-16 (Medium, fix-before-T009, recommended): the interim state-sharing measure for RV-18 is absent.**
Location: no code (T008 disposition for RV-18).
Until the purge exists, the three probe sessions share `config_dir` state, and T009 is supposed to observe
which paths are session state versus credential. Nothing records a listing or hash of `config_dir` before
and after each session. Either add it to the session driver (names and digests only, never contents, and
inside the secret scan), or make it an explicit runbook step with the operator hashing the directory as the
dedicated user and attaching the result.

## Checks requested by the brief

| Check | Result |
|---|---|
| Each fixed RV is fixed | See the table. 21 fixed, 7 partial (RV-03 DRV-01, RV-08 DRV-08, RV-09 DRV-04, RV-14 DRV-05, plus RV-13, RV-20, RV-33 by design or deferred), 1 not fixed (RV-18, DRV-16) |
| New attempts have discriminating controls | Partly: sound by construction (supervisor signal, shm/sem, mach sweep design, tripwires) but none has run and several depend on unverified names or sessions (DRV-09) |
| launch-probe differs from launch exactly by LP-1 | Yes (see "Launch-probe delta") |
| No policy rule broader than NC-1..NC-11 / F5 / 2026-11-02 | Yes. The only SBPL changes are narrower metadata, the accepted `launch-probe` entry and disk limits as a supervisor check, not a rule. `refresh_endpoints` and `helpers` remain empty by default |
| Fail-closed defaults in `make_qualification_runner` | Mostly: sessions, quota, LAN, allowed IP, mach names and the catalog binding fail closed (`P:2465-2480`); `real_home` and `read_credentials` do not (DRV-02, DRV-03) |
| Fail-closed `make_f4_probe_runner` | Yes: `error` unless the probe is in the subset and the policy binds the catalog (`P:2427`), `error` unless both profiles give the same `allowed`/`denied`, a functional probe with any disagreement is `error` (`P:2438-2440`), no controls and no uncontained run happen in the pre-session |
| No qualification-record writing path | Confirmed (see "What looks sound") |
| No secret leakage into bundles | No path found; helpers emit outcome and errno only, `errors` are matched against `[A-Z0-9_]{1,24}` (`P:87`, `P:1785`), environment document is an allow-list, scan covers all files. Depth gaps DRV-03 and DRV-11 |
| RV-22 ancestor ownership | Verified (B:146-163, B:195-201); DRV-13 residual |
| 2 GiB / 100,000 files | Implemented as decided (B:876-915); coverage and overshoot in DRV-06, DRV-07 |

## Recommendation for T009

**NO-GO on the current commit; GO after one small follow-up track and a founder go.** This review does
not authorize T009: it still needs its own founder go, the dedicated account, the pinned binary and the
operator-supplied inputs, none of which exist yet.

Blocking items, all small, to land in one track together (any backend edit changes the environment hash,
so they belong before the first live bundle):

1. DRV-01: session egress from the run's own delta, with a test that pre-session tunnels do not count.
2. DRV-02: `real_home` defaults to the dedicated home, or the pass requires `realHome`.
3. DRV-05: add the transport and quota modules to the component hashes.
4. DRV-12: correct the runbook sentences (code location, `interpreter_root`), update ADR 0035's residual
   list, and drop the stale comment at `harness_host_claude.py:47`.

Recommended in the same track: DRV-03 (credential scan default), DRV-14 (record the real `apiKeySource`
label), DRV-16 (`config_dir` listing before and after each session).

Founder decisions needed (not blocking T009 by themselves): DRV-06 (what to do about `config_dir` disk
growth and the unprobed bound) and DRV-10 (acknowledge the NC-11 reading).

After that track, a delta check restricted to the touched lines should be enough; it does not need a
full review. Everything in the residual list is to be recorded in the T009 bundle summary and carried
into the T010 decision. Plan for the possibility that T009 returns `inconclusive` for FS-07, PROC-06 or
PROC-07 because of failed controls (DRV-09), and for `not-enforced` on `iokit-service` or `sysctl-hw`
(DRV-08); neither would be a profile failure to fix by widening the profile.
