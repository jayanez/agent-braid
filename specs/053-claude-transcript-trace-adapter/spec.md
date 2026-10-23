# SPEC-053: Claude subagent transcript trace adapter

**Milestone:** M4.6 — Claude Code dynamic workflows

**Status:** draft specification. This is a research protocol (gate G0) followed by gated engineering. Only REQ-001 and REQ-002 are actionable now. REQ-003 to REQ-010 are implementation requirements and are **BLOCKED by G0**: only draft design artifacts for them exist in this directory (plan, research, contracts, tasks), kept so the dependency is reviewable; no implementation, schema adoption or task start for them occurs until G0 is frozen, run by the founder and recorded as a pass, and the draft design is re-planned then. A failed or inconclusive G0 closes or leaves them blocked; that is a valid outcome.

## Purpose and scope

Claude Code dynamic workflows let a user run several worktree agents in one session. SPEC-052 gives them a read-only integration gate that returns commit-level evidence. Commit-level evidence cannot see what an agent read, so it cannot see a cross-file dependency where agent A read a file that agent B rewrote. SPEC-053 asks whether the subagent transcripts that Claude Code records can be mapped, conservatively, into Agent Interaction Metadata (AIM) so the existing read-only analyzer can reason about those read/write hazards, and defines the preregistered gate G0 that decides whether building that mapping is justified.

In scope: the G0 preregistration and its source and budget decision; a future additive mapper `claude-subagent-transcript-v1`; a real-source admission path; privacy, retention and size bounds; and the gate v2 requirements that let SPEC-052's `braid-gate` consume transcripts.

Out of scope: any execution, grant, merge or promotion (Article 20); live capture or hooks; changing `agent_braid/analysis.py`; changing SPEC-023 acceptance; any speed claim (parallel runtime speedup is a recorded NO-GO in SPEC-021 G4, SPEC-022 and SPEC-038); other hosts; and any claim that transcript evidence proves commutation.

## Authorities

Constitution clause zero and Articles 1, 5, 7, 12, 13, 15, 19, 20, 21, 23 and 25. Article 12: prompts and planning never replace concurrency control. Article 15: effect metadata for tool protocols without coupling the core to a vendor, so the Claude mapping stays outside `analysis.py`. Article 19: evaluation on real workloads including multi-worktree integration, where success is conflicts prevented, not agent count. Article 20: analysis and execution stay separate. Also GOVERNANCE.md, `docs/theory/OPERATIONAL_SEMANTICS.md`, `docs/theory/CLAIM_DISCIPLINE.md`, `docs/architecture/AGENT_INTERACTION_METADATA.md`, ADR 0021 (grant issuance is never model-callable; host approval is not runtime authority), ADR 0024 (native plugins), `docs/architecture/PARALLEL_INTEGRATION.md` and ADR 0014 (a single coordinator serializes promotion), `docs/tooling/CLAUDE_SOURCE_CONTRACT.md`, `docs/tooling/BUDGET.md`, SPEC-023 and SPEC-052. Hashes are maintained in `assurance.json`. This spec cannot widen any of them.

## Declared dependency on SPEC-023 (milestone ADP.1)

SPEC-023 owns `agent_braid/trace_adapter.py` and its acceptance. SPEC-053 declares an **additive** dependency on it. It adds one mapper identifier and one admission kind; it does not change a SPEC-023 requirement, scenario, test, limit or the synthetic-only default, and every existing SPEC-023 test must pass unchanged. The plan settles the form (plan RS-1 and RS-3): a separate module that imports only public names of `trace_adapter.py` and owns its validators, with `trace_adapter.py` unchanged; the extension of `trace_adapter.py` remains a documented fallback that would need SPEC-023's owner. The known interaction is resolved the same way: today the adapter admits only `{"kind": "synthetic"}` and sets coverage to `unknown` whenever a mapping records a loss, and the transcript mapper's required `partial` coverage coexists with that rule because the new module applies its own rule and the existing mappers are not edited. Whether a canonical ADR is required for a new mapper plus admission kind (SPEC-023 REQ-008) is left to SPEC-023's owner and the founder at the start of PR5 and is not decided here.

## Research protocol: gate G0

Type: preregistered empirical feasibility protocol, run by the founder on the existing Claude subscription at EUR 0 additional spend. Details, procedure, arms, metrics and thresholds live in the [preregistration](../../docs/experiments/CLAUDE_WORKFLOW_INTEGRATION_PROPOSAL.md) and its [inputs](../../docs/experiments/claude-workflow-g0-inputs.json); this section records the protocol elements the template requires.

