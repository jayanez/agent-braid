# Implementation plan — SPEC-058

Status: draft plan. Planning is not permission to implement or deliver. **SPEC-058 must be implemented as an unreleased engineering candidate (behind the G1 gate) before arm A3 can run; adoption or release happens only after G1 gate GG passes and the ADR is adopted** ([adr-proposal.md](adr-proposal.md); decided 2026-10-24: reviewed now, adopted with the G1 outcome). Candidate work starts only after the SPEC-057 policy-profile schema increment (I-3) has merged and the founder has recorded a review disposition of the ADR proposal; the candidate is not packaged, listed or published. Nothing in this plan freezes, signs, approves, installs or runs a hook, workflow, session or team, spends money, publishes or creates a remote issue. `obtained_evidence` in `assurance.json` is empty and human review is pending.

## Technical context and scope

- Milestone: M4.6 — Claude Code dynamic workflows. Program: [SPEC-052 program](../052-claude-workflow-gate/program.md). This specification is the opt-in guard of the orchestration family decided on 2026-10-24 (SPEC-057 advisory core; SPEC-058 opt-in guard; SPEC-059 ledger and active push). It consumes SPEC-057's policy-profile schema, ownership module, settings resolver, host probes and gate G1; it does not edit them.
- Language and stack: Python 3.12+ standard library plus the pinned `requirements-speckit.txt` and `requirements-dev.txt` tooling (`jsonschema` is already pinned). Unit tests use `unittest`. The hook scripts are stdlib-only Python and import no network, socket or process-launching helper.
- Existing code relied on (read, not changed): the SPEC-057 modules once implemented (`agent_braid/ownership.py`: normalization, expansion, prefix overlap equal to `runtime_scheduler._overlap`, settings resolver, notice escaping), `agent_braid/plugin_mcp.py` and the package builder and tests (unchanged). Added first as the unreleased candidate and released only after the gates: `agent_braid/guard_policy.py` (compiler, outputs D and B, report), `agent_braid/guard_decision.py` (decision function, modes, control paths, context builder), `agent_braid/guard_liveness.py`, `agent_braid/guard_audit.py`, `agent_braid/guard_hooks.py` (hook entry points), `agent_braid/cli.py` (two additive subcommands, `compile-policy` and `report-guard`, names provisional), `integrations/agent-braid-guard/` (the companion plugin source) and `scripts/build_guard_plugin.py`.
- Out of scope, unchanged from the specification: hooks or any component in the main plugin, `allow`/`defer`/input rewriting, grants, launching or messaging, mods, push and a ledger, Bash or MCP-effect enforcement through hooks, speed claims, transcript evidence, every host other than Claude Code.
- Spend: EUR 0 additional, existing subscription, included quota only ([budget](../../docs/tooling/BUDGET.md)); stop on quota exhaustion. Probes and G1 use Sonnet at medium effort and small paired designs.

## Constitution check before research

Applicable: clause zero and Articles 1–3, 5–7, 12–15, 19–21, 23 and 25, as listed in `assurance.json`; GOVERNANCE.md, the operational semantics, claim discipline, ADRs 0014, 0021 and 0024, `docs/architecture/PARALLEL_INTEGRATION.md` and SPEC-047, 050, 052, 053 and 054.

