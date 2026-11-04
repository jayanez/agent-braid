# SPEC-065 T009 round 3: security re-check of the touched lines

Date: 2026-11-04. Base `58233022` (develop). Scope: every changed line of `harness_containment_macos.py`,
`harness_transport_claude.py` (comment only), `harness_qualification_probes.py`, `harness_quota.py`, plus the
driver/lab scripts and the runbook. Founder record: `founder-decisions-20261104d.json` (NC-5 token file).
Nothing native ran; the checks are code reading, unit tests and three independent reviews (security, quality,
simplification) whose findings are applied below. This is a re-check, not a qualification.

## Verdict: GO for a new attempt (new name, budget of 3 sessions), conditional on the orchestrator's written GO

## Hashes that move

| Hash | Moves | Why |
| --- | --- | --- |
| `environmentSha256` | yes | component hashes of the backend, the transport (comment) and the quota module change; the credential method is now `dedicated-user-token-file`; the hash now binds `authentication` (token file name, token variable, run-tag variable); the `launch` and `launch-probe` profiles gain one `deny` of the token file, so their profile hashes move (the `fixture` profile does not) |
| `catalogSha256` | yes | the probes module bytes (runner, judge, arena) and helper sources change; value at this head `422d0f12...1cfa` (recompute at the final commit) |
| `profileSha256` of `claude`, interpreter, `sandbox-exec` pins | no | unchanged |
| `bundleSha256` of `t009-20261104b` | no, but `verify_bundle` of that bundle now reports `bundle-drift` on this code: the catalog hash binds the module source, so attempt 2 verifies only at commit `a4d5c294` (as for every earlier bundle) |

## Touched lines

### Backend (`harness_containment_macos.py`)

- `read_token` (new). Opens with `O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC`, checks on the open descriptor (`fstat`, no
  TOCTOU): regular file, owner = dedicated uid, mode exactly 0600, one link, 1..4096 bytes, one ASCII token of
  `[A-Za-z0-9._~+/=-]{20,2048}`. Every failure is `LabError("auth-token-invalid")` raised `from None`: no value in
  messages. A FIFO cannot block (`O_NONBLOCK`, then `S_ISREG`). Missing file returns `None` (no variable set).
  GO.
- `_supervise`: the token is read before any directory is created, for the `launch` entry only; set only in the
  child's environment (`Popen env`), never in argv, evidence, the supervisor's environment or exceptions;
  evidence records `authToken` = `present`/`absent`. `ENV_DENY` semantics in the parent are unchanged. The
  token path belongs here, not in the transport: the backend owns `child_environment` and the supervisor that
  builds the child's environment, so the transport and the plan never hold the value. GO.
- Profile: the child can read and write `config_dir` (NC-7), which includes the token file, and it runs as
  the same uid, so it could replace the file used by later runs (found by the security review). Applied: `launch`
  and `launch-probe` deny `file-read*`/`file-write*` on the token file literal after the `config_dir` allow.
  The child already receives the value in its environment, so no new disclosure; this closes the integrity gap.
  GO.
- Run tag (`RUN_TAG_VARIABLE`, `_tagged`, `_Lineage`): a random 128-bit value in every child's environment,
  matched as `\0NAME=value` in `KERN_PROCARGS2` of each newly seen process of the dedicated user. A process that
  carries it is the child's even if `setsid` and reparenting hid its parent and group (PROC-ESC-1). Unrelated
  launchd agents cannot carry it, so they are still neither counted nor killed. An unreadable environment returns
  `None` and is asked again at the next poll. Residual (stated in the catalog, PROC-04): a descendant that also
  scrubs its environment before it is first seen, or exits between polls, reads as unrelated. GO.
- Memory watchdog: measures `max(pti_resident_size, ri_phys_footprint)` (`proc_pid_rusage`, flavor
  `RUSAGE_INFO_V2`, offset 72, verified), so compressed pages count; a failing rusage call falls back to the
  resident size (never lower than before). Records `peakMemoryBytes` and `memorySamples`. Residual: footprint
  can exceed resident size, so the 4 GiB cap may trigger earlier than before for a very memory-hungry CLI; the
  recorded peak calibrates it. GO.

### Probes (`harness_qualification_probes.py`)

- `NOT_APPLICABLE` + `not_applicable()` + `_judge_row`: the only way an attempt is excluded. Four listed
  (probe, attempt) pairs, each with a closed set of control error codes; the control must not have succeeded;
  the codes come from the uncontained control's stdout (a contained child cannot influence them); at least one
  counted attempt always remains; functional probes are never touched; a contained `allowed` at an excluded
  attempt is still an escape and the row reports `notApplicable`. Residuals now stated in the catalog for
  NET-02 (no IPv6 route: IPv6 egress untested) and PROC-07 (ptrace refused even uncontained). GO.
- Repaired controls: `mach(..., absent=True)` maps bootstrap status 1102 to code `ABSENT` (CRED-02 `mach-secd`,
  FS-07 `mach-spotlight`); FS-03 `var_alias` is a runner-owned file under `/private/var/tmp` reached through
  `/var`, removed on close; PROC-03 `open-files` opens `openFiles+64` descriptors with a soft limit `+64`
  higher (the old limit equalled the count, so the control always hit EMFILE; under the enforced hard limit the
  contained run still fails), `memory` touches every `mmap.PAGESIZE` page (it touched one page in sixteen).
  No denial rule was weakened. GO.
- Sessions: `exitReason` (closed set, from refusal, stop flags, exit code, `init` presence and the token mark,
  never from output text) and `authToken` in each session row. GO.
- Secret scan: the token file is read leniently (any mode) into the scan literals and is included even if it
  holds `/` or `~` (found by the security review). GO.
- `Probe.residual` and the catalog `residual` key; PROC-04's statement of PROC-ESC-1. GO.

### Quota (`harness_quota.py`)

`SOURCE` is now `operator-typed-usage`; `claude-desktop-usage-card` stays an accepted input and a reading
keeps its own label in the evidence. No decision rule changed. GO.

### Scripts

`har_t009_attempt.py`: `auth` self-check stage (`claude auth status` through `launch`; only exit code, token
mark and a closed reason; the output, which can name the account, is never read). `har_t009_lab.py`: step 9b
(`claude setup-token`, hidden `getpass` prompt, temp file + `os.replace`, 0600). Neither is hashed into the
environment. GO.

## Residuals

- PROC-ESC-1 narrowed, not closed: environment-scrubbing leavers. A catalog variant that scrubs would fail
  PROC-04 until the backend can attribute such a process; founder question.
- The contained child holds the token in its environment (unchanged by the file design); egress is limited to
  `api.anthropic.com:443` by the proxy.
- `claude auth status` with only `CLAUDE_CODE_OAUTH_TOKEN` is not verified to exit 0; the `auth` stage answers it
  before a session is spent. Claude Code documents the variable as taking precedence over Keychain credentials.
- `claude setup-token` prints the token to the terminal; run the lab script in the operator's own terminal.
- Mach service names `com.apple.secd` and `com.apple.Spotlight` are excluded only when absent for the account
  (control `ABSENT`); no replacement service was chosen without a live listing.

## Validation

Focused: `tests.test_harness_containment_macos`, `..._qualification_probes`, `..._quota`,
`..._transport_claude`, `test_har_t009_attempt`, `test_har_t009_setup` all pass (597 tests, 3 skipped on
non-macOS or live-only cases). The required profile ran once on the final candidate (see the PR).
