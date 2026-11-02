# SPEC-066: Tasks

Stable task IDs. Completion requires obtained evidence; completing a task does not
imply human review, calibration, promotion or founder acceptance. Parallelizable does
not authorize concurrent agents. No task is started by the specification change.

SPEC-066 is delivered in stages inside one milestone, `S1.5 — System One shadow
activation`. **S1.5a** (T010–T032) is specified to implementation level. **S1.5b–e**
(T101–T403) are outline tasks, **blocked** until T032 records that S1.5a is complete
and the owner reviews the stage's own plan; they exist so the absorbed deferred
issues have a home and nothing is silently dropped. Tests come first in every
implementation task.

**Implementation authorization (2026-11-01).** The owner approved a plan whose first
product step is S1.5a ([founder decisions](../../docs/development/FOUNDER_DECISIONS_20261101.md)),
so S1.5a implementation landed with this specification. The owner then reviewed and
accepted the specification on 2026-11-01 (T001, evidence
[owner-review-20261101.md](owner-review-20261101.md)) and set the native-only
direction: no external service, third-party decision model or pretrained encoder, ever;
Laya and Jev are design references only.
Checked S1.5a tasks below cite `tests/test_system_one_shadow.py` (one module instead
of the separate test files named in each task); unchecked ones remain open, partly
implemented where noted.

Existing deferred issues absorbed by this milestone, with the SPEC-066 task that
carries each one forward, are listed in [issue-drafts.md](issue-drafts.md) and
[tracking-drafts.json](tracking-drafts.json). Moving them is a tracking action
(T003, T004), not a closure; their acceptance criteria stay those of the original
specifications unless a SPEC-066 requirement amends them.

## Governance and tracking

- [x] T001 (all REQ): Owner review of the specification, plan, episode contract and
  open decisions OD-1 to OD-8, including the specification notes recorded in
  `research.md`. Dependencies: T005. Files: `spec.md`, `plan.md`, `contracts/`.
  Evidence: review record in this directory that also records the decisions taken
  on OD-1 to OD-8 and the SC-006 session definition.
  Evidence (2026-11-01): `owner-review-20261101.md`.
- [x] T002: Add the S1.5 track to ROADMAP, STATUS, the milestone index,
  `docs/system-one/README.md` and `RESUMPTION`, the GitHub tracking source
  (`specs` entry, milestone, `project_review_pending`) and `GITHUB_TRACKING.md`.
  Dependencies: none. Files: `ROADMAP.md`, `docs/STATUS.md`,
  `docs/development/SPEC_MILESTONE_INDEX.md`, `docs/system-one/README.md`,
  `docs/development/github-tracking.json`, `docs/development/GITHUB_TRACKING.md`.
  Verification: `python3 scripts/sync_github_tracking.py source`. Evidence: merged
  change and source output.
  Evidence (2026-11-01): ROADMAP, milestone index, `docs/system-one/README.md` and
  `RESUMPTION` merged in #860; milestone #26 created on GitHub and registered,
  SPEC-066 added to `project_review_pending`, STATUS and `GITHUB_TRACKING.md`
  updated by the tracking-sync change; `source` reports 13 review-pending records.
- [x] T003: Support a task-level milestone override in the tracking source so the
  absorbed SPEC-029, SPEC-031 and SPEC-033 tasks can move to S1.5 while their
  parent specs stay in Deferred. Tests first. Dependencies: T002. Files:
  `scripts/sync_github_tracking.py`, `docs/development/github-tracking.json`,
  `docs/development/GITHUB_TRACKING.md`, `tests/test_github_tracking.py`.
  Verification: `python3 -m unittest tests.test_github_tracking -v` and
  `python3 scripts/sync_github_tracking.py source`. Evidence: merged change.
  Evidence (2026-11-01): `task_milestone_overrides` with validation and scoped-audit
  support, the 15 R6 moves to S1.5 and 45 closed System One tasks pinned to their
  historical S1.0–S1.4 milestones (owner default, plan approval in
  `owner-review-20261101.md`); `TaskMilestoneOverrideTests` in
  `tests/test_github_tracking.py`.
