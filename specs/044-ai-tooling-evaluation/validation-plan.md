# SPEC-044: Prospective validation procedures

These procedures are plans except for bounded synthetic deterministic-control evidence for REQ-003/SC-003, recorded at `evidence/sc-003.json` and bound only to the candidate identified there. That evidence does not establish actual-host or provider observations, MCP SDK transport behavior, clean-room reproduction or human outcome evaluation. The other procedures remain planned or pending unless their own evidence records say otherwise. A passed source validator checks structure only.

Record positive, refusal, unknown, failed, cancelled and unexecuted outcomes. Evidence must include full candidate and input hashes, command/tool trace, environment, output hashes, domain and limits. Human decisions remain separate.

## procedure_registration_gate (REQ-001/SC-001)

The registration is ready for approval only after the stable 040–043 candidate, immutable inputs/fixtures, exact host builds and discriminated provider model identities, full 108-slot roster, source rights, mandatory included-subscription-only `billingPolicy`, two unique abstract independent reviewer roles, the approved human-evaluation deferral record, frozen rubric and numerical cost/resource caps are identified. This v3 requirement does not alter legacy v1/v2 optional-policy behavior. For v3 technical capture, `humanReviewers` is empty; named identities and scoring are deferred to a separately bound addendum. Legacy v1/v2 retain their named-human contract and reject v3 phase/deferral/role fields. Before any actual attempt, validate that the approved registration binds those values and that drift, missing rights or unapproved provider cost refuses admission; owned deterministic controls remain a separately identified engineering path. Include success and refusal/unavailable counterparts; retain source/result-root integrity and exact typed output. Drafting or validating a registration does not authorize paid/provider capture. Test both immutable-provider-build and approved observable-requested-route identities: exposed immutable identifiers are mandatory; an opaque backend stays unavailable; metadata digests cannot substitute for model-build identity. Missing or tampered selector, effort, catalog, effective configuration, host build or account route refuses admission, including mutations after attestation. Preserve the legacy immutable interpretation; a new observable record cannot pass by filling its backend fields with metadata hashes.

Prospective targets: `specs/044-ai-tooling-evaluation/registration.json (future); research/tooling_evaluation.py (new); tests/test_tooling_evaluation.py (new); specs/044-ai-tooling-evaluation/evidence/ (future); docs/releases/M4_5_CLOSURE.md (future)`. Planned receipt: `evidence/sc-001.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

## procedure_actual_host_observation (REQ-002/SC-002)

Given a real host and a mock protocol client; perform host support is assessed. Assert only real host receipts satisfy host acceptance, with exact host/bundle identities, requested and reported model selectors distinguished, backend identity unavailable when not exposed, and interactive blocks reported. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `specs/044-ai-tooling-evaluation/registration.json (future); research/tooling_evaluation.py (new); tests/test_tooling_evaluation.py (new); specs/044-ai-tooling-evaluation/evidence/ (future); docs/releases/M4_5_CLOSURE.md (future)`. Planned receipt: `evidence/sc-002.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

## procedure_negative_controls (REQ-003/SC-003)

Given all mandatory positive/negative control cases; perform deterministic validation runs. Assert zero unauthorized effects, false successes or authority exposures occur; every attempted failure remains recorded. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `specs/044-ai-tooling-evaluation/registration.json (future); research/tooling_evaluation.py (new); tests/test_tooling_evaluation.py (new); specs/044-ai-tooling-evaluation/evidence/ (future); docs/releases/M4_5_CLOSURE.md (future)`. Planned receipt: `evidence/sc-003.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

## procedure_clean_reproduction (REQ-004/SC-004)

Given separate clean environments and frozen artifacts; perform reproduction runs. Assert candidate/environment/commands/results are bound; Linux protocol results do not claim real-host adoption. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `specs/044-ai-tooling-evaluation/registration.json (future); research/tooling_evaluation.py (new); tests/test_tooling_evaluation.py (new); specs/044-ai-tooling-evaluation/evidence/ (future); docs/releases/M4_5_CLOSURE.md (future)`. Planned receipt: `evidence/sc-004.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

