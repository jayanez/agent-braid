# Prospective validation

No feature acceptance checks have run. The draft contracts ([argument schema](contracts/braid-gate-args.schema.json), [result schema](contracts/braid-gate-result.schema.json)) exist as planning files; the other named implementation files (integrations/agent-braid/plugin/workflows/braid-gate.js, tests/test_claude_workflow_gate.py, tests/claude_workflow_gate_helpers.py, docs/tooling/CLAUDE_WORKFLOWS.md) are planned, not existing. Host-dependent observations need a recorded Claude Code version and are never inferred from documentation. Task identifiers refer to [tasks.md](tasks.md); the plan and decisions are in [plan.md](plan.md) and [research.md](research.md); repeatable commands are in [quickstart.md](quickstart.md).

Three execution layers are kept separate in every procedure: (1) offline structural checks that always run (source inspection, schemas, fixture builder); (2) offline execution of the script with mocked agents in a recorded JavaScript runtime, where a missing runtime is an unavailable observation, never a pass; (3) native host receipts under `specs/052-claude-workflow-gate/evidence/` with the Claude Code version. A layer-1 or layer-2 result never substitutes for a layer-3 observation required by a procedure.

## procedure_req_001

Trace: REQ-001 / SC-001.

Given the native plugin is installed in Claude Code and the operator has registered a workspace, exercise: the operator invokes /agent-braid:braid-gate with args {base, sources, workspaceId} directly or through a nested workflow() call. Required observation: a plugin-shipped workflow script with a literal meta (name braid-gate, description, phases) starts, accepts only the documented argument fields, rejects unknown fields and missing required fields before any agent is spawned, and returns one structured result.

Commands and controls:
- Inspect the planned integrations/agent-braid/plugin/workflows/braid-gate.js: parse the leading `export const meta` literal and the argument validation block with the planned unit tests (tests/test_claude_workflow_gate.py, a Node-free structural parser or a pinned JS runtime recorded in the evidence; tasks T004, T006, T008). Validate the accepted arguments against contracts/braid-gate-args.schema.json.
- Feed fixture args: valid, missing base, missing workspaceId, unknown field, wrong types, empty sources, sources not an array, a single source, a duplicate source, an identifier with revision syntax. Host evidence: invoke `/agent-braid:braid-gate` directly and through a nested `workflow()` call (T026, T030).

Expected observation: meta.name is braid-gate; every invalid args case ends with status refused and zero agent() calls; a valid args case reaches the validation phase.

Failure handling: Any case that spawns an agent before argument validation, or accepts an undocumented field, fails the requirement; record the host and runtime used for the script check and treat a missing JS runtime as an unavailable observation, not a pass. Bind source, candidate, host version and policy identifiers; retain missingness, failures and all costs. Native or human acceptance needs its own obtained observations.

## procedure_req_002

Trace: REQ-002 / SC-002.

Given args name a base and a list of sources, exercise: the validation phase runs. Required observation: each input is resolved to a full commit identifier and pinned; the run is refused when a source equals the base, is unresolvable, duplicates another source, resolves to a commit that is not a descendant of the base, is not present in the registered workspace repository, there are fewer than two distinct sources, or the number of operations exceeds 32, or the explicit `workspaceId` is not registered (`workspace-not-registered`) or the repository root reported by Git differs from the registered `sourceRoot` (`workspace-root-mismatch`); the registered roots come from one read-only call of the bootstrap tool `workspaces` by the validate agent, which takes no admission lock (agent_braid/plugin_mcp.py, `PluginRouter.invoke`), or on the constrained-CLI fallback from the read-only launcher subcommand `plugin workspaces` (REQ-016(e)); the run is also refused under REQ-016 rules. The refusal names the offending input and the rule, and uncommitted work is stated as not observed.