- [x] T004: After merge to `develop`, publish S1.5 tracking: `audit` scoped with
  `--new-record-key` for exactly the missing SPEC-066 records, review, `apply
  --confirm-repository jayanez/agent-braid --plan-sha256 <digest>`, move the 15
  absorbed issues from Deferred, record the milestone number, re-audit to zero
  operations, set the parent to Review pending in Project 6, and update the Deferred
  milestone description and the reopen condition. Dependencies: T002, T003 merged.
  Evidence: audit and apply outputs, milestone number in `github-tracking.json`.
  Evidence (2026-11-02): milestone #26 registered (#897); scoped apply created the
  parent #900 and 39 task issues with sub-issue links and closed the completed ones;
  after #940 the 15 absorbed issues were moved to #26 with readback, the #26 and #24
  descriptions were set to the source text and read back, and the scoped #26
  re-audit planned no operation; #900 is in Review pending in Project 6. The scoped
  #24 audit still stops on SPEC-041/T002 (closed in M4.5), outside S1.5.
- [ ] T005: Freeze the specification candidate with
  `python3 -m scripts.validate_spec_kit freeze specs/066-system-one-shadow`.
  Dependencies: T002. Evidence: historical snapshot in `assurance.json`.

## S1.5a — Shadow mode

- [x] T010 (REQ-003 / SC-002): Reason table and episode builder: pure functions that
  turn a System 2 report plus the operation name and analysis kind into an
  episode object, with the exact sentence-to-code table, the 64-pair cap, `effectKinds` as `null` (the report carries no
  kinds) and the `unmapped-reason` skip. Include the drift test that scans the analyzer's reason
  sentences and fails if one is missing from the table. Tests first. Files:
  `agent_braid/system_one_shadow.py`, `tests/test_system_one_shadow.py`,
  `tests/fixtures/system_one_shadow/`. Dependencies: T001 (T001 waived for implementation by the 2026-11-01 owner plan approval; required before T032). Verification:
  procedure_002.
- [x] T011 (REQ-003 / SC-002): Episode validator and privacy test: closed
  vocabularies, key sets, bounds, canonical bytes, duplicate members, and a seeded
  test with hostile instance IDs, resource names, paths and prompts proving none of
  them appears in the serialized episode; negative controls inject one extra
  string, an unknown reason code and a mislabelled field. Files:
  `agent_braid/system_one_shadow.py`, `tests/test_system_one_shadow.py`.
  Dependencies: T010. Verification: procedure_002.
- [x] T012 (REQ-007 / procedure_008): Pinned identity: compiled backend ID and
  manifest digest, comparison with the installed identity, `identity-mismatch`
  refusal, and the constant `abstained` / `calibration-absent` answer of the
  reference backend. A test fails when the installed manifest digest changes
  without the compiled constant. Files: `agent_braid/system_one_shadow.py`,
  `tests/test_system_one_shadow.py`. Dependencies: T010. Verification:
  procedure_008.
- [x] T013 (REQ-004 / SC-003): `EpisodeStore`: telemetry-equivalent path safety,
  private files, 4 MiB day cap, 30-date retention on access, non-blocking lock,
  unknown-file refusal, in-memory refusal counters, and a parity test against the
  telemetry path checker. Negative controls: symlink at each level, repository
  ancestor, group-readable file, extra hard link, foreign owner, oversize, busy
  lock, unknown file, full disk. Files: `agent_braid/system_one_shadow.py`,
  `tests/test_system_one_shadow_store.py`. Dependencies: T011. Verification:
  procedure_003.
  Evidence (2026-11-01): negative-control matrix and telemetry path-checker parity in
  `tests/test_system_one_shadow_store.py`; parity found no gap. Own-file unlink logic
  in purge is factored into `_unlink_own`.
- [x] T014 (REQ-002 / SC-001, SC-003): Observer, budget and wiring:
  `ToolingConfig.system_one`, `ShadowObserver` with the 50 ms stage checks and
  exception containment, lazy call from `ToolingService.invoke` after the
  envelope, and the byte-parity test between `off` and `shadow` for every tool with
  fixed UUID and clock. Negative controls: an observer that raises, a store that
  refuses, an over-budget clock, an input that mutates if the observer writes to
  it. Files: `agent_braid/system_one_shadow.py`, `agent_braid/tooling_mcp.py`,
  `tests/test_system_one_shadow_parity.py`. Dependencies: T012, T013 (T001 waived for implementation by the 2026-11-01 owner plan approval; required before T032). Verification:
  procedure_001, procedure_003.
