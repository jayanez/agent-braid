# Proposed tasks

All tasks are unchecked; paths are proposed targets, not files added to the active candidate. Commands are future verification obligations, not commands run here. Dependency independence does not authorize agents. Recheck IDs on the latest branch before integration; retain aliases rather than reusing historic identities.

- [ ] SPEC-045/T009 (RF-T01): Route, consent and source applicability matrix.
  Requirements/scenarios: SPEC-045/REQ-CI-001, SPEC-045/SC-CI-001. Dependencies: none.
  Targets: specs/045-local-forecasting-capabilities/addenda/owned-work-authority.md.
  Verification/negative controls: Missing authority, denied provider route, wrong source root and blanket NO-GO misapplication are distinguished; no collection performed.
  Planned command: `Not executed; after contract adoption and authorized implementation: isolated-python -m unittest tests.test_owned_work_contracts -v`. Planned evidence: `outputs/owned-work-readiness/route-authority.json`; obtained: none.
  Stop rule: Stop collection on missing applicable route authority, source/version drift, privacy failure, unbounded resource use or outcome/split leakage; preserve failure, no paid/model fallback.

- [ ] SPEC-045/T010 (RF-T02): New real-work ledger contract and compatibility disposition.
  Requirements/scenarios: SPEC-045/REQ-CI-002, SPEC-045/SC-CI-002. Dependencies: SPEC-045/T009.
  Targets: specs/045-local-forecasting-capabilities/contracts/owned-work-evaluation-v1.md, specs/045-local-forecasting-capabilities/addenda/owned-work-migration.md.
  Verification/negative controls: Reject relabeling authentic-on-synthetic, current forecast API repo inputs and attempts to modify SPEC047 store; explicit incompatible-version and migration decision.
  Planned command: `Not executed; after contract adoption and authorized implementation: isolated-python -m unittest tests.test_owned_work_contracts -v`. Planned evidence: `outputs/owned-work-readiness/contract-controls.json`; obtained: none.
  Stop rule: Stop collection on missing applicable route authority, source/version drift, privacy failure, unbounded resource use or outcome/split leakage; preserve failure, no paid/model fallback.

- [ ] SPEC-045/T011 (RF-T03): Private bounded lineage store and replay design.
  Requirements/scenarios: SPEC-045/REQ-CI-003, SPEC-045/SC-CI-003. Dependencies: SPEC-045/T010.
  Targets: agent_braid/owned_work_ledger.py, tests/test_owned_work_ledger.py.
  Verification/negative controls: Digest tamper, duplicated/conflicting attempt, truncated write, symlink/hardlink, overflow, revocation, retention and user-managed backups; no source content persistence.
  Planned command: `Not executed; after contract adoption and authorized implementation: isolated-python -m unittest tests.test_owned_work_ledger -v`. Planned evidence: `outputs/owned-work-readiness/ledger-controls.json`; obtained: none.
  Stop rule: Stop collection on missing applicable route authority, source/version drift, privacy failure, unbounded resource use or outcome/split leakage; preserve failure, no paid/model fallback.

- [ ] SPEC-045/T012 (RF-T04): Causal stage/resource receipt adapter.
  Requirements/scenarios: SPEC-045/REQ-CI-004, SPEC-045/SC-CI-004. Dependencies: SPEC-045/T010.
  Targets: agent_braid/owned_work_observer.py, tests/test_owned_work_observer.py.
  Verification/negative controls: Clock regression, missing counters, inclusive span double-counting, observer overhead and cold/warm separation; hook mutation/stall/cleanup failures; no identity enters collector047.
  Planned command: `Not executed; after contract adoption and authorized implementation: isolated-python -m unittest tests.test_owned_work_observer -v`. Planned evidence: `outputs/owned-work-readiness/stage-controls.json`; obtained: none.
  Stop rule: Stop collection on missing applicable route authority, source/version drift, privacy failure, unbounded resource use or outcome/split leakage; preserve failure, no paid/model fallback.

- [ ] SPEC-045/T013 (RF-T05): All-attempt denominator and independently checkable outcome oracle.
  Requirements/scenarios: SPEC-045/REQ-CI-005, SPEC-045/SC-CI-005. Dependencies: SPEC-045/T011, SPEC-045/T012.
  Targets: specs/045-local-forecasting-capabilities/contracts/owned-work-oracle.md, tests/test_owned_work_outcomes.py.
  Verification/negative controls: Prose success, incomplete tests, retry-selected success, immature/censored outcome and changed validation command cannot silently become gold. Freeze inclusion and oracle before collection.
  Planned command: `Not executed; after contract adoption and authorized implementation: isolated-python -m unittest tests.test_owned_work_outcomes -v`. Planned evidence: `outputs/owned-work-readiness/oracle-and-attempt-registry.json`; obtained: none.
  Stop rule: Stop collection on missing applicable route authority, source/version drift, privacy failure, unbounded resource use or outcome/split leakage; preserve failure, no paid/model fallback.

