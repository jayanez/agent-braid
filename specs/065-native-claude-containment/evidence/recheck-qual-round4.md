# SPEC-065 T009 round 4: security re-check of the touched lines

Date: 2026-11-04. Base `0eb75d84` (develop). Scope: every changed line of `harness_containment_macos.py` and
`harness_qualification_probes.py`, the self-check in `scripts/har_t009_attempt.py`, and the tests. Founder
acceptance of the round: 2026-11-04 ("OK, adelante"); result of the attempt that motivates it:
`t009-attempt3-result.md`. `harness_transport_claude.py` and every driver other than `har_t009_attempt.py` are
unchanged. Nothing native ran: the checks are code reading, unit tests, three independent reviews (security,
quality, simplification; findings applied below) and four plain-Python experiments on `setrlimit` and
`proc_pid_rusage` (no sandbox, no `claude`). This is a re-check, not a qualification.

## Verdict: GO for `--self-check` and then a new attempt, conditional on the orchestrator's written GO

No SBPL rule changed: the three profiles render byte for byte as before (`profileSha256` unchanged).

## Hashes that move

| Hash | Moves | Why |
| --- | --- | --- |
| `environmentSha256` | yes | the backend module hash changes (watchdog, proxy flag, launch options); recomputed by the dry run |
| `catalogSha256` | yes | the probes module bytes (runner, judge, process filter, redaction) and the PROC-03 helper source and residual change; value at this head `4433fa49...e5019` (recompute at the final commit) |
| profile hashes (`fixture`, `launch`, `launch-probe`), `claude`, interpreter, `sandbox-exec` pins | no | unchanged |
| `bundleSha256` of `t009-20261104b` and `t009-20261104c` | no, but each verifies only at the commit it ran at (`a4d5c294` for `b`): the catalog hash binds the module source |

## Touched lines

### Backend (`harness_containment_macos.py`)

- `_footprint`: reads `RUSAGE_INFO_V4` (296 bytes, 37 words) and returns the larger of `ri_phys_footprint`
  (word 9) and `ri_lifetime_max_phys_footprint` (word 30). The offset was checked on macOS 27.2 against a process
  that allocated 300 MiB and freed it: word 30 kept 306.8 MiB after the free, word 9 fell to 6.7 MiB. A failing
  call returns 0 as before (the resident size still counts). The measure only grows, so the watchdog stops no
  fewer runs than before; a CLI whose lifetime peak exceeds 4 GiB while its current footprint does not is now
  stopped (a real excess, counted once). GO.
- `_watch`: sleeps 10 ms instead of 50 ms once the measured tree exceeds a quarter of the limit. More syscalls
  only while a run is already memory-heavy; no change to what stops a run. GO.
- `EgressProxy.refuse_all` and the `_tunnel` check: when set, the CONNECT is answered `403` and counted
  `denied:no-egress-stage` before the allow-list test, the TLS hello or the upstream `connect`. The flag is
  written only by `launch(no_egress=True)`, after `_pre_session` and under the exclusive lock, and cleared in a
  `finally` (also when `_spawn` raises; tested). A plain attribute read in the proxy thread: a write that races a
  connection can only refuse a connection that would otherwise be allowed, never the reverse, because the flag is
  set before the child is spawned and cleared after it is reaped and swept. GO.
- `launch(capture_stderr, no_egress)`: `stderr` goes to `<run_dir>/stderr`, opened by the supervisor and inherited
  (the child opens nothing, so the profile is unchanged); `RLIMIT_FSIZE` bounds it; only the last 8 KiB are read, in
  the `finally` before `_remove_tree`, into `ContainedHostRun.stderr_tail`. The tail is **not** copied into
  `run_evidence` (tested) and `compare=False, repr=False` keep it out of equality and logs. Callers must redact
  it; the only caller is the `startup` stage, which does. Without the options the behaviour is as before
  (`DEVNULL`). GO.

### Probes (`harness_qualification_probes.py`)

- `PROC-03` `memory` and `memory-burst`: the allocation is the limit plus 1 GiB (was 256 MiB) and is held for two
  seconds before the child exits. Real memory use on the founder's Mac rises from about 4.5 GiB to 5 GiB only if
  the watchdog fails to stop it. The residual is stated in the catalog (`residual`): exit between two samples is not
  stopped; no kernel limit backs the watchdog (experiment below). GO.
- Judge: `parse_helper_output` and `_helper_row` read `swept_settled(result)` instead of `result.settled`. It is
  `True` when the group settled, or when the sweep killed leavers and **nothing survived the sweep**
  (`surviving_processes == 0` with `escaped_processes > 0`); with `surviving_processes` `None` it is the strict
  flag. A run that left a survivor, or whose sweep failed, is still unsettled, hence `allowed`. The change only
  turns an `allowed` caused by a member that was dying into the limit kill that it was. GO.
