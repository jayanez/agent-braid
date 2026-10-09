# SPEC-044: AI tooling evaluation and closure

**Milestone:** M4.5 — AI tooling integrations for Codex and Claude Code

**Status:** draft specification; implementation, observations and human acceptance are pending.

## Purpose and scope

Register and execute candidate-bound deterministic controls, clean reproduction, actual Codex/Claude journeys and the complete 108-attempt three-arm technical comparison. Human outcome ratings and adjudication are a separate, explicitly deferred phase under [the owner decision](human-evaluation-deferral-clarification.md).

## Authorities

Constitution clause zero and Articles 3–7, 12–16, 19–25; GOVERNANCE.md; operational semantics, claim discipline, ADRs 0019/0020 and proposed ADR 0021. This spec is subordinate to accepted authorities. See assurance.json for references and authority inventory.

## Requirements and acceptance scenarios

### REQ-001

Preregister exact population, source rights, candidate/input/host/SDK identities and either an immutable provider model-build identity or an explicitly labelled observable requested route, all 108 attempts, the mandatory included-subscription-only billingPolicy, frozen rubric, two abstract independent reviewer roles, human evaluation deferral record and numerical caps before technical capture. Human identities, ratings and adjudication are added later through a separately bound addendum.

**SC-001:** Given unapproved paid capture or a drifted/missing registration, when capture admission runs, then unapproved costs/rights/versions refuse; owned deterministic controls remain a separately identified engineering path.

Verification: [procedure_registration_gate](validation-plan.md); [T001](tasks.md). Obtained evidence: none.

### REQ-002

Obtain actual discovery, five-skill loading and complete basic journey receipts in both selected macOS arm64 hosts.

**SC-002:** Given a real host and a mock protocol client, when host support is assessed, then only real host receipts satisfy host acceptance, with exact host/bundle identities, requested and reported model selectors distinguished, backend identity unavailable when not exposed, and interactive blocks reported.

Verification: [procedure_actual_host_observation](validation-plan.md); [T002](tasks.md). Obtained evidence: none.

### REQ-003

Run parity, malformed/stale/unsafe/grant/cancellation/recovery and output-agreement controls with exact oracle outcomes.

**SC-003:** Given all mandatory positive/negative control cases, when deterministic validation runs, then zero unauthorized effects, false successes or authority exposures occur; every attempted failure remains recorded.

Verification: [procedure_negative_controls](validation-plan.md); [T003](tasks.md). Obtained evidence: none.

### REQ-004

Reproduce installed-package/core/protocol controls on clean macOS arm64 and Linux x86_64 environments.

**SC-004:** Given separate clean environments and frozen artifacts, when reproduction runs, then candidate/environment/commands/results are bound; Linux protocol results do not claim real-host adoption.

Verification: [procedure_clean_reproduction](validation-plan.md); [T004](tasks.md). Obtained evidence: none.

### REQ-005

Compare CLI, MCP-only and MCP-plus-skills on 108 registered attempts with counterbalanced order and no outcome-driven revisions.

**SC-005:** Given the three-arm fixture roster and isolated sessions, when all slots are processed, then completion, interventions and fidelity are compared with full denominators, failures and carryover disclosed.

Verification: [procedure_three_arm_comparison](validation-plan.md); [T005](tasks.md). Obtained evidence: none.

### REQ-006

Measure complete technical setup/provider/tool/runtime/export/user costs and preserve future human reviewer time/fee fields as unknown until the separate human phase; enforce numerical stops and never interpret technical cost completion as full human-inclusive economic completion.

**SC-006:** Given missing tokens, overlapping phases, exceeded budget and provider failure, when cost accounting and admission run, then unknown differs from zero, wall totals are not double-counted and exceeded/blocked attempts stop without silent retry.

Verification: [procedure_complete_cost](validation-plan.md); [T006](tasks.md). Obtained evidence: none.

### REQ-007

Retain the frozen human rubric and descriptive thresholds before capture; complete deterministic technical interpretation while human outcome labels and adjudication remain pending, then report disagreements/missing labels when the separately deferred human phase occurs.

**SC-007:** Given completion thresholds met with complete costs, or missing required costs, a host failure or unresolved scoring, when the report is interpreted, then per-host denominators and uncertainty remain visible; missing costs that prevent interpretation set utilityClaimEligible false and suppress positive utility claims in reports/exports/decision packets despite completion thresholds; safety failures block acceptance and no general causal speedup claim is inferred.

Verification: [procedure_interpretation](validation-plan.md); [T007](tasks.md). Obtained evidence: none.

### REQ-008

Prepare a technical decision packet from T001–T006 and completed technical T007 evidence, with human evaluation explicitly pending; obtain independent technical review and preserve the separate founder acceptance/closure decision and historical M4 limits.

**SC-008:** Given a bounded completed or inconclusive report, when the decision packet is assembled, then implementation/protocol/human gates are separated; M4.5 acceptance cannot reverse M4 G4 NO-GO or close M4.

Verification: [procedure_acceptance_decision](validation-plan.md); [T008](tasks.md). Obtained evidence: none.

## Scientific boundaries and compatibility

Domain: Exact local host builds and registered provider model identities on macOS arm64 and owned registered fixture population; opaque backend builds remain unavailable under the approved observable-route interpretation. Linux x86_64 core/protocol reproduction is a separate domain.

Hypothesis: MCP plus skills may improve completion, interventions or evidence fidelity over CLI/MCP-only. Negative, null and infeasible outcomes are valid.

Existing AIM/runtime/grant/verifier contracts remain unchanged. Analysis and preparation are consultative; host permission never substitutes for operator grants. No source ref promotion, repository-code/hook execution, arbitrary network effects or new scientific guarantee. Existing M4 G4 NO-GO and independent M3/M3.5 gates remain in effect.

SDK/documentation, structural checks, synthetic controls, actual host observations and independent reproduction have separate evidence domains. Passing one does not establish the others or human approval. Public APIs are additive experimental proposals with migration/versioning review during implementation.

## Approved model identity interpretation

See [model-identity-clarification.md](model-identity-clarification.md) and [human-evaluation-deferral-clarification.md](human-evaluation-deferral-clarification.md). Immutable provider build identifiers are mandatory when exposed. Otherwise freeze the exact requested selector/effort, host build/hash, dated native catalog artifact/entry hashes, selection/configuration and authenticated provider/account route; retain backend identity as unavailable. These metadata hashes are not model-build hashes. Observable drift refuses admission and requires a new reviewed cohort. Hidden backend revisions and nondeterminism limit reproducibility. The owner approved this interpretation on 2026-10-09. The same date, the owner deferred human outcome ratings/adjudication only; all 108 slots, the frozen rubric, full economic scope and all technical capture gates remain. Neither decision approves capture or a complete registration.

## Evidence and unresolved questions

Planned procedures are in validation-plan.md; obtained evidence is empty in assurance.json. The packet records a proposed design, not a runtime acceptance result. Required decisions: technical contract/ADR adoption, exact host versions and installation scope, provider budget/source rights for capture, candidate-bound technical review, later human identities/ratings/adjudication, and founder acceptance. T007 human work, T010 and milestone closure remain pending. See program.md in SPEC-039 and evaluation-protocol.md in SPEC-044.