| Authority | Obligation | How the plan honors it | Verdict |
|---|---|---|---|
| Clause zero | No assumption that commutation applies; no claim from analogy | Ownership is a declaration; the guard restricts writes and claims nothing about commutation; no braid language | No conflict |
| Art. 5 | Effects first-class; hidden effects are uncertainty | Bash, MCP effects, generated files and unattributed writers are stated as not covered in every output | No conflict |
| Art. 6 | Conditions are enforced at the point of use | The check runs at the tool call against a digest-bound envelope; partial coverage degrades the decision instead of widening it | No conflict |
| Art. 12 | Concurrency control, not only prompts | The guard is the only mechanism-class element; it is opt-in, bounded by a published coverage boundary and gated by G1; advice stays labelled communication | No conflict |
| Art. 13 | Explicit class, property, method, domain, assumptions, contracts | Every output and attestation carries the block; liveness is `advisory` unless observed; the class is a producer claim | No conflict |
| Art. 14 | Evidence, not verdicts | Audit records and reports carry decisions, would-decisions, reason codes, digests and counters | No conflict |
| Art. 15 | Vendor-neutral core | The profile is SPEC-057's vendor-neutral schema; Claude specifics live in outputs and the companion | No conflict |
| Art. 19 | Real, measurable problem | False blocks, bypass, tamper and liveness are G1 metrics; no speed claim | No conflict |
| Art. 20 | Analysis and execution separate | Nothing launches, messages, resumes or authorizes; the guard restricts only its own unit's writes | No conflict |
| ADR 0021 | Grants never model-callable; host approval is not runtime authority | No grant member; `allow` and `defer` unreachable so the guard cannot widen host permission | No conflict |
| ADR 0024 | No installation or session hooks ship | The main plugin is untouched; hooks live only in a separate opt-in companion. The unreleased candidate ships nothing (not packaged, listed or published); a package or release needs the ADR proposal's amendment, adopted with the G1 outcome | Conflict resolved for release only by the adopted proposal; the candidate does not ship |
| AGENTS.md | No command authorizes concurrent agents or autonomous delivery | No Agent Braid code launches, messages as, resumes or authorizes anything; probes and G1 runs are launched by the orchestrating session only after the founder authorizes each one (decided 2026-10-24); no task here is a standing authorization | No conflict, with the per-probe authorization recorded |
| Claim discipline | Labels and bounded wording | Matrix evidence statuses; wording lint; "no surveyed shipped plugin found" only | No conflict |

The ADR 0024 row is the one real conflict: the specification cannot be packaged or released while the "no installation or session hooks ship" wording stands, which is exactly why package build and release are blocked by the ADR proposal and not resolved by this specification. An unreleased candidate that the founder installs locally for the G1 arms ships nothing.

## Research, assumptions and alternatives

[research.md](research.md) records the sources, how they were read, the decisions below and the critical review's weak claims. Decisions that shape the design:

- **RS-1 One compiler, three outputs, no hooks in the main plugin.** Output C is rejected by the founder and is unrepresentable.
- **RS-2 Ownership is an allowlist; permissions are a denylist.** Output D denies the others' paths and the control paths and lists the unit's envelope in the sandbox write allowlist, whose semantics (additive versus restrictive) are unconfirmed until GP-5 or HV-8; no OS-level bound is claimed; the lists are operator-supplied host configuration, not Agent Braid authority and not a grant.
- **RS-3 Allow is unreachable.** A positive `PreToolUse` decision can skip the permission prompt; the guard only adds restriction or context.
- **RS-4 Fail open is a fact to report, not to hide.** Decided: an internal error or timeout is no-opinion, recorded, and degrades a liveness attestation that defaults to advisory; `ask` is kept only for undecidable paths in `block` until GP-2.
- **RS-5 Tamper protection is bounded.** A Write/Edit guard protects control paths against Write/Edit only; Bash needs output D.
- **RS-6 Audit first.** The default when enabled is `audit`, which records would-have-blocked and changes nothing; `block` is never default.
- **RS-7 No natural-language parsing.** The task check reads a structured marker only.
- **RS-8 No model-controlled path arguments.** The hook never calls a checker with tool-call strings.
- **RS-9 Whisper.** The default strategy Mailbox + Whisper puts a bounded, escaped `additionalContext` from a validated pull notice into the affected agent's own session; context only, in `warn` and `block`. It forwards no sibling-written path text (unit ids, hazard kinds, a path count, digests and at most 4 own declared paths), because escaping does not neutralise semantic prompt injection; the remaining routes are a stated residual risk.
- **RS-10 Candidate before arm A3.** The unreleased engineering candidate is the artifact G1 evaluates (not a throwaway script); the gate governs release.

Alternatives rejected: hooks inside the main plugin (founder decision; ADR 0024); mods (`agent.spawn`, `tool.call`) as the enforcement route (a larger trust expansion); a fail-closed default (a deny without an actionable reason is a false block by construction); a `PostToolUse` observer using `bashEditDiff` now (documented as best-effort and not for enforcement; not now, agent teams decided with the ledger after HV-L7); a general hook-profile compiler (HAR.3 T005); a ledger-backed guard (needs G2); an `allow` decision for in-envelope writes (would skip the permission prompt).