Commands and controls:
- Run the planned fixture-repository builder to create a temporary repository with a base commit, two independent branches, a branch with no commit beyond base, a branch ahead with a deleted file, and a binary change.
- Execute the validation phase through the planned test harness that substitutes the validation agent with the same hardened read-only git commands (`git rev-parse --verify <input>^{commit}`, `git merge-base --is-ancestor`, `git cat-file -e`, the fixed template of REQ-006) and the registered-root comparison fed by a recorded `workspaces` result (tasks T005, T009), and independently through a native Claude Code run recorded as host evidence (T030).
- Feed `workspaces` fixtures with the explicit `workspaceId` absent from the registry (`workspace-not-registered`) and with a registered `sourceRoot` that differs from the repository root reported by Git (`workspace-root-mismatch`); neither may fall back to another registered workspace.

Expected observation: Each rejection rule, including `workspace-not-registered` and `workspace-root-mismatch`, produces status refused with a rule identifier; accepted inputs show 40-hex identifiers; the equal-to-base case is rejected (the analyzer alone would report complete coverage and an independent candidate for it); 33 sources are rejected and 32 accepted.

Failure handling: If the harness cannot reproduce a rule, keep the gap visible as an unobserved control. A source accepted that equals the base is a blocking defect because it is the known silent false negative. Neither an unregistered workspace nor a root mismatch ever falls back to another workspace. Bind source, candidate, host version and policy identifiers; retain missingness, failures and all costs. Native or human acceptance needs its own obtained observations.

## procedure_req_003

Trace: REQ-003 / SC-003.

Given validated pinned commits and a registered workspace, exercise: the analysis phase runs. Required observation: exactly one agent at a time calls the registered workspace's MCP `analyze-work` with `kind: git` and commit sources, because the plugin admission lock admits one caller; the validate agent's earlier `workspaces` call is a read-only bootstrap call and not an admission-lock caller; `analyze-git` is a bundled-CLI command used only on the constrained-CLI fallback; worktree and path sources are never used because plugin MCP worktree sources must match an operator allowlist; the structured output carries the analysis report reference, coverage, interaction classes and unknown effects without rewriting them.

Commands and controls:
- Static check of the planned workflow script: at most one agent call per phase, no parallel() or pipeline() fan-out around MCP phases, no isolation worktree option.
- Native run of the gate against the fixture repository; capture the MCP call transcript and the returned analysis report (T030). The tools visible to the agent (HV-1, T024) are recorded: the plugin `workspaces` bootstrap tool (read-only, no admission lock, called once by the validate agent) and `analyze-work` are the only MCP calls before finalization; `analyze-git` is not an MCP tool and appears only on the constrained-CLI fallback.

Expected observation: One analysis call per run; the report's interaction classes for the fixture pairs match the offline `analyze-git` output for the same commits; partial coverage and unknown effects from deletions, renames, binaries and symlinks are surfaced verbatim.

Failure handling: A second concurrent MCP caller or a worktree source is a defect. If MCP tools are not visible to workflow agents (host-verification HV-1) the declared fallback is the bundled CLI only on the constrained-CLI conditions of the Clarifications (REQ-016, including the registry checks of REQ-016(e)) or a refusal, never a silent downgrade. Bind source, candidate, host version and policy identifiers; retain missingness, failures and all costs. Native or human acceptance needs its own obtained observations.

## procedure_req_004

Trace: REQ-004 / SC-004.

Given an analysis result for N operations, exercise: N is 2 to 4 and the analysis allows replay. Required observation: the finalize phase obtains replay evidence and the advisory plan from the plugin MCP `analyze` tool (which runs the same replay code as the CLI `plan-git`, `git_replay.produce` inside `mcp_runtime.RuntimeTools`) with the script-derived runtime request, and reports the certificate digests or its failure; the MCP surface has no `plan-git` or `verify-git` tool and the MCP `verify` tool exists only in runtime mode, which REQ-005 and REQ-016 exclude, so `plan-git` and `verify-git` run only on the constrained-CLI fallback path; for N above 4 the replay is skipped with the stated limit, and a skipped replay is never reported as a pass. When `prepare` is not called, the certificate comes from `analyze` alone and the envelope states that independent consumer verification was not performed.