- [x] T015 (REQ-001 / SC-005): Consent: registry `systemOne` member (decode,
  `plan_setup`, digest only when `shadow`), `plugin setup --system-one`, router
  pass-through to `ToolingConfig`, reconnect-required behaviour, and the digest and
  bytes equality test for absent and `off`. Files:
  `agent_braid/plugin_registry.py`, `agent_braid/plugin_cli.py`,
  `agent_braid/plugin_mcp.py`, `tests/test_system_one_shadow_consent.py`,
  `tests/test_plugin_registry.py`. Dependencies: T014. Verification: procedure_005.
- [x] T016 (REQ-008 / procedure_009): `plugin-status` `systemOne` block with
  configured and active mode, store state and retention; no directory creation, no
  episode bodies; existing status tests updated. Files:
  `agent_braid/plugin_mcp.py`, `tests/test_system_one_shadow_consent.py`,
  `tests/test_plugin_mcp.py`. Dependencies: T015. Verification: procedure_009.
- [x] T017 (REQ-005 / SC-004): `system-one report` (text and
  `agent-braid-s1-report/v0.1` JSON) and `purge` with confirmation or `--yes`, over
  the strict validator, with invalid lines counted and no episode body printed.
  Files: `agent_braid/system_one_shadow.py`, `agent_braid/system_one_cli.py`,
  `agent_braid/cli.py`, `tests/test_system_one_shadow_store.py`,
  `tests/test_system_one_cli.py`. Dependencies: T013 (T001 waived for implementation by the 2026-11-01 owner plan approval; required before T032). Verification: procedure_004.
- [x] T018 (REQ-006 / procedure_007): `--telemetry {off,local}` on every
  `system-one` subcommand, the `observe` wrapper in `cli.py`, the `system-one` CLI
  operation in `OPERATIONS`, LIMITS and `docs/tooling/TELEMETRY.md` text, and a test
  that no metric other than the new operation cell appears. Files:
  `agent_braid/cli.py`, `agent_braid/tooling_telemetry.py`,
  `docs/tooling/TELEMETRY.md`, `tests/test_tooling_telemetry.py`,
  `tests/test_system_one_cli.py`. Dependencies: T017. Verification: procedure_007.
  Evidence (2026-11-01): every subcommand accepts `--telemetry`; `docs/tooling/TELEMETRY.md`
  documents the `system-one` operation; the no-other-metric test is in
  `tests/test_system_one_cli.py`.
- [x] T019 (REQ-002, REQ-003 / SC-001): Boundary and validation-profile
  checks: `off` never imports the shadow module (subprocess `sys.modules` check),
  the shadow module imports no network module and no model library, no new
  `executionAuthorization: true`, and the planner routes every touched path to the
  expected rule; update the `system-one-core` boundary text. Files:
  `scripts/validate_change.py`, `tests/test_validation_profiles.py`,
  `tests/test_system_one_shadow_boundaries.py`,
  `docs/development/VALIDATION_PROFILES.md`. Dependencies: T014. Verification:
  procedure_001, `python3 scripts/validate_change.py --base develop --profile quick`.
  Evidence (2026-11-01): `tests/test_system_one_shadow_boundaries.py` (off-mode import
  probe over `cli`, `plugin_mcp` and `tooling_mcp`, no network or model import, no
  `executionAuthorization: true`, empty dependencies) and the routing test in
  `tests/test_validation_profiles.py`; `plugin_mcp` now imports the shadow module only
  in `plugin-status`, which still loads it in `off` mode to report the store location.
- [x] T020 (all REQ): User documentation: `docs/tooling/SYSTEM_ONE_SHADOW.md`
  (what is recorded, what is never recorded, how to enable, report, purge, non-claims
  and limits including the filesystem-stall limit), plus updates to
  `docs/tooling/PLUGIN_PRIVACY.md` and `docs/tooling/INSTALL.md`. Dependencies: T017,
  T018. Evidence: merged documents and a docs link check.
  Evidence (2026-11-01): `docs/tooling/SYSTEM_ONE_SHADOW.md` and cross-references in
  `PLUGIN_PRIVACY.md` and `INSTALL.md`. README and the plugin setup skill still carry
  interim text.
