# Re-check: T009 closed read-only list, second widening (2026-11-04)

Scope: the touched lines of `agent_braid/harness_containment_macos.py` (`SYSCTL_READ_NAMES`,
`SYSCTL_READ_PREFIXES`, new `DATA_READ`, and the one new rule in `ContainmentPolicy.render`) and the
profile test. Founder decision: `evidence/founder-decisions-20261104e.json` ("A. Solo lecturas").

## Facts that drove the change
- Self-check of attempt `t009-20261104c` (round 3): every F4 probe as expected; the `auth` stage gave
  `auth-rejected` (exit 1) with `authToken: present`.
- Operator diagnostic outside the sandbox, exit codes only: the same token through
  `CLAUDE_CODE_OAUTH_TOKEN` gives `claude auth status` exit 0 with an empty and with the real `config_dir`;
  without it, exit 1. The token is valid; the sandbox is the cause.
- Unified log (orchestrator, read-only) for the contained CLI during the stage: denied sysctl-read
  `hw.memsize`, `hw.ncpu`, `hw.activecpu`, `hw.perflevel{0,1,2}.physicalcpu_max`; file-read-metadata
  `/private/var/db/timezone/zoneinfo`, `/usr/share/icu/icudt78l.dat`; `process-exec* /usr/bin/security`;
  also `kern.bootargs`, the syslog socket, `/dev/dtracehelper`, mach-lookup `notification_center`/`logd`.

## Change
- `(allow sysctl-read ...)` gains `hw.memsize`, `hw.ncpu`, `hw.activecpu` (exact names) and the prefix
  `hw.perflevel` (per-performance-level CPU facts: core counts, cache sizes, names).
- New `(allow file-read* (subpath "/private/var/db/timezone") (subpath "/usr/share/icu"))`: the
  root-owned, read-only time-zone database and ICU data.
- Only the `launch` and `launch-probe` profiles; `fixture` unchanged.

## Verdict: GO
- Read-only system facts and system databases: no user data, no secrets, no write, no new exec, no
  new IPC. Worst case is host fingerprinting (memory size, core layout), the same class as the first list.
- `/usr/bin/security` exec, `kern.bootargs`, every `mach-lookup`, the syslog socket, `/dev/dtracehelper`,
  `/System/Volumes/Data`, the network (except the loopback proxy) stay denied; the test asserts each is
  absent, plus no `(subpath "/private/var")` and no `(subpath "/usr/share")`.
- The token-file deny rule, the last-match order and the fixture profile are untouched.
- Hashes: the launch and launch-probe profile hashes, hence `environmentSha256`, move. The catalog hash
  does not (probes module untouched).

Residual: if the `auth` stage still fails, the remaining candidate is the exec of `/usr/bin/security`
(still denied); that needs a new founder decision.