Commands and controls:
- Run the gate over fixtures with 2, 4 and 5 operations (T012, T030).
- Compare the replay evidence and advisory plan produced through the plugin MCP `analyze` tool with the script-derived runtime request (the same replay code as the CLI `plan-git`) with direct `plan-git` and `verify-git` invocations of the bundled CLI for the 2 and 4 operation cases; record that the MCP surface has no `plan-git` or `verify-git` tool and that the MCP `verify` tool exists only in runtime mode (excluded). Check that the envelope states when independent consumer verification was not performed (`prepare` not called).

Expected observation: 2 and 4 operations: certificate present and equal to the direct invocation; 5 operations: replay field says skipped with reason limit-4 and the overall status is not ok-certified.

Failure handling: Replay failure or timeout is reported as failed or inconclusive with the underlying message; do not retry in a loop. Bind source, candidate, host version and policy identifiers; retain missingness, failures and all costs. Native or human acceptance needs its own obtained observations.

## procedure_req_005

Trace: REQ-005 / SC-005.

Given 2 to 4 operations, complete coverage for the analysed pairs, no conflicting or unknown pair, a clean completed baseline, replay evidence from `analyze` and a runtime request the script could derive in full (order, `expectedFinalTree`, `declaredWrites` equal to the observed paths, empty `uncertainPaths`, `runDirectory` under the registered result root), exercise: the finalization phase runs. Required observation: the gate calls the plugin MCP `prepare` tool once in serial mode and reports the batch reference for the operator; `prepare` rehearses in a temporary directory and allocates no run directory (`git_runtime.prepare_run`); with any conflicting or unknown pair, a conflicting or unavailable baseline, more than four operations, partial coverage or any underivable request field it does not prepare and states the reason (`not-prepared`), never guessing a value; it never creates, requests or accepts a grant, never calls an execute, recover, verify, status or runtime-mode tool, and never starts the owned runtime.

Commands and controls:
- Run the gate over the fixture with independent edits (prepare expected), conflicting edits, a deletion (unknown) and five operations (T012, T030).
- Inspect the MCP transcript for the set of tool names called; the allowed set is `workspaces`, `analyze-work`, `analyze` and `prepare` (serial mode).
- Where `expectedFinalTree` cannot be derived, expect `not-prepared` with `expected-tree-unavailable` rather than a guessed tree; likewise for an underivable `declaredWrites` (`declared-writes-mismatch`) or `runDirectory`. Assert that the derived request has full 40-hex ids, a dependency-respecting `order` (input order, labelled not a recommendation), empty `uncertainPaths` and 2 to 4 operations, and that `prepare` allocated no run directory under the registered result root.
- Run the planted-grant negative test: a registration with runtime enabled and a grant store makes the validate phase refuse with `runtime-enabled-workspace` before any other agent runs (REQ-016).

Expected observation: Prepared batch only in the clean case; transcript contains no grant, execute, recover or status-of-execution call; the result reports executionAuthorization false in every case.

Failure handling: Any grant or execute attempt, even refused by the host, is a blocking defect of the script, prompt or host allowlist; prevention is the job of REQ-016 and the attempt is also detected by transcript inspection. Prepare errors are reported verbatim. Bind source, candidate, host version and policy identifiers; retain missingness, failures and all costs. Native or human acceptance needs its own obtained observations.

## procedure_req_006

Trace: REQ-006 / SC-006.

Given validated pinned commits that share the base, exercise: the baseline phase runs. Required observation: for every pair the gate reports the result of git merge-tree --write-tree with the explicit merge base, computed with a temporary object directory so that no object reaches the repository, together with conflicted paths or an error; every Git command of every phase uses one fixed hardened template embedded as script constants (system and global configuration disabled, hooks, fsmonitor, external merge drivers and content filters disabled, no network or credential prompt, an explicit `GIT_OBJECT_DIRECTORY` for the baseline) following docs/architecture/PARALLEL_INTEGRATION.md; a command that cannot be hardened is reported as a stated limit and its phase as unavailable or inconclusive, never run unhardened; the baseline is reported alongside, never merged into, the analyzer verdict, and merge results are ephemeral and never applied.

