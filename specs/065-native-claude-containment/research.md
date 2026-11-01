# SPEC-065: Research

Sources are the repository at `develop` 9c73b137, `claude --help` of the installed
CLI and `sw_vers` on the founder's machine, read on 2026-10-31. Reading code and
help text is not native observation: no `claude -p` session, sandbox probe or
quota read was run for this specification. Facts marked *to be probed* are
inputs to the qualification procedure, not findings.

## R1 Manifest: offline only

`agent_braid/harness_manifest.py` fixes `PROFILE = "offline-foundations"` and
refuses any other profile. `_validate` requires `host.kind == "offline"`,
`executableSha256` and `build` null, requested `{"model": null, "effort": null,
"route": "offline"}` and an all-null observed record. `DEFAULT_LIMITS` sets
`maxNativeSessions`, `maxModelSessions`, `maxChildProcesses`,
`maxNetworkConnections`, `maxAdditionalCashMicros` and `maxAutomaticRetries` to
0, and `_limits` allows only 0 when the maximum is 0.

Consequences: `harness_lab._check_backend` requires a host kind other than
`offline` and `maxNativeSessions >= 1`, and `harness_host_claude._check_transport`
requires `host.kind == "claude"`. Neither can pass with any parseable manifest
today, which is the intended refusal.

Decision: add a second closed profile with its own limits table and host record
instead of loosening the offline one (REQ-001). Alternatives rejected: making the
offline fields optional (changes offline digests and weakens its closed schema);
a free-form host record (Article 15: declared metadata must be checkable).

## R2 Claude adapter: double only

`harness_host_claude.py` defines `ClaudeTransport` (kind `native`, methods
`version()` and `run(plan, prompt, limits, cancel)`), the scripted
`ClaudeHostDouble`, `build_plan` and `run_claude`. `build_plan` already produces
`claude -p --output-format stream-json --verbose --session-id … --permission-mode
{default|plan} --max-turns … --tools … --disallowedTools … --setting-sources ""
--strict-mcp-config`. `ENV_ALLOW = ("HOME", "PATH")` and `ENV_DENY` (API key,
auth token, base URL, Bedrock, Vertex) are declared but enforced by nobody; the
module comment says the T008 launcher must contain the HOME-derived
configuration. `SUBSCRIPTION_KEY_SOURCES = {"none", "oauth"}` is a fixture
assumption until observed. `_check_transport` accepts a native transport only
with a `HostQualification` whose environment hash equals the manifest's and
which has not expired.

Two gaps follow from the code: `run_claude` parses stdout only after
`transport.run` returns, so the `apiKeySource` check in `_terminal` fires after
a session has completed; and `_check_transport` never inspects a containment
backend, so a host qualification alone passes it.

Decision: the native transport supplies `version()` and `run()` through the
contained launcher and reuses the stream, route, session, version, model and
permission checks. It needs the known changes K1–K5 listed in plan.md (live
`init` check, backend check, native wall bound, native environment and pinned
executable path, and an observation-backed key-source set). `HOME` must
not point at the operator's home inside the sandbox (NC-5, NC-7).

## R3 Containment: simulated only

`harness_lab.py` defines `ContainmentBackend` (kind `native`, `qualification`,
`run(source, workdir, limits) -> ChildResult`), `SimulatedContainment` (process
group, rlimits for CPU, file size, core and open files applied by a preamble,
kill-and-settle, environment reduced to `PYTHONHASHSEED=0`) and `ENFORCED_EFFECTS = ("credential",
"filesystem", "network", "process")`. `verify_qualification` requires
`kind == "native"`, an identifier `backend`, `enforced` equal to the four effects,
`expiresAt`, environment and evidence hashes, and a match with a trusted
external hash.

The interface is fixture-oriented: it runs a Python source, not an arbitrary
host executable. A backend for Claude therefore needs a second entry point (a
contained launcher) that `ClaudeTransport.run` uses. Both entry points must use
the same policy and the same qualification so one record cannot qualify a
weaker path.

## R4 Qualification records exist, issuance does not

