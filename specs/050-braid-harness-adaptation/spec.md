# SPEC-050: Braid Harness adaptation and product lifecycle

**Milestone:** HAR.3 — Braid Harness adaptation and integration

**Status:** draft. Tasks T001–T011 are closed with offline-only implementations merged and T012 is open; native qualification, policy adoption and activation remain pending. `executionAuthorization` is false for every record these modules produce.

## Purpose and scope

Extend Braid Harness through versioned task-local component profiles, measured deeper/wider refinement, interaction-aware delegated workflows, governed automatic-promotion software and opt-in product lifecycle integration.

HAR.1/HAR.2 establish the bounded foundation and two-axis evidence. This milestone gives advanced capabilities explicit implementation ownership rather than leaving them as untracked future suggestions. Existing Codex/Claude and EUR 0 extra spend remain constraints (REQ-009). Deterministic engineering and native acceptance remain distinct; unsupported profiles cannot be activated.

Actors: the owner (founder), who decides and approves (owner-decisions records of 2026-11-08, 2026-11-13 and 2026-11-16, and the founder review in T012); independent model reviewers, Codex or Claude Code (D5, T012); the operator who opts in to install a profile and whose authority a promotion needs (T011, REQ-007); the human who observes workflow usability (T011, D6); and the consumers of the advisory contracts, CLI and plugin/MCP (REQ-008, T010).

Exclusions, each covered by the requirement named, and in part only where stated:

- Unsupported profiles MUST NOT be activated: REQ-001 covers refusal when the registry validates an unsupported profile. Activation of a promotion is covered by REQ-007. No requirement defines activation of other profile classes (see Open questions).
- Spend beyond the reused ceilings and EUR 0 MUST NOT occur: REQ-009.
- Canonical authorities, existing runtime grants, provider permissions and global host configuration MUST NOT change, and existing plugin, telemetry, forecasting and System 1 acceptance MUST NOT widen: REQ-010.
- A new task-local executable or tool-loop profile MUST NOT run without an adopted effect contract and actual containment qualification: REQ-002 covers executable content running only in separately qualified containment; no requirement covers the adopted effect contract (see Open questions).
- Native promotion MUST NOT activate without a separately adopted exact policy and operator authority: REQ-007.
- Syntactic validation, a simulated sandbox, model confidence or issue closure MUST NOT be taken as proof of semantic safety: REQ-003 covers syntax validity for hook and plugin effects only; the rest is a scientific boundary below.

## Authorities

Constitution clause zero and Articles 1, 2, 3, 5, 6, 7, 9, 12, 13, 14, 15, 19, 20, 21, 23, 24, 25; GOVERNANCE.md; operational semantics; claim discipline; accepted ADRs 0019/0020 and applicable proposed ADRs 0021/0024/0025. The feature-local ADR proposal changes no canonical authority.

## Requirements and acceptance scenarios

### REQ-001 — Version bounded component profiles

**SC-001:** Given a proposed profile includes guidance, memory, skills, tools, hooks, delegated roles or plugins, when the component registry validates imports and host compatibility, then it checks versioned path/content/effect limits, approved host capabilities and immutable protected layers; unsupported profiles refuse and local rules cannot weaken governance.

