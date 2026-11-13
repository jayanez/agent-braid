# SPEC-069: Tasks

Stable task IDs. Completion requires obtained evidence; task completion does not
imply native-host, release or owner acceptance. Parallelizable is a dependency
property and does not authorize concurrent agents. Every task that can run
unattended is executed by a script or test, never by manual copy-paste (D5).

Commands run from a clean clone; `quick` means
`.venv-speckit/bin/python -m scripts.validate_change --base develop --profile quick`.

T010 spans P2 (baseline) and the closing phase (final run). If P3 is not
needed, its tasks are closed as not needed (`task_cancellations` in
`docs/development/github-tracking.json`) with the baseline evidence linked,
and T010's final run measures the release candidate without them.

## Phase P1 — contract alignment (D6)

- [x] T001 (REQ-001 / SC-001): [P1] Write ADR 0038 and
  `contracts/analyze-work-request.md`; owner review of spec, plan, ADR and
  contract; OD-1 to OD-4 decided as D10–D13. Dependencies: adversarial and counterfactual
  reviews recorded. Verification: procedure_001. Evidence: owner review record
  bound to a frozen commit.
- [x] T002 (REQ-002 / SC-002): [P1] Script that enumerates schema keywords and
  validator checks and probes each with generated inputs; write
  `evidence/divergence-inventory.json`; owner decides each AIM-acceptance change.
  Dependencies: T001. Verification: procedure_002.
- [x] T003 (REQ-003 / SC-003): [P1] Publish the envelope schema; test against
  examples and corpus. Dependencies: T002. Verification: procedure_003.
- [x] T004 (REQ-004 / SC-004): [P1] Corpus generator, committed corpus, differential
  test with both negative controls; apply T002 decisions to schemas and
  validators. Dependencies: T002, T003. Verification: procedure_004.
- [x] T007 (REQ-007 / SC-007): [P1] Pointer-based structural refusals (unknown keys
  tokenized), fixed-code semantic refusals, masked git errors, no path-existence
  oracle; bounded, no value echo. Dependencies: T004 (`units` refusals are added by T006
  if P3 runs). Verification: procedure_007.
- [x] T009 (REQ-009 / SC-009): [P1] Record alpha.7-accepted requests; replay test (byte-identical
  except the REQ-015 label); schema notes per D8; contract version decision;
  rollback note.
  Dependencies: T004, T007. Verification: procedure_009.
- [x] T015 (REQ-015 / SC-015): [P1] Additive declared-not-observed label for
  `independent-candidate` pairs backed only by declared evidence; report schema
  note; alpha.7 replay. Dependencies: T004. Verification: procedure_015.

## Phase P2 — automation and baseline (D6)

- [x] T013 (REQ-013 / SC-013): [P2] Driver `scripts/spec069_native_runs.py` with
  `--fake-hosts` CI self-test, tool allowlist, OS-sandbox denied-access probe
  and canary, transcript redaction and secret scan, teardown check and
  `runbook.md` manual-step list; research host headless and authentication
  modes (D13); install Codex for the driver (D11). Dependencies: T001. Verification: procedure_013.
- [x] T010 (REQ-010 / SC-010): [P2] Write the prompt sets and scoring rules; freeze
  the held-out set before any guidance rewrite. Baseline run (P2) of alpha.7
  plus the PR #1099 guidance through the driver; final run (closing phase) on
  the release candidate, with the ablation arm; record
  `evidence/native-runs-baseline.json` and `evidence/native-runs.json`; report
  shortfalls as negative results. Dependencies: T013 (baseline); T005–T009,
  T014, T015 (final). Verification: procedure_010.
  Progress 2026-11-11 (still open: held-out final run): Codex baseline and the
  development-set ablation (`final` vs `final-no-schema`) are recorded in
  `evidence/native-runs-baseline-codex.json`, `evidence/native-runs-ablation-*.json` and
  `evidence/native-runs-ablation-summary.json`; see `validation-plan.md`.
  Closed 2026-11-12 with accepted deviation (owner decision 2026-11-12, "Aceptar desviación"): D4 is NOT met. Held-out
  final run done once (`evidence/native-runs-t010-heldout-final*.json`, set `spec069-held-out-v1`, arm `final`, 3 repetitions): first attempt
  Claude Code 27/30 (Wilson 0.74-0.97), OpenCode 27/30 (0.74-0.97), Codex 24/30 (0.63-0.90); within one retry 27/30, 27/30, 24/30; prompts
  9/10, 9/10, 7/10 (Codex misses HELD-02, HELD-04, HELD-05). The 10/10-within-one-retry criterion fails in every host and Codex is also below 8/10
  first attempt. HELD-04 fails every trial on all hosts with the same signature (extra declared read of `src/db.py` on the unit writing
  `docs/api.md`); whether the cause is guidance or prompt/scoring ambiguity is not established. The held-out set is consumed and was not changed;
  the `final-no-schema` ablation was not run on the held-out set (development set only). The shortfall is a documented deviation, not a pass;
  details in `validation-plan.md`.

