# T009 attempt 1: diagnosis

Date of the attempt: 2026-11-03 (attempt name `t009-20261104`). Written offline, with doubles only:
nothing native was run for this diagnosis (no `claude`, no `sandbox-exec`, no `sudo`, no `launchctl`),
and no account changed. The only reads of the founder's machine were file listings and plist parses
of the system launchd directories.

## 1. Facts (from the founder's run, as relayed)

Dry run: `ready`, all 34 checks `ok`. Real run, driver `scripts/har_t009_attempt.py --founder-go`,
braidlab session, pre reading typed `32` / `38` / `n` / `now`. Printed:

```json
{"verdict":"error","reason":"ProbeError: secret-in-artifact","quota":{"started":1},"nativeRun":true}
```

(relayed in this form; the driver also prints `outDir`, `next` and `executionAuthorization: false`).
The session counter in the output directory, `.sessions.json`:

```json
{"sessionsStarted": 1, "quotaStop": "session-refused-self-check-failed"}
```

No post reading was asked. No bundle file was written.

## 2. What the code did, in order (derived from the source at 38c0b268)

1. `QualificationProbeRunner.run` ran every helper probe in its three modes (the contained ones
   natively under the sandbox) and, for the three session probes, called the session driver.
2. Session 1 (CRED-05): `_reserve_session` counted it (`sessionsStarted: 1`), the transport factory asked
   for the pre reading, and `native_session_driver.drive` called `transport.version()`, which is
   `backend.launch((claude, "--version"))`. `launch` runs `_pre_session("launch", ..., probes=True)` before it
   spawns anything: mechanism checks, the compile check, then the five F4 probes.
3. That check raised `LabError("self-check-failed")`; the transport re-raised it as `ClaudeHostError`, the
   driver returned `SessionResult(refused="self-check-failed")`, `_settle_quota` turned it into
   `session-refused-self-check-failed`, `_session_row` persisted it as `quotaStop`, and the other two
   session probes and the remaining modes became `refused: quota-stop` rows. No `claude` session was
   started and no prompt was sent; the typed pre reading was never used.
4. `write_bundle` built the four texts and `scan_for_secrets` raised `secret-in-artifact` before
   `mkdir`, so nothing was written. The error carried no detail, so the file, the line and the rule
   are unknown from the output alone.

What `self-check-failed` does and does not say (`harness_containment_macos.py`, lines 1126 to 1141):
it is raised when the compile check's positive case does not exit 0 (the pinned `claude --version`
under the profile) or when an F4 probe is observed `denied` where `allowed` was expected (NET-06) or
`error`. It is not an escape: an F4 probe observed `allowed` where `denied` was expected is
`self-check-allowed`. Whether it was the compile check or an F4 probe, and which, is not recorded.

## 3. Offline reproduction

`tests/test_harness_qualification_probes.py::AttemptOneReproductionTests` drives the runner and
`write_bundle` through the same path with doubles: session 1 refused with `self-check-failed`, the other
modes `quota-stop`, the uncontained-control detector self-tests, and a credential list read by
`credential_values` from a fake `.claude.json` as Claude Code 2.1.x writes it (`userID` 64 hex,
`oauthAccount` with `accountUuid`, `emailAddress`, `organizationUuid`, `organizationName`,
`displayName`, `billingType`, `organizationRole`; `firstStartTime`, `numStartups`, `installMethod`,
`autoUpdates`, `lastModelUsage` with `claude-haiku-4-5-20251001`, `cachedGrowthBookFeatures`).

| Channel into the bundle | Rule that fires | Reproduced | Evidence |
| --- | --- | --- | --- |
| Baseline of attempt 1 with a benign launchd list and the fake config | none | bundle written | 9 credential candidates; none occurs in any of the five bundle files |
| `machNames` of PROC-06 (the launchd names the runner enumerates, recorded in 3 rows) | `long-run` | yes, with real names | below |
| `quota.json` `decision.reason` and rows' `quotaStop`, composed as `session-refused-<code>` | `long-run` | yes, for any code of 24 or more characters (not attempt 1) | below |
| Credential literals from `.claude.json` / `.credentials.json` | `listed-literal` | no collision found | the 9 fake candidates (UUIDs, model id, billing type, `userID`, env-var-like and flag values) are all absent from the bundle's closed vocabulary |
| `changedOutside` paths | `long-run` | not reproducible with realistic paths | longest component the arena builds is 36 characters (`work-<8>-braid-adj-<12 hex>`); hardened anyway |
| `configDir` listing names, `apiKeySource` label | none | already hardened | `_listing_name` (38 characters per part), `_key_source_label` |
| `environment.json`, `catalog.json`, `summary.json` | none | no | fixed facts and 64-hex digests; the real catalog is part of every existing test bundle |
| `egress` counter keys (NET-05-CLI only) | possible, host-derived | not reproduced | keys are the policy endpoints or fixed `denied:` codes; residual |

