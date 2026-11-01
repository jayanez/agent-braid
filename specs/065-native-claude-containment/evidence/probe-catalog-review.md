# SPEC-065 T008: independent security review of the probe catalog and backend policy

**This review is not a qualification.** It issues no record, qualifies no effect,
authorizes no native session, probe or account setup, and changes no code. `executionAuthorization`
stays `false`. Findings are inputs to follow-up tracks (T005/T007 fixes) and to the founder; nothing
here substitutes for the T009 live attempt or the T010 human issuance.

## Record

| Item | Value |
|---|---|
| Date | 2026-11-01 |
| Task | SPEC-065 T008 (REQ-010 / SC-010) |
| Reviewed commit | `49ebe45ca367fba0802258d6ce29d354c6c45c34` (`origin/develop`; the reviewed code is byte-identical to `e0559555`, the T007 merge, since the intervening commits touch only tracking and SPEC-066 docs) |
| Reviewer | A separate Claude Code derived-track session (Sonnet 5.5), distinct from the sessions that wrote T005/T006/T007. Independent in session and context, **not** a human review and not a different model family; the founder may want a human or second-family pass before T009. |
| Method | Static adversarial review plus reading the unit tests. Nothing native ran: no `sandbox-exec`, no `claude`, no dedicated account, no network probe, no code executed from the reviewed files. Claims about macOS sandbox behavior are marked *hypothesis* where they rest on knowledge rather than on the T005 scratch experiments in `evidence/t005.json`; they are for T009 to confirm or refute. |

### Files reviewed (SHA-256 at the reviewed commit)

| File | SHA-256 |
|---|---|
| `agent_braid/harness_containment_macos.py` (1006 lines) | `dfa7fda83f782edc32150a942647df3c480dd4bf0fd01ef771ce3402e20c3c06` |
| `agent_braid/harness_qualification_probes.py` (1476 lines) | `5f581b6eca7fe6ea98d1ab248bc04703fca0a24241855ea684b334e59333a7c2` |
| `agent_braid/harness_transport_claude.py` (266 lines) | `e98c4db0e279b0a07a90a94d7c2f9a519e29dbdc0ca23c9b123dc3dc043fa19e` |
| `agent_braid/harness_host_claude.py` (read for `ENV_DENY`, `build_plan`, `SUBSCRIPTION_KEY_SOURCES`) | `e31df98faaf998b023961daad4577c206fca0f622e156c27624952d7d739267b` |
| `agent_braid/harness_lab.py` (read for `_settle`, `ENFORCED_EFFECTS`) | `c6a4f43b6981ceec8ca4690ed9b4e71ae1133c8d323c5bfcce0abe11cd0e3744` |
| `tests/test_harness_containment_macos.py` | `e9a79201aa02153d68888fdd99161d71e118a75f1be4d56dc93f1bddc0cb01d3` |
| `tests/test_harness_qualification_probes.py` | `a03abd295085238ec24afa54874afdb33738de641e2d2ca5263b0187ddec82c3` |
| `specs/065-native-claude-containment/evidence/founder-decisions-20261031.json` | `9aa51097b838c255ca92ecfb6f93a9fcea373d31c8a73ea6d45e635ae45e692e` |
| `specs/065-native-claude-containment/contracts/containment-qualification.md` | `8dda4230c0281c595d803529363a6bd5e34251adade65369a0797193902715ce` |
| `docs/adr/0035-native-claude-laboratory-containment.md` | `5bbd4ef4c56db0b1ea4d4f7a60b797a0e700398d32fdc9f5ea21235b20eb7b31` |

Also read: `spec.md`, `plan.md`, `tasks.md` (T005, T006, T007, T008), `contracts/native-profile.md`,
`evidence/t005.json`, `t006.json`, `t006-live-output.json`, `t007.json`. The catalog hash recorded
in `t007.json` is `4445ba5b42dccc099c7f7e440f1cfd240f85b00ff0dc24e2a6406345a7d44d52`; the file hashes
of `t007.json` match the files above. Line numbers below refer to the reviewed commit.

## Summary

34 findings: 0 critical, 4 high, 16 medium, 12 low, 2 informational.
Primary dispositions: 12 fix-in-T005, 16 fix-in-T007, 3 needs-founder-decision, 3 residual-risk.

None of the findings is a demonstrated escape: nothing native ran. The high findings are of two
kinds. RV-01 and RV-02 make the process effect impossible to pass as written (the attempt would
fail closed, which is the right direction but wastes the live budget). RV-03, RV-04 and RV-05 are
**false-pass risks**: the catalog or the NC-11 pre-session check can report `denied` without having
exercised the thing it names.

**Recommendation.** Do not start T009 until RV-01 to RV-05, RV-14 and RV-15 are fixed or the founder
explicitly defers them, and RV-21 (keychain and profile growth) is decided. Any change to the SBPL
profile, the helpers or the pass rule after this review voids its coverage of the changed part and
needs a delta review. The profile will almost certainly grow once `claude` is first run under it
(dyld, sysctl, TLS roots, keychain), which re-opens every "policy broader than decisions" question.

### What looks sound (so the findings are read in proportion)

- Deny-default SBPL without `bsd.sb`/`system.sb` import; no `mach-lookup`, `iokit`, `sysctl`,
  `ipc-*`, `network-bind`, `network-inbound`, UDP, raw or Unix-socket rule exists, and the unit test
  asserts that exact negative set (`tests/test_harness_containment_macos.py:169`).