- [ ] T021 (REQ-002 / SC-003): Overhead measurement: median and p95 of the shadow
  step for 2, 12 and 32 operations on the owner machine, with and without a warm
  store, reported as a measurement receipt (not a gate) with the 50 ms budget as
  reference. Dependencies: T014. Evidence:
  `evidence/overhead-<date>.json`.
  Status 2026-11-01: Pending.

- [x] T022 (REQ-003 / SC-002): Episode v0.2 enrichment: extend the builder, validator
  and store to `agent-braid-s1-episode/v0.2` ([contract](contracts/episode-v0.2.md)):
  resource classes (src/test/docs/config/lockfile/generated), path depth, directory
  overlap, per-side effect kinds read from the validated request, and per-repo salted
  resource hashes in a separate field; v0.1 episodes stay readable. Tests first,
  including a seeded privacy test that no raw name or path appears and that the salt
  never appears in an episode, and a purge test that removes the salt. Files:
  `agent_braid/system_one_shadow.py`, `tests/test_system_one_shadow.py`,
  `tests/fixtures/system_one_shadow/`. Dependencies: T011. Verification:
  procedure_010 (see [validation-plan.md](validation-plan.md)).
  Evidence (2026-11-01): merged in #860 (owner decisions R11, R12); v0.2 builder,
  validator, salt and purge tests in `tests/test_system_one_shadow.py`.

## S1.5a — Owner-run check

- [ ] T030 (REQ-002, REQ-003 / SC-006): Enable `shadow` on the owner machine with
  `plugin setup --system-one shadow --apply`, reconnect, work normally with Agent
  Braid, then run `system-one report`. Commit a redacted receipt under the
  `docs/development/REAL_USE_EVIDENCE.md` rules: sources consulted, window, episode
  and pair counts, DP-1 opportunity share, plugin and package version, no
  identifiers. Zero episodes is a valid receipt and is reported as such.
  Dependencies: T014, T015, T017, T020. Evidence:
  `evidence/real-use-shadow-<date>.json`.
  Plan (owner, 2026-11-01): run on the published `0.1.0-alpha.5` plugin, not a local
  build; the owner runs setup with guidance (R14). Day 1 is the date `plugin-status`
  first shows `systemOne.activeMode=shadow`; the report is due 7 days later. Day 1:
  pending.

## S1.5a — Closure

- [ ] T031: Pre-PR reviews (code review, quality, simplification),
  `validate_change --profile pr` on the stable candidate, `/speckit-converge`.
  Converge input (2026-11-01): the code also records an episode for a report-bearing
  `analyze` result (`OPERATIONS` includes `analyze`), while REQ-003 names only
  `analyze-work`; the user guide follows the code. Align the spec or the code.
  Dependencies: T010–T021.
- [ ] T032: Record obtained evidence in `assurance.json`, freeze, and owner review
  of the S1.5a closure, with the decision whether S1.5b starts. Dependencies: T030,
  T031.

## S1.5b — Owned corpus (outline, blocked until T032)

