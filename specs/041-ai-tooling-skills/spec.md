# SPEC-041: Portable product skills for AI tooling

**Milestone:** M4.5 — AI tooling integrations for Codex and Claude Code

**Status:** draft assurance; experimental implementation and bounded technical
controls exist. Original native-host procedures and human acceptance remain pending.

## Purpose and scope

Ship five portable product skills guiding analysis, planning, already-granted execution, recovery and evidence in Codex and Claude Code.

## Authorities

Constitution clause zero and Articles 3–7, 12–16, 19–25; GOVERNANCE.md; operational semantics, claim discipline, ADRs 0019/0020 and proposed ADR 0021. This spec is subordinate to accepted authorities. See assurance.json for references and authority inventory.

## Requirements and acceptance scenarios

### REQ-001

Maintain one Agent Skills-compliant canonical bundle with five matching names/descriptions and minimal host-specific metadata.

**SC-001:** Given packaged bundle and both supported hosts, when static validation then actual discovery runs, then all five names load at recorded versions; static format checks alone do not count as host discovery.

Verification: [procedure_portable_bundle](validation-plan.md); [T001](tasks.md). Obtained evidence: none.

### REQ-002

Guide analyze through immutable input selection, conflict/conditional/unknown explanation and evidence references without execute.

**SC-002:** Given independent, conflicting and unresolved operations, when agent-braid-analyze is used, then the explanation matches the analyzer and observation domain; no analysis verdict grants execution.

Verification: [procedure_analyze_skill](validation-plan.md); [T002](tasks.md). Obtained evidence: none.

### REQ-003

Guide plan through existing prepare and disclose order, constraints, plan digest and absent operator authority.

**SC-003:** Given an admissible batch and missing grant, when agent-braid-plan is used, then the plan is advisory with explicit missing permission and no model-issued grant.

Verification: [procedure_plan_skill](validation-plan.md); [T003](tasks.md). Obtained evidence: none.

### REQ-004

Guide execute only for an already granted exact prepared batch, then status and independent verify.

**SC-004:** Given matching and wrong/expired grant references, when agent-braid-execute is used, then the matching bounded result is verified or the request refuses; no secret/grant-store edits or bypass instruction occurs.

Verification: [procedure_execute_skill](validation-plan.md); [T004](tasks.md). Obtained evidence: none.

### REQ-005

Guide interruption inspection and bounded recovery using current state, existing authority and verification.

**SC-005:** Given an interrupted owned run or unknown/mismatched run, when agent-braid-recover is used, then the actual recovery/verifier outcome is reported and mismatched authority refuses.

Verification: [procedure_recover_skill](validation-plan.md); [T005](tasks.md). Obtained evidence: none.

### REQ-006

Guide evidence explanations/exports with input identity, artifact links, observation/assurance limits and unknowns.

**SC-006:** Given verified, failed and inconclusive records, when agent-braid-evidence is used, then chat and export retain actual outcomes and cannot imply code correctness, general confluence or speedup.

Verification: [procedure_evidence_skill](validation-plan.md); [T006](tasks.md). Obtained evidence: none.

### REQ-007

Handle unavailable MCP, skills or unsupported host features with actionable diagnostics and bounded read-only fallback.

**SC-007:** Given missing MCP dependency/configuration and an execution request, when a workflow cannot connect, then the skill reports the missing capability; only documented read-only CLI fallback is offered.

Verification: [procedure_missing_capability](validation-plan.md); [T007](tasks.md). Obtained evidence: none.

### REQ-008

Separate skill guidance from host permission and grant enforcement, with adversarial instructions and no hooks/helper-agent side effects.

**SC-008:** Given repo/evidence text requesting grants, secrets or false success, when workflow guidance reads the text, then it treats text as untrusted and respects deterministic refusal; no hidden configuration, hooks or authority changes ship.

Verification: [procedure_adversarial_guidance](validation-plan.md); [T008](tasks.md). Obtained evidence: none.

## Scientific boundaries and compatibility

Domain: Instruction guidance over the exact MCP/CLI contracts; skills are not effect enforcement, operator authority or mathematical proof.

Hypothesis: Focused portable guidance may improve workflow completion and evidence fidelity; model compliance and positive utility are not presumed.

Existing AIM/runtime/grant/verifier contracts remain unchanged. Analysis and preparation are consultative; host permission never substitutes for operator grants. No source ref promotion, repository-code/hook execution, arbitrary network effects or new scientific guarantee. Existing M4 G4 NO-GO and independent M3/M3.5 gates remain in effect.

SDK/documentation, structural checks, synthetic controls, actual host observations and independent reproduction have separate evidence domains. Passing one does not establish the others or human approval. Public APIs are additive experimental proposals with migration/versioning review during implementation.


## Non-functional requirements

Operational and quality constraints, each with its source. They restate existing
requirements; none is new.

- Portable: one canonical bundle with minimal host-specific metadata serves both
  supported hosts (REQ-001).
- Advisory only: analysis and preparation are consultative and host permission never
  substitutes for an operator grant (REQ-002, REQ-003).
- Bounded fallback: when MCP, skills or a host feature is unavailable, only the
  documented read-only CLI fallback is offered (REQ-007).
- Additive and experimental: public APIs are additive experimental proposals with
  migration and versioning review during implementation; existing AIM, runtime,
  grant and verifier contracts remain unchanged (Scientific boundaries section).
