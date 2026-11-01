# SPEC-065: Native Claude laboratory containment and transport

**Track:** HAR (unblocks SPEC-048/T008 for the Claude profile, then SPEC-049/T004)

**Status:** draft; implementation in progress. T003 (native manifest profile),
T004 (quota gate) and T005 (macOS containment backend) are implemented at unit
level; nothing is qualified
or authorized. The founder decided every security choice (NC-1 to NC-11) and F5 is
bound, in the [founder decision record](evidence/founder-decisions-20261031.json)
(T001, 2026-10-31). The decisions authorize no execution, qualification or
native session.

## Purpose and scope

On 2026-10-31 the founder authorized SPEC-048/T008 qualification of the Claude
profile only, with EUR 0 additional cash, the SPEC-049 D2 caps and containment
verified before every native session
([founder review](../048-harness-variant-laboratory/evidence/founder-review-20261031.json),
[D2 caps](../049-harness-evaluation-learning/evidence/registration/d2-caps-founder-decision-20261031.json)).
The founder also chose **STRICT** isolation: writes only inside the candidate
directory; network denied except the Anthropic API; credential in a dedicated
`CLAUDE_CONFIG_DIR`; process and CPU limits; anything that cannot be enforced is
recorded not-qualified.

The T008 track then found native qualification infeasible because no task owns
four pieces ([research.md](research.md) R1–R4):

1. a native manifest profile: `agent_braid/harness_manifest.py` accepts only the
   `offline-foundations` profile with host kind `offline`;
2. a native `ClaudeTransport`: `agent_braid/harness_host_claude.py` defines the
   interface and a scripted double only;
3. a real containment backend: `agent_braid/harness_lab.py` provides only
   `SimulatedContainment`, which confines nothing;
4. an evidence-based qualification procedure that produces the records checked by
   `verify_qualification` (`harness_lab.py`) and `verify_host_qualification`
   (`harness_host_claude.py`).