- Environment built from scratch (no `DYLD_*`, `NODE_OPTIONS`, inherited tokens), `close_fds=True`,
  the status pipe made non-inheritable before `exec`, `start_new_session`, rlimits applied in a
  preamble that fails closed, and kill/settle/sweep in a `finally` on every exit path.
- The qualification, host qualification, OS window, account uid, mechanism hash, pinned executables,
  environment hash and expiry are all re-verified before every run; the proxy refuses ECH, plain
  HTTP, other methods and SNI mismatches.
- The probe helpers emit only outcome and errno, never file content; the bundle holds no raw transcript;
  the runner has no code path that writes a qualification record.
- The pass rule is monotone toward `allowed`: independent observations can only escalate, a failed
  control makes a denial `inconclusive`, and an observed escape is never hidden by a failed control.

## Findings

Severity: **High** = a false pass is possible, or the qualification cannot succeed as built.
**Medium** = a real coverage gap or a policy/decision mismatch. **Low** = hardening or hygiene.
Disposition: `fix-in-T005` (backend/policy), `fix-in-T007` (catalog/runner), `residual-risk`,
`needs-founder-decision`. "T009 blocker" means the live attempt cannot produce a pass until fixed.

### High

**RV-01 (High, T009 blocker): a swept group-leaver is judged as an escape, so PROC-04 and PROC-08 can never pass.**
Location: `harness_containment_macos.py:951` (`settled = ... and escapedProcesses == 0`), `:995-1006`
(`_sweep` returns `len(escaped)` whether the survivors were killed or are still alive after 40 tries);
`harness_qualification_probes.py:1238-1246` (`_survival_state`), `:1316`.
The double-fork and `setsid` helpers always leave the group (the profile allows `process-fork`; `setsid` is
not gated). The sweep kills them, but any count above zero makes the run unsettled, and
`_survival_state` maps `not result.settled` to `allowed`. The contained row for PROC-04 and PROC-08 is
therefore `allowed` whenever the sweep works, and also when it fails; the two cases are
indistinguishable in the evidence. The `process` effect is then permanently `not-enforced`.
Disposition: **fix-in-T005**: report `escapedProcesses` (seen leaving the group) and
`survivingProcesses` (alive after the final sweep iteration, including the 40-iteration exhaustion
case) separately in `HostRun`/`ChildResult`-adjacent evidence. Keep `settled` strict for production
runs (a leaver taints the measurement). **fix-in-T007**: judge PROC-04/PROC-08 on
`survivingProcesses == 0` plus an independent post-run scan (RV-12); record `escapedProcesses > 0` as
an informational "swept" observation. Rationale: the contract text is "survive kill", and the
sandbox still confined the leaver while it lived. This answers the open item left to T008: the
backend keeps its strict `settled`, the judgement changes.

**RV-03 (High): NET-05-CLI cannot be obtained honestly and passes vacuously if a tap supplies "nothing seen".**
Location: `harness_qualification_probes.py:774-784` (`classify_session`), `:822-846` (driver), `:805-812`
(self-test); `harness_containment_macos.py:494-551` (`EgressProxy` keeps no counters).
`unexpectedDirect` has no source: a direct connection attempt is denied by the kernel and the proxy never
sees it, so nothing in the design can count it. `admitted` is a subset of the allowed endpoints by
construction (the proxy admits nothing else), so `set(admitted) <= endpoints` is a tautology.
The only way to reach `denied` is for a future tap to assert `unexpectedDirect: 0`, and the classifier also
returns `denied` for `admitted == []` (no traffic seen at all), which proves nothing about the CLI.
Disposition: **fix-in-T005**: give `EgressProxy` thread-safe counters (admitted CONNECT targets, refused
requests with reason class, bytes, connection count) and expose them. **fix-in-T007**: define the verdict as
"`admitted` is non-empty and equals the allowed set, every refusal is recorded, and no other
destination appears"; make `admitted == []` `inconclusive`; drop `unexpectedDirect` or source it
from the sandbox's own denial log if the founder wants direct-attempt counts (that needs a log-access
decision, so it is optional). Until then NET-05-CLI keeps `network` at `inconclusive`, which is the
safe direction.

**RV-04 (High): the probes and the NC-11 pre-session check exercise only the `fixture` profile, never the `launch` profile Claude runs under.**
Location: `harness_containment_macos.py:218-248` (two different profiles), `:805-826` (`run_probe` uses the
`fixture` entry), `:764-776` (`_run_probes`), `harness_qualification_probes.py:1155-1164`, `:1458-1476`.
The `launch` profile differs: it adds read/write on `config_dir`, drops the interpreter, and allows exec of
`claude` and helpers. Every FS/NET/CRED/PROC escape probe and every F4 probe runs under `fixture`, so the
rules that exist only in `launch` (the one place a persistent, credential-bearing writable tree is
granted) are covered by a compile check (exec of `/usr/bin/false` denied) and by HOST-01 alone.
A rendering bug in the `launch`-only lines, or a future widening there, would pass F4 on every session.
Disposition: **fix-in-T007** with a **T005** hook: add a probe-only profile variant `launch-probe`
rendered by the same function, identical to `launch` except that the exec allow-list also contains the
pinned interpreter; bind its hash in the environment hash; add a unit test that the diff between
`launch-probe` and `launch` is exactly that one exec literal; run the catalog (and the F4 subset)
against it. Alternative, weaker: a render-level test asserting the allowed write/read set of `launch` plus
FS probes aimed at `config_dir`'s parent, siblings and symlinks (RV-09).

