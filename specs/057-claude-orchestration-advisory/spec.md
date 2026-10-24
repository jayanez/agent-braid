# SPEC-057: Declared ownership, pre-flight, checkpoint and recovery evidence for orchestrator-style parallel Claude Code agents

**Milestone:** M4.6 — Claude Code dynamic workflows

**Status:** draft specification. This is an engineering specification with one preregistered evidence protocol (gate G1, owned here) and a set of host-verification probes (HV-6 to HV-13). Implementation starts only after three changes have merged: the SPEC-052 and SPEC-053 specification pull request (#671), the SPEC-052 implementation pull request (#672) and the pull request that carries this specification (stacked on #671). Those are the only dependencies named by this specification; the plan's increments I-1 to I-6 are separate reviewed changes after them. Nothing is implemented, frozen, signed, run or approved. Obtained evidence: none; human review pending. The binding founder decisions of 2026-10-24 (three rounds) are recorded under Clarifications.

## Purpose and scope

Users of Claude Code run several agents at once in four documented ways, named in this family only by the surface ids `workflow-tracks`, `linked-sessions`, `agent-teams` and `batch`: dynamic-workflow tracks, linked or derived sessions launched from another session (agent view and background sessions, desktop-launched sessions, cross-session messaging), agent teams and the `/batch` skill. SPEC-052 is a specification (unadopted, host behavior unobserved) for an end-of-run, read-only integration gate over committed work. It is the intended integration evidence for dynamic-workflow tracks, and only as inferred branch tips for linked sessions; it does not mention `/batch`, and agent teams share one working tree and produce no commits to gate. It cannot help before the agents start, while they work, or after one of them stops. According to the host documentation read on 2026-10-24, the guidance for avoiding conflicts is prose (partition the files so that each teammate owns a different set); the host documents no ownership declaration, conflict detection or read/write staleness check for these surfaces. Article 12 says prompts and planning do not substitute for concurrency control when correctness depends on shared state.

SPEC-057 is the **advisory core** of the orchestration family that the founder opened on 2026-10-24. It lets the orchestrator (a user, a user-written workflow script, or the orchestrating Claude session) declare who owns what, obtain Agent Braid evidence about the declaration before work starts, compare the declaration with what Git shows at quiescent checkpoints, and obtain a read-only report when a unit stops or is orphaned. Every result is evidence for a human or a script the user wrote to read; none starts, stops, schedules, messages or authorizes anything. It reuses the existing analyzer (`analyze-work` with `kind: aim`) and the existing Git adapter, adds one pure ownership module and a few read-only CLI subcommands, and defines the schemas that the later opt-in guard (SPEC-058) consumes. It also owns the preregistered G1 experiment that decides whether the guard and anything stronger than advice may be released.

### The family

| Spec | Deliverable | Status of this delivery |
| --- | --- | --- |
| SPEC-052 | Read-only integration gate over committed work | Existing specification; unchanged apart from cross-references |
| SPEC-053 | Transcript to AIM adapter, behind gate G0 | Existing specification; unchanged |
| **SPEC-057 (this)** | Advisory core: declared ownership, pre-flight, checkpoint receipts, recovery reports, pull notices, the orchestration-settings and policy-profile schemas, host probes, gate G1 | Specified now; implementation after #671, #672 and this specification's pull request have merged |
| SPEC-058 | Opt-in guard: policy compiler with three outputs, a companion plugin (working name `agent-braid-guard`), modes ladder | Specified now; implemented first only as an unreleased engineering candidate behind G1 (needed by G1 arm A3); adoption and release blocked by G1 gate GG and an adopted ADR amendment |
| SPEC-059 | Sketch only: objective, limits, decisions taken (Mailbox + Whisper by default; Megaphone and Doorbell opt-in, gated by G1 late-notice harm and by G2; a separate notification companion; an attributed-write ledger decided after probe HV-L7; interoperability as documentation only) and a draft coordination contract kept for founder review. No requirement breakdown | Sketched now; blocked by gate G2 (the "Coordination across tools" contract of specs/039), which is decided after G1, and its own ADR |

### In scope

- A vendor-neutral ownership and footprint declaration, with a pure expansion module that turns directories and patterns into exact paths against a pinned base and degrades to partial coverage whenever the expansion is not exact (REQ-001, REQ-002).
- Pre-flight evidence through the existing analyzer, with a closed output vocabulary and a statement of what disjoint declarations do not show (REQ-003).
- A declared-versus-observed receipt at committed or quiesced checkpoints, run through the bundled CLI and not by polling the plugin MCP (REQ-004).
- An isolation and base audit, including the configured `worktree.baseRef` against the local HEAD (REQ-005).
- A per-surface capability and assurance matrix with host versions and `preview` labels, and the explicit list of what is not covered (REQ-006).
- Read-only recovery and orphan reports built from `claude agents --json` output the operator supplies and from Git (REQ-007).
- An epoch-stamped hazard notice schema with escaped, bounded repository strings, delivered as data to be read (REQ-008), and the orchestration-settings schema (notification strategy and guard mode per scope, most specific scope wins with a block floor, operator-owned) with a versioned extension point that SPEC-059 extends and in which only pull notices are effective (REQ-009).
- The policy-profile schema that SPEC-058 consumes (REQ-010).
- A wave-gate documentation recipe and a test that Agent Braid ships no fan-out (REQ-011).
- Host-verification probes HV-6 to HV-13, launched by the orchestrating Claude session only after the founder authorizes each probe (REQ-012), and ownership of the preregistered, staged G1 protocol (REQ-013).
- A documented, deferred interoperability contract; import adapters wait for demand or G1 evidence (REQ-014), a dated prior-art pass that bounds every market claim (REQ-015), the governance boundary with its HAR.3 reconciliation (REQ-016) and fixed bounds that fail closed (REQ-017).

### Out of scope

- Agent Braid launching, messaging as, resuming, stopping or authorizing any session, agent, team or batch (AGENTS.md; ADR 0021; Article 20). The orchestrator owns every launch and message primitive.
- Any shipped fan-out, and any shipped workflow that calls `agent()` with write capability.
- Hooks, mods, monitors or channels in the main plugin, and any blocking behavior of any kind. Those belong to SPEC-058 behind G1 and an ADR amendment. No `PostToolUse` Bash observer is specified now: the checkpoint receipt covers the worktree surfaces, and the agent-teams case is decided together with the SPEC-059 ledger after probe HV-L7.
- An orchestration skill. It is deferred, not discarded (task T039, blocked by the ADR amendment and by G1 gate GA); guidance ships now as repository documentation and CLI help.
- Active push to sessions (the opt-in Megaphone and Doorbell strategies), a durable shared ledger, leases, locks and cross-session delivery (SPEC-059, behind G2, which is decided after G1). SPEC-057 does not build locks; where locks exist elsewhere it is designed to interoperate.
- Telemetry. Nothing is collected now (REQ-017); a narrow, additive SPEC-047 vocabulary is deferred (T041).
- Speed, throughput or wall-clock claims (parallel runtime speedup is a recorded NO-GO: SPEC-021 G4, SPEC-022, SPEC-038), claims about the prevalence of semantic interference, and claims about conflicts beyond declared coverage.
- Transcript-derived read evidence (SPEC-053, blocked by G0), rename-aware or hunk-level analysis, and any change to `agent_braid/analysis.py`.
- Codex, cloud sessions, Remote Control and other-machine sessions, the VS Code extension and Windows ledger support. They are recorded as `not covered` in the matrix; this specification is Claude Code only.

## Authorities

Constitution clause zero and Articles 1–3, 5–7, 12–15, 19–21, 23 and 25; the article-by-article application is in the constitution check of [plan.md](plan.md). In short: a declaration of ownership is not a claim that units commute (Article 2); hidden effects are surfaced as uncertainty (Article 5); an execution contract is required before parallelism, so this specification never schedules (Article 6); advice is never labelled control, and only SPEC-058's opt-in outputs could be control within the coverage boundary it must publish (Article 12); every result declares a compatibility class and its contracts and exposes the observation boundary (Articles 13 and 14); analysis and execution stay separate (Article 20). Also GOVERNANCE.md; `docs/theory/OPERATIONAL_SEMANTICS.md`; `docs/theory/CLAIM_DISCIPLINE.md`; `docs/architecture/AGENT_INTERACTION_METADATA.md`; `docs/architecture/PARALLEL_INTEGRATION.md` (path disjointness alone is insufficient for undeclared build, test, generated-file or external resources, and a single coordinator serializes promotion); ADR 0014; ADR 0021 (grant issuance is never model-callable; host approval is not runtime authority); ADR 0024 native AI plugins (no installation or session hooks ship; the five product skills are unchanged), whose amendment for any opt-in component belongs to SPEC-058 and the feature-local proposal of SPEC-052; `specs/039-ai-tooling-program/program.md` (the "Coordination across tools" route); `specs/050-braid-harness-adaptation` tasks T005, T006 and T011 (HAR.3); `specs/047-local-technical-telemetry` (consent and vocabulary for any counts); `docs/tooling/BUDGET.md` (EUR 0 additional spend). The prior-art record is `research/radar/2026-10-24-claude-orchestration.json` (RAD-2026-016 to RAD-2026-033, including the official-marketplace sweep RAD-2026-033), the section "Orchestrator coordination prior-art pass (M4.6, 2026-10-24)" of `docs/strategy/ECOSYSTEM.md` and adoption track AT-2026-007 in `research/adoption/2026-09-initial-triage.json`; the hypothesis register entry is `research/hypotheses/H-CW2-claude-orchestration-ownership.md` and the preregistration proposal is `docs/experiments/CLAUDE_ORCHESTRATION_G1_PROPOSAL.md` with its inputs record. Hashes are maintained in `assurance.json`. This specification cannot widen any of them.

## The four surfaces and four lifecycle points

The surface ids in the first column are the single vocabulary of the whole family (`workflow-tracks`, `linked-sessions`, `agent-teams`, `batch`); every schema member, matrix cell, task, procedure and draft that names a surface uses exactly these ids, and adding a surface is a versioned schema change. The facts below are the host documentation as read on 2026-10-24 (Claude Code changelog up to 2.1.310) and the project's own code. They are documentation readings, not host observations, unless a row says otherwise; the behaviors the design depends on and that the documentation does not settle are the probes HV-6 to HV-13.

| Surface id | Isolation (documented) | State and communication (documented) | Git ground truth for a checkpoint | Notes |
| --- | --- | --- | --- | --- |
| `workflow-tracks` | Opt-in per agent through the `isolation: "worktree"` option (option list documented in the host's bundled authoring guidance; treated as inferred); without it agents share the session working directory | Agents report only to the script; no shared task list or lock | Committed or quiesced worktrees where isolation was chosen | Worktrees branch from the origin default branch unless `worktree.baseRef` is `head`; a resumed or restarted agent can re-apply edits over files other tracks touched |
| `linked-sessions` | Dispatched background sessions move into their own worktree before editing, with documented exceptions (moved or forked in place, non-git directories, `bgIsolation: none`); a Desktop session has the worktree toggle off by default | Cross-session messaging, `notify_when_idle`, `claude agents --json` for reading state (agent view is a research preview) | Per-session worktrees when isolated; a shared checkout otherwise | Delete in agent view discards uncommitted work; `~/.claude/jobs` is not a stable interface |
| `agent-teams` | None: teammates work in the main session directory | Mailbox files and a shared task list (documented rule: the task tools are present by default only on some models; presence on the model in use is unconfirmed, HV-7) | None per agent: one tree | Experimental; no resume of in-process teammates; the host's own guidance is to partition files by prose |
| `batch` | Always one isolated worktree per unit | Units report to the batch conversation | Published branch or change per unit; the layout is undocumented (HV-11) | Five to thirty units; replay certificates apply only to a chosen subset of at most four |

| Lifecycle point | What SPEC-057 provides | What it does not |
| --- | --- | --- |
| Pre-flight | Declaration, expansion, pairwise evidence, isolation and base audit | Proof that the declaration is complete or that a merge will be clean |
| Continuous | Receipts at committed or quiesced checkpoints, pull notices that expire and can be superseded | Per-tool-call monitoring, push, blocking, observation of Bash in flight |
| Recovery | Read-only classification of what a stopped or orphaned unit left behind | Resuming, reclaiming, deleting, messaging or any repair |
| Integration | Nothing new. Planned reuse of the SPEC-052 gate, by surface: `workflow-tracks` over committed work (SPEC-052 unadopted, host behavior unobserved); `linked-sessions` only if a session's branch tip is a usable commit source (inferred); `agent-teams` none, because there are no commit sources on a shared tree; `batch` not covered until probe HV-11 records the layout, and SPEC-052 does not mention `/batch` | Any integration evidence of its own, or a claim that SPEC-052 already covers a surface |

## Operation

1. **Declare.** The orchestrator writes one declaration record per unit (REQ-001) and pins a base. The expansion module (REQ-002) produces exact repository-relative paths, create regions, and a coverage statement. Anything not exactly expandable is partial.
2. **Pre-flight.** The expansion emits AIM `0.2.0-draft` records in the declared channel and the existing analyzer returns the pairwise classes with coverage (REQ-003). The result is `declared-only`: its quality is bounded by the declaration. Under-declaration, especially of reads, is the dangerous direction and is measured by G1, not assumed away. The result says in so many words that disjoint file sets are not evidence of a clean merge: the literature reports textual conflicts despite disjoint authored file sets caused by base mismatch, so the isolation and base audit (REQ-005) and the SPEC-052 gate remain necessary.
3. **Checkpoint.** At a point where a unit is committed or quiesced, the operator or orchestrating session runs the bundled CLI check (REQ-004). The plugin MCP has a global non-blocking admission lock, four active calls and a worktree allowlist fixed at connection, and `analyze-git` refuses a worktree that changes during its two observations; continuous checking therefore runs as a serialized CLI call at quiescent checkpoints, never as MCP polling by many agents. One rule covers every refusal (REQ-017): when the command cannot take a bounded, stable observation (lock busy, a worktree that changes between the two Git observations, an unobservable or over-bound source or input) it stops with a stable error code and produces no receipt; an error is never a result and is never read as clean or independent. Inside a produced receipt, `not-observed` and `unknown` are results about what the observation contract excludes by design (for example a unit for which no source was supplied) and are also never clean.
4. **Notice.** A checkpoint that finds a hazard can produce a notice (REQ-008): data with an epoch and an expiry that the orchestrator reads and may relay. The default strategy is Mailbox + Whisper: the pull notice (the Mailbox, which the orchestrator reads; the host already wakes the orchestrator at the end of each turn of a linked session) and, only with the SPEC-058 companion installed, `PreToolUse` `additionalContext` to the affected agent in its own session (the Whisper). Only the Mailbox is effective in this specification (REQ-009). The opt-in Megaphone (monitor or channels) and Doorbell (a script posting data to the orchestrator's own session messaging socket) are reserved for SPEC-059, are enabled only if G1 shows late notices with measurable harm and, for the Doorbell, a transport verified after G2, and need an ADR that reframes "never messages as a session" for the Doorbell.
5. **Recover.** When a unit fails or stops, the operator supplies `claude agents --json` output and the report (REQ-007) classifies what the worktree holds against the claim. The report lists information; it takes no action.
6. **Integrate.** Nothing new here. Where a surface produces commit sources (see the lifecycle table), the user's script or the human may call the SPEC-052 gate over the published commits once that specification is adopted. For more than four units the pairwise matrix can identify which subset of at most four may be certified first; the rest are listed as uncertified.

The planned bundled CLI subcommands are `expand-ownership`, `check-ownership`, `audit-isolation` and `report-recovery`. The names are provisional until the plan's design is accepted. They are read-only, are invoked by an operator or by the orchestrating session, and are **not** added to SPEC-052's constrained Bash allowlist: a gate agent never runs them.

## Known limits of the evidence

- A declaration is a claim by the orchestrator or a model. Over-claiming and under-claiming are both possible; single-author preprints report that agent self-reports over-claim shared resources; this specification has not verified those reports and relies on no figure from them (research.md, source table). The result class is `declared-only` and G1 measures declaration recall and precision against observed reads and writes.
- Exact-string resource identity is the analyzer's rule. A directory or pattern the expansion cannot enumerate exactly, a file that will be created, and an unknown tool effect become partial coverage and therefore `unknown`.
- A checkpoint observes committed or quiesced Git state at file level. Deletions, renames (rename detection is off), binaries, symlinks and submodules are unknown. Reads are never observed by Git. Bash writes, formatters, generated files and MCP tool effects are invisible unless declared.
- On a shared tree (agent teams, and sessions that edit in place) Git cannot attribute a change to a unit, so the receipt there attributes nothing to any unit: it inventories changed paths against the union of the declarations, makes no per-unit comparison and truncates over-long lists with a recorded total instead of refusing. Orchestrator, human and shared-tree writers are unattributed. The receipt reports them as `unknown` by default and does not blame a unit; only an explicit exemption rule that the orchestrator declared in the declaration excludes a path from that report.
- Pre-flight independence is not merge safety. The pre-flight false-assurance rate (pairs the pre-flight called independent that conflict under `git merge-tree` at integration) is a G1 metric.
- The dogfood datum (three fan-outs, one stale-read event that serialization avoided) is one anecdote with no outcome measured. One preprint reports that most of the races a freshness guard blocks are benign and that blocking them costs safe completions; the figure is unverified and not relied upon. It is not evidence that anything was prevented.
- Hosts change weekly and several surfaces are marked experimental or research preview by the host. Matrix rows are tied to a version and are not claims about later versions.

## Requirements and acceptance scenarios

Stages: C = pure core and read-only commands (implementation after #671, #672 and this specification's pull request have merged); H = host verification probes launched by the orchestrating Claude session after per-probe founder authorization; R = recipes, contracts and reconciliation; G = the G1 protocol; D = documents and decisions. Stage does not authorize starting; it records order. Every requirement has planned evidence only.

### REQ-001 — Declare ownership and footprints in a vendor-neutral, bounded schema

**SC-001:** Given an orchestrator's plan for 2 to 32 parallel units (on the surfaces `workflow-tracks`, `linked-sessions`, `agent-teams` or `batch`), when each unit's ownership is written as a declaration record and validated against the declaration schema, then all of the following hold.

- The record accepts only the documented members (unit id, surface id from the closed four-id set, declared base reference, reads, critical reads, writes, creates, deletes, declared dependencies, shared-resource classes, a completeness flag, provenance with an optional imported-from member, and optional explicit exemption rules for unattributed writers).
- The record rejects unknown members, any member that could carry file content, command text, prompts or transcripts, duplicate unit ids, the reserved unit id `unattributed`, more than 32 units, more than 512 path entries per unit, strings over 256 characters, strings that contain a character of the REQ-008 text exclusion set (also when a line feed follows) and a base reference containing `..` or `//`.
- The core members contain no vendor-specific member.
- A declaration that claims completeness without a declared base is refused.

Failure and inconclusive cases: an accepted unknown or content-bearing member, a vendor-specific member in the core schema, a surface id outside the closed set, or a declaration that is accepted as complete without a base fails the requirement. A schema that cannot be validated with the pinned `jsonschema` package is an unavailable observation, not a pass. Checks that a schema cannot express (critical reads covered by reads, duplicate unit ids, dependencies naming known units, an exemption rule naming only declared paths) are validator rules with their own tests, not schema guarantees.

Verification: [procedure_req_001](validation-plan.md#procedure_req_001). Planned evidence only; obtained evidence: none.
### REQ-002 — Expand ownership to exact paths with explicit path identity and conservative coverage

**SC-002:** Given a declaration with literal paths, directories and glob patterns and a pinned base tree, when the pure expansion module (planned `agent_braid/ownership.py`) expands it, then all of the following hold.

- Literal paths and patterns that match files at the pinned base become exact repository-relative paths under one normalization rule (separator, `./`, `..`, absolute to repository-relative, Unicode NFC, case-fold collision detection for case-insensitive filesystems, and symlinks that resolve inside the repository or are refused).
- `creates` entries are carried as exact paths or as prefix regions.
- Every pattern or region that cannot be expanded exactly is reported with partial coverage, so any pair that involves it is classified `unknown` or `conflicting` and never as an independent candidate.
- Two units that create the same path, or a create prefix that overlaps another unit's path, are reported as conflicting.
- The prefix-overlap rule is the semantics of `agent_braid/runtime_scheduler._overlap`, moved once into a neutral helper that both the expansion module and the scheduler import, with the scheduler's current behavior pinned by its existing tests, so that no second spelling of the rule exists.

Failure and inconclusive cases: a directory or glob silently treated as disjoint from a file it contains, a new path created by two units that passes as disjoint, a case-only or symlink alias that passes as disjoint, or an absolute and a relative spelling of one path that pass as different resources fails the requirement. Two spellings of the prefix rule in two places is a defect.

Verification: [procedure_req_002](validation-plan.md#procedure_req_002). Planned evidence only; obtained evidence: none.

### REQ-003 — Produce pre-flight evidence through the existing AIM analyzer with a closed output vocabulary

**SC-003:** Given expanded declarations for 2 to 32 units, when the pre-flight runs through the bundled CLI or through the existing plugin MCP `analyze-work` tool with `kind: aim`, then all of the following hold.

- The expansion emits AIM `0.2.0-draft` operation records in the declared channel and the existing analyzer is reused unchanged (no new analyzer, `agent_braid/analysis.py` untouched).
- Every pair keeps the existing classes independent candidate, ordered, conflicting or unknown with its coverage.
- A result involving partial coverage is never an independent candidate.
- The envelope states evidence, constraints and unknowns in a closed vocabulary and never wording that starts, schedules, approves or recommends parallel execution (a wording lint over emitted text and over the recipe and skill text rejects such terms).
- The class is `0-heuristic` and the label is `declared-only`.
- The envelope states that disjoint file sets do not imply a clean merge and that integration evidence remains SPEC-052.
- Empty read sets and undeclared shared-resource conventions (lockfiles, barrel files, generated outputs, formatters) are reported as constraints and unknowns.
- `executionAuthorization` is false.

Failure and inconclusive cases: an independent candidate returned for a pair with partial coverage, a verdict worded as permission to start or parallelize, an edit to `agent_braid/analysis.py`, a missing statement that disjoint declarations are not merge evidence, or a pre-flight that reads a declaration without a declared base fails the requirement. An unavailable plugin MCP inside workflow agents (HV-1) means the pre-flight runs from the orchestrating session or the CLI before the workflow is launched; that is the declared fallback, not a defect.

Verification: [procedure_req_003](validation-plan.md#procedure_req_003). Planned evidence only; obtained evidence: none.

### REQ-004 — Compare declared and observed footprints at committed or quiesced checkpoints

**SC-004:** Given a declaration and the Git state of each unit at a checkpoint where the unit is committed or quiesced, when the operator or the orchestrating session runs the checkpoint check through the bundled CLI, not by polling the plugin MCP, then all of the following hold.

- The receipt lists per unit the undeclared writes, the writes into another unit's declared area, the declared writes not observed, and `unknown` for deletions, renames, binaries, symlinks and submodules.
- Writers that cannot be attributed (orchestrator, human and shared-tree edits) are reported as an unattributed writer with unknown effect and never as a violation by a unit, unless a declared exemption rule explicitly excludes the path, in which case the receipt names the rule.
- On a shared working tree (agent teams, sessions editing in place) the receipt attributes no change to any unit, lists every changed path as an unattributed writer and makes no per-unit comparison.
- A list longer than its reporting bound is cut deterministically and the cut is recorded with its total in `truncations`, so a busy shared tree yields a partial receipt that is never clean and not a refusal.
- A unit for which no source was supplied, or whose commits are not a descendant of the declared base, is a per-unit `not-observed` result with a closed reason and is never clean.
- A busy lock, a worktree that changes between the two Git observations, an unobservable source, over-bound input (REQ-017) or an existing output path is a refusal, that is an error with a stable code and no receipt (the single rule of REQ-017).
- The class is `1-syntactic`, limited to exact repository-relative paths at the named snapshot (on a shared tree it says only that these paths changed, not who changed them).
- The receipt states what was observed (committed or quiesced Git) and what was not (Bash in flight, MCP effects, reads, uncommitted work of active writers).
- It carries a snapshot digest, paths and hashes only.

Failure and inconclusive cases: a refused, unstable or unobservable snapshot that appears as a receipt or as clean, a `not-observed` unit read as clean, a rename or delete reported as a clean or complete observation, an orchestrator edit attributed to a unit, an unattributed writer silently dropped without a declared exemption rule, or a receipt that carries file content fails the requirement. Observing a worktree that is being written is a refusal, not a result. On a shared tree, an attribution of any change to a teammate or a refusal caused only by a long list of changed paths fails the requirement.

Verification: [procedure_req_004](validation-plan.md#procedure_req_004). Planned evidence only; obtained evidence: none.
### REQ-005 — Audit isolation and base as configuration observations

**SC-005:** Given the orchestrator's repository, the documented Claude Code settings files and, optionally, the text of a user's workflow script, when the isolation and base audit runs, then all of the following hold.

- It reports as observations and not as verdicts whether units share a working tree (current directory versus repository root versus `git worktree list`, and session working directories read from supplied `claude agents --json` output, reported as booleans and counts and never as stored paths).
- The configured `worktree.baseRef` (a read-only read of documented settings files, unreadable meaning unknown) compared with the local HEAD and the origin default branch, so a unit that branches from the origin default cannot silently miss unpushed orchestrator commits.
- And, for a supplied workflow script text, whether `agent()` calls lack the `isolation: "worktree"` option, labelled `inferred` because the option list is documented only in the host's bundled authoring guidance.
- Every observation names its source and is `unknown` when unreadable. The audit reads only a closed key list from settings files (`worktree.baseRef` and `worktree.bgIsolation`), never outputs or persists any other settings value (an `env` value, a token, a hook command), and persists session `name`, `waitingFor` and `cwd` from the supplied listing in no output (they are used in memory to compute the booleans and counts only). The class is `0-heuristic`.

Failure and inconclusive cases: an unreadable setting reported as a value, a verdict worded as safe or unsafe, an observation without a named source, a settings value outside the closed key list or a session `name`, `waitingFor` or `cwd` in any output or log, or the audit executing the host binary fails the requirement. The `agent()` option lint is a text heuristic over a user-supplied file and never proves isolation.

Verification: [procedure_req_005](validation-plan.md#procedure_req_005). Planned evidence only; obtained evidence: none.
### REQ-006 — Publish a per-surface capability and assurance matrix with host versions and preview labels

**SC-006:** Given the four surface ids (`workflow-tracks`, `linked-sessions`, `agent-teams`, `batch`) and the lifecycle points pre-flight, continuous checkpoint, recovery and integration, when the matrix document and its checker are reviewed, then all of the following hold.

- Every surface and lifecycle cell records a capability, a status (planned, deferred, reuse of SPEC-052 unverified, not covered), the Article 13 class, the owner specification (or `none`), the minimum Claude Code version with its documentation basis, a `preview` label where the host marks the surface experimental or a research preview, and an evidence status (documented, inferred, unconfirmed or host-observed).
- The surface ids are a closed set shared with the declaration schema, the policy-profile attestation, the SPEC-058 guard matrix and the SPEC-059 contracts, and a checker rejects any other spelling.
- Codex, cloud sessions, Remote Control and other-machine sessions, the VS Code extension and Windows ledger support are listed as `not covered`.
- An integration cell never says covered while SPEC-052 is unadopted and its host probes are unobserved, and the `batch` integration cell is not covered until HV-11 because SPEC-052 does not mention `/batch`.
- The checker rejects a cell marked host-observed without a receipt path, a cell without a class, a missing preview label for agent teams and agent view, and any wording that says a surface is enforced.

Failure and inconclusive cases: a cell that claims verified or enforced behavior without a receipt, a surface that is silently absent or spelled differently, or a host version that is not recorded fails the requirement. A matrix row is a statement about documentation or an observation at a stated version, never a claim about later versions; where two matrices of the family state different minimum versions for one surface they must name the different capabilities that explain the difference.

Verification: [procedure_req_006](validation-plan.md#procedure_req_006). Planned evidence only; obtained evidence: none.
### REQ-007 — Report orphans and recovery state read-only

**SC-007:** Given the output of `claude agents --json` (with or without `--all`) saved to a file or supplied on standard input, and the Git state of the units' worktrees, when the recovery report runs, then all of the following hold.

- It classifies each unit as untouched, dirty, published, conflicting or unknown from the observed Git state against the declared claim, lists overlap with units that are still live, and never reclaims, resumes, deletes, messages, restarts or launches anything.
- Agent Braid never executes the `claude` binary (the operator supplies the input).
- Input that is not parseable JSON or exceeds the bound is a refusal (an error, REQ-017), while input that parses but has a missing, renamed or unknown field or value yields a per-unit `unknown` naming the field.
- Interfaces without a documented stable form (the agent-teams task directory, workflow journals) are best-effort, labelled `inferred` and fail soft.
- A unit with uncommitted work in a worktree that the host's agent-view delete would discard is listed as a warning datum.
- The report persists no session `name`, `waitingFor`, `cwd` or other free text from the listing (only the unit id, the closed state and kind enumerations, booleans, counts and an input digest). The class is `0-heuristic`.

Failure and inconclusive cases: any action beyond reading (a delete, a resume, a message, an executed `claude` command), a guessed value for a missing field, a failed unit reported as untouched without Git evidence, an agent self-report used as evidence, or a persisted session name, waiting text or directory fails the requirement.

Verification: [procedure_req_007](validation-plan.md#procedure_req_007). Planned evidence only; obtained evidence: none.
### REQ-008 — Emit epoch-stamped hazard notices as data with injection-safe repository strings

**SC-008:** Given a pre-flight verdict or a checkpoint receipt that contains repository-derived strings (paths, branch names, commit subjects, task text), when a hazard notice is built for the orchestrator to read (the Mailbox), then all of the following hold.

- The notice carries a notice id, an epoch (digest of the declaration and observation snapshot), a valid-until time, an optional superseded notice id, a recheck instruction chosen from a closed list that contains no repository text, and structured hazard items.
- Every repository-derived string is escaped (each character of the text exclusion set, namely Cc and C1 controls, Cf format characters including bidirectional and zero-width characters, U+2028, U+2029 and tag characters, is replaced by visible text), bounded to 256 characters, and placed only in labelled data fields, never in an instruction field.
- The notice schema enforces exactly that rule, so it rejects a string that still contains an excluded character or ends with a line feed, a `validUntil` that is not a UTC time of the stated shape and duplicate unit ids in a hazard item, without relying on a format checker.
- Adversarial fixtures (a file named like an instruction, a branch name with directives, a commit subject with markup, an oversized name) leave the notice schema-valid and the instruction fields byte-identical.
- The notice is delivered only as data (a file or standard output) that the orchestrator reads, expires and can be superseded.
- It carries no file content, command text or transcript.
- The same escaping and bounding rules are the contract that any rendering of the notice by a later component (the SPEC-058 Whisper, the SPEC-059 ledger notice) must reuse byte for byte.

Failure and inconclusive cases: repository text in an instruction field, a notice without an epoch or expiry, an unbounded string, a string with a character of the exclusion set or a trailing line feed that validates, a `validUntil` of the wrong shape that validates, or an imperative sentence generated from repository text fails the requirement. The schema patterns end with `(?!\n)$` because the pinned Python validator lets a bare `$` match before a final line feed; seeded fixtures cover each character class and a trailing line feed. A notice does not authorize anything and does not claim to be heard by any session.

Verification: [procedure_req_008](validation-plan.md#procedure_req_008). Planned evidence only; obtained evidence: none.
### REQ-009 — Own the orchestration-settings schema, with pull notices as the only effective strategy and a versioned extension point

**SC-009:** Given a settings record that may be present at conversation, repository and user scope, when the settings are resolved for a run, then all of the following hold.

- The record accepts `notificationMode` (`pull` or `push`), `notificationStrategy` (`mailbox-whisper`, `megaphone` or `doorbell`) and `guardMode` (`off`, `audit`, `warn` or `block`) and nothing else outside a namespaced `extensions` member.
- The resolver applies the most specific scope (conversation over repository over user).
- A `block` guard mode set at repository or user scope is a floor that a more specific scope cannot lower, so the resolved guard mode is `block` and the resolution records the floor and the scope it came from.
- Settings are operator-owned, so the resolver reads each scope only from its defined operator-owned location (user: a file in the per-user configuration directory; repository: a file outside every working tree, keyed by the repository digest; conversation: a document the operator supplies at invocation), records where each scope came from, and refuses any other source (a tracked or untracked file inside a working tree, a symlink, a file writable by group or others) with `ERR-UNOBSERVABLE-SOURCE`.
- The block floor can come only from the repository and user locations and is as strong as their file permissions, no stronger.
- In this specification every resolved notification value yields the effective strategy Mailbox (the pull notice that the orchestrator reads), the Whisper is recorded as a SPEC-058 companion output that this specification neither implements nor enables, and a request for `push`, `megaphone` or `doorbell` is recorded with the status `reserved-for-SPEC-059` and causes no push, no network operation and no socket operation.
- Unknown values, unknown scopes and unknown top-level or scope members are rejected, as is a mode and strategy that contradict each other (`push` with `mailbox-whisper`, `pull` with `megaphone` or `doorbell`).
- The schema carries an `extensions` member at the top level and at each scope, keyed by owner specification identifier, each value carrying its own `extensionVersion` and a bounded `settings` object that this specification stores without interpreting, effectiveness or defaults, so that SPEC-059 extends the schema under its own versioned definition without a change here.

Failure and inconclusive cases: any push behavior, any network or socket call, an accepted unknown value, an effective notification strategy other than Mailbox, a guard mode lowered below a `block` floor, a value read from a location outside the defined operator-owned ones (including a tracked or untracked file inside a working tree), a floor read from the conversation scope, or an extension member that this specification interprets or treats as effective fails the requirement. The precedence, the floor and operator ownership are decided (Clarifications, 2026-10-24); the Megaphone and Doorbell remain opt-in and reserved. The locations are defined in `contracts/README.md`; they do not resist a writer that holds the operator's own file permissions, including shell access, so the floor is as strong as those permissions and no stronger. The conversation scope is supplied at invocation and can never lower a floor.

Verification: [procedure_req_009](validation-plan.md#procedure_req_009). Planned evidence only; obtained evidence: none.
### REQ-010 — Define the policy-profile schema shared with SPEC-058

**SC-010:** Given a unit's declared ownership and a requested enforcement mode, when a policy profile is written against `contracts/policy-profile.schema.json` and validated, then all of the following hold.

- The profile has the unit, the ownership envelope, the mode (`off`, `audit`, `warn` or `block`; absent means `off`; the default when enabled is `audit`) and up to three supported output targets: native host settings (`permissions.deny` and a sandbox write allowlist), a companion plugin's hook configuration (the opt-in is installing that plugin), and an exported settings snippet for manual paste.
- Hooks inside the main plugin are not representable.
- The guard output vocabulary is limited to no-opinion, ask, deny and additional context, and `allow` or any grant member is unrepresentable.
- The profile names its coverage boundary (Write and Edit tool calls; Bash only through native permissions and sandbox where host verification HV-8 confirms it) and carries an `enforcementObserved` attestation whose default is false.
- An enabled mode (`audit`, `warn` or `block`) requires non-empty `protectedControlPaths`.
- A Bash coverage of `covered-where-verified` is valid only for the native-host-settings output alone and with an attestation naming the HV-8 receipt.
- The profile states the failure behavior as data (a guard internal error or timeout is fail-open and recorded: no opinion, a record, and the liveness attestation degraded to advisory; `ask` is used only for undecidable paths in `block` mode until probe GP-2 settles it).
- The schema expresses these constraints with conditional rules where JSON Schema can, and the compiler and validator rules that it cannot express (the audit default when enabled, a mode that skips the ladder, that the envelope digest matches) are named and tested separately.
- This specification ships the schema, examples and conformance tests only, and the compiler, hooks and guard belong to SPEC-058.

Failure and inconclusive cases: a profile that validates with an `allow` decision, a grant member, a target inside the main plugin, an enabled mode without protected control paths, Bash coverage claimed without the native-settings-only output and an attestation, or an `enforcementObserved` default of true fails the requirement. The schema alone does not reject a mode that skips the ladder default (the mode member is optional by design); that is a compiler and validator rule and the procedure assigns a test to it. A compiler, hook script or settings writer appearing in this specification's deliverables is a scope defect. `NotebookEdit` is not representable: SPEC-058 proposed it, the founder decision names Write and Edit, and it would be added by a versioned schema change if the founder accepts it (planning interpretations below).

Verification: [procedure_req_010](validation-plan.md#procedure_req_010). Planned evidence only; obtained evidence: none.
### REQ-011 — Document the wave-gate recipe without shipping a fan-out

**SC-011:** Given a user who writes their own dynamic workflow, session launcher or batch plan, when the recipe document `docs/tooling/CLAUDE_ORCHESTRATION.md` (planned), the CLI help of the four subcommands and the shipped package files are reviewed, then all of the following hold.

- The recipe contains a copyable snippet of the user's own script that runs the pre-flight, branches deterministically on the returned verdict, runs a checkpoint between waves and defers integration to the SPEC-052 gate, in which the launch step is a placeholder comment (for example `// your own agent launch here`) and the snippet contains no `agent(` call and no other launch, message or resume construct.
- Agent Braid ships no workflow or script that calls `agent()` with write capability or creates a fan-out (a static test over every shipped workflow file) and the same static test scans the code blocks of the recipe and of the shipped documentation for an `agent(` call.
- The recipe states that shared files such as roadmap and program documents are serialized to one unit.
- The recipe records the dogfood datum (three fan-outs, one stale-read event, no outcome measured) with those limits and makes no value, speed or prevention claim.
- The recipe states for each surface which lifecycle points are covered and which are not. Guidance ships as repository documentation and CLI help only.
- An orchestration skill is deferred (T039).

Failure and inconclusive cases: a shipped workflow that fans out or writes, a runnable fan-out template in the recipe or in any shipped documentation, a recipe sentence that implies prevention or speed, or a snippet that launches agents from Agent Braid code fails the requirement. The dogfood datum is an anecdote and is never evidence of prevented failures.

Verification: [procedure_req_011](validation-plan.md#procedure_req_011). Planned evidence only; obtained evidence: none.
### REQ-012 — Verify host behavior by recorded probes before any assertion

**SC-012:** Given the host behaviors that the design depends on and that the documentation does not settle (HV-6 to HV-13, listed in the plan), when the orchestrating Claude session launches each probe through a workflow or derived sessions on a scratch repository on the existing subscription after the founder authorizes that probe individually, then all of the following hold.

- Each probe has a recorded outcome of pass, fail or unobserved with the Claude Code version, operating system, surface id, date and a receipt made only of counts and booleans, pinned to the host version.
- Nothing in any output or document is labelled host-observed without its receipt.
- A failed probe selects the documented fallback or removes the capability from the matrix.
- Probes create no standing hook or setting in a shared configuration.
- Coding agents prepare only log-only probe scripts, which stay outside the repository with their hashes in the receipt.
- No authorization carries from one probe to another.
- Agent Braid itself launches nothing.

Failure and inconclusive cases: a behavior asserted from documentation as if observed, a receipt that carries content, a probe that leaves a hook or setting behind, a probe launched without that probe's own founder authorization, or a quota overrun beyond the existing subscription fails the requirement. An unobserved probe is a valid report and keeps the capability labelled inferred or unconfirmed.

Verification: [procedure_req_012](validation-plan.md#procedure_req_012). Planned evidence only; obtained evidence: none.
### REQ-013 — Own the preregistered, staged G1 protocol

**SC-013:** Given the G1 proposal at `docs/experiments/CLAUDE_ORCHESTRATION_G1_PROPOSAL.md` with its inputs record, written alongside this specification and not yet frozen, when its structure is checked against this requirement and the founder freezes it as a separate act, then all of the following hold.

- The proposal states the baseline arm A0 (prompt partitioning, the host isolation flag where it applies and the SPEC-052 gate), the advisory arms A1 and A2, the opt-in guard arms A3a (audit mode) and A3b (block mode) and a native-controls-only comparison (the host's own `permissions.deny` and sandbox write allowlist without any Agent Braid component; its identifier is set by the G1 proposal), so that the guard is compared with what the host already provides.
- The staging, in which stage 1 (A0 to A2) runs first on two surfaces and stage 2 (A3) starts only after the founder reads the stage 1 report and records a separate decision.
- The sentence that SPEC-058 must be implemented as an unreleased engineering candidate (behind the G1 gate) before arm A3 can run, and that adoption or release happens only after G1 gate GG passes and the ADR is adopted.
- That the planned run count and every threshold are fixed before the freeze and never changed afterwards.
- The four surfaces (`workflow-tracks`, `linked-sessions`, `agent-teams`, `batch`) each with a minimum number of eligible runs and each claimed or dropped on its own.
- Paired task sets with repetitions and a recorded permutation seed.
- The primary metrics (conflicts prevented or caught earlier than the SPEC-052 gate, parallelism retained, false blocks, bypasses, the pre-flight false-assurance rate, declaration recall and precision, enforcement liveness, overhead and notification volume).
- The three gates with their semantics (GA for the advisory arms, GN for pull digests as a prerequisite for planning G2, GG for the guard, with the stated order of evaluation in which a failure outranks an inconclusive outcome and a pass permits only the planning or release consideration of the dependent specification).
- The limit that the benefit criterion CA1 is an existence screen on designed strata on at least two surfaces and says nothing about prevalence.
- That gate GG needs at least one claimed surface.
- Pre-stated kill criteria.
- EUR 0 additional spend on the existing subscription with Sonnet at medium effort and a downgrade to observational findings before launch when the paired arms are infeasible.
- The host version recorded per run.
- Designed-overlap runs reported separately and never used for prevalence.
- No speed claim.
- The decision on whether `batch` has a pre-flight arm, which the founder takes after probe HV-11 records the layout and before the freeze (T043).
- A structural checker and tests (drafted by the G1 track) pin these elements once the proposal is frozen.
- G1 results are an input to SPEC-058's release decision but not a precondition of the advisory core's implementation.

Failure and inconclusive cases: a proposal that omits an arm, a stage, a metric, a gate, a kill criterion, the unreleased-candidate sentence, the EUR 0 rule or the downgrade rule, that relaxes a threshold or the planned run count after data exist, or that states a speed claim fails the requirement. Fewer eligible runs than the stated minimum is an inconclusive report. Consistency between the proposal and this requirement is established by the checker and by the review recorded under T032, not assumed.

Verification: [procedure_req_013](validation-plan.md#procedure_req_013). Planned evidence only; obtained evidence: none.
### REQ-014 — Specify optional interoperability inputs, documentation now and adapters deferred

**SC-014:** Given third-party coordination tools that may already hold a team's claims or conflict predictions (Clash, mcp_agent_mail, git-kura, Gas Town and Beads), when the interoperability contract document is reviewed, then all of the following hold.

- It defines input-only imports as declared or observed inputs with the provenance `imported` plus an `importedFrom` member naming the tool and version (rendered `imported:<tool>@<version>`), never as authority and never as a grant.
- It positions Agent Braid as an evidence gate that such a tool's verification step may call through documented interfaces, without coupling.
- Every import is optional, bounded, read from files offline and not implemented until the tool's output format is verified on a dated version and there is demand or G1 evidence for it.
- No adapter code ships in this specification's first releases.
- The document makes no claim about those tools beyond what the dated sources show, each such statement citing its source and date (the radar entries RAD-2026-016 to RAD-2026-020 and the repository metadata read read-only on 2026-10-24) and none being used as parity or behind evidence unless the radar classification itself supports it.

Failure and inconclusive cases: an import path that treats another tool's state as authority, a network or process call to another tool, a claim about a competitor that the dated sources do not support, a characterization without a dated source, or adapter code in the first releases fails the requirement.

Verification: [procedure_req_014](validation-plan.md#procedure_req_014). Planned evidence only; obtained evidence: none.
### REQ-015 — Bound uniqueness and market claims by a dated prior-art pass

**SC-015:** Given the market and literature research recorded in research.md, the dated pass recorded in `research/radar/2026-10-24-claude-orchestration.json` (RAD-2026-016 to RAD-2026-033, including the official-marketplace sweep of 315 plugins), `docs/strategy/ECOSYSTEM.md` and adoption track AT-2026-007, and the claim discipline of the repository, when the prior-art pass is repeated or extended under T002 and the wording of the specification set, the recipe and any skill text is checked, then all of the following hold.

- A prior-art record with its query set, sources, date and results exists before any public wording that says unique, first or only.
- Until then the only permitted wording is the single bounded sentence recorded in ECOSYSTEM.md ("In a dated pass on 2026-10-24 (query set recorded in the radar snapshot), no surveyed shipped Claude Code plugin or coordination tool README was found that declares read/write effect hazards with explicit coverage, or that provides order-independence evidence from bounded replay. This is absence within the surveyed set, not a statement about the whole market, not a claim of novelty over the literature, and not evidence of user demand."), or its shorter form `no surveyed shipped plugin found` with the same query set and date.
- Parity and behind items are listed (plain write exclusion and leases, glob ownership, hook-based blocking, textual conflict prediction, symbol-level overlap (DriftWatch), declared-footprint pre-flight scheduling (OpenWeft, Orchestune), combined-tree integration checks that also name missing evidence (Radar) and merge queues with verification gates (SVRF, Gas Town Refinery), shared claims and liveness recovery, and the quick wins), and syntax-aware textual merge (Mergiraf) is listed as complementary.
- `unknown` as a first-class result is not claimed as a differentiator by itself, because Radar and other tools report missing evidence.
- Only the combination of an Article 13 compatibility class, pairwise classification that includes unknown, declared read/write hazards and the declared-versus-observed receipt is retained as a bounded, untested candidate.
- The literature (STORM, Atomix, S-Bus, MPAC, Claim Plane) is cited as prior art for the technique so that novelty is stated as an application to Claude Code agent fleets and not as a new technique.
- The pass is repeated before publication wording, before SPEC-058 release and at M4.6 closure.
- A wording lint rejects unbounded superlatives, the words unique, only, first and "nobody offers", and a standalone unknown-as-differentiator claim.

Failure and inconclusive cases: an unbounded superlative, a competitor characterization without a dated source, a stale statement that the marketplace or topic sweeps were not done where the radar records them, or a feature claimed as a differentiator that the research records as parity, behind or easily copied fails the requirement. Absence of a tool in an aggregator is not evidence that it does not exist. Archived or very small projects are not evidence of demand.

Verification: [procedure_req_015](validation-plan.md#procedure_req_015). Planned evidence only; obtained evidence: none.
### REQ-016 — Keep the governance boundary and reconcile with HAR.3

**SC-016:** Given the repository's authorities (ADR 0021, ADR 0024, AGENTS.md, Articles 12, 13 and 20) and specs/050 tasks T005, T006 and T011, when the deliverables of this specification are inspected and its tests run, then all of the following hold.

- No code, workflow, skill or package file from this specification launches, messages as, resumes, authorizes or stops a session, agent, team or batch.
- Adds a hook, mod, monitor or channel to the main plugin (the existing no-hooks inventory assertions of `tests/test_plugin_package.py` stay unchanged).
- Adds a model-callable grant or MCP tool.
- Or executes the `claude` binary.
- Every emitted object has `executionAuthorization` false.
- The new commands are operator or orchestrator invoked and are not added to SPEC-052's constrained Bash allowlist.
- The cross-reference to specs/050 T005, T006 and T011 states what is reused and that this specification builds no second hook-profile compiler or orchestration planner.
- The documentation and tracking consistency fixes are recorded as T029; the integrator made most of them in this pull request and the remaining one (the cross-note in the SPEC-052 ADR proposal's no-go list) is not made by this specification's track.

Failure and inconclusive cases: a launch, message, resume, hook, mod, monitor, channel or grant path; an executed host binary; a new MCP tool; or a duplicated compiler or planner fails the requirement. A conflict with a MUST in an authority blocks the work and is not resolved by this specification.

Verification: [procedure_req_016](validation-plan.md#procedure_req_016). Planned evidence only; obtained evidence: none.
### REQ-017 — Fail closed within fixed bounds, refuse with errors and keep records free of content

**SC-017:** Given any input to the new commands (declarations, Git state, `claude agents --json` output, settings files, script text), when the commands run, including on oversized, malformed or unreadable input, then all of the following hold.

- All new commands are read-only, local and offline (no network and no socket).
- The commands refuse over-limit input before analysis (declaration at most 1 MiB, at most 32 units, at most 512 paths per unit, strings at most 256 characters, `claude agents --json` input at most 1 MiB, Git observation within the existing bounded Git helpers).
- The commands never write into the repository or the registry.
- The commands write results only to explicit new private paths and refuse existing paths.
- The commands store paths and hashes only (no file content, command text, prompts, transcripts, session names or settings values outside the closed key list).
- One rule governs every refusal: a busy lock, an unstable snapshot (a worktree that changes between the two Git observations), an unobservable source, an over-bound or malformed input and an existing output path end the command with a stable error code from a closed list (`command-error.schema.json`), a nonzero exit status and no result object, so that a refusal cannot appear as a receipt, a pre-flight verdict or a report and cannot be read as clean or independent, while `unknown`, `not-observed` and a recorded truncation inside a produced result are Article 13 outcomes of the observation contract and are also never clean (an observed list longer than its reporting bound is truncated and recorded, which is a result and not a refusal).
- Nothing is collected by telemetry now: the exclusion list below is part of this specification, and a later SPEC-047 vocabulary may add only the aggregate families named in task T041 after SPEC-047 and ADR 0025 are adopted and the producing feature ships.

The never-collect list for any future telemetry about these commands and their companions is: paths and hashes; branch, reference and commit identifiers; prompts, messages and transcripts; free text; unit and pair identities; sub-day timestamps; exact durations, token counts and costs; exact model and host build identifiers; per-user bypass and false-block counts; and anything taken from G0 or G1 manifests. Granularity is none. Planned validator tests (T040) reject any record or fixture bound for telemetry that carries a member from these categories, and a seeded violating fixture must fail.

Failure and inconclusive cases: an over-limit input that reaches analysis, a write outside an explicit new path, a refusal that appears as a result, any content in an output, a telemetry record, or a telemetry-bound member from the never-collect list, fails the requirement.

Verification: [procedure_req_017](validation-plan.md#procedure_req_017). Planned evidence only; obtained evidence: none.
## Scientific boundaries and compatibility

Claim separation. *Analogy*: none relied upon (clause zero; Article 18). *Hypotheses* (not requirements; no observation exists). The hypothesis register entry H-CW2 (`research/hypotheses/H-CW2-claude-orchestration-ownership.md`) has three parts, and this family maps them without duplicating them: part (a), the advisory arms A1 and A2, is carried here as H-OR1 and H-OR2; part (b), pull digests of arm A2 against A1, is carried by SPEC-059 as H-LD1 (SPEC-057 states no separate hypothesis for it: the REQ-008 notice is the artifact that arm A2 tests); part (c), the opt-in guard, is carried by SPEC-058 as H-OR3. H-OR1: on real Claude Code parallel runs a declared-ownership pre-flight together with a checkpoint receipt catches or prevents integration failures earlier than prompt partitioning plus the SPEC-052 gate, without serializing most of the work (criteria CA1, CA2 and CA5 of gate GA). H-OR2: the pre-flight false-assurance rate and the declaration under-coverage are small enough for the advice to be useful (hard criteria CA3, CA4 and CA6 of gate GA). The disproof conditions are stated in the register entry and the G1 proposal and are not restated here: any unmet hard criterion with its denominator met, or an unmet benefit criterion, falsifies; an unmet denominator minimum is inconclusive; fail outranks inconclusive once minimums are met; inconclusive is not support; and the evaluation order in the proposal governs. The gates are GA (advisory arms; informs this specification), GN (arm A2 against A1; a pass permits only the planning of G2) and GG (guard arms; gates SPEC-058). *Empirical*: nothing obtained. *Formal*: no new result; the analyzer's definitions are unchanged. Null results, counterexamples, an inconclusive G1 and a host that cannot support a capability are valid outcomes, and the protocol's completion does not require any hypothesis to be true.

Domain. Claude Code on the local machine, four documented parallel surfaces, Git repositories, file-level resources, at most 32 units per declaration. Not covered: Codex, cloud and remote sessions, the VS Code extension, other hosts, and non-Git workspaces.

Observation contract. Declared ownership as written by the orchestrator; committed or quiesced Git state at named snapshots; documented host configuration read from a closed key list of settings files; session state as printed by the host's own `claude agents --json` and supplied by the operator, used for booleans and counts. Absent, unreadable or excluded observations are `unknown` or `not-observed` and never mean clean; an observation the command cannot take in a bounded and stable way is a refusal (an error), not a result.

Execution contract. Read-only, local, offline, bounded; no model invocation by the commands; no grant, launch, message, resume or merge; `executionAuthorization` is false in every emitted object; the plugin MCP tool set is unchanged.

Article 13 classes (decided 2026-10-24). The declared-versus-observed exact-path receipt is `1-syntactic`; the pre-flight, the recovery report and the isolation audit are `0-heuristic`; `notAGuarantee` is true on every result. A class is a claim by the producer, not verified evidence.

Compatibility. Additive. No change to `agent_braid/analysis.py`, AIM `0.2.0-draft`, SPEC-023, the SPEC-052 gate or its schemas, the plugin MCP tools, limits or grants, or the existing five product skills. The new CLI subcommands, pure module and schemas are the only additions. Any plugin-level change (a new or edited skill, a workflow, a hook component) is outside this specification and needs the ADR amendment that SPEC-058 and the SPEC-052 proposal discuss. The next plugin release number is the founder's decision and is not implied.

Not claimed: faster delivery, fewer conflicts, safety of any integration, completeness of any declaration, that more agents is better, that a surface is covered because a row exists, or that Agent Braid is the only tool of its kind.

## Clarifications

Recorded with the founder on 2026-10-24 in three rounds. These are binding planning decisions for the specification set. They are not acceptance, adoption, freeze or signature of anything.

### Round 1

- **Split:** SPEC-057 is the advisory core and is specified now, with implementation after #671, #672 and this specification's pull request have merged. SPEC-058 (opt-in guard) is specified now and its implementation is blocked by G1 and an ADR amendment. SPEC-059 (ledger and active push) is specified now (reduced to a sketch in Round 3) and its implementation is blocked by G2, the "Coordination across tools" contract of specs/039 (identity, concurrency, idempotency, recovery), and its own ADR.
- **Surfaces:** all four: dynamic-workflow tracks (`workflow-tracks`); linked or derived sessions launched from another session that communicate continuously (`linked-sessions`: desktop `start_session`, agent view and background sessions, cross-session messaging); agent teams, with no worktrees (`agent-teams`); and `/batch` (`batch`). **Lifecycle:** pre-flight, continuous (checkpoints) and recovery; integration stays SPEC-052.
- **Control:** a single policy compiler (SPEC-058) turns declared ownership into an enforcement profile with three supported outputs: (D) native host `permissions.deny` plus a sandbox write allowlist, preferred where host verification confirms it applies to subagents and teammates and because it covers Bash; (A) a companion plugin (working name `agent-braid-guard`) with `PreToolUse` on Write and Edit and `TaskCreated` hooks, where installing it is the opt-in and the main plugin keeps its no-hooks property; (B) an exported settings snippet for manual paste. Output (C), hooks inside the main plugin, is **rejected**. The modes ladder is `off`, `audit` (records "would have blocked"), `warn`, `block`; the default when enabled is `audit`. The guard's output vocabulary is limited to no-opinion, ask, deny and additional context; it never says allow and never holds grants. This specification owns the shared policy-profile schema (REQ-010); the compiler is SPEC-058.
- **Evidence:** a preregistered G1 experiment, owned by this specification, is required before SPEC-058 is released. Cost is EUR 0 additional: the founder's subscription, Sonnet at medium effort, small paired designs, with a downgrade to observational findings if paired arms are infeasible (REQ-013).
- **Boundaries:** Agent Braid never launches, messages as, resumes or authorizes sessions or agents; it ships no fan-out; ADR 0021 forbids model-callable grants; the MCP global lock means continuous checks run through the CLI at quiescent checkpoints and not as MCP polling; the scope is Claude Code only for now, and Codex, cloud, Remote Control and the VS Code extension are recorded as not covered.

### Round 2

- **Notifications:** the default strategy is Mailbox + Whisper. The Mailbox is the pull notice that the orchestrator reads (the host already wakes the orchestrator at the end of each turn of a linked session). The Whisper is `PreToolUse` `additionalContext` delivered to the affected agent in its own session, a SPEC-058 companion output. The Megaphone (monitor or channels) and the Doorbell (a script posting data to the orchestrator's own session messaging socket) are opt-in in SPEC-059 only; they are enabled only if G1 shows late notices with measurable harm and, for the Doorbell, a transport verified after G2; the ADR must reframe "never messages as a session" for the Doorbell. In this specification only the Mailbox is effective (REQ-008, REQ-009).
- **Settings:** the most specific scope wins (conversation over repository over user), except that a `block` set at repository or user scope is a floor a conversation cannot lower. Settings are operator-owned (REQ-009). This replaces the earlier to-confirm assumption.
- **G1 gate GA failure:** SPEC-057 makes no pre-flight value claim; its scope narrows to the structural parts (declaration schema, isolation and base audit, checkpoint receipt and recovery report as observations), and SPEC-058 and SPEC-059 are not adopted, as the G1 proposal states.
- **Orchestration skill:** deferred, not discarded. Task T039 is blocked by the ADR amendment and by G1 gate GA; if GA fails, guidance stays documentation and CLI help. Guidance ships now as repository documentation and CLI help (REQ-011).
- **Telemetry:** narrow-go, deferred. Nothing is collected now. Later, and only after SPEC-047 and ADR 0025 are adopted and the producing feature ships, an additive SPEC-047 vocabulary may carry families A (pre-flight verdict mix), B (guard decision mix by mode, including would-have-blocked) and D (hook and gate duration buckets); family C (host drift canary) only after G1; granularity is no. The never-collect list in REQ-017 is a specification exclusion with planned validator tests (T040, T041).
- **G1:** staged, with stage 1 first and on two surfaces; the planned run count and the thresholds are fixed before the freeze; downgrade to observational findings if EUR 0 is infeasible. The designed-stratum existence criterion CA1 on at least two surfaces is stated as a limit; gate GG needs at least one claimed surface; whether `batch` gets a pre-flight arm is decided after the layout probe and before the freeze (REQ-013, T043).
- **Differentiation wording:** "unknown as a first-class result" is dropped as a standalone differentiator, because Radar (Jake-Network/radar) and other tools report missing evidence. Only the combination (Article 13 compatibility class, pairwise classification including unknown, declared read/write hazards, declared-versus-observed receipt) is retained as a bounded, untested candidate, under the claim "no surveyed shipped plugin found" with the query set and the date. git-kura and Radar stay as radar entries; their existence was confirmed with read-only GitHub API calls on 2026-10-24 (REQ-014, REQ-015).
- **Unattributed writers:** orchestrator, human and shared-tree writers are `unknown` by default; only an explicit declared exemption rule excludes them (REQ-001, REQ-004).
- **Article 13 classes:** the declared-versus-observed exact-path receipt is `1-syntactic`; the pre-flight, the recovery report and the isolation audit are `0-heuristic`; `notAGuarantee` always.
- **Guard failure behavior:** a guard internal error or timeout is fail-open and recorded (no opinion, a record, liveness degraded to advisory). `ask` is kept only for undecidable paths in `block` mode until probe GP-2 (REQ-010; SPEC-058).
- **Interoperability:** documentation now; import adapters deferred until there is demand or G1 evidence (REQ-014).
- **Later decisions:** G2 is decided after G1. Companion names and distribution are decided after G1 (the names are working names, in the same marketplace, with publication only on release acceptance). The two companions are separate: `agent-braid-guard` (SPEC-058) and a notification and ledger companion (SPEC-059).
- **Agent-teams ledger:** whether an attributed-write ledger serves agent teams is decided after probe HV-L7 (SPEC-059); otherwise guidance is documentation plus per-teammate checkpoints (T044).
- **Hypotheses:** H-CW1 and H-CW2 are indexed only in `research/hypotheses/README.md` now (the integrator does it); `RESEARCH.md` changes in a separate authority change.
- **Guard ADR proposal:** reviewed now and adopted together with the G1 outcome.
- **Host probes HV-6 to HV-13:** the orchestrator (the Claude main session) launches them through workflows or derived sessions after the founder authorizes each probe; agents prepare log-only scripts; the evidence is pinned with the host version (REQ-012).
- **No `PostToolUse` Bash observer now:** the checkpoint receipt covers the worktree surfaces; agent teams are decided with the ledger after HV-L7.
- **G1 arm A3 blocker:** SPEC-058 must be implemented as an unreleased engineering candidate (behind the G1 gate) before arm A3 can run; adoption or release happens only after G1 gate GG passes and the ADR is adopted. G1, SPEC-057 and SPEC-058 state exactly this.

### Round 3

- **SPEC-059 is a sketch:** a short specification (objective, limits, the decisions taken: Mailbox + Whisper by default; Megaphone and Doorbell opt-in, gated by G1 late-notice harm and by G2; a separate notification companion; an attributed-write ledger decided after probe HV-L7; interoperability as documentation only), with its drafted coordination contract kept as a draft for founder review. It no longer carries a requirement and task breakdown; its assurance record is minimal and blocked by G2.
- **G1 stays staged** and gains a native-controls-only comparison: the host's own `permissions.deny` and sandbox write allowlist without any Agent Braid component (REQ-013).
- **Guard ADR proposal:** reviewed now and adopted together with the G1 outcome.
- **Settings locations:** the operator-owned locations are defined in `contracts/README.md` so that the block floor is implementable; they are a proposal for the founder to confirm (planning interpretations below).

### Planning interpretations by the drafting track (proposed; not founder-approved)

These choices fill gaps the decisions leave open. They are listed so the founder can accept, amend or reject them; none is recorded as approved.

- **CLI, not agents:** the four new subcommands are invoked by an operator or by the orchestrating session. They are not admitted to SPEC-052's constrained Bash allowlist, so gate agents never call them, and this specification needs no amendment to SPEC-052 REQ-016.
- **One refusal rule:** a busy lock, an unstable snapshot, an unobservable source, an over-bound or malformed input and an existing output path are errors with stable codes and produce no result object (REQ-017); per-unit `not-observed` is reserved for a unit with no supplied source or one that is not a descendant of the declared base. This resolves the earlier contradiction between REQ-004 and REQ-017.
- **Operator-owned locations:** the user location is the per-user configuration directory; the repository location is outside every working tree, keyed by the repository digest; the conversation scope is supplied at invocation; the floor can come only from the first two (`contracts/README.md`). Proposed, not founder-approved.
- **Coverage tools:** the founder decision names `Write` and `Edit`, and the policy-profile schema admits only those. `NotebookEdit`, which SPEC-058 proposes, needs founder acceptance and a versioned schema change.
- **Minimum host versions:** the matrix records, per cell, the first changelog entry that names the capability (read-only reading of the public changelog on 2026-10-24); that is documentation, not a support claim, and SPEC-058's matrix may state a different version for a different capability of the same surface (for example the `TaskCreated` hook).

## Evidence and unresolved questions

Obtained evidence: none. Human review pending. Nothing is frozen, signed, run or approved. The host-verification outcomes HV-6 to HV-13 are all unobserved. The G1 proposal, its inputs record and its structural checker exist as drafts written by the G1 track and are unfrozen; consistency with REQ-013 is checked by the review under T032 and by that checker, and is not assumed.

Settled by the Clarifications above and not open: the split into three specifications (SPEC-059 reduced to a sketch), the surfaces and lifecycle points, the control outputs, the notification strategy, settings precedence, G1 staging and the other items recorded there. They are not restated.

Genuinely open, to be answered by the founder or by observation:

- **Receipt class:** whether `1-syntactic` stays the right label after the first obtained evidence (the label is decided; its adequacy is observed).
- **Minimum Claude Code version per capability:** the matrix states first-changelog versions; the founder confirms the support floor.
- **`batch` pre-flight arm:** decided after HV-11 and before the freeze (T043).
- **Agent-teams ledger:** decided after HV-L7 (T044).
- **Host behaviors that the documentation does not settle** (HV-1 from SPEC-052 and HV-6 to HV-13): whether plugin MCP tools are visible inside workflow agents; whether hooks fire inside workflow agents, `/batch` units and in-process and split-pane teammates (documented for subagents, inferred elsewhere); whether the task tools are present on the model in use, which decides whether `TaskCreated` fires at all (documented rule; presence on the model in use unconfirmed); whether permission rules and the sandbox apply inside subagents and teammates and cover Bash; the `claude agents --json` fields on the installed version; the base that a workflow agent's worktree actually used; the `/batch` branch layout; the formats of the agent-teams task directory and workflow journals, which are not documented interfaces; and the plugin MCP process topology.
- **Prior-art coverage:** the recorded pass (RAD-2026-016 to RAD-2026-033) covered the official marketplace by a name and description filter, GitHub search and topic queries, merge-queue and semantic-merge tools and named orchestrators from READMEs; a peer-reviewed literature query and re-reads of commercial products were not done, and the pass is repeated or extended under T002 before publication wording, before SPEC-058 release and at M4.6 closure.
- **Integration with the documents the integrator owns:** the roadmap, program, status, ecosystem, SPEC-052 reference and hypotheses-index edits were made in this pull request. What remains, recorded as T029, is the cross-note in the SPEC-052 ADR proposal's no-go list that hooks are reopened only for the SPEC-058 companion plugin through a separate ADR proposal.

Record feasibility failure, null and inconclusive outcomes as valid reports.
