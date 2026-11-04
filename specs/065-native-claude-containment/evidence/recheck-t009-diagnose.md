# SPEC-065: security re-check of the T009 attempt-1 diagnosis edits

**This re-check is not a qualification.** It issues no record, qualifies no effect, authorizes no native
session, probe or account setup. `executionAuthorization` stays `false`. A GO below means engineering
readiness of the touched lines for the next T009 step (the founder's `--self-check`); it does not replace
the founder's conditional go (`founder-decisions-20261103.json`) and says nothing about whether the sandbox
profile enforces anything (decided only by the T009 observation and the T010 human issuance).

## Record

| Item | Value |
|---|---|
| Date | 2026-11-04 |
| Cause | T009 attempt 1 (`t009-20261104`) ended `ProbeError: secret-in-artifact` after the backend refused the first session; diagnosis in `t009-attempt1-diagnosis.md` |
| Branch | `har/065-t009-diagnose`, base `origin/develop` (`38c0b268`) |
| Scope | `agent_braid/harness_qualification_probes.py`: `ProbeError`, `_SECRET_SHAPES`, `_CODE_RUN`, `_allowed_run`, `_opaque_hits`, `_looks_secret`, `_scan_hits`, `_path_text`, `_leaf_findings`, `_locate`, `scan_for_secrets`, `bundle_safe_name`, `_credential_leaves`, `_is_candidate`, `credential_inventory`, `credential_values`, `write_bundle` (the `origins` input), `QualificationProbeRunner.run` (the labels) and the two row fields `machNames` and `changedOutside`. `scripts/har_t009_attempt.py`: `AttemptFailed`, `refusal_evidence`, `_scan_report`, `_workdirs`, `run_attempt` (inventory, runner input, error evidence), `self_check`, `run_self_check`, the `--self-check` option and the error verdict in `main` |
| Not touched | `harness_containment_macos.py` (the backend, called through two existing methods), `harness_transport_claude.py`, `harness_quota.py`, `cli.py`, `ownership.py`, `docs/STATUS.md`, `ROADMAP.md`, `SPEC_MILESTONE_INDEX.md`, the probe catalog (every probe definition and helper source is byte-identical; only the module hash inside the catalog document moves) |
| Reviewer | The implementing agent, as a self re-check. It is not independent: the three pre-PR reviews were done and their findings dispositioned in the PR description; the orchestrator's re-check is still owed before the founder runs anything |
| Verdict | **GO** for both files, with the residuals below. Required fixes: none |
| Hashes | The catalog document is identical apart from `runnerSha256`, but that field is the SHA-256 of the probes module, so `CATALOG_SHA256` moves: before `3e316cee01683ca1fbc96e7fd365e6dbdc51c7d4d711e41c0d7760b1d10b42b7`, after `f63b779c4517916eccf3a977586cbe66c06afef948085723d715efd4f9d9b478`; the environment hash moves with it. The earlier dry run, the installed code copy and the orchestrator's pins must be redone from the new commit. The earlier assumption that only a content change moves the hash does not hold |
| Tests run | Python 3.12.13 (uv standalone), `-B`: `test_harness_qualification_probes`, `test_har_t009_attempt`, `test_harness_containment_macos`, `test_harness_transport_claude`, `test_harness_quota`, `test_harness_manifest`: TESTS_RUN. Nothing native ran |

## Change 1: the redacted scan report

Verdict: **GO**.

- **Edit.** `scan_for_secrets` still refuses with the reason `secret-in-artifact`, and `str(error)` is still only
  that code. The error now carries `detail`: up to 20 findings with `file` (one of the five bundle file
  names), `line`, `path` (a JSON path), `rule` (`listed-literal`, `long-run` or the shape name), `length` and,
  for a listed literal, `origin` (`caller`, `marker`, `credential#N`), and `total`.
- **What can leak, and why it does not.** The value never enters the detail: only lengths, line numbers, rule
  names and labels are built from a match; no slice of the text is copied. The JSON path prints a key only when
  it is a plain field name (`[A-Za-z][A-Za-z0-9_]{0,31}`) that the scan would not itself refuse; any other key,
  including a key that is a secret or holds one, is printed as `<key>`. A test checks every 3- and 4-character
  window of the secret against the rendered detail and `repr` of the error, for a value, a key, a nested key
  and a path with spaces. The driver adds `source` for a credential finding: the file name and the field-name
  path of the account's own config that holds it (`.claude.json`, `$.oauthAccount.billingType`), built the
  same way, so a project path used as a key is `<key>`.
- **Disclosure that remains, on purpose.** The match length of a listed literal (the length of a token that
  the operator already holds), the line and path (which row of the bundle), and the field name of a config key
  (schema, not a value). The output is for the operator and the orchestrator, like the dry-run report; it is
  not part of the bundle.
- **Fail closed.** The decision to refuse is unchanged and is made on the whole text first; locating is only
  decoration. A finding the line pass cannot place (a literal spanning lines) is reported for the file alone,
  and a refusal always has at least one finding (tested). The second scan of `summary.json` reports its own file.

## Change 2: host-derived names are recorded safely

Verdict: **GO**.

- **Edit.** `bundle_safe_name(text)` returns the text, or `#` plus its SHA-256 when `_looks_secret` says the
  scan would refuse it. It is applied to the PROC-06 launchd names recorded in `machNames` and to the
  `changedOutside` paths of every row. The helper still receives the real names in the arena document, so the
  sweep (`mach_sweep`) tests exactly what launchd lists. A listed secret literal is still checked against the
  recorded text, so a name containing one stays refused (fail closed).
- **What it fixes.** On the founder's machine three real service names trip the long-run rule (a 48-character
  and a 40-character dotless run); a name the scan refuses used to lose the whole bundle, including all the
  sessions' evidence.
