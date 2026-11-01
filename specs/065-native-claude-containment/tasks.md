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

- [ ] T002 (REQ-004 / SC-004; REQ-009 / SC-009): ADR for native Claude
  laboratory containment, drafted from plan.md "Proposed shared-file changes"
  and accepted by the founder before any native session. States the mechanism
  (NC-2), STRICT policy, human issuance, residual risks, and that ADR 0019's
  deferral of arbitrary commands is not lifted. Dependencies: T001. Files:
  `docs/adr/<next>-native-claude-laboratory-containment.md` (separate PR by the
  owner of shared files). Verification: ADR status Accepted with founder
  approval. Evidence: ADR and its PR.
  Progress: [ADR 0035](../../docs/adr/0035-native-claude-laboratory-containment.md)
  proposed (#893, 5e050fff); stays open until the founder accepts it.

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

- [ ] T008 (REQ-010 / SC-010): Independent security review of the probe catalog
  and backend policy before the first live attempt: missing escape classes,
  weak positive controls, policy rules broader than the decisions. Findings are
  fixed in T005/T007 or recorded as residual risk. Dependencies: T005, T007.
  Files: `specs/065-native-claude-containment/evidence/probe-catalog-review.md`.
  Verification: review record with findings and dispositions. Evidence: the
  record. Note: a review is not a qualification.

- [ ] T009 (REQ-005 / SC-005; REQ-006 / SC-006; REQ-007 / SC-007; REQ-008 / SC-008; REQ-010 / SC-010; REQ-003 / SC-003): Qualification attempt on the
  founder's machine: run the full catalog in both modes for the decided
  configuration, including HOST-01 within the NC-10 budget with pre/post quota
  readings. Keep the bundle whatever the outcome. Dependencies: T002 accepted,
  T006, T007, T008; founder go for the live session(s). Files:
  `specs/065-native-claude-containment/evidence/qualification/<attempt>/`.
  Verification: procedure_005 to procedure_008 and procedure_010.
  Evidence: the bundle and its SHA-256. A not-qualified or inconclusive result
  completes this task as a valid negative outcome (H1 not supported).

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
  issuance; it is never widened without that record. Dependencies:
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