## Phase P3 — `units` and schema delivery, only if the P2 baseline misses D4 in a required host (D6)

- [x] T006 (REQ-006 / SC-006): [P3, conditional] `units` schema and `agent_braid/units.py`;
  construction table and golden fixtures; forced `partial` coverage;
  lexical normalization; adapter bounds for units; determinism, replay and
  workspace-boundary tests. Dependencies: T004.
  Verification: procedure_006.
- [x] T005 (REQ-005 / SC-005): [P3, conditional] Host probe of nested per-kind schemas first
  (gate); build-time schemas under `request`, plugin `list_tools` test,
  recording-proxy byte check, named-tokenizer size and cap check.
  Dependencies: T004, T006. Verification: procedure_005.
  Progress (2026-11-07, not ticked): offline part delivered for kinds `aim`, `git` and
  `units` (`scripts/spec069_tool_schemas.py`, generated `agent_braid/analyze_work_schema.py`,
  plugin `tool_listing` unit and SDK tests, corpus differential of the declared schema,
  D12 size check, D9 build-time switch `--delivery`); offline evidence
  `evidence/procedure_005.json`. Pending: the host probe of the nested form in Claude
  Code, Codex and OpenCode, the recording-proxy byte identity across host connections and
  the eager/deferred loading record, all on the native driver
  (`reviews/t005-handoff-20261107.md`).
  Native part (2026-11-13): `scripts/spec069_native_runs.py --probe-schema` puts the recording relay
  (`scripts/spec069_stdio_proxy.py --keep-listing`) in front of `launch` in each disposable installed copy and ran one
  session per host and D9 arm (Claude Code 2.1.311, Codex 0.167.0-alpha.4.1, OpenCode 2.1.4). In both arms all three
  hosts exposed `analyze-work`, the `aim` call with `examples/analysis/file-edits.json` and a `units` call reached the
  server with `request` as a JSON object, and every connection served the same `analyze-work` content, equal to the
  build fingerprint. Loading: Claude Code deferred (ToolSearch first), Codex eager, OpenCode eager after its `execute`
  helper. No host hid or stringified the nested form, so no description-only fallback is declared. procedure_005
  passes (`evidence/procedure_005.json` `native`); evidence `evidence/native-probe-schema-*.json`.
- [x] T014 (REQ-014 / SC-014): [P3, conditional] Telemetry and shadow handling for `units`;
  normalization tests on macOS and Linux CI; Windows tested or declared a
  limit; release-note text for the #1099 transition. Dependencies: T006.
  Verification: procedure_014.
- [x] T008 (REQ-008 / SC-008): [P3, conditional] Rewrite skill and tool description for three
  kinds; add `units` examples; drift test. Dependencies: T005, T006, T007, held-out set frozen (T010).
  Verification: procedure_008.
  Progress 2026-11-12: guidance, scoring support for `units` and drift test landed; development-set first attempt Claude Code
  28/30, OpenCode 30/30, Codex 27/30 (validation-plan.md).
  Closed 2026-11-12 with accepted deviation (owner decision 2026-11-12, "Aceptar desviación"): D4 is NOT met on the held-out run (see T010 and
  `validation-plan.md`): Claude Code 27/30 and OpenCode 27/30 first attempt, Codex 24/30; HELD-04 fails identically on all hosts. The owner
  accepted the REQ-008 deviation and the change to the frozen `scripts/spec069_scoring.py` (PR #1314). T005 and T007 are tracked separately and unchanged.

## Closing — final run, documentation and release

- [ ] T011 (REQ-011 / SC-011): [Closing] Update `docs/tooling/NATIVE_PLUGINS.md` and
  release notes from tests and T010 evidence. Dependencies: T010.
  Verification: procedure_011.
- [ ] T012 (REQ-012 / SC-012): [Closing] Release `0.1.0-alpha.8` (or later) after the
  owner's explicit yes; close #1080 with a link to evidence.
  Dependencies: T010, T011. Verification: procedure_012.

## Limits

Corpus agreement is not proof over all inputs. Native results cover the observed
host versions, models and prompt set. Host sign-in may remain a one-time manual
step (D13); any other manual step is a defect in T013.
