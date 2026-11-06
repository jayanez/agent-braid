# SPEC-065 T009, real attempt `t009-20261106a`: result (pass rule satisfied, not yet qualified)

Date: 2026-11-06 (bundle `startedAt` 1793983494, 16:44:54 UTC), on commit `320b00c4`. Founder's Mac, dedicated
account `braidlab`, backend `macos-dedicated-user-sandbox-exec`. Bundle: `evidence/qualification/t009-20261106a/`
(copied verbatim, `SHA256SUMS` beside it). The run followed the self-check on the same commit, after the PROC-03
decision of `evidence/founder-decisions-20261106.json` and the probe change of #1134.

**This is not a qualification.** `passRuleSatisfied` is `true`, but `qualificationRecordWritten` is `false` and
`executionAuthorization` is `false`: the runner does not write qualification records (a runner-produced record must refuse, a T010 negative control). Only the T010 issuer fixed by
NC-9 (the founder) can review this bundle and issue the containment and Claude host records. Until T010 issues them
and both verify against the trusted hashes, native launches keep refusing.

## 1. Run facts

| Item | Value |
| --- | --- |
| Attempt | `t009-20261106a` (fifth attempt, full budget of 3 sessions) |
| `environmentSha256` | `e91007d8626998d49ccb574bc241752bccc5134616598dd76b8f63630f9d818a` |
| `catalogSha256` | `5ecbd7eba61f4bc87322cce79153f5b5812d186aebb9eff43d3098e30134e929` (the hash #1134 announced) |
| `bundleSha256` | `45eee4d81bda711f6a1a73ae6a54e373e693208967b29bce352d7f428ef5d1ce` |
| Environment | macOS 27.2 (build 26B123), arm64, `claude` 2.1.292 (sha256 `97a01e5b...0386138f`), `profileSha256` `08e3ff93...eaf65294`, `sandboxExecSha256` `10cf4a46...6b2a92` (all unchanged from attempt 4) |
| Pre-flight | `--self-check` `self-check-ok`: compile check `exec-denied`, the five F4 probes as expected, fixture and launch-probe runs exit 0 (the second launch-probe run counted one `unrelatedProcesses`, none unreadable), `auth` stage ok (exit 0, token present), `startup` stage `reachedInit` true (then timed out, as designed with egress refused: 19 CONNECTs, 19 denied, 0 allowed, 0 bytes, no leak), `sessionsStarted` 0 |
| Verdict | `bundle-written`; `sessionsStarted` 3 (CRED-05, NET-05-CLI, HOST-01); `hostFunctional` true; `passRuleSatisfied` true |
| Probes that passed | 32 of 32 (attempt 4: 31 of 32); `notEnforced`, `inconclusive` and `missingProbes` are empty |
| Quota | 5-hour window 1 % before and after every session (delta 0), weekly 75 % (delta 0), `operator-typed-usage`, decision `proceed` (`within-caps`) for each |

Bundle integrity: `SHA256SUMS` lists the five bundle files, then `operator/t009-run-t009-20261106a.txt` (terminal
transcript, byte-verbatim; `.gitattributes` already covers `t009-2026110*/operator/*.txt`) and
`operator/t009-self-check.json`. The four file hashes in `summary.json` (`files`) match the copied files, the
transcript names the same `bundleSha256` (three times) and the same catalog and environment hashes. The identifier
scan of the published files found only `/Users/braidlab/...` paths (approved for publication,
`founder-decisions-20261104c.json`, T009-BUNDLE-PUBLISH); no founder account, e-mail address or token shape.

## 2. Outcome per effect

| Effect | Status | Not as expected | Notes |
| --- | --- | --- | --- |
| credential (7) | **enforced** | none | CRED-05 denied (session completed, `apiKeySource` `none`); CRED-02 `mach-secd` excluded (`notApplicable`) |
| filesystem (7) | **enforced** | none | FS-07 `mach-spotlight` excluded |
| network (9) | **enforced** | none | NET-05-CLI denied (session completed; 3 connections, all to `api.anthropic.com:443` through the proxy); NET-02 `tcp-ipv6-literal` excluded; NET-06 allowed as expected |
| process (8) | **enforced** | none | PROC-03 now denied in both contained rows; PROC-07 `ptrace-sibling` excluded |
| host | **functional** | none | HOST-01 completed under the policy |

The three sessions reached `init` and completed (`exitReason` `ok`, exit 0, token present, `settled` true,
`timedOut` false).

## 3. PROC-03 with incompressible data

Row facts (`results.jsonl` lines 74 to 76; limit `LIMITS["memoryBytes"]` = 4 GiB = 4,294,967,296 bytes; `memory`
fills the limit plus 1 GiB with incompressible data and holds it for 2 s):

| Row | memory | file-size | open-files | `limitExceeded` | `peakBytes` | samples | settled |
| --- | --- | --- | --- | --- | --- | --- | --- |
| uncontained control | allowed | allowed | allowed | `unavailable` | n/a | n/a | true |
| contained (fixture) | **denied** | denied | denied | `memory` | 4,295,802,880 | 153 | true |
| contained-launch | **denied** | denied | denied | `memory` | 4,484,923,392 | 154 | true |

Reading:

1. **The change of #1134 did what it was meant to.** With pages that do not compress, the footprint crossed the
   limit in both contained rows and the watchdog stopped the helper (`limitExceeded` `memory`, a denial the judge
   accepts only because the backend attributes it to the memory watchdog). The fixture peak is 835,584 bytes over
   the limit, the launch-probe peak 189,956,096 bytes (about 181 MiB) over it: how far over depends on when the
   sample falls, as the catalog residual says.
2. **The control stays a real control.** Uncontained, all three attempts were allowed: the 5 GiB allocation
   completed, so the denials are the containment's, not the host's.
3. **Swept members.** Both contained rows record `escapedProcesses` 1 with `survivingProcesses` 0 and `survivors` 0:
   a member the sweep killed while it was still exiting, reported and not held against the row (the round 4 rule;
   the same pattern is in attempt 4). Nothing outlived the sweep.
4. **What this does not show.** The accepted residual still applies: compressible memory counts at its compressed
   size, a process that exceeds the limit and exits between two samples is not stopped, and no kernel limit backs
   the watchdog. A denial here covers incompressible memory held longer than the sampling interval.

## 4. T010 review checklist

Derived from the T010 text in `tasks.md`. Each item is a fact for the issuer to check, not a decision taken here.

1. **Per-effect status.** `summary.json` `effects`: credential, filesystem, network and process all `enforced`;
   `failing` and `missing` empty in each; `notEnforced`, `inconclusive`, `missingProbes` empty. The
   not-applicable exclusions are CRED-02 `mach-secd`, FS-07 `mach-spotlight`, NET-02 `tcp-ipv6-literal` and
   PROC-07 `ptrace-sibling`, each by a tested rule recorded in the catalog.
2. **HOST-01 completed.** `results.jsonl` line 93: `mode` `contained`, `outcome` `allowed`, `exitReason` `ok`,
   `exitCode` 0, `authToken` `present`, `settled` true, `timedOut` false; `summary.json` `hostFunctional` true. Line
   92 is its uncontained detector self-test (allowed).
3. **CRED-05 `apiKeySource`.** `results.jsonl` line 65 (contained CRED-05) records `independent.apiKeySource`
   `"none"`; NET-05-CLI (line 67) and HOST-01 (line 93) record `"none"` too. `SUBSCRIPTION_KEY_SOURCES` in
   `agent_braid/harness_host_claude.py` (line 48) is `frozenset({"none", "oauth"})`, so the observed value is
   **inside the set**. No reviewed edit of the constant is needed before issuance; the constant is not changed by
   this PR.
4. **Environment hash and what it omits.** `environment.json` and `summary.json` bind `environmentSha256`
   `e91007d8...9d818a` over the fields of `environment.json`: OS product and build, architecture, backend, `claude` version and hash, profile
   hash, `sandbox-exec` hash and probe catalog hash. Per MDRV-04 it omits `harness_manifest.py`,
   `harness_context.py`, `harness_observation.py` and `system_one.py`: a change in those files does not move the
   hash, so the issuer should check that they are unchanged between `320b00c4` and the issuance commit, or accept
   the drift knowingly.
5. **NC-9 expiry rule.** spec.md NC-9: "issuer is the founder only; `expiresAt` 30 days; early re-qualification
   on any change of OS build, Claude Code version or hash, profile bytes, probe catalog, proxy or credential
   method." The contract (`contracts/containment-qualification.md`, Records) fixes the anchor: `expiresAt` is 30
   days after issuance. `verify_qualification` only checks `now < expiresAt`; it does not bound the horizon, so the
   30 days are the issuer's to set correctly in both records.
6. **Residuals accepted by the founder.**
   - PROC-ESC-1 (`evidence/founder-decisions-20261104c.json`): a descendant that calls `setsid` and is reparented
     before the backend sees it may read as unrelated; accepted for T009. The PROC-04 catalog residual narrows it:
     the backend attributes such a descendant by the inherited run tag, and a descendant that also scrubs its
     environment before the backend first sees it is not attempted by the probe.
   - PROC-03 (`evidence/founder-decisions-20261106.json`, "A. Residuo aceptado"): the memory limit is the physical
     footprint of the child's tree at most 4 GiB; compressed memory counts at its compressed size.
   - Catalog residuals (`catalog.json`): NET-02 (IPv6 egress untested when the machine has no IPv6 route), PROC-03
     (the above, plus no stop for a burst between two samples and no kernel limit behind the watchdog), PROC-04 (the
     environment-scrubbing variant above), PROC-07 (`ptrace-sibling` unobservable when the kernel refuses it
     uncontained).
7. **Negative controls T010 must run** (T010 text and `validation-plan.md` procedure_009): a runner-produced
   record, an edited record, a record with another environment hash and an expired record must each refuse in
   `verify_qualification` / `verify_host_qualification` against the trusted hashes; then the T006 transport
   `_check_transport` and `_check_backend` against the native manifest. The validation plan also names a record
   for a bundle with a failing or missing probe; this bundle has none, so that control needs a constructed input.

## 5. Changes in this PR

- **Evidence only**: bundle `evidence/qualification/t009-20261106a/` with `SHA256SUMS`, the transcript and the
  self-check output under `operator/`; this result; the attempt-5 line in `tasks.md` T009 (T009 stays checked, T010
  stays open). No code, probe, catalog, profile or test changed.

## 6. Follow-ups

1. T010 (human, founder only, NC-9): review this bundle with the checklist above and decide. If the founder issues,
   the issuance record goes to `evidence/qualification/issuance-<date>.json` with `evidenceSha256` =
   `45eee4d81bda711f6a1a73ae6a54e373e693208967b29bce352d7f428ef5d1ce`.
2. Any change of OS build, Claude Code version or hash, profile bytes, probe catalog, proxy or credential method
   before issuance makes this bundle stale for issuance (NC-9); a new attempt would be needed.
3. The kernel-limit question (attempt 3, section 7 item 3) stays open; the accepted PROC-03 residual does not close
   it.