## procedure_three_arm_comparison (REQ-005/SC-005)

Given an approved T001 registration and the exact stable 040–043 candidate, immutable three-arm fixture roster and isolated sessions; perform all 108 intended slots are processed or explicitly retained as not-started/interrupted. Assert completion, interventions and fidelity are compared with full per-host/class/arm denominators, failures and carryover disclosed, and no prompt, fixture, threshold or rubric is revised from observed outcomes. Include success and refusal/unavailable counterparts; retain source/result-root integrity and exact typed output.

Prospective targets: `specs/044-ai-tooling-evaluation/registration.json (future); research/tooling_evaluation.py (new); tests/test_tooling_evaluation.py (new); specs/044-ai-tooling-evaluation/evidence/ (future); docs/releases/M4_5_CLOSURE.md (future)`. Planned receipt: `evidence/sc-005.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

## procedure_complete_cost (REQ-006/SC-006)

Before any actual T002/T004/T005 attempt, validate the cost fields, source timestamps, stop thresholds and accounting instrumentation against deterministic controls. After all attempted T002–T005 slots, reconcile complete setup and per-attempt costs with the registered denominator, retaining unavailable fields and affected attempt IDs. Given missing tokens, overlapping phases, exceeded budget and provider failure; perform accounting and admission controls. Assert unknown differs from zero, wall totals are not double-counted and exceeded/blocked attempts stop without silent retry. Include success and refusal/unavailable counterparts; retain source/result-root integrity and exact typed output.

Prospective targets: `specs/044-ai-tooling-evaluation/registration.json (future); research/tooling_evaluation.py (new); tests/test_tooling_evaluation.py (new); specs/044-ai-tooling-evaluation/evidence/ (future); docs/releases/M4_5_CLOSURE.md (future)`. Planned receipt: `evidence/sc-006.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

## procedure_interpretation (REQ-007/SC-007)

Given technical outcomes and costs retained for all 108 slots while human labels/adjudication are pending; interpret the technical report and prepare exports/decision packet with human evaluation pending and no positive utility conclusion. After a separately bound human addendum, apply the frozen rubric and all registered cost gates. The complete-cost control may clear cost eligibility only, subject to every other rubric/acceptance gate. In the missing-cost control, assert utilityClaimEligible is false, the utility conclusion is inconclusive, and no positive utility claim appears in structured results, narrative exports or the decision packet despite passing completion thresholds. Retain missing fields and affected attempt IDs; never substitute zero, omit attempts or silently narrow the registered claim. Also test host failure and unresolved scoring: per-host denominators/uncertainty remain visible, safety failures block acceptance and no general causal speedup claim is inferred. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `specs/044-ai-tooling-evaluation/registration.json (future); research/tooling_evaluation.py (new); tests/test_tooling_evaluation.py (new); specs/044-ai-tooling-evaluation/evidence/ (future); docs/releases/M4_5_CLOSURE.md (future)`. Planned receipt: `evidence/sc-007.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

## procedure_acceptance_decision (REQ-008/SC-008)

Given a T009-reconciled technical candidate, T001–T006 and completed technical T007 evidence, applicable technical observation gates, a completed or inconclusive technical report with human evaluation pending, and independent technical findings; perform the decision packet is prepared with candidate/evidence hashes, gate status, limits and a founder decision field explicitly marked pending. Assert packet preparation does not imply owner acceptance. Human evaluation, T010 and final M4.5 closure remain pending. Only after the later human phase, independent findings and actual founder decision may T010 record an appropriate decision; acceptance cannot reverse M4 G4 NO-GO or close M4. Include success and refusal/unavailable counterparts; retain source/result-root integrity and exact typed output.

Prospective targets: `specs/044-ai-tooling-evaluation/registration.json (future); research/tooling_evaluation.py (new); tests/test_tooling_evaluation.py (new); specs/044-ai-tooling-evaluation/evidence/ (future); docs/releases/M4_5_CLOSURE.md (future)`. Planned receipt: `evidence/sc-008.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.
