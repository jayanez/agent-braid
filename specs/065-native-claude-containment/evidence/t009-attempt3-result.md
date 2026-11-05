# SPEC-065 T009, real attempt `t009-20261104c`: result (not qualified)

Date: 2026-11-04 (run at 23:14 local). Founder's Mac, dedicated account `braidlab`, backend
`macos-dedicated-user-sandbox-exec`. Bundle: `evidence/qualification/t009-20261104c/` (copied verbatim,
`SHA256SUMS` beside it). The founder accepted this round on 2026-11-04 ("OK, adelante") after the orchestrator
recommended: record the bundle, add a no-model session-startup diagnostic, fix PROC-08 and PROC-03, and defer any
profile widening to a founder decision with that evidence.

Nothing here is a qualification: `passRuleSatisfied` is `false`, `qualificationRecordWritten` is `false`,
`hostFunctional` is `false`, `executionAuthorization` is `false`. Issuance stays T010 (NC-9, founder only).

## 1. Run facts

| Item | Value |
| --- | --- |
| Attempt | `t009-20261104c` (third attempt, full budget of 3 sessions like attempt 2) |
| `environmentSha256` | `af706ff0482d1f7eb658a4b9b85511651e64c66ca00285fad087dcf6b167dd3d` |
| `catalogSha256` | `422d0f1278638a5f5f87337b3b825de0f55f668558fba339ff0c9f7e93401cfa` |
| `bundleSha256` | `ccd227a9119b74439c59ae4d19946ee3e441270e4e3378fff3e858b3236397da` |
| Environment | macOS 27.2 (build 26B123), arm64, `claude` 2.1.292 (sha256 `97a01e5b...386138f`), `profileSha256` `08e3ff93...2af65294` |
| Pre-flight | dry run `ready`; `--self-check` `self-check-ok`: compile check `exec-denied`, five F4 probes as expected, fixture and launch-probe runs exit 0, `auth` stage ok (exit 0, token present), `sessionsStarted` 0 |
| Verdict | `bundle-written`; `sessionsStarted` 3 |
| Probes that passed | 27 of 32 (attempt 2: 22 of 32) |
| Quota | 5-hour window 9 % before and after every session (delta 0), weekly 59 %, `operator-typed-usage`, decision `proceed` for each |

Bundle integrity: the orchestrator verified the file and bundle hashes; `SHA256SUMS` lists the five bundle
files, then `operator/t009-run-t009-20261104c.txt` (terminal transcript) and `operator/t009-self-check.json`.
The dry-run output (`/Users/Shared/t009-dry-run.json`) names the founder's own account and is **not**
published. The identifier scan of the published files found only `/Users/braidlab/...` paths (approved for
publication, `founder-decisions-20261104c.json`), the runner-owned `/tmp/braid-probe-*` arena paths and Mach
service names; no founder account, e-mail address or token shape.

## 2. Outcome per effect

| Effect | Status | Not as expected | Notes |
| --- | --- | --- | --- |
| credential (7) | inconclusive | CRED-05 (not observed) | CRED-02 `mach-secd` excluded (`ABSENT`, not registered for the account) |
| filesystem (7) | **enforced** | none | FS-03 and FS-07 now pass (repaired controls); FS-07 `mach-spotlight` excluded (`ABSENT`) |
| network (9) | inconclusive | NET-05-CLI (not observed) | NET-02 `tcp-ipv6-literal` excluded (no IPv6 route); NET-06 allowed as expected |
| process (8) | not-enforced | PROC-03 memory and memory-burst allowed; PROC-08 cancel-settlement and outlive-timeout allowed | PROC-04 now denied (was allowed in attempt 2); PROC-07 `ptrace-sibling` excluded (control EPERM) |
| host | not functional | HOST-01 (not observed) | |

