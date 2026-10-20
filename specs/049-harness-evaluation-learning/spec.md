# SPEC-049: Joint harness evaluation and governed experience reuse

**Milestone:** HAR.2 — Harness evaluation and learning

**Status:** draft; owner confirmed planning direction on 2026-10-20. Implementation, architectural adoption, native qualification and human acceptance remain pending.

## Purpose and scope

Determine separately whether harness refinement improves long-task continuity and agent coordination, then retain only scoped evidence-supported lessons and make explicit human or future automatic promotion decisions.

Internal Codex/Claude use comes first; eventual product use is conditional on evidence. Both long-task continuity and coordination precision/optimization are primary outcomes. Initial autonomy is automatic laboratory trials with human promotion. Synthetic scenarios and a separately gated future automatic-promotion policy are explicitly included. Extra cash spend is capped at EUR 0.

## Authorities

Constitution clause zero and Articles 1, 2, 3, 5, 6, 7, 9, 12, 13, 14, 15, 19, 20, 21, 23, 24, 25; GOVERNANCE.md; operational semantics; claim discipline; accepted ADRs 0019/0020 and applicable proposed ADRs 0021/0024/0025. The feature-local ADR proposal changes no canonical authority.

## Requirements and acceptance scenarios

### REQ-001 — Register an honest two-axis corpus with rights and provenance

**SC-001:** Given owned regression fixtures and candidate real task families are identified, when the corpus is frozen before method evaluation, then it records eligibility, rights, source yield, initial state, exclusions, expected outcomes and synthetic/native status for both strata; unavailable native sources produce a feasibility result.

Verification: [procedure_req_001](validation-plan.md#procedure_req_001). Planned evidence only; obtained evidence: none.

### REQ-002 — Freeze a leakage-controlled comparison before observing outcomes

**SC-002:** Given eligible task families and available budgets are known, when the protocol is registered, then it fixes base and simple-intervention comparators, grouped held-out units, budgets, task order, rubric, annotation/adjudication, missingness rules and acceptance margins independently of candidate rankings.

Verification: [procedure_req_002](validation-plan.md#procedure_req_002). Planned evidence only; obtained evidence: none.

### REQ-003 — Measure correctness and optimization on both axes

**SC-003:** Given a registered attempt is started, refused, interrupted or scored, when the report computes performance, then it reports task correctness, interventions, rework, recovery correctness, conflict precision/recall, unsafe admissions, useful parallelism and coverage with explicit denominators, uncertainty and per-axis results; unknowns never become success.

Verification: [procedure_req_003](validation-plan.md#procedure_req_003). Planned evidence only; obtained evidence: none.

### REQ-004 — Include complete chain costs without extra cash

**SC-004:** Given setup, improvements, probes, selection, reflection, verification, human review and cleanup consume resources, when costs and utility are reconciled, then it reports all attempts and actual or unknown cash, quota/tokens, wall/resource and human time; EUR 0 extra spend is enforced operationally and unknown cash blocks an economic acceptance claim.

Verification: [procedure_req_004](validation-plan.md#procedure_req_004). Planned evidence only; obtained evidence: none.

### REQ-005 — Retain scoped reversible experience

**SC-005:** Given an observed contrast suggests a lesson, including a negative or inconclusive one, when the experience store is updated or queried, then it stores cue, bounded claim, evidence, applicability, provenance, trust state and revocation; quarantine/unvalidated lessons cannot become active instructions and only earlier eligible entries reach an online task.

Verification: [procedure_req_005](validation-plan.md#procedure_req_005). Planned evidence only; obtained evidence: none.

### REQ-006 — Keep initial promotion human and candidate-specific

**SC-006:** Given a variant is selected by a model or passes deterministic tests, when promotion to an ordinary workspace or product is requested, then it requires the explicit human decision for the exact candidate, effects, version and observation scope with rollback; missing approval, native evidence or regression coverage refuses promotion.

Verification: [procedure_req_006](validation-plan.md#procedure_req_006). Planned evidence only; obtained evidence: none.

### REQ-007 — Evaluate future automatic promotion without enabling it

**SC-007:** Given a narrowly eligible low-risk class is proposed for automatic promotion, when the offline policy is assessed against adverse, stale, drifted and contaminated evidence, then it returns a documented go/no-go proposal and remains disabled until separately adopted criteria, independent verification, canary/rollback and operator authority exist; synthetic results can qualify controls but cannot accept native utility.

Verification: [procedure_req_007](validation-plan.md#procedure_req_007). Planned evidence only; obtained evidence: none.

### REQ-008 — Publish bounded per-axis decisions and product integration

**SC-008:** Given evidence is positive, negative, mixed, infeasible or incomplete, when the program reports or proposes an advisory interface, then it preserves each axis and cohort result, baselines, costs, uncertainty and open gates; no blended score hides safety loss and no new MCP execution surface or forecast/model promotion is implied.

Verification: [procedure_req_008](validation-plan.md#procedure_req_008). Planned evidence only; obtained evidence: none.

## Scientific boundaries and compatibility

Domain: Two declared strata: long-task continuity/recovery and interaction/conflict coordination. Synthetic controls and permissioned native tasks are separate cohorts; neither results nor acceptance transfer automatically between them.

Hypotheses: small contrastive harness changes may improve each target outcome at acceptable complete cost; scoped experience may transfer. Either hypothesis can fail. Correctness, declared effects and authority constraints precede optimization. No universal precision, confluence, Yang–Baxter, causal-per-edit or cost-saving guarantee is claimed. Synthetic, native, human and economic evidence remain distinct.

Existing runtime/grants, AIM, plugin, System 1, forecasting and local telemetry contracts remain unchanged. No training, model adoption, telemetry consent, FC.1 source admission or M4 utility acceptance transfers. Public interface names in the plan are proposals until versioned and reviewed.

## Evidence and unresolved questions

Obtained acceptance evidence: none. The upstream audit supports design motivation, not these acceptance scenarios. Pending decisions: exact numerical limits, supported containment backend/OS/host versions, permissioned native sources, native route feasibility, evaluation size/margins and candidate-specific promotion. Tasks order these decisions before dependent execution. See plan.md, tasks.md and assurance.json.