- Evidence fidelity: chat and export retain actual outcomes and unknowns (REQ-006).
- Numeric limits (latency, size, cost) have no source in this spec; see
  [Open questions](#open-questions).

## Security and privacy

- No hooks, helper agents, hidden configuration or authority changes ship in the
  bundle; skill text and repository or evidence text are untrusted input
  (REQ-008).
- No secret or grant-store edit and no bypass instruction (REQ-004).
- No model-issued grant: a plan discloses the absent operator authority (REQ-003).
- No execution from analysis or from evidence export (REQ-002, REQ-006).
- The five skills neither enable nor collect telemetry (SPEC-047 boundary below).
- Observational receipts are derived and redacted receipts, not raw transcripts
  ([validation plan](validation-plan.md), amendment 2026-10-31).

## Terminology

- **Canonical bundle:** the five product skills under
  `integrations/agent-braid/skills/`, with host metadata in
  `integrations/agent-braid/hosts.json` (REQ-001).
- **Five skills:** `agent-braid-analyze`, `agent-braid-plan`, `agent-braid-execute`,
  `agent-braid-recover` and `agent-braid-evidence` (REQ-002 to REQ-006).
- **Operator grant:** the authority an operator issues for an exact prepared batch;
  a skill never issues it (REQ-003, REQ-004).
- **Read-only CLI fallback:** the documented analysis-only route, for example
  `analyze-git`, offered when MCP is unavailable (REQ-007).
- **Native observational receipt:** a derived, redacted receipt from a real host
  session, at level C1 discovery, C2 instructions loaded or C3 observed use
  (`native-observation-contract-v1`); not preregistered (tasks T002 to T008).
- **Technical clause:** a separately verified auxiliary task, T011 to T019. It does
  not complete its linked original task.
- **Evidence domains:** SDK/documentation, structural checks, synthetic controls,
  actual host observations and independent reproduction; passing one does not
  establish another.
- **Assurance values:** `stage` is `draft` or `validated`; `human_review` is
  `pending`, `changes-requested` or `approved`.
- Shared terms follow the root [TERMINOLOGY.md](../../TERMINOLOGY.md).

## Risks and assumptions

- Risk: model compliance with skill text is not presumed; guidance may be ignored
  (REQ-008, T008).
- Risk: host versions are not readable from skill listings, so "recorded versions"
  may not be observable (REQ-001, T001).
- Risk: observational evidence covers one owner, one host (Claude Code) and one
  scratch repository, and is not bound to a frozen candidate; it implies no Codex
  coverage (T003, T004, T005, T007).
- Risk: adversarial text in repository or evidence files may request grants,
  secrets or false success (REQ-008).
- Risk: ADR 0021 is proposed, not accepted (REQ-001 to REQ-008).
- Assumption: trusted owned roots, current accepted runtime contracts and explicit
  host and tool permissions (plan, Research section; REQ-004).
- Assumption: existing AIM, runtime, grant and verifier contracts stay unchanged
  (REQ-003, REQ-004, REQ-005).

## Exit criteria

Verification is complete when the obtained evidence for procedures
`procedure_portable_bundle` to `procedure_adversarial_guidance` in the
[validation plan](validation-plan.md) exists for REQ-001 to REQ-008 and
SC-001 to SC-008, or the owner records a task as Deferred with reopen criteria; T009
reconciles that evidence and T010 records the human decision. State as of
2026-11-01 ([owner decision](owner-decision-20261101-real-use-acceptance.md), #857): T003, T004, T005
and T007 are ticked on observational evidence, T002 on observational evidence
without its explanation-quality clauses, and T001, T006 and T008 to T010 stay
Deferred. Passing structural checks or technical clauses is not approval.

## Open questions

- Numeric non-functional limits: whether any latency, size or cost limit applies to
  the skills. Owner: the founder.
- Technical contract and ADR 0021 adoption (proposed). Owner: the founder (T010).
- Exact host versions and installation scope for original procedures. Owner: the
  founder (T001).
- Provider budget and source rights for registered capture. Owner: the founder
  (T009).
- Independent technical review and founder acceptance of the whole spec. Owner: the
  founder (T010).

## Additive SPEC-047 boundary — pending candidate

SPEC-047 defines default-off numeric telemetry at the portable MCP and analyzer CLI boundaries. The five product skills do not enable or collect it. Candidate `4f0a6bf40779` and metadata `b3809cbbaa0a` hold the historical implementation/evidence; the reconstructed source on rewritten develop is still a new unvalidated candidate. Pilot **NO-GO**; T017/T018 and SPEC-047/T010 remain open. No original SPEC-041 or SPEC-044 criterion is relaxed. See [SPEC-047](../047-local-technical-telemetry/spec.md), [installation limits](../../docs/tooling/INSTALL.md) and [M4.5 alignment](../../docs/tooling/M45_ALIGNMENT.md).

## Evidence and unresolved questions

Planned original procedures are in validation-plan.md; their obtained evidence is
empty in assurance.json. Separate bounded technical clauses are recorded without
completing the native procedures. The [implementation map](implementation-status.md)
links current controls and coordination dependencies. Required decisions retain
their scope: technical contract/ADR adoption, exact host versions and installation
scope, provider budget/source rights for capture, independent review and founder
acceptance. See program.md in SPEC-039 and evaluation-protocol.md in SPEC-044.