Verification: [procedure_req_001](validation-plan.md#procedure_req_001). Planned evidence only; obtained evidence: none.

### REQ-002 — Support on-demand skills and qualified helpers

**SC-002:** Given a candidate defines reusable skills, tool guidance or executable helpers, when the loader validates and exposes the selected components, then it validates triggers, references, lazy context budgets, source licenses and helper effect profiles; executable content runs only in separately qualified containment and never from prompt permission alone.

Verification: [procedure_req_002](validation-plan.md#procedure_req_002). Planned evidence only; obtained evidence: none.

### REQ-003 — Constrain tool-loop hooks and plugin components

**SC-003:** Given a hook or plugin subscribes to an event or proposes a tool-loop change, when the host adapter installs a task-local experimental component, then it validates event schema, ordering, bounded effects and cancellation, denies recursive privilege expansion and cleans up on failure; syntax validity alone cannot qualify effects.

Verification: [procedure_req_003](validation-plan.md#procedure_req_003). Planned evidence only; obtained evidence: none.

### REQ-004 — Use interaction-aware delegated workflows

**SC-004:** Given candidate roles or coordination policies change how work is delegated or combined, when the planner prepares a bounded workflow, then it binds inputs, handoffs, dependencies and effects, preserves serial-reference correctness and refuses unknown unsafe interactions; role text never grants concurrency or permissions.

Verification: [procedure_req_004](validation-plan.md#procedure_req_004). Planned evidence only; obtained evidence: none.

### REQ-005 — Scale refinement within measured limits

**SC-005:** Given registered sequential-depth or parallel-width variants compete with one-round refinement, when the search controller expands an admitted trial graph, then it reserves all stage/session costs, records lineage, retries and keep-base decisions, honors cancellation and identity-bound cache reuse, and measures marginal utility rather than rewarding search volume.

Verification: [procedure_req_005](validation-plan.md#procedure_req_005). Planned evidence only; obtained evidence: none.

### REQ-006 — Curate experience and context under drift

**SC-006:** Given a reusable lesson or context profile becomes stale, contradictory, oversized or inapplicable, when the curator retrieves, compacts or revalidates it, then it preserves supporting/contrary provenance and temporal filters, expires or quarantines drifted entries and tests negative transfer without rewriting the historical evidence.

Verification: [procedure_req_006](validation-plan.md#procedure_req_006). Planned evidence only; obtained evidence: none.

### REQ-007 — Implement separately governed automatic promotion

**SC-007:** Given an offline automatic-policy proposal and candidate decision inputs exist, when the disabled-by-default policy engine runs shadow/canary evaluation, then it abstains on missing evidence, scope drift or unknown costs, exercises rollback and incident stops, and cannot activate native promotion without a separately adopted exact policy and operator authority.

Verification: [procedure_req_007](validation-plan.md#procedure_req_007). Planned evidence only; obtained evidence: none.

### REQ-008 — Integrate and operate an opt-in product capability

**SC-008:** Given a reviewed profile is exposed to CLI or a separately versioned plugin/MCP consumer, when installation, migration, operation, drift or uninstall occurs, then it uses explicit workspace/profile binding, compatibility checks, private export controls, canary/rollback and revocation, and preserves a usable previous profile; planning or synthetic checks never imply native product acceptance.

Verification: [procedure_req_008](validation-plan.md#procedure_req_008). Planned evidence only; obtained evidence: none.

### REQ-009 — Keep native effort within the reused cost ceilings

**SC-009 (spec only, see OQ-15):** Given a native unit or cohort is admitted under any profile, when it runs, then every unit MUST stay within 30 minutes of wall time, every session within 10 % of the 5-hour quota window and the cohort within 15 % of the weekly quota window, and the work MUST NOT incur additional cash beyond EUR 0; the further limits (cohort size, stop rule) are in [contracts/interface.md](contracts/interface.md) section 6.

Verification: [procedure_req_009](validation-plan.md#procedure_req_009). Planned evidence only; obtained evidence: none. Source: owner decision 3 of 2026-11-08.

### REQ-010 — Do not widen existing authority

**SC-010 (spec only, see OQ-15):** Given a component profile is compiled, installed, migrated or operated, when the work completes or refuses, then canonical authorities, existing runtime grants, provider permissions and global host configuration MUST remain unchanged, and existing plugin, telemetry, forecasting and System 1 acceptance MUST NOT widen.

Verification: [procedure_req_010](validation-plan.md#procedure_req_010). Planned evidence only; obtained evidence: none.

## Scientific boundaries and compatibility

Deeper search, reusable workflows and automatic selection may fail to improve either primary axis. Registered equal-budget comparisons and complete costs must precede useful-native or economic claims. No generic model confidence, syntactic validation, simulated sandbox or issue closure proves semantic safety.

Canonical authorities, existing runtime grants, provider permissions and global host configuration remain immutable (REQ-010). A new task-local executable or tool-loop profile requires an adopted effect contract and actual containment qualification. This spec cannot widen existing plugin, telemetry, forecasting or System 1 acceptance (REQ-010).

## Evidence and unresolved decisions

Obtained acceptance evidence: none recorded in `assurance.json` for any scenario. Offline task evidence exists: merged modules and tests for T001–T011, `evidence/t004.json`, `evidence/t009.json` to `evidence/t012.json`, `evidence/integration/portfolio-20261112.json` and the independent model review record `evidence/review/gpt6-d5-20261124.json`. It supports implemented-offline claims only; none of it qualifies or activates a profile. Per-profile feasibility, supported host/OS/builds, admission limits, native source yield and future automatic-policy adoption remain pending and ordered in tasks.md. Capability closure requires implemented and reviewed scope; a no-go assessment leaves blocked implementation tasks visible.

Open questions: see the section of that name below.

## Owner decisions

Decided. The chosen answers are in the owner decision records in this folder, which state the option chosen for each point; the options offered for E1 are in [effect-contract-decision.md](effect-contract-decision.md), and for the other points the records restate the chosen option only. None of these decisions authorizes native execution, adopts an ADR or activates anything.

- 2026-11-08 ([owner-decisions-20261108.md](owner-decisions-20261108.md)): freeze the T001 contract now with SPEC-049/T005 open; the feature-local ADR stays a proposal; the SPEC-049 D2 caps are reused for every profile; hooks, plugins/tool loops and delegated roles are blocked from the start.
- 2026-11-13 ([owner-decisions-20261113.md](owner-decisions-20261113.md)): D1 tolerate no pending endpoints; D2 native chain, amended the same day to start now; D3 no top-level alias and T010 closed; D4 lifecycle retention is 30 days; D5 independent review over the merged offline portfolio; D6 usability observation after the native wave; D7 activation policy and ADR when SPEC-049/T014 has results.
- 2026-11-16 ([owner-decisions-20261116.md](owner-decisions-20261116.md)): E1 E3 effect contract drafted and the adapter implemented against deterministic doubles; E2 read-only MCP contract specified under its own spec and published only if D7 does not close the harness as experimental; E3 Codex reviews and verifies through repository packets, native Codex qualification becomes tasks in a later milestone.
- 2026-11-23 ([evidence/t004.json](evidence/t004.json)): T004 closed offline-only; the native remainder moved to SPEC-084/T015.
- D7 was applied by SPEC-049 T007: the harness stays experimental and nothing is promoted ([evaluation report](../049-harness-evaluation-learning/evaluation-report.md)).
- 2026-11-26 ([evidence/owner-decisions-20261126.md](evidence/owner-decisions-20261126.md)): REQ-009 and REQ-010 added; independent model review stays required, by a Codex or Claude Code model.

## Open questions

Each is unresolved and owned by the founder unless another owner is named.

- OQ-1 (REQ-002, REQ-003): should the adopted effect contract for a new executable or tool-loop profile have its own requirement? Today only the qualified-containment half is covered.
- OQ-2 (REQ-001): should activation of a non-promotion profile have a requirement? Today REQ-001 covers refusal at validation only.
- OQ-3 (D5, T012): the delta review after the native evidence is pending; the 2026-11-24 review by a Codex-run GPT-6 model was obtained instead of Luna and covered the merged offline portfolio at e79b33b0. Owner: founder, to confirm that it meets D5 as amended on 2026-11-26.
- OQ-4 (T012): human review and founder approval of the portfolio are pending.
- OQ-5 (T011, D6): the human usability observation is pending; the 2026-11-23 record schedules it after alpha.10 with the SPEC-080 `harness` skill, about 20–30 guided minutes.
- OQ-6 (T004, E1): adoption of the contract section 13 E3 draft, a SPEC-065 re-qualification that pins the helpers and one contained helper run. Owner: SPEC-084/T015.
- OQ-7 (T005): the observed hook and event schemas per host build (contract section 12, question 3); the current matrices are placeholders.
- OQ-8 (C3, C8): the pinned hash for `core/prompts.py` and the fit review of `core/proposer.py` (contract section 12, question 4).
- OQ-9 (REQ-002): per-class CPU, RSS and disk caps for E3 helpers, which need a qualified containment (contract section 12, question 2).
- OQ-10 (T001): ADR numbering at adoption, because the proposal's "next available" note is out of date (contract section 12, question 5).
- OQ-11 (REQ-009, REQ-005): owner approval of the module-local limits that are provisional: maxOps 64, timeoutMs 10000, input 16 KiB and writes 256 KiB (T004); MAX_ROLES 8 and the 256 KiB artifact ceiling (T006); search ceilings of depth 1 and width 1 (T007, contract section 6).
- OQ-12 (D1, T009): the revisit of tolerating pending endpoints, which D1 ties to SPEC-049/T014 measuring them; T009 still abstains with `pending-endpoints`.
- OQ-13 (REQ-008, E2): whether the read-only MCP contract is published, given that D7 was applied and the harness stays experimental.
- OQ-14 (E3): native Codex qualification tasks in a later milestone.
- OQ-15 (REQ-009, REQ-010): no task carries their tags, so no task owns their verification yet, and `assurance.json` holds no SC-009 or SC-010: its bytes are bound to the preserved public draft candidate and a changed record does not inherit that validation route (SPEC_KIT.md, "Assurance record"). Adding the scenarios needs a separately reviewed re-snapshot of the record. Owner: orchestrator with the founder.
- OQ-16: no performance or availability requirement is recorded in this spec.

## Non-functional requirements

The recorded operational constraints are REQ-009 (native time, quota and cash ceilings) and REQ-010 (no widening of existing authority). Context budgets for lazy loading are stated in REQ-002 and bounded costs in REQ-005. The numeric module limits and the search ceilings are provisional, see OQ-11. No performance or availability requirement is recorded, see OQ-16.

## Security and privacy

- Private export controls for lifecycle and CLI operation: REQ-008.
- Executable content runs only in separately qualified containment, never from prompt permission alone: REQ-002.
- Hooks and plugins deny recursive privilege expansion: REQ-003.
- Existing grants, provider permissions and global host configuration stay unchanged: REQ-010.
- Retention of lifecycle records is 30 days, followed by a human purge that keeps the digest receipt (D4, T011). REQ-008 names private export controls but no retention requirement, so D4 is not covered by a requirement.

## Terminology

Shared terms follow `TERMINOLOGY.md`. Glossary of terms this spec introduces:

- Component profile: a versioned task-local inventory of guidance, memory, skills, tools, hooks, delegated roles or plugins (REQ-001).
- Protected layer: an immutable layer that local rules cannot weaken (REQ-001).
- Serial reference: the serial execution against which delegated workflows are checked (REQ-004).
- Keep-base decision: a recorded decision to keep the base instead of a variant (REQ-005).
- Admission state: the per-class, host and profile-version state recorded by the contract (T001).
- `executionAuthorization`: the record field that is false for advice and for every record these modules produce (T010, T011).

Values named in this spec:

- Component kinds named in REQ-001: guidance, memory, skills, tools, hooks, delegated roles, plugins. The contract inventories classes C1 to C10 (contract section 3).
- Admission states named in T001 and contract section 2: implemented, qualified, enabled, blocked, excluded.
- Effect classes of contract section 7: E0, E1, E2, E3, E4.
- Refinement variants named in REQ-005: sequential-depth, parallel-width, one-round.
- Drift states named in REQ-006: stale, contradictory, oversized, inapplicable.
- Promotion evaluation states named in REQ-007: shadow, canary; T009 adds disabled and stopped, and `active` is unreachable.
- Product consumers named in REQ-008: CLI, plugin/MCP.
- Lifecycle events named in REQ-008: installation, migration, operation, drift, uninstall.
- Hosts: `claude` is supported; `codex` is refused for task-local components because it is not installed (T002, T005).
- Dispositions seen in evidence, not a closed list: `offline-only` (T004), `implemented-offline-not-activated` (T011), `validated-offline-with-explicit-gaps` (T012).

## Risks

- Risk: deeper search, reusable workflows and automatic selection may fail to improve either primary axis (REQ-005, REQ-007).
- Risk: source yield and hidden provider revisions limit inference (REQ-005).
- Risk: structural tests are not semantic or human approval (REQ-008).
- Risk: an internally consistent forged report is not detected by the promotion engine, and actor, checker, ledgers, spend, incident flag and tick are caller-asserted (REQ-007, T009).
- Risk: the trust registry is hygiene on self-asserted ids, cue conflict is normalized-string only and held-out lists are caller-declared, so the temporal comparison is synthetic (REQ-006, T008).
- Risk: the host event matrices are placeholders modeled but not observed (REQ-003, T005).
- Risk: the SPEC-065 qualification covers one host build and needs requalification when the build changes (REQ-008).

## Assumptions

- Assumption: sources are owner-controlled and hosts are qualified local hosts only (REQ-001, REQ-002).
- Assumption: authorities are immutable and policies are frozen (REQ-001, REQ-010).
- Assumption: no provider permission, containment support or positive utility is inferred (REQ-002, REQ-005, REQ-008).

## Exit criteria

Verification is complete when each of procedure_req_001 to procedure_req_010 in the [validation plan](validation-plan.md) has obtained evidence, passing or failing, recorded against its task in [tasks.md](tasks.md), and T012 is closed. T012 closes when its acceptance in tasks.md is met and these are recorded: the delta independent model review after the native evidence, human review and founder approval of the portfolio, the human usability observation (D6) and a stable `pr`-profile result. A negative, inconclusive or infeasible result completes verification as a finding and leaves blocked implementation tasks visible; it does not close a task by relabeling.
