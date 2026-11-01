# ADR 0034: Native Claude laboratory containment

- **Status:** Proposed. Not accepted: founder acceptance is a separate act and must precede any native session.
- **Date:** 2026-11-01
- **Deciders:** Juan Antonio Yáñez García (founder); decision pending
- **Constitutional articles:** 0, 4–7, 12–15, 19, 20, 24
- **Specification:** [SPEC-065](../../specs/065-native-claude-containment/spec.md) (track HAR.1), task T002

## Context

The Braid Harness laboratory ([ADR 0027](0027-braid-harness-offline-foundations.md))
runs only an offline profile. The only qualified-shaped `ContainmentBackend` before
SPEC-065 is `SimulatedContainment`, and `ClaudeTransport` has only a scripted double. A native
Claude Code session (`claude -p`) is an effectful child process: it reads files,
holds a credential, opens network connections and spawns helpers. Article 12 treats
isolation failures as systems problems, not prompt problems, so no native
session may run until a qualified OS-level mechanism exists. [ADR 0019](0019-bounded-local-git-runtime.md)
defers arbitrary commands until enforceable OS isolation exists. The founder
recorded F5 and NC-1 to NC-11 on 2026-10-31
([record](../../specs/065-native-claude-containment/evidence/founder-decisions-20261031.json)).

## Decision

1. **Mechanism (NC-2).** Native Claude laboratory sessions run under a dedicated
   macOS user account plus a deny-default `sandbox-exec` (SBPL) profile. UID
   separation covers credentials, files and per-user process counts; the profile
   covers files, network and process execution. The account is created by the
   operator, outside code.
2. **STRICT policy (F5).** Writes only in the candidate directory, a per-run
   `TMPDIR` and the dedicated user's `CLAUDE_CONFIG_DIR` (NC-7). Network denied
   except `api.anthropic.com:443` and OAuth token-refresh hosts, enforced by a
   loopback proxy that checks TLS SNI against the `CONNECT` host; telemetry and
   update endpoints denied (NC-1). The refresh host names are not yet known: they
   are observed by probe and fixed in the T009 bundle, and until then the code
   allows only the API host. Credential only through the dedicated user's own
   login, with no secret copied (NC-5). Wall 30 min, CPU 30 min, memory 4 GB, file
   size 64 MB, 256 open files, 16 descendants and an executable allow-list (NC-8).
   Any effect the mechanism cannot enforce leaves the profile **not-qualified**;
   the backend refuses rather than degrades and never falls back to simulated
   containment.
3. **Pinned environment.** macOS 27.0.x only, with the self-check re-run on each
   build (NC-3); Claude Code exactly 2.1.292 with a pinned executable SHA-256
   checked at every launch and auto-update disabled (NC-4). The proxy and the
   credential method are part of the environment hash.
4. **Per-session verification (F4, NC-11).** Before every session the backend
   recomputes the environment hash, verifies the containment and Claude host
   records, and runs the contained probe subset FS-01, NET-01, CRED-01, PROC-01 and
   NET-06. A mismatch or non-denial refuses the session and is appended to the run
   evidence.
5. **Quota (F2, F3, NC-6, NC-10).** No paid route. Plan usage is read from the
   Claude Desktop usage card by the orchestrator before and after each session; the
   reading is an external, timestamped observation (fresh within 5 minutes). A session
   starts only below 90 % of the 5-hour window; the cohort stops on a missing or
   stale reading or when one session uses more than 10 %. Qualification probes have a separate cap of three minimal sessions
   per attempt, each at most 2 % of the 5-hour window.
6. **Human issuance (NC-9).** The probe runner writes evidence only. Qualification
   records are issued by the founder alone, from an evidence bundle, with trusted
   hashes passed to the runtime out of band. Records expire after 30 days and are
   re-issued early on a change of OS build, Claude version or hash, profile bytes,
   probe catalog, proxy or credential method. No code path self-qualifies.