Commands and controls:
- Run the baseline over the fixtures: disjoint files, same file different hunks, same hunk, delete versus modify, rename, binary (T005, T011).
- Record `git count-objects -v` and `git fsck --unreachable --no-reflogs` before and after the run.
- Hardening control (T011, T030): a fixture repository whose configuration and attributes contain a sentinel hook, `core.fsmonitor` command, external merge driver and content filter that write a marker file; the baseline and every other Git command of the gate must leave no marker, and a command that cannot be hardened must make its phase unavailable or inconclusive. Assert that the command text sent to agents is the fixed template (no network, `GIT_TERMINAL_PROMPT=0`, system and global configuration disabled, explicit temporary `GIT_OBJECT_DIRECTORY`).
- Confirm merge-tree results (pairwise and chained) are discarded with the temporary object directory and never applied to a ref, worktree or the repository store.

Expected observation: Per-pair outcomes match direct `git merge-tree --write-tree --merge-base` runs; object counts and unreachable-object output are unchanged; refs unchanged.

Failure handling: Any new object or ref in the repository is a defect, and so is the execution of a sentinel hook, fsmonitor, merge driver or filter planted in the repository configuration. A Git version without merge-tree --write-tree is reported as baseline unavailable, not as clean. Bind source, candidate, host version and policy identifiers; retain missingness, failures and all costs. Native or human acceptance needs its own obtained observations.

## procedure_req_007

Trace: REQ-007 / SC-007.

Given the gate finished, was refused or was inconclusive, exercise: the result is produced. Required observation: the script returns a schema-validated envelope with executionAuthorization false, pinned base and source identifiers, operation count, per-phase status, analyzer interactions with coverage, replay and prepare status, baseline pairs, an agreement classification between analyzer and baseline, an advisory order that is `null` unless the analysis declares dependencies (the gate declares none, and the order used for `prepare` is labelled input order, not a recommendation), the number of agents used, the end-of-run stale-reference report (a moved or deleted reference makes the status `inconclusive`), an `assurance` block (compatibility class, property, evidence method, domain, assumptions, observation contract and execution contract, plus a constant `notAGuarantee` marker; the class is set by the script, is `0-heuristic`, and is not verified evidence or authorization), and explicit limits (file-level resources, coarser than hunk merging, no reads, only committed work, no speed claim).

Commands and controls:
- Validate result samples from every status against contracts/braid-gate-result.schema.json (drafted in T001, tested in T007, produced by the script in T008 and T013).
- Re-resolve the source references at the end of the run in the harness and move a branch between phases, then delete one: the status is `inconclusive`, `staleRefs.report` names the input, the pinned and current identifiers and the reason, and no phase is re-run.
- Assert the `assurance` block is present with `compatibilityClass` `0-heuristic`, every other field non-empty and `notAGuarantee` true, and that `advisoryOrder` is `null` whenever no dependencies were declared; reject a result whose `assurance` is missing or altered.
- Agent count: argument refusal uses 0 agents, a run that completes validate, analyze, baseline and finalize uses exactly 4, and an earlier refusal, busy or failure uses fewer.

Expected observation: All statuses validate; the limits array is non-empty and identical in content across statuses; a moved ref is reported as stale rather than silently reanalysed.

Failure handling: An envelope without limits or the assurance block, or with an authorization field other than false, fails. Unknown extra fields are rejected by the schema. Bind source, candidate, host version and policy identifiers; retain missingness, failures and all costs. Native or human acceptance needs its own obtained observations.

## procedure_req_008

Trace: REQ-008 / SC-008.

Given the packaged workflow and plugin manifest, exercise: they are statically and dynamically inspected. Required observation: the workflow spawns at most four agents per run, strictly sequentially, none with worktree isolation, none instructed to edit files, apply a merge, push, create refs or branches, or run hooks; no agent call sets a `model` or `effort` option (agents inherit the session model); the plugin ships no hooks, mods or agent definitions for the gate; agent prompts embed only validated identifiers and schema-bound structured results, never raw repository text.

