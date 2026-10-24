# SPEC-052: Claude workflow integration gate

**Milestone:** M4.6 — Claude Code dynamic workflows

**Status:** draft planning. Implementation, host verification, ADR adoption, release acceptance and publication are pending. Obtained evidence: none.

## Purpose and scope

Users of Claude Code dynamic workflows run several agents in isolated worktrees but receive no merge or conflict reasoning: according to its documentation the runtime applies no automatic merge and no conflict detection, and the worktree orchestrators reviewed in the radar were reported to operate at path level at most (a reading of their documentation, not reproduced here; see the packaging statement H2 below). SPEC-052 gives such a workflow a final, read-only integration gate shipped in the Agent Braid native plugin as the workflow `/agent-braid:braid-gate`.

Given a base and the committed work of each worktree agent, the gate returns Agent Braid evidence (file-level effects and interactions through existing read-only analyzers), a pairwise `git merge-tree` baseline and, for at most four operations, replay evidence and a prepared batch. The prepare step rehearses in a temporary directory and allocates no run directory. Outside the workflow, the operator grants with the existing grant policy and executes through the owned runtime, or integrates manually; the gate itself is read-only. The gate is an engineering feature, not a research protocol; its comparison against merge-tree is a bounded empirical check (REQ-015).

Agent Braid ships no fan-out. The user's own workflow creates the worktree agents; the gate only observes their committed results. It does not replace orchestration (docs/strategy/ECOSYSTEM.md): it consumes recorded commits.

What the gate adds, stated plainly. At commit level the Agent Braid primary flag is equivalent to a naive path check: the analyzer marks a pair `conflicting` exactly when both operations have a write-like effect on one exact resource, and `analyze-git` emits write effects only for added or modified files, with empty read versions and no declared dependencies, so `conflicting` means "two agents changed a common path". The only extra signal is the `unknown` labelling of deletions, renames, binaries and symlinks (partial coverage). The value of R1 is therefore packaging, labelling, a bounded replay certificate for at most four operations and refusal controls (equal-to-base, unregistered workspace, runtime-enabled registration); it is not extra detection, and no detection advantage over naive path overlap or over `git merge-tree` is claimed. REQ-015 reports the analyzer against naive path overlap as well as against merge-tree.

### Exclusions

- No transcript or tool-call analysis, and no read hazards: SPEC-053 (adapter) and the G0 experiment, after which a gate v2 may use them.
- No pre-flight partitioning of work before agents start: a possible future SPEC-054 behind gate G2, requiring the coordination-across-tools contract of specs/039 and its own ADR.
- No edits, no merge applied to any ref, worktree or the repository object store, no refs, branches, pushes, hooks, mods, plugin agents, grants, execution, runtime-mode calls or remote artifacts. The merge results the gate computes (pairwise and chained `git merge-tree --write-tree`) are ephemeral: they live only in a temporary object directory, are never applied and are discarded.
- No speed, throughput or agent-count claim; the parallel runtime speedup results are recorded NO-GO (SPEC-021 G4, SPEC-022, SPEC-038).
- No change to SPEC-023 acceptance, to Codex packaging or to existing contracts.

## Authorities