Progress against attempt 2: the repaired positive controls work (CRED-02, FS-03, FS-07, NET-02, PROC-07 no longer
fail on a control), PROC-04 passes through the run-tag attribution (#1075), and the filesystem effect is
enforced. The three session probes, PROC-03 and PROC-08 are what remains.

## 3. The three sessions: not observed

CRED-05, NET-05-CLI and HOST-01 each ended `exitReason` `exit-before-init`, `exitCode` 1, `authToken` `present`,
not timed out, settled. The CLI exited before its `init` event although a token file existed, and no quota was
spent. The dedicated account's `config_dir` gained `policy-limits.json`, its signature and stamp, and
`remote-settings.json` during session 1 (the CLI reached the network through the proxy that far) and nothing in
sessions 2 and 3 (`egress` empty in NET-05-CLI: no CONNECT at all, so it died before any network use).

The kernel sandbox denials collected during the three sessions (founder's Mac log, not published) name:
`/dev/dtracehelper`; `mach-lookup` of `notification_center`, `opendirectoryd.libinfo`, `securityd.xpc`, `logd`,
`SecurityServer`; `kern.bootargs`; the syslog socket; `file-read` of `/Library/Application Support`,
`/private/etc/passwd` (data and metadata), `/Library/Preferences/com.apple.security.plist` and
`.GlobalPreferences.plist`; `system-info vfs.disk-space`; `process-exec*` of `/usr/bin/security`, `/usr/bin/git`
and `/bin/sh`; `file-read-data` of `/usr/local/libexec/braid` and `/Users/braidlab/t009` (directory listing);
metadata of `/tmp`, `/home` and the run's stdout; `file-ioctl` on the run's stdin. The log does not say which of
them kills the CLI: several are probes or best-effort lookups that Bun tolerates. No profile rule is widened in
this change: any new allow needs a founder decision with evidence of which denial is fatal.

The evidence to decide that is missing because the CLI's standard error is discarded by the supervisor
(`stderr=DEVNULL`) and because a session that dies before `init` leaves nothing else. The new `startup` stage of
`--self-check` (section 6) makes it visible before another session is spent.

## 4. PROC-08 (cancel-settlement, outlive-timeout): allowed, a judge error

| Row | `escapedProcesses` | `survivingProcesses` | runner `survivors` (outlive-timeout) | cancel half `survivors` |
| --- | --- | --- | --- | --- |
| attempt 2, contained | 1 | 0 | 0 | 0 |
| attempt 2, contained-launch | 1 | 0 | 0 | 0 |
| attempt 3, contained | 1 | 0 | 2 | 8 |
| attempt 3, contained-launch | 1 | 0 | 5 | 7 |

The backend's own accounting is the same in both attempts: the leaver was seen leaving the group, the sweep
killed it, nothing survived the sweep. The row turned `allowed` because the runner's independent observation
changed: `survivors` is the nonce scan plus the diff of two `ps -U <uid>` snapshots of the dedicated account taken
around the run, and it counted every new process of that account. In attempt 3 two to eight new processes
appeared; PROC-04, run seconds earlier in the same attempt, saw none. The #1075 change left the survivor judge as it was
(`git show 92d00dc5` adds only evidence fields to `_helper_row`); what changed is the noise of the
account, and the judge had no way to tell a launchd agent from a survivor. The backend already states this in its
own accounting: "a GUI session's launchd agents appear at any time and are not the child's" (`_sweep`).

What the processes were is **not known**: the bundle records a count and no names. This is an inference from the
backend counts and from PROC-04 seeing none, not an observation. The fix records the names (section 5).

## 5. PROC-03 (memory, memory-burst): allowed, a watchdog that did not see the burst

Row facts (`independent.memoryWatchdog`, limit `LIMITS["memoryBytes"]` = 4 GiB = 4,294,967,296 bytes):

| Row | `peakBytes` | % of limit | samples | `limitExceeded` | memory | memory-burst | settled |
| --- | --- | --- | --- | --- | --- | --- | --- |
| contained (fixture) | 4,246,670,672 | 98.9 % | 154 | none | allowed | allowed | true |
| contained-launch | 4,332,437,984 | 100.9 % | 19 | `memory` | allowed | inconclusive | **false** |

The probe allocates the limit plus 256 MiB (106 % of it) and its forked child exits as soon as the last page is
touched. Four things follow from the row:

1. **The watchdog never saw the allocation it was meant to stop.** In the fixture row it measured at most 98.9 %
   of the limit in 154 samples while the child held 106 % and exited 0; both attempts completed ("allowed"). The
   measured footprint trails the allocation by at least 7 %: `ri_phys_footprint` counts a page the memory
   compressor holds at its compressed size, and the pages the probe touches (one byte each) compress to almost
   nothing. This is the likely cause; it was not isolated (no compressor counters were recorded).
2. **A burst that ends between two samples is lost.** The child exits right after allocating, so the last sample
   is the last chance; with a poll of 50 ms plus the cost of listing every process of the account, the final
   fraction of the allocation can fall between two samples. The footprint is read only while the process lives.
3. **The kill does work when the sample catches it.** In the launch-probe row the watchdog fired
   (`limitExceeded` `memory`, peak 100.9 %), but only during `memory-burst`: `memory` had already completed.
4. **The kill was then judged unsettled.** `escapedProcesses` 1 with `survivingProcesses` 0 (a dying member of
   the killed group seen on its way out) made `settled` false, so the parser did not read the missing outcome of
   `memory-burst` as a limit kill (`inconclusive`) and `row_outcome` treats an unsettled row as `allowed`. The
   survival probes already tolerated a swept leaver (`swept_settled`); PROC-03 did not.

## 6. Changes in this PR

- **PROC-08, PROC-03 (judge)**: a new process of the table diff counts as a survivor only when it is alive, not a
  zombie, and carries the name of an executable the profile lets a contained run start (the pinned interpreter,
  `claude` and its helpers, `sandbox-exec`, and the runner's own interpreter). The rest is recorded as
  `strayProcesses` (count and up to 8 sanitized names) in the row, and in the `cancel` object of PROC-08, so the
  noise level is evidence. A failing `ps` counts every new process (fail closed). Every row now reads `settled`
  through `swept_settled` (a member killed by the sweep while exiting is reported in `escapedProcesses`, not held
  against the row; anything that survived the sweep still is), and a limit kill is recognised on the same terms.
- **PROC-03 (watchdog)**: per process the watchdog takes the largest of the resident size, `ri_phys_footprint` and
  `ri_lifetime_max_phys_footprint` (`RUSAGE_INFO_V4`, offset 240, checked on macOS 27.2: it keeps the peak after the
  memory is freed), and polls every 10 ms (was 50 ms) once the tree holds a quarter of the limit. The two memory
  attempts now exceed the limit by 1 GiB (was 256 MiB) and hold the allocation for two seconds, so the watchdog has
  several samples at the burst. The catalog states the residual: a process that exceeds the limit and exits
  between two samples is not stopped.
- **Kernel limit tried and rejected**: on macOS 27.2, `setrlimit(RLIMIT_AS or RLIMIT_DATA)` refuses (`EINVAL`) any
  value below the address space the process already has (466 GiB for a bare Python), so 4 GiB cannot be set. A
  value of "address space at start plus 1 GiB" is accepted, is enforced (`mmap` of 2 GiB fails with `ENOMEM`) and
  survives `exec`, but `RLIMIT_DATA` also counts a `PROT_NONE` reservation (an 8 GiB one failed), and a JavaScript
  runtime reserves address space in bulk. It was not applied to `launch`: it could stop the CLI at startup and
  cannot be tested without a session. See the open questions.
- **Startup stage**: `--self-check` ends with `startup`, the probe runner's session launch with the model made
  unreachable (below).

### The `startup` stage and why it cannot bill

It builds the exact `claude -p ... --output-format stream-json ...` argv of `build_plan`, the same prompt on stdin,
and calls the same `MacOSContainment.launch` (same `launch` profile, environment, token and pre-session check) with
two additions: `capture_stderr=True` and `no_egress=True`.

- `no_egress` sets `EgressProxy.refuse_all` after the pre-session check (which needs the proxy for NET-06) and
  clears it in a `finally`. With it, `_tunnel` raises `_Refused("no-egress-stage")` and answers `403` after the
  CONNECT line is parsed and **before** the allow-list test, the TLS hello or any upstream `connect`; the upstream
  socket is created only after those, so no connection to any host is ever opened (a unit test uses a `connect`
  that fails the test if called).
- The profile allows the child no network except `localhost:<proxy port>` (NET-01 to NET-08 are denied in the same
  bundle), so the proxy is the only way out. A model request cannot leave the machine and no token is exchanged.
- The stage reads the proxy's own counter delta for the launch and reports it; any `allowed`, `bytesUp`,
  `bytesDown` or `upstreamFailed` ends the self-check as `self-check-egress-leak` (it cannot happen by construction;
  the counters are the check). No quota reading is taken, no session is reserved, no bundle is written.
- Reported: `reachedInit` (the `init` event is in the stream), `exitCode`, `reason` (the closed set of
  `session_exit_reason`), `authToken`, the egress counters, and `stderrTail`: the last 20 lines of the child's
  standard error (captured by the supervisor, last 8 KiB), each reduced to printable ASCII and passed through the
  bundle's secret scan (listed credential literals including the token, token shapes, long opaque runs); a line
  that trips it becomes `<redacted:rule>`, `/Users/<operator>` becomes `<operator-home>` and the operator account
  `<operator>`. A tail cut at the capture limit loses its first line, which could be half a token.
- It is diagnostic: it does not change the verdict, because a CLI that cannot reach its API may fail for that
  reason alone. If `reachedInit` is true the fatal denial of attempt 3 is not in startup and the next suspect is
  the network phase; if false, `stderrTail` should name it. The first session of attempt 3 did reach the network
  (it wrote `policy-limits.json`), so a stage with the network refused may fail earlier or differently than a real
  session; the orchestrator should read it with that in mind.

## 7. Follow-ups and open questions

1. Run `--self-check` on the new commit and read `startup`. Decide from its `stderrTail` which denial, if any, to
   widen (founder decision with that evidence); nothing is widened here.
2. After the self-check, a new attempt (new name; its session budget is the founder's call, as for attempts 2 and 3)
   re-runs PROC-03 and PROC-08 with the fixes.
3. Founder question: should the memory limit also be a kernel limit for the probes (not for `launch`), using
   "address space at start plus the limit"? It would make PROC-03 deterministic but would test a mechanism the
   production CLI does not run under.
4. `stderr` of the CLI stays discarded in real sessions; only the `startup` stage captures it.