Commands and controls:
- Planned static checks over the workflow script and package inventory: forbidden calls and options, absence of hooks and mods files, prompt templates containing only validated placeholders, and no `model` or `effort` option on any `agent(` call, with a mutation control that adds one and must fail the check (T004, T015).
- Dynamic observation: refs, worktrees and working tree status before and after a native run.

Expected observation: Zero edits, zero refs changed, zero extra worktrees; inventory contains the workflow file and no hook or mod file; the agent count is at most four.

Failure handling: A prompt carrying commit messages or file contents, a parallel() wrapper, isolation worktree, or a `model` or `effort` option on any agent call fails this requirement. Bind source, candidate, host version and policy identifiers; retain missingness, failures and all costs. Native or human acceptance needs its own obtained observations.

## procedure_req_009

Trace: REQ-009 / SC-009.

Given the gate is used under host approval or auto mode, exercise: the result or documentation describes what was checked. Required observation: host approval and auto mode are treated as no authority (ADR 0021), the script-computed prompts are not user authority, the operator grants outside the workflow, wording never claims faster integration, guaranteed order independence, conflict freedom or semantic correctness, and analysis is kept separate from execution.

Commands and controls:
- Review the planned envelope text, workflow comments and docs/tooling/CLAUDE_WORKFLOWS.md against a claim-discipline checklist.
- Run the gate in a host auto-mode session and check that no operator action is taken (T031).

Expected observation: Only the permitted claims appear; the result never suggests execution is allowed; auto-mode run yields the same envelope.

Failure handling: Any speed, safety or semantic-correctness claim, or any implied approval, is corrected before acceptance; the negative parallel-speedup results (SPEC-021 G4, SPEC-022, SPEC-038) are cited, never contradicted. Bind source, candidate, host version and policy identifiers; retain missingness, failures and all costs. Native or human acceptance needs its own obtained observations.

## procedure_req_010

Trace: REQ-010 / SC-010.