7. **Authority.** `executionAuthorization` stays `false` everywhere. Accepting this
   ADR authorizes no native session, probe or account setup. A native session needs
   this ADR accepted, a T009 evidence bundle reviewed by the founder and an issued
   and unexpired qualification (T010).
8. **ADR 0019 is not lifted.** Its deferral of arbitrary commands stands. This
   decision admits the hash-pinned Claude executable plus the helpers listed in a
   reviewed T009 bundle, under one qualified policy; no other command or shell.
9. **ADR 0027 boundary.** On acceptance, the "native capability not activated"
   wording is amended for the Claude profile only; capability is not activated until
   an issued, unexpired qualification exists (item 7). Codex stays not-qualified (F1).

## Current implementation state

Merged: `agent_braid/harness_containment_macos.py` (T005) builds the policy, SBPL
profile, environment hash, loopback `EgressProxy`, supervisor and F4 pre-run checks
with unit tests; `agent_braid/harness_quota.py` (T004) is a pure gate over supplied
readings. Neither qualifies anything: whether the profile enforces each effect is
decided only by the T007/T009 probes and the human records (unit tests are not
containment evidence), and the Keychain
(no `mach-lookup` is allowed) and refresh-endpoint behavior are untested until then.
Not yet built: the native manifest profile (T003), the native `ClaudeTransport`
(T006), the probe runner (T007) and the live probe attempt (T009).

## Alternatives considered

- **Sandbox without a dedicated user.** Rejected (NC-2): no UID separation for
  credentials, and `RLIMIT_NPROC` is per user so descendants cannot be capped.
- **macOS or Linux VM, container.** Stronger boundary but heavy, with a second login
  and network policy, or a different host profile.
- **Pinned IP addresses instead of a proxy.** Sandbox rules match addresses and
  ports, not names; the proxy makes the name list enforceable at the cost of a
  trusted component.
- **Reusing the operator's login or copying a token.** Refused (NC-5).

## Consequences

- Positive: a native Claude measurement for SPEC-048/T008 and SPEC-049 becomes
  possible, if the T009 probes show all four effects enforced, with containment
  enforced by the OS rather than by model or CLI behavior.
- Negative: operator account administration; a trusted proxy in the qualification;
  re-qualification every 30 days and on any trigger.
- Uncertain (H1): the mechanism may be unable to enforce all four effects while the
  CLI still completes a read-only session. That is a valid negative result and
  leaves the profile not-qualified.

## Residual risks

- `sandbox-exec` is deprecated and its profile language undocumented; any OS update
  can change behavior. Mitigation: NC-3 window and per-build self-check.
- Same-UID hostile processes outside the sandbox, kernel or sandbox bugs, physical
  access and supply-chain compromise of the CLI are out of scope.
- The proxy cannot inspect TLS contents; encrypted ClientHello would hide the real
  SNI, so the proxy refuses it. Allowed endpoints can still carry data to Anthropic.
- Probe results are observations on one machine, one OS build and one CLI version
  over a finite catalog, not a proof of isolation (Articles 4, 13).
- Quota readings are manual or external and can be wrong; the caps are limits on
  policy, not measured billing.

## Validation

Per the SPEC-065 [validation plan](../../specs/065-native-claude-containment/validation-plan.md)
and [assurance.json](../../specs/065-native-claude-containment/assurance.json). Revisit
this decision if `sandbox-exec` stops working on a supported build or a probe shows an
effect cannot be enforced.

## References

- [Constitution](../../CONSTITUTION.md)
- [SPEC-065 plan](../../specs/065-native-claude-containment/plan.md) and [founder decisions NC-1 to NC-11](../../specs/065-native-claude-containment/evidence/founder-decisions-20261031.json)
- [ADR 0019](0019-bounded-local-git-runtime.md)
- [ADR 0027](0027-braid-harness-offline-foundations.md)
