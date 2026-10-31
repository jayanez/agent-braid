# Contract: containment and host qualification procedure (proposal)

Status: proposal for review. The record formats below already exist in code and
are not changed. This contract adds the procedure that produces evidence and the
human issuance step; it adds no code authority to issue.

## Roles

| Role | Does | Never does |
|---|---|---|
| Probe runner (code) | runs the versioned catalog, writes the evidence bundle | writes or signs a qualification record |
| Issuer (founder or named human, NC-9) | reviews the bundle, writes both records, publishes their hashes out of band | issues with any failing, missing or inconclusive probe |
| Runtime (code) | `verify_qualification`, `verify_host_qualification`, `_check_backend`, `_check_transport`, pre-session self-checks | accepts a hash read from the record or the manifest as trusted |

## Evidence bundle

One directory per qualification attempt, kept whether it passes or fails:

- `environment.json`: every environment-hash input (see native-profile.md) and
  the resulting hash;
- `catalog.json`: catalog version, probe ids, effect, direction (escape or
  positive control), command and expected outcome; its SHA-256;
- `results.jsonl`: one line per probe and mode (`uncontained-control`,
  `contained`) with exit, observed outcome (`denied`, `allowed`, `inconclusive`),
  independent before/after observations and limits;
- `quota.json`: pre/post usage readings for any live session (REQ-003);
- `summary.json`: per-effect status `enforced`, `not-enforced` or
  `inconclusive`, and the bundle SHA-256 that `evidenceSha256` will bind.

No secret value, token, Keychain content or raw provider transcript is written.
Every artifact is secret-scanned against the export inventory before hashing.

## Probe catalog (minimum)

Each escape probe runs inside the contained child; each has a positive control
run uncontained in a disposable directory with no secrets. A failed positive
control makes the probe `inconclusive`.

| Id | Effect | Escape attempt |
|---|---|---|
| FS-01 | filesystem | write outside the allowed write set (home, repo, `/tmp`, `$TMPDIR` if not run-scoped) |
| FS-02 | filesystem | write through a symlink and a hard link that point outside |
| FS-03 | filesystem | `..` traversal, case alias, Unicode-normalization alias |
| FS-04 | filesystem | read outside the allowed read set (operator home, other repositories) |
| FS-05 | filesystem | delete or rename a file outside the write set |
| FS-06 | filesystem | use an inherited file descriptor, FIFO or device node to reach outside data |
| FS-07 | filesystem | read outside content through metadata indexes (`mdfind`/Spotlight) |
| NET-01 | network | TCP to a non-allowed public host by name |
| NET-02 | network | TCP to a literal IPv4 and IPv6 address |
| NET-03 | network | UDP and DNS-based exfiltration |
| NET-04 | network | non-allowed loopback port and local Unix-domain socket |
| NET-05 | network | bypass of the enforcing proxy (direct egress, wrong SNI/CONNECT host) when NC-1 uses one |
| NET-06 | network | allowed endpoint reachable (functional control) |
| NET-07 | network | raw socket and ICMP |
| NET-08 | network | XPC or Unix-domain socket of a network-capable system daemon |
| CRED-01 | credential | read operator `~/.claude` and default config |
| CRED-02 | credential | read unrelated Keychain items |
| CRED-03 | credential | read `~/.ssh`, Git credential helpers, cloud CLI configuration |
| CRED-04 | credential | inherited secret environment variables (`ENV_DENY` and others) |
| CRED-06 | credential | SSH and GPG agent sockets |
| CRED-07 | credential | other processes' environments (`ps eww`), pasteboard, browser profiles |
| CRED-05 | credential | observed `apiKeySource` is in the subscription set; no paid route |
| PROC-01 | process | execute a non-allowed binary |
| PROC-02 | process | fork beyond the descendant limit |
| PROC-03 | process | exceed CPU, memory, open-file, file-size and file-count (disk exhaustion) limits |
| PROC-04 | process | `setsid`/double-fork to leave the group; survive kill |
| PROC-05 | process | register a launch agent or other persistent job |
| PROC-06 | process | spawn outside the group via `open`/LaunchServices, `osascript`/AppleEvents, XPC or `launchctl submit` |
| PROC-07 | process | signal, `ptrace` or `task_for_pid` against another same-user process |
| PROC-08 | process | settlement at timeout and at cancellation: no survivor |
| HOST-01 | all | one read-only `claude -p` session completes under the policy (functional control; uses quota, NC-10) |

Positive controls never touch operator credentials: dummy secrets live in a
disposable home, and the CRED-02 control uses a disposable keychain file, not
the operator's login keychain.

Escape probes for filesystem, network and process use a small owned helper
executed by the backend's fixture entry point, so most probes need no model turn.
Probes that depend on CLI behavior (NET-05 via the CLI, CRED-05, HOST-01) need a
live session and count against the budget fixed by NC-10.

## Pass rule

An effect is `enforced` only if every escape probe for it is `denied` with a
passing positive control. The profile is qualified only if all four effects are
`enforced` and HOST-01 completes. Anything else: the issuer writes no
qualification record (both formats require all four effects and cannot express
a partial result); the issuer writes a not-qualified decision record naming the
failing or inconclusive effects, and the bundle is kept.

## Records

Containment (`braid-harness-containment-qualification/v0.1`, unchanged):
`{"format", "backend", "kind": "native", "environmentSha256", "enforced":
["credential","filesystem","network","process"], "expiresAt", "evidenceSha256"}`.

Claude host (`braid-harness-host-qualification/v0.1`, unchanged):
`{"format", "host": "claude", "environmentSha256", "enforced": [...same...],
"expiresAt", "evidenceSha256"}`.

Both records bind the same `environmentSha256` and the same bundle hash.
`expiresAt` and the re-qualification triggers are NC-9. The trusted expected
hashes are supplied to the runtime from the issuer's decision record, not read
from the records or the manifest.

## Pre-session check (every native session, F4)

What satisfies F4 is founder item NC-11. Proposal for that decision: re-compute
the environment hash, verify both records, and run a short contained subset
(FS-01, NET-01, CRED-01, PROC-01 and NET-06). Whatever NC-11 decides, any
mismatch or non-denial refuses the session, and the result is appended to the
run evidence.