This specification defines those four pieces for one host (`claude`, the Claude
Code CLI) on one platform (macOS on the founder's machine). It is engineering,
not a research protocol. Its single engineering hypothesis (H1, below) is
allowed to fail: a negative probe result is a valid outcome that leaves the
profile not-qualified.

Exclusions:

- Codex. The founder recorded the Codex profile as not-qualified (CLI absent).
  Nothing here qualifies, launches or prepares Codex; one host's qualification
  can never admit the other.
- Mutating tools. The Claude adapter keeps its read-only tool allow-list
  (`Glob`, `Grep`, `Read`) and denied list. Widening it needs its own decision.
- Admission of the SPEC-049 native pilot (SPEC-049/T004), cohort runs, case
  rosters and any evaluated outcome.
- Paid routes, API keys, Bedrock, Vertex, gateways and extra usage.
- Linux, Windows, CI runners and any host other than the founder's macOS machine.
- Changes to SPEC-048 or SPEC-049 artifacts, ADRs, `docs/STATUS.md`,
  `ROADMAP.md`, `SPEC_MILESTONE_INDEX.md` or `github-tracking.json` in this
  feature's specification change. Entries those files need, including the ADR
  that T002 drafts in a separate pull request, are listed as proposals in
  [plan.md](plan.md#proposed-shared-file-changes).

The normative contracts are [contracts/native-profile.md](contracts/native-profile.md)
and [contracts/containment-qualification.md](contracts/containment-qualification.md).

## Authorities

Constitution clause zero and Articles 5 (effects are first-class; hidden effects
are uncertainty), 6 (execution contracts preserve semantics), 7 (isolated
execution stays a distinct stage), 12 (isolation is a systems problem, not a
prompt), 13 (claimed class is not verified evidence), 14 (evidence, not
verdicts), 15 (declared metadata is not blindly trusted), 19, 20 and 24;
[GOVERNANCE.md](../../GOVERNANCE.md);
[ADR 0019](../../docs/adr/0019-bounded-local-git-runtime.md) (arbitrary commands
deferred until enforceable OS isolation exists);
[ADR 0027](../../docs/adr/0027-braid-harness-offline-foundations.md) (offline
foundations; native capability not activated);
[ADR 0021](../../docs/adr/0021-codex-claude-tooling-integration.md);
[claim discipline](../../docs/theory/CLAIM_DISCIPLINE.md);
[validation profiles](../../docs/development/VALIDATION_PROFILES.md);
SPEC-048 [spec](../048-harness-variant-laboratory/spec.md),
[tasks](../048-harness-variant-laboratory/tasks.md) and
[offline contract](../048-harness-variant-laboratory/contracts/offline-foundations.md);
SPEC-049 [tasks](../049-harness-evaluation-learning/tasks.md) and the two founder
records above.

## Founder decisions already recorded (inputs, not re-decided here)

| ID | Decision | Source |
|---|---|---|
| F1 | Qualify the Claude profile only; Codex not-qualified | founder-review-20261031.json |
| F2 | EUR 0 additional cash; no paid fallback | founder-review-20261031.json |
| F3 | D2 caps: 30 min per unit, ≤10 % of the 5-hour window per session, ≤15 % of weekly all-models per cohort, ≤16 native units; stop when weekly > 80 %, extra usage enabled, or quota reading unavailable or stale | d2-caps-founder-decision-20261031.json |
| F4 | Containment verified before every native session | founder-review-20261031.json |
| F5 | STRICT isolation as stated above; unenforceable effects are recorded not-qualified | [founder-decisions-20261031.json](evidence/founder-decisions-20261031.json) (T001; first stated in the orchestrator brief, 2026-10-31) |

T001 bound F5 into a repository founder record; NC-1, NC-5 and NC-7 fix the
exact endpoints, credential location and the write locations beyond the
candidate directory that the CLI itself needs.

## Requirements and acceptance scenarios

Each requirement has one acceptance scenario; procedures are in
[validation-plan.md](validation-plan.md) and the trace is in
[assurance.json](assurance.json).

**REQ-001 Native Claude manifest profile.** A second, closed manifest profile
for host kind `claude` is added beside `offline-foundations`. It binds the
executable hash, the build, the requested model/effort and route `subscription`,
the containment backend identity and non-zero native limits within the founder's
caps. The offline profile is byte-compatible: every existing offline manifest
parses to the same view and the same SHA-256, and every existing offline refusal
is unchanged. The native profile never sets `executionAuthorization`.
- **SC-001** Given the committed offline manifests and the offline test corpus,
  when they are parsed by the extended parser, then the bytes, digests, views and
  refusal reasons equal the pre-change results; and given a native manifest with
  any field outside the closed native schema, any limit above the founder caps,
  route other than `subscription`, or host kind other than `claude`, when parsed,
  then it is refused with a fixed reason and no partial view.

**REQ-002 Native ClaudeTransport.** A native transport runs headless
`claude -p` with the JSON event stream already planned by `build_plan`
(`--output-format stream-json`), under the containment backend of REQ-004, with
the environment allow/deny policy (`ENV_ALLOW`, `ENV_DENY`) enforced, not just
declared, and the executable launched by absolute pinned path whose SHA-256 is
re-checked at every launch. It passes `_check_transport` only with a verified
Claude host qualification whose environment hash equals the native manifest's
and that has not expired, and it refuses unless its own containment backend
passes the same verified-containment check as `_check_backend` (today
`_check_transport` never inspects a backend, so this is a required change, plan
item K2). It keeps the subscription route; it has no paid fallback and never
retries on a different route. Because `run_claude` parses output only after the
run returns, the contained launcher reads the `init` event as it arrives and
kills the process group as soon as `apiKeySource` is outside the subscription
set (plan item K1), so a paid-route session cannot run to completion. A denied
environment variable present or a missing containment qualification refuses
before launch.
- **SC-002** Given a native manifest, a verified host qualification and a
  contained launcher, when one run is dispatched, then the transport reports the
  discovered version, the run's stdout, exit, timeout, cancellation and
  settlement, the observation is labelled `host`, and `executionAuthorization`
  stays false; and given each of: no qualification, an expired or drifted one, a
  Codex qualification, `ANTHROPIC_API_KEY` in the parent environment, a non-
  subscription `apiKeySource`, a host qualification without a qualified
  backend, or an executable whose hash differs from the pin, when dispatched,
  then it refuses before launch, or for `apiKeySource` kills the process group
  at the `init` event before any `assistant` or `result` event is accepted, with
  a fixed reason, and starts no second attempt.

**REQ-003 Quota observation around every session.** Plan usage is read before
and after each native session from the source fixed by NC-6. A session starts
only if the pre-reading is fresh, every F3 stop condition is clear and the
per-session check fixed by NC-6 passes (per-unit token counts are not observed,
so how the 10 % per-session cap is checked is a founder choice); the
post-reading and the delta are recorded in the run evidence. Cohort-level caps
(15 % weekly, 16 units) need cohort state owned by SPEC-049; the gate takes that
state as a caller-supplied input and refuses when it is absent. A missing, stale or unparseable reading is a stop, not
a zero.
- **SC-003** Given quota readings, when a session is requested, then it starts
  only with a fresh pre-reading within the caps and records the post-reading and
  delta; and given a stale reading, an unavailable source, weekly use above 80 %,
  or extra usage enabled, when requested, then it refuses with a fixed reason and
  launches nothing.

**REQ-004 macOS containment backend.** A native backend implements
`ContainmentBackend` for the owned laboratory fixtures and provides the contained
launcher used by REQ-002. Before every run it verifies its own qualification and
runs the F4 pre-session check fixed by NC-11; it enforces
all four `ENFORCED_EFFECTS` (`credential`, `filesystem`, `network`, `process`) at
the STRICT level of REQ-005 to REQ-008. When any effect cannot be enforced on the
current machine (mechanism missing, profile rejected, self-check failing,
version outside the supported window), it refuses the run; it never degrades to
a weaker mode, never falls back to `SimulatedContainment`, and never labels a
weaker run `native`.
- **SC-004** Given a qualified backend on a supported machine, when an owned
  fixture runs, then `_check_backend` returns `native`, the result carries the
  backend label, and the run evidence records the qualification hash and the
  pre-session self-check results; and given the mechanism removed or
  replaced, a profile compile failure, a failed self-check or an unsupported OS
  build, when a run is requested, then it refuses with a fixed reason and no
  child is started.

**REQ-005 Filesystem effect (STRICT).** The contained child can create, modify
or delete files only inside the candidate directory and the additional locations
fixed by NC-7. Reads outside the allowed read set fixed by NC-7 are denied. Path
tricks (symlinks, hard links, `..`, case aliases, Unicode aliases, bind
locations, `/tmp` and `$TMPDIR`), inherited file descriptors, FIFOs, device
nodes and metadata indexes (Spotlight) do not widen either set.
- **SC-005** Given the contained child, when it attempts each write and read
  escape in the probe catalog (outside writes, symlink and hard-link targets
  outside, `..` traversal, case and normalization aliases, temp directories,
  reads of the operator's home and other repositories), then each attempt fails
  with a recorded denial and an independent before/after scan shows no change
  outside the allowed write set.

**REQ-006 Network effect (STRICT).** All network egress from the contained
child is denied except to the endpoints fixed by NC-1, by the mechanism fixed by
NC-1 and NC-2. DNS, raw sockets, ICMP, UDP, IPv6, local services, other
loopback ports, and Unix-domain sockets or XPC services of network-capable
daemons do not bypass the policy.
- **SC-006** Given the contained child, when it attempts connections to a
  non-allowed public host, a literal IP, IPv6, UDP and DNS exfiltration, a
  non-allowed loopback port and a proxy-bypass variant, then each fails with a
  recorded denial and the allowed endpoint remains reachable; one successful
  escape makes the network effect not-qualified.

**REQ-007 Credential effect (STRICT).** The child authenticates only through a
dedicated `CLAUDE_CONFIG_DIR` set up by the method fixed by NC-5, without copying
the operator's existing secrets into the repository, the evidence, the candidate
directory or the run logs. No other credential (operator `~/.claude`, other
Keychain items, SSH keys and SSH/GPG agent sockets, Git credentials, cloud
CLIs, browser profiles, the pasteboard, other processes' environments, API-key
environment variables) is readable by the child. Evidence records the credential
method and the observed `apiKeySource`, never a secret value.
- **SC-007** Given the contained child, when it attempts to read the operator's
  default Claude configuration, unrelated Keychain items, `~/.ssh` and agent
  sockets, Git credential helpers, cloud CLI configuration, browser profiles,
  the pasteboard, other processes' environments and inherited secret
  environment variables, then each fails with a recorded denial; a secret-scan of every
  produced artifact against the export inventory finds none.

**REQ-008 Process effect (STRICT).** The child runs in its own process group
with the CPU, memory, file-size, open-file and descendant limits fixed by NC-8,
may execute only the allow-listed executables fixed by NC-8, and is killed and
confirmed settled at timeout, cancellation and exit. No descendant survives the
run, escapes the process group, re-parents to `launchd`, is started outside the
group through LaunchServices, AppleEvents, XPC or `launchctl`, registers a
persistent agent, or signals, traces or inspects other same-user processes.
- **SC-008** Given the contained child, when it attempts to execute a
  non-allowed binary, fork beyond the limit, exceed CPU, memory, open-file,
  file-size and file-count limits, `setsid`/double-fork to escape the group,
  spawn through `open`/LaunchServices/`osascript`/`launchctl`, signal or trace
  another same-user process, and register a launch agent, and when it is
  timed out or cancelled, then
  each is denied or terminated with a recorded reason and a post-run process
  scan finds no survivor.

**REQ-009 Evidence-based qualification; no self-qualification.** A
qualification procedure runs a fixed, versioned probe catalog against the exact
backend, launcher, executable, OS build and configuration, and writes an
evidence bundle with hashes, commands, exits, environment and limits. Code never
issues a qualification. A founder or a human the founder names (NC-9) reviews
the bundle and issues the containment record (`braid-harness-containment-qualification/v0.1`)
and the Claude host record (`braid-harness-host-qualification/v0.1`) with
`evidenceSha256` bound to that bundle and `expiresAt` fixed by NC-9. Runtime code
only verifies the records against externally supplied trusted hashes. Any probe
that does not pass, or any effect that cannot be enforced, yields a
not-qualified decision record naming the failing effects (a decision record,
not a qualification record: both qualification formats require all four
effects and cannot express a partial result) and the whole profile stays
refused.
- **SC-009** Given a complete passing evidence bundle and a human issuance
  record, when the runtime verifies the records with the trusted hashes, then
  `verify_qualification` and `verify_host_qualification` accept them and a run
  proceeds; and given a record produced by the probe runner itself, a bundle
  with any failing or missing probe, an edited record, a different environment
  hash or an expired record, then verification or the issuance gate refuses.

**REQ-010 Adversarial controls are part of qualification.** For each of the four
effects the probe catalog contains escape attempts executed from inside the
contained child (not only from the parent), each with a positive control showing
the probe would detect the effect when uncontained. The catalog, its version and
its hash are bound in the evidence bundle.
- **SC-010** Given the probe catalog, when it is run once uncontained (positive
  controls in a disposable directory holding only dummy secrets created for the probe) and once contained, then
  every escape is observed uncontained and denied contained; a probe whose
  positive control fails is reported inconclusive and blocks qualification.

**REQ-011 Unblocking map.** Completion of this specification's tasks provides
inputs to SPEC-048/T008 for the Claude profile, and only then to SPEC-049/T004.
It does not itself complete T008, admit any SPEC-049 pilot, change any SPEC-048
or SPEC-049 checkbox, or imply Codex qualification.
- **SC-011** Given all SPEC-065 tasks complete, when the SPEC-048/T008 and
  SPEC-049/T004 records are inspected, then they are unchanged by this feature
  and the hand-off packet lists the issued records, their hashes and the open
  T008 acceptance items.

## Founder decisions NC-1 to NC-11

Each item was decided by the founder on 2026-10-31 in the
[founder decision record](evidence/founder-decisions-20261031.json) (T001). The
options and risks offered are kept as history. The decisions were taken in the
recommended order NC-2, NC-3, NC-4, NC-1, NC-5, NC-7, NC-8, NC-6, NC-9, NC-11, NC-10,
because the mechanism fixes what the policy can express.

- **NC-1 Exact allowed network endpoints and how they
  are enforced.** Decided (founder, 2026-10-31): option (b): `api.anthropic.com:443` plus the OAuth token-refresh endpoints (exact names to be observed by probe), enforced by a loopback proxy that checks the TLS SNI/CONNECT host; telemetry, error-reporting and update endpoints denied. ([record](evidence/founder-decisions-20261031.json)) History: macOS sandbox profiles filter by IP address and port, not by
  host name ([research.md](research.md) R6). Options:
  (a) `api.anthropic.com:443` only, enforced by a loopback forward proxy that is
  the only allowed egress and checks TLS SNI/CONNECT host against the list;
  (b) (a) plus the OAuth/console endpoints needed to refresh the subscription
  token (exact names to be observed by probe);
  (c) (b) plus telemetry, error-reporting and update endpoints;
  (d) resolved-IP allow-list pinned at qualification time.
  Risks: (a) may break token refresh mid-session (a failed run, not a leak);
  (c) sends usage data off-machine and widens the surface; (d) breaks on CDN
  rotation and silently allows co-hosted services on the same IPs; a proxy adds
  a trusted component that must itself be qualified. Related: whether
  `DISABLE_NONESSENTIAL_TRAFFIC`-style settings and auto-update are forced off
  (recommended with (a)/(b), unverified until probed).

- **NC-2 Isolation mechanism.** Decided (founder, 2026-10-31): option (b): a dedicated macOS user account plus `sandbox-exec`. ([record](evidence/founder-decisions-20261031.json)) History: `sandbox-exec` and SBPL
  are deprecated by Apple yet present on this machine and already used by
  `system_one_verified_stdio.py` for a network deny. Options:
  (a) accept `sandbox-exec` with a pinned binary hash, OS-build window and
  per-run self-checks, re-qualifying on any OS update;
  (b) a dedicated macOS user account plus `sandbox-exec` (UID separation for
  credentials and files, sandbox for network);
  (c) a virtual machine (for example a macOS guest) with only the candidate
  directory shared and a host firewall;
  (d) a Linux container/VM on macOS, which changes the host profile to Linux
  Claude Code and needs its own qualification.
  Risks: (a) undocumented semantics can change in any OS update and Apple gives
  no stability guarantee; (b) adds account administration and a second
  credential login; (c) and (d) cost setup time, disk and memory, and (d) is no
  longer "macOS native". Refusal-on-failure applies to every option.

- **NC-3 Supported macOS versions.** Decided (founder, 2026-10-31): option (b): the macOS 27.0.x series, with the self-check re-run on each build. ([record](evidence/founder-decisions-20261031.json)) History: Options:
  (a) exactly the observed build (macOS 27.0.1, build 26A434) and nothing else;
  (b) the 27.0.x series, re-running the self-check on each build;
  (c) a wider window. Risk: wider windows trust untested sandbox behavior; the
  narrowest window refuses after every OS update until re-qualified.

- **NC-4 Supported Claude Code versions and update
  policy.** Decided (founder, 2026-10-31): option (a): exactly Claude Code 2.1.292 with a pinned executable SHA-256; auto-update disabled for the laboratory configuration. ([record](evidence/founder-decisions-20261031.json)) History: Observed `2.1.292 (Claude Code)` at `/opt/homebrew/bin/claude`.
  Options: (a) exact version and executable SHA-256, auto-update disabled for
  the laboratory configuration; (b) a half-open `CompatibilityWindow`
  `[2.1.292, 2.2.0)` with the executable hash bound per qualification; (c) a
  wider window. Risks: (a) refuses after each update until re-qualified;
  (b)/(c) let behavior that probes never saw (new tools, new network calls,
  new credential paths) run under an old qualification.

- **NC-5 Credential isolation without copying secrets.** Decided (founder, 2026-10-31): option (c): the dedicated user's own login, with its own `CLAUDE_CONFIG_DIR` and keychain; no secret is copied. ([record](evidence/founder-decisions-20261031.json)) History:
  Options: (a) log in once inside the dedicated `CLAUDE_CONFIG_DIR` with the
  CLI's own login flow, leaving the token where the CLI stores it for that
  directory (location to be observed by probe; may be the login Keychain);
  (b) a long-lived subscription token from `claude setup-token`, kept in a
  dedicated Keychain item and injected into the child environment only at
  launch; (c) a dedicated macOS user (NC-2 b) whose own login holds the token;
  (d) reuse the operator's existing login. Risks: (a) if the token lives in the
  shared login Keychain, a Keychain-reachable child may read other items, so the
  sandbox must deny Keychain access except the one item, which may not be
  expressible; (b) an environment secret is visible to the child process and
  must be excluded from every export; (c) adds account setup; (d) violates the
  STRICT credential rule and is listed only to be refused. Interaction: a
  configuration directory purged after every run (NC-7 b) would destroy an
  option (a) login, so (a) needs a persistent configuration directory or a
  separate persistent credential location.

- **NC-6 Quota reading source and freshness.** Decided (founder, 2026-10-31): option (a): the Claude Desktop usage card read by the orchestrator session immediately before and after each session; freshness 5 minutes; a session starts only if the 5-hour window is below 90 % used; the cohort stops if a post-reading shows more than 10 % of the 5-hour window used by one session. ([record](evidence/founder-decisions-20261031.json)) History: The
  founder records used the Claude Desktop usage card (read-only). Options:
  (a) the desktop app usage reading taken by the orchestrator session
  immediately before and after each session; (b) a manual reading by the
  founder; (c) a CLI-side usage report if the supported version offers one in
  headless mode (to be probed). Also the freshness bound (for example 5 or 15
  minutes), and how the 10 % per-session cap is checked when per-session use
  is only visible after the fact (for example: refuse when less than 10 % of the
  5-hour window remains below a founder-set ceiling, and stop the cohort when a
  post-reading shows the cap was exceeded). Risks: (a) depends on the desktop app and a session outside the
  sandbox; (b) is slow and error-prone; (c) may not exist or may itself use the
  network; a loose freshness bound lets two sessions overlap one reading.

- **NC-7 Filesystem write and read sets.** Decided (founder, 2026-10-31): writes = candidate directory + per-run `TMPDIR` + the dedicated user's configuration directory, with session state purged after each run and the credential kept; reads = option (i): candidate directory, configuration directory, the Claude executable and system libraries. ([record](evidence/founder-decisions-20261031.json)) History: STRICT says
  writes only inside the candidate directory, but the CLI also writes session
  state under its configuration directory and temporary files. Options for
  writes: (a) candidate directory only, configuration directory read-only (the
  CLI may fail; a failed run, not a leak); (b) candidate directory plus a
  run-scoped `CLAUDE_CONFIG_DIR` and run-scoped `TMPDIR`, both purged after the
  run except the evidence the contract keeps; (c) (b) with a persistent
  configuration directory across runs. Options for reads: (i) candidate
  directory, configuration directory, the Claude executable and system
  libraries only; (ii) (i) plus the source checkout read-only. Risks: (c) lets
  state leak between runs and between arms; (ii) exposes repository content not
  in the context package. Interaction with NC-5: see the note there.

- **NC-8 Process and CPU limits and the executable
  allow-list.** Decided (founder, 2026-10-31): wall 30 min, CPU 30 min, memory 4 GB, file size 64 MB, 256 open files, 16 descendants; executables = the Claude binary plus helpers observed by probe. ([record](evidence/founder-decisions-20261031.json)) History: Values for session wall time (at most the F3 30-minute unit
  cap; today the shared host bound is 60 s, see analysis A2), CPU seconds, address space or memory, file size,
  open files and descendants, and which executables may run (the Claude binary
  and any helper the allowed read-only tools need, such as a bundled search
  tool, to be observed by probe). Note: `RLIMIT_NPROC` on macOS counts per user,
  not per run, so a descendant cap may need NC-2 (b) or a supervisor. Risks:
  tight limits truncate long tasks, which the D2 decision already counts as
  interrupted; loose limits weaken the process effect.

- **NC-9 Issuer, validity and re-qualification
  triggers.** Decided (founder, 2026-10-31): issuer is the founder only; `expiresAt` 30 days; early re-qualification on any change of OS build, Claude Code version or hash, profile bytes, probe catalog, proxy or credential method. ([record](evidence/founder-decisions-20261031.json)) History: Who may issue (founder only, or a named reviewer), the
  `expiresAt` horizon (for example 7, 30 or 90 days), and which changes force
  re-qualification before expiry (OS build, Claude Code version or hash,
  profile bytes, probe catalog, proxy, credential method). Risk: long validity
  with weak triggers lets drift run under an old record; short validity costs
  repeated probe sessions within the D2 caps.

- **NC-11 What satisfies F4 ("containment verified
  before every native session").** Decided (founder, 2026-10-31): option (b): before every session, recompute the environment hash, verify both records and run the contained subset FS-01, NET-01, CRED-01, PROC-01 and NET-06. ([record](evidence/founder-decisions-20261031.json)) History: Options: (a) recompute the environment hash
  and verify both records only; (b) (a) plus a short contained probe subset per
  session (the contract proposes FS-01, NET-01, CRED-01, PROC-01 and NET-06);
  (c) the full catalog before every session. Risks: (a) misses drift the hash
  does not cover (for example a changed system daemon); (b) checks only a sample;
  (c) costs time per session and, for live probes, quota.

- **NC-10 Live probe budget.** Decided (founder, 2026-10-31): option (b): a separate small cap for live qualification probes, up to 3 minimal `claude -p` sessions per attempt (Haiku, low effort), each at most 2 % of the 5-hour window, separate from the D2 cohort caps. ([record](evidence/founder-decisions-20261031.json)) History: Credential, network and
  route probes need at least one real authenticated `claude -p` session.
  Options: (a) count qualification sessions inside the D2 caps; (b) a separate,
  smaller cap for qualification only; (c) only probes that need no model turn,
  accepting that route and token-refresh behavior stay unobserved (which leaves
  REQ-002 and REQ-007 not-qualified). Model and effort for probe sessions are
  part of this decision.

## Scientific boundaries and compatibility

- **H1 (engineering hypothesis, may fail):** on the founder's macOS machine, the
  mechanism chosen in NC-2 can enforce the four effects at the STRICT level while
  the Claude Code CLI still completes a read-only headless session. A failed
  probe, an unenforceable effect, or a CLI that cannot complete under the policy
  is a valid negative result and leaves the profile not-qualified; no requirement
  needs H1 to be true.
- Probe results are empirical observations on one machine, one OS build and one
  CLI version over a finite catalog. They are not a proof of isolation, not a
  general sandbox guarantee and not evidence about other machines (Articles 4,
  13). A qualification states its exact domain and expiry.
- Same-UID hostile processes outside the sandbox, kernel or sandbox bugs,
  physical access and supply-chain compromise of the CLI are out of scope and
  stated as residual risks in the evidence.
- Compatibility: the offline profile, `agent-braid-plugin`, AIM, runtime grants,
  telemetry contracts and every SPEC-048/049 artifact are unchanged. The native
  profile is a new, versioned closed schema. Both qualification formats keep
  their current shape (`enforced` must equal the four effects); if a format
  change is needed it becomes a new version, never an in-place edit.

## Evidence and unresolved questions

Obtained evidence: none for any scenario. Planned evidence per scenario is in
[assurance.json](assurance.json). Decided: NC-1 to NC-11 and the F5 binding
([founder decision record](evidence/founder-decisions-20261031.json), T001).
Open: values to be observed by probe (OAuth refresh host names, helper
executables, configuration paths that are session state) are fixed only in the
T009 evidence bundle. Human review of this specification is pending.