- [ ] SPEC-045/T014 (RF-T06): Frozen forecast assessment and anti-leakage evaluator.
  Requirements/scenarios: SPEC-045/REQ-CI-006, SPEC-045/SC-CI-006. Dependencies: SPEC-045/T013.
  Targets: specs/045-local-forecasting-capabilities/addenda/owned-work-evaluation-protocol.md, tests/test_owned_work_evaluation.py.
  Verification/negative controls: Future features, train/test family overlap, retry leakage, selected-only denominators, unit/horizon mismatch and tiny/empty groups refuse or yield not-estimable; descriptive controls without model calls/fitting.
  Planned command: `Not executed; after contract adoption and authorized implementation: isolated-python -m unittest tests.test_owned_work_evaluation -v`. Planned evidence: `outputs/owned-work-readiness/evaluation-controls.json`; obtained: none.
  Stop rule: Stop collection on missing applicable route authority, source/version drift, privacy failure, unbounded resource use or outcome/split leakage; preserve failure, no paid/model fallback.

- [ ] SPEC-045/T015 (RF-T07): Feedback counterexamples and deduplicated task drafts.
  Requirements/scenarios: SPEC-045/REQ-CI-007, SPEC-045/SC-CI-007. Dependencies: SPEC-045/T014.
  Targets: specs/045-local-forecasting-capabilities/addenda/feedback-triage-contract.md, tests/test_owned_work_feedback.py.
  Verification/negative controls: Repeated counterexample dedup; uncertain attribution retained; no runtime grants, data admission, fitting/calibration, promotion or automatic issue publication.
  Planned command: `Not executed; after contract adoption and authorized implementation: isolated-python -m unittest tests.test_owned_work_feedback -v`. Planned evidence: `outputs/owned-work-readiness/feedback-drafts.json`; obtained: none.
  Stop rule: Stop collection on missing applicable route authority, source/version drift, privacy failure, unbounded resource use or outcome/split leakage; preserve failure, no paid/model fallback.

- [ ] SPEC-045/T016 (RF-T08): Bounded real-work study readiness and handoff.
  Requirements/scenarios: SPEC-045/REQ-CI-001, SPEC-045/REQ-CI-008, SPEC-045/SC-CI-001, SPEC-045/SC-CI-008. Dependencies: SPEC-045/T015, SPEC-047/T011, SPEC-045/T017.
  Targets: docs/system-one/addenda/owned-work-readiness/README.md, docs/system-one/task-map.json.
  Verification/negative controls: Readiness refuses missing source permission, exact v1 packet/route/cost/oracle/split/caps; records pending science/human/host gates. Admitted future collection is a separate execution decision, not done by readiness.
  Planned command: `Not executed; after contract adoption and authorized implementation: isolated-python -m unittest tests.test_owned_work_contracts -v`. Planned evidence: `outputs/owned-work-readiness/readiness.json`; obtained: none.
  Stop rule: Stop collection on missing applicable route authority, source/version drift, privacy failure, unbounded resource use or outcome/split leakage; preserve failure, no paid/model fallback.

- [ ] SPEC-047/T011 (RF-T09): Ledger-to-aggregate privacy compatibility barrier.
  Requirements/scenarios: SPEC-047/REQ-CI-002, SPEC-047/REQ-CI-008, SPEC-047/SC-CI-002, SPEC-047/SC-CI-008. Dependencies: SPEC-045/T010.
  Targets: specs/047-local-technical-telemetry/addenda/owned-work-compatibility.md, tests/test_owned_work_telemetry_privacy.py.
  Verification/negative controls: Inject repository/task/run/attempt/model/policy hashes, exact timestamps, arbitrary metrics, content and metadata traps: current aggregate schema refuses; default-off has no persistence; no collector activation. Reuse T007 controls, add cross-ledger negatives only.
  Planned command: `Not executed; after contract adoption and authorized implementation: isolated-python -m unittest tests.test_owned_work_telemetry_privacy -v`. Planned evidence: `outputs/owned-work-readiness/privacy-boundary-controls.json`; obtained: none.
  Stop rule: Stop collection on missing applicable route authority, source/version drift, privacy failure, unbounded resource use or outcome/split leakage; preserve failure, no paid/model fallback.

- [ ] SPEC-045/T017 (RF-T10; REQ-CI-009 / SC-CI-009): Measure original real-backlog coverage before everyday-use claims.
  Dependencies: SPEC-045/T009,T010; precedes T016 readiness. Targets: specs/045-local-forecasting-capabilities/contracts/real-backlog-coverage.md and tests/test_owned_work_coverage.py.
  Tests: reject .txt laundering; retain unsupported .py/.md/nested-path/operation-count attempts and distinguish legacy analyzer contribution. Command (planned, not executed): `isolated-python -m unittest tests.test_owned_work_coverage -v`. Evidence: outputs/owned-work-readiness/backlog-coverage.json.
  Stop: if coverage infeasible, draft a versioned domain extension with tests and new authority; do not silently loosen v1 or drop unsupported work from denominator.