- **Residuals.** (1) A refused-looking name is recorded as a digest: the reader of the bundle must hash a
  candidate to identify it; nothing else about the row changes, and the count of names is unchanged. (2) The
  digest of a short, guessable secret-shaped name could be brute-forced; the names are public system service
  names and the rule only hashes names the scan already finds opaque. (3) `changedOutside` paths are built
  from the dedicated account's layout under the driver's `work-` names (36 characters at most); they were not
  seen to trip the rule and are hardened as the same class.

## Change 3: the runner's composed stop reasons

Verdict: **GO**, residual R1.

- **Edit.** `_allowed_run` also accepts a run that fully matches `session-refused-[a-z]+(-[a-z]+)*` and is at
  most 64 characters: the string `_settle_quota` composes from a fixed backend code. The 64-hex digest allowance
  is unchanged.
- **Why this layer.** The composed string is the runner's own vocabulary; the alternatives were to shorten a
  founder-visible code or to hash it, both of which would make the very reason that explains a refusal
  unreadable in the bundle. The allowance is limited to that exact prefix, lowercase letters and hyphens, so
  base64, hex, mixed-case, digit-bearing, underscore-bearing and unprefixed hyphenated text stays refused
  (tested, including the 64-character cap and a 66-character letters-only tail).
- **R1.** A secret that is the exact string `session-refused-` followed by lowercase words is not caught by the
  long-run rule. No token format of Anthropic, GitHub, AWS or the JWT family looks like it, and every
  credential-like value of the account's files remains a listed literal where it qualifies.

## Change 4: credential inventory

Verdict: **GO**. No change to which values are scanned.

`credential_values` is `credential_inventory` minus the origin; the filter (`len >= 16`, one opaque token,
not a plain lowercase name) is the same function now named `_is_candidate`. E-mail addresses, paths, URLs and
sentences are still not literals (they cannot be told from legitimate text, and a leaked e-mail cannot reach the
closed vocabulary of the bundle); UUIDs, ids and account metadata still are. `credential_origins` and the
inventory give the field-name path only. In the driver the inventory is read once, before anything native
runs, from the files of the account that runs the driver, and passed to the runner as `read_credentials`; the
unreadable-files behavior is the previous one (an unreadable file contributes nothing, the credential scan
unavailability check of the runner is unchanged).

## Change 5: the driver prints the evidence it has

Verdict: **GO**.

