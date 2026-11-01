# SPEC-033: Tasks

> Note (2026-11-01): SPEC-066 (draft) absorbs the open tasks T002, T003, T004, T006 and T008 (S1.5c/e: T004 is carried by SPEC-066 T203; T002, T003, T006 and T008 by T401–T403). See [SPEC-066](../066-system-one-shadow/spec.md). No checkbox below is changed by this note.

Implementation and research acceptance tasks; every checkbox starts pending.
IDs are stable inside the spec. Cross-spec dependencies use SPEC-nnn/Tnnn.
No task authorizes parallel agents, paid calls, data collection or live execution.
Paths outside this spec are prospective implementation targets, not existing files.
All evidence records include command, input/candidate hashes, environment and limits.

- [ ] T001 (REQ-002 REQ-006 / SC-002 SC-006): Review capability-specific promotion and rollback criteria.
  Dependencies: SPEC-029/T008 SPEC-031/T001. Target files: promotion-protocol.md, contracts/promotion.md.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Freeze risk/quality/cost envelopes and responsible reviewers before observing candidate rankings. Planned evidence: candidate-bound report under specs/033-system-one-promotion/evidence/t001.json; obtained: none.
- [ ] T002 (REQ-001 / SC-001): Implement shadow-only trace capture and retention controls.
  Dependencies: T001 SPEC-031/T007. Target files: agent_braid/system_one_trace.py, tests/test_system_one_shadow.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_shadow -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Prove identical legacy outputs under shadow, bounded storage and privacy-preserving metadata. Planned evidence: candidate-bound report under specs/033-system-one-promotion/evidence/t002.json; obtained: none.
- [ ] T003 (REQ-002 REQ-004 / SC-002 SC-004): Implement immutable artifact/capability promotion registry.
  Dependencies: T002. Target files: agent_braid/system_one_registry.py, tests/test_system_one_registry.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_registry -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Bind exact candidate and review scope; test altered calibration, policy and optional backend. Planned evidence: candidate-bound report under specs/033-system-one-promotion/evidence/t003.json; obtained: none.
- [ ] T004 (REQ-003 / SC-003): Implement domain drift checks and label-aware monitoring.
  Dependencies: T003. Target files: agent_braid/system_one_monitor.py, tests/test_system_one_drift.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_drift -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Unknown/unlabeled drift stays unknown; affected domains deterministically defer. Planned evidence: candidate-bound report under specs/033-system-one-promotion/evidence/t004.json; obtained: none.
- [ ] T005 (REQ-004 REQ-005 / SC-004 SC-005): Implement atomic rollback and bounded fallback chains.
  Dependencies: T003 T004. Target files: agent_braid/system_one_policy.py, tests/test_system_one_rollback.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_rollback -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Inject outages, OOM, stale manifests and deadline exhaustion; verify no paid/provider call by default. Planned evidence: candidate-bound report under specs/033-system-one-promotion/evidence/t005.json; obtained: none.
- [ ] T006 (REQ-001 REQ-002 REQ-006 / SC-001 SC-002 SC-006): Run paired shadow pilot with complete chain costs.
  Dependencies: T005 SPEC-029/T009 SPEC-031/T008. Target files: research/system_one/shadow-results/, shadow-protocol.md.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Record actual permissions, label coverage, total costs and conflicts; no generic throughput claim. Planned evidence: candidate-bound report under specs/033-system-one-promotion/evidence/t006.json; obtained: none.
- [ ] T007 (REQ-002 REQ-006 / SC-002 SC-006): Build exact-candidate closure packet with fresh reproduction.
  Dependencies: T006. Target files: specs/033-system-one-promotion/closure.md, assurance.json.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Separate software passing, utility/no-gain, host/hardware coverage and pending independent review. Planned evidence: candidate-bound report under specs/033-system-one-promotion/evidence/t007.json; obtained: none.
- [ ] T008 (REQ-002 REQ-006 / SC-002 SC-006): Record founder per-capability go/no-go and reconcile tracking.
  Dependencies: T007. Target files: specs/033-system-one-promotion/founder-review.json, docs/development/github-tracking.json.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Only an actual decision changes adoption/tracking; do not auto-close M3.5 or M4. Planned evidence: candidate-bound report under specs/033-system-one-promotion/evidence/t008.json; obtained: none.

Final candidate verification: `.venv-speckit/bin/python scripts/validate_change.py
--base develop --profile pr`. Tests/procedures and feature evidence do not substitute
for human review, scientific interpretation, explicit source rights or promotion.


## Documentary reconciliation of research and proposed delivery — 2026-10-20

These additive canonical identities retain the existing study/DDP aliases. Checked entries mean only their stated bounded historical lot; original research, human, model and product gates remain open. The evidence register is a documentary source snapshot, not new implementation or independent reproduction. See docs/system-one/README.md and task-map.json. No task launches agents or authorizes a study. Checked entries below that cite PR #655 (commit a6329c82) and the documentary corpus PRs #594, #608, #609, #610 cover the bounded engineering lot only; human, Claude, scientific, admission, calibration, promotion, activation, product-publication and host-adoption gates stay pending ([pending gates](../../docs/system-one/addenda/v1-publication-closure-20261021/pending-gates.md)). `docs/system-one/task-map.json` and the `*-corpus-status.md` files are frozen documentary snapshots: their "open; not started", planned file names and "checkboxes unchanged" wording predate these ticks and are not rewritten. No issue or milestone is closed.

- [x] T009 (REQ-002 REQ-006 / SC-002 SC-006): Package bounded delivery and adoption gates (alias DDP-T08; delivered, bounded engineering lot).
  Dependencies: SPEC-029/T027. Owner: coordinator.
  Delivered at: documentary gate packaging only. The planned `specs/033-system-one-promotion/decision-delivery-gates.md` and `specs/028-system-one-core/decision-delivery-result.md` were intentionally not created (the producer documents carry private-package links); the exact capsules live in the T08 supplement.
  Evidence: [T08 final supplement](../../docs/system-one/addenda/t08-final-20261020/README.md), [T08 corpus status](t08-corpus-status.md); task-map alias DDP-T08.