### 3.1 Launchd service names (`machNames`): reproduced with the names declared in the system plists; not yet observed in a run

`parse_launchd_names` keeps any reverse-DNS token of `launchctl print`, `_MACH_NAME` puts no bound on a
segment, and the bundle then records up to 2000 names three times (once per mode). `_LONG_RUN` refuses
any run of 40 or more characters of `[A-Za-z0-9+_=-]` that is not a 64-hex digest, and a dot ends a run,
so a name whose dotless segment is 40 or more characters is refused. On the founder's machine (file
parse of `Label` and `MachServices` of 2539 names from `/System/Library/Launch{Daemons,Agents}`,
`/Library/Launch{Daemons,Agents}` and the founder's own agents; 2534 pass `_MACH_NAME`), three names
trip the rule:

- `com.apple.proactive.SuggestionRequest.ps_unstructured_reminder_interaction_suggestions` (48-character run)
- `com.apple.proactive.SuggestionRequest.ps_unstructured_calendar_interaction_suggestions` (48)
- `com.apple.SoftwareUpdateNotificationManagerService` (40, CamelCase)

The first two are `MachServices` of the system LaunchDaemon `com.apple.coreduetd` (and of the user agent
`com.apple.knowledge-agent`); the third of the agent `com.apple.SoftwareUpdateNotificationManager`. Each is
kept by `parse_launchd_names` when it appears quoted in a listing (checked). The next-longest dotless
segment is 39 characters (`UserNotificationCenterAgent-LoginWindow`), one under the limit. The test doubles
used `com.apple.fake.service`, which is why no existing test saw this.

Reproduction against the unchanged module (HEAD) and the fixed one, same World double, attempt-1 path:

```
ORIGINAL (HEAD)  benign names -> bundle written | Apple long names -> ProbeError secret-in-artifact (no detail)
FIXED            benign names -> bundle written | Apple long names -> bundle written
```

Not confirmed: that `launchctl print system` and `user/<uid>` list these names on the founder's machine
(no `launchctl` was run). `parse_launchd_names` keeps them whenever they appear, they are declared by
daemons every Mac loads, and the refusal happened at the one place that records launchd names. The
redacted report below turns this into an observation on the next failure; with the fix in place this
particular refusal cannot recur.

### 3.2 Composed reason codes: a second, latent channel

`_settle_quota` stores `f"session-refused-{session.refused}"`: 16 characters plus a code from the backend,
transport or quota modules. Of the 332 hyphenated string literals in those modules (and the manifest, lab,
host and probes modules), 31 give a composed string of 40 or more characters; most are reason codes, for example `session-refused-operator-account-unresolved` (43),
`session-refused-dedicated-user-own-login` (40), `session-refused-process-accounting-failed` (41),
`session-refused-workdir-outside-run-root` (40) and `session-refused-qualification-environment-mismatch`
(50). The module writes it to `quota.json` and to every following row, and the scan refuses it. Attempt 1's
code was `self-check-failed` (33 characters), so this did not fire; any other refusal of a first session
with a 24-character or longer code would lose the bundle in the same way. The reproduction above
(`refused=operator-account-unresolved`, `dedicated-user-own-login`) fails on HEAD and passes fixed.

### 3.3 What was looked for and not found

Credential literals: the candidates a 2.1.x `.claude.json` yields (UUIDs, the model id, `billingType`,
flag values that look like constants, `userID`) do not occur in `environment.json`, `catalog.json`
(checked token by token: the 38 candidate-shaped tokens of the catalog are digests and attempt names),
`results.jsonl`, `quota.json` or `summary.json`, so no literal list entry explains attempt 1 on its own. A
real OAuth token or API key (`sk-ant-...`) would be a true positive and is still refused. No change was
made to which values are read: e-mail addresses, paths and URLs stay out of the list because they cannot be
told apart from legitimate text (`_SECRET_LIKE`); UUIDs, ids and account metadata stay in, because a
bundle that carried the account's identity would be a leak.

