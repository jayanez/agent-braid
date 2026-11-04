# SPEC-065: Tasks

Stable task IDs. Completion requires obtained evidence. A passing unit test is
not containment evidence; only the probe bundle and the human issuance record
are. Dependencies are ordering facts; they do not authorize concurrent agents.
No task is started by the specification change. T001 recorded every founder
decision (NC-1 to NC-11) and the F5 binding in
[evidence/founder-decisions-20261031.json](evidence/founder-decisions-20261031.json);
later tasks remain bound by their other dependencies.

Common verification for code tasks: tests first, then
`.venv-speckit/bin/python -m unittest <module> -v`, then
`.venv-speckit/bin/python -m unittest discover -s tests -p "test_harness*.py" -v`,
then the `quick` profile; `pr` once on the stable candidate (clean clone while the
shared object store fails the portable-root check).

## Decisions

- [x] T001 (REQ-004 / SC-004; REQ-005 / SC-005; REQ-006 / SC-006; REQ-007 / SC-007; REQ-008 / SC-008; REQ-003 / SC-003): Founder decision record. Bind F5 (STRICT)
  into a repository record and decide NC-1 to NC-11, or record any item left open
  with the tasks it keeps blocked. Dependencies: none. Files:
  `specs/065-native-claude-containment/evidence/founder-decisions-<date>.json`;
  `spec.md` (replace each decided `[NEEDS CLARIFICATION]` with the decision and
  a link). Verification: record present, every NC item has a decision or an
  explicit "open" with blocked tasks; `validate_spec_kit` passes. Evidence: the
  record. Negative control: a task citing an undecided NC item stays blocked.
  Obtained: `evidence/founder-decisions-20261031.json` (founder, 2026-10-31;
  F5 bound, NC-1 to NC-11 decided, none left open; authorizes no execution,
  qualification or native session).