- **Target population:** Claude Code dynamic workflows with 3 or 4 agents in isolated Git worktrees on overlapping tasks in one repository, each agent committing.
- **Source permissions:** the founder's own sessions and an owner-controlled repository only. Rights, retention and spend are in the draft [budget and source decision](budget-and-source-decision.md), pending the founder's signature. Provider-terms confirmation is pending and not asserted.
- **Sampling frame:** founder-designed runs, not sampled from history: at least 10 eligible runs, at most 14 started; among the first 10 eligible runs in the run ordinal fixed in the manifest before launch, at least 7 with designed file or shared-symbol overlap and at least 3 with a cross-file contract dependency, each property recorded before launch. Designed overlap limits generalization, makes reference-failure prevalence high by construction (hence the C2 comparison) and is reported as such.
- **Eligibility:** every agent commits something different from the base; base tests pass; each branch passes tests alone; the workflow completes without edits to agent branches; transcripts available (otherwise the run is reported as `probe-unavailable`, counts for the Git arms and C1a only, and is outside the 10-run minimum and the C1b, C2 and C3 denominators).
- **Exclusions, counted and reported:** agent did not commit (the known `analyze-git` silent false negative, never scored as independent), base tests fail, branch tests fail alone, flaky final tests, workflow aborted, quota exhausted, manual edit of an agent branch, probe unavailable.
- **Observed outcomes versus proxy labels:** the reference outcome is observed: a serial Git merge in a preregistered order followed by the project tests, run twice. Tool predictions, including Braid labels and probe overlap, are proxies compared against it. Predictions are hashed before the reference outcome exists so labelling cannot depend on method rankings. No human judgment is used as a label; if a future adjudication is added it needs a new preregistration.
- **Held-out unit:** the run. Pairs within a run are not independent and are never counted as independent trials.
- **Negative and inconclusive reporting:** `g0-pass` needs criteria C1b, C2 and C3 together; any evaluated criterion not met is `g0-fail`; fewer than 10 eligible runs or fewer than 3 probe-flagged runs is `g0-inconclusive`, which does not pass. The order of evaluation is fixed: fewer than 10 eligible runs with probe data is inconclusive; otherwise C1b and C3 are evaluated and either unmet is a fail even with fewer than 3 probe-flagged runs; then fewer than 3 probe-flagged runs is inconclusive; then C2 is evaluated and unmet is a fail. Fail therefore takes precedence over inconclusive once 10 eligible runs with probe data exist. All three outcomes are published with counts, exclusions and costs.
- **Preregistered thresholds:** C1a (commit-level evidence; informs release R1 only and unlocks nothing; not a pass or fail input), at least 1 reference failure missed by both merge-tree baselines and flagged by the Braid primary flag; C1b (transcript-dependent; the only C1 criterion that gates PR5 and PR6), at least 1 reference failure missed by both merge-tree baselines, by naive path overlap and by `analyze-git` under both its primary and inclusive flags, and flagged by the transcript probe; C2, read/write-overlap precision at least 0.3, strictly above both the reference-failure prevalence among eligible runs with probe data (a pre-registered reported denominator) and the naive path-overlap precision; C3, unknown rate at most 40%.
- **Kill outcome on `g0-fail`:** adoption track AT-2026-006 moves to watch or rejected, SPEC-053 closes as not adopted, M4.6 closes with R1 only.

## Requirements and acceptance scenarios

### REQ-001 — Preregister gate G0 before any data exists

**SC-001:** Given the G0 proposal and its inputs record, when the structural checker and its tests run, then the proposal bytes, every required field and each threshold (C1a and C1b at least 1 each, C2 at least 0.3 and above both the reference-failure prevalence and the naive path-overlap precision, C3 at most 40%), the decision rule with its order of evaluation, the kill outcome, the EUR 0 budget, the probe's counts-only retention and the unfrozen, non-authorizing status are pinned, and removing or relaxing any of them is rejected.