Constitution clause zero and Articles 1–3, 5–7, 9, 12–15, 19–21, 23–25. Article 12: prompts and planning never substitute for concurrency control, so every gating rule is computed by the script from schema-bound results and not by an agent's judgment, and the agents' tool surface is restricted by a host permission allowlist and by refusing runtime-enabled registrations (REQ-016), not by prompts alone. Article 13: every result declares a compatibility class and separately identifies property, evidence method, domain, assumptions, observation and execution contracts (REQ-007). Article 14: the envelope exposes the evidence and observation boundary, not only a verdict. Article 15: effect metadata without coupling the core to a vendor; the Claude workflow is an optional package component. Article 19: success is conflicts surfaced, not agent count, and real multi-worktree observation is required before workload claims. Article 20: analysis and execution stay separate. Also GOVERNANCE.md; ADR 0014 (single coordinator serializes promotion); ADRs 0019/0020 (bounded runtime); docs/architecture/PARALLEL_INTEGRATION.md (single coordinator serializes promotion; credentials, network, hooks, submodules, filters and arbitrary project commands stay disabled unless a reviewed execution profile names them: the gate's Git commands follow a fixed hardened template, REQ-006); ADR 0021 (grant issuance is never model-callable; host approval is not runtime authority); ADR 0024 native AI plugins, whose "unchanged five product skills" and "no installation/session hooks" wording requires the amendment in the feature-local [ADR proposal](adr-proposal.md) (no canonical number reserved, nothing adopted); specs/039 program route "Coordination across tools"; docs/tooling/BUDGET.md (EUR 0 additional spend). Hashes are maintained in `assurance.json`.

## Operation of the gate

Arguments: `base` (commit or branch), `sources` (list of commits or branches, one per worktree agent), `workspaceId` (an explicitly registered workspace; never inferred). Phases are strictly sequential, with no worktree isolation and no `parallel()` fan-out. The script launches at most four agents (the host may restart a stalled agent on its own, see Host restarts below): none when the arguments are refused, and exactly four on every run that completes all four agent phases (validate, analyze, baseline and finalize), including a run that ends `inconclusive` because a reference moved. A run that is refused, busy or failed in an earlier phase uses fewer, and later phases are reported `not-run`.

1. **validate** (agent 1; fixed hardened read-only Git commands and the read-only bootstrap tool `workspaces`, or `plugin workspaces` on the constrained-CLI fallback): resolve and pin full identifiers, read the registered `sourceRoot`, `resultRoot` and runtime mode of the explicit `workspaceId` (the bootstrap tool takes no admission lock), compare the repository root, and apply the rejection rules of REQ-002 and REQ-016.
2. **analyze** (agent 2; the only MCP caller holding the admission lock in this phase): MCP `analyze-work` with `kind: git` over commit sources only.
3. **baseline** (agent 3; fixed hardened read-only Git commands): pairwise `git merge-tree --write-tree --merge-base=<base>` in a temporary object directory, plus the chained merge-tree fold in the chosen order that yields `expectedFinalTree`.
4. **finalize** (agent 4; the same single-MCP-caller discipline; it always runs when the run is still live because it also re-resolves the references): for 2 to 4 operations, MCP `analyze` with the runtime request derived by the script (replay evidence and advisory plan) and, only when eligible (REQ-005), MCP `prepare` once; then re-resolve the base and every source. The bundled CLI commands `plan-git` and `verify-git` exist only on the constrained-CLI fallback path (see Clarifications), never on the MCP path.
5. **report** (script, no agent): schema-validated envelope with `executionAuthorization: false`, the assurance block and limits.

Runtime request derivation. The MCP `analyze` and `prepare` tools take a runtime request, which the script (not an agent) derives from schema-bound results: full 40-hex identifiers; `order`, a dependency-respecting order (the gate declares no dependencies, so it is the input order of `sources`, which is not a recommendation); `expectedFinalTree`, derived from the chained baseline merge results; per-operation `declaredWrites` equal to the paths the analyzer observed; empty `uncertainPaths`; 2 to 4 operations; and `runDirectory`, a name directly under the registered `resultRoot` learned from `workspaces`. `prepare` needs that registered root but does not allocate the directory. Where any field cannot be derived deterministically the planned outcome is `not-prepared` with a stated reason; the script never guesses a value.

Commit sources are required because the plugin MCP accepts worktree sources only when they exactly match an operator allowlist and reconnection. The plugin's global non-blocking admission lock admits one caller at a time and the MCP limits are 4 active calls, 32 operations, 1 MiB and 360 s; the gate adopts the stricter of these and never raises them. A moved reference is the defined stale-reference outcome: finalize re-resolves the base and each source, any difference or deletion is listed in `staleRefs`, the status is `inconclusive`, the earlier phase results remain labelled as of the pinned commits and nothing is re-analysed.

Host restarts. The single-caller and no-retry guarantees of this spec are properties of the script: it launches each phase's agent once, runs phases sequentially and contains no retry logic. They are not properties of the host. According to the Claude Code workflows page as read by the PR #671 review on 2026-10-24 (to be re-read and observed under HV-4, not yet verified here), the host may restart an agent whose output stalls automatically (shown as "attempt 2 (stalled)", up to five restarts) from the same prompt, with files already changed staying changed, and re-validates the output of an agent that has a `schema` over several attempts. The script cannot suppress this. Consequences: a restarted `analyze` or `finalize` agent may call the plugin MCP again while its first attempt is still running (a busy refusal on the admission lock) or after it completed (a second call), and a restarted `finalize` agent may call `prepare` again. Mitigations, by contract: every MCP call the gate makes is read-only and idempotent (`analyze-work`, `analyze` and the non-allocating `prepare` rehearsal create no durable state); the script requests `prepare` at most once; admission-lock refusals are reported and never retried by the script, and a busy refusal that may stem from the gate's own earlier attempt is reported as `inconclusive`, never as a clean or definitive result; no value from an agent is trusted without passing the strict result schema, so a restarted attempt's output is checked exactly like a first attempt's. `agentsUsed` counts the agents the script launched and is a lower bound when the host restarts attempts. The effect is observed, not assumed, under HV-4 (REQ-013).

## Known limits of the evidence

- `analyze-git` turns only added or modified files into write effects; deletions, renames (rename detection is off), binaries and symlinks become unknown effects with partial coverage; read versions are empty. An operation whose commit equals the base yields complete coverage and an independent candidate, a silent false negative that REQ-002 prevents by refusing.
- `conflicting` means a shared exact resource with a write-like effect: file-level, coarser than hunk merging, and read plus write on one resource counts as conflicting. `ordered` arises only from declared dependencies.
- At commit level the Agent Braid primary flag equals "two agents changed a common path" plus the `unknown` labelling of deletions, renames, binaries and symlinks (see "What the gate adds"). The inclusive flag (`conflicting` or `unknown`) is the only signal beyond path overlap; no added detection over naive path overlap is claimed.
- Replay evidence, `prepare` and the owned runtime are limited to four operations (and the CLI `plan-git`/`verify-git` on the fallback path).
- A registration with runtime enabled exposes model-callable `execute`, `recover`, `verify` and `status` tools on the same plugin MCP (agent_braid/tooling_mcp.py, tool list when `runtime_enabled`; tool definitions are the union over registered workspaces in agent_braid/plugin_mcp.py), so the gate refuses such registrations (REQ-016) and the operator uses an analysis-only registration for it.
- Uncommitted work in a worktree is not observed.


## Requirements and acceptance scenarios

### REQ-001 — Ship the braid-gate workflow in the native plugin

**SC-001:** Given the native plugin is installed in Claude Code and the operator has registered a workspace, when the operator invokes /agent-braid:braid-gate with args {base, sources, workspaceId} directly or through a nested workflow() call, then a plugin-shipped workflow script with a literal meta (name braid-gate, description, phases) starts, accepts only the documented argument fields, rejects unknown fields and missing required fields before any agent is spawned, and returns one structured result.

Failure and inconclusive cases: Any case that spawns an agent before argument validation, or accepts an undocumented field, fails the requirement; record the host and runtime used for the script check and treat a missing JS runtime as an unavailable observation, not a pass.

Verification: [procedure_req_001](validation-plan.md#procedure_req_001). Planned evidence only; obtained evidence: none.

### REQ-002 — Validate sources deterministically before analysis

**SC-002:** Given args name a base and a list of sources, when the validation phase runs, then each input is resolved to a full commit identifier and pinned; the run is refused when a source equals the base, is unresolvable, duplicates another source, resolves to a commit that is not a descendant of the base, is not present in the registered workspace repository, there are fewer than two distinct sources, or the number of operations exceeds 32, or the explicit `workspaceId` is not registered (`workspace-not-registered`) or the repository root reported by Git differs from the registered `sourceRoot` (`workspace-root-mismatch`); the registered roots come from one read-only call of the bootstrap tool `workspaces` by the validate agent, which takes no admission lock (agent_braid/plugin_mcp.py, `PluginRouter.invoke`), or on the constrained-CLI fallback from the read-only launcher subcommand `plugin workspaces` (REQ-016(e)); the run is also refused under REQ-016 rules. The refusal names the offending input and the rule, and uncommitted work is stated as not observed.

Failure and inconclusive cases: If the harness cannot reproduce a rule, keep the gap visible as an unobserved control. A source accepted that equals the base is a blocking defect because it is the known silent false negative. Neither an unregistered workspace nor a root mismatch ever falls back to another workspace.

Verification: [procedure_req_002](validation-plan.md#procedure_req_002). Planned evidence only; obtained evidence: none.

### REQ-003 — Run exactly one analysis agent over commit sources

**SC-003:** Given validated pinned commits and a registered workspace, when the analysis phase runs, then exactly one agent at a time calls the registered workspace's MCP `analyze-work` with `kind: git` and commit sources, because the plugin admission lock admits one caller; the validate agent's earlier `workspaces` call is a read-only bootstrap call and not an admission-lock caller; `analyze-git` is a bundled-CLI command used only on the constrained-CLI fallback; worktree and path sources are never used because plugin MCP worktree sources must match an operator allowlist; the structured output carries the analysis report reference, coverage, interaction classes and unknown effects without rewriting them.

Failure and inconclusive cases: A second concurrent MCP caller launched by the script, or a worktree source, is a defect; a repeated call caused by a host restart of a stalled agent is outside the script's control, is recorded under HV-4 and handled by the REQ-010 mitigations. If MCP tools are not visible to workflow agents (host-verification HV-1) the declared fallback is the bundled CLI only on the constrained-CLI conditions of the Clarifications (REQ-016, including the registry checks of REQ-016(e)) or a refusal, never a silent downgrade.

Verification: [procedure_req_003](validation-plan.md#procedure_req_003). Planned evidence only; obtained evidence: none.

### REQ-004 — Produce a replay certificate only for at most four operations

**SC-004:** Given an analysis result for N operations, when N is 2 to 4 and the analysis allows replay, then the finalize phase obtains replay evidence and the advisory plan from the plugin MCP `analyze` tool (which runs the same replay code as the CLI `plan-git`, `git_replay.produce` inside `mcp_runtime.RuntimeTools`) with the script-derived runtime request, and reports the certificate digests or its failure; the MCP surface has no `plan-git` or `verify-git` tool and the MCP `verify` tool exists only in runtime mode, which REQ-005 and REQ-016 exclude, so `plan-git` and `verify-git` run only on the constrained-CLI fallback path; for N above 4 the replay is skipped with the stated limit, and a skipped replay is never reported as a pass. When `prepare` is not called, the certificate comes from `analyze` alone and the envelope states that independent consumer verification was not performed.

Failure and inconclusive cases: Replay failure or timeout is reported as failed or inconclusive with the underlying message; do not retry in a loop.

Verification: [procedure_req_004](validation-plan.md#procedure_req_004). Planned evidence only; obtained evidence: none.

### REQ-005 — Prepare an operator batch without issuing authority

**SC-005:** Given 2 to 4 operations, complete coverage for the analysed pairs, no conflicting or unknown pair, a clean completed baseline, replay evidence from `analyze` and a runtime request the script could derive in full (order, `expectedFinalTree`, `declaredWrites` equal to the observed paths, empty `uncertainPaths`, `runDirectory` under the registered result root), when the finalization phase runs, then the gate calls the plugin MCP `prepare` tool once in serial mode and reports the batch reference for the operator; `prepare` rehearses in a temporary directory and allocates no run directory (`git_runtime.prepare_run`); with any conflicting or unknown pair, a conflicting or unavailable baseline, more than four operations, partial coverage or any underivable request field it does not prepare and states the reason (`not-prepared`), never guessing a value; it never creates, requests or accepts a grant, never calls an execute, recover, verify, status or runtime-mode tool, and never starts the owned runtime.

Failure and inconclusive cases: Any grant or execute attempt, even refused by the host, is a blocking defect of the script, prompt or host allowlist; prevention is the job of REQ-016 and the attempt is also detected by transcript inspection. Prepare errors are reported verbatim.

Verification: [procedure_req_005](validation-plan.md#procedure_req_005). Planned evidence only; obtained evidence: none.

### REQ-006 — Report a pairwise merge-tree baseline without writing repository state

**SC-006:** Given validated pinned commits that share the base, when the baseline phase runs, then for every pair the gate reports the result of git merge-tree --write-tree with the explicit merge base, computed with a temporary object directory so that no object reaches the repository, together with conflicted paths or an error; every Git command of every phase uses one fixed hardened template embedded as script constants (system and global configuration disabled, hooks, fsmonitor, external merge drivers and content filters disabled, no network or credential prompt, an explicit `GIT_OBJECT_DIRECTORY` for the baseline) following docs/architecture/PARALLEL_INTEGRATION.md; a command that cannot be hardened is reported as a stated limit and its phase as unavailable or inconclusive, never run unhardened; the baseline is reported alongside, never merged into, the analyzer verdict, and merge results are ephemeral and never applied.

Failure and inconclusive cases: Any new object or ref in the repository is a defect, and so is the execution of a sentinel hook, fsmonitor, merge driver or filter planted in the repository configuration. A Git version without merge-tree --write-tree is reported as baseline unavailable, not as clean.

Verification: [procedure_req_006](validation-plan.md#procedure_req_006). Planned evidence only; obtained evidence: none.

### REQ-007 — Return a bounded, versioned result that states its limits

**SC-007:** Given the gate finished, was refused or was inconclusive, when the result is produced, then the script returns a schema-validated envelope with executionAuthorization false, pinned base and source identifiers, operation count, per-phase status, analyzer interactions with coverage, replay and prepare status, baseline pairs, an agreement classification between analyzer and baseline, an advisory order that is `null` unless the analysis declares dependencies (the gate declares none, and the order used for `prepare` is labelled input order, not a recommendation), the number of agents used, the end-of-run stale-reference report (a moved or deleted reference makes the status `inconclusive`), an `assurance` block (compatibility class, property, evidence method, domain, assumptions, observation contract and execution contract, plus a constant `notAGuarantee` marker; the class is set by the script, is `0-heuristic`, and is not verified evidence or authorization), and explicit limits (file-level resources, coarser than hunk merging, no reads, only committed work, no speed claim).

Failure and inconclusive cases: An envelope without limits or the assurance block, or with an authorization field other than false, fails. Unknown extra fields are rejected by the schema. Echoed strings (`request`, `refusal.input`, `refusal.message`, `phases[].detail`) are untrusted text: they may carry repository-controlled or tool-controlled content, consumers must not feed them back to a model as instructions, and the recipe says so (T019); tightening the echoed fields is T047.

Verification: [procedure_req_007](validation-plan.md#procedure_req_007). Planned evidence only; obtained evidence: none.

### REQ-008 — Ship no fan-out, edit, merge, ref or hook behavior

**SC-008:** Given the packaged workflow and plugin manifest, when they are statically and dynamically inspected, then the workflow spawns at most four agents per run, strictly sequentially, none with worktree isolation, none instructed to edit files, apply a merge, push, create refs or branches, or run hooks; no agent call sets a `model` or `effort` option (agents inherit the session model); the plugin ships no hooks, mods or agent definitions for the gate; agent prompts embed only validated identifiers and schema-bound structured results, never raw repository text.

Failure and inconclusive cases: A prompt carrying commit messages or file contents, a parallel() wrapper, isolation worktree, or a `model` or `effort` option on any agent call fails this requirement. After the validate phase, a later-phase prompt that embeds a user-supplied name instead of the 40-hex identifier the script resolved also fails it; the validate agent's own prompt carries only names that passed the arguments schema pattern, and a name is data, never an instruction (T047).

Verification: [procedure_req_008](validation-plan.md#procedure_req_008). Planned evidence only; obtained evidence: none.

### REQ-009 — Keep authority and claim boundaries explicit

**SC-009:** Given the gate is used under host approval or auto mode, when the result or documentation describes what was checked, then host approval and auto mode are treated as no authority (ADR 0021), the script-computed prompts are not user authority, the operator grants outside the workflow, wording never claims faster integration, guaranteed order independence, conflict freedom or semantic correctness, and analysis is kept separate from execution.

Failure and inconclusive cases: Any speed, safety or semantic-correctness claim, or any implied approval, is corrected before acceptance; the negative parallel-speedup results (SPEC-021 G4, SPEC-022, SPEC-038) are cited, never contradicted.

Verification: [procedure_req_009](validation-plan.md#procedure_req_009). Planned evidence only; obtained evidence: none.

### REQ-010 — Degrade explicitly on busy, unregistered or limit conditions

**SC-010:** Given the plugin admission lock is busy, the workspace is not registered, MCP limits are exceeded, a timeout occurs, the workflow is disabled by the organization, or the host restarts a stalled gate agent automatically, when the gate runs, then the result is refused, busy or inconclusive with the specific condition, without retry loops in the script, without choosing another workspace, without widening limits, and with partial phase outputs preserved; a host restart is tolerated by contract (MCP calls are read-only and idempotent, a busy refusal that may stem from the gate's own earlier attempt is reported as `inconclusive`, every agent result still passes the strict schema, and `agentsUsed` counts script-launched agents as a lower bound).

Failure and inconclusive cases: Infinite or repeated retries by the script, trusting an unvalidated result from a restarted attempt, or fabricating a clean verdict after a failure, fail the requirement. The host's own restarts cannot be suppressed by the script; they are recorded, not hidden (HV-4).

Verification: [procedure_req_010](validation-plan.md#procedure_req_010). Planned evidence only; obtained evidence: none.

### REQ-011 — Package the workflow reproducibly as a Claude-only plugin component

**SC-011:** Given a clean source checkout, when scripts/build_native_plugin.py assembles the plugin, then until the ADR 0024 amendment is adopted the build excludes `workflows/` by default and includes it only with an explicit opt-in that marks the artifact engineering-only (never a releasable identity, since the version string is unchanged); with the opt-in, and by default after adoption, the workflow source under integrations/agent-braid/plugin/workflows is copied to plugin/workflows with a byte-stable inventory entry and hash, the Claude manifest discovers it, the portable (Codex) manifest and MCP configuration are unchanged and Codex ignores the directory, existing skills and the setup skill are byte-identical, and package verification rejects a missing, altered or extra workflow file.

Failure and inconclusive cases: Non-reproducible bytes, changed existing skills, a default pre-adoption build that contains `workflows/`, or an opt-in build presented as a release block the requirement; the build never modifies the frozen Git runners.

Verification: [procedure_req_011](validation-plan.md#procedure_req_011). Planned evidence only; obtained evidence: none.

### REQ-012 — Document the recipe in docs/tooling/CLAUDE_WORKFLOWS.md

**SC-012:** Given a user who runs their own Claude workflows with worktree agents, when they read the recipe, then it shows how to end a workflow with the gate directly or via nested workflow(), how to split sign-off into separate workflows, what the gate returns and does not return, how the operator grants and executes outside the workflow, the host-verification status of each unconfirmed behavior, and the claude-code versions observed.

Failure and inconclusive cases: Unverified host behavior presented as fact fails review.

Verification: [procedure_req_012](validation-plan.md#procedure_req_012). Planned evidence only; obtained evidence: none.

### REQ-013 — Verify the unconfirmed host behaviors before relying on them

**SC-013:** Given the documentation does not confirm that plugin MCP tools are available inside workflow agents, that plugin agents can be used as agentType, or that a plugin workflow can be called by name from nested workflow(), when host verification runs on a recorded Claude Code version, then each behavior (HV-1 plugin MCP tools in workflow agents, HV-2 plugin agentType, HV-3 nested call by plugin name, HV-4 resume after interruption and automatic restart of a stalled agent, HV-5 per-run approval, auto-mode prompts and the permission allowlist of REQ-016) has a recorded pass, fail or unobserved outcome with version, and the design degrades to a declared fallback or a no-go when a required behavior fails.

Failure and inconclusive cases: A failed required behavior records a negative result and triggers the fallback or kill criterion in program.md; negative outcomes are valid.

Verification: [procedure_req_013](validation-plan.md#procedure_req_013). Planned evidence only; obtained evidence: none.

### REQ-014 — Require release acceptance before any plugin-dist publication

**SC-014:** Given a candidate plugin package containing the workflow, when release is considered, then acceptance records the clean source commit, package and inventory hashes, a fresh-checkout reproduction, native install on supported hosts, the gate over the fixture matrix, update from the previous alpha and uninstall behavior, with unobserved platforms stated; publication to plugin-dist and any remote artifact remains a separate founder decision and is not part of this delivery.

Failure and inconclusive cases: Missing observations remain listed as not observed; no claim of compatibility for unobserved hosts.

Verification: [procedure_req_014](validation-plan.md#procedure_req_014). Planned evidence only; obtained evidence: none.

### REQ-015 — Check the baseline against the analyzer on a known-answer corpus

**SC-015:** Given a fixture corpus of base and branch commits with known file-level truth, including delete versus modify, rename, binary, same hunk, different hunks and untouched pairs, when the analyzer verdict and the merge-tree baseline are compared per pair, then the agreement classification (both clean, both conflicting, analyzer stricter, baseline stricter, analyzer unknown) is reported with a naive path-overlap column (paths changed by both branches relative to the base); an analyzer `conflicting` pair counts as added detection only where naive overlap missed it (expected: none at commit level, so any such pair is an analyzer-versus-naive discrepancy to explain, not a success); any case where the analyzer says independent-candidate and the baseline conflicts is a recorded counterexample, and no hypothesis of conservativeness is claimed beyond the corpus.

Failure and inconclusive cases: A counterexample is a valid finding and blocks conservativeness wording; it does not by itself fail the protocol.

Verification: [procedure_req_015](validation-plan.md#procedure_req_015). Planned evidence only; obtained evidence: none.

### REQ-016 — Restrict the gate agents' tool surface by allowlist and registration mode, not by prompts

**SC-016:** Given the gate runs under any permission mode, when the validate phase reads the registry and the agents run, then (a) the script refuses with `runtime-enabled-workspace` when any registered workspace has runtime enabled or a grant store, because the plugin MCP then lists model-callable `execute`, `recover`, `verify` and `status` tools next to the gate's own (the tool definitions are the union over registered workspaces) and a script-computed prompt is not a concurrency or authority control (Article 12; ADR 0021: host approval is not runtime authority); (b) on the MCP path the recipe and the host receipts require a host permission allowlist that allows only the plugin tools `workspaces`, `analyze-work`, `analyze` and `prepare` the fixed hardened read-only Git command templates, the exact scratch creation command `mktemp -d "${TMPDIR:-/tmp}/braid-gate.XXXXXXXX"` and `rm -rf --` of one `braid-gate.XXXXXXXX` path directly under `TMPDIR` (the only writes, a temporary directory outside the repository; the agent checks the path pattern before removal and reports `removed`, `failed` or `refused`, and a scratch that was not removed is a stated limit that prevents certification); a host that cannot express the last two narrowly makes the baseline phase unavailable (a recorded no-go), not unhardened, with the exact visible tool names recorded in HV-1 and HV-5; (c) the validate agent reports, under a strict schema, the plugin tool names visible to it, and the script refuses with `unsafe-tool-surface` when `execute`, `recover`, `verify` or `status` is among them instead of relying on instructions (an agent-reported defensive check, not enforcement; HV-1 records whether the host can deny them); (d) the constrained Bash is defined once, here and in the Clarifications: a host permission rule set in force for the session that allows only the fixed read-only Git prefixes and explicit launcher subcommands from a closed list, never the launcher binary as a whole, because the launcher also exposes grant and execute subcommands; for gate v1 the closed list is `analyze-git`, `plan-git`, `verify-git` and the read-only registry read `plugin workspaces` with no further arguments, admitted only on the constrained-CLI fallback (MCP tools not visible to workflow agents, HV-1); gate v2 (SPEC-053, blocked by G0) would add exactly one more explicit subcommand, `analyze-claude-transcripts`, usable alongside working MCP tools, as a planning amendment approved by the founder on 2026-10-24; (e) on the constrained-CLI fallback the registry rules are computed from the rows printed by `plugin workspaces` (the same fields as the MCP bootstrap tool, read live instead of from the connect-time snapshot): `workspace-not-registered`, `workspace-root-mismatch` and `runtime-enabled-workspace` apply unchanged, the `unsafe-tool-surface` check applies to any plugin tool names the validate agent reports, and the Bash allowlist, which the script cannot observe, is the only control for the launcher; the fallback refuses with `mcp-unavailable` when the registry rows cannot be obtained or parsed, and is a recorded no-go unless HV-5 recorded that the host can express the allowlist.

Failure and inconclusive cases: A grant or execute attempt, even refused by the host, a registration with runtime enabled that is not refused, or a fallback rule that matches `grant-policy-run`, `execute-policy-run` or other launcher subcommands, or a v1 rule set that admits `analyze-claude-transcripts`, is a blocking defect. A host that cannot express the allowlist is a recorded no-go input for the CLI fallback, not a pass. Limit stated: rule (a) is computed after the validate agent has already run, so for that one agent the host allowlist (b) is the only control; this is why (b) is required and recorded rather than assumed.

Verification: [procedure_req_016](validation-plan.md#procedure_req_016). Planned evidence only; obtained evidence: none.

## Scientific boundaries and compatibility

Claim separation. *Analogy*: none relied upon. *Hypotheses* (not requirements, no observation exists): H1, on add/modify-only histories the analyzer's file-level conflicting set may contain merge-tree's (the expected reason is that it is file-level; this is a reason to expect it, not a result); H2 is not a detection hypothesis: at commit level the Agent Braid primary flag equals path overlap plus `unknown` labelling, so no detection advantage over path-only orchestrators or naive overlap is hypothesized; H2 states only that the packaging (labelled file-level evidence, a bounded replay certificate for at most four operations, refusal controls and stated limits) may be useful to operators of worktree-agent workflows, and no requirement here tests it. *Empirical*: nothing obtained. *Formal*: no new result; the analyzer's definitions are unchanged. Null results, counterexamples and a host that cannot support the design are valid outcomes; protocol adherence is assessed separately from them.

Domain and observation contract: committed work only; file-level resources; at most 32 operations (replay and prepare at most four). Execution contract: read-only analysis and a non-allocating prepare step; no authority is created; the agents' tool surface is restricted by allowlist and registration mode (REQ-016). Host dependence: workflows were introduced in Claude Code v2.1.154 (documented current v2.1.309); the runtime has per-run approval, may be disabled by the organization, and gives no documented merge or conflict detection for worktree agents. Three behaviors are unconfirmed in documentation and become host-verification tasks (REQ-013): plugin MCP tools inside workflow agents, plugin agents as `agentType`, and calling a plugin workflow by name from nested `workflow()`; the permission allowlist of REQ-016 is observed under HV-5.

Compatibility: additive; Claude only (Codex ignores `workflows/`); no change to existing skills (the five product skills and the setup skill, six skill files), MCP tools, schemas or grants. Plugin version impact: the next release would be 0.1.0-alpha.4 (develop ships alpha.3), subject to founder decision. SPEC-053 depends on SPEC-023 (ADP.1) additively and is independent of SPEC-052 except for gate v2 (PR6), which consumes both and is blocked by G0 and by this gate's v1.

## Clarifications

Recorded with the founder on 2026-10-23 (`speckit-clarify`). These are planning
decisions, not acceptance or approval.

- **Sources:** a run requires at least two distinct sources; a single source
  yields no pairwise evidence and is refused.
- **Refs:** branch or tag names are accepted, resolved to full commit SHAs in
  the validation phase and re-resolved at the end; a moved ref is reported as
  stale.
- **Merge-tree objects:** the baseline runs with a temporary
  `GIT_OBJECT_DIRECTORY` that uses the repository store as an alternate, so no
  object is written into the repository.
- **Workspace:** `workspaceId` is a required explicit argument; the gate never
  defaults to a registered workspace and refuses when the agent's repository
  root does not match it.
- **MCP unavailability:** if host verification shows plugin MCP tools are not
  available to workflow agents, the analysis agent may use the bundled CLI only
  when the Bash permission can be constrained to the plugin launcher; otherwise
  R1 is no-go and only the documentation recipe ships. Interpretation recorded
  with this spec (plan.md, HV-5): the constraint is an explicit permission
  allowlist of launcher subcommands (`analyze-git`, `plan-git`, `verify-git`)
  that coexists with the fixed read-only Git prefixes the primary path already
  needs, and never the launcher binary as a whole. The closed list and its
  planning extensions are defined once in the next two bullets.
- **Constrained Bash (the single definition; SPEC-053 uses it unchanged):** a
  host permission rule set in force for the session that allows only (i) the
  fixed hardened read-only Git command templates, the exact baseline scratch
  commands (`mktemp -d "${TMPDIR:-/tmp}/braid-gate.XXXXXXXX"` and `rm -rf --` of
  one `braid-gate.XXXXXXXX` path under `TMPDIR`) and (ii) explicit launcher subcommands
  from a closed list, with no rule matching the launcher binary as a whole,
  `grant-policy-run`, `execute-policy-run`, `recover-policy-run` or any other
  subcommand, because the launcher also exposes grant and execute subcommands.
  The closed list for gate v1 is `analyze-git`, `plan-git`, `verify-git` and,
  as a planning interpretation approved by the founder on 2026-10-24, the read-only registry
  read `plugin workspaces` with no further arguments (no `--apply`, source
  root, runtime or grant option), which the fallback needs to compute the
  registry rules of REQ-002 and REQ-016 (REQ-016(e)); if the host cannot
  express an exact no-argument rule for it the fallback refuses
  (`mcp-unavailable`). Gate v1 admits the list only on the fallback path.
- **Planning amendment for gate v2 (approved by the founder on 2026-10-24):**
  SPEC-053 REQ-009 needs one additional explicit launcher subcommand,
  `analyze-claude-transcripts`, used alongside working MCP tools and not only
  as a fallback, because the plugin MCP is bound to registered workspaces and
  cannot read transcripts. It is read-only toward the repository, the registry
  and the transcripts and creates only its own new private output files at
  explicit paths. The host Bash allowlist cannot constrain those output paths,
  so the subcommand itself must refuse existing or out-of-scratch paths; it is
  therefore not "read-only" in the sense of REQ-016(b), and that difference is
  part of the approved amendment. A second planning amendment, approved by the founder on 2026-10-24, lets gate v2 prompts carry validated
  path tokens (transcript paths checked by the script) in addition to the
  identifiers REQ-008 and T004 allow today. It is admitted only for gate v2, which is blocked by G0 and
  by this gate's v1; gate v1 never allows it. If the founder refuses the
  amendment or the host cannot express the list, the transcript part of gate v2
  is no-go and the commit-level gate is unaffected.
- **Models:** gate agents inherit the session model; the workflow pins no model
  or effort.
- **Sequencing:** the packaging increment (PR2) may merge before adoption of the
  ADR 0024 amendment provided no version bump, `plugin-dist` publication or
  release occurs until adoption.
- **Release:** R1 ships the commit-level gate alone as the next alpha
  (expected `0.1.0-alpha.4`), independent of G0, subject to separate founder
  release acceptance.

## Evidence and open questions

Obtained evidence: none; human review pending. The planning questions (minimum number of sources, branch names, object-store quarantine, explicit workspace, CLI fallback, model policy, packaging before ADR adoption and the release number) were answered as planning decisions in the Clarifications above; they are not approvals. What remains open: host verification HV-1 to HV-5 (REQ-013), including the permission allowlist syntax (REQ-016), whether a plugin workflow resolves by name from nested `workflow()` and the effect of host restarts of stalled agents (HV-4); whether `git merge-tree --write-tree` accepts a tree-ish as a branch argument for the chained derivation of `expectedFinalTree` (a scratch test reported by the PR #671 review accepted a tree-ish and a commit with `--merge-base` on Git 2.54.0, Apple Git-157; that is not retained evidence, and the minimum Git version for the chained fold is still unstated, to be recorded by T005 and T011); whether the Git hardening template (REQ-006) can disable every configured merge driver and filter; ADR 0024 amendment adoption; the release number and any publication; and real multi-worktree observation (Article 19). Record feasibility failure, null and inconclusive outcomes as valid reports.
