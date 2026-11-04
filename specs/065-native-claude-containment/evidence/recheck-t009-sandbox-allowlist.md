# SPEC-065: security re-check of the T009 sandbox allow-list edit

**Not a qualification.** It issues no record, qualifies no effect, authorizes no native session, probe or
account setup. `executionAuthorization` stays `false`. A GO means engineering readiness of the touched lines
for the founder's next `--self-check`; whether the profile enforces anything is decided only by the T009
observation and the T010 human issuance. Self re-check by the implementing agent (not independent); the
orchestrator's re-check is still owed. Nothing native was run.

## Record

| Item | Value |
|---|---|
| Date | 2026-11-04 |
| Cause | `t009-selfcheck1-20261104.md`; founder decision "A. Lista cerrada (Recommended)" (`founder-decisions-20261104.json`) |
| Branch / base | `har/065-t009-sandbox-allowlist`, `origin/develop` `e3901f81` |
| Scope | `agent_braid/harness_containment_macos.py`: the constants `SYSCTL_READ_NAMES`, `SYSCTL_READ_PREFIXES`, `LOCALE_READ`, `METADATA_ONLY`; `ContainmentPolicy.render` (three rules); `exec_probe`, `child_environment` and `_fixture` (`-B`, `PYTHONDONTWRITEBYTECODE`); `_pidinfo`, `_accounting_error`; `_compile_check` (evidence argument, `compileExit`); `_pre_session` (call site); `_spawn` (two integers). `scripts/har_t009_attempt.py`: `_int`, `_integers`, `refusal_evidence`, `self_check` (`probeRuns`) |
| Not touched | `cli.py`, `ownership.py`, `harness_transport_claude.py`, `harness_quota.py`, `harness_qualification_probes.py` (the catalog), `harness_lab.py`, `docs/STATUS.md`, `ROADMAP.md`, `SPEC_MILESTONE_INDEX.md`, `CONSTITUTION.md` |
| Verdict | **GO** for both files, with the residuals below. Required fixes: none |
| Hashes | Environment hash moves (backend module is a component; the `launch` and `launch-probe` profiles change). Catalog hash does not move (`842f47fc18b843d81cf866478a0b895b29be0d81b5b5b29d0fd648da2ff8599b`, probes module unchanged). Backend module sha256 `2b8b440e2d4cb3cd95a4aa1c55ff9a9a7a2cb2f14ff18c3694370cf3de4d74c6` -> value in the PR at its head |
| Tests run | Python 3.12.13 (uv standalone): `test_harness_containment_macos`, `test_har_t009_attempt`, `test_harness_qualification_probes` and the required profile; see the PR |

## Line by line

1. **`sysctl-read` allow (launch, launch-probe).** Seven `sysctl-name` literals plus `(sysctl-name-prefix
   "hw.optional.")`. Read-only; the names are host facts (page size, CPU feature flags, OS product version,
   OS variant status, iOS support version, lockdown-mode state, ephemeral storage). `kern.osproductversion`
   is already part of the environment hash and `host_facts()`; none gives write access, an identity of the
   founder or a path. The prefix covers one family; `hw.optional.` cannot reach `hw.memsize` or `kern.*`
   because prefix matching is on the full name. **GO.** Residual SYS-01: a process in the sandbox can read
   the CPU feature flags and the OS version; it can already infer both from its own binary and from the
   environment hash inputs.
2. **`file-read-data` three literals under `/usr/share/locale`.** Literal files, not a subpath: only the
   `LC_CTYPE` of `UTF-8`, `C.UTF-8`, `en_US.UTF-8`. System data, same for every user. Narrower than the
   founder's "under /usr/share/locale" on purpose. **GO.**
3. **`file-read-metadata` literals `/etc` and `/var`.** Metadata (stat) of the two directories themselves,
   not a listing and not of anything below them (`literal`, no `subpath`). `/etc` and `/var` are
   symlinks to `/private/...`; the deny rule for `/System/Volumes/Data` is unchanged and stays last, so the
   data volume is still not readable. Residual SYS-02: existence and mode of `/etc` and `/var` are visible,
   which `/` read-data (already granted for dyld) makes inferable. **GO.**
4. **Not added, and why.** `kern.bootargs` (boot arguments are system configuration; no evidence claude
   fails without them), `mach-lookup` (python only; nothing shown for claude), `/dev/dtracehelper`
   (harmless denial), `process-exec*` of `/usr/bin/curl` (NET-01 control), anything under
   `/System/Volumes/Data`. Tests assert the profile text contains none of them.
5. **`fixture` profile unchanged.** The three rules are only added for `launch` and `launch-probe`; the
   `launch-probe` delta check (`launch_probe_delta_is_interpreter_only`) compares line by line and both
   carry the same three lines, so it still sees only the interpreter. Test: the fixture profile has no
   `sysctl`.
6. **`-B` and `PYTHONDONTWRITEBYTECODE=1`.** Fixture interpreter no longer attempts `__pycache__` writes
   inside the read-only interpreter root; no write permission was added. **GO.**
7. **`_pidinfo`.** Failure handling reads `errno` (`use_errno=True` already set). `ESRCH` -> gone. For a
   task flavor, a process whose `pbi_status` is `SZOMB` -> gone. Everything else still ends in
   `process-accounting-failed` (fail closed). Residual SYS-03: a zombie is treated as having zero resident
   bytes; it holds no task memory, so the memory watchdog cannot be bypassed by it, and the sweep still
   kills every new process of the dedicated user. The recursion is one level (BSD info is not recursed).
   **GO.**
8. **Diagnostics.** `compileExit`, `accountingErrno`, `accountingFlavor` are integers set by the backend;
   the driver prints an integer only when `type(value) is int` and |value| <= 1000 (booleans are not
   integers there), so no text, path, account or hash can reach the output through these keys.
   `LabError` keeps its fixed reason code; the errno is an extra attribute. **GO.**

## Residuals carried

SYS-01, SYS-02, SYS-03 above; the earlier DRV-04, 07, 08, 09, 11, 13, 15 and MDRV-01 to MDRV-04 are
unchanged. The process-accounting cause is not proven (see `t009-selfcheck1-20261104.md` section 4).