- `refusal_evidence` copies from a backend record only `entry`, `refused`, `compileCheck` (each matched
  against `[A-Za-z0-9][A-Za-z0-9-]{0,47}`) and the F4 rows `probe`, `expected`, `observed` (verdicts `allowed`,
  `denied`, `error`). The record also holds the operator and lab account names, uids, home mode, hashes and OS
  build; none is copied (tested with a record carrying them). At most 12 records. A non-list or foreign
  value is dropped.
- `nativeRun` is now always `true` in the error verdict of a real run: the helper probes run natively with or
  without a session (attempt 1 printed `true` because one session was counted; a failure with zero sessions
  would have printed `false`).

## Change 6: `--self-check`

Verdict: **GO**, residuals R2 to R4.

- **What it calls.** After the same pre-flight, the backend built exactly as in the real run (the same factory
  arguments, tested), then `with backend._exclusive("launch"): backend._pre_session("launch", workdir,
  probes=True)`. These are the two calls `MacOSContainment.launch` makes before it spawns anything; a test
  reads the source of `launch` and of `_run_probes` and the signature of `_pre_session`, so a backend change
  that moves them fails a test. Nothing is added to the backend.
- **What does not happen.** No transport, no `launch`, no `_spawn` of a session, no quota module, no usage
  reading, no typed confirmation, no session reserved, no counter, no bundle (every one of these is replaced by
  a double that raises in the tests). `sessionsStarted` and `usageReadings` are `0` in the output.
- **What does run natively, stated in the module docstring, the option help and the runbook.** Under the
  sandbox: the pinned `claude --version` (the compile check's positive case, and again once per F4 probe under
  the `launch-probe` profile; no session, no prompt, no login), the F4 fixtures with the interpreter, and for
  NET-06 one TLS handshake with the allowed endpoint through the local proxy. It is the same set the real run
  performs at its first launch, so the self-check adds no new capability and no new target. It therefore needs
  `--founder-go` and a `ready` pre-flight; either missing refuses before anything is built (tested).
  `claude --version` is the one place where the pinned Claude executable runs in this mode; no F4 probe launches
  Claude itself, and the mode cannot exclude the compile check without changing the check it diagnoses.
- **After a refusal** the F4 probes the check did not reach are run one by one through the backend's own probe
  runner and marked `supplementary`; an exception or an unknown answer is `error`. After `self-check-allowed`
  (a denied probe observed `allowed`, an escape) none is run: they are marked `not-run`, as the backend stops
  at the first mismatch (pre-PR review, tested).
- **Credential paths.** A key that is itself a candidate credential value prints as `<key>` in the `source`
  path (pre-PR review F1, tested with a 32-character alphanumeric key). The nested refusals come from
  the backend's own `run_evidence`.
- **R2.** `_exclusive` and `_pre_session` are underscore-named backend methods used from the driver. The
  drift test above is the guard; the alternative (a public backend method) is an edit to a file this task may
  not touch and would move the environment hash again.
- **R3.** The self-check takes the run-root `flock` and starts the local proxy listener (127.0.0.1, the policy
  port) for its duration, as a launch does; a concurrent real run would refuse with `dedicated-user-busy`.
- **R4.** The stage (`mechanism-or-workspace`, `compile-check`, `f4-probes`) is inferred from the backend's
  record and its fixed reason codes; it is a reading aid, not a backend field.

## What was not checked or is outside this change

- That `launchctl print` lists the three long service names on the founder's machine (not run); the report
  of the next refusal, if any, would show it. With Change 2 such a refusal cannot occur for host names.
- The cause of `self-check-failed`: unknown until `--self-check` runs.
- The session counter policy after a refused first session (founder and orchestrator, NC-10): untouched.
- Independent review: this file is the implementer's. The three pre-PR reviews of the track and the
  orchestrator's re-check remain required before the founder runs the self-check.

## Residuals carried

R1 (composed stop-reason allowance: lowercase words after the `session-refused-` prefix, 64 characters at most; the text comes from a `LabError` reason code chosen in the source, never from host or operator input, and the complete code set is spread over modules this task may not edit, so an exact list would drift; kept), R2 (private backend methods used by the driver), R3 (lock and proxy
held during the self-check), R4 (stage inference), and from the earlier re-checks DRV-04, 07, 08, 09, 11, 13,
15 and MDRV-01 to MDRV-04, unchanged.