Given the plugin admission lock is busy, the workspace is not registered, MCP limits are exceeded, a timeout occurs, the workflow is disabled by the organization, or the host restarts a stalled gate agent automatically, exercise: the gate runs. Required observation: the result is refused, busy or inconclusive with the specific condition, without retry loops in the script, without choosing another workspace, without widening limits, and with partial phase outputs preserved; a host restart is tolerated by contract (MCP calls are read-only and idempotent, a busy refusal that may stem from the gate's own earlier attempt is reported as `inconclusive`, every agent result still passes the strict schema, and `agentsUsed` counts script-launched agents as a lower bound).

Commands and controls:
- Provoke each condition in the harness: hold the admission lock from a second caller, use an unregistered workspaceId, exceed the 1 MiB or 32-operation limit, simulate a timeout (T006, T014), and (host evidence) run under disableWorkflows (T031).
- Host restarts (T014, T047, host evidence T027): deliver the same phase result twice, and a busy admission-lock refusal after the first attempt of the same phase completed; assert a schema-valid envelope, a busy result attributable to the gate's own attempt reported as `inconclusive`, `prepare` requested at most once by the script, no script retry, and no unvalidated agent result trusted. The host side is observed under HV-4 with a forced stall.

Expected observation: Each condition maps to its status and message; no second workspace is tried; no automatic retry occurs in the script; a restarted attempt is recorded and its output is schema-checked like any other.

Failure handling: Infinite or repeated retries, or fabricating a clean verdict after a failure, fail the requirement. Bind source, candidate, host version and policy identifiers; retain missingness, failures and all costs. Native or human acceptance needs its own obtained observations.

## procedure_req_011

Trace: REQ-011 / SC-011.

Given a clean source checkout, exercise: scripts/build_native_plugin.py assembles the plugin. Required observation: until the ADR 0024 amendment is adopted the build excludes `workflows/` by default and includes it only with an explicit opt-in that marks the artifact engineering-only (never a releasable identity, since the version string is unchanged); with the opt-in, and by default after adoption, the workflow source under integrations/agent-braid/plugin/workflows is copied to plugin/workflows with a byte-stable inventory entry and hash, the Claude manifest discovers it, the portable (Codex) manifest and MCP configuration are unchanged and Codex ignores the directory, existing skills and the setup skill are byte-identical, and package verification rejects a missing, altered or extra workflow file.

Commands and controls:
- Build twice from the same clean commit and compare inventories and hashes (T015, T016; release candidate T039).
- Tamper with workflows/braid-gate.js in a copy and run package verification.
- Pre-adoption guard (T015, T016): the default build excludes `workflows/` (inventory without the entry, package verification passes) and the explicit opt-in build includes it and is marked engineering-only; assert both, and that the opt-in build keeps the unchanged version string and is never a release identity. After adoption (T036) the default includes the workflow and the tests assert that instead.
- Diff the Codex manifest, MCP configuration and skill trees against the previous alpha package.

Expected observation: Identical bytes across builds; verification fails on tampering; no change outside the workflows entry and the documented README wording and version bump.

Failure handling: Non-reproducible bytes, changed existing skills, a default pre-adoption build that contains `workflows/`, or an opt-in build presented as a release block the requirement; the build never modifies the frozen Git runners. Bind source, candidate, host version and policy identifiers; retain missingness, failures and all costs. Native or human acceptance needs its own obtained observations.

## procedure_req_012

Trace: REQ-012 / SC-012.

Given a user who runs their own Claude workflows with worktree agents, exercise: they read the recipe. Required observation: it shows how to end a workflow with the gate directly or via nested workflow(), how to split sign-off into separate workflows, what the gate returns and does not return, how the operator grants and executes outside the workflow, the host-verification status of each unconfirmed behavior, and the claude-code versions observed.

Commands and controls:
- Planned documentation review plus a link and anchor check; run the example commands in the fixture repository (T019, T032).

Expected observation: Every command in the recipe runs or is explicitly marked unverified; limits are quoted from the result envelope.

Failure handling: Unverified host behavior presented as fact fails review. Bind source, candidate, host version and policy identifiers; retain missingness, failures and all costs. Native or human acceptance needs its own obtained observations.

## procedure_req_013

Trace: REQ-013 / SC-013.

Given the documentation does not confirm that plugin MCP tools are available inside workflow agents, that plugin agents can be used as agentType, or that a plugin workflow can be called by name from nested workflow(), exercise: host verification runs on a recorded Claude Code version. Required observation: each behavior (HV-1 plugin MCP tools in workflow agents, HV-2 plugin agentType, HV-3 nested call by plugin name, HV-4 resume after interruption and automatic restart of a stalled agent, HV-5 per-run approval, auto-mode prompts and the permission allowlist of REQ-016) has a recorded pass, fail or unobserved outcome with version, and the design degrades to a declared fallback or a no-go when a required behavior fails.

Commands and controls:
- Run the native probes on a recorded Claude Code version with the plugin installed; save transcripts, version and outcome per behavior in the evidence directory (T023 to T029). The founder provides the host at EUR 0 additional spend.
- Record in HV-1 and HV-5 the exact plugin tool names visible to a workflow agent (with a runtime-enabled and an analysis-only registration) and the permission rules used (REQ-016).

Expected observation: Five outcome records exist; R1 depends only on the behaviors it needs (HV-1, HV-3 for the nested path, HV-5).

Failure handling: A failed required behavior records a negative result and triggers the fallback or kill criterion in program.md; negative outcomes are valid. Bind source, candidate, host version and policy identifiers; retain missingness, failures and all costs. Native or human acceptance needs its own obtained observations.

## procedure_req_014

Trace: REQ-014 / SC-014.

Given a candidate plugin package containing the workflow, exercise: release is considered. Required observation: acceptance records the clean source commit, package and inventory hashes, a fresh-checkout reproduction, native install on supported hosts, the gate over the fixture matrix, update from the previous alpha and uninstall behavior, with unobserved platforms stated; publication to plugin-dist and any remote artifact remains a separate founder decision and is not part of this delivery.

Commands and controls:
- Planned release acceptance document modeled on specs/046-native-ai-plugins/release-acceptance.md (T037 to T041); no publication command is part of the procedure. The scoped, owner-authorized publication task (T042) is separate and not part of this delivery.

Expected observation: Acceptance record exists with hashes and explicit gaps; no remote write occurred.

Failure handling: Missing observations remain listed as not observed; no claim of compatibility for unobserved hosts. Bind source, candidate, host version and policy identifiers; retain missingness, failures and all costs. Native or human acceptance needs its own obtained observations.

## procedure_req_015

Trace: REQ-015 / SC-015.

Given a fixture corpus of base and branch commits with known file-level truth, including delete versus modify, rename, binary, same hunk, different hunks and untouched pairs, exercise: the analyzer verdict and the merge-tree baseline are compared per pair. Required observation: the agreement classification (both clean, both conflicting, analyzer stricter, baseline stricter, analyzer unknown) is reported with a naive path-overlap column (paths changed by both branches relative to the base); an analyzer `conflicting` pair counts as added detection only where naive overlap missed it (expected: none at commit level, so any such pair is an analyzer-versus-naive discrepancy to explain, not a success); any case where the analyzer says independent-candidate and the baseline conflicts is a recorded counterexample, and no hypothesis of conservativeness is claimed beyond the corpus.

Commands and controls:
- Run the corpus through the analyzer and direct merge-tree; tabulate classification counts and list counterexamples with commit identifiers (T005, T021); compute naive path overlap (paths changed by both branches relative to the base) for every pair and report the analyzer against it, so that a hit counts as added detection only where naive overlap missed it. Truth labels are written before any tool output is read.

Expected observation: Complete classification table with denominators; counterexamples listed or stated as none observed in this corpus.

Failure handling: A counterexample is a valid finding and blocks conservativeness wording; it does not by itself fail the protocol. Bind source, candidate, host version and policy identifiers; retain missingness, failures and all costs. Native or human acceptance needs its own obtained observations.

## Candidate checks

Run the quick validation profile after coherent changes and the pr profile once stable, using isolated pinned dependencies (`python3 -m scripts.validate_change --base develop --profile quick`). Frozen-candidate evidence, independent review, human review and founder decisions remain separate. No remote write, publication or concurrent agent run is part of any procedure here.

## procedure_req_016

Trace: REQ-016 / SC-016.

Given the gate runs under any permission mode, exercise: the validate phase reads the registry and the agents run. Required observation: (a) the script refuses with `runtime-enabled-workspace` when any registered workspace has runtime enabled or a grant store, because the plugin MCP then lists model-callable `execute`, `recover`, `verify` and `status` tools next to the gate's own (the tool definitions are the union over registered workspaces) and a script-computed prompt is not a concurrency or authority control (Article 12; ADR 0021: host approval is not runtime authority); (b) on the MCP path the recipe and the host receipts require a host permission allowlist that allows only the plugin tools `workspaces`, `analyze-work`, `analyze` and `prepare` the fixed hardened read-only Git command templates, the exact scratch creation command `mktemp -d "${TMPDIR:-/tmp}/braid-gate.XXXXXXXX"` and `rm -rf --` of one `braid-gate.XXXXXXXX` path directly under `TMPDIR` (the only writes, a temporary directory outside the repository; the agent checks the path pattern before removal and reports `removed`, `failed` or `refused`, and a scratch that was not removed is a stated limit that prevents certification); a host that cannot express the last two narrowly makes the baseline phase unavailable (a recorded no-go), not unhardened, with the exact visible tool names recorded in HV-1 and HV-5; (c) the validate agent reports, under a strict schema, the plugin tool names visible to it, and the script refuses with `unsafe-tool-surface` when `execute`, `recover`, `verify` or `status` is among them instead of relying on instructions (an agent-reported defensive check, not enforcement; HV-1 records whether the host can deny them); (d) the constrained Bash is defined once, here and in the Clarifications: a host permission rule set in force for the session that allows only the fixed read-only Git prefixes and explicit launcher subcommands from a closed list, never the launcher binary as a whole, because the launcher also exposes grant and execute subcommands; for gate v1 the closed list is `analyze-git`, `plan-git`, `verify-git` and the read-only registry read `plugin workspaces` with no further arguments, admitted only on the constrained-CLI fallback (MCP tools not visible to workflow agents, HV-1); gate v2 (SPEC-053, blocked by G0) would add exactly one more explicit subcommand, `analyze-claude-transcripts`, usable alongside working MCP tools, as a planning amendment approved by the founder on 2026-10-24; (e) on the constrained-CLI fallback the registry rules are computed from the rows printed by `plugin workspaces` (the same fields as the MCP bootstrap tool, read live instead of from the connect-time snapshot): `workspace-not-registered`, `workspace-root-mismatch` and `runtime-enabled-workspace` apply unchanged, the `unsafe-tool-surface` check applies to any plugin tool names the validate agent reports, and the Bash allowlist, which the script cannot observe, is the only control for the launcher; the fallback refuses with `mcp-unavailable` when the registry rows cannot be obtained or parsed, and is a recorded no-go unless HV-5 recorded that the host can express the allowlist.

Commands and controls:
- Harness (T006, T012): feed `workspaces` fixtures in which one registered workspace has `runtimeEnabled` true with a grant store while the explicit `workspaceId` names a different, analysis-only workspace; expect `refused` with rule `runtime-enabled-workspace`, zero agent calls after validate and no `analyze-work` call. Repeat with the explicit workspace itself runtime-enabled.
- Native (T024, T028, T030): with an analysis-only registration, record the plugin tool names the workflow agent can see (expected `workspaces`, `plugin-status`, `analyze-work`, `analyze`, `prepare`) and the allowlist rules in force; with a deliberately runtime-enabled scratch registration and a planted grant, confirm the gate refuses before any agent can call `execute`, `recover`, `verify` or `status`, and that the MCP transcript contains none of those calls.
- Inspect the recipe and the fallback rules: the launcher is allowed only through the explicit subcommands `analyze-git`, `plan-git`, `verify-git` and `plugin workspaces` with no further arguments (no `--apply`, source root, runtime or grant option), and no rule matches the launcher binary as a whole, `grant-policy-run`, `execute-policy-run`, `recover-policy-run`, `analyze-claude-transcripts` (gate v2 only, SPEC-053) or any other launcher subcommand.
- Harness (T006, T009): on the constrained-CLI fallback fixtures feed the rows printed by `plugin workspaces`; expect the same `workspace-not-registered`, `workspace-root-mismatch` and `runtime-enabled-workspace` refusals as on the MCP path, and `mcp-unavailable` when the rows are missing or unparsable; a fallback run whose HV-5 receipt does not record an expressible allowlist is a recorded no-go, not a pass.

Expected observation: the runtime-enabled registration is refused by script code; the transcript shows only allowlisted tools; a host that cannot deny `execute`, `recover`, `verify` or `status` yields a refused or inconclusive record, not a pass; the CLI fallback is recorded no-go when the explicit-subcommand allowlist cannot be expressed.

Failure handling: A grant or execute attempt, even refused by the host, a registration with runtime enabled that is not refused, or a fallback rule that matches `grant-policy-run`, `execute-policy-run` or other launcher subcommands, or a v1 rule set that admits `analyze-claude-transcripts`, is a blocking defect. A host that cannot express the allowlist is a recorded no-go input for the CLI fallback, not a pass. Limit stated: rule (a) is computed after the validate agent has already run, so for that one agent the host allowlist (b) is the only control; this is why (b) is required and recorded rather than assumed. Bind source, candidate, host version and policy identifiers; retain missingness, failures and all costs. Native or human acceptance needs its own obtained observations.