- [x] T002 (REQ-004 / SC-004; REQ-009 / SC-009): ADR for native Claude
  laboratory containment, drafted from plan.md "Proposed shared-file changes"
  and accepted by the founder before any native session. States the mechanism
  (NC-2), STRICT policy, human issuance, residual risks, and that ADR 0019's
  deferral of arbitrary commands is not lifted. Dependencies: T001. Files:
  `docs/adr/<next>-native-claude-laboratory-containment.md` (separate PR by the
  owner of shared files). Verification: ADR status Accepted with founder
  approval. Evidence: ADR and its PR.
  Progress: [ADR 0035](../../docs/adr/0035-native-claude-laboratory-containment.md)
  proposed (#893, 5e050fff).
  Obtained: ADR 0035 accepted 2026-11-02 by the founder (answer "Aceptar tal
  cual (Recommended)"; PRs #893 and #941).
  Acceptance authorizes no native session, probe, qualification or execution:
  T009 still needs T008 and a separate founder go; issuance stays NC-9.

## Implementation

- [x] T003 (REQ-001 / SC-001): Native `native-claude-laboratory` manifest
  profile beside the unchanged offline profile. Write offline goldens first
  (every committed offline manifest and test manifest: bytes, digest, view,
  refusal reason) and prove them unchanged. Dependencies: T001 (NC-4, NC-8,
  NC-10 limits; F3 caps). Files: `agent_braid/harness_manifest.py`,
  `tests/test_harness_manifest.py`. Verification: procedure_001. Negative
  controls: unknown native field; any limit above cap; route other than
  `subscription`; host other than `claude`; `executionAuthorization: true`;
  offline manifest carrying native keys; native manifest with offline host.
  Evidence: `evidence/t003.json` (candidate, commands, test counts, goldens hash).
  Obtained: `evidence/t003.json` (#862, 25128665; manifest validation only,
  offline goldens unchanged; nothing native runs). Hash comparisons of the
  native containment and host pins against trusted qualification values are
  carried by T006 (K2). SPEC-048 snapshots frozen at 530a5f39.

- [x] T004 (REQ-003 / SC-003): Quota gate over a timestamped plan-usage reading
  and the F3 caps. Pure function; reads no network; source and per-session
  check per NC-6; cohort state (units used, cohort weekly use) is a
  caller-supplied input owned by SPEC-049 and its absence refuses.
  Dependencies: T001 (NC-6, freshness bound). Files: `agent_braid/harness_quota.py`,
  `tests/test_harness_quota.py`. Verification: procedure_003. Negative controls:
  stale, missing, unparseable, future-dated reading; weekly > 80 %; extra usage
  enabled; per-session check (NC-6) failing; cohort > 15 % weekly; unit count
  > 16; cohort state absent. Evidence: `evidence/t004.json`.
  Obtained: `evidence/t004.json` (#858, cad7824f; pure gate at unit level, no
  quota source read and no session launched; T006 wires it into the transport).

- [x] T005 (REQ-004 / SC-004; REQ-005 / SC-005; REQ-006 / SC-006; REQ-007 / SC-007; REQ-008 / SC-008): macOS containment backend implementing
  `ContainmentBackend`: one policy object from the T001 decisions rendering the
  NC-2 isolation profile (deny-default for files, network and process
  execution), minimal environment with `HOME`, `CLAUDE_CONFIG_DIR`
  and `TMPDIR` locations per NC-5 and NC-7, rlimits and group settlement reusing the
  `harness_lab` patterns, executable allow-list (NC-8), environment-hash
  computation, the F4 pre-session check per NC-11, run evidence carrying the
  qualification hash and check results, and a `launch` entry point for the
  CLI sharing the same policy. Refuses with fixed reasons, never degrades, never
  falls back to `SimulatedContainment`. Dependencies: T001 (NC-1, NC-2, NC-3, NC-4,
  NC-5, NC-7, NC-8, NC-11), T002, T003.
  Files: `agent_braid/harness_containment_macos.py`,
  `tests/test_harness_containment_macos.py`. Verification: procedure_004 (unit
  level; live probes are T007/T009). Negative controls: mechanism absent;
  mechanism binary hash changed; policy render/compile failure; self-check
  returns allowed; OS build or CLI version outside window; `ENV_DENY` variable
  in parent environment; qualification for another backend or environment.
  Evidence: `evidence/t005.json`.
  Obtained: `evidence/t005.json` (#856, 9a52b4a7; unit-level engineering only,
  it qualifies nothing). Landed ahead of T002 and T003: the ADR (T002) must
  still be accepted before any native session, and the backend refuses to run
  without the verified qualification records that only T009/T010 can issue.

- [x] T006 (REQ-002 / SC-002): Native `ClaudeTransport` (`kind = "native"`):
  `version()` and `run()` through the T005 launcher; quota gate (T004) and
  F4 check (NC-11) before launch; no retry and no alternative route;
  `run_claude` stream checks reused. Includes the known changes K1–K4 of
  plan.md, each a separately reviewed edit: K1 live `init` parsing that kills
  the group on a non-subscription `apiKeySource` before any `assistant` or
  `result` event is accepted; K2 refusal unless the transport's backend passes
  the verified-containment check; K3 native-only session wall bound (≤ F3 30
  minutes, value NC-8; `MAX_WALL_SECONDS`, fixtures and Codex unchanged); K4
  native `ENV_ALLOW` per NC-5/NC-7 and absolute pinned `argv[0]` hash-checked
  at every launch. Dependencies: T003, T004, T005. Files:
  `agent_braid/harness_transport_claude.py`, `agent_braid/harness_host_claude.py`
  (wall bound only), `tests/test_harness_transport_claude.py`,
  `tests/test_harness_host_claude.py`. Verification: procedure_002 with a
  fake launcher. Negative controls: no, expired, drifted or Codex qualification;
  unqualified backend; API-key variables present; non-subscription
  `apiKeySource` (group killed at `init`, no `result` accepted); host
  qualification with an unqualified or missing backend; executable hash differs
  from the pin; `PATH` shadowing of `claude`; version drift; quota stop;
  cancellation before launch; second attempt after failure. Evidence: `evidence/t006.json`.
  Obtained: `evidence/t006.json` (#892, 83d2d306) and `evidence/t006-live-output.json`
  (#894, 2e417962; T005 `launch` gains the `on_output` hook, so the transport accepts
  the real backend). Unit level with a fake launcher only: nothing native runs and
  nothing is qualified; launches still refuse without T009/T010 records.

## Qualification

- [x] T007 (REQ-009 / SC-009; REQ-010 / SC-010; REQ-005 / SC-005; REQ-006 / SC-006; REQ-007 / SC-007; REQ-008 / SC-008): Versioned probe catalog and runner
  per [contracts/containment-qualification.md](contracts/containment-qualification.md).
  Adversarial escapes run from inside the contained child, each with an
  uncontained positive control in a disposable directory with dummy secrets:
  filesystem FS-01 to FS-05 (outside write, symlink and hard-link targets, `..`,
  case and Unicode aliases, outside read, outside delete/rename); network NET-01
  to NET-06 (non-allowed host, literal IPv4/IPv6, UDP and DNS exfiltration,
  loopback port and Unix socket, proxy bypass, allowed-endpoint control);
  credential CRED-01 to CRED-05 (operator `~/.claude`, other Keychain items,
  `~/.ssh`/Git/cloud credentials, inherited secret variables, `apiKeySource`);
  process PROC-01 to PROC-08 (non-allowed exec, fork limit, CPU/memory/
  open-file/file-size/file-count limits, group escape, launch agent,
  LaunchServices/AppleEvents/XPC/`launchctl` spawn, signal/ptrace of same-user
  processes, settlement at timeout and cancel); FS-06/FS-07 (inherited
  descriptors, FIFOs, devices, Spotlight); NET-07/NET-08 (raw socket, ICMP,
  daemon XPC/Unix sockets); CRED-06/CRED-07 (SSH/GPG agents, other processes'
  environments, pasteboard, browser profiles); HOST-01 functional session. The runner writes
  the evidence bundle and per-effect status; it has no code path that writes a
  qualification record. Dependencies: T005, T006 (HOST-01, CRED-05 and the
  CLI variant of NET-05 run through the native transport). Files:
  `agent_braid/harness_qualification_probes.py`,
  `tests/test_harness_qualification_probes.py`. Verification: procedure_009
  (catalog shape, pass rule, no record writing, secret scan), live probes
  skipped in unit runs. Negative controls: probe with failing positive control →
  `inconclusive`; one `allowed` escape → effect `not-enforced`; missing probe →
  profile not qualified. Evidence: `evidence/t007.json`, catalog hash.
  Obtained: `evidence/t007.json` (#896, e0559555; 32-probe catalog with its SHA-256,
  bundle writer with secret scan and no record-writing path; unit level only,
  live positive controls opt-in and never run in CI; nothing native ran).
  Open for T008: PROC-04/PROC-08 judge a swept group-leaver as an escape;
  FS-06/FS-07 controls may not discriminate; NET-05-CLI stays inconclusive
  without a proxy egress tap; PROC-08 cancel half needs a cancel driver.

- [x] T008 (REQ-010 / SC-010): Independent security review of the probe catalog
  and backend policy before the first live attempt: missing escape classes,
  weak positive controls, policy rules broader than the decisions. Findings are
  fixed in T005/T007 or recorded as residual risk. Dependencies: T005, T007.
  Files: `specs/065-native-claude-containment/evidence/probe-catalog-review.md`.
  Verification: review record with findings and dispositions. Evidence: the
  record. Note: a review is not a qualification.
  Obtained: `evidence/probe-catalog-review.md` (#952; 34 findings, 0 critical,
  4 high; static review, nothing native ran) plus the founder dispositions of
  RV-17, RV-19 and RV-21 in `evidence/founder-decisions-20261102.json`
  (2026-11-02; `executionAuthorization` false). The fix-in-T005 and fix-in-T007
  findings were fixed in T005/T007 follow-ups (#957, #959, #966), reviewed again in
  `evidence/probe-catalog-delta-review.md` (#975) and fixed in #979
  (`evidence/pre-t009-fixes.json`; founder records `founder-decisions-20261102b.json`,
  the launch-probe deviation, and `founder-decisions-20261102c.json`, DRV-06 and
  DRV-10). The mini delta re-check `evidence/probe-catalog-delta-recheck.md` (#985) gave
  GO for engineering readiness only, with residuals MDRV-01 to MDRV-04. No record is
  issued and `executionAuthorization` stays false.

- [ ] T009 (REQ-005 / SC-005; REQ-006 / SC-006; REQ-007 / SC-007; REQ-008 / SC-008; REQ-010 / SC-010; REQ-003 / SC-003): Qualification attempt on the
  founder's machine: run the full catalog in both modes for the decided
  configuration, including HOST-01 within the NC-10 budget with pre/post quota
  readings. Keep the bundle whatever the outcome. Dependencies: T002 accepted,
  T006, T007, T008; founder go for the live session(s). Preconditions from the
  delta re-check (engineering readiness, not an authorization): any edit to the
  backend, probes, transport or quota module moves the environment and catalog
  hash and needs a new re-check of the touched lines before the attempt; carry
  the residuals DRV-04, 07, 08, 09, 11, 13, 15 and MDRV-01 to MDRV-04 into the
  bundle summary and the T010 decision. The HAR consolidation review touched
  `_egress_verdict`, `classify_session`, the runner `endpoints` option and
  `make_qualification_runner` in `harness_qualification_probes.py` (NET-05-CLI
  judged against the policy endpoints) and `_InitWatch._line` in
  `harness_transport_claude.py` (non-string `apiKeySource`); both need the
  re-check of the touched lines. Files:
  `specs/065-native-claude-containment/evidence/qualification/<attempt>/`.
  Verification: procedure_005 to procedure_008 and procedure_010.
  Evidence: the bundle and its SHA-256. A not-qualified or inconclusive result
  completes this task as a valid negative outcome (H1 not supported).
  Status 2026-11-03: the founder gave a conditional go
  (`evidence/founder-decisions-20261103.json`: the orchestrator prepares evidence and
  a checklist, the founder runs the sudo setup, the orchestrator verifies it, then the
  founder launches the attempt in the dedicated account's own login session) and chose
  the sysadminctl commands for the standard account. The re-check of the #988 lines is
  `evidence/recheck-988-touched-lines.md` (GO, no fixes). The operator-run driver is
  `scripts/har_t009_attempt.py` (`tests/test_har_t009_attempt.py`; `--dry-run` is
  pre-flight only) and the runbook is quickstart.md "Operator setup for T009".
  Nothing native has run; `executionAuthorization` stays false and issuance stays
  T010. Blockers resolved by the founder on 2026-11-03
  (`evidence/founder-decisions-20261103b.json`): NC-3 amended to the whole macOS 27.x
  series, RV-16 changed (the console owner is no longer refused; the founder's own
  account, privileged gids and uids below 500 are, through the driver's required
  `--operator-account`), NC-6 readings typed by the operator from claude.ai Usage or the
  phone (self-attested), and in-memory attempt records accepted (not issuance). The
  backend and driver edits are re-checked in `evidence/recheck-t009-unblock.md`; a
  re-check by the orchestrator is required before the founder starts the runbook, and the
  dry run on the founder's machine is the next evidence. This task
  stays unchecked.
  Attempt 1, 2026-11-03 (diagnosis: `evidence/t009-attempt1-diagnosis.md`; re-check of the fix:
  `evidence/recheck-t009-diagnose.md`): the dry run was `ready`; the real run (attempt
  `t009-20261104`) ended `ProbeError: secret-in-artifact` with one session counted
  (`.sessions.json`: `sessionsStarted: 1`, `quotaStop: session-refused-self-check-failed`). The
  backend's pre-session check refused the first `claude --version` launch before anything was
  spawned (no `claude` session, no prompt, no usage consumed; the typed pre reading was not used),
  and the bundle was then blocked by the secret scan, so no bundle was written and no post reading
  was asked. The scan refusal is reproduced offline with the names declared in the system launchd plists (not yet observed in a run; `launchctl print` was not run): PROC-06 records the launchd service names, and
  macOS 27 has system service names with a 48-character identifier
  (`com.apple.proactive.SuggestionRequest.ps_unstructured_reminder_interaction_suggestions`) that the
  long-run rule refuses; the runner's composed `session-refused-<reason>` codes of 24 or more characters
  are a second such channel (latent). Fixed in `harness_qualification_probes.py`: such names are
  recorded as `#` plus their SHA-256 (the helper still sweeps the real name), the runner's composed
  `session-refused-<code>` stop reasons are not opaque runs, and a refusal now carries a redacted report (file, line, JSON path, rule, match
  length; never a value). `scripts/har_t009_attempt.py` prints that report and the backend's refusal
  evidence in its error verdict and has `--self-check` (the backend's pre-session check alone, no
  session). Why the self-check refused is not known: it is what `--self-check` shows (runbook step 10b).
  The probes module edit moves the catalog and environment hashes (the catalog binds the module's
  own bytes), so the dry run, the installed code copy (step 5) and the re-check by the orchestrator
  are repeated. The counter of the output directory stops further sessions: its reset is a
  founder decision (quickstart "If step 11 fails"). Nothing is qualified; `executionAuthorization` stays false.
  Self-check 1, 2026-11-04 (`evidence/t009-selfcheck1-20261104.md`; founder record
  `evidence/founder-decisions-20261104.json`; re-check `evidence/recheck-t009-sandbox-allowlist.md`): the
  founder's `--self-check` refused at the compile check (`self-check-failed`): the allowed `claude --version`
  exited non-zero under the profile, which granted no `sysctl-read` (kernel log: the Bun binary was denied its
  start-up `hw.*` and `kern.*` reads). The founder chose "A. Lista cerrada": the `launch` and `launch-probe`
  profiles now allow a closed list of read-only system information (named `sysctl-read`s plus the
  `hw.optional.` prefix, three literal `LC_CTYPE` files, metadata of `/etc` and `/var`); `kern.bootargs`,
  `mach-lookup`, `/dev/dtracehelper` and everything else stay denied. The fixture interpreter runs with
  `-B`. `process-accounting-failed` (fixture entry) is handled for exited-unreaped processes, and the
  self-check now prints exit codes (`compileExit`, `exitCode`, `probeRuns`) and the errno of an accounting
  failure, integers only. The backend edit moves the environment hash (the catalog hash does not); the dry
  run, the installed copy and the orchestrator's re-check are repeated before the self-check is re-run. The
  NC-10 counter decision for the refused session 1 is a new attempt with 3 sessions. This task stays
  unchecked.

- [ ] T010 (REQ-009 / SC-009): Human issuance. The issuer fixed by NC-9 reviews
  the T009 bundle; if every effect is `enforced` and HOST-01 completed, writes
  the containment and Claude host records with `evidenceSha256` = bundle hash,
  `expiresAt` per NC-9, and a decision record carrying both canonical records
  and their trusted hashes; otherwise writes a not-qualified decision naming the
  failing or inconclusive effects. Then run `verify_qualification` and
  `verify_host_qualification` against the trusted hashes and the T006 transport
  `_check_transport`/`_check_backend` against the native manifest. If CRED-05
  observed a subscription `apiKeySource` outside `SUBSCRIPTION_KEY_SOURCES`, the
  constant changes only in a separate reviewed edit citing the bundle, before
  issuance; it is never widened without that record. The issuer also knows that the
  environment hash omits `harness_manifest.py`, `harness_context.py`,
  `harness_observation.py` and `system_one.py` (MDRV-04). Dependencies:
  T009. Files: `specs/065-native-claude-containment/evidence/qualification/issuance-<date>.json`;
  only for K5: `agent_braid/harness_host_claude.py`, `tests/test_harness_host_claude.py`.
  Verification: procedure_009. Negative controls: runner-produced record,
  edited record, wrong environment hash, expired record all refuse. Evidence:
  issuance record and verification output.

## Hand-off and closure

- [ ] T011 (REQ-011 / SC-011): Hand-off packet for SPEC-048/T008 (Claude
  profile only): issued or not-qualified records, hashes, environment, limits,
  residual risks, expiry and re-qualification triggers, and the T008 acceptance
  items still open (`agent_braid/harness_hosts.py`, profile decision record,
  route/quota observations). SPEC-049/T004 is unblocked only after T008 records
  its own decision. Dependencies: T010. Files:
  `specs/065-native-claude-containment/evidence/handoff-spec048-t008.md`.
  Verification: procedure_011 (no SPEC-048/049 bytes changed by this feature).
  Evidence: the packet.

- [ ] T012 (all REQ / SC): Stable-candidate validation and review: `pr` profile,
  code review of T003–T007, assurance obtained-evidence update, authority
  snapshot, freeze, and human review of the feature. Dependencies: T003–T011.
  Files: `assurance.json`, `evidence/t012.json`. Verification: `quick`, `pr`,
  `validate_spec_kit`. Evidence: validation output bound to the candidate commit.

## Unblocking map

| Task | Needs |
|---|---|
| T002, T003, T004 | T001 |
| T005 | T001, T002, T003 |
| T006 | T003, T004, T005 |
| T007 | T005, T006 |
| T008 | T005, T007 |
| T009 | T002 accepted, T006, T007, T008, founder go |
| T010 | T009 |
| T011 | T010 |
| T012 | T003–T011 |
| SPEC-048/T008 (Claude profile) | T011 plus its own acceptance items |
| SPEC-049/T004 | SPEC-048/T008 decision plus its own source/route/quota approval |

Scientific limit: T009/T010 describe one machine, OS build, CLI version and
catalog version until `expiresAt`. They are not a general isolation proof and
say nothing about Codex.