- [ ] T101 (REQ-101): Owner consent record that admits the owner's own work (episodes,
  real runs, and the SPEC-047, SPEC-053 and SPEC-059 real-use sources) as the only
  permissioned corpus, restricted to plugin-registered workspaces (other repositories
  only on the owner's express approval), reusing the SPEC-051 validator; third-party
  sources stay excluded. Carries forward
  SPEC-029 T001 (#285). Dependencies: T032. Evidence: owner record.
- [ ] T102 (REQ-102): Outcome observer that joins DP-1 episodes with a later runtime
  conflict, merge conflict or verify result under a random join key; pairs without an
  outcome stay unlabelled. Dependencies: T101. Files: to be set by the S1.5b plan.
- [ ] T103 (REQ-103): Amended label rubric: observed outcomes primary, owner
  adjudication of a random sample for label noise, missing-label policy frozen before
  any fit. Carries forward SPEC-029 T002 (#286). Dependencies: T101.
- [ ] T104 (REQ-101, REQ-102, REQ-103): Build the owned corpus with group split,
  near-duplicate audit, class and size coverage shown before any fit, and the
  pre-fit feasibility review that seals the untouched test manifest. Carries forward
  SPEC-029 T003 (#287) and T008 (#292). Dependencies: T102, T103.
- [ ] T105 (REQ-103): Owner adjudication of the random label sample. Dependencies:
  T103, T104. Evidence: owner record.
- [ ] T106 (REQ-104): Git-history replay labels: pair real branches or commits of the
  owner's plugin-registered workspaces, obtain the observed conflict with
  `git merge-tree`, reuse the SPEC-012 replay planner, and emit structural episodes
  only (same privacy rules as REQ-003). A repository outside the registered
  workspaces requires the owner's express approval first. Tests first; negative
  controls: an unregistered repository, a pair without an observable outcome (stays
  unlabelled), a merge-tree failure. Dependencies: T101, T022. Files: to be set by the
  S1.5b plan.

## S1.5c — Reference-grade contracts (outline, blocked until T032)

- [ ] T201 (REQ-201): Tri-state abstention, echoed threshold and per-bucket,
  risk-scaled thresholds fitted on a split disjoint from evaluation; metrics and
  split enforcement. Carries forward SPEC-029 T006 (#290). Dependencies: T104.
- [ ] T202 (REQ-202): Two named confidence signals, normalized entropy and maximum
  probability, with stated formulas and no accuracy wording. Dependencies: T201.
- [ ] T203 (REQ-203): Drift demotion to `off` on a different or mixed backend
  identity until a new calibration is pinned, plus domain-drift monitoring. Carries
  forward SPEC-033 T004 (#325). Dependencies: T201.
- [ ] T204 (REQ-204): Batched questions over one state, bounded batches, per-question
  failure isolation, parity with unbatched evaluation. Dependencies: T201.
- [ ] T205 (REQ-205): Option-order invariance by rotation, equivariance tests and
  the adversarial conformance and sensitivity suites. Carries forward SPEC-029 T004
  (#288). Dependencies: T201.
- [ ] T206 (REQ-206): Evaluation gate in CI with minimum accuracy, maximum ECE,
  per-slice metrics and a tolerance against a committed baseline. Dependencies:
  T201, T205.

## S1.5d — Native learned model (outline, blocked until T032)

- [ ] T301 (REQ-301): Native model module inside `agent_braid`, standard library only
  (`dependencies = []`; no numpy, no extra, no download): calibrated logistic
  regression or boosted trees over the episode v0.2 structural features, behind the
  existing `Backend` protocol, with deterministic training, own weights and a pinned
  manifest digest. Tests first. Dependencies: T206.
- [ ] T302 (REQ-301): Calibration and abstention: temperature or isotonic scaling and
  abstention thresholds fitted on a calibration split disjoint from training and
  evaluation; freeze the resource budgets and the paired evaluation plan; implement
  the common baseline runners (rule backend, SPEC-019 linear model) with complete cost
  accounting. Carries forward SPEC-029 T005 (#289) and T007 (#291). Dependencies: T301.
- [ ] T303 (REQ-301): Ablation with and without the per-repo salted resource hashes,
  then the registered comparison at a common risk budget (or a documented
  infeasibility). Keep the hashes only if they measurably improve precision without
  degrading calibration. Record the H-S1 verdict; a null or negative result is valid.
  Carries forward SPEC-029 T009 (#293) and SPEC-031 T008 (#311). Dependencies: T302.

## S1.5e — Go/no-go (outline, blocked until T032)

- [ ] T401 (REQ-401): Immutable promotion registry, shadow trace capture and
  retention reuse, and atomic rollback to `off`. Carries forward SPEC-033 T002
  (#323) and T003 (#324). Dependencies: T303.
- [ ] T402 (REQ-401): Paired shadow pilot with complete chain costs on the owner's
  work. Carries forward SPEC-033 T006 (#327). Dependencies: T401.
- [ ] T403 (REQ-401): Owner go/no-go per decision point and tracking
  reconciliation; `advise` only on a recorded go. Carries forward SPEC-033 T008
  (#329). Dependencies: T402.
