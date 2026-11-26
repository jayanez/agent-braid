# SPEC-048: Braid Harness variants and isolated probing

**Milestone:** HAR.1 — Braid Harness laboratory

**Status:** draft; owner confirmed planning direction on 2026-10-20. All 15 tasks are done (2026-11-21): the offline laboratory is implemented and reviewed, and T008 closed on 2026-11-20 with the Claude profile qualified with limits (founder T008-11) through SPEC-065; Codex native qualification is not done. Human acceptance of the feature remains pending.

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

### REQ-009 — Build bounded trusted context

**SC-009:** Given authorized context entries include hostile text, large histories, stale facts or hidden grading material, when the context builder selects and packages evidence for a trial, then it includes only eligible trusted-inventory entries within frozen budgets, labels untrusted text and every truncation/omission, and excludes held-out graders without widening read access.

Verification: [procedure_req_009](validation-plan.md#procedure_req_009). Planned evidence only; obtained evidence: none.

### REQ-010 — Capture inspectable private observations

**SC-010:** Given a fixture or qualified host yields complete, missing, sensitive or malformed events and artifacts, when the observer creates or exports a trajectory/evidence package, then it binds raw/normalized identities, records event loss and unknown effects, verifies redaction/retention and preserves terminal failures; unobservable outcomes cannot become completed success.

Verification: [procedure_req_010](validation-plan.md#procedure_req_010). Planned evidence only; obtained evidence: none.

## Scientific boundaries and compatibility

Domain: Owned repository tasks, task-local guidance and selected context packaging; deterministic laboratory controls first. Arbitrary tools, scripts, hooks, policy rewrites and production source mutation are outside the initial editable surface.

Hypotheses: small contrastive harness changes may improve each target outcome at acceptable complete cost; scoped experience may transfer. Either hypothesis can fail. Correctness, declared effects and authority constraints precede optimization. No universal precision, confluence, Yang–Baxter, causal-per-edit or cost-saving guarantee is claimed. Synthetic, native, human and economic evidence remain distinct.

Existing runtime/grants, AIM, plugin, System 1, forecasting and local telemetry contracts remain unchanged. No training, model adoption, telemetry consent, FC.1 source admission or M4 utility acceptance transfers. Public interface names in the plan are proposals until versioned and reviewed.

## Evidence and unresolved questions

Obtained acceptance evidence: none. The upstream audit supports design motivation, not these acceptance scenarios. Decided: the offline profile limits (`offline-adoption.json`), the native caps (`evidence/founder-decisions-20261106.json` D2, carried to `founder-decisions-20261120.json`) and the Claude host and containment (SPEC-065 issuance of 2026-11-17, Claude 2.1.292, Haiku, subscription route, EUR 0; T008-11). Still pending: full-feature limits, Codex containment, host and native route, later permissioned native sources, evaluation size and margins, and candidate-specific promotion. Tasks order these decisions before dependent execution. Open questions: see [Open questions](#open-questions). See plan.md, tasks.md and assurance.json.

## Non-functional requirements

The recorded operational constraints are in REQ-007 (frozen limits, visible counts, wall time, process and resource usage, additional cash spend capped at EUR 0), REQ-006 (resume without duplicate effects) and REQ-009 (frozen context budgets). The offline profile is frozen in `offline-adoption.json` (native, model, child, network and retry counts 0, extra cash 0 EUR, admission maximum 300 seconds). The native caps are frozen in `evidence/founder-decisions-20261106.json` D2 (30 minutes per unit, at most 10% of the 5-hour window, at most 15% weekly, stop when weekly use exceeds 80%, EUR 0). Limits for the full feature are not fixed, see OQ-1. No performance or availability requirement is recorded, see OQ-2.

## Security and privacy

- Protected layers and executable content stay outside the editable surface: REQ-001.
- Candidate admission is operator-scoped and no existing runtime grant is widened: REQ-003.
- Undeclared filesystem, credential, process or network access is denied or stopped: REQ-004.
- Hidden grading material is excluded from context and untrusted text is labeled: REQ-009.
- Observations are redacted before export and unobservable outcomes cannot become success: REQ-010.
- Retention of private observations has no stated period or purge rule, see OQ-3.

## Terminology

Shared terms follow `TERMINOLOGY.md`. Glossary of terms this spec introduces:

- Base: the immutable starting harness against which variants are compared (REQ-001, REQ-002).
- Candidate: a proposed task-local harness variant (REQ-001, REQ-003).
- Probe: one isolated trial of a candidate (REQ-004, REQ-005).
- Keep-base: the decision to retain the base instead of a candidate (REQ-005).
- Laboratory admission: the operator-adopted, independently enforced envelope that lets a probe run (REQ-003).

Values named in this spec:

- Round outcomes (REQ-005): candidate, keep-base, inconclusive, refused.
- Evidence classes (Scientific boundaries): synthetic, native, human, economic.
- Hosts (Purpose and scope): Codex and Claude, each through a separately qualified adapter.

## Risks and assumptions

- Risk: small contrastive harness changes may not improve either primary outcome at acceptable complete cost (REQ-005).
- Risk: unknown provider build identity can be mistaken for a pinned build (REQ-002).
- Risk: worktree or model instruction alone could be mistaken for containment (REQ-004).
- Risk: unobservable outcomes could be recorded as completed success (REQ-010).
- Assumption: the Claude profile is qualified with limits through SPEC-065 and Codex native qualification is not done (REQ-004, T008).
- Assumption: existing runtime, AIM, plugin, System 1, forecasting and telemetry contracts stay unchanged, as stated in Scientific boundaries and compatibility; REQ-003 covers grants only (REQ-003).

## Exit criteria

Verification is complete when each of procedure_req_001 to procedure_req_010 in the [validation plan](validation-plan.md) has obtained evidence, passing or failing, recorded against its task in [tasks.md](tasks.md). Human acceptance of the feature stays pending. T008 closed with Codex refused, as its acceptance allows (OQ-6). A negative, inconclusive or infeasible result completes verification as a finding.

## Open questions

Each is unresolved and owned by the founder. Owner answers of 2026-11-26 are in [evidence/owner-decisions-20261126.md](evidence/owner-decisions-20261126.md).

- OQ-1 (REQ-007, REQ-004, REQ-005): what limits apply to the full feature beyond the offline profile and the native caps already decided, what are the Codex containment backend, OS and host versions, and what are the evaluation size and margins (also SPEC-049)?
- OQ-2: does this feature need a performance or availability requirement? None is recorded.
- OQ-3 (REQ-010): what retention period and purge rule apply to private observations, and does it need its own MUST requirement? `assurance.json` is bound to a preserved public draft tag, so a new requirement needs a separately reviewed re-snapshot.
- OQ-4 (REQ-003, REQ-004): which later permissioned native sources apply, and is Codex route feasibility pursued? The Claude route is decided (subscription only, EUR 0, T008-11 in `evidence/founder-decisions-20261120.json`) and Codex is refused and not installed.
- OQ-5 (REQ-005): what candidate-specific promotion decision applies?
- OQ-6 (T008): does HAR.1 acceptance need Codex qualification, given T008 closed with Codex refused?