**RV-05 (High): `gaierror` is classified `denied`, so NET-01, NET-05 `direct-allowed-host` and NC-11's NET-01 cannot detect a network-rule regression.**
Location: `harness_qualification_probes.py:122-123` (`_classify`), `:306-308` (NET-01), `:325`
(NET-05), `harness_containment_macos.py:79-80` (`F4_PROBES`).
Under the profile the child cannot resolve names (mDNSResponder is reached over a Unix socket and mach, both
denied), so `getaddrinfo` fails before any `connect`. NET-01 is "TCP by name", so it is denied by name
resolution failure regardless of whether `network-outbound` is correctly restricted. If a profile
regression allowed all outbound TCP, NET-01 would still report `denied`, and NC-11 chose NET-01 as
the pre-session network check. The positive control cannot catch this, because it only shows the
uncontained attempt works. Offline machines and transient DNS errors also turn into `denied`.
Disposition: **fix-in-T007**: treat `gaierror` as `inconclusive` for connect-level attempts and as `denied`
only for the explicit DNS attempt in NET-03; make the F4 network probe deterministic and offline-capable
by adding a connect-level attempt to a runner-owned loopback listener (as NET-04 does) and to a literal
public IP, keeping the by-name attempt as an additional one. The F4 subset is a founder decision (NC-11): the
probe ids stay, the attempts inside NET-01 change, which the founder should be told. Resolve the `direct-allowed-host`
attempt with a runner-resolved literal address of the allowed host (`A["allowed_ip"]`), not the name.

### Medium

**RV-02 (Medium, T009 blocker): the PROC-08 cancellation half cannot be driven.**
Location: `harness_containment_macos.py:825` (`cancel=None` for fixture runs), `:828-851`
(`launch` accepts only the Claude argv), `harness_qualification_probes.py:1328-1343` (`_cancel`).
Cancellation is wired only into `launch`, which refuses any `argv[0]` other than the pinned Claude
executable; `run_probe` has no `cancel` parameter. A `cancel_check` driver therefore has nothing to call, and
the row stays `inconclusive`. Disposition: **fix-in-T005**: add an optional `cancel: threading.Event`
to `run_probe` (probe entry only, same checks). **fix-in-T007**: a driver that starts the PROC-08
helper, sets the event after a fixed delay, and reports survivors and `cancelled` from the settled run.

**RV-06 (Medium): FS-06 is non-discriminating.**
Location: `harness_qualification_probes.py:280-298`, `:1068-1072`.
`inherited-descriptor` returns `False` ("explicit refusal") when no descriptor is open, and the contained
child never receives one (`close_fds=True`), so it is `denied` for every possible profile. `device-node`
opens `/dev/zero`, which is simply absent from the profile; `fifo` opens a FIFO that sits in the arena,
outside the write set, so it repeats FS-04.
Disposition: **fix-in-T007**: replace the first attempt with a descriptor inventory (loop `fcntl(F_GETFD)` /
`F_GETPATH` over a wide range) that must find exactly {0, 1, 2}, with 1 and 0 resolving to the run files, and
count any other open descriptor (the supervisor's lock file, proxy sockets, status pipe) as `allowed`; the
control already passes a descriptor, so it stays valid. Add `/dev/tty`, `/dev/ptmx`, `/dev/fd/N` and a
FIFO created inside the candidate directory. Do not add `/dev/disk*`, `/dev/bpf*` or `/dev/oslog` as
counted attempts (their uncontained controls fail for a non-root account); note them as covered by the
deny-default.

**RV-07 (Medium): FS-07's denial comes from the exec allow-list, not from Spotlight isolation.**
Location: `harness_qualification_probes.py:299-305`; control needs an indexed volume (`t007.json`).
`mdfind` is not on the exec allow-list, so the exec fails with `EPERM` before any metadata query. The
real risk is the `mds` services reached over mach, which this probe never tests.
Disposition: **fix-in-T007**: replace with `mach("com.apple.metadata.mds")`, `...mdwrite` and
`com.apple.Spotlight` lookups (control: lookup succeeds uncontained, which needs no indexed volume);
keep the `mdfind` attempt as informational.

**RV-08 (Medium): no systematic mach/XPC, IOKit, shared-memory, sysctl or process-listing coverage.**
Location: `harness_qualification_probes.py:342-345`, `:350-354`, `:365-383`, `:459-463`.
The blanket rule is "no `mach-lookup`", but the catalog samples about ten service names. The classes the
task named have no probe: IOKit (`IOServiceOpen`), POSIX and SysV shared memory and semaphores
(`shm_open`, `sem_open`, `shmget`), `sysctl` reads (`kern.proc.all`, `hw.*`), `proc_listpids`
(the backend itself relies on it, the child must not), `kqueue` proc/vnode watches, TCC (`tccd`), and
`launchd`/XPC beyond `launchservicesd` and `appleevents`.
Disposition: **fix-in-T007**: a mach sweep. The runner, outside the sandbox, enumerates the dedicated user's
global and per-user launchd service names (`launchctl print` of its domains, captured at run time and written
to the bundle as a name list and hash); the contained helper calls `bootstrap_look_up` on every name; any
status 0 is `allowed`; the control is the same loop uncontained (non-empty successes required). Add
`ipc-posix-shm`, `ipc-sysv-shm`, `iokit-open`, `sysctl-read` and `process-info-listpids` attempts, each with
an uncontained success as control. Confirm at T009 that `bootstrap_look_up` returns 1100 (not-privileged) for
sandbox denials and 1102 for unknown services, since `mach()` (`:202-209`) maps only 1100 to `denied`
(*hypothesis*, from the Mach headers).

**RV-09 (Medium): filesystem probes never test the boundary of the allowed set or macOS-specific primitives.**
Location: `harness_qualification_probes.py:236-241` (FS-01 targets), `:247-267`, `:274-279`,
`:886-935` (arena layout), `harness_containment_macos.py:241-242`.
All decoys sit far from the allowed set, inside an arena that is not adjacent to `run_root`. An over-broad
rule (the `subpath run_root` metadata rule at `:241`, a parent of `TMPDIR` such as `run_dir`, a sibling
sharing the candidate's name as a prefix, `config_dir`'s parent or siblings in `launch`, the interpreter root
being writable) would not be hit. Also missing: rename or link out of the candidate (FS-05 covers only
outside-to-inside), `clonefile`/`fcopyfile` from outside into the candidate, the data-volume and root-volume
aliases (`/System/Volumes/Data/<path>`, `/Volumes/<boot volume>/<path>`, `/private/var` vs `/var`,
`/tmp` vs `/private/tmp`, `/.vol/<fsid>/<inode>`), write-then-exec and write-then-`dlopen` from the candidate
(the exec literal list and `file-map-executable` are the defence), `chflags`, ACL and extended-attribute writes,
and the real dedicated-user home and `~/Library/LaunchAgents` (only decoys under the arena are used).
The hard-link attempt (FS-02) needs a target the dedicated user can write; the arena target qualifies, but a
hard link to a file in the dedicated user's own tree (for example a dotfile) is the realistic case.
Whether `file-link` checks the source path is *hypothesis*; the probe settles it.
Disposition: **fix-in-T007**: add adjacent decoys created by the runner next to the real allowed paths
(candidate prefix-sibling, `run_dir`, `run_root`, `config_dir` parent/sibling, interpreter root) and the
attempts above; add real-path attempts for the dedicated user's `~/Library/LaunchAgents` guarded by a
cleanup that removes any file created.

**RV-10 (Medium): network coverage omits LAN, link-local, IPv6 UDP and proxy-parsing attacks; NET-05 omits the "wrong SNI/CONNECT host" case the contract names.**
Location: `harness_qualification_probes.py:309-330`; contract table NET-05.
Missing: RFC 1918 and link-local targets (gateway, `169.254.169.254`, `fe80::`), IPv6 and multicast UDP
(mDNS `ff02::fb`), connect to the host's own non-loopback interface address on the proxy port (it tests what
SBPL `localhost` means; the T005 scratch run covered only `127.0.0.1` and `::1`), `0.0.0.0` and IPv4-mapped
addresses. NET-05 has three attempts and none sends a CONNECT to the allowed host with a different SNI,
different case or port, a trailing dot, userinfo, an absolute-URI request, a split or pipelined ClientHello.
These need no sandbox: they test the proxy, which is a trusted component of the qualification (NC-1).
Disposition: **fix-in-T007**: add the attempts to NET-02/NET-03, and a proxy-parsing block run against a live
`EgressProxy` with a fake upstream (both uncontained and contained), each expecting an explicit `403` or a
close before upstream connect.