- `_new_processes`, `live_process_names`, `descendant_names`: the table diff keeps a new process only when `ps -p`
  lists it, its state is not `Z` and its executable basename is one the exec allow-list lets a contained run start
  (policy `claude`, interpreter and helpers, `sandbox-exec`, the runner's own interpreter, and the generic
  `Python`/`python`/`python3`/`python3.x` names so that a different build of the same interpreter is never
  missed). Everything else is recorded as `strayProcesses` (`count` and at most 8 names, each through
  `bundle_safe_name` and a character-class check). `ps` failing keeps every new process (fail closed); a
  runner built without `child_names` (all tests that predate it) keeps the old behaviour. What it can miss: a
  survivor that execs a binary the profile does not allow is impossible by the profile; a survivor that renames
  its executable cannot (the name is the exec path, not `argv[0]`); a survivor that is a zombie has exited. A
  survivor whose name is allowed but whose environment is scrubbed is still caught by this diff (it keeps the
  name), so the independent check is not weaker than before for the case PROC-ESC-1 describes. GO.
  Residual: the cause of attempt 3's extra processes is inferred, not observed; the row now records the names.
- `reached_init`, `redact_stderr_tail`: scan order is secret scan on the printable-reduced line first (listed
  literals, shapes, long runs), account replacement second, so a line that trips the scan is never partly
  published; `<redacted:rule>` names the rule only. A tail at the capture limit drops its first line. The
  founder's account is replaced by `<operator>` and `/Users/<account>` by `<operator-home>`; other paths, for
  example `/Users/braidlab/...`, stay (approved for publication). GO. Residual: a secret split over two lines or
  rewritten (base64 of a token) is not recognised; the stage prints 20 lines of a CLI that holds one token and
  the scan list contains it, so a plain leak is caught.

### Self-check (`scripts/har_t009_attempt.py`)

- `startup_stage`: the argv is `build_plan(ClaudeRequest(..., model="haiku", max_turns=1), PROBE_PROMPT)` with the
  pinned `claude` first, the stdin is `PROBE_PROMPT`, the call is `backend.launch(..., capture_stderr=True,
  no_egress=True)`: the same `launch` profile, environment, token and pre-session check as a real session. It
  skips the transport's quota gate and `init` watch on purpose (no model request can happen; no usage reading is
  taken). It reports the proxy's counter delta and ends the self-check with `self-check-egress-leak` if a tunnel
  opened. It cannot raise the verdict to ok or lower it for anything but a leak. Wall bound 45 s. GO.
- `run_self_check` reads `credential_inventory(config_dir)` (as `run_attempt` does) for the redaction list. GO.

## Why `startup` cannot bill

A model request needs a TCP connection to `api.anthropic.com:443`. The `launch` profile allows the child
`network-outbound` only to `localhost:<proxy port>` (the five F4 probes, NET-01 to NET-08, deny the rest in the
same bundle), and during the stage the proxy refuses every CONNECT before opening an upstream socket. The counters
of the launch are reported and a non-zero `allowed`, `bytesUp`, `bytesDown` or `upstreamFailed` is a verdict. The
`setup-token` credential is in the child's environment as for every session, but with no route out it is never
sent anywhere.

## Experiments (plain Python on the founder's Mac, no sandbox, no CLI)

- `setrlimit(RLIMIT_AS|RLIMIT_DATA, 1/8/64 GiB)` on a bare Python: `EINVAL`; 1 TiB: accepted. The process's address
  space is 466 GiB.
- `address space + 1 GiB`: accepted for both; `mmap` of 2 GiB then fails with `ENOMEM`; the limit survives `exec`.
- `RLIMIT_DATA` at `address space + 1 GiB`: an 8 GiB `PROT_NONE` `mmap` also fails, so reserved address space counts.
- `proc_pid_rusage(RUSAGE_INFO_V4)`: word 30 is the lifetime peak footprint (above).

Conclusion: a kernel limit exists but is relative, counts reservations and could stop the CLI at startup; it is not
applied (open question in the result).

## Residuals

- PROC-03: exit between two samples (10 ms once the tree is above a quarter of the limit); a footprint that the
  compressor keeps below the allocation by more than the 1 GiB margin. Both are stated in the catalog.
- PROC-08 and PROC-04: the table-diff filter relies on the executable name; PROC-ESC-1 (environment-scrubbing
  leavers) stays as in round 3.
- `startup` runs with the network refused; a CLI that needs the network before `init` fails there for that reason
  and the stage cannot tell.
- The attempt-3 sandbox denials are not widened; each addition needs a founder decision with the `startup`
  evidence.

## Validation

Focused: `tests.test_harness_containment_macos`, `..._qualification_probes`, `test_har_t009_attempt`,
`test_har_t009_setup` all pass (552 tests, 3 skipped on non-macOS or live-only cases). The required profile ran
once on the final candidate (see the PR).