Verification: tests/test_claude_workflow_g0_proposal.py and [procedure_req_001](validation-plan.md#procedure_req_001). Obtained evidence: none (a structural pass is not a result).

### REQ-002 — Record source rights and budget for founder signature

**SC-002:** Given the draft decision record, when it is reviewed, then it states EUR 0 additional spend on the existing subscription, the transcript source scope and its pending provider-terms confirmation, the G0 aggregate-only retention table and a pending signature, and no approval is inferred from the draft.

Verification: tests/test_claude_workflow_g0_proposal.py and [procedure_req_002](validation-plan.md#procedure_req_002). Obtained evidence: none.

### REQ-003 — Map transcripts with an additive Claude mapper (BLOCKED by G0)

**SC-003:** Given bounded Claude subagent transcripts and a base commit, when `claude-subagent-transcript-v1` maps them to AIM `0.2.0-draft`, then `Read` yields a read effect, `Edit`, `Write` and `NotebookEdit` yield write effects, and `Bash`, `Grep`, `Glob`, MCP tools and every other tool yield an `unknown` effect; the mapper lives outside `agent_braid/analysis.py`, has a versioned identifier, adds no vendor field to the core schema and leaves analysis results for existing inputs unchanged.

Verification: [procedure_req_003](validation-plan.md#procedure_req_003). Planned evidence only; blocked until G0 passes.

### REQ-004 — Bind reads to the base blob and ignore self-reads (BLOCKED by G0)

**SC-004:** Given an agent reads a path that exists at the base commit, when the mapper emits `readVersions`, then the read is bound to the base blob identity (the integer representation and its provenance table are fixed at planning); a read of a path the same agent already wrote, a path absent at the base, or a path outside the worktree emits no read effect and no read version and is counted as a recorded loss (an AIM read effect without a version is itself reported as a loss by the generic importer, so none is emitted).

Verification: [procedure_req_004](validation-plan.md#procedure_req_004). Planned evidence only; blocked until G0 passes.

### REQ-005 — Keep coverage partial and never promote unknown (BLOCKED by G0)

**SC-005:** Given any mapped transcript, when coverage is assigned, then it is always `partial` (never `complete`), failed tool calls produce no effect and count as losses, and no pair containing an `unknown` effect is reported as an independent candidate with complete coverage; because coverage is always `partial`, a transcript-derived pair can be classified only as `conflicting`, `ordered` or `unknown`, never as an independent candidate, so transcript evidence can surface hazards but never positive independence; transcript-derived effects are recorded in the `inferred` channel because they are the agent's recorded request, not an independently observed effect.

Verification: [procedure_req_005](validation-plan.md#procedure_req_005). Planned evidence only; blocked until G0 passes.

### REQ-006 — Admit real transcripts only through a reviewed path (BLOCKED by G0)

**SC-006:** Given a real Claude transcript and today's adapter that admits only synthetic input, when a real source is offered, then it is accepted only with a separately reviewed admission record naming rights, allowed fields, transformations, retention and privacy boundaries, using a new admission kind; without the record, or with a mismatched one, it is rejected with a fixed diagnostic code, and the synthetic path is byte-for-byte unchanged.

Verification: [procedure_req_006](validation-plan.md#procedure_req_006). Planned evidence only; blocked until G0 passes.

### REQ-007 — Enforce privacy, retention and size bounds (BLOCKED by G0)

**SC-007:** Given transcripts that contain prompts, file contents, command output and secret-like strings, when they are converted, then the converter reads locally and without network, streams within fail-closed bounds (confirmed at clarification on 2026-10-23: at most 32 transcripts, 32 MiB per transcript, 1 MiB per line, 512 distinct paths per agent, metadata strings of at most 256 characters), retains and emits only allowlisted metadata and aggregate counts under the retention label `allowlisted-metadata-and-counts` (not `aggregate-only`, which is the G0 probe's stricter rule), names the retained non-aggregate items (repository-relative paths, base object ids and a per-transcript SHA-256 digest) in the admission record as sensitive metadata, never copies prompts, file contents, command text or tool output into a result, provenance or diagnostic, and rejects breaches before analysis.

Verification: [procedure_req_007](validation-plan.md#procedure_req_007). Planned evidence only; blocked until G0 passes.

### REQ-008 — Preserve SPEC-023 acceptance (BLOCKED by G0)

**SC-008:** Given the additive mapper and admission kind are implemented, when the SPEC-023 and trace-adapter test suites and the existing `analyze-trace` behavior run, then they pass without modification and without changing a SPEC-023 limit, mapper, schema or acceptance statement, and the SPEC-023 owner's review is recorded before merge.

Verification: [procedure_req_008](validation-plan.md#procedure_req_008). Planned evidence only; blocked until G0 passes.

### REQ-009 — Let the gate consume subagent transcripts (BLOCKED by G0 and SPEC-052)

**SC-009:** Given SPEC-052's `braid-gate` receives transcript inputs through new optional arguments (explicit transcript paths, or file names under a `<transcriptDir>/subagents/` directory), when it runs, then a single agent converts them to AIM through the mapper by calling the bundled CLI subcommand `analyze-claude-transcripts`, used alongside the working MCP tools and not only as a fallback, under the constrained Bash that SPEC-052's Clarifications and REQ-016(d) define once (explicit launcher subcommands only, never the launcher binary) and that gate v2 extends by exactly that one additional subcommand as a planning amendment approved by the founder on 2026-10-24 (the plugin MCP tool set is unchanged and cannot read transcripts outside registered workspaces), without raising SPEC-052's bound of four agents, and a missing, unreadable, oversized or unrecognized transcript degrades only the transcript evidence, never the commit-level evidence, and is reported as such; if the host cannot express that constrained Bash, the amendment is refused or host verification HV-1 fails, the transcript part of the gate is no-go (a valid negative result) and the commit-level gate is unaffected.

Verification: [procedure_req_009](validation-plan.md#procedure_req_009). Planned evidence only; blocked until G0 passes and SPEC-052's v1 gate exists.

### REQ-010 — Merge transcript and Git analysis under result schema v2 (BLOCKED by G0 and SPEC-052)

**SC-010:** Given commit-level analysis and transcript-derived AIM for the same agents, when the gate merges them, then the result uses an additive schema v2 (a new `schemaVersion`, because the SPEC-052 v1 schema rejects unknown members) in which every pair keeps its commit-level label and adds the transcript read/write hazards with their coverage, and the `git merge-tree` baseline, replay eligibility and the unknown share are unchanged in meaning; "v1 consumers keep working" holds only in this bounded sense: the v1 result is emitted unchanged when no transcripts are supplied and every v1 field keeps its name, type and meaning in v2, while a strict v1 validator does not accept a v2 payload; a migration note states every field, `assurance` constant and canonical limit added, replaced or preserved (the v1 `assurance` constants remain valid when no transcripts are supplied; in v2 the `property`, `evidenceMethod`, `domain`, `assumptions`, `observationContract` and `executionContract` constants are extended to cover transcript evidence, while `compatibilityClass` stays `0-heuristic` and `notAGuarantee` stays true).

Verification: [procedure_req_010](validation-plan.md#procedure_req_010). Planned evidence only; blocked until G0 passes and SPEC-052's v1 gate exists.

## Scientific boundaries and compatibility

Claim labels: the mapping rules are engineering definitions; the prediction that read/write overlap anticipates integration failures is a heuristic and hypothesis [H-CW1](../../research/hypotheses/H-CW1-claude-workflow-integration.md), untested; no analogy or formal claim is made. Hypothesis falsity is a legitimate completion of the protocol.

Domain: Claude Code dynamic-workflow subagent transcripts of worktree agents in a Git repository. Observation contract: a transcript is the host's record of requested tool calls; it does not show effects of `Bash`, hidden tool effects, failed or reverted edits unless the result says so, or what a model understood. Transcript layout and field names are documented by the host but are unconfirmed for this project until the founder verifies them on the first G0 run and the mapper pins a version. Execution contract: read-only; no model invocation by the adapter; no network; no grant. The G0 probe and the product mapper are different instruments (the probe counts a failed call as unknown for C3, the mapper emits no effect for it); C3 stays tied to the probe and the planned conformance check reports every difference rather than redefining C3.

Compatibility: additive to AIM `0.2.0-draft`, the analysis report and the SPEC-052 gate. No change to `analysis.py`, SPEC-023 acceptance, the plugin MCP tool set or limits (4 active calls, 32 operations, 1 MiB, 360 s) unless a separately reviewed change says so. Replay and the owned runtime remain limited to 4 operations. The commit-level gate evidence stays correct and useful if G0 fails.

Not claimed: a lower conflict rate, faster delivery, completeness of effects, safety of any integration, or that more agents is better.

## Clarifications

Recorded with the founder on 2026-10-23 (`speckit-clarify`). These are planning
decisions, not acceptance, freeze or signature.

- **G0 parameters:** the drafted design is accepted as the preregistration
  draft: at least 10 runs of 3–4 worktree agents; C1 at least one reference
  failure missed by `git merge-tree` and flagged by Agent Braid or the probe;
  C2 read/write-overlap precision of at least 0.3; C3 unknown rate of at most
  40%, measured as the probe's tool-call share, with Git-level unknown shares
  reported as secondary. Freezing remains an explicit founder step.
- **Review amendments to the G0 parameters (draft, not yet founder-confirmed;
  confirmation is the freeze act):** an adversarial review found that C1 as
  accepted could pass on commit-level evidence alone and so unblock the
  transcript adapter without any transcript contributing, and that C2 had no
  base-rate reference. The draft therefore splits C1 into C1a (commit-level,
  informs release R1 only, unlocks nothing) and C1b (missed by both merge-tree
  baselines, naive path overlap and both Braid flags, and flagged by the probe;
  the only C1 criterion that gates PR5 and PR6); requires C2 to exceed both the
  pre-registered reference-failure prevalence and the naive path-overlap
  precision; and fixes the order of evaluation (below 10 eligible runs with
  probe data is inconclusive; C1b and C3 unmet is fail even below 3 probe-flagged
  runs; then below 3 flagged runs is inconclusive; then C2). The founder may
  amend or reject these before freezing; after freezing they bind.
- **Inconclusive G0:** fewer eligible runs or probe-flagged runs than required
  is not a pass; the founder decides afterwards whether to attempt a new
  preregistration, and the frozen proposal is never amended after data are seen.
  Inconclusive applies only where the order of evaluation above has not already
  produced a fail.
- **R1:** the commit-level SPEC-052 gate release; a failed G0 closes M4.6 with
  R1 only.
- **Adoption track:** AT-2026-006 is recorded in
  `research/adoption/2026-09-initial-triage.json`; `featureRef` and `adrRef`
  stay unset until adoption.
- **Converter bounds:** at most 32 transcripts, 32 MiB per transcript, 1 MiB per
  line, 512 distinct paths per agent and metadata strings of at most 256
  characters.
- **SPEC-023 integration:** whether the mapper edits `trace_adapter.py` or lives
  in a separate module, the integer form of base-blob `readVersions`, and the
  interaction with the adapter's loss-to-unknown rule are settled in the plan
  (RS-1 to RS-3), preserving SPEC-023 acceptance.
- **SPEC-052 dependency (planning amendment approved by the founder on 2026-10-24):** the "constrained Bash" is defined once by SPEC-052 (Clarifications and REQ-016(d)): explicit launcher subcommands only, never the launcher binary. Gate v2 needs exactly one more, `analyze-claude-transcripts`, used alongside working MCP tools and not only as a fallback; it is admitted only for gate v2 and amends SPEC-052 REQ-016 for that purpose, which is recorded in SPEC-052's Clarifications.
- **Retention label:** the product mapper retains allowlisted metadata
  (repository-relative paths, base object ids, a transcript digest) and counts
  and is labeled `allowlisted-metadata-and-counts`; `aggregate-only` is kept for
  the G0 probe, which retains no path or path hash.

## Evidence and unresolved questions

Obtained evidence: none. G0 is not frozen, no run exists and the decision record is unsigned.

Settled by the Clarifications above and no longer open: the unknown rate that binds C3 (the probe's tool-call share, with Git-level shares secondary); the meaning of "R1" (the commit-level SPEC-052 gate release); where adoption track AT-2026-006 is recorded (`research/adoption/2026-09-initial-triage.json`); the base-blob integer representation for `readVersions` and the edit-versus-separate-module question (plan RS-1 and RS-2); the size bounds; and that an inconclusive G0 never passes and any further attempt is a new preregistration whose start is the founder's separate decision.

Genuinely open:

- Founder confirmation of the review amendments to C1, C2 and the order of evaluation, which happens at freezing.
- Founder signature of the source and budget decision, including the provider-terms confirmation (pending, not asserted).
- The transcript line schema, unconfirmed until the founder's first G0 run; the `-v1` pin follows it.
- Whether a canonical ADR is required for a new mapper plus admission kind (SPEC-023 REQ-008): SPEC-023's owner and the founder, at the start of PR5.
- Host verification HV-1 and the Bash constraint that REQ-009 depends on, and two reviewed SPEC-052 amendments, both planning amendments approved by the founder on 2026-10-24: the one additional explicit launcher subcommand `analyze-claude-transcripts` in the REQ-016 allowlist for gate v2, and the validated path tokens that the transcript arguments need (plan, gate-result-v2 contract); otherwise the transcript part of the gate is no-go.
- Spec-owner and founder confirmation of the bounded reading of SC-010.