**RV-11 (Medium): PROC-07 omits ptrace, `task_for_pid` and, above all, signalling the supervisor.**
Location: `harness_qualification_probes.py:464-478`; contract row PROC-07.
The supervisor runs as the same uid as the child (`_check_mechanism`, `:714`) and is the highest-value
same-user target; the only signal attempt goes to a synthetic sibling.
Disposition: **fix-in-T007**: add `kill(getppid(), 0)` and a harmless `SIGUSR2`-style probe to the supervisor
(a handler-free test hook, or signal 0 only), `ptrace(PT_ATTACH)` and `task_for_pid` against the sibling and
the supervisor. Controls: signal 0 and `PT_ATTACH` against a same-uid, non-hardened sibling succeed;
`task_for_pid` may fail uncontained, in which case it is `inconclusive` and must be listed as such rather than
hidden.

**RV-12 (Medium): the independent survivor scan is cooperative.**
Location: `harness_qualification_probes.py:1167-1177` (`scan_processes`), `:1307-1309`.
It finds processes whose command line contains the arena nonce. A survivor that rewrites its argv or title
or re-execs is invisible; the probe helpers are cooperative, so the probe cannot show that a hostile
survivor would be caught.
Disposition: **fix-in-T007**: diff the dedicated user's process table by `(pid, start time)` before and
after each helper run, independently of the backend's own accounting (for example `ps -U <account>` with
`lstart`), and keep the nonce scan as a second signal.

**RV-13 (Medium): limit denials are not attributed to the intended mechanism, and the memory limit is a sampled watchdog.**
Location: `harness_qualification_probes.py:140-160` (`limit`), `:1191-1215` (`parse_helper_output`),
`harness_containment_macos.py:385-390`, `:961-981`.
A forked limit child killed by any signal, or exiting with `ENOMEM`/`ENFILE`, is `denied`; a terminal attempt
with no report is `denied` whenever the leader was killed and settled, including an output-cap kill. The row
does not record the backend's `limitExceeded` or `outputTruncated`. Memory is enforced only by a 50 ms poll of
resident bytes (macOS refuses `RLIMIT_AS` below the current address space); resident size excludes compressed
pages and misses a burst between polls. PROC-03's memory attempt touches 1 MiB steps and measures only a slow
allocation.
Disposition: **fix-in-T007**: copy the backend's stop reason (`limitExceeded`, `timedOut`, `outputTruncated`)
into the row and require `limitExceeded == "memory"` for a memory denial; add a fast-burst allocation attempt.
**residual-risk (T005)**: memory is a best-effort DoS bound, not a confinement property; consider
`ri_phys_footprint` from `proc_pid_rusage`, which includes compressed memory, in place of resident size.