Both verifiers check identity against a trusted external hash and state that the
evidence behind the record is "judged by the T008 decision records, not here".
No code, task or procedure defines the probes, the evidence bundle or the issuer.
This is the gap REQ-009 and REQ-010 close. Self-qualification is excluded by
construction: the probe runner writes evidence only; records are written by a
human issuance step and their hashes are supplied out of band.

## R5 Reusable partial mechanisms

- `agent_braid/system_one_verified_stdio.py` launches a child through
  `/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)'`, with a
  minimal environment, a private `HOME` and `start_new_session=True`, and records
  `networkDeniedByOS`. It is an allow-default profile: it denies network only and
  confines no files or credentials.
- `harness_lab._PREAMBLE` applies `RLIMIT_CPU`, `RLIMIT_FSIZE`, `RLIMIT_CORE`,
  `RLIMIT_NOFILE` inside the child without `preexec_fn`; `_settle` kills the
  process group and confirms it is empty.
- `agent_braid/git_process.py` refuses when hard address-space limits are
  unavailable (`GitResourceLimitUnavailable`) instead of degrading, the pattern
  REQ-004 generalizes.

Decision: reuse the launch shape, the rlimit preamble idea, the group settlement
and the refuse-if-unavailable pattern. A STRICT profile must be deny-default for
files, network and process execution, unlike the existing allow-default one.

## R6 Platform facts and limits

- `sw_vers`: macOS 27.0.1, build 26A434; `/usr/bin/sandbox-exec` present
  (root-owned). Apple marks `sandbox-exec` deprecated and documents no stable
  profile language; behavior can change with any OS update (NC-2, NC-3).
- Sandbox network rules match addresses and ports, not host names; a host-name
  allow-list needs an enforcing component such as a loopback proxy, or pinned
  addresses (NC-1). DNS resolution on macOS goes through system services, so a
  deny-default profile must decide whether name lookups are allowed at all.
- `RLIMIT_NPROC` is per user on macOS, so it cannot cap one run's descendants
  without a separate user or a supervisor (NC-8).
- Keychain access is mediated by system services; whether a sandbox rule can
  admit one Keychain item and deny the rest is *to be probed* (NC-5).

## R7 CLI facts (help text only)

`claude --version` reports `2.1.292 (Claude Code)` at `/opt/homebrew/bin/claude`.
`claude --help` lists `--output-format` (print mode only, including
`stream-json`), `--permission-mode`, `--allowedTools`/`--disallowedTools`,
`--mcp-config`, `--bare` (minimal mode that skips hooks and other discovery),
and the subcommands `auth` and `setup-token` (long-lived authentication token).
*To be probed:* where a login under a dedicated `CLAUDE_CONFIG_DIR` stores its
token, which endpoints a headless session contacts (API, OAuth refresh,
telemetry, update checks), which helper executables the read-only tools spawn,
the observed `apiKeySource` values for a subscription login, and whether a
headless usage report exists. Whether `--bare` should replace or complement the
current isolation flags is a T004 design question bounded by the existing
`build_plan` tests.

## R8 Quota observation

The founder records read plan usage from the Claude Desktop usage card
(5-hour, weekly all-models, weekly per-model windows, extra usage flag). No
headless CLI usage report is confirmed (R7). Per-session token counts are not
observed. Decision: treat quota reading as an external, timestamped observation
with a freshness bound and a fixed source chosen by the founder (NC-6); the
transport refuses when the reading is missing or stale, matching the D2 stop
conditions.

## R9 Alternatives considered for the backend

| Option | Strength | Weakness |
|---|---|---|
| `sandbox-exec` deny-default profile | present, already used, per-process, cheap | deprecated, undocumented, host-name filtering absent |
| separate macOS user + sandbox | UID separation for files and credentials, per-user process caps | account administration, second login |
| macOS VM | strong boundary, snapshot/reset | heavy, slow, needs its own Claude login and network policy |
| Linux VM/container | mature namespaces and firewalls | different host profile (Linux CLI), not macOS native |

The choice is NC-2. The specification is written so that every option yields
the same records, probes and refusal behavior; only the backend identifier,
environment hash and probe implementations differ.
