# SPEC-048: Bounded harness variants and isolated probing

**Milestone:** HAR.1 — Harness variant laboratory

**Status:** draft; owner confirmed planning direction on 2026-10-20. Implementation, architectural adoption, native qualification and human acceptance remain pending.

## Purpose and scope

Provide a native Agent Braid mechanism to propose, probe and compose small task-local harness variants against an immutable base, first with deterministic fixtures and later through separately qualified Codex/Claude adapters.

Internal Codex/Claude use comes first; eventual product use is conditional on evidence. Both long-task continuity and coordination precision/optimization are primary outcomes. Initial autonomy is automatic laboratory trials with human promotion. Synthetic scenarios and a separately gated future automatic-promotion policy are explicitly included. Extra cash spend is capped at EUR 0.

## Authorities

Constitution clause zero and Articles 1, 2, 3, 5, 6, 7, 9, 12, 13, 14, 15, 19, 20, 21, 23, 24, 25; GOVERNANCE.md; operational semantics; claim discipline; accepted ADRs 0019/0020 and applicable proposed ADRs 0021/0024/0025. The feature-local ADR proposal changes no canonical authority.

## Requirements and acceptance scenarios

### REQ-001 — Protect authorities and constrain the editable surface

**SC-001:** Given a candidate changes global instructions, grants, validators, host settings, tools, hooks, executable scripts or an out-of-scope path, when the importer validates the candidate, then it refuses before materialization or execution and preserves the base; symlinks, traversal, oversized files and undeclared effects refuse.

Verification: [procedure_req_001](validation-plan.md#procedure_req_001). Planned evidence only; obtained evidence: none.

### REQ-002 — Bind complete experiment identity

**SC-002:** Given a base, candidate, task source, host/model selection, tool inventory, policy, context or environment changes, when any admission, cache or resume consumer validates its immutable manifest, then it detects the mismatch and refuses reuse; unknown provider build identity stays explicit and cannot masquerade as a pinned build.

Verification: [procedure_req_002](validation-plan.md#procedure_req_002). Planned evidence only; obtained evidence: none.

### REQ-003 — Separate proposal from operator admission

**SC-003:** Given a proposed candidate exists without fresh matching laboratory admission, when a probe requests execution, then it refuses without effects; only an independently enforced, operator-adopted envelope can admit dynamically generated candidate hashes and no existing runtime grant is widened.

Verification: [procedure_req_003](validation-plan.md#procedure_req_003). Planned evidence only; obtained evidence: none.

### REQ-004 — Enforce and qualify laboratory containment

**SC-004:** Given a probe attempts undeclared filesystem, credential, process or network access, when the qualified laboratory launches or supervises it, then it denies the effect or stops and marks the attempt interrupted; unavailable containment refuses native launch; a worktree or model instruction alone never qualifies containment.

Verification: [procedure_req_004](validation-plan.md#procedure_req_004). Planned evidence only; obtained evidence: none.

### REQ-005 — Implement bounded contrastive refinement with baseline retention

**SC-005:** Given general and task-specific variants yield valid, invalid, tied or missing observations, when one configured propose-probe-compose round completes, then it records contrasts and composition, then returns candidate, keep-base, inconclusive or refused under a frozen selection policy; generating output alone never demonstrates improvement.

Verification: [procedure_req_005](validation-plan.md#procedure_req_005). Planned evidence only; obtained evidence: none.

### REQ-006 — Resume without duplicate effects or stale context

**SC-006:** Given a process stops after a durable start or checkpoint and inputs may drift, when recovery inspects the owned run, then it reconciles the exact attempt, preserves completed work, and refuses unsafe redispatch or mismatched state; recovery does not renew permissions.

Verification: [procedure_req_006](validation-plan.md#procedure_req_006). Planned evidence only; obtained evidence: none.

### REQ-007 — Enforce complete operational limits

**SC-007:** Given proposal, probing, selection, reflection, retry or cleanup approaches a frozen limit, when the supervisor admits the next step or observes exhaustion, then it reserves conservatively and refuses or stops further work; counts, wall time, process/resource usage and unknown costs remain visible; additional cash spend is capped at EUR 0.

Verification: [procedure_req_007](validation-plan.md#procedure_req_007). Planned evidence only; obtained evidence: none.

### REQ-008 — Return bounded advisory evidence

**SC-008:** Given a synthetic or native run finishes or fails, when the CLI or an eventual separately versioned read-only adapter presents its result, then it exposes identities, decisions, losses, effects, limits and obtained evidence without grants, source promotion, success fabrication or scientific acceptance.

Verification: [procedure_req_008](validation-plan.md#procedure_req_008). Planned evidence only; obtained evidence: none.

## Scientific boundaries and compatibility

Domain: Owned repository tasks, task-local guidance and selected context packaging; deterministic laboratory controls first. Arbitrary tools, scripts, hooks, policy rewrites and production source mutation are outside the initial editable surface.

Hypotheses: small contrastive harness changes may improve each target outcome at acceptable complete cost; scoped experience may transfer. Either hypothesis can fail. Correctness, declared effects and authority constraints precede optimization. No universal precision, confluence, Yang–Baxter, causal-per-edit or cost-saving guarantee is claimed. Synthetic, native, human and economic evidence remain distinct.

Existing runtime/grants, AIM, plugin, System 1, forecasting and local telemetry contracts remain unchanged. No training, model adoption, telemetry consent, FC.1 source admission or M4 utility acceptance transfers. Public interface names in the plan are proposals until versioned and reviewed.

## Evidence and unresolved questions

Obtained acceptance evidence: none. The upstream audit supports design motivation, not these acceptance scenarios. Pending decisions: exact numerical limits, supported containment backend/OS/host versions, permissioned native sources, native route feasibility, evaluation size/margins and candidate-specific promotion. Tasks order these decisions before dependent execution. See plan.md, tasks.md and assurance.json.