**RV-14 (Medium): the runner, judge and arena are not bound to any hash, and the catalog-to-policy binding is never checked.**
Location: `harness_qualification_probes.py:609-638`, `:1458-1476`; `harness_containment_macos.py:273-276`.
`catalog_sha256` covers the probe list, attempt names and helper sources. `judge_probe`, `summarize`,
`row_outcome`, `Arena`, `parse_helper_output`, `classify_session` and the executors are outside it and outside
`_component_hashes()` (which hashes only `harness_containment_macos`, `harness_lab`, `harness_host_claude`).
Weakening the pass rule or moving the decoys changes neither the environment hash nor the NC-9 "probe
catalog" re-qualification trigger. `policy_binds_catalog` (`:636`) is called nowhere outside tests;
`make_f4_probe_runner` does not verify that `backend.policy.probe_catalog_sha256 == CATALOG_SHA256`, so a
session can run today's probes against a qualification issued for another catalog.
Disposition: **fix-in-T007**: make `run` in `make_f4_probe_runner` return `error` unless
`policy_binds_catalog(backend.policy)`; include a hash of the runner/judge/arena source in
`catalog_document` (for example the file hash of `harness_qualification_probes.py`, read by path so there is no
import cycle). **fix-in-T005** (same finding): add `harness_qualification_probes.py`, `harness_transport_claude.py`
and `harness_quota.py` to the environment-hash component list by reading their files.

**RV-15 (Medium): the NC-10 / NC-6 stop rule and the quota readings are not implemented in the runner.**
Location: `harness_qualification_probes.py:822-846` (docstring: "No quota reading ... is wired"), `:1345-1366`,
`:1349`.
NC-10 requires pre/post readings per live session and stopping the attempt if one session exceeds 2 %.
The driver records only the admission decision; no post-reading is taken or compared, the next session
starts regardless, and `quota` stays `None` for NET-05-CLI. The 3-session cap is counted per runner instance,
so a second `run()` after a failure resets it.
Disposition: **fix-in-T007**: `SessionResult.quota` carries `pre` and `post` readings supplied by the
orchestrator; the runner stops further session probes when `post - pre > 2` or a reading is missing or stale,
records the stop in `quota.json`, and persists the session count in the bundle directory so a retry cannot
exceed three per attempt. The readings themselves stay an orchestrator act (NC-6 source).