## Design and compatibility

### Data flow

Declaration (SPEC-057) → expansion (SPEC-057) → `compile-policy`: profile validated against the SPEC-057 schema, envelope digest computed, control paths added, outputs D/A/B rendered to explicit new private paths → the operator applies the output (installs the companion, supplies the settings document or pastes the snippet) → at run time the hook reads the operator-owned profile and envelope (bounded), decides purely, writes one content-free audit record and returns one of four words → at a SPEC-057 quiescent checkpoint `report-guard` correlates the audit record and the receipt to give bypass observations and liveness.

### The guard decision function

A pure function of (mode, event, path situation, agent identity situation, envelope digest state). The path situation is computed with the SPEC-057 normalization and prefix rule: `in-envelope`, `outside-envelope`, `control-path` or `undecidable-path` (symlink resolution failure, path outside the repository, a partial envelope entry). The decision table is in the [contracts README](contracts/README.md) and is pinned by the conformance vectors. The effective mode comes from the SPEC-057 resolver (most specific scope wins; a `block` at repository or user scope is a floor) with the compiled profile mode as the lowest-precedence default, pinned by the mode-resolution vectors. Identity: `agent_id` maps to a unit through the profile; an unmapped identity on a shared tree is `unattributed-writer` and never blocked.

### Output D (native settings)

Documented keys (reading of 2026-10-24): `permissions.deny` rules in the host's rule syntax and `sandbox.filesystem.allowWrite`. Deny wins over allow, so the rules enumerate other units' declared write and create paths and the control paths; the allowlist lists the unit's envelope, and whether it restricts or is additive to the default working-directory write access is unconfirmed (HV-8, GP-5). Patterns that cannot be expressed exactly are `unexpressible`. The document is supplied by the operator's launcher (for example `--settings`) or settings placement; on a shared tree rules are per path, not per teammate. Offered per surface only where HV-8 and GP-5 record behavior.

### Output A (companion plugin)

`PreToolUse` with a matcher for Write and Edit (NotebookEdit only if the founder accepts that proposed extension), and `TaskCreated`. No `SessionStart` hook and no `PostToolUse` observer. The same hook delivers the Whisper. The liveness canary is a recorded, harmless first-use event per session and surface and the expected-versus-observed counters; its exact trigger is a design detail resolved with GP-1 and GP-3. The pinned copy of the ownership module is checked against the repository hash at build and at hook start. `block` on a partial envelope requires an operator exemption record.

### Output B (snippet)

Text with a coverage header; never applied.

### Wire adaptation and coexistence

Provisional table in the contracts README (`TaskCreated` has no `ask`). The guard never emits `allow` or `defer`; the host combines decisions most-restrictive first, so the guard cannot override another hook or a permission rule. Hooks from managed settings may run first; `allowManagedHooksOnly` or `disableAllHooks` can switch the companion off, which the attestation reports as advisory.

### Bounds and privacy

Profile and envelope reads at most 1 MiB, 512 paths per list, 256-character strings; no network, socket or process launch; the audit record is content-free, private, outside the repository and excluded from Git; retention is a rule to state before release and no count is collected or emitted (telemetry is deferred; the never-collect list is an exclusion). The G1 hook latency criterion (p95 500 ms) is a proposed value, measured and reported, never claimed.

### HAR.3 cross-reference (specs/050-braid-harness-adaptation)

HAR.3 T005 (per-host task-local hook and plugin adapters with independent Codex and Claude support matrices), T006 (bounded delegated roles and orchestration binding ownership, dependencies and tool/effect scopes) and T011 (opt-in lifecycle, canary, incident stop, rollback) overlap this guard conceptually. Rule: HAR.3 profiles are task-local variants of the laboratory evaluated offline and promoted by humans; SPEC-058 is a user-facing opt-in product capability for a user's own live sessions. The plan (a) reuses the T005 qualification matrix and the T011 lifecycle (opt-in, canary, incident stop, rollback, uninstall cleanup) if and when they land and does not write a general hook-profile compiler or orchestration planner; the only compiler here maps ownership to a profile; (b) reuses T006's ownership-binding vocabulary where it exists; (c) makes no depth or width claim (T007); (d) states that, if T005 lands first, the hook-adapter layer of the companion either consumes its qualified adapter contract or records why it is independent. The cross-reference is documentation (T025) checked by the governance test.

