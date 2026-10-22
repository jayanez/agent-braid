# SPEC-024 tasks

T002–T004 are implemented and locally verified but remain open: their
declared dependency T001 is still open (canonical ADR integration pending an
owner decision) and the independent code review of the SPEC-024 implementation
has not happened. All other tasks remain open. Negative or inconclusive results
can finish the protocol; real adapters remain excluded.

- [ ] T001 (REQ-001/SC-001, REQ-001/SC-002): Define the typed simulation contract and architecture decision
  - Dependencies: none; contract/ADR review before integration.
  - Status: open. The founder adopted the bounded architecture on 2026-10-21 (feature-local `architecture-decision-20261021.md`); the canonical `docs/adr/` entry and its number await an owner decision.
  - Targets: new dedicated `docs/adr/` ADR, `research/workload_lab/SEMANTICS.md`, new experimental request/report schemas; preserve existing schemas.
  - Commands: planned `python3 scripts/validate_contracts.py`; review grammar, aliases, outcomes and zero external execution.
  - Evidence: reviewed premise/field inventory, positive/negative schema corpus, versioning note, hashes and explicit approval status.
- [ ] T002 (REQ-001/SC-001, REQ-001/SC-002): Implement private configurations and closed transitions
  - Dependencies: T001.
  - Targets: `research/workload_lab/model.py`, `tests/test_effectful_workload_lab.py`.
  - Commands: planned focused tests named in quickstart SC-001/SC-002.
  - Evidence: fresh-state, alias, results/versions/step traces, malformed inputs; source review of forbidden execution surfaces.
  - Status: implemented, pending T001 and independent review; `tests.test_effectful_workload_model` and `tests.test_effectful_workload_contracts` pass; local scan of `research/workload_lab/` finds no process, network, dynamic-import or eval surfaces.
- [ ] T003 (REQ-002/SC-003): Implement finite branch exploration and deterministic caps
  - Dependencies: T002.
  - Targets: `research/workload_lab/explore.py`, `research/workload_lab/__main__.py`, exploration tests.
  - Commands: planned `WorkloadExplorationTests.test_complete_and_truncated_domains` and CLI exploration.
  - Evidence: complete counts, cap-exhaustion artifacts, honest unvisited upper bounds.
  - Status: implemented, pending T001 and independent review; `WorkloadExplorationTests` (including `test_complete_and_truncated_domains`) pass; `python3 -m research.workload_lab explore` on a single frozen fixture request writes an exclusive report; exploration also stops at a 256 MiB retained-payload budget (`capReason: "bytes"`).
- [ ] T004 (REQ-003/SC-004, REQ-005/SC-006): Bind observations and replay retained partial effects
  - Dependencies: T003.
  - Targets: `research/workload_lab/observations.py`, `research/workload_lab/evidence.py`, observation/evidence tests.
  - Commands: planned SC-004/SC-006 tests and `python3 -m research.workload_lab verify <report>`.
  - Evidence: send-then-error/projection and successful matching-values/different-results-or-events controls, global terminal-projection-match labels and stronger-claim refusals, omission/tamper results, digests and no-authorization output.
  - Status: implemented, pending T001 and independent review; `WorkloadObservationTests`, `WorkloadEvidenceTests` and `WorkloadCliTests` pass; `verify` regenerates the report read-only and keeps `executionAuthorization: false`.
- [ ] T005 (REQ-004/SC-005): Freeze race, idempotency and uncertainty controls
  - Dependencies: T002, T004.
  - Status: open, pending T001, T002–T004 and independent review. Manifest/registration and `WorkloadControlsTests` pass. Control evidence `evidence/controls-20261022.json` (SHA-256 `2813261672a3ec2949659a4bd9729e548115a58a67ee81098d53dbb29a3d5290`, captured with `python3 -m research.workload_lab.controls` at source commit `52c49f6d`, Python 3.13.11, no timings): 17/17 fixtures with complete coverage and passing authored controls (7 named controls, 10 H2 fixtures); H2 eligibility 4 terminal candidates, 6 exclusions (outside-additive-class 3, non-success-path 1, unknown-effects 1, version-precondition 1). Scientific review of the corpus is pending.
  - Targets: `examples/workload-lab/` manifest/invariants, control tests.
  - Commands: planned `WorkloadControlsTests.test_named_races_and_hidden_effects` and manifest exploration.
  - Evidence: eligibility/exclusion counts; named race witnesses, alias/hidden-effect abstentions and positives.
- [ ] T006 (REQ-005/SC-006): Compare conservative and declared-effect analysis over matched coverage
  - Dependencies: T003, T004, T005; freeze manifest/budgets before measurement.
  - Targets: `scripts/run_effectful_workload_experiment.py`, `research/workload_lab/analysis.py`, comparison tests/evidence directory.
  - Commands: planned experiment command in quickstart; reject unequal-coverage comparisons.
  - Evidence: environment/input/tool hashes, stage and total costs, retained counts, coverage and negative/inconclusive results.
- [ ] T007 (REQ-006/SC-007): Reproduce and submit the bounded report for scientific review
  - Dependencies: T006, T008.
  - Targets: feature evidence/report/review packet, `research/workload_lab/README.md`, assurance and future-adapter refinement checklist.
  - Commands: planned SC-007 test, clean-clone repetition, quick/stable PR profiles; snapshot then freeze clean candidate.
  - Evidence: raw reproduction output, review findings/status; no real refinement or independent-validation claim until separately evidenced.

- [ ] T008 (REQ-007/SC-008): Implement and freeze the bounded additive terminal-candidate H2 comparison
  - Dependencies: T002, T003, T004, T005; freeze class, corpus and whole-cost threshold before any comparison run. T007 review packet also includes T008 results.
  - Targets: simulator add-constant primitive/rule, `scripts/run_effectful_workload_experiment.py`, `tests/test_effectful_workload_lab.py`, future H2 manifest and evidence packet.
  - Commands: planned `WorkloadH2Tests.test_terminal_rule_preserves_raw_differences_and_denies_runtime` and registered comparison command from quickstart; quick/PR remain separate.
  - Evidence: exact-resource baseline, complete oracle, recovered/false-candidate counts, exclusions, all return/event differences, 3 warm-up/20 measured method repetitions and full-cost accounting. No contextual or runtime safe-parallelism claim; negative/inconclusive completion is valid.
