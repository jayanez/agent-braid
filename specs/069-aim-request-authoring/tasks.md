# SPEC-069: Tasks

Stable task IDs. Completion requires obtained evidence; task completion does not
imply native-host, release or owner acceptance. Parallelizable is a dependency
property and does not authorize concurrent agents. Every task that can run
unattended is executed by a script or test, never by manual copy-paste (D5).

Commands run from a clean clone; `quick` means
`.venv-speckit/bin/python -m scripts.validate_change --base develop --profile quick`.

T010 spans P2 (baseline) and the closing phase (final run). If P3 is not
needed, its tasks are closed as not needed with the baseline evidence linked,
and T010's final run measures the release candidate without them.

## Phase P1 — contract alignment (D6)

- [ ] T001 (REQ-001 / SC-001): Write ADR 0038 and
  `contracts/analyze-work-request.md`; owner review of spec, plan, ADR and
  contract; decide OD-1 to OD-4. Dependencies: adversarial and counterfactual
  reviews recorded. Verification: procedure_001. Evidence: owner review record
  bound to a frozen commit.
- [ ] T002 (REQ-002 / SC-002): Script that enumerates schema keywords and
  validator checks and probes each with generated inputs; write
  `evidence/divergence-inventory.json`; owner decides each AIM-acceptance change.
  Dependencies: T001. Verification: procedure_002.
- [ ] T003 (REQ-003 / SC-003): Publish the envelope schema; test against
  examples and corpus. Dependencies: T002. Verification: procedure_003.
- [ ] T004 (REQ-004 / SC-004): Corpus generator, committed corpus, differential
  test with both negative controls; apply T002 decisions to schemas and
  validators. Dependencies: T002, T003. Verification: procedure_004.
- [ ] T007 (REQ-007 / SC-007): Pointer-based structural refusals (unknown keys
  tokenized), fixed-code semantic refusals, masked git errors, no path-existence
  oracle; bounded, no value echo. Dependencies: T004 (`units` refusals are added by T006
  if P3 runs). Verification: procedure_007.
- [ ] T009 (REQ-009 / SC-009): Record alpha.7-accepted requests; replay test (byte-identical
  except the REQ-015 label); schema notes per D8; contract version decision;
  rollback note.
  Dependencies: T004, T007. Verification: procedure_009.
- [ ] T015 (REQ-015 / SC-015): Additive declared-not-observed label for
  `independent-candidate` pairs backed only by declared evidence; report schema
  note; alpha.7 replay. Dependencies: T004. Verification: procedure_015.

## Phase P2 — automation and baseline (D6)

- [ ] T013 (REQ-013 / SC-013): Driver `scripts/spec069_native_runs.py` with
  `--fake-hosts` CI self-test, tool allowlist, OS-sandbox denied-access probe
  and canary, transcript redaction and secret scan, teardown check and
  `runbook.md` manual-step list; research host headless and authentication
  modes (OD-4); install Codex for the driver (D11). Dependencies: T001. Verification: procedure_013.
- [ ] T010 (REQ-010 / SC-010): Write the prompt sets and scoring rules; freeze
  the held-out set before any guidance rewrite. Baseline run (P2) of alpha.7
  plus the PR #1099 guidance through the driver; final run (closing phase) on
  the release candidate, with the ablation arm; record
  `evidence/native-runs-baseline.json` and `evidence/native-runs.json`; report
  shortfalls as negative results. Dependencies: T013 (baseline); T005–T009,
  T014, T015 (final). Verification: procedure_010.

## Phase P3 — `units` and schema delivery, only if the P2 baseline misses D4 in a required host (D6)

- [ ] T006 (REQ-006 / SC-006): `units` schema and `agent_braid/units.py`;
  construction table and golden fixtures; forced `partial` coverage;
  lexical normalization; adapter bounds for units; determinism, replay and
  workspace-boundary tests. Dependencies: T004.
  Verification: procedure_006.
- [ ] T005 (REQ-005 / SC-005): Host probe of nested per-kind schemas first
  (gate); build-time schemas under `request`, plugin `list_tools` test,
  recording-proxy byte check, named-tokenizer size and cap check.
  Dependencies: T004, T006. Verification: procedure_005.
- [ ] T014 (REQ-014 / SC-014): Telemetry and shadow handling for `units`;
  normalization tests on macOS and Linux CI; Windows tested or declared a
  limit; release-note text for the #1099 transition. Dependencies: T006.
  Verification: procedure_014.
- [ ] T008 (REQ-008 / SC-008): Rewrite skill and tool description for three
  kinds; add `units` examples; drift test. Dependencies: T005, T006, T007, held-out set frozen (T010).
  Verification: procedure_008.

## Closing — final run, documentation and release

- [ ] T011 (REQ-011 / SC-011): Update `docs/tooling/NATIVE_PLUGINS.md` and
  release notes from tests and T010 evidence. Dependencies: T010.
  Verification: procedure_011.
- [ ] T012 (REQ-012 / SC-012): Release `0.1.0-alpha.8` (or later) after the
  owner's explicit yes; close #1080 with a link to evidence.
  Dependencies: T010, T011. Verification: procedure_012.

## Limits

Corpus agreement is not proof over all inputs. Native results cover the observed
host versions, models and prompt set. Host sign-in may remain a one-time manual
step (OD-4); any other manual step is a defect in T013.