## Validation strategy

### Validation profile

Per [validation profiles](../../docs/development/VALIDATION_PROFILES.md): during implementation run `python3 scripts/validate_change.py --base develop --profile quick` (the planner escalates sensitive or unknown paths, including new modules under `agent_braid/` and `integrations/`); run `--profile pr` once on a stable candidate. Structural Spec Kit validation (`python3 scripts/validate_spec_kit.py` and `snapshot` for this feature) is part of every candidate. Clean-room reproduction, evidence capture, human review and founder approval stay separate boundary gates and are never implied by a passing profile.

### Requirement to scenario to test to evidence

| Requirement | Scenario | Procedure | Planned test file or evidence | Tasks |
|---|---|---|---|---|
| REQ-001 | SC-001 | procedure_req_001 | tests/test_guard_policy_compiler.py | T011 |
| REQ-002 | SC-002 | procedure_req_002 | tests/test_guard_native_settings.py | T009, T012 |
| REQ-003 | SC-003 | procedure_req_003 | tests/test_guard_settings_snippet.py | T009, T013 |
| REQ-004 | SC-004 | procedure_req_004 | tests/test_guard_companion_package.py | T021, T026 |
| REQ-005 | SC-005 | procedure_req_005 | tests/test_guard_decision_contract.py | T006, T010, T014 |
| REQ-006 | SC-006 | procedure_req_006 | tests/test_guard_modes.py | T001, T014 |
| REQ-007 | SC-007 | procedure_req_007 | tests/test_guard_control_paths.py | T007, T015 |
| REQ-008 | SC-008 | procedure_req_008 | tests/test_guard_liveness.py | T004, T010, T016 |
| REQ-009 | SC-009 | procedure_req_009 | tests/test_guard_fail_open.py | T001, T005, T017 |
| REQ-010 | SC-010 | procedure_req_010 | tests/test_guard_bypass_report.py | T023 |
| REQ-011 | SC-011 | procedure_req_011 | tests/test_guard_task_created.py | T008, T020 |
| REQ-012 | SC-012 | procedure_req_012 | tests/test_guard_context_and_audit.py | T010, T017, T018 |
| REQ-013 | SC-013 | procedure_req_013 | tests/test_guard_bounds.py | T019, T021 |
| REQ-014 | SC-014 | procedure_req_014 | tests/test_guard_surface_matrix.py and host receipts | T005 to T009, T024 |
| REQ-015 | SC-015 | procedure_req_015 | tests/test_guard_governance.py | T001, T002, T003, T025, T026, T028 |
| REQ-016 | SC-016 | procedure_req_016 | tests/test_guard_release_gate.py | T002, T004, T022, T027, T028 |

Negative controls are part of the tests: every schema has a mutation set (`allow`, `defer`, grant, content member, unbounded string, `observed` without receipt, non-pass release gate); the decision function has the conformance table; the companion inventory has seeded violating components; the hook scripts have seeded network, process and model-path violations; the context builder has the adversarial-string set.

### Evidence handling

Obtained evidence is recorded only after a command runs, with the command, exit status, output hash, environment and limits, and is kept apart from planned evidence. Host receipts carry counts and booleans only. Raw hook inputs, transcripts, prompts, diffs and repository text from probes and G1 runs stay local and are never committed. A fingerprint is not approval; freezing and review are separate founder and reviewer acts.

## Sequence