## 4. Root causes

1. (Most likely cause of the scan refusal; the redacted report will confirm.) The scan treated host-derived
   launchd service names as if they were secrets: `long-run` on a 48-character identifier in a name that
   macOS itself registers. Fixed at the producer: names the scan would refuse are recorded as `#` plus the
   SHA-256 of the name, which identifies them without the opaque run; the PROC-06 helper still receives
   the real names, so the sweep is unchanged.
2. (Latent) `session-refused-<code>` strings of 40 or more characters. Fixed in the scan: exactly the
   prefix `session-refused-` followed by lowercase words joined by hyphens, at most 64 characters, is
   the runner's own vocabulary and not an opaque token. Digits, capitals, underscores, any other
   hyphenated text and anything longer stay refused.
3. (Diagnosability) `scan_for_secrets` refused with no detail, so neither the file nor the rule could be
   learned from the output. Fixed by the redacted report.
4. (Diagnosability) A failed real run printed only the exception and the session count, and there was
   no way to run the backend's pre-session check without spending a session. Fixed by the error
   evidence and `--self-check`.

The refusal of the first session (`self-check-failed`) is a separate fact and its cause is unknown (section 6).

## 5. What changed

- `agent_braid/harness_qualification_probes.py`: `ProbeError.detail`; `scan_for_secrets(..., origins=)`
  with named shape rules, `_locate`; `bundle_safe_name` applied to `machNames` and `changedOutside`;
  the composed `session-refused-<code>` stop reasons allowed; `credential_inventory` / `credential_origins`; the runner labels the
  literals `caller`, `marker` and `credential#N`.
- `scripts/har_t009_attempt.py`: the error verdict prints `scan` and `preSessionEvidence`; `--self-check`;
  the credential literals are read once before anything native runs and passed to the runner.
- Tests: 16 in `AttemptOneReproductionTests` and `RedactedScanReportTests`, 15 in `ErrorDiagnosisTests`
  and `SelfCheckTests`; quickstart step 10b and "If step 11 fails"; the T009 note in `tasks.md`.
- Not touched: `harness_containment_macos.py`, `harness_transport_claude.py`, `harness_quota.py`,
  `cli.py`, `ownership.py`, `docs/STATUS.md`, `ROADMAP.md`, `SPEC_MILESTONE_INDEX.md`.

Redacted report, produced by the fixed module on a bundle that carries the 48-character name (a sample
of the shape; with the producer fix the scan no longer refuses it):

```json
{"findings": [{"file": "results.jsonl", "line": 2, "path": "$.machNames[1]", "rule": "long-run", "length": 48}], "total": 1}
```

The hashes move. The catalog hash binds the bytes of the probes module (`runnerSha256`), not only the
probe definitions: the catalog document is otherwise identical (checked), but any edit to the module changes
`CATALOG_SHA256` and therefore the environment hash. Catalog hash before
`3e316cee01683ca1fbc96e7fd365e6dbdc51c7d4d711e41c0d7760b1d10b42b7`, after
`f63b779c4517916eccf3a977586cbe66c06afef948085723d715efd4f9d9b478`. The earlier dry run no longer matches, the installed code copy (step 5) must be
replaced by one from the new commit, and the re-check of the touched lines
(`recheck-t009-diagnose.md`) is the one the T009 note requires.

## 6. What stays unknown until the founder runs `--self-check`

- Why the pre-session check refused: the compile check's positive case (`claude --version` under the
  `launch` profile, exit not 0) or one F4 probe, and which. The self-check prints the compile check,
  all five F4 verdicts (also after a refusal) and the nested refusals, with no session spent.
- Whether the other helper probes (contained and contained-launch rows) behaved as expected: their rows
  were lost with the bundle. The next bundle will show them.
- Whether the launchd names above are what `launchctl print` lists for the dedicated account.

Decisions that belong to the founder and the orchestrator, not made here: whether the refused session
still counts against the budget of three and whether `.sessions.json` (which now carries
`quotaStop: session-refused-self-check-failed`, so a re-run with the same `--out-dir` refuses every session)
may be archived and restarted in a new `--out-dir`.

## 7. Test evidence

Focused modules, run with the pinned Python 3.12.13 without bytecode: see `recheck-t009-diagnose.md`
for the counts. The probes and driver modules were also run against the doubles of the existing tests
unchanged: all pre-existing tests still pass.
