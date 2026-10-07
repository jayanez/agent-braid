# SPEC-032: Tasks

Implementation and research acceptance tasks; every checkbox starts pending.
IDs are stable inside the spec. Cross-spec dependencies use SPEC-nnn/Tnnn.
No task authorizes parallel agents, paid calls, data collection or live execution.
Paths outside this spec are prospective implementation targets, not existing files.
All evidence records include command, input/candidate hashes, environment and limits.

T001 records a selected or deferred disposition for every extension. Only selected
branches become implementation prerequisites. A deferred branch keeps its task
unchecked, its scenarios draft and obtained evidence empty; record the reason and
reconsideration condition. T008 can finish a bounded decision packet for the selected
subset without completing deferred tasks or accepting the entire spec. Model
selection gates learned branches only, never the schema compiler or core hooks.

- [x] T001 (REQ-001 REQ-002 REQ-003 REQ-004 REQ-005 REQ-006 / SC-001 SC-002 SC-003 SC-004 SC-005 SC-006): Review supported feature subset and CPU/device budget matrix.
  Dependencies: SPEC-028/T001. Target files: product-decisions.md, contracts/product.md.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Record a selected/deferred disposition, supported domain, deployment envelope, branch prerequisites and reconsideration condition for each extension. A pending or NO-GO model experiment cannot block selecting the schema compiler or core hooks. Planned evidence: candidate-bound report under specs/032-system-one-product/evidence/t001.json; obtained: `evidence/technical-delivery.json` and its bound focused controls, Luna review, full executable profiles and installed-wheel records (selected synthetic engineering only; broader acceptance pending).
- [ ] T002 (REQ-001 / SC-001): Implement optional export/quantization with CPU reference parity.
  Dependencies: T001 SPEC-028/T008. Target files: agent_braid_system_one/export.py, tests/test_system_one_export.py.
  Branch requirements: Only if export/quantization is selected; require SPEC-030/T008 for the exact model being exported. If deferred, leave T002 pending and record no backend support claim.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_export -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Measure probability/decision changes, cold/warm latency and peak RSS; no blanket speed claims. Planned evidence: candidate-bound report under specs/032-system-one-product/evidence/t002.json; obtained: none.
- [x] T003 (REQ-002 / SC-002): Implement evidence-bound language/task/model routing.
  Dependencies: T001 SPEC-028/T008. Target files: agent_braid/system_one_router.py, tests/test_system_one_router.py.
  Branch requirements: Only if routing is selected. Rules/metadata routing can be engineered without a model; learned routing additionally requires SPEC-030/T008. Domain/calibration and promotion evidence remain separate gates.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_router -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Test Spanish, English, unknown languages, short code and mixed-script input before confidence routing. Planned evidence: candidate-bound report under specs/032-system-one-product/evidence/t003.json; obtained: `evidence/technical-delivery.json` and its bound focused controls, Luna review, full executable profiles and installed-wheel records (selected synthetic engineering only; broader acceptance pending).
- [x] T004 (REQ-003 / SC-003): Implement bounded schema-to-question compiler.
  Dependencies: SPEC-028/T008 T001. Target files: agent_braid/system_one_schema.py, tests/test_system_one_schema.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_schema -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Cover nested local refs, enums, nullability, cycles, ordering and refusal of free-form generation. Planned evidence: candidate-bound report under specs/032-system-one-product/evidence/t004.json; obtained: `evidence/technical-delivery.json` and its bound focused controls, Luna review, full executable profiles and installed-wheel records (selected synthetic engineering only; broader acceptance pending).
- [ ] T005 (REQ-004 / SC-004): Implement shortlist and tournament with subset provenance.
  Dependencies: T001 SPEC-028/T008 SPEC-029/T009. Target files: agent_braid/system_one_catalogue.py, tests/test_system_one_catalogue.py.
  Branch requirements: Only if catalogue selection is selected. Require T003 only when using its router, and SPEC-030/T008 only when using a learned scorer. An infeasibility report from SPEC-029/T009 supplies no measured recall, calibration or utility; those acceptance gates remain pending.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_catalogue -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Compare recall@k and tournament group/order sensitivity; calibrate final chain separately. Planned evidence: candidate-bound report under specs/032-system-one-product/evidence/t005.json; obtained: none.
- [ ] T006 (REQ-005 / SC-005): Implement token-budget batching and reference-counted model lifecycle.
  Dependencies: T001 SPEC-028/T008. Target files: agent_braid_system_one/worker.py, tests/test_system_one_lifecycle.py.
  Branch requirements: Only if batching/model lifecycle is selected; require SPEC-030/T008 for the served model. Require T002 or T003 only when the selected worker uses that export or router. A reference worker need not implement either extension.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_lifecycle -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Barrier tests cover unload-during-inference, cancellation, overload and cross-request contamination. Planned evidence: candidate-bound report under specs/032-system-one-product/evidence/t006.json; obtained: none.
- [x] T007 (REQ-006 / SC-006): Implement observer hooks and fresh offline wheel install checks.
  Dependencies: T001 SPEC-028/T008. Target files: agent_braid/system_one_hooks.py, tests/test_system_one_packaging.py.
  Branch requirements: Only if hooks/packaging is selected. Wheel checks require completed implementation only for extensions included in that wheel; deferred backends must be absent or reported unsupported. Core hook checks do not require model, catalogue or batching implementation.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_packaging -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Test sealed-input mutation, blocked hooks and installed extras in a clean environment. Planned evidence: candidate-bound report under specs/032-system-one-product/evidence/t007.json; obtained: `evidence/technical-delivery.json` and its bound focused controls, Luna review, full executable profiles and installed-wheel records (selected synthetic engineering only; broader acceptance pending).
- [x] T008 (REQ-001 REQ-002 REQ-003 REQ-004 REQ-005 REQ-006 / SC-001 SC-002 SC-003 SC-004 SC-005 SC-006): Capture per-feature evaluation and accept or defer each extension.
  Dependencies: T001. Target files: specs/032-system-one-product/feature-acceptance.md, assurance.json.
  Branch requirements: Require each selected implementation task among T002 through T007, plus its declared branch prerequisites. Deferred tasks are not prerequisites and stay pending. An all-deferred packet may document infeasibility without any implementation acceptance.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Retain negative recall/language/parity findings and a per-feature selected/deferred/evaluated disposition with actual evidence and remaining gates. Validate only scenarios with their own executed evidence; deferred scenarios remain draft with empty obtained evidence. Test the planning exits for schema-only, hooks-only, deferred export with reference lifecycle, and all-deferred subsets. No whole-spec acceptance or SPEC-033 promotion is inferred from completing this packet. Obtained selected engineering packet: `feature-acceptance.md`, `evidence/technical-delivery.json` and its bound executable profiles, independent Luna review and installed-wheel checks. Supported clean candidate freeze executed; human/empirical/model acceptance remains pending and deferred tasks stay unchecked.

Final candidate verification: `.venv-speckit/bin/python scripts/validate_change.py
--base develop --profile pr`. Tests/procedures and feature evidence do not substitute
for human review, scientific interpretation, explicit source rights or promotion.

## Obtained selected engineering evidence (2026-10-07)

Evidence is bound in `evidence/technical-delivery.json` and the focused, review,
quick-profile and exact offline-wheel records. Whole assurance remains draft;
human/empirical/model acceptance is pending. Stable PR profile passed on the bound metadata candidate. Clean supported freeze
is recorded in assurance.json; human/empirical gates remain pending.