**RV-16 (Medium): the "dedicated" account is never verified to be dedicated or unprivileged.**
Location: `harness_containment_macos.py:710-714`.
The check is `uid != 0` and `getuid() == geteuid() == uid(account)`. It passes if the operator runs the
supervisor as their own login and names that account, in which case UID separation (NC-2's premise for
credentials, files and process counts) is absent while every hash still verifies. Nothing checks group
membership (`admin`, `wheel`), that the account is not the console user, or that the account's home and
`config_dir` ancestors are closed to other users. `config_dir` is checked for owner, mode and realpath, but not
its ancestors. Separately, the supervisor must import `agent_braid` and read the repository it runs from;
where that code lives and who can read the operator's checkout is unspecified, and if the dedicated account
can read it, only the SBPL stands between the child and the source tree (NC-7: "the source checkout is not
readable").
Disposition: **fix-in-T005**: refuse if the account is in `admin` or `wheel`, equals the console user, or its
home is group/other-accessible; add the facts (group ids, home mode) to the environment hash; document in the T009
runbook where the code lives and that the account must have no read access to the operator's home.

**RV-17 (Medium): the credential is readable by the child by design and can leave through the allowed API host with an attacker-supplied key.**
Location: `harness_containment_macos.py:244-245`, `:250-261`; ADR 0035 "Residual risks".
`config_dir` is readable and writable and holds the OAuth credential (NC-5, NC-7). Network is limited to
`api.anthropic.com:443`, but a prompt injected through candidate content can instruct the child to send the
credential or the candidate to Anthropic using an API key (or file API) the attacker placed in the content. The
ADR notes that "allowed endpoints can still carry data to Anthropic" but not credential exfiltration by this
route. This is inherent in NC-1 and NC-5, not an implementation bug; it bounds what "qualified" can mean for
untrusted candidate content.
Disposition: **needs-founder-decision** (acknowledge as an explicit residual in ADR 0035 and restrict native
sessions to trusted candidate content, or accept the risk with a rotation procedure for the dedicated login after
each cohort). Probes cannot show this; no catalog entry should claim it is covered.

**RV-18 (Medium): NC-7 session-state purge and the persistence of `config_dir` are not implemented.**
Location: `harness_containment_macos.py:244-245` (whole `config_dir` read/write); no purge in
`harness_containment_macos.py` or `harness_transport_claude.py`; founder record NC-7, ADR item 2.
Everything one session writes into `config_dir` (transcripts, `projects/`, memory files, global config)
is visible to the next, including probe sessions and later cohort units: cross-session contamination and
persistence for a hostile child. `build_plan` passes `--setting-sources ""`, which removes settings-file
and hook persistence, but memory files and other state are not covered.
Disposition: **fix-in-T005** once T009 observes which paths are session state versus credential (the founder
record defers that observation to the probe); until then record the first attempt's sessions as sharing
state, and take a hash listing of `config_dir` before and after each session into the bundle.

**RV-19 (Medium): no bound on total disk use or file count.**
Location: `harness_containment_macos.py:902-905` (`RLIMIT_FSIZE` only), `harness_qualification_probes.py:435-438`
(file-count informational); contract PROC-03 lists "file-count (disk exhaustion)".
NC-8 caps one file at 64 MB but not the number of files or the total. A child can fill the volume shared with
the operator's machine within the 30-minute wall. The catalog marks the attempt informational because the
decision has no limit to test, which leaves the contract's disk-exhaustion item untested and the process
effect formally "enforced" with a known unbounded resource.
Disposition: **needs-founder-decision**: add a total-size and file-count bound (a supervisor watchdog on the
candidate, `TMPDIR` and `config_dir` trees, or a fixed-size volume for `run_root`) as a new NC-8 value, or
record disk exhaustion as an accepted residual and exclude it from "process enforced".

**RV-21 (Medium): the keychain/mach question (NC-5) is open, and the profile will grow after first contact with `claude`.**
Location: `evidence/t005.json` (`openForProbesAndFounder`), `harness_containment_macos.py:229-248`.
With no `mach-lookup`, the dedicated user's keychain is unreachable; either the login works from
`CLAUDE_CONFIG_DIR` alone (plaintext credential file) or an enumerated `mach-lookup` set is added. The same
applies to `sysctl-read`, TLS trust roots under `/etc/ssl` or the system keychain, `iokit` and shared-memory
needs of a Bun-based binary. Every addition is a policy change broader than the recorded decisions.
Disposition: **needs-founder-decision**: decide the keychain route before T009; require each profile addition to
come with a decision record, a catalog extension for the opened class (RV-08), and a delta review of this
document. If `securityd` is allowed, CRED-02 becomes a test against the dedicated user's login keychain content, not a
disposable file; say so before it runs.

### Low

**RV-20 (Low): metadata and read rules are broader than the recorded read set.**
Location: `harness_containment_macos.py:81-83`, `:236-241`.
NC-7 reads are "candidate, config, Claude binary and system libraries". The profile also grants
`file-read-metadata` on every path under `run_root` (other candidates' and run directories' names, sizes and
times) and on all ancestors of every executable, root, write path and `run_root`, plus read of all of
`/System/Library`, `/Library/Apple`, `/usr/lib`, the cryptex paths and `/private/var/db/dyld`, and a
listing of `/`. No secret is expected there, but it exceeds the wording.
Disposition: **fix-in-T005**: replace the `subpath run_root` metadata rule with literals for `run_root`, the
candidate and `TMPDIR` params; trim `SYSTEM_READ` with an observed list at T009 (the SBPL `trace` facility).
Recorded residuals stay: the root listing and the ancestor stat.

**RV-22 (Low): executable trust checks ignore ancestor ownership and leave a hash-to-exec window.**
Location: `harness_containment_macos.py:131-151`.
`_shared_ancestor` rejects group/other-writable ancestors but not an ancestor directory owned by a third
non-root account with mode 755, whose owner can swap the binary between the hash read and `exec`
(`harness_transport_claude.py:174-181` hashes it again). The risk requires a hostile or careless local owner.
Disposition: **fix-in-T005**: require every ancestor to be owned by root or by the dedicated account; the
stronger form installs the pinned binary into a root-owned directory the account cannot write.

**RV-23 (Low): the compile check cannot tell "denied by profile" from "exec failed".**
Location: `harness_containment_macos.py:746-762`.
Exit 71 is the only signal; a missing `/usr/bin/false` or any exec failure yields the same code, and there is no
positive case (an allowed binary executes under the same profile). A profile that denied everything would pass.
Disposition: **fix-in-T005**: also run an allow-listed trivial command under the rendered profile and require
success. The NET-06 functional control partly covers this at F4.

**RV-24 (Low): evidence secret scanning is a literal-match backstop; the environment document is unvalidated.**
Location: `harness_qualification_probes.py:1392-1397`, `:1403-1407`, `:1410-1437`; contract "Evidence bundle".
No leak path was found: helpers emit outcome and errno only, rows carry fixed reason codes and arena-relative
paths, session stdout is never persisted, `apiKeySource` is bucketed. Weaknesses: `scan_for_secrets` checks
only the arena markers and the `secrets` argument (default empty), not the "export inventory" the contract
promises; `_environment_document` accepts any mapping with two valid fields; `environment.json` carries the
account name, uid and absolute paths (privacy, and it will be committed). A real credential value is never in
the scan list unless the caller adds it.
Disposition: **fix-in-T007**: an allow-list schema for `environment.json`, token-pattern scanning
(`sk-ant-`, JWT, `-----BEGIN`, long base64/hex runs) over all five files, and let the runner read the
credential values from `config_dir` (as the dedicated account) to add to the scan list without printing them.
Review the bundle for local identifiers before committing it.

**RV-25 (Low): CRED-04 cannot be `allowed`.**
Location: `harness_qualification_probes.py:362-364`, `:931`, `:1062-1066`.
The contained child's environment is built from scratch, so `any(name in os.environ ...)` is always false; it
is a regression test of `child_environment`, not an escape probe. The realistic scenario (secrets in the
supervisor's environment) is untestable for `ENV_DENY` names, since `_check_mechanism` refuses first
(`:705`), and `ENV_DENY` omits `CLAUDE_CODE_OAUTH_TOKEN`, Foundry and cloud-provider variables.
Disposition: **fix-in-T007**: set a non-`ENV_DENY` dummy variable in the supervisor's `os.environ` around the
contained call so the test fails if a future change forwards the parent environment. **fix-in-T005**
(optional): extend `ENV_DENY`-style refusal to `CLAUDE_CODE_OAUTH_TOKEN`.

**RV-26 (Low): any non-200 or a closed connection counts as a proxy denial.**
Location: `harness_qualification_probes.py:212-217`, `:220-233`.
`tunnel` and `tls` return `False` when the reply does not start with `HTTP/1.1 200`, including an empty read
after the proxy closed the connection (for example at `MAX_CONNECTIONS`). Disposition: **fix-in-T007**:
`denied` only on an explicit `HTTP/1.1 403`.

**RV-27 (Low): attempt discovery is a regex over the helper text.**
Location: `harness_qualification_probes.py:75`, `:528-529`, `:595-606`.
Only attempts at line start are counted; an indented or helper-wrapped `attempt(` would be emitted but not
declared and silently dropped by the parser. Disposition: **fix-in-T007**: `_validate_catalog` should compare
the number of `attempt(`/`limit(` call sites to the declared names. Also note that `note("raw-socket")`
(NET-07) is informational, so a successful raw socket would not fail the probe; a non-root account cannot create
one, so the control would also fail.

**RV-28 (Low, residual): session-probe controls are synthetic and narrow.**
Location: `harness_qualification_probes.py:797-815`, `:757-785`, `harness_host_claude.py:47`.
CRED-05 and NET-05-CLI controls are a classifier self-test, not a real CLI behavior; `apiKeySource` values
are an assumption (`none`, `oauth`) that T009 will observe; `none` is in the subscription set, so CRED-05 alone
cannot tell "no credential" from "subscription"; HOST-01 runs one turn of a trivial prompt and exercises none of
the effectful policy (tool exec, file reads in the candidate). Disposition: **residual-risk**: record the
literal `apiKeySource` values and the tool list seen in `init` in the bundle, and state in the T010 decision
that HOST-01 shows the CLI starts and answers under the profile, not that real tasks work.

**RV-29 (Low): proxy robustness and observability.**
Location: `harness_containment_macos.py:494-503`, `:398-437`.
The accept loop returns on any `OSError` and leaves `running` true, so a proxy can silently stop accepting
(fail-closed, but invisible); a ClientHello carrying ECH GREASE is refused, which may break the CLI's TLS
stack (functional, fail-closed); the SNI check adds little given that the proxy connects to the CONNECT host
itself, and should be documented as defence in depth against clients that disagree with their own request.
Disposition: **fix-in-T005**: log accept-loop death as a refusal reason on the next `_pre_session`; counters (RV-03).

**RV-30 (Low): cleanup silently tolerates what the child can make undeletable.**
Location: `harness_containment_macos.py:947` (`rmtree(..., ignore_errors=True)`).
`file-write*` includes flags and ACLs; a child can set `uchg` on files in `TMPDIR` or the candidate so removal
fails, leaving data and filling the volume with no record. Disposition: **fix-in-T005**: clear flags
before removal, record `cleanupFailed` in the run evidence and refuse the next run when leftovers exist.

**RV-31 (Low, residual): post-run consumers of the candidate directory.**
Location: not in the reviewed code; applies to T006/T009/SPEC-049 readers of the candidate, and to the
`Arena.snapshot` pattern (`harness_qualification_probes.py:1032-1048`).
The child can create symlinks and hard links inside the candidate. Any unsandboxed reader running as the
dedicated account (collecting output, building a diff, copying evidence) that follows them can be made to read
the credential in `config_dir` or write elsewhere. The snapshot reader is safe (it does not follow links, and
the child is settled before it reads). Disposition: **residual-risk** with a hand-off note: consumers must
use `O_NOFOLLOW`/`lstat`, treat `st_nlink > 1` as hostile and never open paths derived from candidate content.

**RV-32 (Low): the sweep treats every new dedicated-user process as an escape, including legitimate per-user daemons.**
Location: `harness_containment_macos.py:983-1006`.
A per-user helper started by launchd during the run (not by the child) would be killed and make the run
unsettled; the 40-iteration exhaustion returns the same count as success. Disposition: **fix-in-T005**:
distinguish parentage where possible (descendants of the child vs others), part of RV-01's separate counters.

### Informational

**RV-33 (Info): evidence and naming drift.** `evidence/t005.json` records the backend hash
`d9bd8bf9932df47db48d60926868dbc423af84f3b19a6e75f9a8975b86feb2eb`; the file is now `dfa7fda8...` (T006 changed it).
`harness_host_claude.py:47` still says the subscription key sources are refused "until T008 observes the real
values"; T008 is now this review, and the observation belongs to T009. Disposition: **fix-in-T005**
(evidence/docs refresh at the next edit).

**RV-34 (Info, residual): recorded residuals this review confirms and adds to.**
Same-uid supervisor and child (a sandbox escape reaches the supervisor and proxy); `sandbox-exec` deprecation
and undocumented semantics; the root directory listing; covert channels through allowed metadata and `kqueue`
watches; per-process (not aggregate) CPU rlimit within the wall bound; exfiltration through the allowed host
(RV-17); one machine, one build, finite catalog. None changes a disposition above.

## Coverage of the escape classes named for this review

| Class | Profile rule or mitigation | Probe coverage | Gap |
|---|---|---|---|
| mach/XPC services | no `mach-lookup` | ~10 sampled names (NET-08, CRED-02/07, PROC-06) | sweep, RV-08 |
| IOKit | no `iokit-open` | none | RV-08 |
| sysctl | no `sysctl-read` | indirect (`KERN_PROCARGS2` in CRED-07) | RV-08 |
| shared memory, semaphores | no `ipc-*` | none | RV-08 |
| kqueue, timing channels | not gated | none | residual, RV-34 |
| `/dev` nodes | only `/dev/null`, `random`, `urandom` | `/dev/zero` only (FS-06) | RV-06 |
| TCC | file and mach denial | none (GUI) | RV-08 |
| Keychain via securityd | no `mach-lookup` | CRED-02 mach lookups | RV-21 |
| launchd, LaunchAgents | exec and mach denial | PROC-05/06 | RV-09 (real path) |
| mDNS, DNS | Unix socket and mach denial | NET-03, NET-08 | RV-05 (name-resolution masking) |
| IPv6 link-local, LAN | only `localhost:PORT` | public literals only | RV-10 |
| proxy env bypass, DoH | network deny | NET-05 (3 attempts) | RV-10 |
| time-of-check races | flock, realpath, private candidate | none | RV-22, RV-31 |
| symlink races in candidate | SBPL resolves symlinks | FS-02 | RV-31 |
| open fds | `close_fds`, non-inheritable pipes | FS-06 (non-discriminating) | RV-06 |
| process group escape | sweep | PROC-04/08 | RV-01, RV-12 |

## Positive-control assessment

| Probe | Control quality | Note |
|---|---|---|
| FS-01, 02, 03, 04, 05 | Adequate | Same user, uncontained, real success required; decoys only (RV-09) |
| FS-06 | Weak | Denial is structural, RV-06 |
| FS-07 | Weak | Denial by exec allow-list, RV-07 |
| NET-01, NET-05 `direct-allowed-host` | Weak | Name resolution masks `connect`, RV-05 |
| NET-02, 03, 04, 07 | Adequate | Need internet and IPv6 on the founder machine; ICMP/raw note RV-27 |
| NET-05 `connect-nonallowed-host` | Adequate with caveat | Control uses a permissive stand-in, not the real proxy; RV-10, RV-26 |
| NET-06 | Adequate | Functional; real TLS to the allowed host |
| NET-08, CRED-02/06/07 | Adequate | Mach status mapping unverified (RV-08) |
| CRED-04 | Tautological | RV-25 |
| PROC-01, 02 | Adequate | |
| PROC-03 | Mixed | Memory sampled, CPU and file-count informational, RV-13, RV-19 |
| PROC-04, 08 | Unpassable | RV-01, RV-02, RV-12 |
| PROC-05, 06, 07 | Partial | exec denial can mask the mach attempt; RV-11 |
| CRED-05, NET-05-CLI, HOST-01 | Synthetic | RV-03, RV-15, RV-28 |

## Policy against the founder decisions

| Decision | Matches | Broader or open |
|---|---|---|
| F5, NC-1 network | Only TCP to `localhost:<proxy>`; proxy lists `api.anthropic.com:443`; SNI equals host | `refresh_endpoints` and `helpers` accepted without a decision reference; the environment hash binds them (RV-14 for the runner) |
| NC-2 mechanism | Dedicated uid check, `sandbox-exec` pinned and root-owned | account not verified dedicated or unprivileged (RV-16) |
| NC-3 macOS window | `27.0.x` regex; build in the environment hash | none |
| NC-4 Claude version and hash | exact version, hash checked at each launch (backend and transport) | ancestor ownership (RV-22) |
| NC-5 credential | env from scratch, no secret copied | keychain unreachable (RV-21); readable by child (RV-17) |
| NC-7 reads and writes | writes: candidate, `TMPDIR`, `config_dir` | reads: metadata on all of `run_root` and ancestors, whole `/System/Library` (RV-20); purge missing (RV-18) |
| NC-8 limits | all six values present | memory sampled (RV-13); no total disk or file-count bound (RV-19); aggregate CPU not bounded |
| NC-9 triggers | OS build, Claude, profile bytes, catalog, proxy, credential method in the hash | runner and judge code not bound (RV-14) |
| NC-10 live budget | cap of 3 sessions in the catalog | stop rule and readings not implemented (RV-15) |
| NC-11 F4 subset | exact five probes | run only on the `fixture` profile (RV-04); NET-01 insensitive (RV-05) |

## Disposition of the open items left by T007

| T007 open item | Disposition |
|---|---|
| PROC-04/PROC-08 swept group-leaver judged as escape | RV-01: the judgement changes, the backend gains a separate survivor count, `settled` stays strict |
| PROC-08 cancel driver | RV-02: `run_probe` needs an optional `cancel`; then a driver |
| FS-06 control | RV-06: replace with a descriptor inventory and in-candidate FIFO |
| FS-07 control | RV-07: replace with mach lookups of the metadata services |
| NET-05-CLI proxy egress tap | RV-03: counters in `EgressProxy`; verdict redefined; `unexpectedDirect` has no source |
| PROC-03 CPU and file-count informational | RV-13, RV-19: CPU stays informational (per-process, wall-bounded); file-count/disk needs a founder decision |
| Public targets, 4.25 GiB memory touch | Acceptable on the founder machine; connect-only targets; record the memory touch in the runbook |

## Hand-off

Suggested follow-up tracks (not started here): (1) T005 delta: RV-01, RV-02, RV-03 counters, RV-14
component hashes, RV-16, RV-20, RV-22, RV-23, RV-30, RV-32; (2) T007 delta: RV-04 to RV-15, RV-24 to RV-27,
with a new catalog hash; (3) founder decisions: RV-17, RV-19, RV-21; (4) a delta review of whatever those
tracks change, before T009.
