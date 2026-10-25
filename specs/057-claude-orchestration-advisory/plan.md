# Implementation plan — SPEC-057

Status: draft plan. Planning is not permission to implement or deliver. Implementation starts only after the SPEC-052 and SPEC-053 specification pull request (#671), the SPEC-052 implementation pull request (#672) and the pull request that carries this specification have merged, and each increment below (I-1 to I-6) is a separate reviewed change. Nothing in this plan freezes, signs, approves, runs a workflow, a session or a team, spends money, publishes or creates a remote issue. `obtained_evidence` in `assurance.json` is empty and human review is pending.

## Technical context and scope

- Milestone: M4.6 — Claude Code dynamic workflows. Program: [SPEC-052 program](../052-claude-workflow-gate/program.md). This specification is the advisory core of the orchestration family decided on 2026-10-24 (SPEC-057 advisory core; SPEC-058 opt-in guard; SPEC-059 ledger and active push) and owns gate G1 and the host probes HV-6 to HV-13. The binding founder decisions of 2026-10-24 (three rounds) are recorded in the specification's Clarifications and applied here.
- Language and stack: Python 3.12+ standard library plus the pinned `requirements-speckit.txt` and `requirements-dev.txt` tooling (`jsonschema` is already pinned for schema checks). Unit tests use `unittest` (no new test stack). The planned module is stdlib-only and imports no network, socket or process-launching helper of its own; Git is reached only through the existing bounded helpers.
- Existing code relied on (read, and not changed by this plan except where stated in the file-level design below): `agent_braid/analysis.py` (exact-string resource identity; unchanged), `agent_braid/git_adapter.py` and `agent_braid/git_process.py` (bounded read-only Git; double observation; `--no-renames`), `agent_braid/runtime_scheduler.py` (`_overlap`, the prefix rule, which moves into a neutral helper that the scheduler and the new module both import), `agent_braid/plugin_mcp.py` and `agent_braid/tooling_mcp.py` (admission lock, allowlist, limits; unchanged). Changed additively after #672: `agent_braid/cli.py` (four subcommand registrations) and one new module `agent_braid/ownership.py`.
- Inputs that exist now: the G1 proposal document, its inputs record, its structural checker and tests (drafted by the G1 track, unfrozen), the hypothesis register entry H-CW2, the radar snapshot `research/radar/2026-10-24-claude-orchestration.json` with `docs/strategy/ECOSYSTEM.md` and adoption track AT-2026-007, the SPEC-052 and SPEC-053 specifications, the research digest summarized in [research.md](research.md).
- Out of scope, unchanged from the spec: launching, messaging, resuming or authorizing anything; a shipped fan-out; hooks, mods, monitors and channels in the main plugin; blocking behavior; a `PostToolUse` Bash observer; an orchestration skill (deferred, T039); push (Megaphone, Doorbell) and a shared ledger; telemetry (deferred, T041); speed claims; transcript evidence; Codex and every host other than Claude Code.
- Spend: EUR 0 additional, existing subscription, included quota only ([budget](../../docs/tooling/BUDGET.md)); stop on quota exhaustion. Probes and G1 use Sonnet at medium effort and small paired designs. The orchestrating Claude session launches each probe after the founder authorizes that probe; no authorization carries to the next.

## Constitution check before research

Applicable: clause zero and Articles 1–3, 5–7, 12–15, 19–21, 23 and 25, as listed in `assurance.json`. Also GOVERNANCE.md, the operational semantics, claim discipline, ADRs 0014, 0021 and 0024, `docs/architecture/AGENT_INTERACTION_METADATA.md`, `docs/architecture/PARALLEL_INTEGRATION.md` and SPEC-023, 047, 050, 052 and 053.

| Authority | Obligation | How the plan honors it | Verdict |
|---|---|---|---|
| Clause zero | No assumption that Yang–Baxter or commutation applies; no claim from analogy | Ownership is a declaration, not a commutation claim; an independent candidate keeps the constraint that an execution contract is required before parallelism; no braid language | No conflict |
| Art. 1 | Interactions over prompts | Declarations and observations are computed and schema-bound; no prompt decides a class | No conflict |
| Art. 2 | Order is a semantic question | Disjoint declarations are not evidence of order independence; `ordered` arises only from declared dependencies; the recipe says so | No conflict |
| Art. 5 | Effects first-class; hidden effects are uncertainty | Reads, writes, creates and deletes are effects; Bash, generated files, MCP effects, renames and binaries are unknown or not observed | No conflict |
| Art. 6 | Conditions travel with the operation | Constraints (`requires-execution-contract-before-parallelism`, shared-resource classes, base assumption) travel in the envelope; nothing schedules | No conflict |
| Art. 7 | Distinguishable decision stages | Declaration, expansion, AIM mapping, analysis, checkpoint comparison and notice building are separate pure steps with provenance | No conflict |
| Art. 12 | Prompts and communication do not replace concurrency control | Advice and notices are labelled communication, never control; the only mechanism-class outputs are SPEC-058's, bounded by a published coverage boundary and gated by G1 | No conflict |
| Art. 13 | Explicit class, property, method, domain, assumptions, contracts | Every envelope carries the block; classes `0-heuristic` and `1-syntactic` are claims by the producer, not verified evidence | No conflict |
| Art. 14 | Evidence, not verdicts | Receipts list per-unit entries, unknowns, snapshot digests and what was not observed | No conflict |
| Art. 15 | Vendor-neutral core | The declaration core has no vendor member; Claude specifics live in the audit, recovery input, matrix and recipe | No conflict |
| Art. 19 | Real, measurable problem; correctness over agent count | G1 measures conflicts prevented or caught earlier, parallelism retained, false blocks, bypass, overhead; designed-overlap runs are reported separately; no speed claim | No conflict |
| Art. 20 | Analysis and execution are separate | Read-only commands; no launch, message, resume or grant; wave-gate lives in the user's script | No conflict |
| ADR 0021 | Grants never model-callable; host approval is not runtime authority | No grant member; no MCP tool added; `executionAuthorization` false; the guard (SPEC-058) never emits allow | No conflict |
| ADR 0024 | No installation or session hooks ship; five product skills unchanged | No hooks, no new skill; guidance is repository documentation and CLI help; the orchestration skill is a deferred task (T039) blocked by the ADR amendment and G1 gate GA; the opt-in components are separate companion plugins (working names, decided after G1) | No conflict |
| AGENTS.md | No command authorizes concurrent agents or autonomous delivery | Each probe and each G1 run needs its own founder authorization before the orchestrating session launches it; no task authorizes an agent to start a workflow, session or team by itself and Agent Braid launches nothing | No conflict |
| Claim discipline | Labels and bounded wording | Matrix evidence statuses; the dated prior-art pass; a wording lint | No conflict |

No conflict is expected before research; this check is repeated after design.

## Research, assumptions and alternatives

[research.md](research.md) records the sources, how they were read, the decisions below and the weak claims that the critical review raised. The decisions that shape the design:

- **RS-1 Checkpoints through the CLI, not MCP polling.** The plugin admits one MCP caller at a time, caps active calls, fixes the worktree allowlist at connection and refuses to analyze a worktree that changes between two observations. Runtime-created worktrees cannot be reached through the MCP. Continuous evidence is therefore a serialized CLI call at committed or quiesced points; the MCP remains available for pre-flight queries where HV-1 confirms it.
- **RS-2 Declared-only is the honest class.** A pre-flight is as good as the declaration. Partial coverage whenever an entry is not exactly expanded keeps the class conservative, and under-declaration (especially of reads) is measured by G1 instead of assumed absent.
- **RS-3 Expansion before analysis.** The analyzer compares exact strings, so a directory or pattern would silently be disjoint from a file inside it. The expansion step is a prerequisite, with the existing prefix rule reused in one place.
- **RS-4 Mailbox + Whisper by default.** The Mailbox is the pull notice the orchestrator reads (the host already wakes the orchestrator at the end of each turn of a linked session); the Whisper is `PreToolUse` `additionalContext` to the affected agent in its own session and belongs to SPEC-058. The Megaphone (monitor or channels) and the Doorbell (a script posting data to the orchestrator's own session socket) are opt-in, reserved for SPEC-059, enabled only if G1 shows late notices with measurable harm and, for the Doorbell, a transport verified after G2; the ADR must reframe "never messages as a session" for the Doorbell. Mods remain excluded.
- **RS-5 One policy-profile schema, three outputs, no hooks in the main plugin.** Owned here so that SPEC-058 consumes it; the compiler is SPEC-058.
- **RS-6 Interoperate, do not build locks.** Imports are optional, offline and deferred; uniqueness wording waits for the dated prior-art pass.
- **RS-7 G1 arm A3 needs an unreleased SPEC-058 candidate.** Stage 1 (A0 to A2) does not depend on SPEC-058. SPEC-058 must be implemented as an unreleased engineering candidate (behind the G1 gate) before arm A3 can run; adoption or release happens only after G1 gate GG passes and the ADR is adopted. A throwaway log-only script remains useful for the host probes, not as the A3 arm.
- **RS-8 One refusal rule.** A busy lock, an unstable snapshot, an unobservable source, over-bound or malformed input and an existing output path end a command with a stable error code and no result object (`command-error.schema.json`); `not-observed` and `unknown` inside a result are outcomes of the observation contract. This replaces the earlier mixed rule in which a refusal was both an error and a per-unit result.
- **RS-9 Settings are operator-owned.** Most specific scope wins; a `block` at repository or user scope is a floor; each scope has one defined operator-owned location (user configuration directory; a file outside every working tree keyed by the repository digest; a document supplied at invocation) and anything else is refused, so an agent that can only write inside its working tree cannot lower the floor; the schema has a versioned `extensions` member that SPEC-059 extends without a change here.

Alternatives rejected: shipping hooks in the main plugin (conflicts with ADR 0024 and with the founder's decision); shipping a runnable fan-out wave-gate workflow or a runnable fan-out template in the recipe (a fan-out is out of scope and would need agent write capability; the snippet uses a placeholder for the launch step); a `PostToolUse` Bash observer now (the checkpoint receipt covers the worktree surfaces; the agent-teams case waits for the SPEC-059 ledger decision after HV-L7); polling the plugin MCP from many agents (lock contention, admission lock); a durable shared ledger now (needs G2); adding a plugin skill now (needs the ADR amendment; deferred as T039, not discarded); a new analyzer (duplicates the algebra, Article 20); executing `claude agents --json` from Agent Braid (it would make Agent Braid a launcher of host processes).

## Design and compatibility

### File-level design (all after #672, the SPEC-052 implementation pull request)

New files:

- `agent_braid/ownership.py` — pure functions, stdlib only: `validate_declaration`, `normalize_path`, `expand_declaration` (to exact paths and create regions, with a coverage statement), `to_aim` (AIM `0.2.0-draft` records in the declared channel), `compare_envelope` (declared versus observed), `build_notice` and `read_notice`, `audit_isolation`, `build_recovery_report`, `resolve_settings` (scope precedence, block floor, extension storage), and the settings resolver with the operator-owned locations of `contracts/README.md`. The single prefix-overlap rule is not copied: it moves from `runtime_scheduler._overlap` into a small neutral helper module (name set at implementation) imported by both `ownership.py` and the scheduler, with the scheduler's existing tests pinning its behavior. Splitting into a package is allowed at implementation time if the file grows beyond review size; the public names above stay stable.
- Four additive CLI subcommand registrations in `agent_braid/cli.py`: `expand-ownership` (declaration to AIM plus the pre-flight evidence block), `check-ownership` (declaration plus committed or quiesced worktrees or commits to a receipt), `audit-isolation` (repository, settings files and optional script text and agents JSON to configuration observations) and `report-recovery` (agents JSON file or standard input plus Git state to a recovery report). All are read-only, local, offline and bounded; outputs go to standard output or to an explicit new private path.
- `contracts/*.schema.json` (finalized from the drafts), `tests/test_*.py` and `tests/fixtures/ownership/` as in [validation-plan.md](validation-plan.md), and `docs/tooling/CLAUDE_ORCHESTRATION.md` (recipe).
- Not created by this specification: `scripts/validate_claude_orchestration_g1_proposal.py` and `tests/test_claude_orchestration_g1_proposal.py` already exist as drafts written by the G1 track alongside the proposal. Task T032 reviews them against REQ-013 and extends them only by agreement with that track.

Unchanged: `agent_braid/analysis.py`, `agent_braid/git_adapter.py`, `agent_braid/runtime_scheduler.py` (except that it imports the neutral overlap helper instead of defining the rule), `agent_braid/plugin_mcp.py`, `agent_braid/tooling_mcp.py`, AIM `0.2.0-draft`, the SPEC-052 gate and its schemas, the plugin MCP tool set, the registry, grants, telemetry vocabulary, and the existing five product skills.

Data flow: declaration (JSON) → `validate_declaration` (bounds, no content) → `expand_declaration` against a pinned base (Git object reads through the bounded helper; case-fold and symlink checks) → `to_aim` → existing `analyze` / `analyze-work kind=aim` → pre-flight evidence block (class, label, constraints, unknowns, closed vocabulary). At a checkpoint: declaration + worktree or commit sources → Git adapter observation (two observations, stability check) → `compare_envelope` → receipt (+ `build_notice` when a hazard exists).

### Path identity and expansion

One normalization function: separator, `./`, `..`, absolute to repository-relative (outside the repository is a refusal), Unicode NFC, and a case-fold collision check (two entries equal under case-folding are reported as one resource with partial coverage unless the repository is known case-sensitive). Symlinks resolve inside the repository or the entry is refused. Patterns expand against the pinned base tree (listing, not content). A pattern that matches nothing, a `creates` prefix, a path that does not exist at the base, or an entry that exceeds the bounds yields partial coverage and an explicit unknown. The overlap function treats equal paths and path-prefix relations (with `/`) as overlapping, exactly as the scheduler does, so the declared-versus-observed comparison and the pre-flight cannot disagree.

### Why the pre-flight cannot approve

The analyzer's independent candidate already carries the constraint `requires-execution-contract-before-parallelism` and `executionAuthorization: false`. The plan adds a closed vocabulary (evidence, constraints, unknowns) and a lint over every emitted string and over the recipe: terms that start, schedule, approve or recommend parallel execution are rejected. The result states in a fixed sentence that disjoint file sets are not evidence of a clean merge and that integration evidence is the SPEC-052 gate.

### Checkpoint and quiescence

A checkpoint is a point the operator or the user's script chooses: a unit has committed, or the wave has ended and no writer is active. The CLI observes twice and compares; a changing worktree is a refusal: the command stops with `ERR-UNSTABLE-SNAPSHOT` naming the declared unit id and produces no receipt; the operator reruns it at a quiescent point. The CLI never takes the plugin lock and is not subject to the plugin worktree allowlist because it is operator-run; that is also why it is not an agent tool and is not added to SPEC-052's constrained Bash allowlist. A hook-invoked variant would circumvent the MCP allowlist and is therefore SPEC-058's design problem, with its own resource limits and no model-controlled path arguments.

### Host verification (probes HV-6 to HV-13)

Probes run on a scratch repository on the existing subscription. The orchestrating Claude session launches each one through a workflow or derived sessions only after the founder authorizes that probe; coding agents prepare the log-only scripts, which stay outside the repository and are hashed in the receipt, together with throwaway settings that are removed afterwards. Evidence is pinned to the host version. Each records an outcome of `pass`, `fail` or `unobserved`, the Claude Code version, operating system, surface and date, and counts and booleans only.

| Probe | Question | If it fails or is unobserved |
|---|---|---|
| HV-6 | Do settings-provided and plugin-provided `PreToolUse` hooks fire, with `agent_id` and `agent_type`, for Write and Edit inside workflow agents, `/batch` units, in-process and split-pane teammates? (Documented for subagents; inferred for workflow agents and `/batch`; unobserved for teammates.) Which working directory do they report for a Desktop session in a worktree? | SPEC-058 outputs A (hooks) are labelled inferred on that surface; the matrix keeps the cell unconfirmed; no behavior is asserted, and `inferred` stays attached wherever hook firing is used downstream |
| HV-7 | The documented rule is that the task tools are present by default only on some models; are they present on the model actually in use, and therefore does `TaskCreated` fire for an agent team? | `TaskCreated`-based enforcement is reported as unavailable on that model; Write/Edit controls are the model-independent fallback |
| HV-8 | Do permission deny rules and a sandbox write allowlist apply inside workflow agents, `/batch` units and teammates, do they stop shell writes, and does `--settings` reach dispatched sessions? | Output D (native settings) is not offered for that surface; Bash coverage is not claimed |
| HV-9 | What does `claude agents --json` (and `--all`, `--cwd`) actually print? Are workflow agents and teammates listed? | The recovery report is written against the observed shape; everything else is unknown |
| HV-10 | Which base does a workflow-agent or background-session worktree actually use when the local HEAD is ahead, and where is the effective `baseRef` readable? | The base audit reports unknown instead of a value |
| HV-11 | What branch and publication layout does `/batch` produce? | The `/batch` integration row stays unconfirmed; no input contract is claimed |
| HV-12 | Are the agent-teams task directory, team configuration and workflow journal readable by a separate read-only process when a unit is stopped? | The best-effort branches are dropped from REQ-007 |
| HV-13 | Do sessions, subagents and teammates share one plugin MCP process or start their own? | The checkpoint design is unaffected (it never depends on shared MCP state); the lock note in the recipe is adjusted |

SPEC-058 names its own probes GP-1 to GP-5 and SPEC-059 its own HV-L1 to HV-L8 (HV-L7 reuses the HV-6 receipt). SPEC-052's HV-1 to HV-5 stay owned by SPEC-052; HV-1 (plugin MCP tools inside workflow agents) is the gate for the MCP route of the pre-flight, and the fallback is the CLI from the orchestrating session.

### HAR.3 cross-reference (specs/050-braid-harness-adaptation)

HAR.3 tasks T005 (per-host task-local hook and plugin adapters with independent Codex and Claude support matrices), T006 (bounded delegated roles and interaction-aware orchestration binding ownership, dependencies and tool/effect scopes), T007 (measured depth and width) and T011 (opt-in lifecycle, canary, incident stop, rollback) overlap this family conceptually. The rule recorded here: HAR.3 profiles are task-local variants of the laboratory, evaluated offline and promoted by humans; SPEC-057 is a user-facing, opt-in product capability for a user's own live sessions. SPEC-057 therefore (a) reuses the T005 qualification matrix and the T011 lifecycle if and when they land and does not write a second hook-profile compiler or orchestration planner, (b) reuses the T006 ownership-binding vocabulary where it exists rather than inventing a parallel one, (c) claims nothing about depth or width search (T007), and (d) records that SPEC-058's policy compiler must state which HAR.3 contract it consumes or why it is independent. The cross-reference is documentation (T028) and is checked by the governance test (no compiler or planner module among the deliverables).

T028 cross-reference note (written 2026-10-25, T028 still unchecked). Status of the three SPEC-050 tasks at `develop` `8d24c6f`: T005, T006 and T011 are all unchecked in `specs/050-braid-harness-adaptation/tasks.md`, and `agent_braid/harness_hooks.py`, `agent_braid/harness_orchestration.py` and `agent_braid/harness_lifecycle.py` are not among the SPEC-057 deliverables. Reused if and when they land: from T005 the per-host qualification matrix (SPEC-057 T024 is the matrix checker; it adds no hook-profile compiler) and the per-host hook support statements; from T006 the ownership, dependency and tool/effect-scope binding vocabulary (SPEC-057 reads it and adds no planner; the analyzer in `agent_braid/analysis.py` stays unchanged); from T011 the opt-in lifecycle, drift requalification and incident stop (SPEC-057 adds no lifecycle manager). Independent: the declaration schema and validator (T012, T013), the expansion and pre-flight (T014 to T016), the checkpoint comparison (T017) and the advisory notices (T019); none writes grants or launches sessions. Not yet done and not claimed: the recipe pointer (the recipe is T026) and the governance-test confirmation that no compiler or planner module exists in this specification's deliverables (`tests.test_orchestration_governance` is T025 and does not exist). T028 can be checked only after both exist.

## Validation strategy

### Validation profile

Per [validation profiles](../../docs/development/VALIDATION_PROFILES.md): during implementation run `python3 scripts/validate_change.py --base develop --profile quick` (the planner escalates sensitive or unknown paths, including new modules under `agent_braid/`); run `--profile pr` once on a stable candidate. Structural Spec Kit validation (`python3 scripts/validate_spec_kit.py` and the `snapshot` mode for this feature) is part of every candidate. Clean-room reproduction, evidence capture, human review and founder approval stay separate boundary gates and are never implied by a passing profile. A structural pass is not a scientific result.

### Requirement to scenario to test to evidence

| Requirement | Scenario | Procedure | Planned test file or evidence | Tasks |
|---|---|---|---|---|
| REQ-001 | SC-001 | procedure_req_001 | tests/test_ownership_declaration.py | T012, T013 |
| REQ-002 | SC-002 | procedure_req_002 | tests/test_ownership_expansion.py | T014, T015 |
| REQ-003 | SC-003 | procedure_req_003 | tests/test_ownership_preflight.py | T015, T016 |
| REQ-004 | SC-004 | procedure_req_004 | tests/test_ownership_receipt.py | T017, T018 |
| REQ-005 | SC-005 | procedure_req_005 | tests/test_isolation_audit.py | T020 |
| REQ-006 | SC-006 | procedure_req_006 | tests/test_orchestration_matrix.py | T011, T024, T044 |
| REQ-007 | SC-007 | procedure_req_007 | tests/test_recovery_report.py | T021 |
| REQ-008 | SC-008 | procedure_req_008 | tests/test_hazard_notice.py | T019 |
| REQ-009 | SC-009 | procedure_req_009 | tests/test_orchestration_settings.py | T022 |
| REQ-010 | SC-010 | procedure_req_010 | tests/test_policy_profile.py | T023 |
| REQ-011 | SC-011 | procedure_req_011 | tests/test_orchestration_recipe.py | T026, T027, T039 |
| REQ-012 | SC-012 | procedure_req_012 | host receipts under evidence/ | T003 to T011 |
| REQ-013 | SC-013 | procedure_req_013 | tests/test_claude_orchestration_g1_proposal.py | T032 to T036, T043 |
| REQ-014 | SC-014 | procedure_req_014 | tests/test_orchestration_interop_contract.py | T030, T031 |
| REQ-015 | SC-015 | procedure_req_015 | tests/test_orchestration_claim_wording.py | T002, T027 |
| REQ-016 | SC-016 | procedure_req_016 | tests/test_orchestration_governance.py | T001, T025, T028, T029 |
| REQ-017 | SC-017 | procedure_req_017 | tests/test_orchestration_bounds.py | T013, T018, T025, T040, T041, T042 |

Negative controls are part of the tests: every schema has a mutation set (including the settings floor and extension cases, the profile's conditional rules and the refusal-versus-result split); the expansion has the alias set (glob versus path, two creators, case, symlink, absolute versus relative, Unicode); the receipt has the unstable-snapshot refusal, the no-source not-observed unit, and the unattributed-writer and declared-exemption cases; the notice has the adversarial-string set; the policy profile has the `allow`, grant, main-plugin-target and default-attestation mutations; static tests have seeded violating fixtures.

### Evidence handling

Obtained evidence is recorded only after a command runs, with the command, exit status, output hash, environment and limits, and is kept apart from planned evidence. Host receipts carry counts and booleans only. Raw transcripts, prompts, diffs and repository text from probes and G1 runs stay local and are never committed. A fingerprint is not approval; freezing and review are separate founder and reviewer acts.

## Delivery and gate sequence for this specification

Each item is a separate reviewed change. GitHub remote artifacts remain drafts and publication is forbidden in this delivery. Dependencies are named by what they are: the SPEC-052 and SPEC-053 specification pull request (#671), the SPEC-052 implementation pull request (#672) and the pull request that carries this specification (stacked on #671). The increments I-1 to I-6 below are this plan's own and are unrelated to any pull request number.

1. **Specification pull requests** (#671 for SPEC-052 and SPEC-053; this specification, SPEC-058, SPEC-059 and the G1 proposal stacked on it; tracking by the integrator).
2. **SPEC-052 implementation** (#672, not this specification). SPEC-057 code waits for it because both touch `agent_braid/cli.py`, the package inventory tests and the builder.
3. **Probes HV-6 to HV-13**, each launched by the orchestrating session after the founder authorizes that probe (receipts under `evidence/`; may start after the specification pull requests; EUR 0).
4. **Prior-art pass** (T002, repeat or extend the recorded pass; may start after the specification pull requests; research only).
5. **I-1 — declaration, expansion, pre-flight** (T012 to T016): schema finalization, the pure module's first functions, `expand-ownership`.
6. **I-2 — checkpoint and recovery** (T017 to T021, T042): comparison, `check-ownership`, notices, `audit-isolation`, `report-recovery`, the command-error contract.
7. **I-3 — settings, profile schema, matrix, governance tests** (T022 to T025, T040). SPEC-058 consumes the profile schema from here.
8. **I-4 — recipe and reconciliation** (T026 to T028; T029 is the integrator's).
9. **I-5 — G1 checker review** (T032); the founder's decision on the `batch` pre-flight arm after HV-11 (T043) and the freeze (T033); the G1 stage 1 runs (T034). Stage 2 (arm A3) needs SPEC-058 implemented as an unreleased engineering candidate (behind the G1 gate) and a separate founder decision after the stage 1 report.
10. **I-6 — G1 evidence report** (T035) and the disposition (T036).
11. **Closure** (T037, T038).

Deferred and unscheduled: T030 and T031 (interoperability), T039 (orchestration skill, blocked by the ADR amendment and G1 gate GA), T041 (SPEC-047 telemetry vocabulary) and the T044 decision (agent-teams ledger, after HV-L7). SPEC-058 is adopted or released only if G1 gate GG passes and the ADR amendment is adopted; SPEC-059 only if the founder opens G2, which is decided after G1.

## Risks

- **Under-declaration** gives false assurance (the dangerous direction). Mitigation: `declared-only` class, partial coverage by default, a lint for empty read sets, the pre-flight false-assurance and declaration recall metrics in G1.
- **Disjoint is not merge-clean.** Mitigation: the fixed statement, the base audit, and the SPEC-052 gate remaining the integration evidence.
- **Host drift and preview surfaces.** Mitigation: version-tagged matrix rows, probes with receipts, `preview` labels, no dependence on channels, monitors, mods or desktop session tool names.
- **Platform erosion.** Anthropic could ship native ownership declaration or conflict detection. Mitigation: bounded claims, interoperation, and a G1 that can end in "no catches beyond the gate", which narrows the specification.
- **Notice injection.** Repository text in model-visible context. Mitigation: escaped, bounded, data-labelled fields; closed instruction vocabulary; adversarial fixtures.
- **Scope creep into control.** Mitigation: no hook, mod, monitor, channel, compiler or settings writer in this specification; the governance test.
- **Overhead.** The CLI starts a Python process per checkpoint. Mitigation: checkpoints only; G1 reports the overhead; no per-tool-call hook in this specification.
- **Surface weakness.** Agent teams have no Git ground truth; evidence there is the weakest and is reported separately per surface.
- **Budget.** G1 may not be affordable with paired arms at EUR 0. Mitigation: staged execution (stage 1 first, two surfaces), the planned run count and thresholds fixed before the freeze, and the pre-stated downgrade to observational findings with no efficacy claim.
- **Late notices.** A pull notice is read only when the orchestrator reads it. Mitigation: epoch, expiry and supersede link; notification volume and lateness are G1 metrics; the Megaphone and Doorbell stay reserved until G1 shows measurable harm.
- **Refusal read as a result.** Mitigation: one rule (errors have codes and no result object), tested with the refusal-versus-result matrix.
- **Settings and host inputs leaking content.** Mitigation: a closed key list for settings reads, no persisted session names, working directories or waiting text, and the never-collect exclusion for telemetry.
- **G1 proposal drift.** The proposal was written by another track and may change before the freeze. Mitigation: the review under T032 reports inconsistencies; the checker edits neither document; REQ-013 refers to gates and elements, not to numbers that only the frozen proposal may fix.

## Constitution check after design

The design adds no analyzer, no execution path and no authority. The only mechanism-class element anywhere in the family, the opt-in guard, is outside this specification and subject to its own gate and ADR. Article 12 is honored by labeling every output of this specification as evidence or communication. Article 13 is honored by the class block on every envelope and the matrix. No conflict found; a conflict with a MUST in an authority would block the work and be reported, not resolved here.

## Human review and unresolved decisions

Human review is pending. Open items for the founder are listed in the specification's "Evidence and unresolved questions" and in task T001: the adequacy of the receipt class label after the first evidence; the minimum Claude Code version per capability; the `batch` pre-flight arm (T043); the agent-teams ledger (T044). The settings precedence and block floor, the guidance form, the unattributed-writer default, the telemetry decision and the probe launch rule were decided on 2026-10-24. The integrator handles the documents this track does not own (T029).