Dependencies are named by what they are, not by numbered pull requests. The SPEC-052 and SPEC-053 specification pull request (#671), the SPEC-052 implementation pull request (#672) and the pull request that carries SPEC-057 to SPEC-059 (stacked on #671) come first; SPEC-057's own increments are I-1 to I-6 and are unrelated to any pull request number. The increments of this plan are S-1 to S-7.

1. **S-1 — Specification set** (this delivery; carried by the SPEC-057 to SPEC-059 specification pull request with the G1 proposal). Documents only.
2. **S-2 — Founder decisions** (T001), **ADR review disposition** (T002; adoption waits for the G1 outcome), integrator reconciliation (T003), G1 consistency review (T004).
3. **S-3 — Probes GP-1 to GP-5** (T005 to T009), each launched by the orchestrating session after the founder authorizes that probe, EUR 0, extending HV-6 to HV-8 and HV-10.
4. **S-4 — SPEC-057 I-3** (policy-profile schema, settings resolver; not owned here), then the **unreleased engineering candidate** (T010 to T021, T023 to T025) at a recorded commit that the G1 manifest hashes. The candidate is not packaged, listed or published and is installed by the founder as an explicit local opt-in.
5. **S-5 — G1** (SPEC-057: freeze, stage 1, the separate stage-2 decision, stage 2 with arms A3a and A3b on the candidate and the optional native-controls-only arm AN, report). Not owned here.
6. **S-6 — Release decision** (T027): a `pass` GG (which requires a `pass` GA) with a per-surface pass for every claimed surface and output, and the ADR adopted. Otherwise SPEC-058 closes as not adopted and nothing in S-7 happens.
7. **S-7 — Release** in reviewed stages: the release gate and package builder (T022), the operator recipe (T026), review and closure (T028). Adoption, version number and publication are separate founder decisions.

## Risks

- **False blocks and lost parallelism.** Mitigation: audit first; `block` never default; G1 false-block criteria; partial envelopes refuse `block`.
- **Bypass through Bash and other routes.** Mitigation: stated coverage boundary; output D where HV-8 supports; bypass recorded from receipts; the metric is G1's.
- **Tamper of the guard's own control paths.** Mitigation: operator-owned envelope, control-path denial, digest check, G1 tamper negative control; the Bash gap is stated.
- **Silent non-enforcement (hooks disabled, failing or not firing on a surface or model).** Mitigation: liveness attestation defaulting to advisory; `guard-not-covered`.
- **Host drift and preview surfaces.** Mitigation: version-tagged matrix, probes with receipts, `preview` labels.
- **Authority creep.** Mitigation: no `allow`, no grant, no launch; governance tests; the ADR gate.
- **Platform erosion.** Anthropic could ship native ownership enforcement. Mitigation: bounded claims; output D defers to native controls; G1 may end in "no benefit beyond native controls", which closes the specification.
- **Prompt injection through model-visible context.** Mitigation: closed templates, SPEC-057's escaping definition reused byte for byte, bounded data fields, adversarial fixtures, and a Whisper that forwards no sibling-written path text. Residual and unmeasured: escaping does not neutralise semantic injection, and any other route by which one unit's file name reaches another agent is not controlled.
- **A GG pass read as value over native controls.** G1 has no native-controls-only arm unless the optional stage 2 arm `AN` runs. Mitigation: the release decision records per surface whether `AN` ran and carries the proposal's limitation sentence otherwise.
- **Budget.** G1's S2 may not be affordable at EUR 0; a downgraded G1 evaluates no threshold and cannot release the guard.
- **Unconfirmed sandbox allowlist semantics.** If the allowlist is additive, output D restricts nothing beyond its deny rules. Mitigation: no restriction or OS-level bound is claimed without a GP-5 or HV-8 receipt.
- **Candidate drift.** The evaluated candidate and the released artifact could differ. Mitigation: the release decision binds the evaluated candidate commit and the release is a reviewed change on it.

## Constitution check after design

The design adds no analyzer, no execution path and no grant. The one mechanism-class element is opt-in, gated and bounded, and its only blocking conflict (ADR 0024's hook wording) is held behind the ADR proposal rather than resolved here. Article 12 is honored by publishing the coverage boundary and by never labelling advice as control or configuration as enforcement. Article 13 is honored by the class block and the attestation. No further conflict found; a conflict with a MUST in an authority would block the work and be reported, not resolved here.

## Human review and unresolved decisions

Human review is pending. Open items for the founder are in the specification's "Evidence and unresolved questions" and in task T001; the settings precedence, fail-open stance, notification strategy, telemetry, G1 staging with its native-controls-only comparison, ADR timing, the SPEC-059 sketch and the probe launch rule were decided on 2026-10-24 and are recorded in the Clarifications. The integrator handles the documents this track does not own (T003).
